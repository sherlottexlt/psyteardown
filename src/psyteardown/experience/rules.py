"""Deterministic policies for workflow gates and cross-candidate comparison."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable
from uuid import uuid4

from psyteardown.experience.models import (
    CandidateDraft,
    CandidateEvaluationRecord,
    CandidateFactsSnapshot,
    CandidatePartialOrder,
    CriterionAssessment,
    DependencyRef,
    DesignBrief,
    DesignCandidate,
    DesignIteration,
    DomainStateError,
    EventCoverage,
    EvidenceConflict,
    ExperienceCriterion,
    InterventionEventSequence,
    PartialOrderReason,
    PartialOrderTier,
    RevisionMeta,
    ValidationIssue,
    VariablePatch,
    PatchConflict,
    ValueMissingReason,
    Evidence,
    Observation,
    ExperienceHypothesis,
    Critique,
)
from psyteardown.experience.iteration import canonical_variable_id


REQUIRED_EVENT_TYPES = {
    "normal_intervention",
    "defer_or_reject",
    "low_confidence",
    "misclassification_recovery",
}


# M1 evidence/claim checks ---------------------------------------------------
# These checks deliberately return ``ValidationIssue`` values instead of
# silently rewriting provider output.  Callers can show the issues to a human
# reviewer and persist a new immutable revision after correction.

OVERSTRONG_CLAIM_TERMS = (
    "必然",
    "证明",
    "一定导致",
    "必定导致",
    "必然导致",
    "inevitably",
    "proves",
    "proven",
    "definitely causes",
    "always causes",
    "guarantees",
    "guaranteed to",
)


def check_claim_language(*parts: str) -> tuple[str, ...]:
    """Return deterministic overclaim tokens found in claim text."""

    text = " ".join(parts).lower()
    return tuple(term for term in OVERSTRONG_CLAIM_TERMS if term.lower() in text)


def validate_evidence(evidence: Evidence) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if not evidence.artifact_id or not evidence.quote_or_locator:
        issues.append(ValidationIssue(code="evidence_source_missing", field="evidence", message="evidence requires artifact_id and a source locator"))
    if evidence.kind in {"video", "audio"} and evidence.start_ms is not None and evidence.end_ms is not None and evidence.end_ms < evidence.start_ms:
        issues.append(ValidationIssue(code="evidence_locator_invalid", field="evidence.time_range", message="end_ms must be >= start_ms"))
    artifact = evidence.artifact_id.lower()
    if (
        evidence.evidence_role in {"physical_measurement", "experiment_result"}
        and (evidence.provenance in {"blender_derived", "design_derived"} or artifact.endswith((".glb", ".gltf", ".png")))
    ):
        issues.append(ValidationIssue(code="design_asset_not_measurement", field="evidence.evidence_role", message="Blender/GLB/PNG assets are design observations, not physical performance evidence"))
    return tuple(issues)


def validate_observation_claim(observation: Observation) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = list(
        issue for evidence in observation.evidence for issue in validate_evidence(evidence)
    )
    if not observation.evidence:
        issues.append(ValidationIssue(code="evidence_source_missing", field="observation.evidence", message="an observation fact requires at least one traceable source"))
    direct_psychology = observation.observation_type == "psychological" or any(
        token in observation.predicate.lower()
        for token in ("feel", "emotion", "trust", "safe", "comfort", "安心", "信任", "情绪", "舒适")
    )
    if direct_psychology and (
        observation.certainty != "reported"
        or not any(item.kind in {"interview", "experiment"} for item in observation.evidence)
    ):
        issues.append(ValidationIssue(code="psychology_claim_from_observation", field="observation.predicate", message="psychological conclusions require an explicit report and must be tested as a hypothesis"))
    if observation.certainty == "supported" and not any(item.kind == "experiment" for item in observation.evidence):
        issues.append(ValidationIssue(code="supported_without_experiment", field="observation.certainty", message="supported requires real experiment evidence"))
    return tuple(issues)


def validate_hypothesis_claim(hypothesis: ExperienceHypothesis) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if not hypothesis.alternative_explanations:
        issues.append(ValidationIssue(code="alternative_explanation_missing", field="hypothesis.alternative_explanations", message="at least one alternative explanation is required"))
    if hypothesis.status == "supported" and not any(item.kind == "experiment" for item in hypothesis.evidence):
        issues.append(ValidationIssue(code="supported_without_experiment", field="hypothesis.status", message="supported requires real experiment evidence"))
    overclaims = check_claim_language(hypothesis.mechanism, hypothesis.predicted_outcome)
    if hypothesis.status == "supported" and overclaims:
        issues.append(ValidationIssue(code="overstrong_causal_language", field="hypothesis.predicted_outcome", message="over-strong causal language cannot be marked supported"))
    issues.extend(issue for evidence in hypothesis.evidence for issue in validate_evidence(evidence))
    return tuple(issues)


def validate_critique_claim(critique: Critique) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for index, hypothesis in enumerate(critique.hypotheses):
        issues.extend(
            issue.model_copy(update={"field": f"hypotheses[{index}].{issue.field}"})
            for issue in validate_hypothesis_claim(hypothesis)
        )
    if critique.status == "approved" and not critique.reviewer:
        issues.append(ValidationIssue(code="human_review_required", field="critique.reviewer", message="an approved critique requires a human reviewer"))
    return tuple(issues)


def validate_m1_claims(
    *,
    evidence: Iterable[Evidence] = (),
    observations: Iterable[Observation] = (),
    hypotheses: Iterable[ExperienceHypothesis] = (),
    critiques: Iterable[Critique] = (),
) -> tuple[ValidationIssue, ...]:
    """Validate a collection of generic M1 claims without mutating it."""

    issues: list[ValidationIssue] = []
    issues.extend(issue for item in evidence for issue in validate_evidence(item))
    issues.extend(issue for item in observations for issue in validate_observation_claim(item))
    issues.extend(issue for item in hypotheses for issue in validate_hypothesis_claim(item))
    issues.extend(issue for item in critiques for issue in validate_critique_claim(item))
    return tuple(issues)


# Friendly aliases for callers that use the shorter naming from the M1 brief.
check_m1_claims = validate_m1_claims
check_experience_claims = validate_m1_claims


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def validate_brief_for_freeze(brief: DesignBrief) -> None:
    if brief.status == "frozen":
        return
    if not brief.researchability_confirmed:
        raise DomainStateError("DesignBrief requires researchability confirmation before freeze")
    if not brief.scenario_ids:
        raise DomainStateError("DesignBrief requires at least one scenario")
    if not brief.criteria:
        raise DomainStateError("DesignBrief requires at least one operationalized criterion")
    if len({c.criterion_id for c in brief.criteria}) != len(brief.criteria):
        raise DomainStateError("DesignBrief contains duplicate criterion IDs")
    if len(brief.divergence_matrix.strategy_directions) < brief.divergence_matrix.minimum_directions:
        raise DomainStateError("DesignBrief divergence matrix is incomplete")


def validate_candidate_draft(draft: CandidateDraft, brief: DesignBrief) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if draft.brief_revision_id != brief.revision_id:
        issues.append(ValidationIssue(code="brief_mismatch", field="brief_revision_id", message="candidate references another brief revision"))
    if not draft.description or not draft.interaction_story or not draft.target_context:
        issues.append(ValidationIssue(code="input_incomplete", field="candidate", message="description, interaction_story and target_context are required"))
    if not draft.declared_facts:
        issues.append(ValidationIssue(code="input_incomplete", field="declared_facts", message="at least one declared fact is required"))
    if not draft.variables:
        issues.append(ValidationIssue(code="input_incomplete", field="variables", message="at least one canonical variable is required"))
    event_types = {event.event_type for event in draft.events}
    missing = REQUIRED_EVENT_TYPES - event_types
    if missing:
        issues.append(ValidationIssue(code="generation_invalid", field="events", message=f"missing required event types: {sorted(missing)}"))
    if draft.supports_critical and "critical_intervention" not in event_types:
        issues.append(ValidationIssue(code="generation_invalid", field="events", message="supports_critical requires critical_intervention event"))
    for event in draft.events:
        issues.extend(validate_event_sequence(event))
        if event.scenario_id not in brief.scenario_ids:
            issues.append(ValidationIssue(code="brief_mismatch", field=f"events[{event.event_id}].scenario_id", message="event scenario is not in the frozen brief"))
    if not draft.changed_variable_ids:
        issues.append(ValidationIssue(code="divergence_missing", field="changed_variable_ids", message="candidate must name changed design variables"))
    issues.extend(_validate_import_constraints(draft, brief))
    return tuple(issues)


def _validate_import_constraints(draft: CandidateDraft, brief: DesignBrief) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    values = {variable.variable_id: variable.normalized_value for variable in draft.variables}
    values.update({fact.fact_id: fact.value for fact in draft.declared_facts})
    for constraint in brief.constraints:
        if constraint.check_stage != "import" or constraint.field_path not in values:
            continue
        actual = values[constraint.field_path]
        expected = constraint.value
        try:
            valid = {
                "eq": actual == expected,
                "ne": actual != expected,
                "lt": actual < expected,
                "lte": actual <= expected,
                "gt": actual > expected,
                "gte": actual >= expected,
                "in": actual in expected if isinstance(expected, tuple) else actual == expected,
                "not_in": actual not in expected if isinstance(expected, tuple) else actual != expected,
            }[constraint.operator]
        except TypeError:
            valid = False
        if not valid:
            issues.append(
                ValidationIssue(
                    code=constraint.failure_status,
                    field=constraint.field_path,
                    message=f"constraint {constraint.constraint_id} failed: {actual!r} {constraint.operator} {expected!r}",
                )
            )
    return issues


def validate_event_sequence(event: InterventionEventSequence) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not event.feedback_steps:
        issues.append(ValidationIssue(code="input_incomplete", field=f"events[{event.event_id}].feedback_steps", message="feedback_steps cannot be empty"))
    if len(event.feedback_steps) > 3:
        issues.append(ValidationIssue(code="event_sequence_complexity_exceeded", field=f"events[{event.event_id}].feedback_steps", message="at most 3 feedback steps are allowed"))
    if len(event.response_branches) > 5:
        issues.append(ValidationIssue(code="event_sequence_complexity_exceeded", field=f"events[{event.event_id}].response_branches", message="at most 5 response branches are allowed"))
    response_types = {branch.response for branch in event.response_branches}
    for required in {"user_rejected", "user_snoozed", "no_response", "feedback_not_detectable", "user_corrected"}:
        if required not in response_types:
            issues.append(ValidationIssue(code="input_incomplete", field=f"events[{event.event_id}].response_branches", message=f"missing {required} branch"))
    if not event.termination_conditions:
        issues.append(ValidationIssue(code="input_incomplete", field=f"events[{event.event_id}].termination_conditions", message="termination conditions are required"))
    if event.criticality == "critical" and event.escalation_count > 1:
        issues.append(ValidationIssue(code="event_sequence_complexity_exceeded", field=f"events[{event.event_id}].escalation_count", message="critical escalation may occur at most once"))
    return issues


def build_candidate(draft: CandidateDraft, brief: DesignBrief, *, actor: str, reason: str) -> DesignCandidate:
    issues = validate_candidate_draft(draft, brief)
    revision_id = _id(f"{draft.candidate_id}.r1")
    return DesignCandidate(
        candidate_id=draft.candidate_id,
        candidate_revision_id=revision_id,
        meta=RevisionMeta(revision=1, created_by=actor, reason=reason),
        brief_revision_id=draft.brief_revision_id,
        parent_candidate_revision_id=draft.parent_candidate_revision_id,
        status="generation_invalid" if issues else "input_valid",
        name=draft.name,
        description=draft.description,
        interaction_story=draft.interaction_story,
        target_context=draft.target_context,
        unknowns=tuple(draft.unknowns),
        strategy_direction=draft.strategy_direction,
        changed_variable_ids=tuple(draft.changed_variable_ids),
        declared_facts=tuple(draft.declared_facts),
        variables=tuple(draft.variables),
        events=tuple(draft.events),
        supports_critical=draft.supports_critical,
        validation_issues=issues,
        generator_application_declarations=tuple(sorted(draft.generator_application_declarations.items())),
        shape=draft.shape,
        design=draft.design,
    )


def check_batch_divergence(candidates: Iterable[DesignCandidate], brief: DesignBrief) -> tuple[str, ...]:
    candidates = tuple(candidates)
    directions = {c.strategy_direction for c in candidates if c.status == "input_valid"}
    required_vars = set(brief.divergence_matrix.variable_ids)
    changed = {v for c in candidates for v in c.changed_variable_ids}
    gaps: list[str] = []
    if len(directions) < brief.divergence_matrix.minimum_directions:
        gaps.append("strategy_directions")
    if required_vars - changed:
        gaps.append("variables:" + ",".join(sorted(required_vars - changed)))
    return tuple(gaps)


def patch_scopes_overlap(left: VariablePatch, right: VariablePatch) -> bool:
    if left.scope.global_scope or right.scope.global_scope:
        return True

    def overlaps(a: tuple[str, ...], b: tuple[str, ...]) -> bool:
        return not a or not b or bool(set(a).intersection(b))

    return all(
        (
            overlaps(left.scope.scenario_ids, right.scope.scenario_ids),
            overlaps(left.scope.event_ids, right.scope.event_ids),
            overlaps(left.scope.user_segments, right.scope.user_segments),
            overlaps(left.scope.time_or_device_modes, right.scope.time_or_device_modes),
        )
    )


def analyze_patch_conflicts(patches: Iterable[VariablePatch]) -> tuple[PatchConflict, ...]:
    """Return an auditable classification for every overlapping patch pair."""

    confirmed = tuple(patch for patch in patches if patch.status == "confirmed")
    conflicts: list[PatchConflict] = []
    for left, right in combinations(confirmed, 2):
        left_variable = canonical_variable_id(left.variable_id)
        right_variable = canonical_variable_id(right.variable_id)
        if left_variable != right_variable or not patch_scopes_overlap(left, right):
            continue
        left_target = left.to_value.normalized_value if left.to_value else None
        right_target = right.to_value.normalized_value if right.to_value else None
        incompatible = left.operation != right.operation or left_target != right_target
        if not incompatible:
            classification = "compatible"
            reason = "same canonical variable, overlapping scope and compatible target"
        elif "explore" in {left.enforcement, right.enforcement}:
            classification = "exploratory"
            reason = "explore patches do not silently override confirmed must/should changes"
        elif {left.enforcement, right.enforcement} == {"must", "should"}:
            winner = left if left.enforcement == "must" else right
            classification = "shadowed"
            conflicts.append(PatchConflict(
                left_revision_id=left.revision_id,
                right_revision_id=right.revision_id,
                variable_id=left_variable,
                classification=classification,
                winning_revision_id=winner.revision_id,
                reason="must patch deterministically shadows should patch in overlapping scope",
            ))
            continue
        else:
            classification = "blocking"
            reason = "incompatible confirmed patches have equal enforcement and overlapping scope"
        conflicts.append(PatchConflict(
            left_revision_id=left.revision_id,
            right_revision_id=right.revision_id,
            variable_id=left_variable,
            classification=classification,
            reason=reason,
        ))
    return tuple(conflicts)


def find_patch_conflicts(patches: Iterable[VariablePatch]) -> tuple[tuple[str, str], ...]:
    """Backward-compatible blocking conflict IDs for existing callers."""
    return tuple(
        (item.left_revision_id, item.right_revision_id)
        for item in analyze_patch_conflicts(patches)
        if item.classification == "blocking"
    )


def freeze_candidate_facts(
    candidate: DesignCandidate,
    *,
    actor: str,
    confirmed_observations: tuple | None = None,
    conflicts: tuple[EvidenceConflict, ...] = (),
    dependencies: tuple[DependencyRef, ...] = (),
    evidence_review_ids: tuple[str, ...] = (),
) -> CandidateFactsSnapshot:
    if candidate.status != "input_valid":
        raise DomainStateError("generation-invalid candidate cannot freeze facts")
    observations = confirmed_observations
    if observations is None:
        from psyteardown.experience.models import ConfirmedObservation

        observations = tuple(
            ConfirmedObservation(
                observation_id=f"{fact.fact_id}.obs",
                source_fact_id=fact.fact_id,
                subject=fact.subject,
                predicate=fact.predicate,
                value=fact.value,
                source_locator=fact.source_locator,
                confirmation="accepted",
                confirmed_by=actor,
            )
            for fact in candidate.declared_facts
        )
    not_observable = tuple(
        observation.source_fact_id
        for observation in observations
        if observation.confirmation == "not_observable"
    )
    return CandidateFactsSnapshot(
        facts_snapshot_id=_id(f"{candidate.candidate_id}.facts"),
        candidate_id=candidate.candidate_id,
        candidate_revision_id=candidate.candidate_revision_id,
        brief_revision_id=candidate.brief_revision_id,
        meta=RevisionMeta(revision=1, created_by=actor, reason="candidate facts freeze"),
        observations=tuple(observations),
        variables=candidate.variables,
        events=candidate.events,
        conflicts=conflicts,
        not_observable_fact_ids=not_observable,
        dependencies=(DependencyRef(object_type="candidate", object_id=candidate.candidate_id, revision=1), *dependencies),
        evidence_review_ids=evidence_review_ids,
    )


def aggregate_evaluation(
    brief: DesignBrief,
    facts: CandidateFactsSnapshot,
    reviews: tuple,
    *,
    blocked_rule_ids: tuple[str, ...] = (),
    unmet_must_patch_ids: tuple[str, ...] = (),
) -> CandidateEvaluationRecord:
    by_criterion: dict[str, list] = defaultdict(list)
    for item in reviews:
        for criterion_id in item.criterion_ids:
            by_criterion[criterion_id].append(item)
    order = {"strong_risk": 5, "risk": 4, "unknown": 3, "neutral": 2, "support": 1, "strong_support": 0}
    assessments: list[CriterionAssessment] = []
    for criterion in brief.criteria:
        items = by_criterion.get(criterion.criterion_id, [])
        alignments = [item.alignment for item in items]
        if any(item.status == "blocked" or item.alignment == "strong_risk" for item in items):
            alignment = "strong_risk"
        elif any(item.status == "explore" or item.alignment == "unknown" for item in items):
            alignment = "unknown"
        elif alignments:
            alignment = max(alignments, key=lambda value: order[value])
        else:
            alignment = "unknown"
        tension = any(item.alignment in {"support", "strong_support"} for item in items) and any(
            item.alignment in {"risk", "strong_risk"} for item in items
        )
        outcome = max((item.outcome_evidence for item in items), default="none", key=lambda value: ["none", "exploratory", "observed", "supported", "replicated"].index(value))
        assessments.append(
            CriterionAssessment(
                criterion_id=criterion.criterion_id,
                alignment=alignment,
                outcome_evidence=outcome,
                review_item_revision_ids=tuple(item.review_item_revision_id for item in items),
                reasons=tuple(item.risk if item.alignment in {"risk", "strong_risk"} else item.hypothesis for item in items),
                mechanism_tension=tension,
            )
        )
    event_coverage: list[EventCoverage] = []
    for event in facts.events:
        event_reviews = tuple(item for item in reviews if item.event_id == event.event_id)
        if any(item.status == "blocked" for item in event_reviews):
            status = "blocked"
        elif not event_reviews:
            status = "unknown"
        elif any(item.status == "explore" for item in event_reviews):
            status = "partial"
        else:
            status = "covered"
        event_coverage.append(EventCoverage(event_id=event.event_id, status=status, review_item_revision_ids=tuple(item.review_item_revision_id for item in event_reviews)))
    confirmed_blocked_rules = tuple(
        sorted(
            set(blocked_rule_ids).union(
                rule_id
                for item in reviews
                if item.status == "blocked"
                for rule_id in item.approved_rule_ids
            )
        )
    )
    return CandidateEvaluationRecord(
        evaluation_id=_id(f"{facts.candidate_id}.eval"),
        meta=RevisionMeta(revision=1, created_by="system", reason="deterministic evaluation"),
        candidate_id=facts.candidate_id,
        candidate_revision_id=facts.candidate_revision_id,
        facts_snapshot_id=facts.facts_snapshot_id,
        brief_revision_id=facts.brief_revision_id,
        criterion_assessments=tuple(assessments),
        event_coverage=tuple(event_coverage),
        blocked_rule_ids=confirmed_blocked_rules,
        unresolved_conflict_ids=tuple(c.conflict_id for c in facts.conflicts if c.status == "unresolved"),
        unmet_must_patch_ids=unmet_must_patch_ids,
    )


def build_partial_order(
    brief: DesignBrief,
    iteration: DesignIteration,
    evaluations: tuple[CandidateEvaluationRecord, ...],
) -> CandidatePartialOrder:
    tiers: dict[PartialOrderTier, list[str]] = {tier: [] for tier in PartialOrderTier}
    reasons: list[PartialOrderReason] = []
    provisionally_preferred: list[CandidateEvaluationRecord] = []
    for evaluation in evaluations:
        candidate_id = evaluation.candidate_id
        critical_blockers = evaluation.blocked_rule_ids
        has_strong_risk = any(a.alignment == "strong_risk" for a in evaluation.criterion_assessments)
        has_unknown = bool(evaluation.unresolved_conflict_ids) or any(a.alignment == "unknown" for a in evaluation.criterion_assessments) or any(c.status in {"partial", "unknown"} for c in evaluation.event_coverage)
        if critical_blockers or has_strong_risk or any(c.status == "blocked" for c in evaluation.event_coverage):
            if critical_blockers or any(c.status == "blocked" for c in evaluation.event_coverage):
                tier = PartialOrderTier.BLOCKED
                codes = ("approved_rule_block",)
            else:
                tier = PartialOrderTier.VIABLE_ALTERNATIVES
                codes = ("strong_risk_tradeoff",)
        elif has_unknown:
            tier = PartialOrderTier.NEEDS_EVIDENCE
            codes = ("evidence_missing_or_explore",)
        elif evaluation.unmet_must_patch_ids:
            tier = PartialOrderTier.VIABLE_ALTERNATIVES
            codes = ("unmet_must_patch_not_preferred",)
        elif any(a.alignment == "risk" for a in evaluation.criterion_assessments):
            tier = PartialOrderTier.VIABLE_ALTERNATIVES
            codes = ("tradeoff_or_risk",)
        else:
            tier = PartialOrderTier.PREFERRED
            codes = ("meets_progression_threshold",)
            provisionally_preferred.append(evaluation)
        tiers[tier].append(candidate_id)
        reasons.append(PartialOrderReason(candidate_id=candidate_id, tier=tier, codes=codes, criterion_ids=tuple(a.criterion_id for a in evaluation.criterion_assessments if a.alignment in {"risk", "strong_risk", "unknown"}), event_ids=tuple(c.event_id for c in evaluation.event_coverage if c.status != "covered")))
    # Within candidates that meet the progression threshold, retain the
    # Pareto frontier instead of manufacturing a weighted 1-N score.
    alignment_rank = {
        "strong_risk": 0,
        "risk": 1,
        "unknown": 2,
        "neutral": 3,
        "support": 4,
        "strong_support": 5,
    }

    def dominates(left: CandidateEvaluationRecord, right: CandidateEvaluationRecord) -> bool:
        left_values = [alignment_rank[item.alignment] for item in left.criterion_assessments]
        right_values = [alignment_rank[item.alignment] for item in right.criterion_assessments]
        return all(a >= b for a, b in zip(left_values, right_values)) and any(
            a > b for a, b in zip(left_values, right_values)
        )

    dominated = {
        candidate.candidate_id
        for candidate in provisionally_preferred
        if any(
            other.candidate_id != candidate.candidate_id and dominates(other, candidate)
            for other in provisionally_preferred
        )
    }
    if dominated:
        tiers[PartialOrderTier.PREFERRED] = [
            candidate_id
            for candidate_id in tiers[PartialOrderTier.PREFERRED]
            if candidate_id not in dominated
        ]
        tiers[PartialOrderTier.VIABLE_ALTERNATIVES].extend(sorted(dominated))
        reasons = [
            reason.model_copy(
                update={
                    "tier": PartialOrderTier.VIABLE_ALTERNATIVES,
                    "codes": ("pareto_dominated",),
                }
            )
            if reason.candidate_id in dominated
            else reason
            for reason in reasons
        ]

    incomparable: list[tuple[str, str]] = []
    for left, right in combinations(tiers[PartialOrderTier.PREFERRED], 2):
        left_eval = next(e for e in evaluations if e.candidate_id == left)
        right_eval = next(e for e in evaluations if e.candidate_id == right)
        if any(a.alignment != b.alignment for a, b in zip(left_eval.criterion_assessments, right_eval.criterion_assessments)):
            incomparable.append((left, right))
    return CandidatePartialOrder(
        partial_order_id=_id(f"{iteration.iteration_id}.order"),
        meta=RevisionMeta(revision=1, created_by="system", reason="deterministic partial order"),
        brief_revision_id=brief.revision_id,
        iteration_id=iteration.iteration_id,
        preferred_set_id=_id("preferred-set"),
        preferred=tuple(tiers[PartialOrderTier.PREFERRED]),
        viable_alternatives=tuple(tiers[PartialOrderTier.VIABLE_ALTERNATIVES]),
        needs_evidence=tuple(tiers[PartialOrderTier.NEEDS_EVIDENCE]),
        blocked=tuple(tiers[PartialOrderTier.BLOCKED]),
        incomparable_pairs=tuple(incomparable),
        reasons=tuple(reasons),
    )
