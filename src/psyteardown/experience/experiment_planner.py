"""Deterministic M2 experiment planning from conditional hypotheses.

The planner creates a preregistration-shaped draft.  It does not recruit
participants, run statistics, or promote a hypothesis to ``supported``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

from psyteardown.experience.models import (
    AnalysisProtocolReview,
    AnalysisFamily,
    ConditionSnapshot,
    DependencyRef,
    ExperimentPlan,
    ExperimentVariable,
    ExperienceHypothesis,
    HypothesisBinding,
    MeasureSpec,
    RevisionMeta,
    SamplePlan,
    StoppingRule,
    DesignVariableValue,
)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _revision_number(revision_id: str) -> int:
    try:
        return int(revision_id.rsplit(".r", 1)[1])
    except (IndexError, ValueError):
        return 1


def _slug(value: str) -> str:
    return "-".join(value.lower().replace("/", " ").split())[:64] or "variable"


def plan_completeness(plan: ExperimentPlan) -> tuple[str, ...]:
    """Return missing preregistration fields in deterministic order."""
    missing: list[str] = []
    if not plan.hypothesis_binding_ids:
        missing.append("hypothesis_binding_ids")
    if not plan.research_question:
        missing.append("research_question")
    if not plan.independent_variables:
        missing.append("independent_variables")
    if any(len(variable.levels) < 2 for variable in plan.independent_variables):
        missing.append("independent_variables.levels")
    if not plan.control_conditions:
        missing.append("control_conditions")
    if not plan.dependent_measures:
        missing.append("dependent_measures")
    if plan.sample_plan is None:
        missing.append("sample_plan")
    if not plan.confounds:
        missing.append("confounds")
    if not plan.stopping_rules:
        missing.append("stopping_rules")
    if not plan.success_criteria:
        missing.append("success_criteria")
    if not plan.analysis_family_revision_id:
        missing.append("analysis_family_revision_id")
    if not plan.condition_snapshot_ids:
        missing.append("condition_snapshot_ids")
    primary_measures = tuple(item.measure_id for item in plan.dependent_measures if item.primary)
    if len(primary_measures) != 1:
        missing.append("dependent_measures.primary_exactly_one")
    return tuple(missing)


def build_hypothesis_binding(
    hypothesis: ExperienceHypothesis,
    *,
    binding_id: str,
    measure_ids: Iterable[str],
    analysis_family_id: str,
    candidate_revision_id: str | None = None,
    facts_snapshot_id: str | None = None,
    event_ids: Iterable[str] = (),
    role: str = "primary",
    actor: str = "system",
) -> HypothesisBinding:
    """Create the immutable hypothesis-to-protocol binding for a plan."""
    return HypothesisBinding(
        binding_id=binding_id,
        revision_id=f"{binding_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="hypothesis bound to experiment protocol"),
        hypothesis_revision_id=hypothesis.revision_id,
        candidate_revision_id=candidate_revision_id or f"{hypothesis.hypothesis_id}.candidate.r1",
        facts_snapshot_id=facts_snapshot_id or f"{hypothesis.hypothesis_id}.facts.r1",
        event_ids=tuple(event_ids),
        role=role,
        predicted_outcome=hypothesis.predicted_outcome,
        measure_ids=tuple(measure_ids),
        analysis_family_id=analysis_family_id,
        dependencies=(DependencyRef(object_type="experience_hypothesis", object_id=hypothesis.hypothesis_id, revision=hypothesis.meta.revision),),
    )


def build_analysis_family(
    *,
    family_id: str,
    binding: HypothesisBinding,
    primary_measure_ids: Iterable[str],
    correction: str = "none",
    analysis_method: str = "pre-registered comparison with uncertainty interval",
    interpretation_policy: str = "primary result is interpreted before secondary or exploratory results",
    actor: str = "system",
    locked: bool = False,
) -> AnalysisFamily:
    """Create the analysis-family snapshot that fixes result tiers."""
    return AnalysisFamily(
        family_id=family_id,
        revision_id=f"{family_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="analysis family declared for experiment"),
        primary_binding_ids=(binding.binding_id,) if binding.role == "primary" else (),
        secondary_binding_ids=(binding.binding_id,) if binding.role == "secondary" else (),
        exploratory_binding_ids=(binding.binding_id,) if binding.role == "exploratory" else (),
        primary_measure_ids=tuple(primary_measure_ids),
        correction=correction,
        interpretation_policy=interpretation_policy,
        locked=locked,
        analysis_method=analysis_method,
    )


def build_condition_snapshots(
    plan: ExperimentPlan,
    *,
    candidate_revision_id: str | None = None,
    environment: str = "unspecified",
    actor: str = "system",
) -> tuple[ConditionSnapshot, ...]:
    """Materialize immutable baseline/proposed condition lineage for a plan."""
    candidate = candidate_revision_id or f"{plan.generated_from_hypothesis_id or plan.experiment_id}.candidate.r1"
    snapshots: list[ConditionSnapshot] = []
    for variable in plan.independent_variables:
        for level in variable.levels:
            condition_id = f"{plan.experiment_id}-{variable.variable_id}-{_slug(level)}"
            value = DesignVariableValue(
                variable_id=variable.variable_id,
                value_type="enum",
                normalized_value=level,
                display_value=level,
            )
            snapshot = ConditionSnapshot(
                condition_id=condition_id,
                revision_id=f"{condition_id}.r1",
                meta=RevisionMeta(revision=1, created_by=actor, reason="immutable experiment condition snapshot"),
                candidate_revision_id=candidate,
                variable_values=(value,),
                environment=environment,
            )
            snapshots.append(snapshot.model_copy(update={"content_hash_value": snapshot.content_hash}))
    return tuple(snapshots)


def revise_condition_snapshot(
    snapshot: ConditionSnapshot,
    *,
    variable_values: Iterable[DesignVariableValue],
    reason: str,
    actor: str = "human",
) -> ConditionSnapshot:
    """Create a child condition revision; never mutate a presented condition."""
    values = tuple(variable_values)
    if not values:
        raise ValueError("a condition revision requires at least one variable value")
    revision = snapshot.meta.revision + 1
    child = snapshot.model_copy(update={
        "revision_id": f"{snapshot.condition_id}.r{revision}",
        "meta": RevisionMeta(
            revision=revision,
            parent_revision_id=snapshot.revision_id,
            created_by=actor,
            reason=reason,
        ),
        "variable_values": values,
        "content_hash_value": None,
    })
    return child.model_copy(update={"content_hash_value": child.content_hash})


def validate_analysis_protocol(
    plan: ExperimentPlan,
    *,
    family: AnalysisFamily | None = None,
    bindings: Iterable[HypothesisBinding] = (),
    conditions: Iterable[ConditionSnapshot] = (),
) -> tuple[str, ...]:
    """Return deterministic pre-data analysis gate failures.

    The gate is intentionally descriptive: it never runs an analysis and it
    never changes a hypothesis status.  Callers can present the returned codes
    to a human reviewer before importing real outcomes.
    """
    issues: list[str] = list(plan_completeness(plan))
    if plan.status not in {"preregistered", "approved", "started", "completed"}:
        issues.append("plan_not_preregistered")
    binding_values = tuple(item for item in bindings if item is not None)
    condition_values = tuple(item for item in conditions if item is not None)
    if family is None:
        issues.append("analysis_family_not_loaded")
    else:
        if family.revision_id != plan.analysis_family_revision_id:
            issues.append("analysis_family_revision_mismatch")
        if not family.locked:
            issues.append("analysis_family_not_locked")
        tiers = set(family.primary_binding_ids) | set(family.secondary_binding_ids) | set(family.exploratory_binding_ids)
        if set(plan.hypothesis_binding_ids) != tiers:
            issues.append("analysis_family_binding_coverage")
        declared_primary = tuple(item.measure_id for item in plan.dependent_measures if item.primary)
        if tuple(family.primary_measure_ids) != declared_primary:
            issues.append("analysis_family_primary_measure_mismatch")
    if binding_values:
        ids = {item.binding_id for item in binding_values}
        if ids != set(plan.hypothesis_binding_ids):
            issues.append("hypothesis_binding_coverage")
        for item in binding_values:
            if item.analysis_family_id and family is not None and item.analysis_family_id != family.family_id:
                issues.append(f"binding_analysis_family_mismatch:{item.binding_id}")
            measure_ids = set(item.measure_ids)
            declared = {measure.measure_id for measure in plan.dependent_measures}
            if not measure_ids.issubset(declared):
                issues.append(f"binding_measure_unknown:{item.binding_id}")
    else:
        issues.append("hypothesis_bindings_not_loaded")
    if condition_values:
        ids = {item.revision_id for item in condition_values}
        if ids != set(plan.condition_snapshot_ids):
            issues.append("condition_snapshot_coverage")
        if any(item.content_hash_value != item.content_hash for item in condition_values):
            issues.append("condition_snapshot_hash_mismatch")
    else:
        issues.append("condition_snapshots_not_loaded")
    # Preserve order while preventing duplicate messages when a malformed plan
    # triggers the same structural check through multiple paths.
    return tuple(dict.fromkeys(issues))


def review_analysis_protocol(
    plan: ExperimentPlan,
    *,
    reviewer: str,
    family: AnalysisFamily | None = None,
    bindings: Iterable[HypothesisBinding] = (),
    conditions: Iterable[ConditionSnapshot] = (),
    approved: bool = False,
    finalize: bool = False,
    rationale: str = "analysis protocol reviewed",
    actor: str | None = None,
    reviewed_at: datetime | None = None,
) -> AnalysisProtocolReview:
    """Record a human analysis-protocol gate decision."""
    issues = validate_analysis_protocol(plan, family=family, bindings=bindings, conditions=conditions)
    when = reviewed_at or datetime.now(timezone.utc)
    status = "approved" if approved and not issues else ("rejected" if (approved and issues) or finalize else "pending")
    if approved and issues:
        rationale = rationale + "; gate failures: " + ", ".join(issues)
    review_id = _id("analysis-protocol-review")
    return AnalysisProtocolReview(
        review_id=review_id,
        revision_id=f"{review_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor or reviewer, reason=rationale),
        experiment_revision_id=plan.revision_id,
        reviewer=reviewer,
        sample_size_reviewed="sample_plan" not in issues,
        stopping_rules_reviewed="stopping_rules" not in issues,
        missingness_reviewed=(
            bool(plan.dependent_measures)
            and "dependent_measures" not in issues
            and "dependent_measures.primary_exactly_one" not in issues
            and all(bool(item.missingness_policy.strip()) for item in plan.dependent_measures)
        ),
        analysis_family_reviewed=not any(item.startswith("analysis_family") for item in issues),
        condition_lineage_reviewed=not any(item.startswith("condition_") for item in issues),
        status=status,
        rationale=rationale,
        reviewed_at=when if status in {"approved", "rejected"} else None,
    )


def build_experiment_plan_bundle(
    hypothesis: ExperienceHypothesis,
    **kwargs,
) -> tuple[ExperimentPlan, HypothesisBinding, AnalysisFamily, tuple[ConditionSnapshot, ...]]:
    """Build a plan and all formal lineage snapshots in one pure operation."""
    actor = kwargs.get("actor", "system")
    # Keep lineage-only options local to the bundle builder; the base planner
    # intentionally accepts only fields that belong on ``ExperimentPlan``.
    plan_kwargs = {
        key: value for key, value in kwargs.items()
        if key in {
            "experiment_id", "brief_revision_id", "hypothesis_binding_id",
            "independent_variables", "control_conditions", "dependent_measures",
            "sample_plan", "confounds", "stopping_rules", "success_criteria",
            "ethics_notes", "actor", "candidate_revision_id", "facts_snapshot_id",
            "event_ids", "correction",
        }
    }
    plan = build_experiment_plan(hypothesis, **plan_kwargs)
    binding_id = plan.hypothesis_binding_ids[0]
    family_id = plan.analysis_family_revision_id.rsplit(".r", 1)[0] if plan.analysis_family_revision_id else f"{plan.experiment_id}.analysis"
    binding = build_hypothesis_binding(
        hypothesis,
        binding_id=binding_id,
        measure_ids=[item.measure_id for item in plan.dependent_measures],
        analysis_family_id=family_id,
        candidate_revision_id=kwargs.get("candidate_revision_id"),
        facts_snapshot_id=kwargs.get("facts_snapshot_id"),
        event_ids=kwargs.get("event_ids", ()),
        actor=actor,
    )
    family = build_analysis_family(
        family_id=family_id,
        binding=binding,
        primary_measure_ids=[item.measure_id for item in plan.dependent_measures if item.primary],
        correction=kwargs.get("correction", "none"),
        actor=actor,
        locked=False,
    )
    conditions = build_condition_snapshots(
        plan,
        candidate_revision_id=kwargs.get("candidate_revision_id"),
        environment=hypothesis.environment_condition,
        actor=actor,
    )
    plan = plan.model_copy(update={
        "hypothesis_binding_ids": (binding.binding_id,),
        "analysis_family_revision_id": family.revision_id,
        "condition_snapshot_ids": tuple(item.revision_id for item in conditions),
        "protocol_snapshot": {
            **dict(plan.protocol_snapshot),
            "hypothesis_binding_revision_id": binding.revision_id,
            "analysis_family_revision_id": family.revision_id,
            "condition_snapshot_ids": [item.revision_id for item in conditions],
        },
        "dependencies": (
            DependencyRef(
                object_type="experience_hypothesis",
                object_id=hypothesis.hypothesis_id,
                revision=hypothesis.meta.revision,
            ),
            DependencyRef(
                object_type="hypothesis_binding",
                object_id=binding.binding_id,
                revision=binding.meta.revision,
            ),
            DependencyRef(
                object_type="analysis_family",
                object_id=family.family_id,
                revision=family.meta.revision,
            ),
            *tuple(
                DependencyRef(
                    object_type="condition",
                    object_id=item.condition_id,
                    revision=item.meta.revision,
                )
                for item in conditions
            ),
        ),
    })
    return plan, binding, family, conditions


# Verbose command-oriented aliases used by integrations that treat these
# builders as explicit domain commands.
create_hypothesis_binding = build_hypothesis_binding
create_analysis_family = build_analysis_family
create_condition_snapshots = build_condition_snapshots
analysis_protocol_gate = validate_analysis_protocol


def build_experiment_plan(
    hypothesis: ExperienceHypothesis,
    *,
    experiment_id: str | None = None,
    brief_revision_id: str = "unbound-brief.r1",
    hypothesis_binding_id: str | None = None,
    candidate_revision_id: str | None = None,
    facts_snapshot_id: str | None = None,
    event_ids: Iterable[str] = (),
    correction: str = "none",
    independent_variables: Iterable[ExperimentVariable] | None = None,
    control_conditions: Iterable[str] | None = None,
    dependent_measures: Iterable[MeasureSpec] | None = None,
    sample_plan: SamplePlan | None = None,
    confounds: Iterable[str] | None = None,
    stopping_rules: Iterable[StoppingRule] | None = None,
    success_criteria: Iterable[str] | None = None,
    ethics_notes: Iterable[str] | None = None,
    actor: str = "system",
) -> ExperimentPlan:
    """Create a deterministic draft plan, filling only defensible defaults."""
    if hypothesis.status == "rejected":
        raise ValueError("cannot plan an experiment from a rejected hypothesis")
    experiment_id = experiment_id or _id("experiment")
    variables = tuple(independent_variables or ())
    if not variables:
        for index, feature in enumerate(hypothesis.physical_features or ("design intervention",)):
            variable_id = f"feature-{index + 1}-{_slug(feature)}"
            variables += (ExperimentVariable(
                variable_id=variable_id,
                label=feature,
                levels=("baseline", "proposed"),
                manipulation=f"hold all other features constant and vary {feature}",
                assignment="between_subject",
            ),)
    controls = tuple(control_conditions or ("baseline condition without the focal intervention",))
    measures = tuple(dependent_measures or (
        MeasureSpec(
            measure_id="primary-task-outcome",
            label="task outcome",
            operational_definition=hypothesis.predicted_outcome,
            method="pre-registered task observation with explicit missingness coding",
            primary=True,
        ),
    ))
    sample = sample_plan or SamplePlan(
        target_population=hypothesis.target_population,
        minimum_n=20,
        maximum_n=60,
        allocation="balanced across conditions",
    )
    confound_values = tuple(confounds or (
        "prior familiarity with the product",
        "task difficulty and environmental interruption",
        "order and learning effects",
    ))
    rules = tuple(stopping_rules or (
        StoppingRule(rule_id="safety-stop", condition="any participant safety or privacy concern", action="stop"),
        StoppingRule(rule_id="quality-pause", condition="critical measure missingness exceeds 20%", action="pause"),
    ))
    criteria = tuple(success_criteria or (
        f"Compare conditions on: {hypothesis.predicted_outcome}",
        "Report uncertainty, missingness, deviations, and alternative explanations",
    ))
    ethics = tuple(ethics_notes or (
        "obtain informed consent before formal task exposure",
        "do not infer health, emotion, or intent from behavior",
        "allow withdrawal without penalty and minimize retained raw data",
    ))
    question = f"Under {hypothesis.environment_condition} and {hypothesis.social_condition}, does {hypothesis.mechanism} change {hypothesis.predicted_outcome}?"
    binding_id = hypothesis_binding_id or f"{experiment_id}-binding"
    payload = {
        "planner": "psyteardown-m2",
        "hypothesis_id": hypothesis.hypothesis_id,
        "alternative_explanations": list(hypothesis.alternative_explanations),
        "validation_method": hypothesis.validation_method,
        "hypothesis_binding_revision_id": f"{binding_id}.r1",
        "analysis_family_revision_id": f"{experiment_id}.analysis.r1",
        "candidate_revision_id": candidate_revision_id or f"{hypothesis.hypothesis_id}.candidate.r1",
        "facts_snapshot_id": facts_snapshot_id or f"{hypothesis.hypothesis_id}.facts.r1",
        "event_ids": list(event_ids),
        "multiplicity_correction": correction,
    }
    condition_ids = tuple(
        f"{experiment_id}-{variable.variable_id}-{_slug(level)}.r1"
        for variable in variables for level in variable.levels
    )
    return ExperimentPlan(
        experiment_id=experiment_id,
        revision_id=f"{experiment_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="M2 experiment plan generated"),
        brief_revision_id=brief_revision_id,
        hypothesis_binding_ids=(binding_id,),
        generated_from_hypothesis_id=hypothesis.hypothesis_id,
        research_question=question,
        independent_variables=variables,
        control_conditions=controls,
        dependent_measures=measures,
        sample_plan=sample,
        confounds=confound_values,
        stopping_rules=rules,
        success_criteria=criteria,
        ethics_notes=ethics,
        protocol_snapshot=payload,
        analysis_family_revision_id=f"{experiment_id}.analysis.r1",
        condition_snapshot_ids=condition_ids,
        status="draft",
    )


def preregister_plan(plan: ExperimentPlan, *, actor: str = "human") -> ExperimentPlan:
    """Freeze a complete draft as a new preregistered revision."""
    if plan.status != "draft":
        raise ValueError("only draft experiment plans can be preregistered")
    missing = plan_completeness(plan)
    if missing:
        raise ValueError("experiment plan is incomplete: " + ", ".join(missing))
    revision = plan.meta.revision + 1
    return plan.model_copy(update={
        "revision_id": f"{plan.experiment_id}.r{revision}",
        "meta": RevisionMeta(revision=revision, parent_revision_id=plan.revision_id, created_by=actor, reason="human preregistration approval"),
        "status": "preregistered",
    })


def render_experiment_plan_markdown(plan: ExperimentPlan) -> str:
    lines = [
        f"# Preregistration: `{plan.experiment_id}`", "",
        f"- Revision: `{plan.revision_id}`", f"- Status: `{plan.status}`",
        f"- Hypothesis: `{plan.generated_from_hypothesis_id or 'unbound'}`", "",
        "## Research question", "", plan.research_question or "未声明", "",
        "## Independent variables", "",
    ]
    for variable in plan.independent_variables:
        lines.append(f"- `{variable.variable_id}` — {variable.label}: {', '.join(variable.levels)} ({variable.assignment})")
        lines.append(f"  - manipulation: {variable.manipulation}")
    lines += ["", "## Controls", "", *[f"- {item}" for item in plan.control_conditions], "", "## Dependent measures", ""]
    for measure in plan.dependent_measures:
        lines.append(f"- `{measure.measure_id}` — {measure.label}{' (primary)' if measure.primary else ''}: {measure.operational_definition}; method: {measure.method}; missingness: {measure.missingness_policy}")
    sample = plan.sample_plan
    lines += ["", "## Sample", "", f"- population: {sample.target_population if sample else '未声明'}", f"- range: {sample.minimum_n if sample else '—'}–{sample.maximum_n if sample else '—'}", f"- allocation: {sample.allocation if sample else '—'}", "", "## Confounds", "", *[f"- {item}" for item in plan.confounds], "", "## Stopping rules", ""]
    lines += [f"- `{rule.rule_id}` — {rule.condition} → **{rule.action}**" for rule in plan.stopping_rules]
    lines += ["", "## Analysis lock", "", f"- analysis family revision: `{plan.analysis_family_revision_id or '未声明'}`", f"- condition snapshots: {', '.join(plan.condition_snapshot_ids) if plan.condition_snapshot_ids else '未声明'}", "- primary/secondary/exploratory tiers must be locked before data import.", "", "## Success criteria", "", *[f"- {item}" for item in plan.success_criteria], "", "## Ethics and privacy", "", *[f"- {item}" for item in plan.ethics_notes], "", "## Limitations", "", "- This is a preregistration plan, not evidence of a result.", "- Supported/rejected status requires later human review of real experiment data.", "- Analysis-protocol review is a human gate; it does not run statistics or update hypothesis status."]
    return "\n".join(lines) + "\n"


def render_experiment_plan_json(plan: ExperimentPlan) -> str:
    return json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2)
