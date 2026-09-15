"""Versioned portfolio projection for the experience-design workflow.

The JSON artifact is the durable source for a case study.  Markdown is a
human-readable derivative, generated from the same snapshot so a portfolio
does not drift away from revisions, patches or provider assets.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from psyteardown.experience.models import (
    BoundaryModel,
    DesignBrief,
    DesignCandidate,
    DesignToolRun,
    ProgressiveDesignModel,
    VariablePatch,
)
from psyteardown.experience.mobility import build_scenario_policy


class PortfolioProductSnapshot(BoundaryModel):
    candidate_revision_id: str
    model_revision_id: str | None = None
    title: str
    form_factor: str | None = None
    silhouette: str | None = None
    body_placement: str | None = None
    attachment_strategy: str | None = None
    contact_area: str | None = None
    mass_distribution: str | None = None
    feedback_modality: str | None = None
    feedback_timing: str | None = None
    visible_state: str | None = None
    cancel_action: str | None = None
    declared_unknowns: list[str] = Field(default_factory=list)


class PortfolioChange(BoundaryModel):
    change_id: str
    sequence: int = Field(ge=1)
    kind: Literal["baseline", "variable_patch", "visual_asset", "validation_plan"]
    title: str
    summary: str
    parent_candidate_revision_id: str | None = None
    parent_model_revision_id: str | None = None
    candidate_revision_id: str | None = None
    model_revision_id: str | None = None
    patch_revision_ids: list[str] = Field(default_factory=list)
    graphic_asset_refs: list[str] = Field(default_factory=list)
    review_view_refs: dict[str, str] = Field(default_factory=dict)
    status: Literal["draft", "confirmed", "planned", "exploratory", "observed", "supported", "replicated"]
    evidence_boundary: str


class StateTransition(BoundaryModel):
    from_state: str
    event: str
    guard: str
    action: str
    to_state: str
    user_control_boundary: str


class ScenarioStateMachine(BoundaryModel):
    machine_id: str
    scenario_id: str
    name: str
    purpose: str
    initial_state: str
    states: list[str]
    transitions: list[StateTransition]
    invariants: list[str]
    out_of_scope: list[str]


class PrototypeMeasure(BoundaryModel):
    measure_id: str
    question: str
    conditions: list[str]
    metric: str
    acceptance_boundary: str
    confounds: list[str]
    evidence_level_before_test: Literal["none"] = "none"


class PrototypeValidationProtocol(BoundaryModel):
    protocol_id: str
    title: str
    objective: str
    prototype_boundary: str
    participants_and_context: str
    measures: list[PrototypeMeasure]
    stopping_conditions: list[str]
    outcomes_not_claimed: list[str]
    status: Literal["planned", "exploratory", "observed", "supported", "replicated"] = "planned"
    protocol_revision: str = "v1"


class PortfolioCaseStudy(BoundaryModel):
    schema_version: Literal["portfolio-case-study/v1"] = "portfolio-case-study/v1"
    case_id: str
    title: str
    brief_revision_id: str
    generated_from: str
    design_challenge: str
    design_direction: str
    changes: list[PortfolioChange]
    current_product_snapshot: PortfolioProductSnapshot
    scenario_state_machine: ScenarioStateMachine
    prototype_validation_protocol: PrototypeValidationProtocol
    portfolio_boundary: str
    evidence_workflow: dict[str, object] = Field(default_factory=dict)
    executable_scenario_policy: dict[str, object] | None = None
    scenario_policy_revisions: list[str] = Field(default_factory=list)
    virtual_validation: dict[str, object] | None = None
    scenario_replay: dict[str, object] | None = None


def _snapshot(candidate: DesignCandidate, model: ProgressiveDesignModel | None) -> PortfolioProductSnapshot:
    shape = candidate.design.shape if candidate.design else candidate.shape
    values = {value.variable_id: value.display_value for value in candidate.variables}
    return PortfolioProductSnapshot(
        candidate_revision_id=candidate.candidate_revision_id,
        model_revision_id=model.revision_id if model else None,
        title=candidate.design.title if candidate.design else candidate.name,
        form_factor=shape.form_factor if shape else None,
        silhouette=shape.silhouette if shape else None,
        body_placement=shape.body_placement if shape else values.get("wearable.body_placement"),
        attachment_strategy=shape.attachment_strategy if shape else values.get("wearable.attachment_strategy", values.get("wearable.attachment")),
        contact_area=shape.contact_area if shape else values.get("wearable.contact_area"),
        mass_distribution=shape.mass_distribution if shape else values.get("wearable.mass_distribution"),
        feedback_modality=shape.feedback_modality if shape else values.get("feedback.modality"),
        feedback_timing=shape.feedback_timing if shape else values.get("feedback.timing"),
        visible_state=shape.visible_state if shape else values.get("device.visible_state"),
        cancel_action=values.get("control.cancel_action"),
        declared_unknowns=list(dict.fromkeys(candidate.unknowns + (candidate.design.declared_unknowns if candidate.design else ()))),
    )


def default_transit_state_machine(scenario_id: str = "crowded-transit-transfer") -> ScenarioStateMachine:
    """State machine for routine intervention; it never infers consent."""

    return ScenarioStateMachine(
        machine_id="transit-anchor-routine-intervention/v1",
        scenario_id=scenario_id,
        name="Crowded transit routine intervention",
        purpose="Suppress routine AI intervention during movement hazards while preserving a bounded, private recovery path.",
        initial_state="monitoring",
        states=["monitoring", "suppressed", "deferred", "private_signal", "awaiting_response", "terminated", "safe_boundary_review"],
        transitions=[
            StateTransition(from_state="monitoring", event="hazard_phase_entered", guard="doors, stairs, crossing or high-motion transit is declared", action="do not present routine content", to_state="suppressed", user_control_boundary="movement state does not imply intent, consent or attention"),
            StateTransition(from_state="suppressed", event="routine_event_arrives", guard="hazard remains declared", action="record only minimal event metadata and defer", to_state="deferred", user_control_boundary="no public output and no escalation"),
            StateTransition(from_state="deferred", event="safe_boundary_declared", guard="hazard no longer declared and intervention permission remains valid", action="offer one private bounded signal", to_state="private_signal", user_control_boundary="safe boundary is not consent; user may still reject or ignore"),
            StateTransition(from_state="private_signal", event="signal_completed", guard="routine event", action="open one bounded response window", to_state="awaiting_response", user_control_boundary="no visual or two-handed response is required"),
            StateTransition(from_state="awaiting_response", event="reject_or_cancel", guard="guarded control is reachable", action="stop event and suppress ordinary re-intervention in scope", to_state="terminated", user_control_boundary="cancellation is immediate and local"),
            StateTransition(from_state="awaiting_response", event="no_response_timeout", guard="response window expires", action="terminate with no implicit consent and no escalation", to_state="terminated", user_control_boundary="silence is not acceptance"),
            StateTransition(from_state="awaiting_response", event="context_corrected", guard="user indicates an incorrect context", action="stop current event and require new permission decision", to_state="safe_boundary_review", user_control_boundary="correction overrides the current inference"),
            StateTransition(from_state="terminated", event="new_independent_event", guard="new permission and no active hazard", action="return to monitoring", to_state="monitoring", user_control_boundary="previous response is not generalized beyond scope"),
        ],
        invariants=[
            "Routine intervention never uses public audio for private content.",
            "No-response ends a routine event; it never grants consent.",
            "Hazard, pose, route and movement state are context inputs, not evidence of intent or emotion.",
            "Rejection and correction do not trigger ordinary escalation.",
            "When hands are unavailable, the system relies on suppression or timeout rather than pretending a physical control is reachable.",
        ],
        out_of_scope=["critical-event policy", "emotion or health inference", "measured haptic detectability", "production sensor classifier accuracy"],
    )


def default_transit_validation_protocol() -> PrototypeValidationProtocol:
    return PrototypeValidationProtocol(
        protocol_id="transit-anchor-physical-validation/v1",
        title="Transit Anchor physical prototype validation",
        objective="Test whether the declared wrist form preserves bounded control and low interruption under plausible crowded-transit movement conditions.",
        prototype_boundary="This is a test plan, not evidence that a render, CAD blockout or design declaration meets any target.",
        participants_and_context="Consented adult participants perform controlled standing-transit, handrail, bag-carrying, sleeve and walking tasks; no road-crossing or live transit hazard is required for the first protocol.",
        measures=[
            PrototypeMeasure(measure_id="fit-displacement", question="Does the device slip or rotate under declared movements?", conditions=["standing vibration proxy", "handrail grip", "bag carry", "sleeve and sweat proxy"], metric="displacement and rotation relative to initial marked position", acceptance_boundary="Pre-register a tolerable displacement/rotation threshold before data collection; do not derive it from the render.", confounds=["wrist circumference", "strap tension", "sleeve friction", "sweat proxy", "movement intensity"]),
            PrototypeMeasure(measure_id="false-activation", question="Does gripping or incidental contact trigger guarded controls?", conditions=["handrail grip", "bag handle grip", "body contact proxy"], metric="false activations per task and per controlled exposure time", acceptance_boundary="Compare against a pre-registered maximum false-activation rate.", confounds=["control guard geometry", "activation force", "gloves", "hand size", "task instruction"]),
            PrototypeMeasure(measure_id="stop-path", question="Can a reachable user perform reject/stop without visual search?", conditions=["one hand free", "intermittent hand availability", "attention-divided task"], metric="completion rate, completion time and erroneous activation", acceptance_boundary="Pre-register success and time bounds; hands-unavailable trials test suppression/timeout policy rather than control reachability.", confounds=["dominant hand", "familiarization", "tactile cue learning", "sleeve coverage"]),
            PrototypeMeasure(measure_id="haptic-detectability", question="Is the private haptic pattern detectable without demanding visual attention?", conditions=["vibration proxy", "walking", "sleeve coverage", "sweat proxy"], metric="hit rate, false alarm rate and response time", acceptance_boundary="Pre-register a detection criterion and distinguish non-detection from rejection.", confounds=["motor placement", "strap tension", "ambient vibration", "hearing/vision distraction", "skin contact"]),
            PrototypeMeasure(measure_id="contact-boundary", question="Does the declared contact geometry create observable pressure, heat or irritation signals in the short protocol?", conditions=["short wear", "movement task", "sleeve coverage"], metric="participant-reported discomfort plus measured surface/skin-adjacent temperature where safely instrumented", acceptance_boundary="Exploratory safety screen only until duration, measurement method and threshold are pre-registered.", confounds=["skin sensitivity", "ambient temperature", "material finish", "wear duration", "individual fit"]),
            PrototypeMeasure(measure_id="privacy-observability", question="Can bystanders infer private content from routine feedback?", conditions=["nearby observer", "private haptic", "wearer-facing state edge"], metric="observer identification of state versus private content", acceptance_boundary="Pre-register acceptable content-identification rate; state-legibility and content leakage are analyzed separately.", confounds=["lighting", "observer distance", "display brightness", "instruction wording"]),
        ],
        stopping_conditions=["Stop an individual session on discomfort, skin irritation, distress or a participant request.", "Do not test the routine intervention flow in live road-crossing, vehicle-door or stair hazards in this first protocol.", "Pause the protocol if a control failure removes the local stop path."],
        outcomes_not_claimed=["long-term comfort", "medical safety", "ingress protection", "manufacturing durability", "real-world crash or injury reduction", "user intent, emotion or consent inference"],
    )


def build_portfolio_case_study(
    brief: DesignBrief,
    candidates: list[DesignCandidate],
    models: list[ProgressiveDesignModel],
    patches: list[VariablePatch],
    tool_runs: list[DesignToolRun],
    *,
    case_id: str = "transit-anchor",
    prototype_runs: list[object] | None = None,
    observations: list[object] | None = None,
    evidence_reviews: list[object] | None = None,
    validation_protocol: PrototypeValidationProtocol | None = None,
    scenario_policy: object | None = None,
    external_assets: list[object] | None = None,
    observation_drafts: list[object] | None = None,
    confirmed_observations: list[object] | None = None,
    virtual_validation: object | None = None,
    scenario_replay: object | None = None,
) -> PortfolioCaseStudy:
    """Build a bounded portfolio projection from immutable persisted records."""

    by_revision = {candidate.candidate_revision_id: candidate for candidate in candidates}
    model_by_candidate: dict[str, ProgressiveDesignModel] = {}
    model_by_revision: dict[str, ProgressiveDesignModel] = {}
    for model in models:
        model_by_revision[model.revision_id] = model
        current = model_by_candidate.get(model.candidate_revision_id)
        if current is None or model.meta.revision > current.meta.revision:
            model_by_candidate[model.candidate_revision_id] = model
    patch_by_revision = {patch.revision_id: patch for patch in patches}
    patch_revision_by_id = {patch.patch_id: patch.revision_id for patch in patches}
    children = [candidate for candidate in candidates if candidate.parent_candidate_revision_id]
    latest = max(children or candidates, key=lambda candidate: (candidate.meta.created_at, candidate.candidate_revision_id))
    baseline = next((candidate for candidate in candidates if candidate.parent_candidate_revision_id is None), latest)

    changes: list[PortfolioChange] = [
        PortfolioChange(
            change_id="baseline",
            sequence=1,
            kind="baseline",
            title="Baseline structured concept",
            summary=baseline.design.concept_summary if baseline.design else baseline.description,
            candidate_revision_id=baseline.candidate_revision_id,
            model_revision_id=model_by_candidate.get(baseline.candidate_revision_id).revision_id if baseline.candidate_revision_id in model_by_candidate else None,
            status="confirmed",
            evidence_boundary="Structured design facts only; no physical comfort, scale or outcome is validated.",
        )
    ]
    for sequence, candidate in enumerate(sorted(children, key=lambda value: (value.meta.created_at, value.candidate_revision_id)), start=2):
        candidate_patch_ids = [
            patch_revision_by_id[patch_id]
            for patch_id, _declaration in candidate.generator_application_declarations
            if patch_id in patch_revision_by_id
        ]
        change_titles = [patch_by_revision[patch_id].variable_id for patch_id in candidate_patch_ids if patch_id in patch_by_revision]
        changes.append(
            PortfolioChange(
                change_id=f"patch-{candidate.candidate_revision_id}",
                sequence=sequence,
                kind="variable_patch",
                title="Parameterized design revision",
                summary="Applied: " + (", ".join(change_titles) if change_titles else "declared VariablePatch inputs"),
                parent_candidate_revision_id=candidate.parent_candidate_revision_id,
                candidate_revision_id=candidate.candidate_revision_id,
                model_revision_id=model_by_candidate.get(candidate.candidate_revision_id).revision_id if candidate.candidate_revision_id in model_by_candidate else None,
                patch_revision_ids=candidate_patch_ids,
                status="confirmed",
                evidence_boundary="Patch adoption describes a structured design revision, not verified physical performance.",
            )
        )
    latest_runs: dict[str, DesignToolRun] = {}
    for run in sorted(tool_runs, key=lambda value: (value.meta.created_at, value.run_id)):
        previous = latest_runs.get(run.candidate_revision_id)
        if previous is None or (run.confirmation == "confirmed" and previous.confirmation != "confirmed") or run.meta.created_at >= previous.meta.created_at:
            latest_runs[run.candidate_revision_id] = run
    for run in latest_runs.values():
        assets = list(run.result_json.get("render_asset_refs", [])) + list(run.result_json.get("geometry_asset_refs", [])) + list(run.result_json.get("derived_review_views", {}).values())
        resulting_model = model_by_revision.get(run.resulting_model_revision_id or "")
        # ``design-attach`` requests are intentionally minimal and may not
        # repeat patch IDs in the DesignToolRun envelope.  Recover the
        # immutable patch lineage from the resulting model snapshot so the
        # portfolio does not present a patched visual draft as if it had no
        # declared variable changes.
        patch_revision_ids = list(run.patch_revision_ids)
        if not patch_revision_ids and resulting_model is not None:
            patch_revision_ids = list(resulting_model.applied_patch_revision_ids)
        changes.append(
            PortfolioChange(
                change_id=f"asset-{run.run_id}",
                sequence=len(changes) + 1,
                kind="visual_asset",
                title="Derived Blender blockout",
                summary="Review image and geometry exported for form, control-access and placement discussion.",
                parent_model_revision_id=run.parent_model_revision_id,
                candidate_revision_id=run.candidate_revision_id,
                model_revision_id=run.resulting_model_revision_id,
                patch_revision_ids=patch_revision_ids,
                graphic_asset_refs=assets,
                review_view_refs=dict(run.result_json.get("derived_review_views", {})),
                status="confirmed" if run.confirmation == "confirmed" else "draft",
                evidence_boundary="Derived assets are review material only; the blockout does not validate dimensions, fit, comfort, materials or movement stability.",
            )
        )
    prototype_runs = prototype_runs or []
    observations = observations or []
    evidence_reviews = evidence_reviews or []
    external_assets = external_assets or []
    observation_drafts = observation_drafts or []
    confirmed_observations = confirmed_observations or []
    levels = {"none": 0, "exploratory": 1, "observed": 2, "supported": 3, "replicated": 4}
    latest_observations: dict[str, object] = {}
    for observation in observations:
        observation_id = getattr(observation, "observation_id", None)
        if observation_id is None:
            continue
        previous = latest_observations.get(observation_id)
        if previous is None or observation.meta.revision >= previous.meta.revision:
            latest_observations[observation_id] = observation
    accepted_levels = []
    valid_review_ids: set[str] = set()
    valid_confirmed_ids: list[str] = []
    for review in evidence_reviews:
        if getattr(review, "decision", None) not in {"accepted", "modified"}:
            continue
        confirmed_ids = tuple(getattr(review, "confirmed_observation_ids", ()))
        confirmed = [latest_observations.get(observation_id) for observation_id in confirmed_ids]
        if not confirmed_ids or any(
            item is None
            or getattr(item, "status", None) != "confirmed"
            or getattr(item, "provenance", None) in {"blender_derived", "design_derived"}
            for item in confirmed
        ):
            continue
        valid_review_ids.add(getattr(review, "review_id", ""))
        valid_confirmed_ids.extend(confirmed_ids)
        accepted_levels.append(getattr(review, "evidence_level_after", "none"))
    evidence_level = max(accepted_levels, key=lambda value: levels.get(value, 0), default="none")
    protocol_status = "planned" if evidence_level == "none" else evidence_level
    changes.append(
        PortfolioChange(
            change_id="validation-plan",
            sequence=len(changes) + 1,
            kind="validation_plan",
            title="Prototype validation protocol",
            summary="A pre-prototype measurement plan for fit, control, detectability, contact and privacy boundaries.",
            candidate_revision_id=latest.candidate_revision_id,
            model_revision_id=model_by_candidate.get(latest.candidate_revision_id).revision_id if latest.candidate_revision_id in model_by_candidate else None,
            status=protocol_status,
            evidence_boundary="Planned measures are not evidence until a protocol is run and reviewed.",
        )
    )
    protocol = (validation_protocol or default_transit_validation_protocol()).model_copy(
        update={"status": "planned" if evidence_level == "none" else evidence_level}
    )
    workflow = {
        "prototype_run_ids": [getattr(run, "run_id", str(run)) for run in prototype_runs],
        "external_asset_ids": [getattr(asset, "asset_id", str(asset)) for asset in external_assets],
        "observation_draft_ids": [getattr(draft, "draft_id", str(draft)) for draft in observation_drafts],
        "confirmed_design_observation_ids": [getattr(item, "observation_id", str(item)) for item in confirmed_observations],
        "protocol_snapshots": [getattr(run, "protocol_snapshot", {}) for run in prototype_runs if getattr(run, "protocol_snapshot", {})],
        "observation_ids": [getattr(item, "observation_id", str(item)) for item in observations],
        "evidence_review_ids": [getattr(item, "review_id", str(item)) for item in evidence_reviews],
        "accepted_evidence_review_ids": sorted(valid_review_ids),
        "confirmed_observation_ids": list(dict.fromkeys(valid_confirmed_ids)),
        "evidence_level": evidence_level,
        "blender_is_not_evidence": True,
    }
    if scenario_policy is None and getattr(brief, "movement_scenarios", ()):
        scenario = next((item for item in brief.movement_scenarios if item.scenario_id == brief.scenario_ids[0]), brief.movement_scenarios[0])
        scenario_policy = build_scenario_policy(scenario)
    policy_revisions = [getattr(model, "scenario_policy_revision_ids", ()) for model in models]
    policy_revision_ids = list(dict.fromkeys(item for group in policy_revisions for item in group))
    return PortfolioCaseStudy(
        case_id=case_id,
        title="Transit Anchor — crowded-transit wrist companion",
        brief_revision_id=brief.revision_id,
        generated_from="experience SQLite revisions, VariablePatch records and DesignToolRun records",
        design_challenge=brief.goal,
        design_direction="Low-profile dorsal-wrist private haptic companion with bounded routine intervention and a local stop path.",
        changes=changes,
        current_product_snapshot=_snapshot(latest, model_by_candidate.get(latest.candidate_revision_id)),
        scenario_state_machine=default_transit_state_machine(brief.scenario_ids[0]),
        prototype_validation_protocol=protocol,
        portfolio_boundary="This portfolio projection separates declared design changes, derived graphics and planned validation. It never presents Blender output or scenario context as proof of user outcomes, comfort, consent, engineering readiness or physical performance.",
        evidence_workflow=workflow,
        executable_scenario_policy=(scenario_policy.model_dump(mode="json") if hasattr(scenario_policy, "model_dump") else None),
        scenario_policy_revisions=policy_revision_ids,
        virtual_validation=(virtual_validation.model_dump(mode="json") if hasattr(virtual_validation, "model_dump") else virtual_validation),
        scenario_replay=(scenario_replay.model_dump(mode="json") if hasattr(scenario_replay, "model_dump") else scenario_replay),
    )


def render_portfolio_markdown(case: PortfolioCaseStudy) -> str:
    snapshot = case.current_product_snapshot
    lines = [
        f"# {case.title}",
        "",
        f"> {case.design_direction}",
        "",
        "## Design challenge",
        "",
        case.design_challenge,
        "",
        "## Current design direction",
        "",
        f"- **Candidate revision:** `{snapshot.candidate_revision_id}`",
        f"- **Model revision:** `{snapshot.model_revision_id or 'not recorded'}`",
        f"- **Form:** {snapshot.form_factor or 'not declared'} — {snapshot.silhouette or 'not declared'}",
        f"- **Placement:** {snapshot.body_placement or 'not declared'}",
        f"- **Attachment:** {snapshot.attachment_strategy or 'not declared'}",
        f"- **Contact / mass intent:** {snapshot.contact_area or 'not declared'} / {snapshot.mass_distribution or 'not declared'}",
        f"- **Routine feedback:** {snapshot.feedback_modality or 'not declared'}; {snapshot.feedback_timing or 'timing not declared'}",
        f"- **Visible state:** {snapshot.visible_state or 'not declared'}",
        f"- **Local stop:** {snapshot.cancel_action or 'not declared'}",
        "",
        "## Product and graphic evolution",
        "",
    ]
    for change in case.changes:
        lines.extend([f"### {change.sequence}. {change.title}", "", f"- **Status:** `{change.status}`", f"- {change.summary}"])
        if change.parent_candidate_revision_id:
            lines.append(f"- Parent: `{change.parent_candidate_revision_id}`")
        if change.parent_model_revision_id:
            lines.append(f"- Parent model: `{change.parent_model_revision_id}`")
        if change.candidate_revision_id:
            lines.append(f"- Candidate: `{change.candidate_revision_id}`")
        if change.model_revision_id:
            lines.append(f"- Model: `{change.model_revision_id}`")
        if change.patch_revision_ids:
            lines.append("- Patches: " + ", ".join(f"`{item}`" for item in change.patch_revision_ids))
        if change.graphic_asset_refs:
            lines.append("- Assets:")
            lines.extend(f"  - `{item}`" for item in change.graphic_asset_refs)
        if change.review_view_refs:
            lines.append("- Review views:")
            lines.extend(f"  - **{name}:** `{ref}` (derived review material)" for name, ref in change.review_view_refs.items())
        lines.extend([f"- **Evidence boundary:** {change.evidence_boundary}", ""])
    machine = case.scenario_state_machine
    lines.extend(["## Scenario state machine", "", f"**Scenario:** {machine.name} (`{machine.scenario_id}`)", "", "| From | Event / guard | Action | To |", "| --- | --- | --- | --- |"])
    for transition in machine.transitions:
        lines.append(f"| {transition.from_state} | {transition.event}; {transition.guard} | {transition.action} | {transition.to_state} |")
    lines.extend(["", "### Control boundaries", ""])
    lines.extend(f"- {item}" for item in machine.invariants)
    lines.extend(["", "### Not claimed by this state machine", ""])
    lines.extend(f"- {item}" for item in machine.out_of_scope)
    if case.executable_scenario_policy:
        policy = case.executable_scenario_policy
        lines.extend(["", "## Executable scenario policy", "", f"- **Policy:** `{policy.get('policy_id', 'unknown')}` / `{policy.get('revision_id', 'unknown')}`", "", "| Phase | Action | Feedback | Max intensity | Timeout | Offline stop |", "| --- | --- | --- | ---: | ---: | --- |"])
        for decision in policy.get("decisions", []):
            lines.append(f"| {decision.get('phase_id', '')} | {decision.get('action', '')} | {decision.get('feedback_modality', '')} | {decision.get('max_intensity', '')} | {decision.get('response_timeout_ms', '')} ms | {decision.get('offline_stop', '')} |")
        lines.extend(["", "_Policy inputs are declared movement context. They do not infer intent, emotion or consent._"])
    if case.virtual_validation:
        virtual = case.virtual_validation
        lines.extend(
            [
                "",
                "## Virtual engineering preflight",
                "",
                f"- **Decision:** `{virtual.get('decision', 'unknown')}`",
                f"- **Evidence level:** `{virtual.get('evidence_level', 'none')}`",
                "- **Evidence eligible:** `false`",
                "- This deterministic first-order estimate uses declared assumptions only; it is not a physical prototype run or participant result.",
            ]
        )
        results = virtual.get("results", [])
        if isinstance(results, list):
            estimated = [item for item in results if isinstance(item, dict) and item.get("status") in {"pass_estimate", "risk_estimate"}]
            not_modelled = [item.get("metric_id", "unknown") for item in results if isinstance(item, dict) and item.get("status") == "not_modelled"]
            if estimated:
                risk_count = sum(1 for item in estimated if item.get("status") == "risk_estimate")
                lines.append(f"- **Estimated metrics:** {len(estimated)} ({risk_count} risk estimate(s))")
            if not_modelled:
                lines.append("- **Not modelled:** " + ", ".join(str(item) for item in not_modelled))
    if case.scenario_replay:
        replay = case.scenario_replay
        lines.extend(
            [
                "",
                "## Deterministic scenario replay",
                "",
                f"- **Status:** `{replay.get('status', 'unknown')}`",
                f"- **Evidence level:** `{replay.get('evidence_level', 'none')}`",
                "- **Evidence eligible:** `false`",
                f"- **Traces:** {len(replay.get('cases', [])) if isinstance(replay.get('cases', []), list) else 0}",
                "- This is a policy-control-flow replay over declared phases, not a sensor classification or user outcome.",
            ]
        )
    protocol = case.prototype_validation_protocol
    lines.extend(["", "## Prototype validation protocol", "", f"**Objective:** {protocol.objective}", "", f"**Participants and context:** {protocol.participants_and_context}", "", "| Test question | Conditions | Metric | Evidence boundary |", "| --- | --- | --- | --- |"])
    for measure in protocol.measures:
        lines.append(f"| {measure.question} | {'; '.join(measure.conditions)} | {measure.metric} | {measure.acceptance_boundary} |")
    lines.extend(["", "### Stopping conditions", ""])
    lines.extend(f"- {item}" for item in protocol.stopping_conditions)
    lines.extend(["", "### Outcomes not claimed", ""])
    lines.extend(f"- {item}" for item in protocol.outcomes_not_claimed)
    workflow = case.evidence_workflow
    lines.extend(["", "## Evidence workflow", "", f"- **Protocol status:** `{protocol.status}`", f"- **Evidence level:** `{workflow.get('evidence_level', 'none')}`", f"- **Prototype runs:** {len(workflow.get('prototype_run_ids', []))}", f"- **Imported observations:** {len(workflow.get('observation_ids', []))}", f"- **External assets:** {len(workflow.get('external_asset_ids', []))}", f"- **Observation drafts:** {len(workflow.get('observation_draft_ids', []))}", f"- **Confirmed design observations:** {len(workflow.get('confirmed_design_observation_ids', []))}", f"- **Human reviews:** {len(workflow.get('evidence_review_ids', []))}", "- Blender/derived assets are never promoted automatically to prototype evidence."])
    lines.extend(["", "---", "", f"_Portfolio boundary: {case.portfolio_boundary}_"])
    return "\n".join(lines)
