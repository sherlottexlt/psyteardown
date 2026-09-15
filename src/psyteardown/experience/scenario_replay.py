"""Deterministic replay of the declared routine-intervention state machine.

Replay is a policy/test artifact.  It exercises control-flow invariants over
declared phases; it does not classify movement sensors or predict user intent,
consent, comfort or task performance.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from psyteardown.experience.models import ScenarioPolicy


ReplayEvent = Literal[
    "hazard_phase_entered",
    "routine_event_arrives",
    "safe_boundary_declared",
    "signal_completed",
    "reject_or_cancel",
    "no_response_timeout",
    "context_corrected",
    "new_independent_event",
]


class ScenarioReplayStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    phase_id: str = Field(min_length=1)
    event: ReplayEvent
    permission_valid: bool = True
    expected_state: str | None = None


class ScenarioReplayCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1)
    initial_state: Literal[
        "monitoring",
        "suppressed",
        "deferred",
        "private_signal",
        "awaiting_response",
        "terminated",
        "safe_boundary_review",
    ] = "monitoring"
    steps: tuple[ScenarioReplayStep, ...] = Field(min_length=1)


class ScenarioReplayInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transit-anchor-scenario-replay/v1"] = "transit-anchor-scenario-replay/v1"
    scenario_id: str = Field(min_length=1)
    policy_revision_id: str = Field(min_length=1)
    cases: tuple[ScenarioReplayCase, ...] = Field(min_length=1)


class ScenarioReplayStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    phase_id: str
    event: ReplayEvent
    state_before: str
    state_after: str
    policy_action: Literal["suppress", "defer", "allow"]
    feedback_modality: Literal["private_haptic", "visual", "none"]
    accepted: bool
    violations: tuple[str, ...] = ()


class ScenarioReplayCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    initial_state: str
    final_state: str
    status: Literal["pass", "violations"]
    steps: tuple[ScenarioReplayStepResult, ...]
    violations: tuple[str, ...] = ()


class ScenarioReplayReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transit-anchor-scenario-replay-report/v1"] = "transit-anchor-scenario-replay-report/v1"
    scenario_id: str
    policy_revision_id: str
    method: str
    evidence_level: Literal["none"] = "none"
    evidence_eligible: Literal[False] = False
    cases: tuple[ScenarioReplayCaseResult, ...]
    status: Literal["pass", "violations"]
    limitations: tuple[str, ...]


def _violation(message: str, violations: list[str], step_violations: list[str]) -> None:
    violations.append(message)
    step_violations.append(message)


def run_scenario_replay(policy: ScenarioPolicy, spec: ScenarioReplayInput) -> ScenarioReplayReport:
    """Replay control transitions against a frozen deterministic policy."""

    if policy.scenario_id != spec.scenario_id:
        raise ValueError("scenario replay and policy reference different scenarios")
    if policy.revision_id != spec.policy_revision_id:
        raise ValueError("scenario replay references a different policy revision")

    all_violations: list[str] = []
    case_results: list[ScenarioReplayCaseResult] = []
    for case in spec.cases:
        state = case.initial_state
        step_results: list[ScenarioReplayStepResult] = []
        case_violations: list[str] = []
        for step in case.steps:
            before = state
            decision = policy.evaluate(step.phase_id, permission_valid=step.permission_valid)
            step_violations: list[str] = []

            if step.event == "hazard_phase_entered":
                if state != "monitoring":
                    _violation(f"{case.trace_id}/{step.step_id}: hazard entry requires monitoring, got {state}", case_violations, step_violations)
                else:
                    state = "suppressed"
            elif step.event == "routine_event_arrives":
                if state not in {"monitoring", "suppressed", "deferred"}:
                    _violation(f"{case.trace_id}/{step.step_id}: routine event is not accepted in {state}", case_violations, step_violations)
                elif state == "suppressed":
                    state = "deferred"
                elif decision.action == "suppress":
                    state = "suppressed"
                elif decision.action == "defer":
                    state = "deferred"
                else:
                    state = "private_signal"
            elif step.event == "safe_boundary_declared":
                if state != "deferred":
                    _violation(f"{case.trace_id}/{step.step_id}: safe boundary requires deferred event, got {state}", case_violations, step_violations)
                elif decision.action == "allow":
                    state = "private_signal"
                elif decision.action == "suppress":
                    _violation(f"{case.trace_id}/{step.step_id}: safe boundary still has a suppress policy", case_violations, step_violations)
                else:
                    state = "deferred"
            elif step.event == "signal_completed":
                if state != "private_signal":
                    _violation(f"{case.trace_id}/{step.step_id}: signal completion requires private_signal, got {state}", case_violations, step_violations)
                else:
                    state = "awaiting_response"
            elif step.event in {"reject_or_cancel", "no_response_timeout"}:
                if state != "awaiting_response":
                    _violation(f"{case.trace_id}/{step.step_id}: {step.event} requires awaiting_response, got {state}", case_violations, step_violations)
                else:
                    state = "terminated"
            elif step.event == "context_corrected":
                if state != "awaiting_response":
                    _violation(f"{case.trace_id}/{step.step_id}: context correction requires awaiting_response, got {state}", case_violations, step_violations)
                else:
                    state = "safe_boundary_review"
            elif step.event == "new_independent_event":
                if state != "terminated":
                    _violation(f"{case.trace_id}/{step.step_id}: new event requires terminated state, got {state}", case_violations, step_violations)
                elif not step.permission_valid or decision.action != "allow":
                    _violation(f"{case.trace_id}/{step.step_id}: new event requires valid permission and allow policy", case_violations, step_violations)
                else:
                    state = "monitoring"

            if step.expected_state is not None and state != step.expected_state:
                _violation(f"{case.trace_id}/{step.step_id}: expected {step.expected_state}, got {state}", case_violations, step_violations)
            if decision.action == "suppress" and step.event in {"routine_event_arrives", "safe_boundary_declared"} and state == "private_signal":
                _violation(f"{case.trace_id}/{step.step_id}: suppress policy cannot open a private signal", case_violations, step_violations)

            step_results.append(
                ScenarioReplayStepResult(
                    step_id=step.step_id,
                    phase_id=step.phase_id,
                    event=step.event,
                    state_before=before,
                    state_after=state,
                    policy_action=decision.action,
                    feedback_modality=decision.feedback_modality,
                    accepted=not step_violations,
                    violations=tuple(step_violations),
                )
            )
            all_violations.extend(step_violations)
        case_results.append(
            ScenarioReplayCaseResult(
                trace_id=case.trace_id,
                initial_state=case.initial_state,
                final_state=state,
                status="violations" if case_violations else "pass",
                steps=tuple(step_results),
                violations=tuple(case_violations),
            )
        )

    return ScenarioReplayReport(
        scenario_id=spec.scenario_id,
        policy_revision_id=spec.policy_revision_id,
        method="deterministic replay of declared routine state transitions; no sensor classification or user outcome data",
        cases=tuple(case_results),
        status="violations" if all_violations else "pass",
        limitations=(
            "Replay verifies control-flow invariants only; it does not establish discoverability, comfort, haptic detection, privacy leakage or task performance.",
            "Movement phases and permission validity are declared test inputs, not inferred user intent or consent.",
            "A pass is a software-policy result and is never prototype or user evidence.",
        ),
    )


def render_scenario_replay_markdown(report: ScenarioReplayReport) -> str:
    lines = [
        "# Transit Anchor — deterministic scenario replay",
        "",
        f"- **Scenario:** `{report.scenario_id}`",
        f"- **Policy:** `{report.policy_revision_id}`",
        f"- **Status:** `{report.status}`",
        "- **Evidence level:** `none`",
        "- **Evidence eligible:** `false`",
        "",
        "> This replay checks declared state transitions only. It is not a sensor result, user study or prototype evidence.",
    ]
    for case in report.cases:
        lines.extend(["", f"## Trace `{case.trace_id}`", "", f"- **Status:** `{case.status}`", f"- **Final state:** `{case.final_state}`", "", "| Step | Event | Phase | Policy | State transition | Result |", "| --- | --- | --- | --- | --- | --- |"])
        for step in case.steps:
            result = "pass" if step.accepted else "; ".join(step.violations)
            lines.append(f"| {step.step_id} | {step.event} | {step.phase_id} | {step.policy_action} | {step.state_before} → {step.state_after} | {result} |")
        if case.violations:
            lines.extend(["", "Violations:", "", *[f"- {item}" for item in case.violations]])
    lines.extend(["", "## Limitations", "", *[f"- {item}" for item in report.limitations]])
    return "\n".join(lines)
