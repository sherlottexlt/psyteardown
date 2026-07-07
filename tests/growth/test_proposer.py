from psyteardown.growth.models import FrameworkCandidate, CandidateList
from psyteardown.growth.proposer import propose_frameworks
from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.memory.models import Case
from psyteardown.pipeline.schemas import (
    ProductProfile, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _case(cid, one_liner):
    result = TeardownResult(
        product=ProductProfile(name=cid, product_type="App", one_liner=one_liner,
                               features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[Mapping(feature="f", framework_id="hook-model", principle_id="trigger",
                          rationale="r", evidence="每日推送", confidence=0.4)],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )
    c = Case.from_result(result, description=one_liner, created_at="t")
    c.case_id = cid          # Case 非 frozen,直接设定以便测试引用确定的 id
    return c


def _existing():
    return [Framework(id="hook-model", name="上瘾模型", category="habit",
                      summary="触发-行动-奖励-投入", tags=["习惯"],
                      principles=[Principle(id="trigger", name="触发", description="d")],
                      references=["r"])]


def _candidate(fid, support):
    fw = Framework(id=fid, name="新框架", category="emotion", summary="新机制",
                   tags=["x"],
                   principles=[Principle(id="p", name="p", description="d", look_for=["a"])],
                   references=["r"])
    return FrameworkCandidate(framework=fw, rationale="盖不住", source_case_ids=support)


def test_empty_cases_returns_empty():
    provider = FakeProvider()  # 空队列;空案例应直接返回,不调 LLM
    assert propose_frameworks(provider, [], _existing(), created_at="t") == []
    assert provider.calls == []


def test_existing_frameworks_in_prompt_and_stamps_created_at():
    cases = [_case(str(i), f"产品{i}") for i in range(3)]
    cand = _candidate("new-fw", support=["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CandidateList(candidates=[cand])])
    out = propose_frameworks(provider, cases, _existing(), created_at="2026-06-14", min_support=3)
    assert len(out) == 1
    assert out[0].created_at == "2026-06-14"
    assert "hook-model" in provider.calls[0]["prompt"]   # 现有框架进了 prompt


def test_filters_below_min_support():
    cases = [_case(str(i), f"产品{i}") for i in range(3)]
    weak = _candidate("weak", support=["0"])              # 仅 1 个支撑
    strong = _candidate("strong", support=["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CandidateList(candidates=[weak, strong])])
    out = propose_frameworks(provider, cases, _existing(), created_at="t", min_support=3)
    assert [c.framework.id for c in out] == ["strong"]


def test_drops_hallucinated_case_ids():
    cases = [_case(str(i), f"产品{i}") for i in range(3)]
    cand = _candidate("x", support=["0", "1", "999"])     # 999 不存在
    provider = FakeProvider(structured_responses=[CandidateList(candidates=[cand])])
    out = propose_frameworks(provider, cases, _existing(), created_at="t", min_support=3)
    assert out == []                                       # 有效支撑仅 2 个 < 3
