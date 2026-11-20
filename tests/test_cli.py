import io
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from rich.console import Console

from baby_code_agent.agent import build_agent
from baby_code_agent.cli import Session, main, run_repl
from baby_code_agent.tools import build_tools
from tests.fakes import RaisingModel, ScriptedToolModel


def tool_call(name, args, call_id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def make_console():
    return Console(file=io.StringIO(), record=True, force_terminal=False, width=110)


def make_session(tmp_path: Path, responses, confirm=lambda _: False):
    model = ScriptedToolModel(responses=responses, seen_message_counts=[])
    tools = build_tools(tmp_path, confirm=confirm)
    agent = build_agent(model, tools, tmp_path)
    return Session(agent=agent)


def feed(lines):
    iterator = iter(lines)
    return lambda: next(iterator)


def output_of(console):
    return console.export_text()


def test_help_exits_zero_without_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENCODEGOAPIKEY", raising=False)

    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])

    assert excinfo.value.code == 0
    assert "baby-code-agent" in capsys.readouterr().out


def test_missing_key_exits_non_zero(monkeypatch, capsys):
    monkeypatch.delenv("OPENCODEGOAPIKEY", raising=False)

    assert main([]) == 2
    assert "OPENCODEGOAPIKEY" in capsys.readouterr().err


def test_help_command_lists_commands(tmp_path):
    console = make_console()
    session = make_session(tmp_path, [AIMessage(content="unused")])

    run_repl(session, console, "test-model", tmp_path, feed(["/help", "/exit"]))

    text = output_of(console)
    assert "/reset" in text
    assert "show this help" in text


def test_exit_and_eof_end_the_loop(tmp_path):
    console = make_console()
    session = make_session(tmp_path, [AIMessage(content="unused")])

    run_repl(session, console, "test-model", tmp_path, feed(["/exit"]))

    def raise_eof():
        raise EOFError

    run_repl(session, make_console(), "test-model", tmp_path, raise_eof)


def test_reset_changes_thread_id(tmp_path):
    console = make_console()
    session = make_session(tmp_path, [AIMessage(content="unused")])
    original = session.thread_id

    run_repl(session, console, "test-model", tmp_path, feed(["/reset", "/exit"]))

    assert session.thread_id != original


def test_streamed_turn_renders_text_and_tool_panel(tmp_path):
    (tmp_path / "notes.txt").write_text("hello\n", encoding="utf-8")
    responses = [tool_call("read_file", {"path": "notes.txt"}), AIMessage(content="all done")]
    session = make_session(tmp_path, responses)
    console = make_console()

    run_repl(session, console, "test-model", tmp_path, feed(["read the notes", "/exit"]))

    text = output_of(console)
    assert "all done" in text
    assert "tool · read_file" in text


def test_denied_shell_call_is_rendered_and_turn_completes(tmp_path):
    responses = [
        tool_call("run_shell", {"command": "echo nope"}),
        AIMessage(content="understood"),
    ]
    session = make_session(tmp_path, responses, confirm=lambda _: False)
    console = make_console()

    run_repl(session, console, "test-model", tmp_path, feed(["run it", "/exit"]))

    text = output_of(console)
    assert "denied" in text
    assert "understood" in text


def test_turn_error_does_not_end_session(tmp_path):
    model = RaisingModel()
    agent = build_agent(model, build_tools(tmp_path, confirm=lambda _: False), tmp_path)
    console = make_console()
    prompts = []

    def read():
        prompts.append(1)
        return ["break please", "/exit"][len(prompts) - 1]

    run_repl(Session(agent=agent), console, "test-model", tmp_path, read)

    text = output_of(console)
    assert "Error: RuntimeError: provider unreachable" in text
    assert len(prompts) == 2
