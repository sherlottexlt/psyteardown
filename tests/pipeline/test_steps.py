from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider, LLMError
from psyteardown.pipeline import steps
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _fw(id_, tags):
    return Framework(
        id=id_, name=id_, category="motivation", summary="s", tags=tags,
        principles=[Principle(id="p", name="p", description="d", look_for=["x"])],
        references=["r"],
    )


def _profile():
    return ProductProfile(
        name="Demo", product_type="App", one_liner="x",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=["推送"],
    )


def test_step1_parse_product():
    provider = FakeProvider(structured_responses=[_profile()])
    profile = steps.parse_product(provider, "一些产品描述文本")
    assert profile.name == "Demo"
    assert "一些产品描述文本" in provider.calls[0]["prompt"]


def test_step2_retrieve_is_pure_no_llm():
    provider = FakeProvider()  # 空队列;若 step2 调 LLM 会抛错
    library = [_fw("habit", ["习惯养成", "推送"]), _fw("pricing", ["定价"])]
    frameworks = steps.retrieve(_profile(), library, max_n=1)
    assert frameworks[0].id == "habit"
    assert provider.calls == []  # 确认未触 LLM


def test_step3_maps_each_feature():
    mapping = Mapping(
        feature="签到", framework_id="habit", principle_id="p",
        rationale="r", evidence="e", confidence=0.9,
    )
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[mapping]),
        MappingList(mappings=[]),  # 触点「推送」无映射
    ])
    mappings = steps.map_features(provider, _profile(), [_fw("habit", ["习惯养成"])])
    assert mappings[0].feature == "签到"


def test_step3_failure_marks_error_and_continues():
    # 队列耗尽 → 每个目标映射失败,应返回带 error 的占位 mapping 而非崩溃
    provider = FakeProvider(structured_responses=[])
    mappings = steps.map_features(provider, _profile(), [_fw("habit", ["习惯养成"])])
    assert len(mappings) == 2  # 1 feature + 1 touchpoint
    assert all(m.error is not None for m in mappings)


def test_step4_assess_experience():
    assessment = ExperienceAssessment(
        strengths=["强"], friction_points=["阻"], ethics_warnings=["伦"], opportunities=["机"],
    )
    provider = FakeProvider(structured_responses=[assessment])
    out = steps.assess_experience(provider, _profile(), [])
    assert out.strengths == ["强"]


def test_step5_synthesize():
    provider = FakeProvider(structured_responses=[Synthesis(executive_summary="总结文本")])
    summary = steps.synthesize(provider, _profile(), [], ExperienceAssessment())
    assert summary == "总结文本"
