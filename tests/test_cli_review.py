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


class _FakeLLM:
    """按队列返回预置结构化结果(monkeypatch _build_provider 用)。"""

    def __init__(self, payloads):
        self._p = list(payloads)
        self.calls = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        return self._p.pop(0)

    def complete(self, prompt, *, system=None):
        return ""


def _seed_case(tmp_path):
    """无自评落盘一个案例,返回 (db, case_id)。"""
    r, db, _ = _analyze(tmp_path)
    assert r.exit_code == 0, r.stdout
    cases = [c for c, _ in CaseStore(db).all()]
    return db, cases[0].case_id


def test_review_backfills_and_overwrites(tmp_path, monkeypatch):
    import psyteardown.cli as cli
    from psyteardown.review.models import CaseReview

    db, cid = _seed_case(tmp_path)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM([CaseReview(score=0.4)]))
    r = runner.invoke(app, ["review", cid, "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert CaseStore(db).get(cid).review.score == 0.4

    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM([CaseReview(score=0.9)]))
    r = runner.invoke(app, ["review", cid, "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert CaseStore(db).get(cid).review.score == 0.9      # 覆盖旧自评


def test_review_missing_case_errors(tmp_path):
    db = tmp_path / "cases.db"
    r = runner.invoke(app, ["review", "nope", "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 1
    assert "案例不存在" in (r.stdout + str(r.stderr or ""))


def test_reanalyze_without_self_review_warns_on_losing_old_review(tmp_path, monkeypatch):
    """同描述重跑 analyze 不开自评 → 覆盖丢旧自评前给出警告。"""
    import psyteardown.cli as cli
    from psyteardown.review.models import CaseReview

    db, cid = _seed_case(tmp_path)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM([CaseReview(score=0.4)]))
    r = runner.invoke(app, ["review", cid, "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    monkeypatch.undo()

    r, db, _ = _analyze(tmp_path)          # 同描述 → 同 case_id,未开自评
    assert r.exit_code == 0, r.stdout
    assert "旧自评将被覆盖丢弃" in (r.stdout + str(r.stderr or ""))
    assert CaseStore(db).get(cid).review is None


def test_review_to_reflect_creates_strategy_candidate(tmp_path, monkeypatch):
    import psyteardown.cli as cli
    from psyteardown.review.models import CaseReview
    from psyteardown.strategy.models import StrategyCard, CardList

    db, cid = _seed_case(tmp_path)
    card = StrategyCard(id="check-retention-first", rule="定置信前先核对留存数据",
                        rationale="自评建议", target_step="mapping")
    monkeypatch.setattr(cli, "_build_provider", lambda name: _FakeLLM([
        CaseReview(score=0.6, suggestions=["先核对留存数据再定置信"]),
        CardList(cards=[card]),
    ]))
    r = runner.invoke(app, ["review", cid, "--store", str(db),
                            "--to-reflect", "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "check-retention-first" in r.stdout


def test_review_to_reflect_empty_suggestions_skips(tmp_path, monkeypatch):
    import psyteardown.cli as cli
    from psyteardown.review.models import CaseReview

    db, cid = _seed_case(tmp_path)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM([CaseReview(score=0.9)]))
    r = runner.invoke(app, ["review", cid, "--store", str(db),
                            "--to-reflect", "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert "跳过" in r.stdout
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "无候选策略卡" in r.stdout
