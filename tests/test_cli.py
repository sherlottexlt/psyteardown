import json

from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()


def test_kb_list_shows_frameworks():
    result = runner.invoke(app, ["kb", "list"])
    assert result.exit_code == 0
    assert "fogg-behavior-model" in result.stdout


def test_kb_show_one_framework():
    result = runner.invoke(app, ["kb", "show", "flow"])
    assert result.exit_code == 0
    assert "心流" in result.stdout


def test_kb_show_unknown_errors():
    result = runner.invoke(app, ["kb", "show", "nope"])
    assert result.exit_code != 0


def test_analyze_with_fake_provider_writes_json(tmp_path):
    src = tmp_path / "product.txt"
    src.write_text("一个每日签到App,有推送提醒。", encoding="utf-8")
    out = tmp_path / "result.json"
    result = runner.invoke(app, [
        "analyze", "--input", str(src), "--format", "json",
        "--out", str(out), "--provider", "fake",
    ])
    assert result.exit_code == 0, result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "executive_summary" in data


def test_analyze_empty_input_errors(tmp_path):
    src = tmp_path / "empty.txt"
    src.write_text("   ", encoding="utf-8")
    result = runner.invoke(app, [
        "analyze", "--input", str(src), "--provider", "fake",
    ])
    assert result.exit_code != 0
