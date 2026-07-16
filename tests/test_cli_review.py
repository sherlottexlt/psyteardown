from typer.testing import CliRunner

from psyteardown.cli import app
from psyteardown.memory.store import CaseStore

runner = CliRunner()


def _analyze(tmp_path, *extra):
    src = tmp_path / "p.txt"
    src.write_text("社交产品:动态推送点赞", encoding="utf-8")
    db = tmp_path / "cases.db"
    out = tmp_path / "r.md"
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--out", str(out),
                            "--provider", "fake", "--embed-provider", "fake",
                            *extra])
    return r, db, out


def test_analyze_self_review_renders_and_saves(tmp_path):
    r, db, out = _analyze(tmp_path, "--self-review")
    assert r.exit_code == 0, r.stdout
    assert "拆解自评" in out.read_text(encoding="utf-8")
    cases = [c for c, _ in CaseStore(db).all()]
    assert len(cases) == 1
    assert cases[0].review is not None


def test_analyze_self_review_no_save_still_renders(tmp_path):
    r, db, out = _analyze(tmp_path, "--self-review", "--no-save")
    assert r.exit_code == 0, r.stdout
    assert "拆解自评" in out.read_text(encoding="utf-8")
    assert CaseStore(db).count() == 0


def test_analyze_without_flag_no_review(tmp_path):
    r, db, out = _analyze(tmp_path)
    assert r.exit_code == 0, r.stdout
    assert "拆解自评" not in out.read_text(encoding="utf-8")
    cases = [c for c, _ in CaseStore(db).all()]
    assert cases[0].review is None


def test_analyze_self_review_failure_degrades(tmp_path, monkeypatch):
    import psyteardown.cli as cli

    def _boom(*a, **k):
        raise RuntimeError("自评炸了")

    monkeypatch.setattr(cli, "review_case", _boom)
    r, db, out = _analyze(tmp_path, "--self-review")
    assert r.exit_code == 0, r.stdout          # 降级不中断
    text = out.read_text(encoding="utf-8")
    assert "拆解自评" not in text               # 报告无自评节但照常产出
    cases = [c for c, _ in CaseStore(db).all()]
    assert len(cases) == 1                      # 案例照常落盘(review=None)
    assert cases[0].review is None
