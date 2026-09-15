import json

from psyteardown.experience.scaffold import (
    DesignCriterionInput,
    InitialDesignRequest,
    generate_complete_design,
    generate_initial_design_batch,
    render_initial_design_batch,
    render_initial_design_json,
)


def request() -> InitialDesignRequest:
    return InitialDesignRequest(
        brief_id="brief-entrypoint",
        product_category="桌面 AI 专注助手",
        goal="在深度工作中提供低打扰、可撤销的情境化介入",
        target_segment="需要长时间专注的知识工作者",
        context="安静办公室中的深度工作",
        criteria=[
            DesignCriterionInput(
                criterion_id="control",
                name="控制感",
                operational_definition="用户可以明确接受、拒绝、延后或纠正一次介入",
                desired_direction="higher",
                priority=1,
            ),
            DesignCriterionInput(
                criterion_id="low_interruption",
                name="低打扰",
                operational_definition="routine 事件不会无界地争夺注意力",
                desired_direction="higher",
                priority=2,
            ),
        ],
        required_capabilities=["local policy gate", "bounded recovery"],
        design_language=["quiet physical presence", "clear state transitions"],
        prohibited_experiences=["公开播放私人内容"],
        hard_constraints=["必须有物理取消路径"],
    )


def test_high_level_entrypoint_returns_five_complete_candidates():
    batch = generate_initial_design_batch(request())
    assert batch.brief.status == "frozen"
    assert len(batch.candidates) == 5
    assert all(candidate.status == "input_valid" for candidate in batch.candidates)
    assert all(candidate.design is not None for candidate in batch.candidates)
    assert all(len(candidate.design.components) >= 3 for candidate in batch.candidates)
    assert all(candidate.design.problem_statement for candidate in batch.candidates)
    assert all(candidate.design.functional_architecture for candidate in batch.candidates)
    assert all(candidate.design.verification_plan for candidate in batch.candidates)
    assert "avoid: 公开播放私人内容" in batch.candidates[0].design.design_principles
    assert "constraint note: 必须有物理取消路径" in batch.candidates[0].design.design_principles


def test_high_level_entrypoint_supports_explicit_variant_and_exports():
    design = generate_complete_design(request(), variant=2)
    assert design.candidate_id == "scaffold-r1-3"
    assert design.design is not None
    assert design.design.shape.form_factor

    batch = generate_initial_design_batch(request())
    markdown = render_initial_design_batch(batch)
    assert markdown.count("## Variant ") == 5
    assert "桌面 AI 专注助手" in markdown
    payload = json.loads(render_initial_design_json(batch))
    assert len(payload["candidates"]) == 5
    assert payload["candidates"][0]["design"]["components"]
