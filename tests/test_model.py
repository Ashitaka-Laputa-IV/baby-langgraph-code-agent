from baby_code_agent.model import create_chat_model
from baby_code_agent.settings import Settings


def test_factory_builds_configured_model():
    settings = Settings(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
    )

    model = create_chat_model(settings)

    assert model.model_name == "test-model"
    assert model.openai_api_base == "https://example.test/v1"
    assert model.temperature == 0
    assert model.default_headers["x-opencode-session"].startswith("ses_")


def test_factory_accepts_a_fixed_session_id():
    model = create_chat_model(Settings(api_key="test-key"), session_id="ses_test")

    assert model.default_headers["x-opencode-session"] == "ses_test"
