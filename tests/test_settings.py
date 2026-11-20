import pytest

from baby_code_agent.settings import (
    API_KEY_ENV,
    BASE_URL_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    FALLBACK_API_KEY_ENV,
    MODEL_ENV,
    ConfigError,
    load_settings,
)


def test_missing_key_names_the_variable():
    with pytest.raises(ConfigError) as excinfo:
        load_settings({})

    message = str(excinfo.value)
    assert API_KEY_ENV in message


def test_blank_key_is_missing():
    with pytest.raises(ConfigError):
        load_settings({API_KEY_ENV: "   "})


def test_falls_back_to_the_legacy_variable():
    settings = load_settings({FALLBACK_API_KEY_ENV: "fallback-key"})

    assert settings.api_key == "fallback-key"


def test_primary_variable_wins():
    settings = load_settings(
        {API_KEY_ENV: "primary-key", FALLBACK_API_KEY_ENV: "fallback-key"}
    )

    assert settings.api_key == "primary-key"


def test_defaults():
    settings = load_settings({API_KEY_ENV: "key-value"})

    assert settings.base_url == DEFAULT_BASE_URL
    assert settings.model == DEFAULT_MODEL
    assert settings.api_key == "key-value"


def test_model_and_base_url_overrides():
    settings = load_settings(
        {
            API_KEY_ENV: "key-value",
            MODEL_ENV: "another-model",
            BASE_URL_ENV: "https://example.test/v1",
        }
    )

    assert settings.model == "another-model"
    assert settings.base_url == "https://example.test/v1"
