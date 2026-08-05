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
        "--out", str(out), "--provider", "fake", "--no-save",
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


def test_build_provider_deepseek(monkeypatch):
    from psyteardown.cli import _build_provider
    from psyteardown.llm.deepseek import DeepSeekProvider

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    assert isinstance(_build_provider("deepseek"), DeepSeekProvider)


def test_llm_provider_default_from_env(tmp_path, monkeypatch):
    """PSYTEARDOWN_LLM=deepseek → 不传 --provider 也走 DeepSeek。"""
    import psyteardown.cli as cli

    seen: list[str] = []
    real = cli._build_provider

    def spy(name: str):
        seen.append(name)
        return real("fake")            # 测试中不真连 DeepSeek

    monkeypatch.setenv("PSYTEARDOWN_LLM", "deepseek")
    monkeypatch.setattr(cli, "_build_provider", spy)
    src = tmp_path / "p.txt"
    src.write_text("一个每日签到App。", encoding="utf-8")
    r = runner.invoke(app, ["analyze", "--input", str(src), "--no-save",
                            "--out", str(tmp_path / "r.md"),
                            "--embed-provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert seen == ["deepseek"]


def test_analyze_out_creates_parent_dirs(tmp_path):
    src = tmp_path / "p.txt"
    src.write_text("一个每日签到App。", encoding="utf-8")
    out = tmp_path / "deep" / "nested" / "r.md"      # 父目录不存在
    r = runner.invoke(app, ["analyze", "--input", str(src), "--no-save",
                            "--out", str(out), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert out.exists()


def test_analyze_max_n_flag_reaches_pipeline(tmp_path, monkeypatch):
    """CLI --max-n 必须落到 run_teardown;flag 只在最外层新增,内层 v7 已透传。"""
    from psyteardown.mcp_server import tools

    seen = {}
    real = tools.run_teardown
    monkeypatch.setattr(tools, "run_teardown",
                        lambda *a, **k: (seen.update(k), real(*a, **k))[1])

    src = tmp_path / "product.txt"
    src.write_text("一个每日签到App,有推送提醒。", encoding="utf-8")
    result = runner.invoke(app, [
        "analyze", "-i", str(src), "-o", str(tmp_path / "r.md"),
        "--store", str(tmp_path / "cases.db"),
        "--provider", "fake", "--embed-provider", "fake",
        "--max-n", "12", "--min-n", "1",
    ])
    assert result.exit_code == 0, result.stdout
    assert seen["max_n"] == 12
    assert seen["min_n"] == 1
