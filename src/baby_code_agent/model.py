"""Build the chat model used by the agent."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from baby_code_agent.settings import Settings


def create_chat_model(settings: Settings) -> ChatOpenAI:
    """Create an OpenAI-compatible chat model pointed at the configured endpoint."""
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        temperature=0,
        timeout=120,
        max_retries=2,
    )
