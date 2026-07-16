import json

from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, ExperienceAssessment, TeardownResult,
    TeardownMeta, FrameworkCitation,
)
from psyteardown.report.render import render_markdown, render_json


def _result():
    return TeardownResult(
        product=ProductProfile(
            name="Demo", product_type="App", one_liner="每日签到App",
            features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
            touchpoints=["推送"],
        ),
        frameworks_used=["hook-model"],
        citations=[
            FrameworkCitation(id="hook-model", name="上瘾模型(Hook)",
                              references=["Eyal, N. (2014). Hooked."]),
        ],
        mappings=[
            Mapping(feature="签到", framework_id="hook-model", principle_id="trigger",
                    rationale="形成回访习惯", evidence="每日推送提醒", confidence=0.9),
            Mapping(feature="低置信项", framework_id="flow", principle_id="clear_goals",
                    rationale="r", evidence="e", confidence=0.3),
            Mapping(feature="坏项", framework_id="", principle_id="", rationale="",
                    evidence="", confidence=0.0, error="解析失败"),
        ],
        assessment=ExperienceAssessment(
            strengths=["回访强"], friction_points=["步骤多"],
            ethics_warnings=["可能滥用推送"], opportunities=["增加自定义"],
        ),
        executive_summary="这是一个依赖习惯回路的签到产品。",
        meta=TeardownMeta(model="claude-opus-4-8", generated_at="2026-06-13"),
    )


def test_render_json_is_valid_and_complete():
    data = json.loads(render_json(_result()))
    assert data["executive_summary"]
    assert data["frameworks_used"] == ["hook-model"]


def test_markdown_appendix_includes_references():
    md = render_markdown(_result())
    assert "Eyal, N. (2014). Hooked." in md  # 出处必须出现在附录


def test_markdown_has_all_sections():
    md = render_markdown(_result())
    for heading in ["概述", "产品画像", "逐功能心理学拆解", "整体体验评估",
                    "伦理", "机会点", "附录"]:
        assert heading in md


def test_markdown_flags_low_confidence():
    md = render_markdown(_result())
    assert "⚠️" in md  # 低置信度(0.3)应被标注


def test_markdown_notes_failed_mapping():
    md = render_markdown(_result())
    assert "解析失败" in md  # 失败的映射如实呈现,不假装成功


import json as _json

from psyteardown.review.models import CaseReview


def _result_for_review():
    from psyteardown.pipeline.schemas import (
        ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
    )
    return TeardownResult(
        product=ProductProfile(name="Demo", product_type="App", one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=[], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def test_markdown_renders_review_section():
    review = CaseReview(score=0.65, strengths=["框架选得准"],
                        weaknesses=["证据薄弱"], suggestions=["补充数据"])
    md = render_markdown(_result_for_review(), review=review)
    assert "## 拆解自评" in md
    assert "0.65" in md
    assert "框架选得准" in md
    assert "证据薄弱" in md
    assert "补充数据" in md


def test_markdown_without_review_unchanged():
    result = _result_for_review()
    assert render_markdown(result) == render_markdown(result, review=None)
    assert "拆解自评" not in render_markdown(result)


def test_json_with_review_adds_top_level_key():
    review = CaseReview(score=0.65)
    payload = _json.loads(render_json(_result_for_review(), review=review))
    assert payload["review"]["score"] == 0.65


def test_json_without_review_no_key():
    payload = _json.loads(render_json(_result_for_review()))
    assert "review" not in payload
