from pathlib import Path

import pytest

from baby_code_agent.tools import build_tools, format_command_for_display


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("first\nsecond\n", encoding="utf-8")
    return tmp_path


def tool_by_name(tools, name):
    return next(tool for tool in tools if tool.name == name)


def invoke(tools, name, **kwargs):
    return tool_by_name(tools, name).invoke(kwargs)


def test_list_dir_marks_directories(root):
    tools = build_tools(root, confirm=lambda _: False)

    result = invoke(tools, "list_dir")

    assert "src/" in result
    assert "notes.txt" in result


def test_list_dir_empty_directory(root):
    (root / "empty").mkdir()
    tools = build_tools(root, confirm=lambda _: False)

    assert invoke(tools, "list_dir", path="empty") == "(empty directory)"


def test_read_file_numbers_lines(root):
    tools = build_tools(root, confirm=lambda _: False)

    result = invoke(tools, "read_file", path="notes.txt")

    assert "first" in result
    assert "second" in result
    assert result.splitlines()[1].strip().endswith("second")


def test_read_file_missing_returns_error(root):
    tools = build_tools(root, confirm=lambda _: False)

    result = invoke(tools, "read_file", path="missing.txt")

    assert result.startswith("Error:")


def test_read_file_rejects_path_escape(root, tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    tools = build_tools(root, confirm=lambda _: False)

    result = invoke(tools, "read_file", path="../outside.txt")

    assert result.startswith("Error:")
    assert "secret" not in result


def test_write_file_creates_parents_and_overwrites(root):
    tools = build_tools(root, confirm=lambda _: False)

    result = invoke(tools, "write_file", path="pkg/deep/module.py", content="x = 1\n")

    assert not result.startswith("Error:")
    assert (root / "pkg" / "deep" / "module.py").read_text(encoding="utf-8") == "x = 1\n"

    invoke(tools, "write_file", path="pkg/deep/module.py", content="x = 2\n")
    assert (root / "pkg" / "deep" / "module.py").read_text(encoding="utf-8") == "x = 2\n"


def test_write_file_refuses_vcs_metadata(root):
    tools = build_tools(root, confirm=lambda _: False)

    result = invoke(tools, "write_file", path=".git/hooks/pre-commit", content="echo hi")

    assert result.startswith("Error:")
    assert not (root / ".git").exists()


def test_run_shell_denied_does_not_spawn(root):
    calls = []

    def confirm(command):
        calls.append(command)
        return False

    tools = build_tools(root, confirm=confirm)

    result = invoke(tools, "run_shell", command="echo should-not-run")

    assert "denied" in result
    assert calls == ["echo should-not-run"]


def test_run_shell_confirmer_receives_exact_command(root):
    seen = []

    def confirm(command):
        seen.append(command)
        return False

    tools = build_tools(root, confirm=confirm)
    command = "echo one\n&& echo two"

    result = invoke(tools, "run_shell", command=command)

    assert "denied" in result
    assert seen == [command]


def test_run_shell_runs_in_root_and_reports_output(root):
    tools = build_tools(root, confirm=lambda _: True)

    result = invoke(tools, "run_shell", command="echo hello")

    assert "hello" in result


def test_run_shell_reports_non_zero_exit(root):
    tools = build_tools(root, confirm=lambda _: True)

    result = invoke(tools, "run_shell", command="exit 3")

    assert "exit code 3" in result


def test_run_shell_timeout(root, monkeypatch):
    import baby_code_agent.tools as tools_module

    monkeypatch.setattr(tools_module, "SHELL_TIMEOUT_SECONDS", 0.2)
    tools = build_tools(root, confirm=lambda _: True)

    result = invoke(tools, "run_shell", command="ping 127.0.0.1 -n 5 > NUL")

    assert "timed out" in result.lower()


def test_format_command_for_display_escapes_control_characters():
    assert format_command_for_display("echo a\nb\rc\x1bd\x00") == "echo a\\nb\\rc\\ed\\x00"
