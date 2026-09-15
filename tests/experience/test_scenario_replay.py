import json
from pathlib import Path

from psyteardown.experience import (
    ScenarioReplayInput,
    ScenarioPolicy,
    run_scenario_replay,
)


def test_round2_scenario_replay_passes_declared_control_paths():
    policy = ScenarioPolicy.model_validate_json(
        Path("output/experience/transit-anchor-strap-release-r1/scenario-policy-r2-replay.json").read_text(encoding="utf-8")
    )
    spec = ScenarioReplayInput.model_validate_json(
        Path("examples/transit-anchor-round2-scenario-replay.json").read_text(encoding="utf-8")
    )
    report = run_scenario_replay(policy, spec)

    assert report.status == "pass"
    assert report.evidence_level == "none"
    assert report.evidence_eligible is False
    assert {case.final_state for case in report.cases} == {"monitoring", "terminated", "safe_boundary_review", "suppressed"}
    assert all(step.accepted for case in report.cases for step in case.steps)


def test_replay_rejects_stale_policy_revision():
    policy = ScenarioPolicy.model_validate_json(
        Path("output/experience/transit-anchor-strap-release-r1/scenario-policy-r2-replay.json").read_text(encoding="utf-8")
    )
    payload = json.loads(Path("examples/transit-anchor-round2-scenario-replay.json").read_text(encoding="utf-8"))
    payload["policy_revision_id"] = "scenario-policy-stale.r1"
    spec = ScenarioReplayInput.model_validate(payload)

    try:
        run_scenario_replay(policy, spec)
    except ValueError as exc:
        assert "different policy revision" in str(exc)
    else:
        raise AssertionError("stale policy revision should be rejected")
