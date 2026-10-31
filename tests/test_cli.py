"""Offline tests for CLI arguments, output, and failure behavior."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.exceptions import ImageValidationError
from src.main import main
from src.models import ContractChangeOutput
from src.pipeline import PipelineResult


@pytest.fixture
def cli_dependencies(monkeypatch):
    settings = SimpleNamespace(
        vision_model="test-vision",
        agent_model="test-agent",
    )
    report = ContractChangeOutput(
        sections_changed=["Cláusula 3"],
        topics_touched=["Condiciones de pago"],
        summary_of_the_change="El importe cambia de USD 500 a USD 650.",
    )
    analyzer = Mock(
        return_value=PipelineResult(
            analysis=report,
            trace_id="test-trace",
        )
    )
    monkeypatch.setattr("src.main.load_settings", lambda: settings)
    monkeypatch.setattr("src.main.analyze_contracts_traced", analyzer)
    return analyzer


def test_success_keeps_stdout_as_json(cli_dependencies, capsys):
    exit_code = main(["original.png", "amendment.png"])

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 0
    assert report["sections_changed"] == ["Cláusula 3"]
    assert "trace_id" not in report
    assert "Trace ID: test-trace" in captured.err


def test_writes_utf8_report(tmp_path, cli_dependencies, capsys):
    output = tmp_path / "report.json"

    exit_code = main(["original.png", "amendment.png", "--output", str(output)])

    captured = capsys.readouterr()
    content = output.read_text(encoding="utf-8")
    assert exit_code == 0
    assert content == captured.out
    assert "Cláusula 3" in content
    assert json.loads(content)["topics_touched"] == ["Condiciones de pago"]


def test_preserves_existing_output_when_analysis_fails(
    tmp_path, cli_dependencies, capsys
):
    output = tmp_path / "report.json"
    output.write_text("Previous report", encoding="utf-8")
    cli_dependencies.side_effect = ImageValidationError("Invalid image")

    exit_code = main(["original.png", "amendment.png", "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "Invalid image" in captured.err
    assert output.read_text(encoding="utf-8") == "Previous report"


def test_handles_output_write_failure(tmp_path, cli_dependencies, monkeypatch, capsys):
    writer = Mock(side_effect=PermissionError("Denied"))
    monkeypatch.setattr("src.main.write_report", writer)

    exit_code = main(
        [
            "original.png",
            "amendment.png",
            "--output",
            str(tmp_path / "report.json"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "unable to read or write" in captured.err


def test_rejects_output_overwriting_input(cli_dependencies, capsys):
    exit_code = main(["original.png", "amendment.png", "--output", "original.png"])

    assert exit_code == 1
    cli_dependencies.assert_not_called()
    assert "must differ" in capsys.readouterr().err


def test_rejects_missing_output_directory(tmp_path, cli_dependencies, capsys):
    output = tmp_path / "missing" / "report.json"

    assert main(["original.png", "amendment.png", "--output", str(output)]) == 1
    cli_dependencies.assert_not_called()
    assert "directory" in capsys.readouterr().err


def test_preserves_paths_with_spaces(cli_dependencies):
    main(["original contract.png", "contract amendment.png"])

    args = cli_dependencies.call_args.args
    assert str(args[0]) == "original contract.png"
    assert str(args[1]) == "contract amendment.png"


def test_verbose_diagnostics_do_not_pollute_json(cli_dependencies, capsys):
    assert main(["original.png", "amendment.png", "--verbose"]) == 0

    captured = capsys.readouterr()
    json.loads(captured.out)
    assert "Vision model: test-vision" in captured.err


def test_help_requires_no_analysis(cli_dependencies, capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--help"])

    assert caught.value.code == 0
    cli_dependencies.assert_not_called()
    assert "--output" in capsys.readouterr().out


def test_missing_arguments_returns_usage_error(cli_dependencies):
    with pytest.raises(SystemExit) as caught:
        main([])

    assert caught.value.code == 2
    cli_dependencies.assert_not_called()
