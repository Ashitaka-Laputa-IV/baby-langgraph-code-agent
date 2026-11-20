"""Command-line entry point and interactive terminal loop."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from baby_code_agent.agent import build_agent, new_thread_id
from baby_code_agent.model import create_chat_model
from baby_code_agent.settings import ConfigError, load_settings
from baby_code_agent.tools import build_tools, format_command_for_display, sanitize_for_terminal

EXIT_COMMANDS = ("/exit", "/quit")
HELP_COMMAND = "/help"
RESET_COMMAND = "/reset"
HELP_TEXT = """\
/help   show this help
/reset  start a new conversation thread
/exit   leave the session (Ctrl+C and EOF also exit)
/quit   alias for /exit
"""


@dataclass
class Session:
    agent: Any
    thread_id: str = field(default_factory=new_thread_id)

    def reset(self) -> None:
        previous = self.thread_id
        self.thread_id = new_thread_id()
        checkpointer = getattr(self.agent, "checkpointer", None)
        delete_thread = getattr(checkpointer, "delete_thread", None)
        if callable(delete_thread):
            try:
                delete_thread(previous)
            except Exception:  # noqa: BLE001 - a reset must never fail the session
                pass


class TurnRenderer:
    """Render one streamed turn, suspending the live region before tool output."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self._live: Live | None = None
        self._buffer = ""

    def add_text(self, text: str) -> None:
        if not text:
            return
        self._buffer += sanitize_for_terminal(text)
        if self._live is None:
            self._live = Live(
                Markdown(self._buffer),
                console=self.console,
                refresh_per_second=12,
                transient=False,
            )
            self._live.start()
        else:
            self._live.update(Markdown(self._buffer))

    def flush_text(self) -> None:
        if self._live is not None:
            self._live.update(Markdown(self._buffer))
            self._live.stop()
            self._live = None
        self._buffer = ""

    def _show_panel(self, title: str, body: Any, border_style: str) -> None:
        self.flush_text()
        self.console.print(
            Panel(
                Text(sanitize_for_terminal(str(body)), overflow="fold"),
                title=sanitize_for_terminal(title),
                border_style=border_style,
            )
        )

    def show_tool_call(self, name: str, args: Any) -> None:
        self._show_panel(f"tool · {name}", args, "cyan")

    def show_tool_result(self, content: Any) -> None:
        self._show_panel("result", content, "dim")

    def close(self) -> None:
        self.flush_text()


def _render_message(renderer: TurnRenderer, message: Any) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        for tool_call in message.tool_calls:
            renderer.show_tool_call(tool_call["name"], tool_call["args"])
    elif isinstance(message, ToolMessage):
        renderer.show_tool_result(message.content)


def _render_update(renderer: TurnRenderer, chunk: Any) -> None:
    if not isinstance(chunk, dict):
        return
    for update in chunk.values():
        if isinstance(update, dict) and isinstance(update.get("messages"), list):
            for message in update["messages"]:
                _render_message(renderer, message)


def run_turn(session: Session, renderer: TurnRenderer, prompt: str) -> None:
    config = {"configurable": {"thread_id": session.thread_id}}
    stream = session.agent.stream(
        {"messages": [HumanMessage(content=prompt)]},
        config=config,
        stream_mode=["messages", "updates"],
    )
    try:
        for mode, chunk in stream:
            if mode == "messages":
                message, _metadata = chunk
                if isinstance(message, (AIMessage, AIMessageChunk)):
                    renderer.add_text(message.text)
            elif mode == "updates":
                _render_update(renderer, chunk)
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
        renderer.close()


def build_confirm(console: Console) -> Callable[[str], bool]:
    def confirm(command: str) -> bool:
        if not console.is_terminal:
            console.print("[red]Shell execution is unavailable in a non-interactive console.[/red]")
            return False
        console.print(
            Panel(
                Text(format_command_for_display(command), overflow="fold"),
                title="Shell command",
                border_style="yellow",
            )
        )
        try:
            return Confirm.ask("Run this command?", console=console, default=False)
        except (EOFError, KeyboardInterrupt):
            console.print()
            return False

    return confirm


def render_banner(console: Console, model_name: str, root: Path) -> None:
    body = Text()
    body.append("model  ", style="dim")
    body.append(f"{sanitize_for_terminal(model_name)}\n")
    body.append("root   ", style="dim")
    body.append(sanitize_for_terminal(str(root)))
    console.print(Panel(body, title="Baby LangGraph Code Agent", border_style="cyan"))


def run_repl(
    session: Session,
    console: Console,
    model_name: str,
    root: Path,
    read_input: Callable[[], str] | None = None,
) -> None:
    render_banner(console, model_name, root)
    read = read_input or (lambda: console.input("[bold cyan]>[/] "))

    while True:
        try:
            line = read()
        except (EOFError, KeyboardInterrupt, StopIteration):
            console.print()
            return

        prompt = line.strip()
        if not prompt:
            continue

        command = prompt.casefold()
        if command in EXIT_COMMANDS:
            return
        if command == HELP_COMMAND:
            console.print(HELP_TEXT, markup=False)
            continue
        if command == RESET_COMMAND:
            session.reset()
            console.print("[dim]Started a new thread.[/dim]")
            continue

        renderer = TurnRenderer(console)
        try:
            run_turn(session, renderer, prompt)
        except Exception as exc:  # noqa: BLE001 - a failed turn must not end the session
            message = sanitize_for_terminal(f"Error: {type(exc).__name__}: {exc}")
            console.print(Text(message, style="red"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="baby-code-agent",
        description="A small LangGraph code agent that reads, edits, and runs code in the current directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    console = Console()
    root = Path.cwd()
    tools = build_tools(root, confirm=build_confirm(console))
    model = create_chat_model(settings)
    agent = build_agent(model, tools, root)

    run_repl(Session(agent=agent), console, model_name=settings.model, root=root)
    return 0
