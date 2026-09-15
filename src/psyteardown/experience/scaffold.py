"""High-level entry points for generating complete first-pass designs."""

from __future__ import annotations

from pydantic import Field

from psyteardown.experience.models import (
    AuditEvent,
    BoundaryModel,
    DesignBrief,
    DesignCandidate,
    DesignRuleSet,
    DesignIteration,
    DivergenceMatrix,
    DomainEvent,
    ExperienceCriterion,
    FutureMovementScenario,
    ProgressiveDesignModel,
    ScenarioPolicy,
    RevisionMeta,
)
from psyteardown.experience.mobility import (
    FutureMovementScenarioInput,
    MovementPhaseInput,
    build_movement_scenarios,
    create_progressive_design_model,
    generate_initial_design_rules,
    build_scenario_policy,
)
from psyteardown.experience.providers import ScaffoldDesignGenerator
from psyteardown.experience.render import render_candidate_markdown
from psyteardown.experience.repositories import InMemoryExperienceRepository
from psyteardown.experience.service import ExperienceApplicationService


class DesignCriterionInput(BoundaryModel):
    criterion_id: str
    name: str
    operational_definition: str
    desired_direction: str = "higher"
    priority: int = Field(default=1, ge=1)


class InitialDesignRequest(BoundaryModel):
    """Small request object for callers that do not need the full domain DTO."""

    brief_id: str = "brief-scaffold"
    product_category: str = "AI mobile device or accessory"
    goal: str
    target_segment: str
    context: str
    criteria: list[DesignCriterionInput]
    scenario_id: str = "core-attention-task"
    prohibited_experiences: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    tradeoff_priorities: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    design_language: list[str] = Field(default_factory=list)
    movement_scenarios: list[FutureMovementScenarioInput] = Field(default_factory=list)


class InitialDesignBatch(BoundaryModel):
    """Boundary response containing the frozen brief and complete candidates."""

    brief: DesignBrief
    iteration: DesignIteration
    candidates: list[DesignCandidate]
    movement_scenarios: list[FutureMovementScenario] = Field(default_factory=list)
    scenario_policies: list[ScenarioPolicy] = Field(default_factory=list)
    design_rule_set: DesignRuleSet | None = None
    progressive_models: list[ProgressiveDesignModel] = Field(default_factory=list)
    domain_events: list[DomainEvent] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


def build_scaffold_brief(request: InitialDesignRequest, *, actor: str = "human") -> DesignBrief:
    movement_inputs = request.movement_scenarios or [
        FutureMovementScenarioInput(
            scenario_id=request.scenario_id,
            name="Default active movement",
            narrative="The user is moving through the world while attention and hand availability change.",
            phases=[
                MovementPhaseInput(
                    phase_id=f"{request.scenario_id}.walking",
                    movement_state="walking",
                    posture="walking_posture",
                    hands_available="intermittent",
                    visual_attention="intermittent",
                    ambient_motion="medium",
                    social_visibility="public",
                    device_relation="worn_wrist",
                    transition_to="task_transition",
                ),
                MovementPhaseInput(
                    phase_id=f"{request.scenario_id}.transition",
                    movement_state="task_transition",
                    posture="standing",
                    hands_available="one",
                    visual_attention="available",
                    ambient_motion="low",
                    social_visibility="shared",
                    device_relation="worn_wrist",
                    transition_from="walking",
                ),
            ],
            task_goal=request.goal,
        )
    ]
    movement_scenarios = build_movement_scenarios(movement_inputs)
    criteria = tuple(
        ExperienceCriterion(
            criterion_id=item.criterion_id,
            name=item.name,
            operational_definition=item.operational_definition,
            desired_direction=item.desired_direction,
            priority=item.priority,
        )
        for item in request.criteria
    )
    base_brief = DesignBrief(
        brief_id=request.brief_id,
        revision_id=f"{request.brief_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="scaffold brief created"),
        product_category=request.product_category,
        goal=request.goal,
        target_segment=request.target_segment,
        researchability_confirmed=True,
        context=request.context,
        scenario_ids=tuple(scenario.scenario_id for scenario in movement_scenarios),
        movement_scenarios=movement_scenarios,
        criteria=criteria,
        tradeoff_priorities=tuple(request.tradeoff_priorities),
        required_capabilities=tuple(request.required_capabilities),
        design_language=tuple(request.design_language)
        + tuple(f"avoid: {item}" for item in request.prohibited_experiences)
        + tuple(f"constraint note: {item}" for item in request.hard_constraints),
        divergence_matrix=DivergenceMatrix(
            variable_ids=("feedback.modality", "feedback.timing", "feedback.confirmation"),
            strategy_directions=("quiet_control", "discoverable", "privacy_first"),
        ),
    )
    rule_set = generate_initial_design_rules(base_brief.revision_id, movement_scenarios, actor=actor)
    return base_brief.model_copy(
        update={
            "initial_design_rules": rule_set.rules,
            "design_rule_set_revision_id": rule_set.revision_id,
        }
    )


def generate_initial_design_batch(
    request: InitialDesignRequest,
    *,
    actor: str = "human",
    count: int = 5,
    repository=None,
    generator: ScaffoldDesignGenerator | None = None,
) -> InitialDesignBatch:
    """Run the guarded Brief -> Iteration -> Candidate import workflow."""

    if count != 5:
        raise ValueError("the first vertical slice requires exactly 5 candidates")
    brief = build_scaffold_brief(request, actor=actor)
    repo = repository or InMemoryExperienceRepository()
    service = ExperienceApplicationService(
        repo,
        design_generator=generator or ScaffoldDesignGenerator(),
    )
    frozen_brief = service.freeze_brief(brief, actor=actor)
    iteration = service.create_iteration(frozen_brief, actor=actor)
    candidates = service.import_candidates(iteration, actor=actor)
    current_iteration = repo.get_current("iteration", iteration.iteration_id)
    movement_scenarios = frozen_brief.movement_scenarios
    rule_set = generate_initial_design_rules(frozen_brief.revision_id, movement_scenarios, actor=actor)
    repo.save("rule_set", rule_set.rule_set_id, rule_set.revision_id, rule_set)
    service._record(
        event_type="DesignRuleSetGenerated",
        aggregate_id=rule_set.rule_set_id,
        revision_id=rule_set.revision_id,
        actor=actor,
        reason="movement scenario projection",
    )
    policies = tuple(build_scenario_policy(scenario, actor=actor) for scenario in movement_scenarios)
    for policy in policies:
        repo.save("scenario_policy", policy.policy_id, policy.revision_id, policy)
        service._record(event_type="ScenarioPolicyCompiled", aggregate_id=policy.policy_id, revision_id=policy.revision_id, actor=actor, reason="movement scenario policy projection")
    progressive_models: list[ProgressiveDesignModel] = []
    for candidate in candidates:
        model = create_progressive_design_model(candidate, rule_set, actor=actor, scenario_policy_revision_ids=tuple(policy.revision_id for policy in policies))
        repo.save("progressive_model", model.model_id, model.revision_id, model)
        progressive_models.append(model)
        service._record(
            event_type="ProgressiveDesignModelInitialized",
            aggregate_id=model.model_id,
            revision_id=model.revision_id,
            actor=actor,
            reason="structured design baseline",
        )
    return InitialDesignBatch(
        brief=frozen_brief,
        iteration=current_iteration,
        candidates=list(candidates),
        movement_scenarios=list(movement_scenarios),
        scenario_policies=list(policies),
        design_rule_set=rule_set,
        progressive_models=progressive_models,
        domain_events=list(repo.domain_events),
        audit_events=list(repo.audit_events),
    )


def generate_complete_design(
    request: InitialDesignRequest,
    *,
    variant: int = 0,
    actor: str = "human",
) -> DesignCandidate:
    """Return one complete variant by explicit index, never by hidden ranking."""

    batch = generate_initial_design_batch(request, actor=actor)
    try:
        return batch.candidates[variant]
    except IndexError as exc:
        raise ValueError(f"variant must be between 0 and {len(batch.candidates) - 1}") from exc


def render_initial_design_batch(batch: InitialDesignBatch) -> str:
    """Render all variants as one readable Markdown design deck."""

    lines = [
        f"# Initial Design Batch: {batch.brief.product_category}",
        "",
        f"- **Brief:** `{batch.brief.brief_id}` / `{batch.brief.revision_id}`",
        f"- **Iteration:** `{batch.iteration.iteration_id}` / `{batch.iteration.status}`",
        f"- **Goal:** {batch.brief.goal}",
        f"- **Target segment:** {batch.brief.target_segment}",
        f"- **Context:** {batch.brief.context}",
        f"- **Movement scenarios:** {len(batch.movement_scenarios)}",
        f"- **Initial design rules:** {len(batch.design_rule_set.rules) if batch.design_rule_set else 0} (candidate/validation-only)",
        "",
        "_以下是并列候选；系统没有自动选择“最佳设计”。_",
        "",
    ]
    if batch.movement_scenarios:
        lines.extend(["## 未来运动场景", ""])
        for scenario in batch.movement_scenarios:
            lines.append(f"- **{scenario.name}** (`{scenario.scenario_id}`): {scenario.narrative}")
            for phase in scenario.phases:
                lines.append(
                    f"  - `{phase.phase_id}`: {phase.movement_state}, hands={phase.hands_available}, "
                    f"visual={phase.visual_attention}, social={phase.social_visibility}, "
                    f"device={phase.device_relation}"
                )
        lines.extend(["", "## 初步设计规则", ""])
        if batch.design_rule_set:
            for rule in batch.design_rule_set.rules:
                lines.append(f"- **{rule.name}** (`{rule.enforcement}`): {rule.recommendation}")
            lines.extend(["", "_规则来自声明的运动场景投影，尚未经过真人结果验证或人工批准。_", ""])
    for index, candidate in enumerate(batch.candidates, start=1):
        lines.extend([f"\n---\n\n## Variant {index}: {candidate.name}\n"])
        lines.append(render_candidate_markdown(candidate))
    return "\n".join(lines)


def render_initial_design_json(batch: InitialDesignBatch) -> str:
    return batch.model_dump_json(indent=2)
