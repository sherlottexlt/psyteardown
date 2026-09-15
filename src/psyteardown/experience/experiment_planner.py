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
    ExperimentPlan,
    ExperimentVariable,
    ExperienceHypothesis,
    MeasureSpec,
    RevisionMeta,
    SamplePlan,
    StoppingRule,
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
    return tuple(missing)


def build_experiment_plan(
    hypothesis: ExperienceHypothesis,
    *,
    experiment_id: str | None = None,
    brief_revision_id: str = "unbound-brief.r1",
    hypothesis_binding_id: str | None = None,
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
    payload = {
        "planner": "psyteardown-m2",
        "hypothesis_id": hypothesis.hypothesis_id,
        "alternative_explanations": list(hypothesis.alternative_explanations),
        "validation_method": hypothesis.validation_method,
    }
    return ExperimentPlan(
        experiment_id=experiment_id,
        revision_id=f"{experiment_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="M2 experiment plan generated"),
        brief_revision_id=brief_revision_id,
        hypothesis_binding_ids=(hypothesis_binding_id or hypothesis.hypothesis_id,),
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
        lines.append(f"- `{measure.measure_id}` — {measure.label}{' (primary)' if measure.primary else ''}: {measure.operational_definition}; method: {measure.method}")
    sample = plan.sample_plan
    lines += ["", "## Sample", "", f"- population: {sample.target_population if sample else '未声明'}", f"- range: {sample.minimum_n if sample else '—'}–{sample.maximum_n if sample else '—'}", f"- allocation: {sample.allocation if sample else '—'}", "", "## Confounds", "", *[f"- {item}" for item in plan.confounds], "", "## Stopping rules", ""]
    lines += [f"- `{rule.rule_id}` — {rule.condition} → **{rule.action}**" for rule in plan.stopping_rules]
    lines += ["", "## Success criteria", "", *[f"- {item}" for item in plan.success_criteria], "", "## Ethics and privacy", "", *[f"- {item}" for item in plan.ethics_notes], "", "## Limitations", "", "- This is a preregistration plan, not evidence of a result.", "- Supported/rejected status requires later human review of real experiment data."]
    return "\n".join(lines) + "\n"


def render_experiment_plan_json(plan: ExperimentPlan) -> str:
    return json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2)
