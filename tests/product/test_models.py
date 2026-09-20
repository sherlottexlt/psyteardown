import pytest
from pydantic import ValidationError

from psyteardown.experience.models import DependencyRef
from psyteardown.product import (
    HumanConfirmation,
    ProblemFact,
    ProductIntent,
    SourceReference,
    ThesisDisposition,
)


def test_product_intent_is_frozen_and_requires_source(proposed_intent):
    with pytest.raises(ValidationError):
        proposed_intent.desired_change = "silently changed"

    payload = proposed_intent.model_dump(mode="python")
    payload["source_refs"] = ()
    with pytest.raises(ValidationError):
        ProductIntent.model_validate(payload)


def test_confirmed_intent_cannot_be_constructed_without_confirmation(proposed_intent):
    payload = proposed_intent.model_dump(mode="python")
    payload["status"] = "confirmed"
    with pytest.raises(ValidationError, match="human confirmation"):
        ProductIntent.model_validate(payload)


def test_problem_fact_requires_at_least_one_source():
    with pytest.raises(ValidationError):
        ProblemFact(fact_id="fact-1", statement="An alleged fact", source_refs=())


def test_confirmed_problem_requires_multiple_explanations(
    proposed_problem, occurred_at
):
    payload = proposed_problem.model_dump(mode="python")
    payload.update(
        {
            "status": "confirmed",
            "competing_explanations": payload["competing_explanations"][:1],
            "confirmation": HumanConfirmation(
                confirmed_by="human-1",
                confirmed_at=occurred_at,
                rationale="reviewed",
            ),
        }
    )
    with pytest.raises(ValidationError, match="two competing explanations"):
        proposed_problem.__class__.model_validate(payload)


def test_problem_explanation_cannot_reference_unknown_fact(proposed_problem):
    payload = proposed_problem.model_dump(mode="python")
    payload["competing_explanations"][0]["supporting_fact_ids"] = ("missing",)
    with pytest.raises(ValidationError, match="unknown facts"):
        proposed_problem.__class__.model_validate(payload)


def test_outcome_contract_rejects_unknown_indicator(proposed_contract):
    payload = proposed_contract.model_dump(mode="python")
    payload["target_outcomes"][0]["indicator_ids"] = ("missing",)
    with pytest.raises(ValidationError, match="unknown indicators"):
        proposed_contract.__class__.model_validate(payload)


def test_confirmed_outcome_contract_requires_reviewed_boundaries(
    proposed_contract, occurred_at
):
    payload = proposed_contract.model_dump(mode="python")
    payload.update(
        {
            "status": "confirmed",
            "prohibited_outcomes_reviewed": False,
            "confirmation": HumanConfirmation(
                confirmed_by="human-1",
                confirmed_at=occurred_at,
                rationale="approve contract",
            ),
        }
    )
    with pytest.raises(ValidationError, match="prohibited-outcome review"):
        proposed_contract.__class__.model_validate(payload)


def test_product_thesis_requires_problem_and_contract_dependencies(proposed_thesis):
    payload = proposed_thesis.model_dump(mode="python")
    payload["dependencies"] = (
        DependencyRef(object_type="problem_model", object_id="problem-1", revision=2),
        DependencyRef(object_type="product_intent", object_id="intent-1", revision=2),
    )
    with pytest.raises(ValidationError, match="outcome_contract"):
        proposed_thesis.__class__.model_validate(payload)


def test_system_cannot_construct_selected_thesis_without_authorization(
    proposed_thesis, occurred_at
):
    payload = proposed_thesis.model_dump(mode="python")
    payload.update(
        {
            "status": "selected",
            "disposition": ThesisDisposition(
                action="selected",
                decided_by="system",
                actor_type="system",
                decided_at=occurred_at,
                rationale="highest model score",
            ),
        }
    )
    with pytest.raises(ValidationError, match="human decision or explicit authorization"):
        proposed_thesis.__class__.model_validate(payload)


def test_source_reference_keeps_model_proposals_distinct_from_evidence():
    source = SourceReference(source_type="model_proposal", source_id="attempt-1")
    assert source.source_type == "model_proposal"
    assert source.source_type != "evidence"
