from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()


class _FakeLLM:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        return self._payload

    def complete(self, prompt, *, system=None):
        return ""


def _seed_cases(tmp_path, n=3):
    db = tmp_path / "cases.db"
    for i in range(n):
        src = tmp_path / f"p{i}.txt"
        src.write_text(f"社交产品{i}:动态推送点赞 {i}", encoding="utf-8")
        r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                                "--out", str(tmp_path / f"r{i}.md"),
                                "--provider", "fake", "--embed-provider", "fake"])
        assert r.exit_code == 0, r.stdout
    return db


def test_strategize_list_approve_then_analyze(tmp_path, monkeypatch):
    db = _seed_cases(tmp_path)
    import psyteardown.cli as cli
    from psyteardown.strategy.models import StrategyCard, CardList
    from psyteardown.memory.store import CaseStore

    ids = [c.case_id for c, _ in CaseStore(db).all()]
    card = StrategyCard(id="prefer-social-proof", rule="社交产品优先社交证明框架",
                        rationale="社交案例反复高置信", target_step="mapping",
                        applies_to=["社交"], source_case_ids=ids)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CardList(cards=[card])))

    r = runner.invoke(app, ["strategize", "--store", str(db), "--min-support", "1",
                            "--provider", "fake"])
    assert r.exit_code == 0, r.stdout

    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "prefer-social-proof" in r.stdout

    r = runner.invoke(app, ["strategies", "approve", "prefer-social-proof", "--store", str(db)])
    assert r.exit_code == 0, r.stdout

    # 还原 _build_provider,让后续 analyze 用真正的 analyze fake 队列(而非 CardList fake)
    monkeypatch.undo()

    # analyze --use-strategies 应把该策略注入 step3(fake LLM 不校验内容,仅确认跑通)
    src = tmp_path / "q.txt"
    src.write_text("社交产品:群组动态与点赞", encoding="utf-8")
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--use-strategies", "--out", str(tmp_path / "q.md"),
                            "--provider", "fake", "--embed-provider", "fake"])
    assert r.exit_code == 0, r.stdout


def test_reflect_creates_candidate(tmp_path, monkeypatch):
    db = tmp_path / "cases.db"      # reflect 不需要案例
    import psyteardown.cli as cli
    from psyteardown.strategy.models import StrategyCard, CardList

    card = StrategyCard(id="no-dark-unsub", rule="订阅产品查退订暗黑模式",
                        rationale="复盘", target_step="assessment", applies_to=["订阅"])
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CardList(cards=[card])))
    r = runner.invoke(app, ["reflect", "--note", "订阅产品记得查退订暗黑模式",
                            "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "no-dark-unsub" in r.stdout


def test_strategies_reject(tmp_path, monkeypatch):
    db = tmp_path / "cases.db"
    import psyteardown.cli as cli
    from psyteardown.strategy.models import StrategyCard, CardList

    card = StrategyCard(id="temp", rule="r", rationale="r", target_step="mapping")
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CardList(cards=[card])))
    runner.invoke(app, ["reflect", "--note", "note", "--store", str(db), "--provider", "fake"])
    r = runner.invoke(app, ["strategies", "reject", "temp", "--store", str(db)])
    assert r.exit_code == 0
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "temp" not in r.stdout
