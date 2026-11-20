import pytest

from baby_code_agent.settings import (
    API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    ConfigError,
    load_settings,
)


def test_missing_key_names_the_variable():
    with pytest.raises(ConfigError) as excinfo:
        load_settings({})

    message = str(excinfo.value)
    assert API_KEY_ENV in message
    assert "super-secret" not in message


def test_blank_key_is_missing():
    with pytest.raises(ConfigError):
        load_settings({API_KEY_ENV: "   "})


def test_defaults():
    settings = load_settings({API_KEY_ENV: "key-value"})

    assert settings.base_url == DEFAULT_BASE_URL
    assert settings.model == DEFAULT_MODEL
    assert settings.api_key == "key-value"


def test_model_and_base_url_overrides():
    settings = load_settings(
        {
            API_KEY_ENV: "key-value",
            "OPENCODEGO_MODEL": "another-model",
            "OPENCODEGO_BASE_URL": "https://example.test/v1",
        }
    )

    assert settings.model == "another-model"
    assert settings.base_url == "https://example.test/v1"
