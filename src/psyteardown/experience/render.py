"""Human-readable exports for first-pass structured product designs.

The renderer is intentionally presentation-only.  It does not turn declared
design intent into measured engineering facts or user outcomes; unknowns and
assumptions remain visible in the export.
"""

from __future__ import annotations

from psyteardown.experience.models import DesignCandidate, DesignSpecification, ProgressiveDesignModel


def _items(values: tuple[str, ...] | list[str], *, empty: str = "—") -> list[str]:
    return [f"- {value}" for value in values] if values else [f"- {empty}"]


def render_design_markdown(design: DesignSpecification) -> str:
    """Render one complete ``DesignSpecification`` as Markdown."""

    shape = design.shape
    lines = [
        f"# {design.title}",
        "",
        f"> {design.concept_summary}",
        "",
        "## 目标用户与情境",
        "",
        design.intended_user_and_context,
        "",
        "## 设计摘要",
        "",
        f"- **Problem:** {design.problem_statement}",
        f"- **User value:** {design.user_value}",
        "",
        "## 形态与交互表面",
        "",
        f"- **Form factor:** `{shape.form_factor}`",
        f"- **Silhouette:** {shape.silhouette}",
        f"- **Interaction surface:** {shape.interaction_surface}",
        f"- **Feedback surface:** {shape.feedback_surface}",
        f"- **Grip / mount:** {shape.grip_or_mount}",
        f"- **Body placement:** {shape.body_placement or '未声明'}",
        f"- **Attachment strategy:** {shape.attachment_strategy or '未声明'}",
        f"- **Contact area (declared):** {shape.contact_area or '未声明'}",
        f"- **Mass distribution (declared):** {shape.mass_distribution or '未声明'}",
        f"- **Feedback modality / timing:** {shape.feedback_modality or '未声明'} / {shape.feedback_timing or '未声明'}",
        f"- **Confirmation action:** {shape.confirmation_action or '未声明'}",
        f"- **Motion adaptation:** {shape.motion_adaptation or '未声明'}",
        f"- **Material hint:** {shape.material_hint or '未声明'}",
        f"- **Visible state:** {shape.visible_state}",
        f"- **Dimensions:** {shape.dimensions or '未测量'}",
        "",
        "## 组件",
        "",
    ]
    if design.components:
        for component in design.components:
            lines.extend(
                [
                    f"### {component.name} (`{component.component_id}`)",
                    "",
                    f"- **Role:** {component.role}",
                    f"- **Placement:** {component.placement}",
                    f"- **Material / finish:** {component.material_or_finish or '未声明'}",
                ]
            )
            if component.physical_unknowns:
                lines.append("- **Physical unknowns:** " + "; ".join(component.physical_unknowns))
            lines.append("")
    else:
        lines.extend(_items(()))
        lines.append("")

    sections = (
        ("设计原则", design.design_principles),
        ("功能架构", design.functional_architecture),
        ("感知与情境推断边界", design.sensing_and_inference),
        ("运动模型", design.movement_model),
        ("人体工学策略", design.ergonomic_strategy),
        ("运动自适应行为", design.adaptation_behavior),
        ("材料与表面假设", design.material_and_finish),
        ("交互流程", design.interaction_flow),
        ("反馈行为", design.feedback_behavior),
        ("隐私与控制", design.privacy_and_control),
        ("数据流", design.data_flow),
        ("供电与连接", design.power_and_connectivity),
        ("安全与失败模式", design.safety_and_failure_modes),
        ("制造假设（未验证）", design.manufacturing_assumptions),
        ("验证计划", design.verification_plan),
        ("成功判据", design.success_criteria),
    )
    for heading, values in sections:
        lines.extend([f"## {heading}", "", *_items(values), ""])

    unknowns = tuple(dict.fromkeys(shape.physical_unknowns + design.declared_unknowns))
    lines.extend(
        [
            "## 明确未知与待验证",
            "",
            *_items(unknowns),
            "",
            f"_Design ID: `{design.design_id}` · 本文档只表达结构化设计声明，不代表 CAD、工程或用户结果验证。_",
        ]
    )
    return "\n".join(lines)


def render_candidate_markdown(candidate: DesignCandidate) -> str:
    """Render candidate metadata followed by its complete design document."""

    if candidate.design is None:
        return "\n".join(
            [
                f"# {candidate.name}",
                "",
                f"- Candidate: `{candidate.candidate_id}`",
                f"- Revision: `{candidate.candidate_revision_id}`",
                f"- Status: `{candidate.status}`",
                "",
                candidate.description,
                "",
                "## 未提供完整 DesignSpecification",
                "",
                "该候选仍是结构化输入草案，只有描述、变量和事件数据。",
            ]
        )
    prefix = [
        f"<!-- candidate_id: {candidate.candidate_id} -->",
        f"<!-- candidate_revision_id: {candidate.candidate_revision_id} -->",
        f"<!-- status: {candidate.status} · strategy: {candidate.strategy_direction} -->",
        "",
    ]
    return "\n".join(prefix) + render_design_markdown(candidate.design)


def render_design_json(design: DesignSpecification) -> str:
    """Export a complete design as stable, Unicode-preserving JSON."""

    return design.model_dump_json(indent=2)


def render_candidate_json(candidate: DesignCandidate) -> str:
    """Export the immutable candidate snapshot, including its design."""

    return candidate.model_dump_json(indent=2)


# Small aliases make the rendering API easy to discover from callers that use
# either the domain noun or the output format as the verb.
render_design_spec = render_design_markdown
render_design_spec_json = render_design_json


def render_progressive_model_markdown(model: ProgressiveDesignModel) -> str:
    """Render convergence state without implying missing layers are complete."""

    lines = [
        f"# Progressive Design Model `{model.model_id}`",
        "",
        f"- **Revision:** `{model.revision_id}`",
        f"- **Stage:** `{model.stage}`",
        f"- **Candidate revision:** `{model.candidate_revision_id}`",
        "",
        "## Layers",
        "",
    ]
    for layer in model.layers:
        lines.append(f"- **{layer.layer}:** `{layer.status}`")
        if layer.artifact_refs:
            lines.append(f"  - artifacts: {', '.join(layer.artifact_refs)}")
        if layer.gaps:
            lines.append(f"  - gaps: {'; '.join(layer.gaps)}")
    lines.extend(["", "## Unresolved gaps", ""])
    lines.extend(_items(model.unresolved_gaps))
    lines.extend(["", "_Provider drafts require human confirmation before a layer is marked complete._"])
    return "\n".join(lines)
