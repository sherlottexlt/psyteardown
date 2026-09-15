"""Future movement scenarios, initial design rules and convergence snapshots."""

from __future__ import annotations

import hashlib

from pydantic import Field

from psyteardown.experience.models import (
    BoundaryModel,
    DesignCandidate,
    DesignRuleCandidate,
    DesignRuleSet,
    FutureMovementScenario,
    ModelLayerStatus,
    MovementPhase,
    InterventionDecision,
    ScenarioPolicy,
    ProgressiveDesignModel,
    RevisionMeta,
)


class MovementPhaseInput(BoundaryModel):
    phase_id: str
    movement_state: str
    posture: str
    hands_available: str
    visual_attention: str
    ambient_motion: str
    social_visibility: str
    device_relation: str
    transition_from: str | None = None
    transition_to: str | None = None
    hazards: list[str] = Field(default_factory=list)


class FutureMovementScenarioInput(BoundaryModel):
    scenario_id: str
    name: str
    narrative: str
    phases: list[MovementPhaseInput]
    task_goal: str
    interruption_cost: str = "medium"
    recovery_cost: str = "medium"
    privacy_sensitivity: str = "medium"
    context_unknowns: list[str] = Field(default_factory=list)


def build_movement_scenarios(
    inputs: list[FutureMovementScenarioInput],
) -> tuple[FutureMovementScenario, ...]:
    return tuple(
        FutureMovementScenario(
            scenario_id=item.scenario_id,
            name=item.name,
            narrative=item.narrative,
            phases=tuple(
                MovementPhase(
                    **phase.model_dump(exclude={"hazards"}),
                    hazards=tuple(phase.hazards),
                )
                for phase in item.phases
            ),
            task_goal=item.task_goal,
            interruption_cost=item.interruption_cost,
            recovery_cost=item.recovery_cost,
            privacy_sensitivity=item.privacy_sensitivity,
            context_unknowns=tuple(item.context_unknowns),
        )
        for item in inputs
    )


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def generate_initial_design_rules(
    brief_revision_id: str,
    scenarios: tuple[FutureMovementScenario, ...],
    *,
    actor: str = "system",
) -> DesignRuleSet:
    """Project bounded rule candidates from declared movement conditions.

    The rules are not learned human-factors truths.  They remain candidate or
    validation-only constraints until evidence and a human approval process
    promote them through the existing heuristic/rule lifecycle.
    """

    scenario_ids = tuple(scenario.scenario_id for scenario in scenarios)
    facts = {
        "hands_limited": any(
            phase.hands_available in {"none", "intermittent"}
            for scenario in scenarios
            for phase in scenario.phases
        ),
        "vision_limited": any(
            phase.visual_attention in {"unavailable", "intermittent"}
            for scenario in scenarios
            for phase in scenario.phases
        ),
        "high_motion": any(
            phase.ambient_motion == "high"
            or phase.movement_state in {"running", "cycling", "micro_mobility"}
            for scenario in scenarios
            for phase in scenario.phases
        ),
        "public_context": any(
            phase.social_visibility == "public"
            for scenario in scenarios
            for phase in scenario.phases
        ),
        "body_worn": any(
            phase.device_relation.startswith("worn_")
            or phase.device_relation in {"clothing_attached", "distributed_body_area"}
            for scenario in scenarios
            for phase in scenario.phases
        ),
        "movement_transition": any(
            phase.transition_from or phase.transition_to
            for scenario in scenarios
            for phase in scenario.phases
        ),
    }
    specs = []
    if facts["hands_limited"]:
        specs.append((
            "hands-limited-control",
            "Hands-free primary control",
            "hands are unavailable or intermittent during motion",
            ("feedback.confirmation", "control.cancel_action"),
            "Do not require a precise two-handed action for the primary acknowledge, reject or emergency-stop path.",
            "Limited hands make a precise manual-only path unavailable at the moment it is needed.",
            "When the user is stationary and both hands are available, richer manual controls may remain optional.",
            "Walk/run transition test: complete reject and stop actions without looking or using both hands.",
        ))
    if facts["vision_limited"]:
        specs.append((
            "vision-limited-feedback",
            "Non-visual primary feedback",
            "visual attention is intermittent or unavailable",
            ("feedback.modality", "feedback.timing"),
            "Avoid a visual-only primary signal; preserve a private non-visual path and an optional visual confirmation.",
            "Visual demand during movement can compete with navigation and hazard monitoring.",
            "A visual-first interface may be appropriate when stationary with confirmed visual availability.",
            "Compare detection and navigation-task error under visual-only and private haptic conditions.",
        ))
    if facts["high_motion"]:
        specs.append((
            "motion-robust-fit",
            "Motion-robust fit and activation",
            "running, cycling, micro-mobility or high ambient motion is present",
            ("wearable.attachment", "control.activation_force", "feedback.detectability"),
            "Use a retention strategy and input geometry that resist slip and accidental activation, while keeping removal reversible.",
            "Motion changes contact, detectability and accidental-input likelihood.",
            "Low-motion seated use may accept a looser mount and lighter activation force.",
            "Prototype test across declared movement phases for displacement, false activation and removal time.",
        ))
    if facts["public_context"]:
        specs.append((
            "public-privacy",
            "Public-context privacy boundary",
            "the product is visible or audible in public",
            ("feedback.modality", "privacy.public_exposure", "device.visible_state"),
            "Default routine content to a private modality and reveal sensing/recording state without exposing private content.",
            "Wearables cross personal and public space; discoverability must not erase privacy boundaries.",
            "User-authorized public safety alerts require a separately approved critical-event policy.",
            "Bystander review plus content-leakage inspection in the public movement scenario.",
        ))
    if facts["body_worn"]:
        specs.append((
            "body-contact-boundary",
            "Body-contact comfort remains unverified",
            "the device is worn on or attached to the body",
            ("wearable.contact_area", "wearable.mass_distribution", "material.skin_contact"),
            "Keep contact geometry, mass distribution, thermal behavior and removal path explicit variables; do not declare comfort before prototype evidence.",
            "A structured concept cannot verify pressure, heat, sweat, skin response or long-duration comfort.",
            "Non-contact or short-duration handheld modes have different physical evidence requirements.",
            "Instrumented fit test plus consented wear trial across the declared durations and movements.",
        ))
    if facts["movement_transition"]:
        specs.append((
            "transition-continuity",
            "State continuity across movement transitions",
            "the user changes posture, vehicle relation, task or movement state",
            ("context.transition_policy", "device.visible_state", "feedback.persistence"),
            "Make state carry-over, suppression and resume behavior explicit at each transition; never infer consent from the transition itself.",
            "A stationary policy can become intrusive or unsafe immediately after movement changes.",
            "Stateless interactions may simply terminate instead of carrying context across a transition.",
            "Replay each declared phase transition and verify state, consent scope and termination behavior.",
        ))

    # This general rule is useful even when the user only supplies one phase.
    specs.append((
        "uncertainty-degradation",
        "Bounded uncertainty degradation",
        "movement or context inference confidence is insufficient",
        ("context.inference_confidence", "feedback.intensity", "feedback.timing"),
        "Reduce, defer or terminate routine intervention and retain an immediate correction path.",
        "Movement context is a declared inference, not a fact about intent, emotion or consent.",
        "A separately approved critical policy may permit one bounded escalation within explicit limits.",
        "Inject false-positive and low-confidence contexts and inspect all event terminations.",
    ))

    rules = tuple(
        DesignRuleCandidate(
            rule_id=_stable_id("movement-rule", code),
            name=name,
            scenario_ids=scenario_ids,
            condition=condition,
            target_variable_ids=variables,
            recommendation=recommendation,
            rationale=rationale,
            counter_condition=counter_condition,
            verification=verification,
            enforcement="consider_as_option" if code in {"public-privacy", "uncertainty-degradation"} else "validation_only",
        )
        for code, name, condition, variables, recommendation, rationale, counter_condition, verification in specs
    )
    rule_set_id = _stable_id("movement-rule-set", brief_revision_id + "|" + "|".join(scenario_ids))
    return DesignRuleSet(
        rule_set_id=rule_set_id,
        revision_id=f"{rule_set_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="initial movement design rules generated"),
        brief_revision_id=brief_revision_id,
        movement_scenario_ids=scenario_ids,
        rules=rules,
    )


def build_scenario_policy(
    scenario: FutureMovementScenario,
    *,
    actor: str = "system",
    status: str = "candidate",
) -> ScenarioPolicy:
    """Compile a declared movement scenario into a bounded routine policy.

    Hazard phases suppress routine output, transitional/medium-motion phases
    defer it, and only low-motion stationary phases allow one private haptic
    signal.  This is deterministic policy logic over declared inputs; it does
    not classify sensors or infer user intent/consent.
    """
    decisions: list[InterventionDecision] = []
    for phase in scenario.phases:
        hard_hazard = bool(phase.hazards) or phase.ambient_motion == "high" or phase.movement_state in {
            "running", "cycling", "micro_mobility", "entering_vehicle", "exiting_vehicle"
        }
        transition = bool(phase.transition_from or phase.transition_to)
        limited_control = phase.hands_available == "none"
        if hard_hazard:
            action = "suppress"
            reason_codes = ("hazard_declared", "high_motion_or_transition")
        elif transition or phase.ambient_motion == "medium" or limited_control:
            action = "defer"
            reason_codes = tuple(
                code for code, enabled in (
                    ("movement_transition", transition),
                    ("medium_motion", phase.ambient_motion == "medium"),
                    ("hands_unavailable", limited_control),
                ) if enabled
            )
        else:
            action = "allow"
            reason_codes = ("low_motion_declared", "private_modality_only")
        decisions.append(
            InterventionDecision(
                scenario_id=scenario.scenario_id,
                phase_id=phase.phase_id,
                action=action,
                feedback_modality="private_haptic" if action == "allow" else "none",
                max_intensity=1 if action == "allow" else 0,
                response_timeout_ms=5000 if action == "allow" else 0,
                offline_stop=(
                    "local_stop"
                    if action == "allow" or (action == "suppress" and not limited_control)
                    else "unavailable"
                    if action == "suppress"
                    else "timeout_terminate"
                ),
                deferred_event_policy="record_minimal_metadata" if action in {"defer", "suppress"} else "drop",
                reason_codes=reason_codes,
                user_control_boundary=(
                    "No response terminates the routine event; silence is not consent."
                    if action == "allow"
                    else "Routine content is withheld; movement context does not imply intent, consent or attention."
                ),
            )
        )
    policy_id = _stable_id("scenario-policy", scenario.scenario_id)
    return ScenarioPolicy(
        policy_id=policy_id,
        revision_id=f"{policy_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="deterministic routine scenario policy compiled"),
        scenario_id=scenario.scenario_id,
        decisions=tuple(decisions),
        status=status,
    )


compile_scenario_policy = build_scenario_policy


def create_progressive_design_model(
    candidate: DesignCandidate,
    rule_set: DesignRuleSet,
    *,
    actor: str = "system",
    scenario_policy_revision_ids: tuple[str, ...] = (),
) -> ProgressiveDesignModel:
    """Create the first convergence snapshot from a complete text design."""

    model_id = f"{candidate.candidate_id}.model"
    gaps = tuple(
        dict.fromkeys(
            (*candidate.unknowns, *(candidate.design.declared_unknowns if candidate.design else ()))
        )
    )
    layers = (
        ModelLayerStatus(layer="brief", status="complete", artifact_refs=(candidate.brief_revision_id,)),
        ModelLayerStatus(layer="movement_scenarios", status="complete" if rule_set.movement_scenario_ids else "missing", artifact_refs=rule_set.movement_scenario_ids),
        ModelLayerStatus(layer="design_rules", status="unverified", artifact_refs=(rule_set.revision_id,), gaps=("candidate rules require evidence and human approval",)),
        ModelLayerStatus(layer="structured_design", status="complete" if candidate.design else "missing", artifact_refs=((candidate.design.design_id,) if candidate.design else ())),
        ModelLayerStatus(layer="event_behavior", status="complete" if candidate.events else "missing", artifact_refs=tuple(event.event_id for event in candidate.events)),
        ModelLayerStatus(layer="render_assets", status="missing", gaps=("no design-tool render imported",)),
        ModelLayerStatus(layer="geometry", status="missing", gaps=("no 3D/CAD geometry imported",)),
        ModelLayerStatus(layer="engineering_spec", status="unverified", gaps=("dimensions, materials, power, thermal and manufacturing require engineering evidence",)),
        ModelLayerStatus(layer="prototype_evidence", status="missing", gaps=("no physical prototype evidence",)),
    )
    return ProgressiveDesignModel(
        model_id=model_id,
        revision_id=f"{model_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="structured design model initialized"),
        brief_revision_id=candidate.brief_revision_id,
        candidate_revision_id=candidate.candidate_revision_id,
        design_rule_set_revision_id=rule_set.revision_id,
        layers=layers,
        unresolved_gaps=gaps,
        scenario_policy_revision_ids=scenario_policy_revision_ids,
    )
