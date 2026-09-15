from psyteardown.experience.models import (
    CandidateDraft,
    DeclaredFact,
    DesignBrief,
    DesignVariableValue,
    DivergenceMatrix,
    EventStep,
    ExperienceCriterion,
    InterventionEventSequence,
    PatchScope,
    ResponseBranch,
    RevisionMeta,
)
from psyteardown.experience.rules import build_candidate, validate_event_sequence


def _event(event_type="normal_intervention"):
    return InterventionEventSequence(
        event_id=f"event-{event_type}",
        event_type=event_type,
        scenario_id="scenario-1",
        criticality="routine",
        trigger="task is active",
        context_snapshot="focused work",
        context_inference="confidence=high",
        permission_decision="allowed",
        feedback_steps=(
            EventStep(
                step_id="step-1",
                modality="private_haptic",
                timing="after 2 seconds",
                salience_level=1,
                duration_ms=300,
                repetition=0,
                variable_refs=("feedback.modality",),
            ),
        ),
        expected_user_response="accept or defer",
        response_branches=(
            ResponseBranch(response="user_rejected", condition="user rejects", outcome="termination"),
            ResponseBranch(response="user_snoozed", condition="user snoozes", outcome="recovery", resume_condition="next task boundary", max_retries=1),
            ResponseBranch(response="no_response", condition="timeout", outcome="termination"),
            ResponseBranch(response="feedback_not_detectable", condition="detectability unknown", outcome="recovery"),
            ResponseBranch(response="user_corrected", condition="wrong context", outcome="recovery"),
        ),
        correction_path="stop and mark corrected",
        recovery_path="return to task",
        termination_conditions=("accepted", "rejected", "timeout"),
    )


def _brief():
    return DesignBrief(
        brief_id="brief-1",
        revision_id="brief-1.r1",
        meta=RevisionMeta(revision=1, created_by="test", reason="draft"),
        goal="low interruption AI device",
        target_segment="knowledge workers",
        researchability_confirmed=True,
        context="attention task",
        scenario_ids=("scenario-1",),
        criteria=(ExperienceCriterion(criterion_id="control", name="Control", operational_definition="can stop", desired_direction="higher", priority=1),),
        divergence_matrix=DivergenceMatrix(variable_ids=("feedback.modality",), strategy_directions=("quiet", "visible", "user_controlled")),
    )


def _draft(candidate_id="candidate-1"):
    variable = DesignVariableValue(variable_id="feedback.modality", value_type="enum", normalized_value="private_haptic", display_value="private haptic")
    return CandidateDraft(
        candidate_id=candidate_id,
        brief_revision_id="brief-1.r1",
        name="Quiet device",
        description="A quiet wearable",
        interaction_story="device vibrates once and waits",
        target_context="focused work",
        strategy_direction="quiet",
        changed_variable_ids=["feedback.modality"],
        declared_facts=[DeclaredFact(fact_id="fact-1", subject="device", predicate="uses", value="private haptic", source_locator="text:1")],
        variables=[variable],
        events=[_event(kind) for kind in ("normal_intervention", "defer_or_reject", "low_confidence", "misclassification_recovery")],
    )


def test_valid_candidate_and_event_sequence():
    candidate = build_candidate(_draft(), _brief(), actor="test", reason="import")
    assert candidate.status == "input_valid"
    assert validate_event_sequence(candidate.events[0]) == []


def test_missing_event_is_generation_invalid():
    draft = _draft()
    draft = draft.model_copy(update={"events": draft.events[:1]})
    candidate = build_candidate(draft, _brief(), actor="test", reason="import")
    assert candidate.status == "generation_invalid"
    assert any(issue.code == "generation_invalid" for issue in candidate.validation_issues)
