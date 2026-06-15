from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _library():
    return [
        Framework(
            id="habit", name="上瘾模型", category="habit", summary="s",
            tags=["签到", "习惯养成"],
            principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
            references=["r"],
        )
    ]


def test_run_teardown_full_pipeline():
    profile = ProductProfile(
        name="Demo", product_type="App", one_liner="每日签到App",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=["推送"],
    )
    mapping = Mapping(
        feature="签到", framework_id="habit", principle_id="trigger",
        rationale="r", evidence="e", confidence=0.9,
    )
    # 队列顺序:step1 profile → step3 两次(签到 + 推送触点)→ step4 → step5
    provider = FakeProvider(structured_responses=[
        profile,
        MappingList(mappings=[mapping]),
        MappingList(mappings=[]),
        ExperienceAssessment(strengths=["强"], friction_points=[], ethics_warnings=["伦"], opportunities=[]),
        Synthesis(executive_summary="总结"),
    ])

    result = run_teardown(
        provider, "每日签到App描述", library=_library(),
        generated_at="2026-06-13", top_n=5,
    )

    assert result.product.name == "Demo"
    assert result.executive_summary == "总结"
    assert "habit" in result.frameworks_used
    assert result.citations[0].id == "habit"
    assert result.citations[0].references == ["r"]  # 出处从库带入结果
    assert result.assessment.ethics_warnings == ["伦"]
    assert result.meta.model == "fake"
