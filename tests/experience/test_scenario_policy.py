import pytest

from psyteardown.experience import FutureMovementScenarioInput, build_movement_scenarios, build_scenario_policy
from psyteardown.experience import InitialDesignRequest, generate_initial_design_batch, SQLiteExperienceRepository


def test_scenario_policy_suppresses_hazards_and_bounds_allow_path():
    scenarios = build_movement_scenarios([FutureMovementScenarioInput(
        scenario_id="s", name="transfer", narrative="test",
        phases=[
            {"phase_id": "safe", "movement_state": "stationary", "posture": "standing", "hands_available": "both", "visual_attention": "available", "ambient_motion": "low", "social_visibility": "public", "device_relation": "worn_wrist"},
            {"phase_id": "hazard", "movement_state": "walking", "posture": "walking_posture", "hands_available": "none", "visual_attention": "intermittent", "ambient_motion": "high", "social_visibility": "public", "device_relation": "worn_wrist", "hazards": ["stairs"]},
        ], task_goal="transfer",
    )])
    policy = build_scenario_policy(scenarios[0])
    assert policy.decision_for("safe").action == "allow"
    assert policy.decision_for("safe").response_timeout_ms > 0
    assert policy.decision_for("hazard").action == "suppress"
    assert policy.decision_for("hazard").feedback_modality == "none"
    assert policy.decision_for("safe", permission_valid=False).action == "suppress"


def test_policy_rejects_unknown_or_critical_event():
    scenario = build_movement_scenarios([FutureMovementScenarioInput(
        scenario_id="s", name="x", narrative="x", phases=[
            {"phase_id": "p", "movement_state": "stationary", "posture": "standing", "hands_available": "both", "visual_attention": "available", "ambient_motion": "low", "social_visibility": "private", "device_relation": "worn_wrist"}
        ], task_goal="x",
    )])[0]
    policy = build_scenario_policy(scenario)
    with pytest.raises(ValueError):
        policy.decision_for("missing")
    with pytest.raises(ValueError):
        policy.decision_for("p", event_type="critical")


def test_initial_design_batch_persists_policies_and_binds_models(tmp_path):
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        batch = generate_initial_design_batch(InitialDesignRequest(goal="test", target_segment="users", context="lab", criteria=[{"criterion_id": "c", "name": "Control", "operational_definition": "can stop"}]), repository=repo)
        assert batch.scenario_policies
        assert all(model.scenario_policy_revision_ids for model in batch.progressive_models)
        assert len(repo.list_revisions("scenario_policy")) == len(batch.scenario_policies)
