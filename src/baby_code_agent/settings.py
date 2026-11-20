"""Environment-backed configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "https://opencode.ai/inference/go/openai/v1"
DEFAULT_MODEL = "deepseek-v4.1-flash"

API_KEY_ENV = "OPENCODEGOAPIKEY"
MODEL_ENV = "OPENCODEGO_MODEL"
BASE_URL_ENV = "OPENCODEGO_BASE_URL"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL


def _read(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Read settings from the process environment, or from ``environ`` in tests."""
    env = os.environ if environ is None else environ

    api_key = _read(env, API_KEY_ENV)
    if not api_key:
        raise ConfigError(
            f"{API_KEY_ENV} is not set. Export your OpenCode Go API key before starting the agent."
        )

    return Settings(
        api_key=api_key,
        base_url=_read(env, BASE_URL_ENV) or DEFAULT_BASE_URL,
        model=_read(env, MODEL_ENV) or DEFAULT_MODEL,
    )
