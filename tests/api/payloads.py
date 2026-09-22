"""Valid HTTP proposal payloads shared by Product Studio API tests."""

from typing import Any


def source() -> dict[str, str]:
    return {"source_type": "user_input", "source_id": "message-1"}


def intent_proposal() -> dict[str, Any]:
    return {
        "desired_change": "Protect focused work without surveilling the user",
        "affected_people": ["independent knowledge workers"],
        "current_situation": "Frequent context switching during desktop work",
        "explicit_non_goals": ["score personal productivity"],
        "known_constraints": ["local-first"],
        "resource_preferences": [],
        "source_refs": [source()],
    }


def problem_proposal(intent_revision_id: str) -> dict[str, Any]:
    return {
        "intent_revision_id": intent_revision_id,
        "facts": [
            {
                "fact_id": "fact-1",
                "statement": "The user reports unplanned context switches",
                "source_refs": [source()],
            }
        ],
        "assumptions": [],
        "unknowns": [],
        "competing_explanations": [
            {
                "explanation_id": "explanation-1",
                "statement": "Incoming notifications drive the switches",
                "supporting_fact_ids": ["fact-1"],
                "contradicting_fact_ids": [],
                "cheapest_falsification": (
                    "Observe a session with notifications muted"
                ),
            },
            {
                "explanation_id": "explanation-2",
                "statement": "Ambiguous tasks drive voluntary switching",
                "supporting_fact_ids": ["fact-1"],
                "contradicting_fact_ids": [],
                "cheapest_falsification": (
                    "Observe a session with a precommitted task list"
                ),
            },
        ],
        "stakeholder_tensions": [],
    }


def contract_proposal(
    intent_revision_id: str, problem_revision_id: str
) -> dict[str, Any]:
    return {
        "intent_revision_id": intent_revision_id,
        "problem_model_revision_id": problem_revision_id,
        "target_segments": ["independent knowledge workers"],
        "applicable_contexts": ["self-directed desktop work"],
        "target_outcomes": [
            {
                "outcome_id": "outcome-1",
                "description": (
                    "Complete chosen focus tasks with fewer involuntary switches"
                ),
                "indicator_ids": ["indicator-1"],
            }
        ],
        "success_indicators": [
            {
                "indicator_id": "indicator-1",
                "operational_definition": (
                    "Unplanned task switches in a declared focus session"
                ),
                "observation_method": "Consented task-session review",
                "desired_direction": "decrease",
                "threshold_or_target": "below the user's unaided baseline",
                "required_evidence": "real_user_observation",
            }
        ],
        "prohibited_outcomes": [],
        "prohibited_outcomes_reviewed": True,
        "resource_boundary": {
            "time_budget": "first prototype within one day",
            "data_boundary": "no hidden activity collection",
            "explicit_unknowns": [],
        },
        "stop_conditions": [
            {
                "condition_id": "stop-1",
                "condition": "Perceived pressure increases",
                "action": "reframe",
            }
        ],
        "minimum_delivery_maturity": "concept",
        "required_real_world_evidence": ["one consented real task session"],
    }


def thesis_proposal(
    problem_revision_id: str, contract_revision_id: str
) -> dict[str, Any]:
    return {
        "problem_model_revision_id": problem_revision_id,
        "outcome_contract_revision_id": contract_revision_id,
        "name": "Intentional interruption gate",
        "product_promise": (
            "Delay nonessential interruptions until a chosen boundary"
        ),
        "differentiation": (
            "Changes interruption timing rather than scoring the user"
        ),
        "realization_modes": ["software"],
        "mechanism_hypotheses": [
            {
                "mechanism_id": "mechanism-1",
                "condition": "A bounded focus task has been declared",
                "proposed_intervention": "Queue nonessential interruptions",
                "expected_change": "Fewer involuntary switches",
                "uncertainty": "The queue could increase anxiety",
                "evidence_refs": [],
            }
        ],
        "falsifiable_predictions": [
            {
                "prediction_id": "prediction-1",
                "prediction": "Unplanned switches decrease",
                "failure_observation": (
                    "Switches do not decrease or pressure rises"
                ),
                "cheapest_test": "One reversible local prototype session",
            }
        ],
        "validation_strategy": [
            {
                "validation_step_id": "validation-1",
                "question": "Can queued items be recovered without losing trust?",
                "method": (
                    "Scripted browser task followed by a consented session"
                ),
                "evidence_level": "real_user_observation",
                "pass_condition": (
                    "No missed critical item and acceptable perceived control"
                ),
                "estimated_cost": "one prototype and one session",
            }
        ],
        "key_unknowns": ["Effect of delayed items on anxiety"],
        "key_risks": ["Suppressing an urgent item"],
        "delivery_estimate": {
            "initial_delivery_cost": "one web prototype",
            "operating_cost": "local processing",
            "maintenance_burden": "browser integration updates",
        },
    }
