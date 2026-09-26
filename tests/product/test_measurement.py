from collections import defaultdict
from datetime import datetime, timezone

import pytest

import pytest

from psyteardown.experience.models import DependencyRef
from psyteardown.product import (
    CompetingExplanation,
    ConfirmOutcomeContract,
    ConfirmOutcomeMeasurementPlan,
    DeriveOutcomeMeasurementPlan,
    ConfirmProblemModel,
    ConfirmProductIntent,
    CreateProductProject,
    InMemoryProductRepository,
    MeasurementGuardrail,
    OutcomeContractProposal,
    OutcomeMeasurementPlan,
    ProblemFact,
    ProblemModelProposal,
    ProductApplicationService,
    ProductIntentProposal,
    ResourceBoundary,
    SourceReference,
    SQLiteProductRepository,
    StopCondition,
    SubmitOutcomeContractProposal,
    SubmitOutcomeMeasurementPlanProposal,
    SubmitProblemModelProposal,
    SubmitProductIntentProposal,
    SuccessIndicator,
    TargetOutcome,
)
from psyteardown.product.measurement import (
    MEASUREMENT_RUNTIME_EVENT_BLOCKED_REASON,
    MEASUREMENT_THRESHOLD_PLACEHOLDER,
    derive_measurement_plan_proposal,
    measurement_plan_blockers,
    measurement_plan_structure_errors,
)
from psyteardown.product.models import is_measurement_threshold_placeholder

NOW = datetime(2026, 9, 25, 9, 0, tzinfo=timezone.utc)


def _service(repository):
    counts: dict[str, int] = defaultdict(int)

    def next_id(prefix: str) -> str:
        counts[prefix] += 1
        return f"{prefix}-c2-{counts[prefix]}"

    return ProductApplicationService(repository, clock=lambda: NOW, id_factory=next_id)


def _confirmed_contract(service: ProductApplicationService):
    project = service.create_project(
        CreateProductProject(
            project_id="project-c2",
            name="Measurement plan test",
            actor="test-user",
            reason="start C2 test",
        )
    )
    source = SourceReference(source_type="user_input", source_id="c2-input")
    intent = service.submit_product_intent(
        SubmitProductIntentProposal(
            project_id=project.project_id,
            intent_id="intent-c2",
            actor="studio",
            reason="structure intent",
            proposal=ProductIntentProposal(
                desired_change="Protect a planned focus session",
                affected_people=["knowledge workers"],
                current_situation="Unplanned context switching interrupts work",
                source_refs=[source],
            ),
        )
    )
    confirmed_intent = service.confirm_product_intent(
        ConfirmProductIntent(
            project_id=project.project_id,
            intent_id=intent.intent_id,
            expected_revision=1,
            actor="test-user",
            reason="intent is correct",
        )
    )
    problem = service.submit_problem_model(
        SubmitProblemModelProposal(
            project_id=project.project_id,
            problem_model_id="problem-c2",
            actor="studio",
            reason="structure problem",
            proposal=ProblemModelProposal(
                intent_revision_id=confirmed_intent.revision_id,
                facts=[ProblemFact(
                    fact_id="fact-c2",
                    statement="The user reports unplanned switches",
                    source_refs=[source],
                )],
                competing_explanations=[
                    CompetingExplanation(
                        explanation_id="explanation-c2-notifications",
                        statement="Incoming notifications drive the switches",
                        supporting_fact_ids=("fact-c2",),
                        cheapest_falsification="Observe a session with notifications muted",
                    ),
                    CompetingExplanation(
                        explanation_id="explanation-c2-ambiguity",
                        statement="Ambiguous tasks drive voluntary switching",
                        supporting_fact_ids=("fact-c2",),
                        cheapest_falsification="Observe a session with one precommitted task",
                    ),
                ],
            ),
        )
    )
    confirmed_problem = service.confirm_problem_model(
        ConfirmProblemModel(
            project_id=project.project_id,
            problem_model_id=problem.problem_model_id,
            expected_revision=1,
            actor="test-user",
            reason="problem boundary is correct",
        )
    )
    contract = service.submit_outcome_contract(
        SubmitOutcomeContractProposal(
            project_id=project.project_id,
            outcome_contract_id="contract-c2",
            actor="studio",
            reason="structure outcome",
            proposal=OutcomeContractProposal(
                intent_revision_id=confirmed_intent.revision_id,
                problem_model_revision_id=confirmed_problem.revision_id,
                target_segments=["knowledge workers"],
                applicable_contexts=["self-directed desktop work"],
                target_outcomes=[TargetOutcome(
                    outcome_id="outcome-c2",
                    description="Complete a planned focus session",
                    indicator_ids=["indicator-c2"],
                )],
                success_indicators=[SuccessIndicator(
                    indicator_id="indicator-c2",
                    operational_definition="Unplanned switches during the session",
                    observation_method="Consented task-session observation",
                    desired_direction="decrease",
                    threshold_or_target=MEASUREMENT_THRESHOLD_PLACEHOLDER,
                    required_evidence="operational_result",
                )],
                prohibited_outcomes=[{
                    "prohibited_outcome_id": "prohibited-c2",
                    "description": "The user feels pressured by the product",
                    "severity": "strong_avoidance",
                    "detection_method": "Ask after the session",
                    "response": "pause and reframe",
                }],
                prohibited_outcomes_reviewed=True,
                resource_boundary=ResourceBoundary(
                    time_budget="one session",
                    data_boundary="no automatic activity collection",
                ),
                stop_conditions=[StopCondition(
                    condition_id="stop-c2",
                    condition="Perceived pressure increases",
                    action="pause",
                )],
                required_real_world_evidence=["operational_result"],
                minimum_delivery_maturity="runnable_prototype",
            ),
        )
    )
    confirmed_contract = service.confirm_outcome_contract(
        ConfirmOutcomeContract(
            project_id=project.project_id,
            outcome_contract_id=contract.outcome_contract_id,
            expected_revision=1,
            actor="test-user",
            reason="outcome boundary is correct",
        )
    )
    return project, confirmed_contract


def test_threshold_gate_rejects_blank_and_common_placeholder_variants():
    assert all(
        is_measurement_threshold_placeholder(value)
        for value in (
            "",
            "   ",
            "TBD",
            "To Be Determined",
            "target: to be determined by the team",
            "Must be set by a human before confirmation",
        )
    )
    assert not is_measurement_threshold_placeholder("at least 3 completed sessions")


def test_runtime_event_guardrails_must_be_explicitly_blocked():
    values = {
        "guardrail_id": "guardrail-runtime",
        "prohibited_outcome_id": "harm-1",
        "severity": "hard",
        "detection_method": "count hidden background events",
        "source_layer": "runtime_event",
        "response": "pause the trial",
    }
    with pytest.raises(ValueError, match="runtime_event guardrails must stay blocked"):
        MeasurementGuardrail(**values)

    blocked = MeasurementGuardrail(**values, blocked_reason=MEASUREMENT_RUNTIME_EVENT_BLOCKED_REASON)
    assert blocked.collectable is False
    assert blocked.evidence_ceiling == "observed"


def test_derivation_declares_source_layers_and_non_evidence_boundary():
    service = _service(InMemoryProductRepository())
    _, contract = _confirmed_contract(service)

    proposal = derive_measurement_plan_proposal(contract)

    assert proposal.outcome_contract_revision_id == contract.revision_id
    assert [measure.source_layer for measure in proposal.measures] == [
        "research_observation",
        "runtime_event",
    ]
    assert proposal.measures[0].primary is True
    assert proposal.measures[1].primary is False
    assert proposal.measures[1].blocked_reason == MEASUREMENT_RUNTIME_EVENT_BLOCKED_REASON
    assert "model_interpretation" not in {
        measure.source_layer for measure in proposal.measures
    }
    assert proposal.stop_condition_ids == ["stop-c2"]
    assert proposal.guardrails[0].prohibited_outcome_id == "prohibited-c2"


def test_structure_gate_rejects_incompatible_source_but_allows_editable_incompleteness():
    service = _service(InMemoryProductRepository())
    project, contract = _confirmed_contract(service)
    proposal = derive_measurement_plan_proposal(contract)
    bad = proposal.model_copy(update={
        "measures": [proposal.measures[0].model_copy(update={"source_layer": "software_check"})],
    })

    errors = measurement_plan_structure_errors(bad, contract)

    assert errors and "cannot produce operational_result" in errors[0]
    draft = service.derive_outcome_measurement_plan(
        DeriveOutcomeMeasurementPlan(
            project_id=project.project_id,
            actor="studio",
            reason="derive incomplete C2 plan",
        )
    )
    incomplete = proposal.model_copy(update={"stop_condition_ids": []})
    saved = service.submit_outcome_measurement_plan(
        SubmitOutcomeMeasurementPlanProposal(
            project_id=project.project_id,
            measurement_plan_id=draft.measurement_plan_id,
            expected_revision=draft.meta.revision,
            proposal=incomplete,
            actor="test-user",
            reason="test incomplete plan",
        )
    )
    assert any("stop condition" in item for item in measurement_plan_blockers(saved, contract))


def test_confirmation_gate_reports_blocked_primary_real_world_guardrail_and_stop_paths():
    service = _service(InMemoryProductRepository())
    _, contract = _confirmed_contract(service)
    proposal = derive_measurement_plan_proposal(contract)
    blocked_primary = proposal.measures[0].model_copy(update={
        "primary": True,
        "threshold_or_target": "at least 20% below baseline",
        "blocked_reason": "participant did not consent to observation",
    })
    blocked_secondary = proposal.measures[1].model_copy(update={
        "primary": False,
        "threshold_or_target": "no more than 3 switches",
    })
    plan = OutcomeMeasurementPlan(
        measurement_plan_id="measurement-plan-gates",
        revision_id="measurement-plan-gates.r1",
        meta=contract.meta.model_copy(update={"revision": 1}),
        project_id=contract.project_id,
        outcome_contract_revision_id=contract.revision_id,
        origin="human_revision",
        measures=(blocked_primary, blocked_secondary),
        guardrails=(),
        stop_condition_ids=(),
        sample_plan=proposal.sample_plan,
        observation_window=proposal.observation_window,
        consent_scope=proposal.consent_scope,
        withdrawal_policy=proposal.withdrawal_policy,
        dependencies=(
            DependencyRef(
                object_type="outcome_contract",
                object_id=contract.outcome_contract_id,
                revision=contract.meta.revision,
            ),
        ),
    )

    blockers = measurement_plan_blockers(plan, contract)

    assert any("requires operational_result but has no collectable measure" in item for item in blockers)
    assert any("primary measure indicator-c2-observed is blocked" in item for item in blockers)
    assert any("prohibited outcome prohibited-c2 has no guardrail" in item for item in blockers)
    assert any("stop condition stop-c2 is not part of the plan" in item for item in blockers)


def test_measurement_plan_revision_confirmation_and_contract_staleness():
    service = _service(InMemoryProductRepository())
    project, contract = _confirmed_contract(service)
    draft = service.derive_outcome_measurement_plan(
        DeriveOutcomeMeasurementPlan(
            project_id=project.project_id,
            actor="studio",
            reason="derive C2 plan",
        )
    )
    assert draft.status == "proposed"
    assert draft.measurement_plan_id.startswith("measurement-plan")
    assert service.get_project_view(project.project_id).measurement_plan_blockers

    proposal = derive_measurement_plan_proposal(contract)
    edited = proposal.model_copy(update={"measures": [
        proposal.measures[0].model_copy(update={"threshold_or_target": "at least 20% below baseline"}),
        proposal.measures[1].model_copy(update={"threshold_or_target": "no more than 3 switches"}),
    ]})
    revised = service.submit_outcome_measurement_plan(
        SubmitOutcomeMeasurementPlanProposal(
            project_id=project.project_id,
            measurement_plan_id=draft.measurement_plan_id,
            expected_revision=draft.meta.revision,
            proposal=edited,
            actor="test-user",
            reason="set a human threshold",
        )
    )
    assert revised.meta.revision == 2
    assert measurement_plan_blockers(revised, contract) == ()
    confirmed = service.confirm_outcome_measurement_plan(
        ConfirmOutcomeMeasurementPlan(
            project_id=project.project_id,
            measurement_plan_id=revised.measurement_plan_id,
            expected_revision=revised.meta.revision,
            actor="test-user",
            reason="measurement plan is executable",
        )
    )
    assert confirmed.status == "confirmed"
    assert confirmed.meta.revision == 3

    changed_contract_proposal = OutcomeContractProposal(
        **contract.model_dump(mode="python", exclude={
            "outcome_contract_id", "revision_id", "meta", "project_id", "status", "dependencies", "confirmation",
            "intent_revision_id", "problem_model_revision_id",
        }),
        intent_revision_id=contract.intent_revision_id,
        problem_model_revision_id=contract.problem_model_revision_id,
    )
    changed_contract = service.submit_outcome_contract(
        SubmitOutcomeContractProposal(
            project_id=project.project_id,
            outcome_contract_id=contract.outcome_contract_id,
            expected_revision=contract.meta.revision,
            proposal=changed_contract_proposal,
            actor="test-user",
            reason="adjust outcome boundary",
        )
    )
    impacts = service.get_project_view(project.project_id).recorded_impacts
    assert changed_contract.meta.revision == 3
    assert any(
        item.dependent_type == "outcome_measurement_plan"
        and item.impact == "stale"
        for item in impacts
    )


def test_measurement_plan_round_trips_through_sqlite(tmp_path):
    database = tmp_path / "c2.sqlite3"
    repository = SQLiteProductRepository(database)
    try:
        service = _service(repository)
        project, contract = _confirmed_contract(service)
        draft = service.derive_outcome_measurement_plan(
            DeriveOutcomeMeasurementPlan(
                project_id=project.project_id,
                actor="studio",
                reason="derive C2 plan",
            )
        )
        proposal = derive_measurement_plan_proposal(contract)
        edited = proposal.model_copy(update={
            "measures": [
                proposal.measures[0].model_copy(update={"threshold_or_target": "at least 20% below baseline"}),
                proposal.measures[1].model_copy(update={"threshold_or_target": "no more than 3 switches"}),
            ]
        })
        revised = service.submit_outcome_measurement_plan(
            SubmitOutcomeMeasurementPlanProposal(
                project_id=project.project_id,
                measurement_plan_id=draft.measurement_plan_id,
                expected_revision=1,
                proposal=edited,
                actor="test-user",
                reason="set threshold",
            )
        )
        confirmed = service.confirm_outcome_measurement_plan(
            ConfirmOutcomeMeasurementPlan(
                project_id=project.project_id,
                measurement_plan_id=revised.measurement_plan_id,
                expected_revision=2,
                actor="test-user",
                reason="confirm plan",
            )
        )
        assert confirmed.status == "confirmed"
    finally:
        repository.close()

    restarted_repository = SQLiteProductRepository(database)
    try:
        restarted = _service(restarted_repository)
        view = restarted.get_project_view("project-c2")
        assert view.outcome_measurement_plan is not None
        assert view.outcome_measurement_plan.status == "confirmed"
        assert view.outcome_measurement_plan.meta.revision == 3
        assert view.measurement_plan_blockers == ()
    finally:
        restarted_repository.close()
