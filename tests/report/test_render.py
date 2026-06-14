import json

from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
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
