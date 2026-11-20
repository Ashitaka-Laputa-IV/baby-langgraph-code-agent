import pytest

from baby_code_agent.cli import main


def test_help_exits_zero_without_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENCODEGOAPIKEY", raising=False)

    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])

    assert excinfo.value.code == 0
    assert "baby-code-agent" in capsys.readouterr().out


def test_missing_key_exits_non_zero(monkeypatch, capsys):
    monkeypatch.delenv("OPENCODEGOAPIKEY", raising=False)

    assert main([]) == 2
    assert "OPENCODEGOAPIKEY" in capsys.readouterr().err
