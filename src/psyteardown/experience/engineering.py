"""P0 engineering objects and orchestration primitives.

The experience slice predates the engineering workflow, so this module keeps
the engineering registry deliberately small and composable.  Engineering
objects are immutable revisions; dependencies are explicit ``DependencyRef``
values and an upstream revision change creates a new stale revision for every
affected downstream object.  No method in this module treats an AI result as
an approval or as physical evidence.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Iterable, Literal, TypeAlias
from uuid import uuid4

from pydantic import ConfigDict, Field, AliasChoices, model_validator

from psyteardown.experience.models import (
    AuditEvent,
    CandidateEvaluationRecord,
    CandidateFactsSnapshot,
    CandidatePartialOrder,
    Critique,
    DesignBrief,
    DesignCandidate,
    DesignFeedbackSelection,
    DesignIteration,
    DomainEvent,
    Evidence,
    ExperienceHypothesis,
    HypothesisBinding,
    Observation,
    ReviewItem,
    VariablePatch,
    AnalysisFamily,
    DependencyGraphRevision,
    DependencyRef,
    DomainStateError,
    FrozenModel,
    RevisionMeta,
    utc_now,
)


EngineeringStatus: TypeAlias = Literal[
    "draft", "current", "approved", "pending", "blocked", "completed",
    "stale", "invalidated", "rejected", "conditional", "unverified", "not_started",
]


class EngineeringRecord(FrozenModel):
    """Common provenance envelope for all P0 engineering objects."""

    # Engineering adapters evolve independently from the initial experience
    # schemas.  Allowing adapter-specific fields preserves their provenance
    # while the named fields below remain the stable shared interface.
    model_config = ConfigDict(frozen=True, extra="allow")
    revision_id: str
    meta: RevisionMeta = Field(
        default_factory=lambda: RevisionMeta(
            revision=1, created_by="system", reason="engineering object created"
        )
    )
    dependencies: tuple[DependencyRef, ...] = ()
    status: EngineeringStatus = "current"
    assumptions: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    stale_reasons: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def normalize_revision_meta(cls, data: Any) -> Any:
        """Accept both the platform's nested meta and adapter flat fields."""
        if not isinstance(data, dict) or data.get("meta") is not None:
            return data
        revision_id = str(data.get("revision_id", ""))
        try:
            revision = int(revision_id.rsplit(".r", 1)[1])
        except (IndexError, ValueError):
            revision = int(data.get("revision", 1))
        data = dict(data)
        data["meta"] = {
            "revision": revision,
            "parent_revision_id": data.get("parent_revision_id"),
            "created_by": data.get("created_by", "system"),
            "reason": data.get("reason", "engineering object created"),
        }
        return data

    @property
    def parent_revision_id(self) -> str | None:
        return self.meta.parent_revision_id or (getattr(self, "model_extra", None) or {}).get("parent_revision_id")

    @property
    def created_by(self) -> str:
        return self.meta.created_by or (getattr(self, "model_extra", None) or {}).get("created_by", "")

    @property
    def created_at(self) -> datetime:
        return self.meta.created_at

    @property
    def id(self) -> str:
        """Aggregate identifier compatibility shorthand."""
        for name, value in self.__dict__.items():
            if name.endswith("_id") and name not in {"revision_id", "parent_revision_id"} and isinstance(value, str):
                return value
        raise AttributeError("engineering record has no aggregate identifier")


class EngineeringRequirement(EngineeringRecord):
    requirement_id: str = Field(validation_alias=AliasChoices("requirement_id", "engineering_requirement_id"))
    title: str
    description: str = ""
    requirement_type: Literal["must", "should", "explore"] = "should"
    acceptance_criteria: tuple[str, ...] = ()
    priority: int = Field(default=1, ge=1)
    applicable_scope: tuple[str, ...] = ()
    verification_methods: tuple[str, ...] = ()
    source_type: Literal["user_declared", "business_declared", "regulatory", "evidence_derived", "ai_default"] = "ai_default"
    verification_owner: str | None = None
    hard_constraint: bool = False
    risk_ids: tuple[str, ...] = ()


class RequirementDeclaration(FrozenModel):
    requirement_id: str
    title: str
    description: str
    requirement_type: Literal["must", "should", "explore"]
    acceptance_criteria: tuple[str, ...] = Field(min_length=1)
    source: str
    source_type: Literal["user_declared", "business_declared", "regulatory"] = "user_declared"
    priority: int = Field(default=1, ge=1)
    applicable_scope: tuple[str, ...] = ()
    verification_methods: tuple[str, ...] = ()
    verification_owner: str | None = None
    hard_constraint: bool = False


class DigitalExperienceSignal(FrozenModel):
    """One App/service finding awaiting cross-domain human triage."""

    signal_id: str
    signal_type: Literal["friction", "ethics", "opportunity"]
    statement: str
    source_refs: tuple[str, ...] = ()


class DiscoveryTriageDecision(FrozenModel):
    """Human routing decision for one digital-experience signal."""

    signal_id: str
    disposition: Literal[
        "app_experience",
        "cross_channel_validation",
        "device_interaction_candidate",
        "rejected",
        "deferred",
    ]
    rationale: str
    candidate_statement: str | None = None
    validation_question: str | None = None

    @model_validator(mode="after")
    def routed_signal_has_required_detail(self) -> "DiscoveryTriageDecision":
        if self.disposition == "device_interaction_candidate" and (
            not self.candidate_statement or not self.validation_question
        ):
            raise ValueError(
                "device interaction candidates require a candidate statement and validation question"
            )
        if self.disposition == "cross_channel_validation" and not self.validation_question:
            raise ValueError("cross-channel validation requires a validation question")
        return self


class DigitalExperienceDiscovery(EngineeringRecord):
    """Immutable discovery snapshot produced from the App teardown pipeline.

    It is not an engineering requirement and contains no physical evidence.
    Only a named human triage can route an individual signal onward.
    """

    discovery_id: str
    product_name: str
    product_type: str
    product_summary: str
    app_features: tuple[str, ...] = ()
    user_goals: tuple[str, ...] = ()
    digital_touchpoints: tuple[str, ...] = ()
    signals: tuple[DigitalExperienceSignal, ...] = ()
    mechanism_hypotheses: tuple[str, ...] = ()
    grounding_quality: Literal["grounded", "partial", "unreliable"] = "unreliable"
    triage_status: Literal["pending", "complete"] = "pending"
    triage_decisions: tuple[DiscoveryTriageDecision, ...] = ()

    @model_validator(mode="after")
    def triage_is_complete_and_human_owned(self) -> "DigitalExperienceDiscovery":
        signal_ids = {item.signal_id for item in self.signals}
        decision_ids = [item.signal_id for item in self.triage_decisions]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("a discovery signal can have only one current triage decision")
        if not set(decision_ids).issubset(signal_ids):
            raise ValueError("triage decision references an unknown discovery signal")
        if self.triage_status == "complete":
            if set(decision_ids) != signal_ids:
                raise ValueError("complete discovery triage must route every signal")
            if not self.reviewer or self.reviewed_at is None:
                raise ValueError("complete discovery triage requires a named review record")
        return self


class EngineeringIntake(EngineeringRecord):
    intake_id: str
    project_id: str
    scenario: str
    product_purpose: str
    target_segment: str
    target_markets: tuple[str, ...] = ()
    business_goals: tuple[str, ...] = ()
    maintenance_assumptions: tuple[str, ...] = ()
    cost_assumptions: tuple[str, ...] = ()
    declared_requirements: tuple[RequirementDeclaration, ...] = ()
    # Optional upstream discovery signals.  These are deliberately separate
    # from declared requirements: a teardown/LLM result is a hypothesis source
    # until a named system engineer reviews it.
    discovery_revision_id: str | None = None
    discovery_source_refs: tuple[str, ...] = ()
    discovery_quality: Literal["grounded", "partial", "unreliable", "not_provided"] = "not_provided"
    experience_risks: tuple[str, ...] = ()
    ethics_risks: tuple[str, ...] = ()
    experience_opportunities: tuple[str, ...] = ()
    behavioral_mechanisms: tuple[str, ...] = ()
    discovery_assumptions: tuple[str, ...] = ()
    discovery_unknowns: tuple[str, ...] = ()
    device_interaction_candidates: tuple[str, ...] = ()
    # Backward-compatible marker for callers of the pre-triage bridge. New
    # discovery CLI paths never set this; it exists only during migration.
    legacy_direct_discovery: bool = False


class EngineeringProjectRevision(EngineeringRecord):
    project_id: str
    intake_revision_id: str
    scenario: str
    product_purpose: str
    stage: Literal[
        "concept_declared", "experience_reviewed", "engineering_ready", "prototype_ready",
        "physical_validation", "compliance_reviewed", "manufacturing_ready", "released",
    ] = "concept_declared"
    requirement_revision_ids: tuple[str, ...] = ()
    role_task_ids: tuple[str, ...] = ()
    gate_decision_revision_ids: tuple[str, ...] = ()
    open_conflict_ids: tuple[str, ...] = ()


class EngineeringConflict(EngineeringRecord):
    conflict_id: str
    title: str
    description: str
    domains: tuple[str, ...]
    affected_objects: tuple[DependencyRef, ...]
    priority_class: Literal[
        "safety", "regulatory", "core_function", "ergonomics", "reliability",
        "manufacturing", "cost", "appearance", "unknown",
    ]
    classification: Literal["hard_block", "pareto_tradeoff", "human_decision_required"]
    alternatives: tuple[str, ...] = ()
    conflict_status: Literal["open", "resolved", "accepted_risk", "rejected"] = "open"
    resolution: str | None = None

    @model_validator(mode="after")
    def resolved_conflict_has_human_decision(self) -> "EngineeringConflict":
        if self.conflict_status != "open" and (
            not self.resolution or not self.reviewer or self.reviewed_at is None
        ):
            raise ValueError("resolved engineering conflict requires a named review record")
        return self


class MechanicalArchitecture(EngineeringRecord):
    architecture_id: str = Field(validation_alias=AliasChoices("architecture_id", "mechanical_architecture_id"))
    requirement_ids: tuple[str, ...] = ()
    components: tuple[str, ...] = ()
    interfaces: tuple[str, ...] = ()
    assembly_strategy: str = ""
    fastening_strategy: str = ""
    sealing_strategy: str = ""
    maintenance_strategy: str = ""
    risk_ids: tuple[str, ...] = ()


class MaterialProcessChoice(EngineeringRecord):
    choice_id: str = Field(validation_alias=AliasChoices("choice_id", "material_process_choice_id"))
    requirement_ids: tuple[str, ...] = ()
    materials: tuple[str, ...] = ()
    process: str = ""
    surface_treatment: str = ""
    supplier_assumptions: tuple[str, ...] = ()
    validation_requirements: tuple[str, ...] = ()
    risk_ids: tuple[str, ...] = ()


class CADArtifact(EngineeringRecord):
    artifact_id: str = Field(validation_alias=AliasChoices("artifact_id", "cad_artifact_id", "cad_id"))
    artifact_type: Literal["cad", "drawing", "mesh", "other"] = "cad"
    uri: str | None = None
    sha256: str | None = None
    format: str = ""
    tool: str = ""
    tool_version: str = ""
    input_revision_ids: tuple[str, ...] = ()

    @property
    def cad_artifact_id(self) -> str:
        return self.artifact_id


class BOMRevision(EngineeringRecord):
    bom_id: str = Field(validation_alias=AliasChoices("bom_id", "bom_revision_id"))
    part_ids: tuple[str, ...] = ()
    parts: tuple[dict[str, Any], ...] = ()
    supplier_assumptions: tuple[str, ...] = ()
    cost_assumptions: tuple[str, ...] = ()
    target_cost: float | None = None
    currency: str | None = None


class ToleranceStack(EngineeringRecord):
    tolerance_stack_id: str = Field(validation_alias=AliasChoices("tolerance_stack_id", "stack_id"))
    dimensions: tuple[dict[str, Any], ...] = ()
    datum_refs: tuple[str, ...] = ()
    worst_case: str | None = None
    statistical_assumptions: tuple[str, ...] = ()
    result: str | None = None


class CAEAnalysisRun(EngineeringRecord):
    analysis_run_id: str = Field(validation_alias=AliasChoices("analysis_run_id", "cae_analysis_run_id", "cae_run_id"))
    analysis_type: str
    solver: str = ""
    solver_version: str = ""
    boundary_conditions: dict[str, Any] = Field(default_factory=dict)
    material_model_refs: tuple[str, ...] = ()
    raw_result_uri: str | None = None
    convergence_status: Literal["not_run", "converged", "not_converged", "failed"] = "not_run"
    uncertainty: tuple[str, ...] = ()
    interpretation: str | None = None

    @property
    def cae_run_id(self) -> str:
        return self.analysis_run_id


class DFMReview(EngineeringRecord):
    review_id: str = Field(validation_alias=AliasChoices("review_id", "dfm_review_id"))
    cad_artifact_revision_id: str | None = None
    manufacturability_risks: tuple[str, ...] = ()
    assembly_steps: tuple[str, ...] = ()
    mold_assumptions: tuple[str, ...] = ()
    cost_assumptions: tuple[str, ...] = ()
    yield_risks: tuple[str, ...] = ()
    recommendation: str = "pending"

    @property
    def dfm_review_id(self) -> str:
        return self.review_id


class FMEARevision(EngineeringRecord):
    fmea_id: str = Field(validation_alias=AliasChoices("fmea_id", "fmea_revision_id"))
    failure_modes: tuple[dict[str, Any], ...] = ()
    severity_scale: str = ""
    occurrence_scale: str = ""
    detection_scale: str = ""
    mitigation_actions: tuple[str, ...] = ()


class DVPRevision(EngineeringRecord):
    """Design verification plan and report revision (DVP&R)."""

    dvp_id: str = Field(validation_alias=AliasChoices("dvp_id", "dvpr_id"))
    requirement_ids: tuple[str, ...] = ()
    critical_requirement_ids: tuple[str, ...] = ()
    test_matrix: tuple[dict[str, Any], ...] = ()
    verification_test_run_ids: tuple[str, ...] = ()
    covered_requirement_ids: tuple[str, ...] = ()
    passed_requirement_ids: tuple[str, ...] = ()
    failed_requirement_ids: tuple[str, ...] = ()
    coverage: Literal["incomplete", "complete", "invalidated"] = "incomplete"

    @model_validator(mode="after")
    def approved_dvp_is_complete(self) -> "DVPRevision":
        if self.status == "approved":
            if self.coverage != "complete" or self.failed_requirement_ids:
                raise ValueError("approved DVP&R requires complete coverage without failed requirements")
            if not set(self.critical_requirement_ids).issubset(self.passed_requirement_ids):
                raise ValueError("approved DVP&R requires every critical requirement to pass")
            if not self.reviewer or self.reviewed_at is None:
                raise ValueError("approved DVP&R requires a human review record")
        return self


class VerificationTestRun(EngineeringRecord):
    test_run_id: str = Field(validation_alias=AliasChoices("test_run_id", "verification_test_run_id"))
    protocol_id: str = ""
    test_type: str = ""
    fixture: str = ""
    sample_ids: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    raw_measurement_refs: tuple[str, ...] = ()
    result: Literal["not_run", "pass", "fail", "inconclusive", "invalidated"] = "not_run"
    evidence_review_id: str | None = None

    @property
    def verification_test_run_id(self) -> str:
        return self.test_run_id


class PilotBuildRun(EngineeringRecord):
    pilot_build_id: str
    bom_revision_id: str
    build_lot: str
    supplier_ids: tuple[str, ...] = ()
    units_started: int = Field(default=0, ge=0)
    units_completed: int = Field(default=0, ge=0)
    units_accepted: int = Field(default=0, ge=0)
    first_pass_yield: float | None = Field(default=None, ge=0, le=1)
    target_yield: float | None = Field(default=None, ge=0, le=1)
    raw_yield_refs: tuple[str, ...] = ()
    quality_issues: tuple[str, ...] = ()
    capacity_observations: tuple[str, ...] = ()
    result: Literal["not_started", "completed", "failed", "invalidated"] = "not_started"

    @model_validator(mode="after")
    def build_counts_and_yield(self) -> "PilotBuildRun":
        if self.units_completed > self.units_started or self.units_accepted > self.units_completed:
            raise ValueError("pilot build unit counts must be monotonically decreasing")
        if self.result == "completed":
            if self.units_started == 0 or not self.raw_yield_refs or self.first_pass_yield is None:
                raise ValueError("completed pilot build requires units, raw yield data and first-pass yield")
        return self


class ReliabilityCertificationReview(EngineeringRecord):
    review_id: str
    target_markets: tuple[str, ...] = ()
    applicable_standards: tuple[str, ...] = ()
    reliability_test_revision_ids: tuple[str, ...] = ()
    certification_evidence_refs: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    decision: Literal["pending", "blocked", "conditional", "approved", "rejected"] = "pending"

    @model_validator(mode="after")
    def approval_has_evidence(self) -> "ReliabilityCertificationReview":
        if self.decision == "approved":
            if self.gaps or not self.applicable_standards or not self.certification_evidence_refs:
                raise ValueError("approved compliance review requires standards, evidence and no gaps")
            if not self.reviewer or self.reviewed_at is None:
                raise ValueError("approved compliance review requires a human reviewer")
        return self


class ManufacturingReadinessReview(EngineeringRecord):
    review_id: str = Field(validation_alias=AliasChoices("review_id", "mrr_id"))
    pilot_build: str = ""
    supplier_ids: tuple[str, ...] = ()
    yield_data_refs: tuple[str, ...] = ()
    quality_plan_refs: tuple[str, ...] = ()
    capacity_assumptions: tuple[str, ...] = ()
    cost_reviewed: bool = False
    readiness: Literal["pending", "blocked", "conditional", "ready"] = "pending"
    blocking_items: tuple[str, ...] = ()
    conditional_items: tuple[str, ...] = ()
    gate_revision_ids: tuple[str, ...] = ()

    @property
    def mrr_id(self) -> str:
        return self.review_id


class ReleaseDecision(EngineeringRecord):
    decision_id: str = Field(validation_alias=AliasChoices("decision_id", "release_decision_id"))
    release_scope: tuple[str, ...] = ()
    blocking_items: tuple[str, ...] = ()
    effective_revision_ids: tuple[str, ...] = ()
    approver: str | None = None
    decision: Literal["pending", "blocked", "conditional", "approved", "rejected"] = "pending"
    rationale: str = ""
    valid_until: datetime | None = None
    remaining_risks: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    gate_revision_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def approved_release_shape(self) -> "ReleaseDecision":
        if self.decision == "approved":
            if self.blocking_items or not self.release_scope or not self.effective_revision_ids:
                raise ValueError("approved release requires scope, effective revisions and no blockers")
            if not self.approver or not self.reviewer or self.reviewed_at is None:
                raise ValueError("approved release requires a named human approval record")
        return self

    @property
    def release_decision_id(self) -> str:
        return self.decision_id


class EngineeringChangeOrder(EngineeringRecord):
    change_order_id: str = Field(validation_alias=AliasChoices("change_order_id", "eco_id"))
    title: str
    reason: str
    affected_objects: tuple[DependencyRef, ...]
    variable_patch_revision_ids: tuple[str, ...] = ()
    impact_areas: tuple[Literal["safety", "regulatory", "function", "ergonomics", "reliability", "manufacturing", "cost", "appearance"], ...] = ()
    verification_required: tuple[str, ...] = ()
    approval: Literal["pending", "approved", "rejected"] = "pending"
    implementation_status: Literal["not_started", "in_progress", "implemented", "verified", "cancelled"] = "not_started"

    @model_validator(mode="after")
    def approved_change_has_human(self) -> "EngineeringChangeOrder":
        if self.approval == "approved" and (not self.reviewer or self.reviewed_at is None):
            raise ValueError("approved engineering change requires a human reviewer")
        return self


class SupplierChangeRecord(EngineeringRecord):
    change_id: str
    supplier_id: str
    part_id: str
    previous_spec: str
    proposed_spec: str
    affected_objects: tuple[DependencyRef, ...]
    qualification_test_revision_ids: tuple[str, ...] = ()
    decision: Literal["pending", "approved", "rejected"] = "pending"

    @model_validator(mode="after")
    def supplier_approval_gate(self) -> "SupplierChangeRecord":
        if self.decision == "approved":
            if not self.qualification_test_revision_ids:
                raise ValueError("approved supplier change requires qualification tests")
            if not self.reviewer or self.reviewed_at is None:
                raise ValueError("approved supplier change requires a human reviewer")
        return self


class FieldIssue(EngineeringRecord):
    issue_id: str
    release_decision_revision_id: str | None = None
    severity: Literal["critical", "major", "minor", "observation"]
    description: str
    evidence_refs: tuple[str, ...] = ()
    affected_objects: tuple[DependencyRef, ...] = ()
    corrective_action_ids: tuple[str, ...] = ()
    disposition: Literal["open", "contained", "corrective_action", "verified", "closed"] = "open"


class CrossCaseEvidenceRef(FrozenModel):
    case_id: str
    hypothesis_id: str
    hypothesis_revision_id: str
    evidence_review_revision_ids: tuple[str, ...]
    condition_snapshot_revision_ids: tuple[str, ...]
    outcome: Literal["supported", "rejected"]
    applicability_notes: tuple[str, ...] = ()


class CrossCaseKnowledgeCandidate(EngineeringRecord):
    rule_id: str
    statement: str
    applicability: tuple[str, ...]
    counter_conditions: tuple[str, ...]
    source_cases: tuple[CrossCaseEvidenceRef, ...]
    supporting_case_ids: tuple[str, ...] = ()
    counterexample_case_ids: tuple[str, ...] = ()
    duplicate_rule_ids: tuple[str, ...] = ()
    resolved_duplicate_rule_ids: tuple[str, ...] = ()
    conflicting_rule_ids: tuple[str, ...] = ()
    resolved_conflict_ids: tuple[str, ...] = ()
    replication_count: int = Field(default=0, ge=0)
    replication_status: Literal["insufficient", "replicated", "conflicted"] = "insufficient"
    counterexamples_reviewed: bool = False
    knowledge_status: Literal["candidate", "approved", "rejected"] = "candidate"
    decision_rationale: str | None = None

    @model_validator(mode="after")
    def approved_knowledge_candidate_gate(self) -> "CrossCaseKnowledgeCandidate":
        if self.knowledge_status == "approved":
            unresolved = set(self.conflicting_rule_ids) - set(self.resolved_conflict_ids)
            unresolved_duplicates = set(self.duplicate_rule_ids) - set(self.resolved_duplicate_rule_ids)
            if self.replication_status != "replicated" or self.replication_count < 2:
                raise ValueError("approved cross-case knowledge requires replication")
            if unresolved or unresolved_duplicates or not self.counterexamples_reviewed:
                raise ValueError("approved cross-case knowledge requires conflict and counterexample review")
            if not self.reviewer or self.reviewed_at is None:
                raise ValueError("approved cross-case knowledge requires a human reviewer")
        return self


class ApprovedKnowledgeRule(EngineeringRecord):
    rule_id: str
    candidate_revision_id: str
    statement: str
    applicability: tuple[str, ...]
    counter_conditions: tuple[str, ...]
    source_case_ids: tuple[str, ...]
    evidence_review_revision_ids: tuple[str, ...]
    replication_count: int = Field(ge=2)
    decision_rationale: str

    @model_validator(mode="after")
    def approved_rule_is_human_owned(self) -> "ApprovedKnowledgeRule":
        if self.status != "approved" or not self.reviewer or self.reviewed_at is None:
            raise ValueError("default knowledge rules require named human approval")
        return self


class EngineeringTask(EngineeringRecord):
    task_id: str
    role: str
    action: str
    depends_on_task_ids: tuple[str, ...] = ()
    human_gate_required: bool = False
    assigned_to: str | None = None
    task_status: Literal["queued", "ready", "running", "blocked", "completed", "cancelled"] = "queued"
    result_revision_ids: tuple[str, ...] = ()


class EngineeringGateDecision(EngineeringRecord):
    gate_id: str
    revision_id: str
    meta: RevisionMeta
    target_object_type: str
    target_object_id: str
    target_revision_id: str
    from_stage: str
    to_stage: str
    reviewer: str
    evidence_refs: tuple[str, ...] = ()
    decision: Literal["approved", "blocked", "conditional"] = "approved"
    rationale: str
    status: Literal["approved", "blocked", "conditional"] = "approved"


class EngineeringArtifactRef(FrozenModel):
    """Hash-addressed raw artifact emitted by a real engineering tool."""

    artifact_id: str
    uri: str
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    role: Literal[
        "cad", "drawing", "mesh", "solver_input", "solver_output", "report",
        "bom", "material_card", "supplier_data", "cost_data", "log", "other",
    ] = "other"
    media_type: str | None = None


class EngineeringToolRequest(EngineeringRecord):
    """Pinned request for CAD/CAE/DFM/BOM execution."""

    request_id: str
    tool_domain: Literal["cad", "cae", "dfm", "bom"]
    operation: str
    tool: str
    tool_version: str
    output_object_id: str
    input_artifact_refs: tuple[str, ...] = ()
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_outputs: tuple[str, ...] = ()
    human_review_required: bool = True


class RawEngineeringToolResult(EngineeringRecord):
    """Uninterpreted result references; never physical evidence by itself."""

    result_id: str
    request_revision_id: str
    tool_domain: Literal["cad", "cae", "dfm", "bom"]
    provider: str
    tool: str
    tool_version: str
    execution_status: Literal["succeeded", "partial", "failed"]
    artifacts: tuple[EngineeringArtifactRef, ...] = ()
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    convergence_status: Literal["not_applicable", "unknown", "converged", "not_converged", "failed"] = "unknown"
    physical_evidence: Literal[False] = False

    @model_validator(mode="after")
    def successful_result_has_artifact(self) -> "RawEngineeringToolResult":
        if self.execution_status == "succeeded" and not self.artifacts:
            raise ValueError("successful engineering tool results require raw artifacts")
        if self.execution_status == "failed" and self.convergence_status == "converged":
            raise ValueError("a failed tool result cannot be converged")
        return self


class EngineeringInterpretation(EngineeringRecord):
    """AI/human interpretation stored separately from raw tool output."""

    interpretation_id: str
    raw_result_revision_id: str
    summary: str
    findings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    structured_payload: dict[str, Any] = Field(default_factory=dict)
    review_decision: Literal["pending", "accepted", "modified", "rejected"] = "pending"

    @model_validator(mode="after")
    def reviewed_interpretation_has_human_record(self) -> "EngineeringInterpretation":
        if self.review_decision != "pending" and (not self.reviewer or self.reviewed_at is None):
            raise ValueError("reviewed engineering interpretation requires reviewer and timestamp")
        return self


ENGINEERING_MODEL_TYPES: dict[str, type[EngineeringRecord]] = {
    "digital_experience_discovery": DigitalExperienceDiscovery,
    "engineering_intake": EngineeringIntake,
    "engineering_project": EngineeringProjectRevision,
    "engineering_requirement": EngineeringRequirement,
    "engineering_conflict": EngineeringConflict,
    "mechanical_architecture": MechanicalArchitecture,
    "material_process_choice": MaterialProcessChoice,
    "cad_artifact": CADArtifact,
    "bom_revision": BOMRevision,
    "tolerance_stack": ToleranceStack,
    "cae_analysis_run": CAEAnalysisRun,
    "dfm_review": DFMReview,
    "fmea_revision": FMEARevision,
    "dvp_revision": DVPRevision,
    "verification_test_run": VerificationTestRun,
    "pilot_build_run": PilotBuildRun,
    "reliability_certification_review": ReliabilityCertificationReview,
    "manufacturing_readiness_review": ManufacturingReadinessReview,
    "release_decision": ReleaseDecision,
    "engineering_change_order": EngineeringChangeOrder,
    "supplier_change": SupplierChangeRecord,
    "field_issue": FieldIssue,
    "cross_case_knowledge_candidate": CrossCaseKnowledgeCandidate,
    "approved_knowledge_rule": ApprovedKnowledgeRule,
    "engineering_task": EngineeringTask,
    "engineering_gate": EngineeringGateDecision,
    "engineering_tool_request": EngineeringToolRequest,
    "raw_engineering_tool_result": RawEngineeringToolResult,
    "engineering_interpretation": EngineeringInterpretation,
}

# Short adapter names are normalized at the orchestration boundary.  The
# canonical names remain the persisted SQLite keys to keep migrations simple.
ENGINEERING_OBJECT_TYPE_ALIASES = {
    "digital_discovery": "digital_experience_discovery",
    "discovery": "digital_experience_discovery",
    "intake": "engineering_intake",
    "project": "engineering_project",
    "requirement": "engineering_requirement",
    "conflict": "engineering_conflict",
    "mechanical": "mechanical_architecture",
    "material": "material_process_choice",
    "cad": "cad_artifact",
    "bom": "bom_revision",
    "tolerance": "tolerance_stack",
    "cae": "cae_analysis_run",
    "dfm": "dfm_review",
    "fmea": "fmea_revision",
    "dvp": "dvp_revision",
    "verification_test": "verification_test_run",
    "pilot_build": "pilot_build_run",
    "compliance_review": "reliability_certification_review",
    "mrr": "manufacturing_readiness_review",
    "release": "release_decision",
    "change_order": "engineering_change_order",
    "eco": "engineering_change_order",
    "supplier_change_record": "supplier_change",
    "aftersales_issue": "field_issue",
    "knowledge_candidate": "cross_case_knowledge_candidate",
    "knowledge_rule": "approved_knowledge_rule",
    "task": "engineering_task",
    "gate": "engineering_gate",
    "tool_request": "engineering_tool_request",
    "tool_result": "raw_engineering_tool_result",
    "interpretation": "engineering_interpretation",
}

# Existing experience objects can participate in the same dependency graph;
# their schemas remain unchanged except for optional dependency fields where
# appropriate.  They are deliberately read-only to this P0 orchestrator.
LEGACY_MODEL_TYPES: dict[str, tuple[type[Any], str]] = {
    "brief": (DesignBrief, "brief_id"),
    "candidate": (DesignCandidate, "candidate_id"),
    "facts": (CandidateFactsSnapshot, "facts_snapshot_id"),
    "review": (ReviewItem, "review_item_id"),
    "iteration": (DesignIteration, "iteration_id"),
    "evaluation": (CandidateEvaluationRecord, "evaluation_id"),
    "partial_order": (CandidatePartialOrder, "partial_order_id"),
    "patch": (VariablePatch, "patch_id"),
    "evidence": (Evidence, "evidence_id"),
    "observation": (Observation, "observation_id"),
    "experience_hypothesis": (ExperienceHypothesis, "hypothesis_id"),
    "critique": (Critique, "critique_id"),
    "feedback_selection": (DesignFeedbackSelection, "selection_id"),
    "hypothesis_binding": (HypothesisBinding, "binding_id"),
    "analysis_family": (AnalysisFamily, "family_id"),
}

_ID_FIELDS = {
    "digital_experience_discovery": "discovery_id",
    "engineering_intake": "intake_id",
    "engineering_project": "project_id",
    "engineering_requirement": "requirement_id",
    "engineering_conflict": "conflict_id",
    "mechanical_architecture": "architecture_id",
    "material_process_choice": "choice_id",
    "cad_artifact": "artifact_id",
    "bom_revision": "bom_id",
    "tolerance_stack": "tolerance_stack_id",
    "cae_analysis_run": "analysis_run_id",
    "dfm_review": "review_id",
    "fmea_revision": "fmea_id",
    "dvp_revision": "dvp_id",
    "verification_test_run": "test_run_id",
    "pilot_build_run": "pilot_build_id",
    "reliability_certification_review": "review_id",
    "manufacturing_readiness_review": "review_id",
    "release_decision": "decision_id",
    "engineering_change_order": "change_order_id",
    "supplier_change": "change_id",
    "field_issue": "issue_id",
    "cross_case_knowledge_candidate": "rule_id",
    "approved_knowledge_rule": "rule_id",
    "engineering_task": "task_id",
    "engineering_gate": "gate_id",
    "engineering_tool_request": "request_id",
    "raw_engineering_tool_result": "result_id",
    "engineering_interpretation": "interpretation_id",
}


ENGINEERING_STAGES = (
    "concept_declared",
    "experience_reviewed",
    "engineering_ready",
    "prototype_ready",
    "physical_validation",
    "compliance_reviewed",
    "manufacturing_ready",
    "released",
)


def _record_id(object_type: str, record: EngineeringRecord) -> str:
    return str(getattr(record, _ID_FIELDS[object_type]))


def canonical_object_type(object_type: str) -> str:
    return ENGINEERING_OBJECT_TYPE_ALIASES.get(object_type, object_type)


def _node_key(ref: DependencyRef) -> str:
    return f"{ref.object_type}:{ref.object_id}:{ref.revision}"


class EngineeringOrchestrator:
    """Registry, dependency invalidation and human-gated task coordinator."""

    def __init__(self, repository: Any, *, actor: str = "ai-orchestrator") -> None:
        self.repository = repository
        self.actor = actor

    def register_object(self, object_type: str, value: EngineeringRecord, *, current: bool = True, auto_invalidate: bool = True) -> EngineeringRecord:
        object_type = canonical_object_type(object_type)
        model = ENGINEERING_MODEL_TYPES.get(object_type)
        if model is None:
            raise ValueError(f"unknown engineering object type: {object_type}")
        if not isinstance(value, model):
            raise TypeError(f"{object_type} expects {model.__name__}")
        normalized_dependencies = tuple(
            DependencyRef(
                object_type=canonical_object_type(item.object_type),
                object_id=item.object_id,
                revision=item.revision,
            )
            for item in value.dependencies
        )
        if normalized_dependencies != value.dependencies:
            value = value.model_copy(update={"dependencies": normalized_dependencies})
        object_id = _record_id(object_type, value)
        previous = self.repository.get_current(object_type, object_id)
        event_id = f"engineering-event-{uuid4().hex}"
        event_type = (
            "EngineeringObjectInvalidated" if value.status == "invalidated"
            else "EngineeringObjectStale" if value.status == "stale"
            else "EngineeringGateReviewed" if object_type == "engineering_gate"
            else "EngineeringTaskRevisionCreated" if object_type == "engineering_task"
            else "EngineeringProjectRevisionCreated" if object_type == "engineering_project"
            else "EngineeringObjectRevisionCreated"
        )
        domain_event = DomainEvent(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=object_id,
            aggregate_revision_id=value.revision_id,
            data=(
                ("object_type", object_type),
                ("status", value.status),
                ("parent_revision_id", value.meta.parent_revision_id or ""),
            ),
        )
        audit_event = AuditEvent(
            audit_id=f"engineering-audit-{uuid4().hex}",
            action=event_type,
            target_id=object_id,
            target_revision_id=value.revision_id,
            actor=value.meta.created_by,
            reason=value.meta.reason,
            expected_revision=previous.meta.revision if previous is not None else None,
        )
        if hasattr(self.repository, "save_command"):
            saved = self.repository.save_command(
                object_type,
                object_id,
                value.revision_id,
                value,
                expected_revision=(previous.meta.revision if previous is not None else None),
                domain_events=(domain_event,),
                audit_events=(audit_event,),
            )
            if not current:
                # ``save_command`` advances current atomically.  Restore the
                # prior pointer only for the rare history-only registration.
                if previous is not None:
                    self.repository.set_current(object_type, object_id, previous.revision_id)
        else:
            saved = self.repository.save(object_type, object_id, value.revision_id, value, current=current)
            self.repository.emit_domain(domain_event)
            self.repository.record_audit(audit_event)
        # New revisions are append-only.  Once an upstream aggregate advances,
        # all current dependents become stale immediately; callers may still
        # invoke ``propagate_invalidation`` explicitly to obtain the affected
        # revision list.
        if (
            auto_invalidate
            and current
            and previous is not None
            and value.meta.revision > previous.meta.revision
            and value.status not in {"stale", "invalidated"}
        ):
            self.propagate_invalidation(
                DependencyRef(object_type=object_type, object_id=object_id, revision=value.meta.revision),
                reason=f"{object_type} revision advanced",
            )
        return saved

    # Short aliases make this usable as a registry from adapters.
    register = register_object

    def get_current(self, object_type: str, object_id: str) -> EngineeringRecord | None:
        return self.repository.get_current(canonical_object_type(object_type), object_id)

    def list_objects(self, object_type: str) -> list[EngineeringRecord]:
        return list(self.repository.list_revisions(canonical_object_type(object_type)))

    def stale_objects(self) -> tuple[EngineeringRecord, ...]:
        """Return the latest stale/invalidated revision per aggregate."""
        result: list[EngineeringRecord] = []
        for object_type in ENGINEERING_MODEL_TYPES:
            grouped: dict[str, list[EngineeringRecord]] = {}
            for item in self.list_objects(object_type):
                grouped.setdefault(_record_id(object_type, item), []).append(item)
            result.extend(
                latest for latest in (
                    max(items, key=lambda item: item.meta.revision) for items in grouped.values()
                ) if latest.status in {"stale", "invalidated"}
            )
        return tuple(result)

    def build_dependency_graph(self, *, actor: str | None = None) -> DependencyGraphRevision:
        refs: list[DependencyRef] = []
        edges: list[tuple[str, str]] = []
        declared_keys: set[str] = set()
        dependency_keys: set[str] = set()
        graph_types: dict[str, str] = {key: key for key in ENGINEERING_MODEL_TYPES}
        graph_types.update({key: key for key in LEGACY_MODEL_TYPES})
        for object_type in graph_types:
            for item in self.list_objects(object_type):
                if object_type in LEGACY_MODEL_TYPES:
                    object_id = str(getattr(item, LEGACY_MODEL_TYPES[object_type][1]))
                else:
                    object_id = _record_id(object_type, item)
                ref = DependencyRef(object_type=object_type, object_id=object_id, revision=item.meta.revision)
                refs.append(ref)
                declared_keys.add(_node_key(ref))
                for dependency in getattr(item, "dependencies", ()):
                    dependency = DependencyRef(
                        object_type=canonical_object_type(dependency.object_type),
                        object_id=dependency.object_id,
                        revision=dependency.revision,
                    )
                    edges.append((_node_key(ref), _node_key(dependency)))
                    dependency_keys.add(_node_key(dependency))
                    if _node_key(dependency) not in declared_keys:
                        refs.append(dependency)
        # A dependency can point at a legacy M1/M2/M3 object that is not in
        # the engineering registry.  Retain that node for graph integrity,
        # but make the graph explicitly incomplete rather than dropping it.
        known = {_node_key(ref) for ref in refs}
        unknown = any(right not in declared_keys for right in dependency_keys)
        closed = bool(refs) and not unknown and all(left in known and right in known for left, right in edges)
        status = "dependency_revision_unknown" if unknown else ("closed" if closed else "incomplete")
        graph_id = f"engineering-graph-{uuid4().hex[:12]}"
        unique_refs = tuple({(_node_key(ref)): ref for ref in refs}.values())
        graph = DependencyGraphRevision(
            graph_id=graph_id,
            revision_id=f"{graph_id}.r1",
            meta=RevisionMeta(revision=1, created_by=actor or self.actor, reason="engineering dependency graph"),
            nodes=unique_refs,
            edges=tuple(edges),
            status=status,
            field_coverage=("revision_id", "dependencies", "provenance", "status"),
        )
        self.repository.save("dependency_graph", graph.graph_id, graph.revision_id, graph)
        return graph

    def propagate_invalidation(
        self,
        changed: DependencyRef,
        *,
        reason: str = "upstream revision changed",
        invalidated: bool = False,
        actor: str | None = None,
    ) -> tuple[EngineeringRecord, ...]:
        """Create stale/invalidated revisions for all transitive dependents."""
        queue: deque[DependencyRef] = deque([changed])
        affected: list[EngineeringRecord] = []
        seen: set[tuple[str, str, int]] = set()
        while queue:
            upstream = queue.popleft()
            upstream = DependencyRef(
                object_type=canonical_object_type(upstream.object_type),
                object_id=upstream.object_id,
                revision=upstream.revision,
            )
            marker = (upstream.object_type, upstream.object_id, upstream.revision)
            if marker in seen:
                continue
            seen.add(marker)
            for object_type in ENGINEERING_MODEL_TYPES:
                all_items = self.list_objects(object_type)
                # A repository's list operation is history-oriented, so group
                # by aggregate ID before selecting each aggregate's current
                # revision.  This is important when multiple CAD/BOM branches
                # coexist in one registry.
                by_id: dict[str, list[EngineeringRecord]] = {}
                for item in all_items:
                    by_id.setdefault(_record_id(object_type, item), []).append(item)
                for object_id, object_revisions in by_id.items():
                    current = max(object_revisions, key=lambda item: item.meta.revision)
                    if not any(
                        canonical_object_type(dep.object_type) == canonical_object_type(upstream.object_type)
                        and dep.object_id == upstream.object_id
                        and dep.revision != upstream.revision
                        for dep in current.dependencies
                    ):
                        continue
                    if current.status in {"stale", "invalidated"}:
                        # Idempotent propagation: an earlier registration may
                        # already have materialized this stale revision.
                        affected.append(current)
                        queue.append(DependencyRef(object_type=object_type, object_id=object_id, revision=current.meta.revision))
                        continue
                    next_revision = max(item.meta.revision for item in object_revisions) + 1
                    new_revision_id = f"{object_id}.r{next_revision}"
                    new_status = "invalidated" if invalidated else "stale"
                    updated = current.model_copy(update={
                        "revision_id": new_revision_id,
                        "meta": RevisionMeta(revision=next_revision, parent_revision_id=current.revision_id, created_by=actor or self.actor, reason=reason),
                        "status": new_status,
                        "stale_reasons": tuple(dict.fromkeys((*current.stale_reasons, f"{upstream.object_type}:{upstream.object_id} changed to r{upstream.revision}", reason))),
                    })
                    self.register_object(object_type, updated, auto_invalidate=False)
                    affected.append(updated)
                    queue.append(DependencyRef(object_type=object_type, object_id=object_id, revision=next_revision))
        return tuple(affected)

    invalidate_dependents = propagate_invalidation

    def invalidate_objects(
        self,
        targets: Iterable[DependencyRef],
        *,
        reason: str,
        invalidated: bool = False,
        actor: str | None = None,
    ) -> tuple[EngineeringRecord, ...]:
        """Mark named current objects stale, then propagate to dependents."""
        affected: list[EngineeringRecord] = []
        seen: set[tuple[str, str, int]] = set()
        for target in targets:
            object_type = canonical_object_type(target.object_type)
            if object_type not in ENGINEERING_MODEL_TYPES:
                raise DomainStateError(f"cannot invalidate unsupported object type: {object_type}")
            current = self.repository.get_current(object_type, target.object_id)
            if current is None:
                raise DomainStateError(f"cannot invalidate unavailable object: {object_type}:{target.object_id}")
            if current.meta.revision != target.revision:
                raise DomainStateError(f"cannot invalidate stale target reference: {object_type}:{target.object_id}")
            if current.status in {"stale", "invalidated"}:
                stale = current
            else:
                next_revision = current.meta.revision + 1
                stale = current.model_copy(update={
                    "revision_id": f"{target.object_id}.r{next_revision}",
                    "meta": RevisionMeta(
                        revision=next_revision,
                        parent_revision_id=current.revision_id,
                        created_by=actor or self.actor,
                        reason=reason,
                    ),
                    "status": "invalidated" if invalidated else "stale",
                    "stale_reasons": tuple(dict.fromkeys((*current.stale_reasons, reason))),
                })
                self.register_object(object_type, stale, auto_invalidate=False)
            key = (object_type, target.object_id, stale.meta.revision)
            if key not in seen:
                affected.append(stale)
                seen.add(key)
            for item in self.propagate_invalidation(
                DependencyRef(object_type=object_type, object_id=target.object_id, revision=stale.meta.revision),
                reason=reason,
                invalidated=invalidated,
                actor=actor,
            ):
                item_type = next(
                    name for name, model in ENGINEERING_MODEL_TYPES.items() if isinstance(item, model)
                )
                item_key = (item_type, _record_id(item_type, item), item.meta.revision)
                if item_key not in seen:
                    affected.append(item)
                    seen.add(item_key)
        return tuple(affected)

    def create_task(self, *, task_id: str, role: str, action: str, dependencies: Iterable[DependencyRef] = (), depends_on_task_ids: Iterable[str] = (), human_gate_required: bool = False, assigned_to: str | None = None, actor: str | None = None) -> EngineeringTask:
        dependency_refs = tuple(dependencies)
        task_dependencies = tuple(depends_on_task_ids)
        task = EngineeringTask(
            task_id=task_id,
            revision_id=f"{task_id}.r1",
            meta=RevisionMeta(revision=1, created_by=actor or self.actor, reason="engineering task created"),
            role=role,
            action=action,
            dependencies=dependency_refs,
            depends_on_task_ids=task_dependencies,
            human_gate_required=human_gate_required,
            assigned_to=assigned_to,
            task_status="queued" if (task_dependencies or dependency_refs) else "ready",
        )
        self.register_object("engineering_task", task)
        return task

    def ready_tasks(self) -> tuple[EngineeringTask, ...]:
        """Return queued tasks whose task and object dependencies are current."""
        latest: dict[str, EngineeringTask] = {}
        for item in self.list_objects("engineering_task"):
            current = latest.get(item.task_id)
            if current is None or item.meta.revision > current.meta.revision:
                latest[item.task_id] = item
        ready: list[EngineeringTask] = []
        for task in latest.values():
            if task.task_status not in {"queued", "ready"}:
                continue
            if any(
                latest.get(dep_id) is None
                or latest[dep_id].task_status != "completed"
                or latest[dep_id].status in {"stale", "invalidated", "blocked", "rejected"}
                for dep_id in task.depends_on_task_ids
            ):
                continue
            if any(
                (current := self.repository.get_current(canonical_object_type(dep.object_type), dep.object_id)) is None
                or current.meta.revision != dep.revision
                or getattr(current, "status", "current") in {"stale", "invalidated", "blocked", "rejected"}
                for dep in task.dependencies
            ):
                continue
            ready.append(task)
        return tuple(ready)

    def update_task(self, task: EngineeringTask, *, status: str, result_revision_ids: Iterable[str] = (), actor: str | None = None) -> EngineeringTask:
        if status == "completed" and task.human_gate_required and (actor or self.actor).startswith("ai"):
            raise DomainStateError("AI cannot complete a human-gated engineering task")
        revisions = self.list_objects("engineering_task")
        revision = max((item.meta.revision for item in revisions if item.task_id == task.task_id), default=task.meta.revision) + 1
        updated = task.model_copy(update={
            "revision_id": f"{task.task_id}.r{revision}",
            "meta": RevisionMeta(revision=revision, parent_revision_id=task.revision_id, created_by=actor or self.actor, reason="engineering task updated"),
            "task_status": status,
            "result_revision_ids": tuple(result_revision_ids),
        })
        self.register_object("engineering_task", updated)
        return updated

    def approve_gate(self, *, target_object_type: str, target_object_id: str, target_revision_id: str, from_stage: str, to_stage: str, reviewer: str, evidence_refs: Iterable[str] = (), rationale: str, decision: Literal["approved", "blocked", "conditional"] = "approved", actor: str = "human") -> EngineeringGateDecision:
        if actor.lower().startswith("ai") or reviewer.lower().startswith("ai"):
            raise DomainStateError("engineering gates require a named human reviewer")
        if from_stage not in ENGINEERING_STAGES or to_stage not in ENGINEERING_STAGES:
            raise ValueError("unknown engineering stage")
        if ENGINEERING_STAGES.index(to_stage) != ENGINEERING_STAGES.index(from_stage) + 1:
            raise ValueError("engineering stage transitions must advance exactly one gate")
        evidence_refs = tuple(evidence_refs)
        if decision == "approved" and not evidence_refs:
            raise DomainStateError("approved engineering gate requires explicit evidence references")
        gate_id = f"gate-{uuid4().hex[:12]}"
        status = decision
        gate = EngineeringGateDecision(
            gate_id=gate_id,
            revision_id=f"{gate_id}.r1",
            meta=RevisionMeta(revision=1, created_by=reviewer, reason="human engineering gate review"),
            target_object_type=target_object_type,
            target_object_id=target_object_id,
            target_revision_id=target_revision_id,
            from_stage=from_stage,
            to_stage=to_stage,
            reviewer=reviewer,
            evidence_refs=evidence_refs,
            decision=decision,
            status=status,
            rationale=rationale,
        )
        return self.register_object("engineering_gate", gate)


# Registry is a useful name for callers that only need object persistence;
# it intentionally shares the orchestrator implementation so dependency and
# gate semantics cannot diverge between two services.
EngineeringRegistry = EngineeringOrchestrator
EngineeringObjectRegistry = EngineeringOrchestrator


def dependency_ref(object_type: str, object_id: str, revision: int) -> DependencyRef:
    """Convenience constructor used by adapters and orchestration plans."""
    return DependencyRef(
        object_type=canonical_object_type(object_type),
        object_id=object_id,
        revision=revision,
    )


__all__ = [
    "EngineeringRecord", "RequirementDeclaration", "DigitalExperienceSignal",
    "DiscoveryTriageDecision", "DigitalExperienceDiscovery", "EngineeringIntake", "EngineeringProjectRevision",
    "EngineeringRequirement", "EngineeringConflict", "MechanicalArchitecture",
    "MaterialProcessChoice", "CADArtifact", "BOMRevision", "ToleranceStack",
    "CAEAnalysisRun", "DFMReview", "FMEARevision", "DVPRevision", "VerificationTestRun",
    "PilotBuildRun", "ReliabilityCertificationReview", "ManufacturingReadinessReview",
    "ReleaseDecision", "EngineeringChangeOrder", "SupplierChangeRecord", "FieldIssue",
    "CrossCaseEvidenceRef", "CrossCaseKnowledgeCandidate", "ApprovedKnowledgeRule", "EngineeringTask",
    "EngineeringGateDecision", "EngineeringOrchestrator", "EngineeringRegistry", "EngineeringObjectRegistry", "ENGINEERING_MODEL_TYPES",
    "ENGINEERING_STAGES", "dependency_ref", "EngineeringArtifactRef",
    "EngineeringToolRequest", "RawEngineeringToolResult", "EngineeringInterpretation",
]
