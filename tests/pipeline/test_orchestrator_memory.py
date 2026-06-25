from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _library():
    return [Framework(
        id="habit", name="上瘾模型", category="habit", summary="s", tags=["签到"],
        principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
        references=["r"],
    )]


def _queue():
    profile = ProductProfile(
        name="Demo", product_type="App", one_liner="每日签到App",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=[],
    )
    mapping = Mapping(feature="签到", framework_id="habit", principle_id="trigger",
                      rationale="r", evidence="e", confidence=0.9)
    return [
        profile,                                   # step1
        MappingList(mappings=[mapping]),           # step3(只有1个 feature,无 touchpoint)
        ExperienceAssessment(),                    # step4
        Synthesis(executive_summary="总结"),       # step5
    ]


def test_prior_summary_reaches_step3_not_step1():
    provider = FakeProvider(structured_responses=_queue())
    run_teardown(provider, "每日签到App描述", library=_library(),
                 generated_at="2026-06-14", prior_summary="- 旧产品X(y):用过框架 hook-model")
    step1_prompt = provider.calls[0]["prompt"]   # parse_product
    step3_prompt = provider.calls[1]["prompt"]   # map_features
    assert "旧产品X" not in step1_prompt          # step1 不被污染
    assert "旧产品X" in step3_prompt              # step3 收到参考


def test_default_no_prior_summary_matches_v1():
    provider = FakeProvider(structured_responses=_queue())
    result = run_teardown(provider, "desc", library=_library(), generated_at="t")
    assert result.executive_summary == "总结"
    assert "仅供参考" not in provider.calls[1]["prompt"]
