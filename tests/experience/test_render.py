import json

from psyteardown.experience.models import DesignBrief, DivergenceMatrix, ExperienceCriterion, RevisionMeta
from psyteardown.experience.providers import ScaffoldDesignGenerator
from psyteardown.experience.render import (
    render_candidate_json,
    render_candidate_markdown,
    render_design_json,
    render_design_markdown,
)
from psyteardown.experience.rules import build_candidate


def brief() -> DesignBrief:
    return DesignBrief(
        brief_id="brief-render",
        revision_id="brief-render.r1",
        meta=RevisionMeta(revision=1, created_by="test", reason="draft"),
        goal="low interruption",
        target_segment="knowledge workers",
        researchability_confirmed=True,
        context="focused work",
        scenario_ids=("scenario-1",),
        criteria=(ExperienceCriterion(criterion_id="control", name="Control", operational_definition="can stop", desired_direction="higher", priority=1),),
        divergence_matrix=DivergenceMatrix(variable_ids=("feedback.modality",), strategy_directions=("quiet", "visible", "privacy_first")),
    )


def test_design_markdown_contains_complete_design_sections_and_unknowns():
    design = ScaffoldDesignGenerator().generate(brief(), count=1)[0].design
    assert design is not None
    markdown = render_design_markdown(design)
    for heading in ("形态与交互表面", "组件", "材料与表面假设", "交互流程", "反馈行为", "隐私与控制", "供电与连接", "制造假设", "明确未知与待验证"):
        assert heading in markdown
    assert "Main body" in markdown
    assert "exact dimensions" in markdown
    assert "不代表 CAD、工程或用户结果验证" in markdown


def test_design_json_is_roundtrippable():
    design = ScaffoldDesignGenerator().generate(brief(), count=1)[0].design
    assert design is not None
    payload = json.loads(render_design_json(design))
    assert payload["components"]
    assert payload["shape"]["form_factor"]


def test_candidate_markdown_and_json_keep_candidate_identity():
    draft = ScaffoldDesignGenerator().generate(brief(), count=1)[0]
    candidate = build_candidate(draft, brief(), actor="test", reason="import")
    markdown = render_candidate_markdown(candidate)
    assert candidate.candidate_id in markdown
    assert candidate.candidate_revision_id in markdown
    payload = json.loads(render_candidate_json(candidate))
    assert payload["candidate_id"] == candidate.candidate_id
    assert payload["design"]["design_id"] == draft.design.design_id
