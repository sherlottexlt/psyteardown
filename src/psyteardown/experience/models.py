"""Immutable domain models for the structured-text experience slice.

Provider/import DTOs are deliberately kept separate from confirmed domain
snapshots.  DTOs use lists for convenient JSON validation; snapshots use
tuples and ``frozen=True`` so a confirmed revision cannot be changed in place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias, Any
import hashlib
import json

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


Identifier = Annotated[str, Field(min_length=1)]
ScalarValue: TypeAlias = str | int | float | bool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        # Pydantic's ``frozen`` setting protects attribute assignment but does
        # not recursively freeze dictionaries.  Convert mapping payloads to a
        # dict-compatible read-only wrapper so revision snapshots cannot be
        # mutated through a nested field after construction.
        for field_name, value in tuple(self.__dict__.items()):
            if isinstance(value, dict):
                object.__setattr__(self, field_name, _freeze_mapping(value))

    @property
    def content_hash(self) -> str:
        """Stable hash of the canonical immutable payload.

        Hashes are derived data, never identity or revision numbers.  Keeping
        this as a property preserves compatibility with existing snapshots
        while giving every immutable record an integrity/reproducibility
        boundary.
        """
        payload = self.model_dump(mode="json", exclude={"content_hash", "content_hash_value"})

        # ``created_at`` is operational metadata, not semantic payload.  It
        # must not make two equivalent snapshots hash differently merely
        # because they were instantiated a few microseconds apart.
        def strip_creation_time(value: Any) -> Any:
            if isinstance(value, dict):
                return {
                    key: strip_creation_time(item)
                    for key, item in value.items()
                    if key != "created_at"
                }
            if isinstance(value, list):
                return [strip_creation_time(item) for item in value]
            return value

        payload = strip_creation_time(payload)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def revision_number(self) -> int | None:
        meta = getattr(self, "meta", None)
        return getattr(meta, "revision", None)


class _ImmutableDict(dict):
    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("immutable revision mapping")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable


def _freeze_mapping(value: dict[Any, Any]) -> _ImmutableDict:
    frozen = _ImmutableDict()
    for key, item in value.items():
        if isinstance(item, dict):
            item = _freeze_mapping(item)
        elif isinstance(item, list):
            item = tuple(_freeze_mapping(entry) if isinstance(entry, dict) else entry for entry in item)
        elif isinstance(item, tuple):
            item = tuple(_freeze_mapping(entry) if isinstance(entry, dict) else entry for entry in item)
        dict.__setitem__(frozen, key, item)
    return frozen


class BoundaryModel(BaseModel):
    """Untrusted boundary object returned by an import/provider adapter."""

    model_config = ConfigDict(extra="forbid")


class DomainStateError(RuntimeError):
    """A command attempted to bypass an explicit workflow gate."""


class SemanticValidationError(ValueError):
    """A schema-valid draft failed deterministic semantic validation."""


class RevisionMeta(FrozenModel):
    revision: int = Field(ge=1)
    parent_revision_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    created_by: Identifier
    reason: Identifier


class DependencyRef(FrozenModel):
    object_type: Identifier
    object_id: Identifier
    revision: int = Field(ge=1)


class MovementPhase(FrozenModel):
    """One observable phase in a future mobility scenario."""

    phase_id: Identifier
    movement_state: Literal[
        "stationary",
        "walking",
        "running",
        "cycling",
        "transit_passenger",
        "micro_mobility",
        "entering_vehicle",
        "exiting_vehicle",
        "task_transition",
    ]
    posture: Literal["seated", "standing", "walking_posture", "running_posture", "riding"]
    hands_available: Literal["both", "one", "none", "intermittent"]
    visual_attention: Literal["available", "intermittent", "unavailable"]
    ambient_motion: Literal["low", "medium", "high"]
    social_visibility: Literal["private", "shared", "public"]
    device_relation: Literal[
        "worn_wrist",
        "worn_ear",
        "worn_neck",
        "worn_torso",
        "clothing_attached",
        "handheld",
        "bag_attached",
        "distributed_body_area",
    ]
    transition_from: str | None = None
    transition_to: str | None = None
    hazards: tuple[str, ...] = ()


class InterventionDecision(FrozenModel):
    """Deterministic routine-intervention decision for one movement phase.

    This is a policy projection, not a sensor classifier: a phase describes
    declared context and never implies intent, consent or emotion.
    """

    scenario_id: Identifier
    phase_id: Identifier
    event_type: Literal["routine"] = "routine"
    action: Literal["suppress", "defer", "allow"]
    feedback_modality: Literal["private_haptic", "visual", "none"]
    max_intensity: int = Field(ge=0, le=3)
    response_timeout_ms: int = Field(ge=0)
    no_response_outcome: Literal["terminate"] = "terminate"
    correction_outcome: Literal["safe_boundary_review"] = "safe_boundary_review"
    offline_stop: Literal["local_stop", "timeout_terminate", "unavailable"]
    deferred_event_policy: Literal["record_minimal_metadata", "drop"] = "record_minimal_metadata"
    permission_required: bool = True
    reason_codes: tuple[str, ...] = ()
    user_control_boundary: Identifier

    @model_validator(mode="after")
    def action_shape(self) -> "InterventionDecision":
        if self.action == "suppress" and (self.feedback_modality != "none" or self.max_intensity != 0 or self.response_timeout_ms != 0):
            raise ValueError("suppressed routine intervention cannot emit feedback or open a response window")
        if self.action == "suppress" and self.offline_stop not in {"local_stop", "unavailable"}:
            raise ValueError("suppressed routine intervention requires local stop or explicit unavailability")
        if self.action == "defer" and self.feedback_modality != "none":
            raise ValueError("deferred routine intervention cannot emit feedback while deferred")
        if self.action == "defer" and self.offline_stop != "timeout_terminate":
            raise ValueError("deferred routine intervention must terminate by timeout when offline")
        if self.action == "allow" and self.feedback_modality != "private_haptic":
            raise ValueError("routine allow path must use private haptic feedback")
        if self.action == "allow" and self.response_timeout_ms <= 0:
            raise ValueError("allowed routine intervention requires a bounded response timeout")
        if self.action == "allow" and self.offline_stop != "local_stop":
            raise ValueError("allowed routine intervention requires an offline local stop path")
        return self


class ScenarioPolicy(FrozenModel):
    """Versioned deterministic policy for one declared movement scenario."""

    policy_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    scenario_id: Identifier
    decisions: tuple[InterventionDecision, ...]
    status: Literal["candidate", "frozen"] = "candidate"
    out_of_scope: tuple[str, ...] = ("critical_event_policy", "sensor_classification", "intent_or_consent_inference")

    @model_validator(mode="after")
    def unique_phases(self) -> "ScenarioPolicy":
        phase_ids = tuple(item.phase_id for item in self.decisions)
        if len(set(phase_ids)) != len(phase_ids):
            raise ValueError("scenario policy requires one decision per phase")
        return self

    def decision_for(self, phase_id: str, *, event_type: str = "routine", permission_valid: bool = True) -> InterventionDecision:
        if event_type != "routine":
            raise ValueError("critical-event policy is out of scope for the routine scenario policy")
        try:
            decision = next(item for item in self.decisions if item.phase_id == phase_id)
        except StopIteration as exc:
            raise ValueError(f"unknown movement phase: {phase_id}") from exc
        if not permission_valid:
            return decision.model_copy(
                update={
                    "action": "suppress",
                    "feedback_modality": "none",
                    "max_intensity": 0,
                    "response_timeout_ms": 0,
                    "reason_codes": tuple(dict.fromkeys((*decision.reason_codes, "permission_not_valid"))),
                }
            )
        return decision

    def evaluate(self, phase_id: str, *, event_type: str = "routine", permission_valid: bool = True) -> InterventionDecision:
        """Runtime-facing alias that keeps policy evaluation deterministic."""
        return self.decision_for(phase_id, event_type=event_type, permission_valid=permission_valid)


class FutureMovementScenario(FrozenModel):
    scenario_id: Identifier
    name: Identifier
    narrative: Identifier
    phases: tuple[MovementPhase, ...]
    task_goal: Identifier
    interruption_cost: Literal["low", "medium", "high"]
    recovery_cost: Literal["low", "medium", "high"]
    privacy_sensitivity: Literal["low", "medium", "high"]
    context_unknowns: tuple[str, ...] = ()

    @model_validator(mode="after")
    def bounded_phases(self) -> "FutureMovementScenario":
        if not 1 <= len(self.phases) <= 8:
            raise ValueError("future movement scenario requires 1-8 phases")
        if len({phase.phase_id for phase in self.phases}) != len(self.phases):
            raise ValueError("movement phase IDs must be unique within a scenario")
        return self


class DesignRuleCandidate(FrozenModel):
    rule_id: Identifier
    name: Identifier
    scenario_ids: tuple[str, ...]
    condition: Identifier
    target_variable_ids: tuple[str, ...]
    recommendation: Identifier
    rationale: Identifier
    counter_condition: Identifier
    verification: Identifier
    source: Literal["deterministic_scenario_projection"] = "deterministic_scenario_projection"
    enforcement: Literal["consider_as_option", "validation_only"] = "validation_only"
    status: Literal["candidate"] = "candidate"


class DesignRuleSet(FrozenModel):
    rule_set_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    movement_scenario_ids: tuple[str, ...]
    rules: tuple[DesignRuleCandidate, ...]
    status: Literal["candidate"] = "candidate"


class ModelLayerStatus(FrozenModel):
    layer: Literal[
        "brief",
        "movement_scenarios",
        "design_rules",
        "structured_design",
        "event_behavior",
        "render_assets",
        "geometry",
        "engineering_spec",
        "prototype_evidence",
    ]
    status: Literal["complete", "partial", "missing", "unverified"]
    artifact_refs: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()


class ProgressiveDesignModel(FrozenModel):
    """Revisioned convergence state; not a claim of geometric completeness."""

    model_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    candidate_revision_id: Identifier
    design_rule_set_revision_id: Identifier
    stage: Literal[
        "structured_design",
        "render_ready",
        "geometry_ready",
        "engineering_ready",
        "prototype_validated",
    ] = "structured_design"
    layers: tuple[ModelLayerStatus, ...]
    applied_patch_revision_ids: tuple[str, ...] = ()
    provider_result_ids: tuple[str, ...] = ()
    scenario_policy_revision_ids: tuple[str, ...] = ()
    unresolved_gaps: tuple[str, ...] = ()


class DesignToolRun(FrozenModel):
    """Immutable bridge record for one provider request/result pair.

    Keeping this separate from ``ProgressiveDesignModel`` makes it possible to
    audit draft versus human-confirmed assets without treating provider output
    as a design fact.
    """

    run_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    candidate_revision_id: Identifier
    parent_model_revision_id: Identifier | None = None
    resulting_model_revision_id: Identifier | None = None
    patch_revision_ids: tuple[str, ...] = ()
    request_json: dict[str, object]
    result_json: dict[str, object]
    confirmation: Literal["pending", "confirmed"] = "pending"


class ExperienceCriterion(FrozenModel):
    criterion_id: Identifier
    name: Identifier
    operational_definition: Identifier
    desired_direction: Identifier
    observable_indicators: tuple[str, ...] = ()
    prohibited_indicators: tuple[str, ...] = ()
    applicable_scenario_ids: tuple[str, ...] = ()
    evidence_required: tuple[str, ...] = ()
    priority: int = Field(ge=1)
    tie_break_policy: Literal["preserve_tie", "prefer_lower_risk", "needs_evidence"] = (
        "preserve_tie"
    )


class ProhibitedExperience(FrozenModel):
    prohibition_id: Identifier
    operational_definition: Identifier
    severity: Literal["hard", "strong_avoidance", "watch"]
    indicator: Identifier
    approved_rule_id: str | None = None
    applicable_scenario_ids: tuple[str, ...] = ()
    evidence_required: tuple[str, ...] = ()
    release_condition: Identifier

    @model_validator(mode="after")
    def hard_requires_rule(self) -> "ProhibitedExperience":
        if self.severity == "hard" and not self.approved_rule_id:
            raise ValueError("hard prohibited experience requires approved_rule_id")
        return self


class DesignConstraint(FrozenModel):
    constraint_id: Identifier
    field_path: Identifier
    operator: Literal["eq", "ne", "lt", "lte", "gt", "gte", "in", "not_in"]
    value: ScalarValue | tuple[ScalarValue, ...]
    unit: str | None = None
    tolerance: float | None = Field(default=None, ge=0)
    evidence_required: Literal["declared", "confirmed", "measured"] = "declared"
    check_stage: Literal["import", "facts_frozen", "prototype"] = "import"
    failure_status: Literal["generation_invalid", "blocked", "explore"]


class DivergenceMatrix(FrozenModel):
    variable_ids: tuple[str, ...]
    strategy_directions: tuple[str, ...]
    minimum_directions: int = Field(default=3, ge=1)

    @model_validator(mode="after")
    def has_meaningful_dimensions(self) -> "DivergenceMatrix":
        if not self.variable_ids:
            raise ValueError("divergence matrix requires at least one variable")
        if len(set(self.strategy_directions)) < self.minimum_directions:
            raise ValueError("divergence matrix has fewer strategy directions than required")
        return self


class DesignBrief(FrozenModel):
    brief_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    status: Literal["draft", "frozen"] = "draft"
    product_category: Identifier = "AI mobile device or accessory"
    goal: Identifier
    target_segment: Identifier
    researchability_confirmed: bool = False
    context: Identifier
    scenario_ids: tuple[str, ...]
    movement_scenarios: tuple[FutureMovementScenario, ...] = ()
    criteria: tuple[ExperienceCriterion, ...]
    prohibited_experiences: tuple[ProhibitedExperience, ...] = ()
    constraints: tuple[DesignConstraint, ...] = ()
    tradeoff_priorities: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    design_language: tuple[str, ...] = ()
    initial_design_rules: tuple[DesignRuleCandidate, ...] = ()
    design_rule_set_revision_id: str | None = None
    divergence_matrix: DivergenceMatrix
    round_one_size: Literal[5] = 5
    round_two_variants_per_direction: Literal[3] = 3
    parallel_branch_budget: int = Field(default=2, ge=1, le=2)
    # Optional engineering traceability entry point.  Existing M1/M2/M3
    # callers may omit it; P0 orchestration can attach requirement revisions
    # without changing the experience snapshot semantics.
    dependencies: tuple[DependencyRef, ...] = ()

    @property
    def id(self) -> str:
        """Compatibility shorthand used by boundary clients."""
        return self.brief_id


class ValueMissingReason(StrEnum):
    NOT_DECLARED = "not_declared"
    NOT_OBSERVABLE = "not_observable"
    NOT_MEASURED = "not_measured"
    CONFLICTED = "conflicted"


class DesignVariableValue(FrozenModel):
    variable_id: Identifier
    value_type: Literal["enum", "number", "boolean", "text", "set"]
    normalized_value: ScalarValue | tuple[str, ...] | None = None
    display_value: Identifier
    unit: str | None = None
    source_fact_id: str | None = None
    certainty: Literal["declared", "confirmed", "measured"] = "declared"
    missing_reason: ValueMissingReason | None = None

    @model_validator(mode="after")
    def validate_value_shape(self) -> "DesignVariableValue":
        if (self.normalized_value is None) == (self.missing_reason is None):
            raise ValueError("provide exactly one of normalized_value or missing_reason")
        if self.value_type == "number" and self.normalized_value is not None:
            if isinstance(self.normalized_value, bool) or not isinstance(
                self.normalized_value, (int, float)
            ):
                raise ValueError("number variable requires a numeric normalized_value")
            if not self.unit:
                raise ValueError("number variable requires unit")
        if self.value_type == "set" and self.normalized_value is not None:
            if not isinstance(self.normalized_value, tuple):
                raise ValueError("set variable requires a tuple normalized_value")
        return self


class DeclaredFact(FrozenModel):
    fact_id: Identifier
    subject: Identifier
    predicate: Identifier
    value: Identifier
    source_locator: Identifier
    risk_relevance: Literal["ordinary", "privacy", "safety", "control"] = "ordinary"


class ConfirmedObservation(FrozenModel):
    observation_id: Identifier
    meta: RevisionMeta = Field(default_factory=lambda: RevisionMeta(revision=1, created_by="system", reason="observation confirmed"))
    source_fact_id: Identifier
    subject: Identifier
    predicate: Identifier
    value: Identifier
    source_locator: Identifier
    confirmation: Literal["accepted", "modified", "not_observable"]
    confirmed_by: Identifier
    confirmed_at: datetime = Field(default_factory=utc_now)
    provenance: Literal["declared", "external_asset", "blender_derived", "prototype_measurement"] = "declared"
    source_draft_id: str | None = None
    asset_ids: tuple[str, ...] = ()
    image_region: "ImageRegion | str | None" = None
    video_segment: "VideoTimeSegment | None" = None
    claim_category: Literal[
        "visual_attribute", "motion", "dimension", "pressure", "strength", "comfort", "other"
    ] = "other"
    calibration_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class ResponseBranch(FrozenModel):
    response: Literal[
        "accepted",
        "user_rejected",
        "user_snoozed",
        "no_response",
        "feedback_not_detectable",
        "user_corrected",
    ]
    condition: Identifier
    outcome: Literal["termination", "recovery"]
    variable_refs: tuple[str, ...] = ()
    resume_condition: str | None = None
    max_retries: int = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def snooze_has_resume_condition(self) -> "ResponseBranch":
        if self.response == "user_snoozed" and not self.resume_condition:
            raise ValueError("user_snoozed requires resume_condition")
        if self.response != "user_snoozed" and self.max_retries:
            raise ValueError("only user_snoozed can retry in the first slice")
        return self


class EventStep(FrozenModel):
    step_id: Identifier
    modality: Literal["private_haptic", "public_audio", "visual", "in_ear_voice", "none"]
    timing: Identifier
    salience_level: int = Field(ge=0, le=3)
    duration_ms: int = Field(ge=0)
    repetition: int = Field(ge=0, le=3)
    variable_refs: tuple[str, ...]


class InterventionEventSequence(FrozenModel):
    event_id: Identifier
    event_type: Literal[
        "normal_intervention",
        "defer_or_reject",
        "low_confidence",
        "misclassification_recovery",
        "critical_intervention",
    ]
    scenario_id: Identifier
    criticality: Literal["routine", "important", "critical"]
    trigger: Identifier
    context_snapshot: Identifier
    context_inference: Identifier
    permission_decision: Identifier
    feedback_steps: tuple[EventStep, ...]
    expected_user_response: Identifier
    response_branches: tuple[ResponseBranch, ...]
    correction_path: Identifier
    recovery_path: Identifier
    termination_conditions: tuple[str, ...]
    escalation_count: int = Field(default=0, ge=0, le=1)


class CandidateDraft(BoundaryModel):
    """Schema-valid but still untrusted candidate input."""

    candidate_id: Identifier
    brief_revision_id: Identifier
    parent_candidate_revision_id: str | None = None
    source: Literal["human", "fake_provider", "manual_import"] = "fake_provider"
    contract_version: Identifier = "experience-candidate/v1"
    name: Identifier
    description: Identifier
    interaction_story: Identifier
    target_context: Identifier
    unknowns: list[str] = Field(default_factory=list)
    strategy_direction: Identifier
    changed_variable_ids: list[str]
    declared_facts: list[DeclaredFact]
    variables: list[DesignVariableValue]
    events: list[InterventionEventSequence]
    supports_critical: bool = False
    generator_application_declarations: dict[str, str] = Field(default_factory=dict)
    shape: "DesignShape | None" = None
    design: "DesignSpecification | None" = None


class DesignShape(FrozenModel):
    """Initial product-form scaffold, not a claim about a manufactured object."""

    form_factor: Literal[
        "desktop_device",
        "wearable",
        "handheld",
        "earbud_case",
        "phone_case",
        "portable_object",
    ] = "portable_object"
    silhouette: Identifier
    interaction_surface: Identifier
    feedback_surface: Identifier
    grip_or_mount: Identifier
    material_hint: str | None = None
    visible_state: Identifier
    body_placement: str | None = None
    attachment_strategy: str | None = None
    motion_adaptation: str | None = None
    # Explicit experience variables are kept on the shape snapshot so a
    # parameterized revision can be rendered without inventing engineering
    # measurements.  These are declarations, not validated comfort/fit data.
    contact_area: str | None = None
    mass_distribution: str | None = None
    feedback_modality: str | None = None
    feedback_timing: str | None = None
    confirmation_action: str | None = None
    dimensions: str | None = None
    physical_unknowns: tuple[str, ...] = ()


class DesignComponent(FrozenModel):
    """A named part of the early product concept."""

    component_id: Identifier
    name: Identifier
    role: Identifier
    placement: Identifier
    material_or_finish: str | None = None
    physical_unknowns: tuple[str, ...] = ()


class DesignSpecification(FrozenModel):
    """Complete text-first product design description for an early concept."""

    design_id: Identifier
    title: Identifier
    concept_summary: Identifier
    problem_statement: Identifier
    user_value: Identifier
    intended_user_and_context: Identifier
    shape: DesignShape
    components: tuple[DesignComponent, ...]
    design_principles: tuple[str, ...] = ()
    functional_architecture: tuple[str, ...] = ()
    sensing_and_inference: tuple[str, ...] = ()
    movement_model: tuple[str, ...] = ()
    ergonomic_strategy: tuple[str, ...] = ()
    adaptation_behavior: tuple[str, ...] = ()
    material_and_finish: tuple[str, ...] = ()
    interaction_flow: tuple[str, ...] = ()
    feedback_behavior: tuple[str, ...] = ()
    privacy_and_control: tuple[str, ...] = ()
    data_flow: tuple[str, ...] = ()
    power_and_connectivity: tuple[str, ...] = ()
    safety_and_failure_modes: tuple[str, ...] = ()
    manufacturing_assumptions: tuple[str, ...] = ()
    verification_plan: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    declared_unknowns: tuple[str, ...] = ()


class ValidationIssue(FrozenModel):
    code: Identifier
    field: Identifier
    message: Identifier


class DesignCandidate(FrozenModel):
    candidate_id: Identifier
    candidate_revision_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    parent_candidate_revision_id: str | None = None
    status: Literal["input_valid", "generation_invalid", "facts_frozen"]
    name: Identifier
    description: Identifier
    interaction_story: Identifier
    target_context: Identifier
    unknowns: tuple[str, ...] = ()
    strategy_direction: Identifier
    changed_variable_ids: tuple[str, ...]
    declared_facts: tuple[DeclaredFact, ...]
    variables: tuple[DesignVariableValue, ...]
    events: tuple[InterventionEventSequence, ...]
    supports_critical: bool = False
    validation_issues: tuple[ValidationIssue, ...] = ()
    generator_application_declarations: tuple[tuple[str, str], ...] = ()
    shape: DesignShape | None = None
    design: DesignSpecification | None = None
    dependencies: tuple[DependencyRef, ...] = ()

    @property
    def id(self) -> str:
        return self.candidate_id

    @property
    def revision(self) -> int:
        return self.meta.revision


class EvidenceConflict(FrozenModel):
    conflict_id: Identifier
    fact_ids: tuple[str, ...]
    description: Identifier
    status: Literal["resolved", "unresolved"]
    resolution: str | None = None


class CandidateFactsSnapshot(FrozenModel):
    facts_snapshot_id: Identifier
    candidate_id: Identifier
    candidate_revision_id: Identifier
    brief_revision_id: Identifier
    meta: RevisionMeta
    observations: tuple[ConfirmedObservation, ...]
    variables: tuple[DesignVariableValue, ...]
    events: tuple[InterventionEventSequence, ...]
    conflicts: tuple[EvidenceConflict, ...] = ()
    not_observable_fact_ids: tuple[str, ...] = ()
    status: Literal["facts_frozen"] = "facts_frozen"
    dependencies: tuple[DependencyRef, ...] = ()
    evidence_review_ids: tuple[str, ...] = ()

    @property
    def candidate_facts_freeze_id(self) -> str:
        return self.facts_snapshot_id


class EvidenceReference(FrozenModel):
    layer: Literal["design_fact", "context", "mechanism", "outcome"]
    source_id: Identifier
    locator: Identifier


# Generic experience-research layer -----------------------------------------
#
# The prototype evidence records above (``ObservationDraft``,
# ``MeasurementObservation`` and ``EvidenceReview``) intentionally model one
# very specific import workflow.  The records below are the product-agnostic
# M1 vocabulary.  They are immutable snapshots as well, but keep sensible
# defaults for ``revision_id``/``meta`` so adapters can construct a first
# revision from a small JSON document.


class Context(FrozenModel):
    """A declared task, environmental and social setting.

    Context is descriptive only.  It must not be interpreted as a classifier
    for intent, emotion or health state.
    """

    context_id: Identifier = Field(validation_alias=AliasChoices("context_id", "id"))
    name: Identifier
    task: Identifier | None = None
    environment: Identifier | None = None
    social_conditions: tuple[str, ...] = ()
    target_population: Identifier | None = None
    unknowns: tuple[str, ...] = ()
    revision_id: Identifier = "context.r1"
    meta: RevisionMeta = Field(
        default_factory=lambda: RevisionMeta(
            revision=1, created_by="system", reason="context created"
        )
    )

    @property
    def id(self) -> str:
        return self.context_id


class PhysicalFeature(FrozenModel):
    """A physical/design feature without an implied psychological outcome."""

    feature_id: Identifier = Field(validation_alias=AliasChoices("feature_id", "id"))
    name: Identifier
    description: Identifier | None = None
    affordances: tuple[str, ...] = ()
    material: str | None = None
    dimensions: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    revision_id: Identifier = "physical-feature.r1"
    meta: RevisionMeta = Field(
        default_factory=lambda: RevisionMeta(
            revision=1, created_by="system", reason="physical feature created"
        )
    )

    @property
    def id(self) -> str:
        return self.feature_id


class Evidence(FrozenModel):
    """A traceable source for an observation or hypothesis claim.

    ``quote_or_locator`` is intentionally opaque: text and interview sources
    use a quote, images use a region description, videos use a time locator,
    and sensor/experiment sources use a file or record locator.  The source
    itself is never treated as proof merely because it is present.
    """

    evidence_id: Identifier = Field(
        default="evidence.r1", validation_alias=AliasChoices("evidence_id", "id")
    )
    kind: Literal["text", "image", "video", "audio", "sensor", "interview", "experiment"] = Field(
        validation_alias=AliasChoices("kind", "source_kind", "source_type")
    )
    artifact_id: Identifier = Field(validation_alias=AliasChoices("artifact_id", "source_id", "artifact"))
    quote_or_locator: Identifier = Field(
        validation_alias=AliasChoices("quote_or_locator", "locator", "source_locator", "quote")
    )
    source_text: str | None = None
    image_region: str | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    sensor_file: str | None = None
    experiment_record: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    provenance: Literal[
        "declared",
        "observed",
        "reported",
        "inferred",
        "prototype_measurement",
        "external_measurement",
        "blender_derived",
        "design_derived",
    ] = "declared"
    evidence_role: Literal[
        "design_observation",
        "physical_measurement",
        "user_report",
        "experiment_result",
        "context",
    ] = "design_observation"
    notes: tuple[str, ...] = ()
    revision_id: Identifier = "evidence.r1"
    meta: RevisionMeta = Field(
        default_factory=lambda: RevisionMeta(
            revision=1, created_by="system", reason="evidence imported"
        )
    )
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def validate_locator(self) -> "Evidence":
        if self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("evidence end_ms must be greater than or equal to start_ms")
        if self.kind == "video" and self.start_ms is None and self.end_ms is None and not self.quote_or_locator:
            raise ValueError("video evidence requires a time range or locator")
        if self.kind == "image" and self.image_region is not None and not self.image_region.strip():
            raise ValueError("image evidence region cannot be empty")
        # GLB/PNG/Blender outputs are review/design material.  They may not be
        # relabelled as a physical measurement or experimental result.
        artifact = self.artifact_id.lower()
        derived_visual = self.provenance in {"blender_derived", "design_derived"} or artifact.endswith(
            (".glb", ".gltf", ".png")
        )
        if derived_visual and self.evidence_role in {"physical_measurement", "experiment_result"}:
            raise ValueError("Blender/GLB/PNG evidence is design observation only, not physical performance evidence")
        return self

    @property
    def id(self) -> str:
        return self.evidence_id


class Observation(FrozenModel):
    """A source-bound, non-causal observation.

    Psychological conclusions belong in ``ExperienceHypothesis``.  A direct
    psychological predicate is therefore only permitted when explicitly
    marked as a participant report and backed by interview/experiment source.
    """

    observation_id: Identifier = Field(validation_alias=AliasChoices("observation_id", "id"))
    subject: Identifier
    predicate: Identifier
    value: Identifier
    context_id: str | None = None
    context: Context | None = None
    evidence: tuple[Evidence, ...] = Field(
        default=(), validation_alias=AliasChoices("evidence", "sources", "evidence_refs")
    )
    certainty: Literal[
        "observed",
        "reported",
        "inferred",
        "exploratory",
        "tested",
        "supported",
        "rejected",
    ] = "observed"
    # ``status`` is retained separately so callers can distinguish source
    # certainty from a hypothesis/evidence lifecycle state.
    status: Literal[
        "observed",
        "reported",
        "inferred",
        "exploratory",
        "tested",
        "supported",
        "rejected",
    ] = "observed"
    observation_type: Literal[
        "physical_feature",
        "user_action",
        "context",
        "behavior",
        "self_report",
        "psychological",
        "other",
    ] = "other"
    unknowns: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    revision_id: Identifier = "observation.r1"
    meta: RevisionMeta = Field(
        default_factory=lambda: RevisionMeta(
            revision=1, created_by="system", reason="observation recorded"
        )
    )
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def source_and_claim_boundary(self) -> "Observation":
        if not self.evidence:
            raise ValueError("an observation fact requires at least one traceable evidence source")
        psych_terms = (
            "feel",
            "feels",
            "emotion",
            "trust",
            "safe",
            "safety",
            "comfortable",
            "comfort",
            "安心",
            "信任",
            "情绪",
            "舒适",
        )
        direct_psychology = self.observation_type == "psychological" or any(
            token in self.predicate.lower() for token in psych_terms
        )
        if direct_psychology:
            if self.certainty != "reported" or not any(
                item.kind in {"interview", "experiment"} for item in self.evidence
            ):
                raise ValueError(
                    "observations cannot assert a psychological conclusion; record a participant report and test it as a hypothesis"
                )
        if (self.certainty == "supported" or self.status == "supported") and not any(item.kind == "experiment" for item in self.evidence):
            raise ValueError("a supported observation requires real experiment evidence")
        return self

    @property
    def id(self) -> str:
        return self.observation_id


class ExperienceHypothesis(FrozenModel):
    """A conditional, falsifiable link between design and experience."""

    hypothesis_id: Identifier = Field(validation_alias=AliasChoices("hypothesis_id", "id"))
    target_population: Identifier = Field(
        validation_alias=AliasChoices("target_population", "target_users", "population")
    )
    task_condition: Identifier = Field(
        validation_alias=AliasChoices("task_condition", "task", "task_context")
    )
    # Compatibility shorthand from the early platform spec.  The explicit
    # task/environment/social fields remain authoritative for M1 validation.
    context: str | None = None
    environment_condition: Identifier = Field(
        validation_alias=AliasChoices("environment_condition", "environment")
    )
    social_condition: Identifier = Field(
        validation_alias=AliasChoices("social_condition", "social", "social_context")
    )
    physical_features: tuple[str, ...] = ()
    user_actions: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("user_actions", "actions")
    )
    construct: Identifier
    mechanism: Identifier
    predicted_outcome: Identifier = Field(
        validation_alias=AliasChoices("predicted_outcome", "prediction", "predicted_result")
    )
    alternative_explanations: tuple[str, ...] = Field(min_length=1)
    evidence: tuple[Evidence, ...] = Field(
        default=(), validation_alias=AliasChoices("evidence", "sources", "evidence_refs")
    )
    unknowns: tuple[str, ...] = ()
    validation_method: Identifier = Field(
        validation_alias=AliasChoices("validation_method", "verification_method", "validation")
    )
    confidence: float = Field(default=0.0, ge=0, le=1)
    status: Literal["exploratory", "candidate", "tested", "supported", "rejected"] = "exploratory"
    revision_id: Identifier = "hypothesis.r1"
    meta: RevisionMeta = Field(
        default_factory=lambda: RevisionMeta(
            revision=1, created_by="system", reason="experience hypothesis recorded"
        )
    )
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def claim_boundaries(self) -> "ExperienceHypothesis":
        if self.status == "supported" and not any(item.kind == "experiment" for item in self.evidence):
            raise ValueError("a supported hypothesis requires evidence from a real experiment")
        # Over-strong causal language is never accepted as a validated result.
        if self.status == "supported" and _contains_overstrong_claim(
            " ".join((self.mechanism, self.predicted_outcome))
        ):
            raise ValueError("over-strong causal language cannot be marked supported")
        return self

    @property
    def id(self) -> str:
        return self.hypothesis_id


class Critique(FrozenModel):
    """Candidate-level summary of evidence-backed review items."""

    critique_id: Identifier = Field(validation_alias=AliasChoices("critique_id", "id"))
    candidate_id: Identifier
    hypotheses: tuple[ExperienceHypothesis, ...] = ()
    observation_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    hard_risks: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    actionable_changes: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    experiment_plan_ids: tuple[str, ...] = ()
    human_decision_required: tuple[str, ...] = ()
    status: Literal["draft", "reviewed", "approved", "rejected"] = "draft"
    reviewer: str | None = None
    decision_rationale: str | None = None
    revision_id: Identifier = "critique.r1"
    meta: RevisionMeta = Field(
        default_factory=lambda: RevisionMeta(
            revision=1, created_by="system", reason="candidate critique recorded"
        )
    )
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def approval_gate(self) -> "Critique":
        if self.status == "approved" and not self.reviewer:
            raise ValueError("an approved critique requires a human reviewer")
        return self

    @property
    def id(self) -> str:
        return self.critique_id


class DesignFeedbackSelection(FrozenModel):
    """Human selection and next-round prompt from the M3 feedback bundle."""

    selection_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    candidate_id: Identifier
    candidate_revision_id: Identifier
    critique_id: Identifier
    ranked_candidate_ids: tuple[str, ...]
    next_prompt_json: Identifier
    actor: Identifier
    # Formal-iteration lineage is optional for draft briefs, but once a
    # frozen brief is attached to an iteration these links make the M3
    # snapshot queryable alongside the canonical SelectionDecision chain.
    iteration_id: Identifier | None = None
    selection_decision_id: Identifier | None = None
    # Required when a human deliberately chooses a candidate other than the
    # deterministic first-ranked candidate.  It is retained even when the
    # selection is later projected into a second-round prompt.
    override_reason: Identifier | None = None
    confirmed_patch_revision_ids: tuple[str, ...] = ()
    status: Literal["confirmed", "rejected"] = "confirmed"
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def selection_is_ranked(self) -> "DesignFeedbackSelection":
        if self.candidate_id not in self.ranked_candidate_ids:
            raise ValueError("selected candidate must occur in the ranked candidate IDs")
        return self


def _contains_overstrong_claim(text: str) -> bool:
    """Return whether *text* uses deterministic/overclaiming causal language."""

    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "必然",
            "证明",
            "一定导致",
            "必定导致",
            "必然导致",
            "inevitably",
            "proves",
            "proven",
            "definitely causes",
            "always causes",
            "guarantees",
            "guaranteed to",
        )
    )


class ValidationTask(FrozenModel):
    task_id: Identifier
    research_question: Identifier
    competing_hypotheses: tuple[str, ...]
    comparison_conditions: tuple[str, ...]
    measures: tuple[str, ...]
    confounds: tuple[str, ...]
    minimum_evidence: Identifier


class PrototypeAsset(FrozenModel):
    """An input file used by a prototype run.

    Assets are provenance records, not evidence by themselves.  In particular,
    Blender exports are explicitly classified as derived review material and
    cannot be promoted by an import operation.
    """

    asset_id: Identifier
    meta: RevisionMeta = Field(default_factory=lambda: RevisionMeta(revision=1, created_by="system", reason="asset imported"))
    uri: Identifier
    sha256: Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")] = Field(validation_alias=AliasChoices("sha256", "content_hash", "file_hash"))
    provider: Identifier
    role: Identifier = "measurement_source"
    provenance: Literal["prototype_measurement", "external_measurement", "blender_derived", "design_derived"] = "external_measurement"
    content_type: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def blender_is_derived(self) -> "PrototypeAsset":
        if self.provenance in {"blender_derived", "design_derived"} and self.provider.lower() != "blender":
            raise ValueError("derived design assets must name blender as provider")
        return self

    @property
    def content_hash(self) -> str:
        return self.sha256


class ImageRegion(FrozenModel):
    """A bounded image region, in normalized or pixel coordinates."""

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    coordinate_space: Literal["normalized", "pixels"] = "normalized"
    label: str | None = None

    @model_validator(mode="after")
    def bounds(self) -> "ImageRegion":
        if self.coordinate_space == "normalized" and (self.x + self.width > 1 or self.y + self.height > 1):
            raise ValueError("normalized image region must stay within the unit frame")
        return self


class VideoTimeSegment(FrozenModel):
    """A half-open source-video interval in milliseconds."""

    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    label: str | None = None

    @model_validator(mode="after")
    def ordered(self) -> "VideoTimeSegment":
        if self.end_ms <= self.start_ms:
            raise ValueError("video segment end_ms must be greater than start_ms")
        return self


class ExternalAsset(FrozenModel):
    """A hash-addressed external design asset awaiting human interpretation."""

    asset_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta = Field(default_factory=lambda: RevisionMeta(revision=1, created_by="system", reason="external asset imported"))
    uri: Identifier
    sha256: Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")] = Field(
        validation_alias=AliasChoices("sha256", "content_hash", "file_hash")
    )
    provider: Identifier
    request_id: str | None = None
    asset_kind: Literal[
        "glb", "gltf", "png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif",
        "mp4", "mov", "webm", "mkv", "m4v", "avi", "wav", "mp3", "cad", "other",
    ] = "other"
    modality: Literal["image", "video", "audio", "geometry", "cad", "other", "unknown"] = "unknown"
    provenance: Literal["external", "blender_derived", "design_derived"] = "external"
    candidate_revision_id: str | None = None
    model_revision_id: str | None = None
    status: Literal["imported", "unavailable", "superseded"] = "imported"
    calibration_status: Literal["unknown", "uncalibrated", "calibrated", "not_applicable"] = "unknown"
    calibration_ref: str | None = None
    width_px: int | None = Field(default=None, gt=0)
    height_px: int | None = Field(default=None, gt=0)
    duration_ms: int | None = Field(default=None, gt=0)
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def infer_modality_and_calibration(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        kind = str(payload.get("asset_kind", "other")).lower()
        if payload.get("modality") in {None, "unknown"}:
            if kind in {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif"}:
                payload["modality"] = "image"
            elif kind in {"mp4", "mov", "webm", "mkv", "m4v", "avi"}:
                payload["modality"] = "video"
            elif kind in {"wav", "mp3"}:
                payload["modality"] = "audio"
            elif kind in {"glb", "gltf"}:
                payload["modality"] = "geometry"
            elif kind == "cad":
                payload["modality"] = "cad"
        if "calibration_status" not in payload:
            payload["calibration_status"] = (
                "uncalibrated" if payload.get("modality") in {"image", "video"} else "not_applicable"
            )
        return payload

    @model_validator(mode="after")
    def derived_provider_boundary(self) -> "ExternalAsset":
        if self.provenance in {"blender_derived", "design_derived"} and self.provider.lower() != "blender":
            raise ValueError("derived external assets must name blender as provider")
        if self.calibration_status == "calibrated" and not self.calibration_ref:
            raise ValueError("calibrated external assets require calibration_ref")
        if self.modality == "image" and self.duration_ms is not None:
            raise ValueError("image assets cannot declare a video duration")
        return self


class ObservationDraft(FrozenModel):
    """Untrusted interpretation of an external asset; not a candidate fact."""

    draft_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta = Field(default_factory=lambda: RevisionMeta(revision=1, created_by="system", reason="observation draft imported"))
    asset_ids: tuple[str, ...] = Field(min_length=1)
    candidate_revision_id: Identifier
    source_fact_id: Identifier
    subject: Identifier
    predicate: Identifier
    proposed_value: Identifier
    method: Identifier
    required_modalities: tuple[Literal["image", "video", "audio", "geometry", "cad"], ...] = ()
    missing_modalities: tuple[Literal["image", "video", "audio", "geometry", "cad"], ...] = ()
    image_region: ImageRegion | str | None = None
    video_segment: VideoTimeSegment | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, gt=0)
    claim_category: Literal[
        "visual_attribute", "motion", "dimension", "pressure", "strength", "comfort", "other"
    ] = Field(default="other", validation_alias=AliasChoices("claim_category", "claim_type"))
    observable_status: Literal["draft", "unknown", "not_observable", "conflicted"] = "draft"
    not_observable_items: tuple[str, ...] = (
        "engineering dimensions",
        "fit and comfort",
        "movement stability and performance",
    )
    limitations: tuple[str, ...] = (
        "An external asset supports visual/design observation only; it does not establish engineering dimensions, fit, comfort or physical performance.",
    )
    confirmation: Literal["pending", "accepted", "modified", "rejected"] = "pending"
    confirmed_observation_id: str | None = None

    @model_validator(mode="after")
    def non_observable_reason(self) -> "ObservationDraft":
        if self.observable_status in {"unknown", "not_observable", "conflicted"} and not self.not_observable_items:
            raise ValueError("not-observable or conflicted drafts require explicit limitations")
        if self.observable_status == "unknown" and not self.missing_modalities:
            raise ValueError("unknown observation drafts require explicit missing modalities")
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("video observation requires both start_ms and end_ms")
        if self.start_ms is not None and self.end_ms is not None and self.end_ms <= self.start_ms:
            raise ValueError("video observation end_ms must be greater than start_ms")
        if self.video_segment is not None and self.start_ms is not None:
            if (self.video_segment.start_ms, self.video_segment.end_ms) != (self.start_ms, self.end_ms):
                raise ValueError("video_segment conflicts with start_ms/end_ms")
        return self

    @property
    def effective_video_segment(self) -> VideoTimeSegment | None:
        if self.video_segment is not None:
            return self.video_segment
        if self.start_ms is not None and self.end_ms is not None:
            return VideoTimeSegment(start_ms=self.start_ms, end_ms=self.end_ms)
        return None


class PrototypeRun(FrozenModel):
    """One execution/import of a pre-registered prototype protocol."""

    run_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    protocol_id: Identifier
    protocol_revision: Identifier = Field(default="v1", validation_alias=AliasChoices("protocol_revision", "protocol_revision_id"))
    candidate_revision_id: Identifier
    model_revision_id: str | None = None
    device_revision: Identifier = Field(validation_alias=AliasChoices("device_revision", "device_revision_id"))
    conditions: tuple[str, ...]
    participant_scope: Identifier = Field(validation_alias=AliasChoices("participant_scope", "participant_context"))
    context_scope: Identifier = Field(validation_alias=AliasChoices("context_scope", "context"))
    source_assets: tuple[PrototypeAsset, ...] = ()
    protocol_snapshot: dict[str, object] = Field(default_factory=dict)
    status: Literal["imported", "in_progress", "completed", "failed"] = "imported"
    import_source: Literal["manual", "measurement_file", "external_runner"] = "manual"
    notes: str | None = None
    dependencies: tuple[DependencyRef, ...] = ()
    experiment_revision_id: str | None = None
    condition_snapshot_ids: tuple[str, ...] = ()
    hypothesis_binding_ids: tuple[str, ...] = ()
    analysis_family_revision_id: str | None = None
    analysis_protocol_review_id: str | None = None

    @model_validator(mode="after")
    def formal_analysis_lineage(self) -> "PrototypeRun":
        declared = any((
            self.experiment_revision_id,
            self.condition_snapshot_ids,
            self.hypothesis_binding_ids,
            self.analysis_family_revision_id,
            self.analysis_protocol_review_id,
        ))
        if declared and not all((
            self.experiment_revision_id,
            self.condition_snapshot_ids,
            self.hypothesis_binding_ids,
            self.analysis_family_revision_id,
            self.analysis_protocol_review_id,
        )):
            raise ValueError("formal prototype runs require complete M2 analysis lineage")
        return self

    @property
    def protocol_revision_id(self) -> str:
        return self.protocol_revision

    @property
    def device_revision_id(self) -> str:
        return self.device_revision

    @property
    def participant_context(self) -> str:
        return self.participant_scope

    @property
    def context(self) -> str:
        return self.context_scope


class MeasurementObservation(FrozenModel):
    """A measurement imported from a run, awaiting independent human review."""

    observation_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    run_id: Identifier
    measure_id: Identifier
    metric: Identifier
    method: Identifier = Field(validation_alias=AliasChoices("method", "measurement_method"))
    condition: Identifier
    value: ScalarValue | None = Field(default=None, validation_alias=AliasChoices("value", "measured_value"))
    unit: str | None = None
    participant_scope: Identifier | None = None
    context_scope: Identifier | None = None
    source_asset_ids: tuple[str, ...] = ()
    status: Literal["draft", "confirmed", "rejected", "not_observable", "technical_failure"] = "draft"
    missing_reason: Literal["not_declared", "not_observable", "not_measured", "conflicted", "technical_failure"] | None = None
    technical_failure_reason: str | None = None
    provenance: Literal["prototype_measurement", "external_measurement", "blender_derived", "design_derived"] = "prototype_measurement"
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None
    raw_file_hash: Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")] | None = Field(default=None, validation_alias=AliasChoices("raw_file_hash", "source_file_hash", "file_hash"))
    condition_snapshot_revision_id: str | None = None
    hypothesis_binding_ids: tuple[str, ...] = ()
    analysis_family_revision_id: str | None = None
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def validate_missing_and_value(self) -> "MeasurementObservation":
        if self.status in {"not_observable", "technical_failure"} and not self.missing_reason:
            raise ValueError("unavailable observations require missing_reason")
        if self.missing_reason and self.value is not None:
            raise ValueError("an unavailable observation cannot contain a value")
        if self.provenance in {"blender_derived", "design_derived"} and self.status == "confirmed":
            raise ValueError("derived design material cannot be confirmed as a measurement")
        return self

    @property
    def measurement_method(self) -> str:
        return self.method

    @property
    def measured_value(self) -> ScalarValue | None:
        return self.value

    @property
    def source_file_hash(self) -> str | None:
        return self.raw_file_hash


class EvidenceReview(FrozenModel):
    """Human decision over imported observations; never generated by a provider."""

    review_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    run_id: Identifier
    observation_ids: tuple[str, ...]
    reviewer: Identifier
    decision: Literal["pending", "accepted", "modified", "confirmed", "rejected", "insufficient"] = Field(default="pending", validation_alias=AliasChoices("decision", "status", "review_status"))
    evidence_level_before: Literal["none", "exploratory", "observed", "supported", "replicated"] = "none"
    evidence_level_after: Literal["none", "exploratory", "observed", "supported", "replicated"] = "none"
    confirmed_observation_ids: tuple[str, ...] = ()
    rationale: Identifier = "pending human review"
    limitations: tuple[str, ...] = ()
    experiment_revision_id: str | None = None
    condition_snapshot_ids: tuple[str, ...] = ()
    hypothesis_binding_ids: tuple[str, ...] = ()
    analysis_family_revision_id: str | None = None
    analysis_protocol_review_id: str | None = None
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def gate_promotion(self) -> "EvidenceReview":
        if self.decision in {"accepted", "modified", "confirmed"} and not self.confirmed_observation_ids:
            raise ValueError("an accepting evidence review must name confirmed observations")
        if self.decision in {"accepted", "modified", "confirmed"} and self.evidence_level_after == "none":
            raise ValueError("an accepting evidence review must declare a non-none evidence level")
        if self.decision not in {"accepted", "modified", "confirmed"} and self.evidence_level_after != "none":
            raise ValueError("non-accepting evidence reviews cannot promote evidence")
        if self.evidence_level_after != "none" and self.evidence_level_before == "none" and self.decision not in {"accepted", "modified", "confirmed"}:
            raise ValueError("evidence promotion requires an explicit human decision")
        if self.decision in {"rejected", "insufficient", "pending"} and self.confirmed_observation_ids:
            raise ValueError("non-accepting evidence review cannot confirm observations")
        return self

    @property
    def status(self) -> str:
        return self.decision

    @property
    def evidence_level(self) -> str:
        return self.evidence_level_after


class PatchScope(FrozenModel):
    global_scope: bool = False
    scenario_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    user_segments: tuple[str, ...] = ()
    time_or_device_modes: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def scope_is_explicit(self) -> "PatchScope":
        has_specific_scope = any(
            (self.scenario_ids, self.event_ids, self.user_segments, self.time_or_device_modes)
        )
        if self.global_scope == has_specific_scope:
            raise ValueError("declare either global_scope or at least one specific scope")
        return self


class VariablePatch(FrozenModel):
    patch_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    review_item_revision_id: Identifier
    variable_id: Identifier
    operation: Literal["set", "replace", "add", "remove", "constrain", "relax"]
    from_value: DesignVariableValue | None = None
    to_value: DesignVariableValue | None = None
    scope: PatchScope
    enforcement: Literal["must", "should", "explore"]
    rationale: Identifier
    evidence_refs: tuple[str, ...]
    expected_effect: Identifier
    risks: tuple[str, ...] = ()
    verification: Identifier
    status: Literal["confirmed", "withdrawn"] = "confirmed"

    @model_validator(mode="after")
    def values_match_variable(self) -> "VariablePatch":
        for value in (self.from_value, self.to_value):
            if value is not None and value.variable_id != self.variable_id:
                raise ValueError("patch values must use patch variable_id")
        if self.enforcement == "must" and not self.scope.global_scope and not any(
            (self.scope.scenario_ids, self.scope.event_ids, self.scope.user_segments)
        ):
            raise ValueError("must patch requires a concrete scenario/event/user scope")
        return self


class PatchConflict(FrozenModel):
    """Explicit conflict analysis for overlapping VariablePatch revisions."""

    left_revision_id: Identifier
    right_revision_id: Identifier
    variable_id: Identifier
    scope_overlap: bool = True
    classification: Literal["blocking", "shadowed", "exploratory", "compatible"]
    winning_revision_id: str | None = None
    reason: Identifier


class VariablePatchDraft(BoundaryModel):
    patch_id: Identifier
    variable_id: Identifier
    operation: Literal["set", "replace", "add", "remove", "constrain", "relax"]
    from_value: DesignVariableValue | None = None
    to_value: DesignVariableValue | None = None
    scope: PatchScope
    suggested_enforcement: Literal["must", "should", "explore"] = "should"
    rationale: Identifier
    evidence_refs: list[str]
    expected_effect: Identifier
    risks: list[str] = Field(default_factory=list)
    verification: Identifier


class ReviewItemDraft(BoundaryModel):
    review_item_id: Identifier
    event_id: Identifier
    criterion_ids: list[str]
    fact_ids: list[str]
    context: Identifier
    observation: Identifier
    hypothesis: Identifier
    alternative_explanations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference]
    proposed_alignment: Literal[
        "strong_support", "support", "neutral", "risk", "strong_risk", "unknown"
    ]
    status: Literal["blocked", "revise", "explore"]
    risk: Identifier
    tradeoff: Identifier
    actionable_changes: list[VariablePatchDraft] = Field(default_factory=list)
    approved_rule_ids: list[str] = Field(default_factory=list)
    unblock_condition: str | None = None
    validation_task: ValidationTask | None = None


class ClaimJudgement(BoundaryModel):
    review_item_id: Identifier
    verdict: Literal["supported", "partially_supported", "unsupported", "overclaimed"]
    evidence_refs: list[str]
    rationale: Identifier


class ReviewItem(FrozenModel):
    review_item_id: Identifier
    review_item_revision_id: Identifier
    meta: RevisionMeta
    candidate_id: Identifier
    candidate_revision_id: Identifier
    facts_snapshot_id: Identifier
    brief_revision_id: Identifier
    event_id: Identifier
    criterion_ids: tuple[str, ...]
    fact_ids: tuple[str, ...]
    context: Identifier
    observation: Identifier
    hypothesis: Identifier
    alternative_explanations: tuple[str, ...] = ()
    evidence: tuple[EvidenceReference, ...]
    alignment: Literal[
        "strong_support", "support", "neutral", "risk", "strong_risk", "unknown"
    ]
    outcome_evidence: Literal["none", "exploratory", "observed", "supported", "replicated"] = (
        "none"
    )
    status: Literal["blocked", "revise", "explore"]
    risk: Identifier
    tradeoff: Identifier
    variable_patches: tuple[VariablePatch, ...] = ()
    approved_rule_ids: tuple[str, ...] = ()
    unblock_condition: str | None = None
    validation_task: ValidationTask | None = None
    claim_judgement: ClaimJudgement
    confirmation: Literal["confirmed", "overridden"] = "confirmed"
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def status_requirements(self) -> "ReviewItem":
        if self.status == "blocked" and (
            not self.approved_rule_ids or not self.unblock_condition
        ):
            raise ValueError("blocked review item requires an approved rule and unblock path")
        if self.status == "explore" and self.validation_task is None:
            raise ValueError("explore review item requires a validation task")
        return self

    @property
    def id(self) -> str:
        return self.review_item_id


class CriterionAssessment(FrozenModel):
    criterion_id: Identifier
    alignment: Literal[
        "strong_support", "support", "neutral", "risk", "strong_risk", "unknown"
    ]
    outcome_evidence: Literal["none", "exploratory", "observed", "supported", "replicated"]
    review_item_revision_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    mechanism_tension: bool = False


class EventCoverage(FrozenModel):
    event_id: Identifier
    status: Literal["covered", "partial", "unknown", "blocked"]
    review_item_revision_ids: tuple[str, ...]
    missing: tuple[str, ...] = ()


class CandidateEvaluationRecord(FrozenModel):
    evaluation_id: Identifier
    meta: RevisionMeta
    candidate_id: Identifier
    candidate_revision_id: Identifier
    facts_snapshot_id: Identifier
    brief_revision_id: Identifier
    criterion_assessments: tuple[CriterionAssessment, ...]
    event_coverage: tuple[EventCoverage, ...]
    blocked_rule_ids: tuple[str, ...] = ()
    unresolved_conflict_ids: tuple[str, ...] = ()
    unmet_must_patch_ids: tuple[str, ...] = ()
    dependencies: tuple[DependencyRef, ...] = ()


class PartialOrderTier(StrEnum):
    PREFERRED = "preferred"
    VIABLE_ALTERNATIVES = "viable_alternatives"
    NEEDS_EVIDENCE = "needs_evidence"
    BLOCKED = "blocked"


class PartialOrderReason(FrozenModel):
    candidate_id: Identifier
    tier: PartialOrderTier
    codes: tuple[str, ...]
    criterion_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


class CandidatePartialOrder(FrozenModel):
    partial_order_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    iteration_id: Identifier
    preferred_set_id: Identifier
    preferred: tuple[str, ...]
    viable_alternatives: tuple[str, ...]
    needs_evidence: tuple[str, ...]
    blocked: tuple[str, ...]
    incomparable_pairs: tuple[tuple[str, str], ...] = ()
    reasons: tuple[PartialOrderReason, ...]
    dependencies: tuple[DependencyRef, ...] = ()

    @property
    def tiers(self) -> dict[str, tuple[str, ...]]:
        return {
            PartialOrderTier.PREFERRED.value: self.preferred,
            PartialOrderTier.VIABLE_ALTERNATIVES.value: self.viable_alternatives,
            PartialOrderTier.NEEDS_EVIDENCE.value: self.needs_evidence,
            PartialOrderTier.BLOCKED.value: self.blocked,
        }


class SelectionDecision(FrozenModel):
    decision_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    iteration_id: Identifier
    partial_order_id: Identifier
    action: Literal["select", "explore_further", "hold", "compose", "reject", "override"]
    candidate_ids: tuple[str, ...]
    decision_basis: tuple[str, ...]
    overridden_tier: str | None = None
    accepted_tradeoffs: tuple[str, ...] = ()
    rejected_tradeoffs: tuple[str, ...] = ()
    required_followups: tuple[str, ...] = ()
    rationale: Identifier
    dependencies: tuple[DependencyRef, ...] = ()


class NextDesignPrompt(FrozenModel):
    prompt_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    iteration_id: Identifier
    selected_candidate_revision_ids: tuple[str, ...]
    confirmed_patch_revision_ids: tuple[str, ...]
    validation_task_ids: tuple[str, ...] = ()
    status: Literal["confirmed"] = "confirmed"
    dependencies: tuple[DependencyRef, ...] = ()


class IterationStatus(StrEnum):
    CREATED = "created"
    CANDIDATES_IMPORTED = "candidates_imported"
    FACTS_FROZEN = "facts_frozen"
    REVIEWS_CONFIRMED = "reviews_confirmed"
    COMPARED = "compared"
    SELECTED = "selected"
    PROMPT_CONFIRMED = "prompt_confirmed"
    COMPLETED = "completed"


class DesignIteration(FrozenModel):
    iteration_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    round_number: Literal[1, 2]
    parent_iteration_id: str | None = None
    status: IterationStatus = IterationStatus.CREATED
    candidate_revision_ids: tuple[str, ...] = ()
    divergence_gaps: tuple[str, ...] = ()
    facts_snapshot_ids: tuple[str, ...] = ()
    review_item_revision_ids: tuple[str, ...] = ()
    evaluation_ids: tuple[str, ...] = ()
    partial_order_id: str | None = None
    selection_decision_id: str | None = None
    next_prompt_id: str | None = None
    variable_repair_trace_ids: tuple[str, ...] = ()
    dependencies: tuple[DependencyRef, ...] = ()


class PatchApplicationTrace(FrozenModel):
    patch_revision_id: Identifier
    variable_id: Identifier
    from_value: DesignVariableValue | None
    expected_value: DesignVariableValue | None
    actual_value: DesignVariableValue | None
    adoption: Literal["adopted", "partially_adopted", "not_adopted", "unverifiable"]
    generator_declaration: str | None = None
    reason: Identifier


class IssueImprovement(FrozenModel):
    review_item_revision_id: Identifier
    status: Literal["improved", "unchanged", "worsened", "indeterminate"]
    evidence_refs: tuple[str, ...]
    reason: Identifier


class VariableRepairTrace(FrozenModel):
    trace_id: Identifier
    meta: RevisionMeta
    parent_candidate_revision_id: Identifier
    child_candidate_revision_id: Identifier
    brief_revision_id: Identifier
    patch_applications: tuple[PatchApplicationTrace, ...]
    issue_improvements: tuple[IssueImprovement, ...]
    dependencies: tuple[DependencyRef, ...] = ()


class DomainEvent(FrozenModel):
    event_id: Identifier
    event_type: Identifier
    aggregate_id: Identifier
    aggregate_revision_id: Identifier
    occurred_at: datetime = Field(default_factory=utc_now)
    data: tuple[tuple[str, str], ...] = ()


class AuditEvent(FrozenModel):
    audit_id: Identifier
    action: Identifier
    target_id: Identifier
    target_revision_id: Identifier
    actor: Identifier
    reason: Identifier
    occurred_at: datetime = Field(default_factory=utc_now)
    expected_revision: int | None = Field(default=None, ge=1)


# Contamination/quarantine models -------------------------------------------------
#
# These records deliberately live beside the other immutable domain snapshots.  A
# quarantine is an audit fact, not a mutable flag on a candidate or review; clean
# reruns therefore always create a separate record/revision and retain the old
# contaminated revision.


class UnauthorizedOutput(FrozenModel):
    """Output produced by an execution that was not authorized at the time."""

    output_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta = Field(default_factory=lambda: RevisionMeta(revision=1, created_by="system", reason="unauthorized output quarantined"))
    output_type: Literal[
        "candidate",
        "review_draft",
        "facts",
        "review_item",
        "partial_order",
        "feedback",
        "experiment_result",
        "other",
    ]
    execution_id: Identifier
    produced_at: datetime = Field(default_factory=utc_now)
    status: Literal["unauthorized_output_quarantined"] = "unauthorized_output_quarantined"
    access_control: Identifier
    isolation_state: Literal["quarantined", "deleted", "pending"] = "quarantined"
    deletion_or_isolation_proof: str | None = None
    impact_analysis_id: str | None = None


class ContaminationMark(FrozenModel):
    """Immutable status for a downstream object in an output's data lineage."""

    object_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta = Field(default_factory=lambda: RevisionMeta(revision=1, created_by="system", reason="unauthorized output contamination recorded"))
    object_type: Identifier
    status: Literal["unauthorized_output_contaminated"] = "unauthorized_output_contaminated"
    source_output_ids: tuple[str, ...]
    dependencies: tuple[DependencyRef, ...] = ()
    support_paused: bool = True
    access_evidence: tuple[str, ...] = ()


class CleanRerunClosure(FrozenModel):
    """Proof that every clean-rerun input boundary was checked."""

    direct_inputs_closed: bool = False
    prompts_closed: bool = False
    caches_closed: bool = False
    retrieval_indexes_closed: bool = False
    dependency_data_closed: bool = False
    environment_closed: bool = False
    model_context_closed: bool = False
    output_storage_closed: bool = False
    new_workspace: bool = False
    independent_environment: bool = False
    frozen_parameters: bool = False
    reproducible_logs: bool = False
    proof_refs: tuple[str, ...] = ()
    contamination_refs: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """Whether the closure satisfies ADR 0427's fail-closed boundary."""

        return all(
            (
                self.direct_inputs_closed,
                self.prompts_closed,
                self.caches_closed,
                self.retrieval_indexes_closed,
                self.dependency_data_closed,
                self.environment_closed,
                self.model_context_closed,
                self.output_storage_closed,
                self.new_workspace,
                self.independent_environment,
                self.frozen_parameters,
                self.reproducible_logs,
            )
        ) and not self.contamination_refs


class CleanRerunRecord(FrozenModel):
    """A new revision derived from a contaminated object in a clean workspace."""

    rerun_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta = Field(default_factory=lambda: RevisionMeta(revision=1, created_by="system", reason="clean rerun recorded"))
    source_object_id: Identifier
    source_revision_id: Identifier
    new_object_id: Identifier
    new_object_revision_id: Identifier
    closure: CleanRerunClosure
    status: Literal[
        "clean_rerun_contamination_uncertain",
        "clean_rederived",
        "clean_rederivation_divergence",
    ]
    source_payload_hash: Identifier
    rerun_payload_hash: Identifier
    key_results_consistent: bool | None = None
    impact_analysis_required: bool = False
    impact_analysis_id: str | None = None
    confirmed: bool = False
    lineage: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def status_shape(self) -> "CleanRerunRecord":
        if self.status == "clean_rerun_contamination_uncertain":
            if self.confirmed:
                raise ValueError("an uncertain clean rerun cannot be confirmed")
        elif self.status == "clean_rederived":
            if not self.closure.complete or self.source_payload_hash != self.rerun_payload_hash or self.key_results_consistent is not True:
                raise ValueError("clean_rederived requires complete closure and matching key results")
        elif self.status == "clean_rederivation_divergence":
            if not self.closure.complete or (
                self.source_payload_hash == self.rerun_payload_hash
                and self.key_results_consistent is not False
            ):
                raise ValueError("divergence requires complete closure and an output/result difference")
            if not self.impact_analysis_required:
                raise ValueError("divergence requires impact analysis")
            if self.confirmed:
                raise ValueError("divergent reruns cannot be confirmed as current")
        return self


# Experiment, dependency, arbitration and release-boundary snapshots ---------
# These records intentionally model provenance and gates, not automatic
# evidence qualification.  They are small enough for the V1 SQLite adapter and
# can be extended with new immutable revisions as the workflow evolves.


class HypothesisBinding(FrozenModel):
    binding_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    hypothesis_revision_id: Identifier
    candidate_revision_id: Identifier
    facts_snapshot_id: Identifier
    event_ids: tuple[str, ...] = ()
    role: Literal["primary", "secondary", "exploratory"] = "primary"
    predicted_outcome: Identifier
    measure_ids: tuple[str, ...] = ()
    analysis_family_id: Identifier | None = None
    status: Literal["current", "stale", "invalidated"] = "current"
    dependencies: tuple[DependencyRef, ...] = ()

    @model_validator(mode="after")
    def binding_shape(self) -> "HypothesisBinding":
        if self.role in {"primary", "secondary"} and not self.measure_ids:
            raise ValueError("primary/secondary hypothesis bindings require measure IDs")
        if self.status != "current" and self.analysis_family_id is None:
            raise ValueError("non-current hypothesis bindings retain their analysis family")
        return self


class AnalysisFamily(FrozenModel):
    family_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    primary_binding_ids: tuple[str, ...] = ()
    secondary_binding_ids: tuple[str, ...] = ()
    exploratory_binding_ids: tuple[str, ...] = ()
    primary_measure_ids: tuple[str, ...] = ()
    correction: Literal["none", "bonferroni", "holm", "fdr", "other"] = "none"
    interpretation_policy: Identifier = "pre-registered interpretation"
    locked: bool = False
    analysis_method: Identifier = "pre-registered model with uncertainty interval"
    multiplicity_policy: Identifier = "report all declared tests; do not select results post hoc"

    @model_validator(mode="after")
    def no_duplicate_bindings(self) -> "AnalysisFamily":
        groups = self.primary_binding_ids + self.secondary_binding_ids + self.exploratory_binding_ids
        if len(set(groups)) != len(groups):
            raise ValueError("an analysis family binding cannot occur in multiple tiers")
        if self.locked and not self.primary_measure_ids:
            raise ValueError("locked analysis family requires primary measures")
        if self.locked and not self.primary_binding_ids:
            raise ValueError("locked analysis family requires a primary binding")
        if len(self.primary_binding_ids) > 1 and self.correction == "none":
            raise ValueError("multiple primary bindings require a multiplicity correction")
        return self


class ExperimentVariable(FrozenModel):
    """One manipulated variable in an M2 experiment plan."""

    variable_id: Identifier
    label: Identifier
    levels: tuple[Identifier, ...] = Field(min_length=2)
    manipulation: Identifier
    assignment: Literal["randomized", "counterbalanced", "within_subject", "between_subject", "fixed"] = "between_subject"

    @model_validator(mode="after")
    def unique_levels(self) -> "ExperimentVariable":
        if len(set(self.levels)) != len(self.levels):
            raise ValueError("experiment variable levels must be unique")
        return self


class MeasureSpec(FrozenModel):
    """A dependent measure with an operational collection method."""

    measure_id: Identifier
    label: Identifier
    operational_definition: Identifier
    method: Identifier
    unit: str | None = None
    primary: bool = False
    missingness_policy: Identifier = "record missingness and do not impute silently"


class SamplePlan(FrozenModel):
    """Bounded sample target; it is planning metadata, not recruited data."""

    target_population: Identifier
    minimum_n: int = Field(ge=1)
    maximum_n: int = Field(ge=1)
    allocation: Identifier = "balanced across conditions"
    inclusion_criteria: tuple[str, ...] = ()
    exclusion_criteria: tuple[str, ...] = ()

    @model_validator(mode="after")
    def bounded_sample(self) -> "SamplePlan":
        if self.maximum_n < self.minimum_n:
            raise ValueError("sample maximum_n must be >= minimum_n")
        return self


class StoppingRule(FrozenModel):
    """Pre-declared condition that stops or pauses an experiment."""

    rule_id: Identifier
    condition: Identifier
    action: Literal["stop", "pause", "continue_review"]
    owner: Identifier = "researcher"


class ExperimentPlan(FrozenModel):
    experiment_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    brief_revision_id: Identifier
    hypothesis_binding_ids: tuple[str, ...]
    generated_from_hypothesis_id: str | None = None
    research_question: str | None = None
    independent_variables: tuple[ExperimentVariable, ...] = ()
    control_conditions: tuple[str, ...] = ()
    dependent_measures: tuple[MeasureSpec, ...] = ()
    sample_plan: SamplePlan | None = None
    confounds: tuple[str, ...] = ()
    stopping_rules: tuple[StoppingRule, ...] = ()
    success_criteria: tuple[str, ...] = ()
    ethics_notes: tuple[str, ...] = ()
    protocol_snapshot: dict[str, Any] = Field(default_factory=dict)
    condition_snapshot_ids: tuple[str, ...] = ()
    analysis_family_revision_id: Identifier | None = None
    status: Literal["draft", "preregistered", "approved", "started", "completed", "stale", "suspended"] = "draft"
    started_at: datetime | None = None
    start_event_id: str | None = None
    dependencies: tuple[DependencyRef, ...] = ()
    analysis_protocol_review_id: Identifier | None = None
    amendment_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def start_lock(self) -> "ExperimentPlan":
        if self.status == "started" and (self.started_at is None or self.start_event_id is None):
            raise ValueError("started experiment requires immutable start event and timestamp")
        if self.status in {"preregistered", "approved", "started", "completed"} and not self.hypothesis_binding_ids:
            raise ValueError("formal experiment requires at least one hypothesis binding")
        return self


class PreregistrationAmendment(FrozenModel):
    amendment_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    experiment_revision_id: Identifier
    changed_fields: tuple[str, ...]
    reason: Identifier
    approved_by: Identifier
    changed_at: datetime = Field(default_factory=utc_now)
    before_start: bool = True
    status: Literal["accepted", "rejected"] = "accepted"

    @model_validator(mode="after")
    def amendment_timing(self) -> "PreregistrationAmendment":
        if not self.before_start:
            raise ValueError("after-start protocol changes must be recorded as ProtocolDeviation")
        if not self.changed_fields:
            raise ValueError("amendment must name changed fields")
        return self


class ProtocolDeviation(FrozenModel):
    deviation_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    experiment_revision_id: Identifier
    field: Identifier
    planned_value: str | None = None
    actual_value: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)
    impact: Literal["none", "limited", "major", "unknown"] = "unknown"
    status: Literal["recorded", "reviewed"] = "recorded"
    analysis_limitations: tuple[str, ...] = ()


class AnalysisProtocolReview(FrozenModel):
    """Human review gate for a preregistered analysis protocol.

    This record is deliberately separate from ``ExperimentPlan`` so an
    approval is an auditable, immutable decision.  It does not run statistics
    or infer a result; it only establishes that the predeclared protocol is
    complete enough to accept real data.
    """

    review_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    experiment_revision_id: Identifier
    reviewer: Identifier
    sample_size_reviewed: bool = False
    stopping_rules_reviewed: bool = False
    missingness_reviewed: bool = False
    analysis_family_reviewed: bool = False
    condition_lineage_reviewed: bool = False
    status: Literal["pending", "approved", "rejected"] = "pending"
    rationale: Identifier = "pending human analysis-protocol review"
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def approval_requires_all_checks(self) -> "AnalysisProtocolReview":
        checks = (
            self.sample_size_reviewed,
            self.stopping_rules_reviewed,
            self.missingness_reviewed,
            self.analysis_family_reviewed,
            self.condition_lineage_reviewed,
        )
        if self.status == "approved" and (not all(checks) or self.reviewed_at is None):
            raise ValueError("approved analysis protocol review requires every gate and review timestamp")
        if self.status == "pending" and self.reviewed_at is not None:
            raise ValueError("pending analysis protocol review cannot have a review timestamp")
        return self


# Public terminology alias: callers may refer to the same immutable review as
# an analysis-protocol gate without introducing a second persistence type.
AnalysisProtocolGate = AnalysisProtocolReview


class ExperimentStartEvent(FrozenModel):
    event_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    experiment_revision_id: Identifier
    trigger: Literal["participant_formal_task", "condition_presented", "formal_data_written", "prototype_formal_test"]
    occurred_at: datetime = Field(default_factory=utc_now)
    irreversible: bool = True

    @model_validator(mode="after")
    def irreversible_trigger(self) -> "ExperimentStartEvent":
        if not self.irreversible:
            raise ValueError("experiment start event must be irreversible")
        return self


class ParticipantRecord(FrozenModel):
    participant_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    experiment_revision_id: Identifier
    status: Literal["candidate", "screened", "enrolled", "formal_sample_member", "completed", "withdrawn", "excluded"] = "candidate"
    exclusion_reason: str | None = None
    exposure_history: tuple[str, ...] = ()
    consent_scope_revision_id: Identifier | None = None

    @model_validator(mode="after")
    def exclusion_requires_reason(self) -> "ParticipantRecord":
        if self.status == "excluded" and not self.exclusion_reason:
            raise ValueError("excluded participant requires a reason")
        return self


class ConditionSnapshot(FrozenModel):
    condition_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    candidate_revision_id: Identifier
    variable_values: tuple[DesignVariableValue, ...] = ()
    event_sequence_ids: tuple[str, ...] = ()
    scenario_revision_id: Identifier | None = None
    asset_hashes: tuple[tuple[str, str], ...] = ()
    environment: Identifier = "unspecified"
    consent_scope_revision_id: Identifier | None = None
    content_hash_value: str | None = None

    @model_validator(mode="after")
    def content_hash_matches_snapshot(self) -> "ConditionSnapshot":
        if self.content_hash_value is not None:
            expected = self.model_copy(update={"content_hash_value": None}).content_hash
            if self.content_hash_value != expected:
                raise ValueError("condition snapshot content hash does not match immutable payload")
        return self


class ConditionPresentationRecord(FrozenModel):
    presentation_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    condition_revision_id: Identifier
    participant_id: Identifier
    presented_asset_hashes: tuple[tuple[str, str], ...] = ()
    device_revision_id: Identifier | None = None
    software_revision_id: Identifier | None = None
    calibration_status: Literal["verified", "unverified", "not_applicable"] = "unverified"
    started_at: datetime = Field(default_factory=utc_now)
    duration_ms: int = Field(default=0, ge=0)
    event_log_ids: tuple[str, ...] = ()
    deviation_ids: tuple[str, ...] = ()
    status: Literal["verified", "presentation_unverified"] = "presentation_unverified"

    @model_validator(mode="after")
    def verified_shape(self) -> "ConditionPresentationRecord":
        if self.status == "verified" and self.calibration_status == "unverified":
            raise ValueError("verified presentation requires verified calibration or explicit N/A")
        return self


class EventLogRecord(FrozenModel):
    log_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    participant_id: Identifier
    condition_revision_id: Identifier
    sequence: int = Field(ge=1)
    event_type: Identifier
    monotonic_time_ms: int = Field(ge=0)
    payload_hash: Identifier
    previous_hash: str | None = None
    encrypted: bool = True
    status: Literal["captured", "uploaded", "integrity_uncertain", "overflow"] = "captured"


class OutcomeObservation(FrozenModel):
    observation_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    participant_id: Identifier
    condition_presentation_id: Identifier
    measure_id: Identifier
    value: ScalarValue | None = None
    status: Literal["observed", "participant_withdrawal", "task_abandonment", "technical_failure", "skipped_by_protocol", "no_response", "not_applicable", "unknown"] = "observed"
    completion_cause: str | None = None
    blinded_roles: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def presentation_boundary(self) -> "OutcomeObservation":
        # A caller can still store an observation when presentation is
        # unverified, but it must remain explicitly non-primary evidence.
        if self.status == "observed" and "presentation_unverified" in self.evidence_refs:
            raise ValueError("unverified presentation cannot be marked as observed primary evidence")
        return self


class ResearcherIntervention(FrozenModel):
    intervention_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    experiment_revision_id: Identifier
    participant_id: Identifier
    trigger: Identifier
    content: Identifier
    affected_condition_id: Identifier | None = None
    duration_ms: int = Field(default=0, ge=0)
    response: str | None = None
    analysis_treatment: Literal["separate", "pre_registered", "unknown"] = "separate"


class DependencyGraphRevision(FrozenModel):
    graph_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    nodes: tuple[DependencyRef, ...]
    edges: tuple[tuple[str, str], ...] = ()
    status: Literal["closed", "incomplete", "dependency_cycle", "dependency_revision_unknown"] = "incomplete"
    field_coverage: tuple[str, ...] = ()

    @model_validator(mode="after")
    def acyclic_and_closed(self) -> "DependencyGraphRevision":
        node_ids = {f"{n.object_type}:{n.object_id}:{n.revision}" for n in self.nodes}
        if any(left not in node_ids or right not in node_ids for left, right in self.edges):
            raise ValueError("dependency edge references an unknown node")
        graph = {node: [] for node in node_ids}
        for left, right in self.edges:
            graph[left].append(right)
        visiting: set[str] = set(); visited: set[str] = set()
        def visit(node: str) -> bool:
            if node in visiting: return True
            if node in visited: return False
            visiting.add(node)
            if any(visit(child) for child in graph[node]): return True
            visiting.remove(node); visited.add(node); return False
        if any(visit(node) for node in node_ids):
            raise ValueError("dependency graph contains a cycle")
        if self.status == "closed" and not self.field_coverage:
            raise ValueError("closed dependency graph requires field coverage")
        return self


class IndependenceAssessment(FrozenModel):
    assessment_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    subject_id: Identifier
    source_ids: tuple[str, ...]
    critical_fields: tuple[str, ...]
    covered_fields: tuple[str, ...] = ()
    shared_dependencies: tuple[str, ...] = ()
    common_failure_modes: tuple[str, ...] = ()
    status: Literal["independent", "limited_independence", "independence_coverage_gap", "independence_dependency_unknown", "correlated_evidence_dependency"] = "independence_dependency_unknown"
    reviewer_id: Identifier | None = None

    @model_validator(mode="after")
    def coverage_gate(self) -> "IndependenceAssessment":
        if self.status == "independent" and not set(self.critical_fields).issubset(self.covered_fields):
            raise ValueError("independent assessment requires critical field coverage")
        return self


class ArbitrationRevision(FrozenModel):
    arbitration_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    provider: Identifier
    model_revision: Identifier | None = None
    data_lineage: tuple[str, ...] = ()
    infrastructure_lineage: tuple[str, ...] = ()
    prompt_revision: Identifier | None = None
    trust_chain_revision: Identifier | None = None
    status: Literal["declared", "independent", "arbitration_lineage_unknown", "correlated_arbitration_lineage", "arbitration_lineage_change"] = "declared"
    parent_arbitration_revision_id: str | None = None

    @model_validator(mode="after")
    def independence_fields(self) -> "ArbitrationRevision":
        if self.status == "independent" and not all((self.model_revision, self.data_lineage, self.infrastructure_lineage, self.trust_chain_revision)):
            raise ValueError("independent arbitration requires model, data, infrastructure and trust lineage")
        return self


class CanaryRevision(FrozenModel):
    canary_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    compatibility_revision_id: Identifier
    path_id: Identifier
    criticality: Literal["critical", "ordinary"]
    source: Literal["independent_steward", "provider_generated", "public_example"] = "independent_steward"
    steward_id: Identifier | None = None
    blinded: bool = True
    status: Literal["registered", "executed", "passed", "failed", "canary_exposed", "canary_generation_contamination", "canary_steward_outcome_contamination", "canary_failure_classification_uncertain", "failure_classification_disputed", "reinstated"] = "registered"
    failure_classification: str | None = None
    replacement_allowed: bool = False
    parent_canary_revision_id: str | None = None
    adjudication_revision_id: str | None = None

    @model_validator(mode="after")
    def canary_safety(self) -> "CanaryRevision":
        if self.source != "independent_steward":
            raise ValueError("confirmation canaries require independent stewardship")
        if self.status in {"passed", "failed", "executed", "reinstated"} and not self.blinded:
            raise ValueError("canary outcome requires blinded stewardship or independent replacement review")
        if self.status == "reinstated" and not self.adjudication_revision_id:
            raise ValueError("reinstatement requires an adjudication revision")
        return self


class SuspensionRevision(FrozenModel):
    suspension_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    trigger_code: Identifier
    scope: tuple[str, ...]
    status: Literal["suspended", "validation_only", "revalidation_ready", "released"] = "suspended"
    isolation_proof_refs: tuple[str, ...] = ()
    recovery_conditions: tuple[str, ...] = ()
    release_revision_id: str | None = None

    @model_validator(mode="after")
    def release_shape(self) -> "SuspensionRevision":
        if self.status == "released" and not self.release_revision_id:
            raise ValueError("released suspension requires a new release revision")
        return self


class ReleaseScopeGrant(FrozenModel):
    grant_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    allowed_interactions: tuple[str, ...] = ()
    allowed_paths: tuple[str, ...] = ()
    brief_revision_ids: tuple[str, ...] = ()
    executor_revision_ids: tuple[str, ...] = ()
    model_rule_revision_ids: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    monitoring_obligations: tuple[str, ...] = ()
    expires_at: datetime | None = None
    status: Literal["active", "superseded", "revoked", "grant_conflict", "grant_revocation_pending"] = "active"
    precedence: Literal["normal", "supersede"] = "normal"

    @model_validator(mode="after")
    def grant_scope(self) -> "ReleaseScopeGrant":
        if not (self.allowed_interactions or self.allowed_paths):
            raise ValueError("release grant must name an explicit interaction or path")
        return self


class ExecutionSurfaceReceipt(FrozenModel):
    node_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    revoke_revision_id: Identifier
    surface_type: Literal["execution_node", "cache", "offline_agent"]
    receipt_version: Identifier
    received_at: datetime = Field(default_factory=utc_now)
    signature: Identifier
    status: Literal["received", "missing", "stale", "unregistered_execution_surface", "post_snapshot_execution_surface"] = "received"


class GrantRevocationRevision(FrozenModel):
    revocation_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    grant_id: Identifier
    reason: Identifier
    receipt_node_ids: tuple[str, ...] = ()
    inventory_node_ids: tuple[str, ...] = ()
    status: Literal["revoke", "grant_revocation_pending", "converged", "execution_inventory_gap", "execution_inventory_watch_gap", "authorization_usage_unknown", "authorization_execution_uncertain"] = "revoke"
    usage_log_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def convergence_gate(self) -> "GrantRevocationRevision":
        if self.status == "converged" and len(set(self.receipt_node_ids)) != len(self.receipt_node_ids):
            raise ValueError("revocation receipts must be unique")
        if self.status == "converged" and set(self.receipt_node_ids) != set(self.inventory_node_ids):
            raise ValueError("revocation convergence requires receipt closure over inventory")
        if self.status == "converged" and not self.usage_log_refs:
            raise ValueError("revocation convergence requires authorization usage history")
        return self


class ExternalCallSnapshot(FrozenModel):
    """Pinned inputs for provider/LLM work executed outside a DB transaction."""

    call_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    provider: Identifier
    model: Identifier
    input_hashes: tuple[tuple[str, str], ...] = ()
    policy_revision_id: Identifier | None = None
    consent_scope_revision_id: Identifier | None = None
    target_object_type: Identifier
    target_object_id: Identifier
    target_revision_id: Identifier
    fingerprint: Identifier


class JobRecord(FrozenModel):
    """Lifecycle envelope for asynchronous work and optimistic result commit."""

    job_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    kind: Identifier
    external_call_snapshot_id: Identifier
    target_object_type: Identifier
    target_object_id: Identifier
    expected_revision: int = Field(ge=1)
    status: Literal[
        "queued", "processing", "succeeded", "failed", "stale_result",
        "orphaned", "cancelled", "awaiting_consent", "expired", "dead_letter",
    ] = "queued"
    attempt: int = Field(default=1, ge=1)
    result_revision_id: str | None = None
    error: str | None = None
    fingerprint: Identifier


class StaleJobResult(FrozenModel):
    """A completed result whose pinned target revision is no longer current."""

    result_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    job_id: Identifier
    target_object_type: Identifier
    target_object_id: Identifier
    expected_revision: int = Field(ge=1)
    actual_revision: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    stale_reasons: tuple[str, ...]
    status: Literal["stale_result"] = "stale_result"


class OutboxEvent(FrozenModel):
    """Transactional side-effect envelope; delivery is idempotent by event_id."""

    outbox_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    event_id: Identifier
    event_type: Identifier
    payload: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "processing", "delivered", "failed", "dead_letter"] = "pending"
    attempts: int = Field(default=0, ge=0)
    available_at: datetime = Field(default_factory=utc_now)
    locked_at: datetime | None = None
    last_error: str | None = None


# Domain terminology aliases.  Keeping these names available makes the stage
# gate explicit at call sites while the persisted object remains the generic
# immutable snapshot type.
DesignBriefSnapshot = DesignBrief
CandidateFactsFreeze = CandidateFactsSnapshot

# ``CandidateDraft`` is declared before ``DesignShape`` to keep the input DTO
# section together; resolve its forward reference once all models exist.
CandidateDraft.model_rebuild()
FutureMovementScenario.model_rebuild()
DesignRuleSet.model_rebuild()
ProgressiveDesignModel.model_rebuild()
ConfirmedObservation.model_rebuild()


# P0 engineering types live in a separate module to keep the historical
# experience model file manageable.  A lazy bridge preserves the established
# ``psyteardown.experience.models`` import surface without introducing a
# module-import cycle while models are being defined.
_ENGINEERING_EXPORTS = {
    "EngineeringRecord", "RequirementDeclaration", "EngineeringIntake", "EngineeringProjectRevision",
    "EngineeringRequirement", "EngineeringConflict", "MechanicalArchitecture",
    "MaterialProcessChoice", "CADArtifact", "BOMRevision", "ToleranceStack",
    "CAEAnalysisRun", "DFMReview", "FMEARevision", "DVPRevision", "VerificationTestRun",
    "PilotBuildRun", "ReliabilityCertificationReview", "ManufacturingReadinessReview",
    "ReleaseDecision", "EngineeringChangeOrder", "SupplierChangeRecord", "FieldIssue",
    "CrossCaseEvidenceRef", "CrossCaseKnowledgeCandidate", "ApprovedKnowledgeRule", "EngineeringTask",
    "EngineeringGateDecision", "EngineeringOrchestrator", "EngineeringRegistry",
    "EngineeringObjectRegistry",
    "EngineeringArtifactRef", "EngineeringToolRequest", "RawEngineeringToolResult",
    "EngineeringInterpretation",
}


def __getattr__(name: str) -> Any:
    if name in _ENGINEERING_EXPORTS:
        from psyteardown.experience import engineering
        return getattr(engineering, name)
    raise AttributeError(name)
