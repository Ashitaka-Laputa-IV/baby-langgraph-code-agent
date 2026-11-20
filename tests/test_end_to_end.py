import io
from pathlib import Path

from langchain_core.messages import AIMessage
from rich.console import Console

from baby_code_agent.agent import build_agent
from baby_code_agent.cli import Session, run_repl
from baby_code_agent.model import create_chat_model
from baby_code_agent.settings import API_KEY_ENV, load_settings
from baby_code_agent.tools import build_tools
from tests.fakes import ScriptedToolModel

SENTINEL_KEY = "sentinel-key-value-123"


def feed(lines):
    iterator = iter(lines)
    return lambda: next(iterator)


def test_scripted_session_writes_a_file_and_reports(tmp_path: Path):
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "write_file",
                    "args": {"path": "hello.py", "content": "print('hi')\n"},
                    "id": "c1",
                }
            ],
        ),
        AIMessage(content="Created hello.py"),
    ]
    model = ScriptedToolModel(responses=responses, seen_message_counts=[])
    tools = build_tools(tmp_path, confirm=lambda _: False)
    agent = build_agent(model, tools, tmp_path)
    console = Console(file=io.StringIO(), record=True, force_terminal=False, width=110)

    run_repl(Session(agent=agent), console, "test-model", tmp_path, feed(["create hello.py", "/exit"]))

    assert (tmp_path / "hello.py").read_text(encoding="utf-8") == "print('hi')\n"
    text = console.export_text()
    assert "Wrote" in text
    assert "Created hello.py" in text


def test_api_key_never_appears_in_model_repr():
    settings = load_settings({API_KEY_ENV: SENTINEL_KEY})

    model = create_chat_model(settings)

    assert SENTINEL_KEY not in repr(model)
    assert SENTINEL_KEY not in str(model)


def test_config_error_never_echoes_other_environment_values():
    from baby_code_agent.settings import ConfigError

    try:
        load_settings({"OPENCODEGO_MODEL": SENTINEL_KEY})
    except ConfigError as exc:
        assert SENTINEL_KEY not in str(exc)
    else:  # pragma: no cover - the call must raise
        raise AssertionError("ConfigError was not raised")
