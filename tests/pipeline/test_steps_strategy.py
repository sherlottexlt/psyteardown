from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline import steps
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.strategy.models import StrategyCard
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _fw():
    return Framework(id="hook-model", name="上瘾模型", category="habit", summary="s",
                     tags=["社交"],
                     principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
                     references=["r"])


def _profile():
    return ProductProfile(name="Demo", product_type="社交App", one_liner="x",
                          features=[Feature(name="动态", description="d", user_goal="g")],
                          touchpoints=[])


def _mapping():
    return Mapping(feature="动态", framework_id="hook-model", principle_id="trigger",
                   rationale="r", evidence="e", confidence=0.9)


def test_map_features_injects_strategy_guidance():
    provider = FakeProvider(structured_responses=[MappingList(mappings=[_mapping()])])
    steps.map_features(provider, _profile(), [_fw()],
                       strategy_guidance="- 社交产品优先社交证明")
    prompt = provider.calls[0]["prompt"]
    assert "社交产品优先社交证明" in prompt
    assert "供参考" in prompt


def test_assess_experience_injects_strategy_guidance():
    provider = FakeProvider(structured_responses=[ExperienceAssessment()])
    steps.assess_experience(provider, _profile(), [_mapping()],
                            strategy_guidance="- 订阅产品重点查退订暗黑模式")
    prompt = provider.calls[0]["prompt"]
    assert "订阅产品重点查退订暗黑模式" in prompt


def _queue():
    return [
        _profile(),                              # step1
        MappingList(mappings=[_mapping()]),      # step3
        ExperienceAssessment(),                  # step4
        Synthesis(executive_summary="总结"),     # step5
    ]


def test_run_teardown_dispatches_cards_to_right_steps():
    cards = [
        StrategyCard(id="m", rule="MAP规则", rationale="r", target_step="mapping"),
        StrategyCard(id="a", rule="ASSESS规则", rationale="r", target_step="assessment"),
    ]
    provider = FakeProvider(structured_responses=_queue())
    run_teardown(provider, "desc", library=[_fw()], generated_at="t", strategy_cards=cards)
    step1 = provider.calls[0]["prompt"]
    step3 = provider.calls[1]["prompt"]
    step4 = provider.calls[2]["prompt"]
    assert "MAP规则" not in step1 and "ASSESS规则" not in step1   # step1 不受影响
    assert "MAP规则" in step3 and "ASSESS规则" not in step3       # mapping 卡进 step3
    assert "ASSESS规则" in step4 and "MAP规则" not in step4       # assessment 卡进 step4


def test_run_teardown_none_matches_prior_behavior():
    provider = FakeProvider(structured_responses=_queue())
    result = run_teardown(provider, "desc", library=[_fw()], generated_at="t")
    assert result.executive_summary == "总结"
    assert "历史归纳的拆解策略" not in provider.calls[1]["prompt"]   # step3 无策略注入
    assert "历史归纳的拆解策略" not in provider.calls[2]["prompt"]   # step4 无策略注入
