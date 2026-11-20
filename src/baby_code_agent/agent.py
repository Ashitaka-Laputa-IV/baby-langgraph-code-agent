"""Build the LangGraph agent."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

SYSTEM_PROMPT = """\
You are a small coding agent working in {root}.

Rules:
- Inspect the repository before changing it. Use list_dir and read_file first.
- Make focused edits with write_file. Keep existing conventions and style.
- Use run_shell to run tests or commands; the user must approve each command.
- Filesystem tools are limited to the working directory, and .git metadata is read-only.
- When you are done, summarize what changed and what you verified.
"""


@wrap_tool_call
def _tool_errors_as_messages(request, handler):
    """Turn a raised tool exception into a tool result so one failure does not end the run."""
    try:
        return handler(request)
    except Exception as exc:  # noqa: BLE001 - surface any tool failure to the model
        return ToolMessage(
            content=f"Error: {type(exc).__name__}: {exc}",
            tool_call_id=request.tool_call["id"],
            status="error",
        )


def build_system_prompt(root: Path) -> str:
    return SYSTEM_PROMPT.format(root=root.resolve())


def build_agent(
    model: BaseChatModel,
    tools: list[BaseTool],
    root: Path,
    checkpointer: Any | None = None,
) -> Any:
    """Compile the model/tool loop into a LangGraph agent."""
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=build_system_prompt(root),
        middleware=[_tool_errors_as_messages],
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
    )


def new_thread_id() -> str:
    return uuid.uuid4().hex
