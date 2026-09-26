"""C2 derivation and gates for Outcome Contract measurement plans.

A measurement plan says how each contract indicator would be observed, by
which source layer, and what that layer can at most support.  Derivation is a
deterministic copy of the confirmed contract into a proposal; it never invents
thresholds, recruits anyone or records an observation.  Structural errors are
rejected when a proposal is submitted, while incompleteness is reported as
confirmation blockers so a partially edited plan can still be saved.
"""

from __future__ import annotations

from psyteardown.experience.models import SamplePlan
from psyteardown.product.commands import OutcomeMeasurementPlanProposal
from psyteardown.product.models import (
    MEASUREMENT_LAYER_COMPATIBILITY,
    MEASUREMENT_REAL_WORLD_EVIDENCE,
    MEASUREMENT_RUNTIME_EVENT_BLOCKED_REASON,
    MEASUREMENT_THRESHOLD_PLACEHOLDER,
    MeasurementGuardrail,
    OutcomeContract,
    OutcomeMeasure,
    OutcomeMeasurementPlan,
    SuccessIndicator,
    is_measurement_threshold_placeholder,
)

# A small first trial: enough people to see whether the indicator is
# observable at all, not a powered study.  Humans may change the bounds.
DERIVED_SAMPLE_MINIMUM = 3
DERIVED_SAMPLE_MAXIMUM = 8


def _measures_for(indicator: SuccessIndicator, *, primary: bool) -> list[OutcomeMeasure]:
    common = {
        "indicator_id": indicator.indicator_id,
        "operational_definition": indicator.operational_definition,
        "desired_direction": indicator.desired_direction,
        "threshold_or_target": indicator.threshold_or_target,
    }
    evidence = indicator.required_evidence
    if evidence in {"deterministic_check", "tool_result"}:
        return [
            OutcomeMeasure(
                measure_id=f"{indicator.indicator_id}-software",
                label="Automated check result",
                method="B4 build, Playwright and axe checks on the delivered revision",
                source_layer="software_check",
                value_kind="boolean",
                primary=primary,
                **common,
            )
        ]
    if evidence == "expert_review":
        return [
            OutcomeMeasure(
                measure_id=f"{indicator.indicator_id}-expert",
                label="Named expert judgement",
                method=f"Named expert review against the definition: {indicator.observation_method}",
                source_layer="expert_review",
                value_kind="categorical",
                primary=primary,
                **common,
            )
        ]
    measures = [
        OutcomeMeasure(
            measure_id=f"{indicator.indicator_id}-observed",
            label="Observed in a consented task session",
            method=f"Researcher-observed consented task session: {indicator.observation_method}",
            source_layer="research_observation",
            value_kind="boolean",
            primary=primary,
            **common,
        )
    ]
    if evidence == "real_user_observation":
        measures.append(
            OutcomeMeasure(
                measure_id=f"{indicator.indicator_id}-reported",
                label="Participant report after the session",
                method="Explicit participant report (B7 preview feedback or post-session question)",
                source_layer="user_report",
                value_kind="ordinal_1_5",
                **common,
            )
        )
    else:
        measures.append(
            OutcomeMeasure(
                measure_id=f"{indicator.indicator_id}-runtime",
                label="Runtime event count",
                method="Product runtime events during the session",
                source_layer="runtime_event",
                value_kind="count",
                blocked_reason=MEASUREMENT_RUNTIME_EVENT_BLOCKED_REASON,
                **common,
            )
        )
    return measures


def derive_measurement_plan_proposal(
    contract: OutcomeContract,
) -> OutcomeMeasurementPlanProposal:
    """Copy a confirmed contract into a reviewable measurement plan proposal."""

    if contract.status != "confirmed":
        raise ValueError("a measurement plan can only be derived from a confirmed outcome contract")
    measures: list[OutcomeMeasure] = []
    for index, indicator in enumerate(contract.success_indicators):
        measures.extend(_measures_for(indicator, primary=index == 0))
    guardrails = [
        MeasurementGuardrail(
            guardrail_id=f"{item.prohibited_outcome_id}-guardrail",
            prohibited_outcome_id=item.prohibited_outcome_id,
            severity=item.severity,
            detection_method=item.detection_method,
            source_layer="research_observation",
            response=item.response,
        )
        for item in contract.prohibited_outcomes
    ]
    contexts = "; ".join(contract.applicable_contexts) or "the declared context"
    return OutcomeMeasurementPlanProposal(
        outcome_contract_revision_id=contract.revision_id,
        measures=measures,
        guardrails=guardrails,
        stop_condition_ids=[item.condition_id for item in contract.stop_conditions],
        sample_plan=SamplePlan(
            target_population="; ".join(contract.target_segments) or "the declared target segment",
            minimum_n=DERIVED_SAMPLE_MINIMUM,
            maximum_n=DERIVED_SAMPLE_MAXIMUM,
            allocation="single condition; each participant uses the delivered revision",
            inclusion_criteria=tuple(contract.applicable_contexts),
            exclusion_criteria=("people who cannot give informed consent",),
        ),
        observation_window=f"One consented task session per participant in {contexts}",
        consent_scope=(
            "Explicit per-session consent covering only the listed measures; "
            "no automatic capture from the product (PS-O007)"
        ),
        withdrawal_policy=(
            "A participant may withdraw at any time; their observations are excluded and erased"
        ),
    )


def measurement_plan_structure_errors(
    proposal: OutcomeMeasurementPlanProposal, contract: OutcomeContract
) -> tuple[str, ...]:
    """Errors that make a proposal meaningless against its pinned contract."""

    errors: list[str] = []
    indicators = {item.indicator_id: item for item in contract.success_indicators}
    prohibited = {item.prohibited_outcome_id for item in contract.prohibited_outcomes}
    stops = {item.condition_id for item in contract.stop_conditions}
    for measure in proposal.measures:
        indicator = indicators.get(measure.indicator_id)
        if indicator is None:
            errors.append(f"measure {measure.measure_id} references unknown indicator {measure.indicator_id}")
            continue
        allowed = MEASUREMENT_LAYER_COMPATIBILITY[indicator.required_evidence]
        if measure.source_layer not in allowed:
            errors.append(
                f"measure {measure.measure_id} uses {measure.source_layer}, which cannot produce "
                f"{indicator.required_evidence} for indicator {indicator.indicator_id}"
            )
    for guardrail in proposal.guardrails:
        if guardrail.prohibited_outcome_id not in prohibited:
            errors.append(
                f"guardrail {guardrail.guardrail_id} references unknown prohibited outcome "
                f"{guardrail.prohibited_outcome_id}"
            )
    for condition_id in proposal.stop_condition_ids:
        if condition_id not in stops:
            errors.append(f"plan references unknown stop condition {condition_id}")
    return tuple(errors)


def measurement_plan_blockers(
    plan: OutcomeMeasurementPlan, contract: OutcomeContract | None
) -> tuple[str, ...]:
    """Everything that keeps a plan from being operational and confirmable."""

    if contract is None:
        return ("the project has no current outcome contract",)
    blockers: list[str] = []
    if contract.status != "confirmed":
        blockers.append("the current outcome contract is not confirmed")
    if plan.outcome_contract_revision_id != contract.revision_id:
        blockers.append(
            f"plan pins {plan.outcome_contract_revision_id} but the current outcome contract is "
            f"{contract.revision_id}; derive a new plan revision"
        )
        return tuple(blockers)
    by_indicator: dict[str, list[OutcomeMeasure]] = {}
    for measure in plan.measures:
        by_indicator.setdefault(measure.indicator_id, []).append(measure)
    for indicator in contract.success_indicators:
        measures = by_indicator.get(indicator.indicator_id, [])
        if not measures:
            blockers.append(f"indicator {indicator.indicator_id} has no measure")
            continue
        if indicator.required_evidence in MEASUREMENT_REAL_WORLD_EVIDENCE and not any(
            item.collectable and item.source_layer != "software_check" for item in measures
        ):
            blockers.append(
                f"indicator {indicator.indicator_id} requires {indicator.required_evidence} "
                "but has no collectable measure"
            )
    primaries = [item.measure_id for item in plan.measures if item.primary]
    if len(primaries) != 1:
        blockers.append(f"exactly one primary measure is required; found {len(primaries)}")
    elif not next(item for item in plan.measures if item.primary).collectable:
        blockers.append(f"primary measure {primaries[0]} is blocked and cannot be collected")
    for measure in plan.measures:
        if is_measurement_threshold_placeholder(measure.threshold_or_target):
            blockers.append(f"measure {measure.measure_id} still needs a concrete human-set threshold")
    if not plan.sample_plan.target_population.strip():
        blockers.append("sample target population must be specified")
    if not any(item.strip() for item in plan.sample_plan.inclusion_criteria):
        blockers.append("sample inclusion criteria must be specified")
    if not plan.observation_window.strip():
        blockers.append("observation window must be specified")
    if not plan.consent_scope.strip():
        blockers.append("consent scope must be specified")
    if not plan.withdrawal_policy.strip():
        blockers.append("withdrawal policy must be specified")
    covered = {item.prohibited_outcome_id for item in plan.guardrails}
    for item in contract.prohibited_outcomes:
        if item.prohibited_outcome_id not in covered:
            blockers.append(f"prohibited outcome {item.prohibited_outcome_id} has no guardrail")
    referenced = set(plan.stop_condition_ids)
    for item in contract.stop_conditions:
        if item.condition_id not in referenced:
            blockers.append(f"stop condition {item.condition_id} is not part of the plan")
    return tuple(blockers)
