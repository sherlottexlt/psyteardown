from datetime import datetime, timezone

import pytest

from psyteardown.experience.models import DependencyRef, RevisionMeta
from psyteardown.product import (
    CompetingExplanation,
    DeliveryEstimate,
    FalsifiablePrediction,
    MechanismHypothesis,
    OutcomeContract,
    ProblemFact,
    ProblemModel,
    ProductIntent,
    ProductThesis,
    ResourceBoundary,
    SourceReference,
    StopCondition,
    SuccessIndicator,
    TargetOutcome,
    ValidationStep,
)


@pytest.fixture
def occurred_at() -> datetime:
    return datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def source_ref() -> SourceReference:
    return SourceReference(source_type="user_input", source_id="message-1")


@pytest.fixture
def proposed_intent(source_ref: SourceReference) -> ProductIntent:
    return ProductIntent(
        intent_id="intent-1",
        revision_id="intent-1.r1",
        meta=RevisionMeta(revision=1, created_by="studio", reason="intent proposed"),
        project_id="project-1",
        desired_change="Help independent workers protect focused work time",
        affected_people=("independent knowledge workers",),
        explicit_non_goals=("surveil employee activity",),
        known_constraints=("local-first",),
        source_refs=(source_ref,),
    )


@pytest.fixture
def proposed_problem(source_ref: SourceReference) -> ProblemModel:
    return ProblemModel(
        problem_model_id="problem-1",
        revision_id="problem-1.r1",
        meta=RevisionMeta(revision=1, created_by="studio", reason="problem proposed"),
        project_id="project-1",
        intent_revision_id="intent-1.r2",
        facts=(
            ProblemFact(
                fact_id="fact-1",
                statement="The user reports frequent context switching",
                source_refs=(source_ref,),
            ),
        ),
        competing_explanations=(
            CompetingExplanation(
                explanation_id="explanation-1",
                statement="Incoming tools create avoidable interruptions",
                supporting_fact_ids=("fact-1",),
                cheapest_falsification="Observe one work session with notifications muted",
            ),
            CompetingExplanation(
                explanation_id="explanation-2",
                statement="Task ambiguity drives voluntary switching",
                supporting_fact_ids=("fact-1",),
                cheapest_falsification="Compare a session with a precommitted task list",
            ),
        ),
        dependencies=(
            DependencyRef(object_type="product_intent", object_id="intent-1", revision=2),
        ),
    )


@pytest.fixture
def proposed_contract() -> OutcomeContract:
    return OutcomeContract(
        outcome_contract_id="contract-1",
        revision_id="contract-1.r1",
        meta=RevisionMeta(revision=1, created_by="studio", reason="contract proposed"),
        project_id="project-1",
        intent_revision_id="intent-1.r2",
        problem_model_revision_id="problem-1.r2",
        target_segments=("independent knowledge workers",),
        applicable_contexts=("self-directed desktop work",),
        target_outcomes=(
            TargetOutcome(
                outcome_id="outcome-1",
                description="Complete chosen focus tasks with fewer involuntary switches",
                indicator_ids=("indicator-1",),
            ),
        ),
        success_indicators=(
            SuccessIndicator(
                indicator_id="indicator-1",
                operational_definition="Task switches not initiated by the user's stated plan",
                observation_method="Consented task-session review",
                desired_direction="decrease",
                threshold_or_target="lower than the user's unaided baseline",
                required_evidence="real_user_observation",
            ),
        ),
        prohibited_outcomes_reviewed=True,
        resource_boundary=ResourceBoundary(
            time_budget="first usable prototype within one day"
        ),
        stop_conditions=(
            StopCondition(
                condition_id="stop-1",
                condition="The intervention increases user-reported pressure",
                action="reframe",
            ),
        ),
        required_real_world_evidence=("consented real task session",),
        dependencies=(
            DependencyRef(object_type="product_intent", object_id="intent-1", revision=2),
            DependencyRef(object_type="problem_model", object_id="problem-1", revision=2),
        ),
    )


@pytest.fixture
def proposed_thesis() -> ProductThesis:
    return ProductThesis(
        thesis_id="thesis-1",
        revision_id="thesis-1.r1",
        meta=RevisionMeta(revision=1, created_by="studio", reason="thesis proposed"),
        project_id="project-1",
        problem_model_revision_id="problem-1.r2",
        outcome_contract_revision_id="contract-1.r2",
        name="Intentional interruption gate",
        product_promise="Make nonessential interruptions wait for an intentional boundary",
        differentiation="Changes interruption timing instead of scoring personal productivity",
        realization_modes=("software",),
        mechanism_hypotheses=(
            MechanismHypothesis(
                mechanism_id="mechanism-1",
                condition="The user has declared a bounded focus task",
                proposed_intervention="Queue nonessential interruptions until a task boundary",
                expected_change="Fewer involuntary context switches",
                uncertainty="The queue may create anxiety about missed information",
            ),
        ),
        falsifiable_predictions=(
            FalsifiablePrediction(
                prediction_id="prediction-1",
                prediction="Unaided involuntary task switches decrease",
                failure_observation="Switches do not decrease or perceived pressure rises",
                cheapest_test="One reversible local prototype session",
            ),
        ),
        validation_strategy=(
            ValidationStep(
                validation_step_id="validation-1",
                question="Can a user recover queued items without losing trust?",
                method="Run a scripted browser task and a consented user session",
                evidence_level="real_user_observation",
                pass_condition="No missed critical item and acceptable perceived control",
                estimated_cost="one prototype and one session",
            ),
        ),
        key_unknowns=("Whether delayed items increase anxiety",),
        key_risks=("Suppressing a genuinely urgent item",),
        delivery_estimate=DeliveryEstimate(
            initial_delivery_cost="one web prototype",
            operating_cost="local processing",
            maintenance_burden="browser integration updates",
        ),
        dependencies=(
            DependencyRef(object_type="problem_model", object_id="problem-1", revision=2),
            DependencyRef(object_type="outcome_contract", object_id="contract-1", revision=2),
        ),
    )
