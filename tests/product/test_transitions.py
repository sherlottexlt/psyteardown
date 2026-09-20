import pytest
from pydantic import ValidationError

from psyteardown.experience.models import DependencyRef, DomainStateError
from psyteardown.product import (
    assess_revision_impacts,
    confirm_outcome_contract,
    confirm_problem_model,
    confirm_product_intent,
    revise_product_intent,
    transition_product_thesis,
)


def test_human_confirmation_creates_a_new_intent_revision(
    proposed_intent, occurred_at
):
    confirmed = confirm_product_intent(
        proposed_intent,
        new_revision_id="intent-1.r2",
        actor="user-li",
        reason="desired change and non-goals are correct",
        occurred_at=occurred_at,
    )

    assert confirmed.intent_id == proposed_intent.intent_id
    assert confirmed.revision_id == "intent-1.r2"
    assert confirmed.meta.revision == 2
    assert confirmed.meta.parent_revision_id == proposed_intent.revision_id
    assert confirmed.status == "confirmed"
    assert confirmed.confirmation.confirmed_by == "user-li"


def test_revising_confirmed_intent_returns_to_unconfirmed_proposal(
    proposed_intent, occurred_at
):
    confirmed = confirm_product_intent(
        proposed_intent,
        new_revision_id="intent-1.r2",
        actor="user-li",
        reason="confirmed",
        occurred_at=occurred_at,
    )
    revised = revise_product_intent(
        confirmed,
        {"known_constraints": ("local-first", "no activity surveillance")},
        new_revision_id="intent-1.r3",
        actor="user-li",
        reason="clarified privacy boundary",
        occurred_at=occurred_at,
    )

    assert revised.intent_id == confirmed.intent_id
    assert revised.status == "proposed"
    assert revised.confirmation is None
    assert revised.meta.parent_revision_id == confirmed.revision_id
    assert revised.meta.revision == 3


def test_revision_cannot_replace_stable_identity(proposed_intent, occurred_at):
    with pytest.raises(DomainStateError, match="identity or workflow fields"):
        revise_product_intent(
            proposed_intent,
            {"intent_id": "other-intent"},
            new_revision_id="intent-1.r2",
            actor="user-li",
            reason="invalid identity change",
            occurred_at=occurred_at,
        )


def test_problem_and_contract_confirmation_run_semantic_gates(
    proposed_problem, proposed_contract, occurred_at
):
    problem = confirm_problem_model(
        proposed_problem,
        new_revision_id="problem-1.r2",
        actor="researcher-li",
        reason="facts and alternatives reviewed",
        occurred_at=occurred_at,
    )
    contract = confirm_outcome_contract(
        proposed_contract,
        new_revision_id="contract-1.r2",
        actor="user-li",
        reason="value and evidence boundaries approved",
        occurred_at=occurred_at,
    )

    assert problem.status == "confirmed"
    assert contract.status == "confirmed"
    assert contract.confirmation.confirmed_by == "user-li"


def test_confirmed_snapshot_cannot_be_confirmed_again(proposed_intent, occurred_at):
    confirmed = confirm_product_intent(
        proposed_intent,
        new_revision_id="intent-1.r2",
        actor="user-li",
        reason="confirmed",
        occurred_at=occurred_at,
    )
    with pytest.raises(DomainStateError, match="only a proposed snapshot"):
        confirm_product_intent(
            confirmed,
            new_revision_id="intent-1.r3",
            actor="user-li",
            reason="confirm again",
            occurred_at=occurred_at,
        )


def test_system_selection_requires_explicit_authorization(
    proposed_thesis, occurred_at
):
    with pytest.raises(ValidationError, match="human decision or explicit authorization"):
        transition_product_thesis(
            proposed_thesis,
            "selected",
            new_revision_id="thesis-1.r2",
            actor="studio",
            actor_type="system",
            reason="continue cheapest path",
            occurred_at=occurred_at,
        )

    selected = transition_product_thesis(
        proposed_thesis,
        "selected",
        new_revision_id="thesis-1.r2",
        actor="studio",
        actor_type="system",
        reason="continue user-authorized cheapest path",
        occurred_at=occurred_at,
        authorization_ref="decision-42",
    )
    assert selected.status == "selected"
    assert selected.disposition.authorization_ref == "decision-42"


def test_rejected_thesis_is_terminal_without_a_new_proposal(
    proposed_thesis, occurred_at
):
    rejected = transition_product_thesis(
        proposed_thesis,
        "rejected",
        new_revision_id="thesis-1.r2",
        actor="user-li",
        actor_type="human",
        reason="violates the no-surveillance boundary",
        occurred_at=occurred_at,
    )
    with pytest.raises(DomainStateError, match="invalid product thesis transition"):
        transition_product_thesis(
            rejected,
            "exploring",
            new_revision_id="thesis-1.r3",
            actor="studio",
            actor_type="system",
            reason="silent restart",
            occurred_at=occurred_at,
        )


def test_upstream_change_returns_impacts_without_mutating_dependents(
    proposed_problem, proposed_contract, proposed_thesis
):
    old_intent = DependencyRef(
        object_type="product_intent", object_id="intent-1", revision=2
    )
    impacts = assess_revision_impacts(
        old_intent, (proposed_problem, proposed_contract, proposed_thesis)
    )

    assert [(item.dependent_type, item.impact) for item in impacts] == [
        ("problem_model", "review_required"),
        ("outcome_contract", "stale"),
    ]
    assert proposed_problem.status == "proposed"
    assert proposed_contract.status == "proposed"
    assert proposed_thesis.status == "proposed"
