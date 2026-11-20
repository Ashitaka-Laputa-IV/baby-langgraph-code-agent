"""Shared deterministic chat models for offline tests."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedToolModel(BaseChatModel):
    """Replay scripted AI messages and accept tool binding without a network call."""

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


class RaisingModel(BaseChatModel):
    """Always fail, for exercising per-turn error recovery."""

    @property
    def _llm_type(self) -> str:
        return "raising-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise RuntimeError("provider unreachable")
