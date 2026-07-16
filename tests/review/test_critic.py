from psyteardown.llm.base import FakeProvider
from psyteardown.review.critic import review_case
from psyteardown.review.models import CaseReview
from psyteardown.pipeline.schemas import (
    ProductProfile, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result():
    return TeardownResult(
        product=ProductProfile(name="Demo", product_type="社交App", one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[
            Mapping(feature="动态", framework_id="hook-model", principle_id="trigger",
                    rationale="r", evidence="点赞红点", confidence=0.9),
            Mapping(feature="签到", framework_id="", principle_id="",
                    rationale="", evidence="", confidence=0.0, error="解析失败"),
        ],
        assessment=ExperienceAssessment(strengths=["上手快"], friction_points=["通知多"]),
        executive_summary="总结",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def test_result_brief_reaches_prompt_and_stamps_meta():
    provider = FakeProvider(structured_responses=[CaseReview(score=0.6)])
    out = review_case(provider, _result(), reviewed_at="2026-07-16", model_label="m1")
    assert out.reviewed_at == "2026-07-16"
    assert out.model == "m1"
    prompt = provider.calls[0]["prompt"]
    assert "hook-model.trigger" in prompt          # 机制映射进 prompt
    assert "点赞红点" in prompt                     # 证据进 prompt
    assert "映射失败" in prompt                     # 失败 mapping 标注进 prompt
    assert "上手快" in prompt                       # 体验评估进 prompt
    assert provider.calls[0]["system"] is not None  # 批判性 system 立场


def test_model_label_defaults_empty():
    provider = FakeProvider(structured_responses=[CaseReview(score=0.5)])
    out = review_case(provider, _result(), reviewed_at="t")
    assert out.model == ""
