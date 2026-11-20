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


def test_factory_does_not_require_network():
    model = create_chat_model(Settings(api_key="test-key"))

    assert model.model_name
