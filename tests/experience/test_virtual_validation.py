import json
from pathlib import Path

from typer.testing import CliRunner

from psyteardown.cli import app
from psyteardown.experience import (
    VirtualValidationInput,
    run_virtual_validation,
)


runner = CliRunner()


def _input() -> VirtualValidationInput:
    return VirtualValidationInput.model_validate_json(
        Path("examples/transit-anchor-round2-virtual-validation-input.json").read_text(encoding="utf-8")
    )


def test_virtual_validation_is_deterministic_and_never_evidence():
    first = run_virtual_validation(_input())
    second = run_virtual_validation(_input())

    assert first.model_dump() == second.model_dump()
    assert first.evidence_level == "none"
    assert first.evidence_eligible is False
    assert first.decision == "proceed_to_physical_prototype"
    assert any(item.status == "not_modelled" for item in first.results)
    assert all(item.evidence_eligible is False for item in first.results)


def test_virtual_validation_cli_supports_json_and_markdown(tmp_path):
    source = Path("examples/transit-anchor-round2-virtual-validation-input.json")
    json_output = tmp_path / "virtual.json"
    result = runner.invoke(app, ["virtual-validate", "--input", str(source), "--format", "json", "--out", str(json_output)])
    assert result.exit_code == 0, result.output
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["evidence_level"] == "none"
    assert payload["evidence_eligible"] is False
    assert payload["results"]

    markdown_output = tmp_path / "virtual.md"
    result = runner.invoke(app, ["virtual-validate", "--input", str(source), "--out", str(markdown_output)])
    assert result.exit_code == 0, result.output
    markdown = markdown_output.read_text(encoding="utf-8")
    assert "virtual engineering preflight" in markdown
    assert "not a physical prototype run" in markdown
    assert "Evidence level:** `none`" in markdown
