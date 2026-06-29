from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()
FAKE = ["--provider", "fake", "--embed-provider", "fake"]


def _write(tmp_path, text="一个每日签到App,有推送提醒。"):
    p = tmp_path / "product.txt"
    p.write_text(text, encoding="utf-8")
    return p


def test_analyze_saves_case_to_store(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--out", str(tmp_path / "r.md"), *FAKE])
    assert r.exit_code == 0, r.stdout
    stats = runner.invoke(app, ["memory", "stats", "--store", str(db)])
    assert "1" in stats.stdout


def test_no_save_skips_store(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--no-save", "--out", str(tmp_path / "r.md"), *FAKE])
    assert r.exit_code == 0, r.stdout
    stats = runner.invoke(app, ["memory", "stats", "--store", str(db)])
    assert "0" in stats.stdout


def test_similar_finds_saved_case(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                        "--out", str(tmp_path / "r.md"), *FAKE])
    r = runner.invoke(app, ["similar", "--input", str(src), "--store", str(db),
                            "--embed-provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert "样例产品" in r.stdout  # fake LLM provider 产出的产品名


def test_similar_empty_store_message(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "empty.db"
    r = runner.invoke(app, ["similar", "--input", str(src), "--store", str(db),
                            "--embed-provider", "fake"])
    assert r.exit_code == 0
    assert "空" in r.stdout


def test_analyze_survives_embedder_failure(tmp_path, monkeypatch):
    # 记忆是增强:嵌入器不可用(如离线无模型)时,核心拆解仍须产出,案例跳过落盘
    import psyteardown.cli as cli
    from psyteardown.memory.store import CaseStore

    class _Boom:
        @property
        def dim(self):
            raise OSError("offline")

        def embed(self, texts):
            raise OSError("offline: 无法加载模型")

    monkeypatch.setattr(cli, "_build_embed_provider", lambda name: _Boom())
    src = _write(tmp_path)
    out = tmp_path / "r.md"
    db = tmp_path / "cases.db"
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--out", str(out), "--provider", "fake"])  # 默认 save 开
    assert r.exit_code == 0, r.stdout
    assert out.exists()                       # 报告照常产出
    assert CaseStore(db).count() == 0         # 案例未落盘(优雅降级)


def test_use_memory_runs_without_error(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    # 先存一个案例,再带 --use-memory 跑一次
    runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                        "--out", str(tmp_path / "r1.md"), *FAKE])
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--use-memory", "--out", str(tmp_path / "r2.md"), *FAKE])
    assert r.exit_code == 0, r.stdout
