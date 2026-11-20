from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from baby_code_agent.agent import build_agent, new_thread_id
from baby_code_agent.tools import build_tools


class ScriptedToolModel(BaseChatModel):
    """A fake chat model that replays scripted AI messages and supports tool binding."""

    responses: list[AIMessage]
    seen_message_counts: list[int] = []

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.seen_message_counts.append(len(messages))
        index = min(len(self.seen_message_counts) - 1, len(self.responses) - 1)
        return ChatResult(generations=[ChatGeneration(message=self.responses[index])])


def call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "notes.txt").write_text("hello\n", encoding="utf-8")
    return tmp_path


def test_tool_loop_executes_two_calls_then_answers(root):
    responses = [
        call("list_dir", {"path": "."}, "c1"),
        call("read_file", {"path": "notes.txt"}, "c2"),
        AIMessage(content="done"),
    ]
    model = ScriptedToolModel(responses=responses, seen_message_counts=[])
    tools = build_tools(root, confirm=lambda _: False)
    agent = build_agent(model, tools, root)

    result = agent.invoke(
        {"messages": [HumanMessage(content="inspect the repo")]},
        config={"configurable": {"thread_id": new_thread_id()}},
    )

    tool_messages = [message for message in result["messages"] if message.type == "tool"]
    assert len(tool_messages) == 2
    assert "hello" in tool_messages[1].content
    assert result["messages"][-1].content == "done"


def test_thread_history_is_reused(root):
    responses = [AIMessage(content="first answer"), AIMessage(content="second answer")]
    model = ScriptedToolModel(responses=responses, seen_message_counts=[])
    agent = build_agent(model, build_tools(root, confirm=lambda _: False), root)
    thread = {"configurable": {"thread_id": "thread-1"}}

    agent.invoke({"messages": [HumanMessage(content="first")]}, config=thread)
    agent.invoke({"messages": [HumanMessage(content="second")]}, config=thread)

    assert model.seen_message_counts[0] == 2
    assert model.seen_message_counts[1] == model.seen_message_counts[0] + 2


def test_new_thread_does_not_see_previous_history(root):
    model = ScriptedToolModel(
        responses=[AIMessage(content="one"), AIMessage(content="two")],
        seen_message_counts=[],
    )
    agent = build_agent(model, build_tools(root, confirm=lambda _: False), root)

    agent.invoke(
        {"messages": [HumanMessage(content="first")]},
        config={"configurable": {"thread_id": "a"}},
    )
    agent.invoke(
        {"messages": [HumanMessage(content="second")]},
        config={"configurable": {"thread_id": "b"}},
    )

    assert model.seen_message_counts == [2, 2]


def test_raising_tool_becomes_error_message_and_loop_finishes(root):
    @tool
    def explode() -> str:
        """Always raise."""
        raise RuntimeError("boom")

    responses = [call("explode", {}, "c1"), AIMessage(content="recovered")]
    model = ScriptedToolModel(responses=responses, seen_message_counts=[])
    agent = build_agent(model, [explode], root)

    result = agent.invoke(
        {"messages": [HumanMessage(content="try it")]},
        config={"configurable": {"thread_id": new_thread_id()}},
    )

    tool_messages = [message for message in result["messages"] if message.type == "tool"]
    assert tool_messages and "boom" in tool_messages[0].content
    assert result["messages"][-1].content == "recovered"


def test_agent_has_checkpointer(root):
    model = ScriptedToolModel(responses=[AIMessage(content="ok")], seen_message_counts=[])
    agent = build_agent(model, build_tools(root, confirm=lambda _: False), root, InMemorySaver())

    assert agent.checkpointer is not None
