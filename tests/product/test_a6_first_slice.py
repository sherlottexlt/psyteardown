"""A6 calibration lock for the first digital-product slice.

This test does not claim a real-user result.  It locks the smallest Product
Contract that the first runnable Web prototype must accept and keeps the
human-confirmation boundary executable.
"""

from datetime import datetime, timezone

from psyteardown.experience.models import DependencyRef, RevisionMeta
from psyteardown.product import (
    CompetingExplanation,
    ConfirmOutcomeContract,
    ConfirmProblemModel,
    ConfirmProductIntent,
    CreateProductProject,
    InMemoryProductRepository,
    OutcomeContractProposal,
    ProblemFact,
    ProblemModelProposal,
    ProductApplicationService,
    ProductIntentProposal,
    ProhibitedOutcome,
    DeliveryMaturity,
    ResourceBoundary,
    SourceReference,
    StopCondition,
    SubmitOutcomeContractProposal,
    SubmitProblemModelProposal,
    SubmitProductIntentProposal,
    SuccessIndicator,
    TargetOutcome,
)


NOW = datetime(2026, 9, 21, 9, 0, tzinfo=timezone.utc)


def test_a6_focus_boundary_slice_forms_the_minimum_confirmed_contract() -> None:
    """The selected first slice is confirmable without extra domain fields."""

    id_counts: dict[str, int] = {}

    def next_id(prefix: str) -> str:
        id_counts[prefix] = id_counts.get(prefix, 0) + 1
        return f"{prefix}-a6-{id_counts[prefix]}"

    service = ProductApplicationService(
        InMemoryProductRepository(), clock=lambda: NOW, id_factory=next_id
    )
    project = service.create_project(
        CreateProductProject(
            project_id="project-a6",
            name="Focus boundary Web slice",
            actor="user-a6",
            reason="freeze first digital-product slice",
        )
    )
    source = SourceReference(source_type="user_input", source_id="a6-input")
    intent = service.submit_product_intent(
        SubmitProductIntentProposal(
            project_id=project.project_id,
            intent_id="intent-a6",
            actor="studio",
            reason="structure first-slice input",
            proposal=ProductIntentProposal(
                desired_change=(
                    "Protect a self-directed knowledge worker's planned desktop focus "
                    "session without hiding urgent contact"
                ),
                affected_people=["self-directed knowledge workers"],
                current_situation=(
                    "Email, chat, and task tools cause unplanned context switching "
                    "during a 25-60 minute focus session"
                ),
                explicit_non_goals=[
                    "score or surveil personal productivity",
                    "silence every urgent contact",
                ],
                known_constraints=[
                    "browser Web product",
                    "local-first data boundary",
                    "every intervention must be reversible",
                ],
                resource_preferences=["setup in under one minute"],
                source_refs=[source],
            ),
        )
    )
    confirmed_intent = service.confirm_product_intent(
        ConfirmProductIntent(
            project_id=project.project_id,
            intent_id=intent.intent_id,
            expected_revision=1,
            actor="user-a6",
            reason="user confirmed value, privacy, and reversibility boundaries",
        )
    )

    fact = ProblemFact(
        fact_id="fact-a6-switching",
        statement="The user reports unplanned switches between desktop work tools.",
        source_refs=(source,),
    )
    problem = service.submit_problem_model(
        SubmitProblemModelProposal(
            project_id=project.project_id,
            problem_model_id="problem-a6",
            actor="studio",
            reason="separate observed report from competing explanations",
            proposal=ProblemModelProposal(
                intent_revision_id=confirmed_intent.revision_id,
                facts=[fact],
                unknowns=[],
                competing_explanations=[
                    {
                        "explanation_id": "explanation-a6-notifications",
                        "statement": "Incoming notifications drive avoidable switches.",
                        "supporting_fact_ids": [fact.fact_id],
                        "cheapest_falsification": "Observe a session with non-urgent notifications queued.",
                    },
                    {
                        "explanation_id": "explanation-a6-ambiguity",
                        "statement": "Task ambiguity drives voluntary switching.",
                        "supporting_fact_ids": [fact.fact_id],
                        "cheapest_falsification": "Compare a session with one precommitted task.",
                    },
                ],
            ),
        )
    )
    confirmed_problem = service.confirm_problem_model(
        ConfirmProblemModel(
            project_id=project.project_id,
            problem_model_id=problem.problem_model_id,
            expected_revision=1,
            actor="user-a6",
            reason="user accepted the fact boundary and competing explanations",
        )
    )

    contract = service.submit_outcome_contract(
        SubmitOutcomeContractProposal(
            project_id=project.project_id,
            outcome_contract_id="contract-a6",
            actor="studio",
            reason="freeze the first-slice outcome boundary",
            proposal=OutcomeContractProposal(
                intent_revision_id=confirmed_intent.revision_id,
                problem_model_revision_id=confirmed_problem.revision_id,
                target_segments=["self-directed knowledge workers"],
                applicable_contexts=[
                    "25-60 minute self-directed desktop work sessions"
                ],
                target_outcomes=[
                    TargetOutcome(
                        outcome_id="outcome-a6-focus",
                        description="Complete a planned focus task with fewer unplanned switches.",
                        indicator_ids=["indicator-a6-switches"],
                    )
                ],
                success_indicators=[
                    SuccessIndicator(
                        indicator_id="indicator-a6-switches",
                        operational_definition="Unplanned task switches during a declared focus session",
                        observation_method="Consented task-session observation and product event log",
                        desired_direction="decrease",
                        threshold_or_target="Below the same user's unaided baseline in a preregistered pilot",
                        required_evidence="real_user_observation",
                    )
                ],
                prohibited_outcomes=[
                    ProhibitedOutcome(
                        prohibited_outcome_id="prohibited-a6-urgent",
                        description="An urgent contact is delayed without explicit user choice.",
                        severity="hard",
                        detection_method="User report and consented task-session review",
                        response="Stop the intervention and reframe the product path",
                    ),
                    ProhibitedOutcome(
                        prohibited_outcome_id="prohibited-a6-surveillance",
                        description="Activity or message content is collected without explicit consent.",
                        severity="hard",
                        detection_method="Deterministic data-boundary inspection",
                        response="Stop collection and discard the path",
                    ),
                ],
                prohibited_outcomes_reviewed=True,
                resource_boundary=ResourceBoundary(
                    time_budget="setup in under one minute",
                    user_attention_budget="no more than one decision per surfaced interruption",
                    data_boundary="no hidden activity collection or message-content upload",
                ),
                stop_conditions=[
                    StopCondition(
                        condition_id="stop-a6-control",
                        condition="A user cannot immediately stop or recover an intervention.",
                        action="stop",
                    ),
                    StopCondition(
                        condition_id="stop-a6-urgent",
                        condition="An urgent contact is missed or delayed without explicit user choice.",
                        action="reframe",
                    ),
                ],
                required_real_world_evidence=[
                    "consented observation of the target task",
                    "user-reported control and interruption recovery",
                ],
                minimum_delivery_maturity=DeliveryMaturity.RUNNABLE_PROTOTYPE,
            ),
        )
    )
    confirmed_contract = service.confirm_outcome_contract(
        ConfirmOutcomeContract(
            project_id=project.project_id,
            outcome_contract_id=contract.outcome_contract_id,
            expected_revision=1,
            actor="user-a6",
            reason="user confirmed outcome, prohibited outcomes, resources, and stop conditions",
        )
    )

    assert confirmed_intent.status == "confirmed"
    assert confirmed_problem.status == "confirmed"
    assert confirmed_contract.status == "confirmed"
    assert confirmed_contract.minimum_delivery_maturity.value == "runnable_prototype"
    assert confirmed_contract.required_real_world_evidence == (
        "consented observation of the target task",
        "user-reported control and interruption recovery",
    )
    assert confirmed_contract.dependencies == (
        DependencyRef(
            object_type="product_intent",
            object_id="intent-a6",
            revision=confirmed_intent.meta.revision,
        ),
        DependencyRef(
            object_type="problem_model",
            object_id="problem-a6",
            revision=confirmed_problem.meta.revision,
        ),
    )
