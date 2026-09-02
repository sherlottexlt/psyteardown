import json

from psyteardown.pipeline.schemas import (
    Feature,
    ProductProfile,
    Mapping,
    MappingList,
    GroundingStats,
    ExperienceAssessment,
    TeardownResult,
    TeardownMeta,
)


def test_product_profile_roundtrip():
    p = ProductProfile(
        name="Demo", product_type="App", one_liner="一句话",
        features=[Feature(name="f", description="d", user_goal="g")],
        touchpoints=["onboarding"],
    )
    assert p.features[0].name == "f"


def test_mapping_defaults_error_none():
    m = Mapping(
        feature="f", framework_id="fogg-behavior-model", principle_id="trigger",
        rationale="r", evidence="e", confidence=0.8,
    )
    assert m.error is None


def test_teardown_result_serializes_to_json():
    result = TeardownResult(
        product=ProductProfile(
            name="Demo", product_type="App", one_liner="x",
            features=[], touchpoints=[],
        ),
        frameworks_used=["fogg-behavior-model"],
        mappings=[],
        assessment=ExperienceAssessment(
            strengths=[], friction_points=[], ethics_warnings=[], opportunities=[],
        ),
        executive_summary="总结",
        meta=TeardownMeta(model="claude-opus-4-8", generated_at="2026-06-13"),
    )
    js = result.model_dump_json()
    assert "executive_summary" in js


def test_mapping_list_wraps_mappings():
    ml = MappingList(mappings=[])
    assert ml.mappings == []


def test_grounding_stats_defaults():
    stats = GroundingStats()
    assert (stats.kept, stats.dropped, stats.dropped_mappings) == (0, 0, [])


def test_teardown_result_without_grounding_key_still_validates():
    """存量案例 JSON(v8 及以前)没有 grounding 字段,必须照常反序列化。"""
    result = TeardownResult(
        product=ProductProfile(name="D", product_type="t", one_liner="o",
                               features=[], touchpoints=[]),
        frameworks_used=[], mappings=[],
        assessment=ExperienceAssessment(),
        executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )
    payload = json.loads(result.model_dump_json())
    del payload["grounding"]
    old = TeardownResult.model_validate(payload)
    assert old.grounding.kept == 0 and old.grounding.dropped == 0
