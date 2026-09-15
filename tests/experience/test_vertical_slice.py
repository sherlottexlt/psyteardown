from psyteardown.experience.models import (
    CandidateDraft,
    ClaimJudgement,
    DeclaredFact,
    DesignBrief,
    DesignVariableValue,
    DivergenceMatrix,
    EventStep,
    ExperienceCriterion,
    EvidenceReference,
    InterventionEventSequence,
    PatchScope,
    ReviewItemDraft,
    ResponseBranch,
    RevisionMeta,
    ValidationTask,
    VariablePatchDraft,
)
from psyteardown.experience.providers import FakeClaimJudge, FakeDesignGenerator, FakeReviewReasoner
from psyteardown.experience.service import ExperienceApplicationService


def event(event_type, scenario_id="scenario-1"):
    return InterventionEventSequence(
        event_id=f"{event_type}-{scenario_id}",
        event_type=event_type,
        scenario_id=scenario_id,
        criticality="routine",
        trigger="task active",
        context_snapshot="focused work",
        context_inference="high confidence",
        permission_decision="allowed",
        feedback_steps=(EventStep(step_id=f"step-{event_type}", modality="private_haptic", timing="boundary", salience_level=1, duration_ms=250, repetition=0, variable_refs=("feedback.modality",)),),
        expected_user_response="accept, reject, snooze or correct",
        response_branches=(
            ResponseBranch(response="user_rejected", condition="explicit reject", outcome="termination"),
            ResponseBranch(response="user_snoozed", condition="explicit snooze", outcome="recovery", resume_condition="next boundary", max_retries=1),
            ResponseBranch(response="no_response", condition="timeout", outcome="termination"),
            ResponseBranch(response="feedback_not_detectable", condition="cannot tell", outcome="recovery"),
            ResponseBranch(response="user_corrected", condition="wrong context", outcome="recovery"),
        ),
        correction_path="stop and mark corrected",
        recovery_path="return to task",
        termination_conditions=("reject", "timeout"),
    )


def brief():
    return DesignBrief(
        brief_id="brief-1",
        revision_id="brief-1.r1",
        meta=RevisionMeta(revision=1, created_by="human", reason="draft"),
        goal="low interruption feedback",
        target_segment="knowledge workers",
        researchability_confirmed=True,
        context="attention task",
        scenario_ids=("scenario-1",),
        criteria=(ExperienceCriterion(criterion_id="control", name="Control", operational_definition="can stop", desired_direction="higher", priority=1),),
        divergence_matrix=DivergenceMatrix(variable_ids=("feedback.modality",), strategy_directions=("quiet", "visible", "controlled")),
    )


def candidate(candidate_id, direction, parent=None):
    value = DesignVariableValue(variable_id="feedback.modality", value_type="enum", normalized_value="private_haptic" if direction != "visible" else "visual", display_value=direction)
    return CandidateDraft(
        candidate_id=candidate_id,
        brief_revision_id="brief-1.r1",
        parent_candidate_revision_id=parent,
        name=f"Candidate {candidate_id}",
        description="structured candidate",
        interaction_story="single response step",
        target_context="focused work",
        strategy_direction=direction,
        changed_variable_ids=["feedback.modality"],
        declared_facts=[DeclaredFact(fact_id=f"{candidate_id}-fact", subject="device", predicate="feedback", value=direction, source_locator="text:1")],
        variables=[value],
        events=[event(kind) for kind in ("normal_intervention", "defer_or_reject", "low_confidence", "misclassification_recovery")],
        generator_application_declarations={"patch-1": "applied"},
    )


def review_draft(candidate_id, status="revise"):
    return ReviewItemDraft(
        review_item_id=f"review-{candidate_id}",
        event_id="normal_intervention-scenario-1",
        criterion_ids=["control"],
        fact_ids=[f"{candidate_id}-fact"],
        context="focused work",
        observation="device has a bounded feedback path",
        hypothesis="explicit stop path may preserve control",
        evidence=[EvidenceReference(layer="design_fact", source_id=f"{candidate_id}-fact", locator="text:1")],
        proposed_alignment="support",
        status=status,
        risk="low",
        tradeoff="less discoverable than public audio",
        actionable_changes=[
            VariablePatchDraft(
                patch_id=f"patch-{candidate_id}",
                variable_id="feedback.modality",
                operation="replace",
                from_value=DesignVariableValue(variable_id="feedback.modality", value_type="enum", normalized_value="private_haptic", display_value="private haptic"),
                to_value=DesignVariableValue(variable_id="feedback.modality", value_type="enum", normalized_value="visual", display_value="visual"),
                scope=PatchScope(event_ids=("normal_intervention-scenario-1",)),
                suggested_enforcement="should",
                rationale="test discoverability",
                evidence_refs=[f"{candidate_id}-fact"],
                expected_effect="make feedback easier to notice",
                verification="compare detection rate",
            )
        ],
    )


def test_two_round_slice_tracks_freeze_review_partial_order_and_repair():
    first_round = [candidate(f"candidate-{i}", direction) for i, direction in enumerate(["quiet", "visible", "controlled", "quiet", "visible"], start=1)]
    design = FakeDesignGenerator([first_round])
    reasoner = FakeReviewReasoner([[review_draft(f"candidate-{i}") ] for i in range(1, 6)])
    judge = FakeClaimJudge([ClaimJudgement(review_item_id=f"review-candidate-{i}", verdict="supported", evidence_refs=[f"candidate-{i}-fact"], rationale="fact grounded") for i in range(1, 6)])
    service = ExperienceApplicationService(design_generator=design, review_reasoner=reasoner, claim_judge=judge)
    frozen_brief = service.freeze_brief(brief())
    iteration = service.create_iteration(frozen_brief)
    candidates = service.import_candidates(iteration)
    for imported in candidates:
        facts = service.freeze_facts(imported)
        draft = service.generate_review_drafts(facts)[0]
        service.confirm_review_item(facts, draft, service.judge_review_draft(facts, draft))
    current = service.repository.get_current("iteration", iteration.iteration_id)
    order = service.compare_candidates(current)
    assert len(order.preferred) + len(order.viable_alternatives) + len(order.needs_evidence) + len(order.blocked) == 5
    selected_ids = order.preferred[:1] or order.needs_evidence[:1]
    decision = service.select_candidates(current.model_copy(update={"status": "compared"}), order, candidate_ids=selected_ids, action="explore_further" if order.needs_evidence else "select")
    prompt = service.confirm_next_prompt(
        current.model_copy(update={"status": "selected", "selection_decision_id": decision.revision_id}),
        decision,
        validation_task_ids=("validate-1",) if decision.action == "explore_further" else (),
    )
    # A provider-generated declaration is not trusted; the child fact diff is
    # what determines adoption.
    parent = candidates[0]
    child_draft = candidate("candidate-2-1", "quiet", parent=parent.candidate_revision_id).model_copy(update={"variables": [DesignVariableValue(variable_id="feedback.modality", value_type="enum", normalized_value="visual", display_value="visual")]})
    child = service.repository.get_revision("candidate", parent.candidate_revision_id)
    child = child.model_copy(update={"candidate_id": "candidate-2-1", "candidate_revision_id": "candidate-2-1.r1", "parent_candidate_revision_id": parent.candidate_revision_id, "variables": tuple(child_draft.variables)})
    trace = service.build_variable_repair_trace(parent, child, tuple(item.variable_patches[0] for item in service.repository.list_revisions("review") if item.candidate_id == parent.candidate_id))
    assert trace.patch_applications[0].adoption == "adopted"
    assert prompt.confirmed_patch_revision_ids
