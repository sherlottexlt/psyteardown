from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()


class _FakeLLM:
    """只实现 structured_complete,返回预置结构;够 learn 用。"""
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        return self._payload

    def complete(self, prompt, *, system=None):
        return ""


def _seed_cases(tmp_path, n=3):
    """用 analyze(fake)在临时库里落 n 个案例。"""
    db = tmp_path / "cases.db"
    for i in range(n):
        src = tmp_path / f"p{i}.txt"
        src.write_text(f"产品{i}:每日签到推送提醒习惯养成 {i}", encoding="utf-8")
        r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                                "--out", str(tmp_path / f"r{i}.md"),
                                "--provider", "fake", "--embed-provider", "fake"])
        assert r.exit_code == 0, r.stdout
    return db


def test_learn_then_candidates_flow(tmp_path, monkeypatch):
    db = _seed_cases(tmp_path)

    import psyteardown.cli as cli
    from psyteardown.growth.models import FrameworkCandidate, CandidateList
    from psyteardown.kb.models import Framework, Principle
    from psyteardown.memory.store import CaseStore

    ids = [c.case_id for c, _ in CaseStore(db).all()]
    cand = FrameworkCandidate(
        framework=Framework(id="novelty-loop", name="新奇回路", category="emotion",
                            summary="用不可预期的新奇刺激维持回访", tags=["新奇"],
                            principles=[Principle(id="p", name="p", description="d", look_for=["随机"])],
                            references=["r"]),
        rationale="现有框架未覆盖新奇驱动", source_case_ids=ids)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CandidateList(candidates=[cand])))

    # learn
    r = runner.invoke(app, ["learn", "--store", str(db), "--min-support", "1",
                            "--provider", "fake", "--embed-provider", "fake"])
    assert r.exit_code == 0, r.stdout

    # list
    r = runner.invoke(app, ["candidates", "list", "--store", str(db)])
    assert "novelty-loop" in r.stdout

    # approve → 之后 kb list 应包含它
    r = runner.invoke(app, ["candidates", "approve", "novelty-loop", "--store", str(db)])
    assert r.exit_code == 0, r.stdout
    r = runner.invoke(app, ["kb", "list", "--store", str(db)])
    assert "novelty-loop" in r.stdout
    # kb show 也应能看到已批准的习得框架(与 list/analyze 一致)
    r = runner.invoke(app, ["kb", "show", "novelty-loop", "--store", str(db)])
    assert r.exit_code == 0, r.stdout
    assert "新奇回路" in r.stdout


def test_candidates_reject(tmp_path, monkeypatch):
    db = _seed_cases(tmp_path, n=1)
    import psyteardown.cli as cli
    from psyteardown.growth.models import FrameworkCandidate, CandidateList
    from psyteardown.kb.models import Framework, Principle
    from psyteardown.memory.store import CaseStore

    ids = [c.case_id for c, _ in CaseStore(db).all()]
    cand = FrameworkCandidate(
        framework=Framework(id="temp-fw", name="临时", category="x", summary="s",
                            tags=["t"], principles=[Principle(id="p", name="p", description="d")],
                            references=["r"]),
        rationale="r", source_case_ids=ids)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CandidateList(candidates=[cand])))
    runner.invoke(app, ["learn", "--store", str(db), "--min-support", "1",
                        "--provider", "fake", "--embed-provider", "fake"])
    r = runner.invoke(app, ["candidates", "reject", "temp-fw", "--store", str(db)])
    assert r.exit_code == 0
    r = runner.invoke(app, ["candidates", "list", "--store", str(db)])
    assert "temp-fw" not in r.stdout
