"""Build the chat model used by the agent."""

from __future__ import annotations

import uuid

from langchain_openai import ChatOpenAI

from baby_code_agent.settings import Settings


def new_session_id() -> str:
    return f"ses_{uuid.uuid4().hex}"


def create_chat_model(settings: Settings, session_id: str | None = None) -> ChatOpenAI:
    """Create an OpenAI-compatible chat model pointed at the configured endpoint.

    OpenCode Go requires a stable session id on every request for routing and
    prompt-cache reuse.
    """
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        temperature=0,
        timeout=120,
        max_retries=2,
        default_headers={"x-opencode-session": session_id or new_session_id()},
    )
