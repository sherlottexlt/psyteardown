from psyteardown.strategy.models import StrategyCard, CardList
from psyteardown.strategy.proposer import propose_strategies
from psyteardown.llm.base import FakeProvider
from psyteardown.memory.models import Case
from psyteardown.pipeline.schemas import (
    ProductProfile, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _case(cid, ptype="社交App"):
    result = TeardownResult(
        product=ProductProfile(name=cid, product_type=ptype, one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[Mapping(feature="f", framework_id="hook-model", principle_id="trigger",
                          rationale="r", evidence="e", confidence=0.9)],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )
    c = Case.from_result(result, description=f"{cid} {ptype}", created_at="t")
    c.case_id = cid
    return c


def _card(id_, support, step="mapping"):
    return StrategyCard(id=id_, rule="r", rationale="why", target_step=step,
                        source_case_ids=support)


def test_empty_cases_returns_empty():
    provider = FakeProvider()
    assert propose_strategies(provider, [], created_at="t") == []
    assert provider.calls == []


def test_stamps_created_at_and_summary_in_prompt():
    cases = [_case(str(i)) for i in range(3)]
    card = _card("prefer-x", ["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = propose_strategies(provider, cases, created_at="2026-07-08", min_support=3)
    assert len(out) == 1
    assert out[0].created_at == "2026-07-08"
    assert "hook-model" in provider.calls[0]["prompt"]   # 统计摘要进 prompt


def test_filters_below_min_support():
    cases = [_case(str(i)) for i in range(3)]
    weak = _card("weak", ["0"])
    strong = _card("strong", ["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CardList(cards=[weak, strong])])
    out = propose_strategies(provider, cases, created_at="t", min_support=3)
    assert [c.id for c in out] == ["strong"]


def test_drops_hallucinated_case_ids():
    cases = [_case(str(i)) for i in range(3)]
    card = _card("x", ["0", "1", "999"])
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = propose_strategies(provider, cases, created_at="t", min_support=3)
    assert out == []


def test_drops_invalid_target_step():
    cases = [_case(str(i)) for i in range(3)]
    bad = _card("bad", ["0", "1", "2"], step="synthesis")   # 非法枚举
    provider = FakeProvider(structured_responses=[CardList(cards=[bad])])
    out = propose_strategies(provider, cases, created_at="t", min_support=3)
    assert out == []
