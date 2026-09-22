"""Immutable upper-domain snapshots for the Product Studio.

These models sit above the existing experience/design/engineering kernel.
They describe why a product should exist and what outcome it must pursue;
they do not replace lower-level briefs, evidence, or engineering records.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from psyteardown.experience.models import (
    DependencyRef,
    FrozenModel,
    Identifier,
    RevisionMeta,
)


def _duplicates(values: tuple[str, ...]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _require_dependencies(
    dependencies: tuple[DependencyRef, ...], required_types: tuple[str, ...]
) -> None:
    actual = {dependency.object_type for dependency in dependencies}
    missing = set(required_types) - actual
    if missing:
        raise ValueError(
            "missing required dependencies: " + ", ".join(sorted(missing))
        )


class SourceReference(FrozenModel):
    """A compact pointer to the origin of a product-domain statement."""

    source_type: Literal[
        "user_input",
        "imported_artifact",
        "research",
        "evidence",
        "tool_result",
        "model_proposal",
        "human_decision",
    ]
    source_id: Identifier
    revision_id: str | None = None
    locator: str | None = None


class HumanConfirmation(FrozenModel):
    confirmed_by: Identifier
    confirmed_at: datetime
    rationale: Identifier


class ProductProject(FrozenModel):
    """Minimal project lifecycle aggregate; child objects remain independent."""

    project_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    name: Identifier
    collaboration_mode: Literal["managed", "co_design", "governance"] = "managed"
    status: Literal["active", "paused", "archived"] = "active"
    created_from: tuple[SourceReference, ...] = ()


class ProductIntent(FrozenModel):
    """A user-correctable statement of the reality worth changing."""

    intent_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    project_id: Identifier
    status: Literal["proposed", "confirmed"] = "proposed"
    desired_change: Identifier
    affected_people: tuple[Identifier, ...] = Field(min_length=1)
    current_situation: str | None = None
    explicit_non_goals: tuple[str, ...] = ()
    known_constraints: tuple[str, ...] = ()
    resource_preferences: tuple[str, ...] = ()
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)
    confirmation: HumanConfirmation | None = None

    @model_validator(mode="after")
    def confirmation_matches_status(self) -> "ProductIntent":
        if self.status == "confirmed" and self.confirmation is None:
            raise ValueError("confirmed product intent requires human confirmation")
        if self.status == "proposed" and self.confirmation is not None:
            raise ValueError("proposed product intent cannot carry confirmation")
        return self


class ProblemFact(FrozenModel):
    fact_id: Identifier
    statement: Identifier
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)


class ProblemAssumption(FrozenModel):
    assumption_id: Identifier
    statement: Identifier
    consequence_if_wrong: Identifier
    cheapest_validation: Identifier


class ProblemUnknown(FrozenModel):
    unknown_id: Identifier
    question: Identifier
    decision_impact: Identifier
    next_step: Identifier


class CompetingExplanation(FrozenModel):
    explanation_id: Identifier
    statement: Identifier
    supporting_fact_ids: tuple[str, ...] = ()
    contradicting_fact_ids: tuple[str, ...] = ()
    cheapest_falsification: Identifier


class StakeholderTension(FrozenModel):
    tension_id: Identifier
    stakeholder_refs: tuple[Identifier, ...] = Field(min_length=2)
    description: Identifier
    unresolved_value_choice: Identifier


class ProblemModel(FrozenModel):
    """Versioned separation of reality, interpretation, and uncertainty."""

    problem_model_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    project_id: Identifier
    intent_revision_id: Identifier
    status: Literal["proposed", "confirmed"] = "proposed"
    facts: tuple[ProblemFact, ...] = ()
    assumptions: tuple[ProblemAssumption, ...] = ()
    unknowns: tuple[ProblemUnknown, ...] = ()
    competing_explanations: tuple[CompetingExplanation, ...] = ()
    stakeholder_tensions: tuple[StakeholderTension, ...] = ()
    dependencies: tuple[DependencyRef, ...] = Field(min_length=1)
    confirmation: HumanConfirmation | None = None

    @model_validator(mode="after")
    def validate_problem_model(self) -> "ProblemModel":
        _require_dependencies(self.dependencies, ("product_intent",))
        id_groups = (
            ("fact", tuple(item.fact_id for item in self.facts)),
            ("assumption", tuple(item.assumption_id for item in self.assumptions)),
            ("unknown", tuple(item.unknown_id for item in self.unknowns)),
            (
                "explanation",
                tuple(item.explanation_id for item in self.competing_explanations),
            ),
            ("tension", tuple(item.tension_id for item in self.stakeholder_tensions)),
        )
        for label, values in id_groups:
            duplicates = _duplicates(values)
            if duplicates:
                raise ValueError(f"duplicate {label} IDs: {sorted(duplicates)}")

        fact_ids = {item.fact_id for item in self.facts}
        for explanation in self.competing_explanations:
            referenced = set(explanation.supporting_fact_ids) | set(
                explanation.contradicting_fact_ids
            )
            unknown = referenced - fact_ids
            if unknown:
                raise ValueError(
                    f"explanation {explanation.explanation_id} references unknown facts: "
                    + ", ".join(sorted(unknown))
                )

        if self.status == "confirmed":
            if self.confirmation is None:
                raise ValueError("confirmed problem model requires human confirmation")
            if not self.facts:
                raise ValueError("confirmed problem model requires at least one sourced fact")
            if len(self.competing_explanations) < 2:
                raise ValueError(
                    "confirmed problem model requires at least two competing explanations"
                )
        elif self.confirmation is not None:
            raise ValueError("proposed problem model cannot carry confirmation")
        return self


class DeliveryMaturity(StrEnum):
    CONCEPT = "concept"
    RUNNABLE_PROTOTYPE = "runnable_prototype"
    FIELD_TRIAL = "field_trial"
    OPERATIONAL_CANDIDATE = "operational_candidate"
    RELEASED_PRODUCT = "released_product"


class SuccessIndicator(FrozenModel):
    indicator_id: Identifier
    operational_definition: Identifier
    observation_method: Identifier
    desired_direction: Identifier
    threshold_or_target: Identifier
    required_evidence: Literal[
        "deterministic_check",
        "tool_result",
        "expert_review",
        "real_user_observation",
        "operational_result",
    ]


class TargetOutcome(FrozenModel):
    outcome_id: Identifier
    description: Identifier
    indicator_ids: tuple[Identifier, ...] = ()


class ProhibitedOutcome(FrozenModel):
    prohibited_outcome_id: Identifier
    description: Identifier
    severity: Literal["hard", "strong_avoidance", "watch"]
    detection_method: Identifier
    response: Identifier


class ResourceBoundary(FrozenModel):
    time_budget: str | None = None
    economic_budget: str | None = None
    user_attention_budget: str | None = None
    maintenance_budget: str | None = None
    data_boundary: str | None = None
    explicit_unknowns: tuple[str, ...] = ()

    @model_validator(mode="after")
    def at_least_one_boundary_or_unknown(self) -> "ResourceBoundary":
        values = (
            self.time_budget,
            self.economic_budget,
            self.user_attention_budget,
            self.maintenance_budget,
            self.data_boundary,
        )
        if not any(values) and not self.explicit_unknowns:
            raise ValueError("resource boundary must declare a limit or an explicit unknown")
        return self


class StopCondition(FrozenModel):
    condition_id: Identifier
    condition: Identifier
    action: Literal["pause", "stop", "reframe", "escalate"]


class OutcomeContract(FrozenModel):
    """Human-confirmed outcome and delivery boundary for product search."""

    outcome_contract_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    project_id: Identifier
    intent_revision_id: Identifier
    problem_model_revision_id: Identifier
    status: Literal["proposed", "confirmed"] = "proposed"
    target_segments: tuple[str, ...] = ()
    applicable_contexts: tuple[str, ...] = ()
    target_outcomes: tuple[TargetOutcome, ...] = ()
    success_indicators: tuple[SuccessIndicator, ...] = ()
    prohibited_outcomes: tuple[ProhibitedOutcome, ...] = ()
    prohibited_outcomes_reviewed: bool = False
    resource_boundary: ResourceBoundary
    stop_conditions: tuple[StopCondition, ...] = ()
    minimum_delivery_maturity: DeliveryMaturity = DeliveryMaturity.CONCEPT
    required_real_world_evidence: tuple[str, ...] = ()
    dependencies: tuple[DependencyRef, ...] = Field(min_length=2)
    confirmation: HumanConfirmation | None = None

    @model_validator(mode="after")
    def validate_outcome_contract(self) -> "OutcomeContract":
        _require_dependencies(
            self.dependencies, ("product_intent", "problem_model")
        )
        outcome_ids = tuple(item.outcome_id for item in self.target_outcomes)
        indicator_ids = tuple(item.indicator_id for item in self.success_indicators)
        prohibited_ids = tuple(
            item.prohibited_outcome_id for item in self.prohibited_outcomes
        )
        stop_ids = tuple(item.condition_id for item in self.stop_conditions)
        for label, values in (
            ("outcome", outcome_ids),
            ("indicator", indicator_ids),
            ("prohibited outcome", prohibited_ids),
            ("stop condition", stop_ids),
        ):
            duplicates = _duplicates(values)
            if duplicates:
                raise ValueError(f"duplicate {label} IDs: {sorted(duplicates)}")

        available_indicators = set(indicator_ids)
        for outcome in self.target_outcomes:
            unknown = set(outcome.indicator_ids) - available_indicators
            if unknown:
                raise ValueError(
                    f"outcome {outcome.outcome_id} references unknown indicators: "
                    + ", ".join(sorted(unknown))
                )

        if self.status == "confirmed":
            if self.confirmation is None:
                raise ValueError("confirmed outcome contract requires human confirmation")
            if not self.target_segments or not self.applicable_contexts:
                raise ValueError(
                    "confirmed outcome contract requires target segments and contexts"
                )
            if not self.target_outcomes:
                raise ValueError("confirmed outcome contract requires a target outcome")
            if any(not outcome.indicator_ids for outcome in self.target_outcomes):
                raise ValueError(
                    "every confirmed target outcome requires at least one indicator"
                )
            if not self.prohibited_outcomes_reviewed:
                raise ValueError(
                    "confirmed outcome contract requires prohibited-outcome review"
                )
            if not self.stop_conditions:
                raise ValueError("confirmed outcome contract requires a stop condition")
            if not self.required_real_world_evidence:
                raise ValueError(
                    "confirmed outcome contract requires real-world evidence requirements"
                )
        elif self.confirmation is not None:
            raise ValueError("proposed outcome contract cannot carry confirmation")
        return self


class MechanismHypothesis(FrozenModel):
    mechanism_id: Identifier
    condition: Identifier
    proposed_intervention: Identifier
    expected_change: Identifier
    uncertainty: Identifier
    evidence_refs: tuple[SourceReference, ...] = ()


class FalsifiablePrediction(FrozenModel):
    prediction_id: Identifier
    prediction: Identifier
    failure_observation: Identifier
    cheapest_test: Identifier


class ValidationStep(FrozenModel):
    validation_step_id: Identifier
    question: Identifier
    method: Identifier
    evidence_level: Literal[
        "deterministic_check",
        "simulation",
        "expert_review",
        "real_user_observation",
        "operational_result",
    ]
    pass_condition: Identifier
    estimated_cost: Identifier


class DeliveryEstimate(FrozenModel):
    initial_delivery_cost: Identifier
    operating_cost: Identifier
    maintenance_burden: Identifier


class ThesisDisposition(FrozenModel):
    action: Literal["exploring", "selected", "paused", "rejected"]
    decided_by: Identifier
    actor_type: Literal["human", "system"]
    decided_at: datetime
    rationale: Identifier
    authorization_ref: str | None = None


class ProductThesis(FrozenModel):
    """One differentiated and falsifiable route toward an outcome contract."""

    thesis_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    project_id: Identifier
    problem_model_revision_id: Identifier
    outcome_contract_revision_id: Identifier
    status: Literal["proposed", "exploring", "selected", "paused", "rejected"] = (
        "proposed"
    )
    name: Identifier
    product_promise: Identifier
    differentiation: Identifier
    realization_modes: tuple[
        Literal["software", "hardware", "service", "content", "process", "hybrid"],
        ...,
    ] = Field(min_length=1)
    mechanism_hypotheses: tuple[MechanismHypothesis, ...] = Field(min_length=1)
    falsifiable_predictions: tuple[FalsifiablePrediction, ...] = Field(min_length=1)
    validation_strategy: tuple[ValidationStep, ...] = Field(min_length=1)
    key_unknowns: tuple[Identifier, ...] = Field(min_length=1)
    key_risks: tuple[Identifier, ...] = Field(min_length=1)
    delivery_estimate: DeliveryEstimate
    dependencies: tuple[DependencyRef, ...] = Field(min_length=2)
    disposition: ThesisDisposition | None = None

    @model_validator(mode="after")
    def validate_product_thesis(self) -> "ProductThesis":
        _require_dependencies(
            self.dependencies, ("problem_model", "outcome_contract")
        )
        id_groups = (
            (
                "mechanism",
                tuple(item.mechanism_id for item in self.mechanism_hypotheses),
            ),
            (
                "prediction",
                tuple(item.prediction_id for item in self.falsifiable_predictions),
            ),
            (
                "validation step",
                tuple(item.validation_step_id for item in self.validation_strategy),
            ),
        )
        for label, values in id_groups:
            duplicates = _duplicates(values)
            if duplicates:
                raise ValueError(f"duplicate {label} IDs: {sorted(duplicates)}")

        if len(set(self.realization_modes)) != len(self.realization_modes):
            raise ValueError("product thesis realization modes must be unique")
        if self.status == "proposed" and self.disposition is not None:
            raise ValueError("proposed product thesis cannot carry a disposition")
        if self.status != "proposed":
            if self.disposition is None or self.disposition.action != self.status:
                raise ValueError(
                    "non-proposed product thesis requires a matching disposition"
                )
            if (
                self.status == "selected"
                and self.disposition.actor_type != "human"
                and not self.disposition.authorization_ref
            ):
                raise ValueError(
                    "selected product thesis requires a human decision or explicit authorization"
                )
        return self


# B2 freezes one realization template for the first digital-product slice.
# These constants are intentionally narrow: choosing a template does not grant
# permission to execute generated code or access external services.
WEB_TEMPLATE_ID = "react_typescript_vite_spa"
WEB_TEMPLATE_VERSION = "b2-v1"
WEB_RUNTIME_DEPENDENCIES = ("react", "react-dom")
WEB_DEVELOPMENT_DEPENDENCIES = (
    "@vitejs/plugin-react",
    "@playwright/test",
    "@testing-library/react",
    "typescript",
    "vite",
    "vitest",
)
WEB_OUTPUT_PATHS = (
    "src/main.tsx",
    "src/App.tsx",
    "src/styles.css",
    "tests/",
    "public/",
)


class WebScreenSpec(FrozenModel):
    screen_id: Identifier
    title: Identifier
    purpose: Identifier
    task_ids: tuple[Identifier, ...] = Field(min_length=1)
    state_ids: tuple[Identifier, ...] = Field(min_length=1)


class WebTaskSpec(FrozenModel):
    task_id: Identifier
    screen_id: Identifier
    goal: Identifier
    success_criteria: Identifier
    user_decision_limit: Identifier


class WebStateSpec(FrozenModel):
    state_id: Identifier
    kind: Literal[
        "ready", "loading", "empty", "error", "success", "paused", "stopped"
    ]
    user_visible_behavior: Identifier
    recovery_action: Identifier


class WebContentSlot(FrozenModel):
    slot_id: Identifier
    semantic_role: Literal[
        "heading",
        "instruction",
        "label",
        "status",
        "error",
        "confirmation",
    ]
    description: Identifier
    source_kind: Literal[
        "outcome_contract",
        "product_thesis",
        "user_input",
        "local_fixture",
    ]
    fallback_text: Identifier
    required: bool = True


class WebAcceptanceCheck(FrozenModel):
    check_id: Identifier
    task_id: Identifier
    assertion: Identifier
    evidence_level: Literal["deterministic_check"] = "deterministic_check"


class WebProductGenerationContract(FrozenModel):
    """Minimal, traceable input contract for the first Web realization.

    This object describes what a later generator may build. It is deliberately
    not a source tree, dependency lockfile, execution grant, or user-result
    claim.
    """

    web_generation_contract_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    project_id: Identifier
    product_thesis_revision_id: Identifier
    outcome_contract_revision_id: Identifier
    status: Literal["proposed", "confirmed"] = "proposed"
    template_id: Literal["react_typescript_vite_spa"] = WEB_TEMPLATE_ID
    template_version: Identifier = WEB_TEMPLATE_VERSION
    app_title: Identifier
    screens: tuple[WebScreenSpec, ...] = Field(min_length=1, max_length=5)
    tasks: tuple[WebTaskSpec, ...] = Field(min_length=1, max_length=8)
    states: tuple[WebStateSpec, ...] = Field(min_length=5, max_length=20)
    content_slots: tuple[WebContentSlot, ...] = Field(min_length=1, max_length=20)
    acceptance_checks: tuple[WebAcceptanceCheck, ...] = Field(min_length=1, max_length=20)
    runtime_dependencies: tuple[str, ...] = WEB_RUNTIME_DEPENDENCIES
    development_dependencies: tuple[str, ...] = WEB_DEVELOPMENT_DEPENDENCIES
    output_paths: tuple[str, ...] = WEB_OUTPUT_PATHS
    network_policy: Literal["none"] = "none"
    data_policy: Literal["local_fixture_only"] = "local_fixture_only"
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)
    dependencies: tuple[DependencyRef, ...] = Field(min_length=2)
    confirmation: HumanConfirmation | None = None

    @model_validator(mode="after")
    def validate_generation_contract(self) -> "WebProductGenerationContract":
        _require_dependencies(
            self.dependencies, ("product_thesis", "outcome_contract")
        )
        if self.template_id != WEB_TEMPLATE_ID:
            raise ValueError("unsupported Web realization template")
        if self.template_version != WEB_TEMPLATE_VERSION:
            raise ValueError("unsupported Web realization template version")
        if self.runtime_dependencies != WEB_RUNTIME_DEPENDENCIES:
            raise ValueError("Web runtime dependencies are fixed for the first slice")
        if self.development_dependencies != WEB_DEVELOPMENT_DEPENDENCIES:
            raise ValueError(
                "Web development dependencies are fixed for the first slice"
            )
        if self.output_paths != WEB_OUTPUT_PATHS:
            raise ValueError("Web output layout is fixed for the first slice")
        screen_ids = tuple(item.screen_id for item in self.screens)
        task_ids = tuple(item.task_id for item in self.tasks)
        state_ids = tuple(item.state_id for item in self.states)
        slot_ids = tuple(item.slot_id for item in self.content_slots)
        check_ids = tuple(item.check_id for item in self.acceptance_checks)
        for label, values in (
            ("screen", screen_ids),
            ("task", task_ids),
            ("state", state_ids),
            ("content slot", slot_ids),
            ("acceptance check", check_ids),
        ):
            duplicates = _duplicates(values)
            if duplicates:
                raise ValueError(f"duplicate Web {label} IDs: {sorted(duplicates)}")
        screen_set = set(screen_ids)
        task_set = set(task_ids)
        state_set = set(state_ids)
        for task in self.tasks:
            if task.screen_id not in screen_set:
                raise ValueError(f"task {task.task_id} references an unknown screen")
        for screen in self.screens:
            if not set(screen.task_ids) <= task_set:
                raise ValueError(f"screen {screen.screen_id} references an unknown task")
            if not set(screen.state_ids) <= state_set:
                raise ValueError(f"screen {screen.screen_id} references an unknown state")
        for check in self.acceptance_checks:
            if check.task_id not in task_set:
                raise ValueError(
                    f"acceptance check {check.check_id} references an unknown task"
                )
        required_states = {"ready", "loading", "empty", "error", "success"}
        missing_states = required_states - {item.kind for item in self.states}
        if missing_states:
            raise ValueError(
                "Web contract must define ready/loading/empty/error/success states; "
                + ", ".join(sorted(missing_states))
            )
        if self.status == "confirmed" and self.confirmation is None:
            raise ValueError("confirmed Web generation contract requires human confirmation")
        if self.status == "proposed" and self.confirmation is not None:
            raise ValueError("proposed Web generation contract cannot carry confirmation")
        thesis_dep = next(
            (item for item in self.dependencies if item.object_type == "product_thesis"),
            None,
        )
        if thesis_dep is None:
            raise ValueError("Web generation contract requires a product thesis dependency")
        if self.product_thesis_revision_id != (
            f"{thesis_dep.object_id}.r{thesis_dep.revision}"
        ):
            raise ValueError("Web generation contract thesis dependency does not match its revision")
        return self


class RevisionImpact(FrozenModel):
    dependent_type: Literal[
        "problem_model",
        "outcome_contract",
        "product_thesis",
        "web_generation_contract",
    ]
    dependent_id: Identifier
    dependent_revision_id: Identifier
    impact: Literal["review_required", "stale"]
    changed_dependency: DependencyRef
    reason: Identifier


class ProductProjectView(FrozenModel):
    """Read-only composition of independent current revisions for one project."""

    project: ProductProject
    product_intent: ProductIntent | None = None
    problem_model: ProblemModel | None = None
    outcome_contract: OutcomeContract | None = None
    product_theses: tuple[ProductThesis, ...] = ()
    web_generation_contract: WebProductGenerationContract | None = None
    recorded_impacts: tuple[RevisionImpact, ...] = ()


class ProductProposalJob(FrozenModel):
    """Persisted, revision-pinned work that may only create a proposal."""

    job_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    project_id: Identifier
    kind: Literal[
        "product_intent",
        "problem_model",
        "outcome_contract",
        "product_theses",
        "web_generation_contract",
    ]
    status: Literal[
        "queued", "running", "succeeded", "failed", "stale_input", "cancelled"
    ] = "queued"
    provider: Literal["deterministic_fake"] = "deterministic_fake"
    provider_version: Identifier = "b2-v1"
    input_dependencies: tuple[DependencyRef, ...] = Field(min_length=1)
    result_object_id: Identifier
    result_object_ids: tuple[Identifier, ...] = ()
    result_expected_revision: int | None = Field(default=None, ge=1)
    raw_input: str | None = None
    fingerprint: Identifier
    attempt: int = Field(default=0, ge=0)
    result_revision_id: str | None = None
    result_revision_ids: tuple[str, ...] = ()
    error_code: str | None = None
    error_summary: str | None = None

    @model_validator(mode="after")
    def validate_job_state(self) -> "ProductProposalJob":
        expected_types = {
            "product_intent": {"product_project"},
            "problem_model": {"product_intent"},
            "outcome_contract": {"product_intent", "problem_model"},
            "product_theses": {"problem_model", "outcome_contract"},
            "web_generation_contract": {"product_thesis", "outcome_contract"},
        }[self.kind]
        actual_types = {item.object_type for item in self.input_dependencies}
        if actual_types != expected_types:
            raise ValueError(
                f"{self.kind} job requires dependencies: "
                + ", ".join(sorted(expected_types))
            )
        if self.kind == "product_intent" and not self.raw_input:
            raise ValueError("product intent job requires the original raw input")
        if self.kind != "product_intent" and self.raw_input is not None:
            raise ValueError("only product intent jobs may retain raw input")
        if self.kind == "product_theses":
            if not 2 <= len(self.result_object_ids) <= 3:
                raise ValueError(
                    "product thesis job requires two or three result object IDs"
                )
            if len(set(self.result_object_ids)) != len(self.result_object_ids):
                raise ValueError("product thesis job result object IDs must be unique")
            if self.result_object_id != self.result_object_ids[0]:
                raise ValueError(
                    "product thesis job primary result must be its first result object"
                )
            if self.status == "succeeded" and (
                len(self.result_revision_ids) != len(self.result_object_ids)
                or self.result_revision_id != self.result_revision_ids[0]
            ):
                raise ValueError(
                    "succeeded product thesis job requires every result revision"
                )
        elif self.result_object_ids or self.result_revision_ids:
            raise ValueError("single-result proposal jobs cannot carry result lists")
        elif self.status == "succeeded" and not self.result_revision_id:
            raise ValueError("succeeded proposal job requires a result revision")
        if self.status == "failed" and (not self.error_code or not self.error_summary):
            raise ValueError("failed proposal job requires a safe error code and summary")
        if self.status != "failed" and (self.error_code or self.error_summary):
            raise ValueError("only failed proposal jobs may carry an error")
        return self


# B3 keeps source generation separate from proposal jobs.  A proposal creates
# a revision; a generation job materializes a confirmed realization contract in
# an isolated workspace.  The latter must therefore carry its own budget,
# sandbox declaration, checkpoint and artifact manifest.
GENERATION_JOB_PROVIDER = "deterministic_template"
GENERATION_JOB_VERSION = "b3-v1"
GENERATION_WORKSPACE_RELATIVE_ROOT = "workspaces"
GENERATION_DEFAULT_MAX_ATTEMPTS = 1
GENERATION_DEFAULT_MAX_FILES = 64
GENERATION_DEFAULT_MAX_BYTES = 1024 * 1024
GENERATION_DEFAULT_MAX_DURATION_SECONDS = 60
GENERATION_DEFAULT_MAX_COST_UNITS = 1


class GenerationBudget(FrozenModel):
    """Small, explicit limits for one local source-generation job."""

    max_attempts: int = Field(default=GENERATION_DEFAULT_MAX_ATTEMPTS, ge=1, le=3)
    max_files: int = Field(default=GENERATION_DEFAULT_MAX_FILES, ge=1, le=GENERATION_DEFAULT_MAX_FILES)
    max_bytes: int = Field(default=GENERATION_DEFAULT_MAX_BYTES, ge=1, le=GENERATION_DEFAULT_MAX_BYTES)
    max_duration_seconds: int = Field(
        default=GENERATION_DEFAULT_MAX_DURATION_SECONDS,
        ge=1,
        le=GENERATION_DEFAULT_MAX_DURATION_SECONDS,
    )
    max_cost_units: int = Field(
        default=GENERATION_DEFAULT_MAX_COST_UNITS,
        ge=1,
        le=GENERATION_DEFAULT_MAX_COST_UNITS,
    )


class GenerationSandboxPolicy(FrozenModel):
    """The B3 sandbox declaration; it is not an execution grant."""

    workspace_scope: Literal["project_job"] = "project_job"
    network_policy: Literal["none"] = "none"
    secret_policy: Literal["none"] = "none"
    execution_policy: Literal["not_executed"] = "not_executed"
    symlink_policy: Literal["deny"] = "deny"


class GeneratedFile(FrozenModel):
    path: Identifier
    byte_count: int = Field(ge=0)
    sha256: Identifier

    @model_validator(mode="after")
    def path_is_relative(self) -> "GeneratedFile":
        if self.path.startswith(("/", "\\")) or ".." in self.path.replace("\\", "/").split("/"):
            raise ValueError("generated file path must stay inside the workspace")
        return self


class GenerationManifest(FrozenModel):
    template_id: Literal["react_typescript_vite_spa"] = WEB_TEMPLATE_ID
    template_version: Identifier = WEB_TEMPLATE_VERSION
    files: tuple[GeneratedFile, ...] = Field(min_length=1)
    total_bytes: int = Field(ge=0)
    manifest_version: Literal["b3-v1"] = "b3-v1"

    @model_validator(mode="after")
    def totals_match(self) -> "GenerationManifest":
        paths = tuple(item.path for item in self.files)
        if len(set(paths)) != len(paths):
            raise ValueError("generation manifest file paths must be unique")
        if self.total_bytes != sum(item.byte_count for item in self.files):
            raise ValueError("generation manifest byte total does not match files")
        return self


class ProductGenerationJob(FrozenModel):
    """Persistent, revision-pinned materialization of a Web contract."""

    job_id: Identifier
    revision_id: Identifier
    meta: RevisionMeta
    project_id: Identifier
    kind: Literal["web_product"] = "web_product"
    status: Literal[
        "queued",
        "running",
        "paused",
        "succeeded",
        "failed",
        "stale_input",
        "budget_exhausted",
        "cancelled",
    ] = "queued"
    provider: Literal["deterministic_template"] = GENERATION_JOB_PROVIDER
    provider_version: Identifier = GENERATION_JOB_VERSION
    input_dependencies: tuple[DependencyRef, ...] = Field(min_length=1, max_length=1)
    web_generation_contract_revision_id: Identifier
    workspace_id: Identifier
    workspace_relative_path: Identifier
    budget: GenerationBudget = Field(default_factory=GenerationBudget)
    sandbox: GenerationSandboxPolicy = Field(default_factory=GenerationSandboxPolicy)
    fingerprint: Identifier
    attempt: int = Field(default=0, ge=0)
    checkpoint_step: Literal["prepare", "generate", "validate"] | None = None
    consumed_files: int = Field(default=0, ge=0)
    consumed_bytes: int = Field(default=0, ge=0)
    consumed_duration_seconds: float = Field(default=0, ge=0)
    consumed_cost_units: int = Field(default=0, ge=0)
    manifest: GenerationManifest | None = None
    error_code: str | None = None
    error_summary: str | None = None

    @model_validator(mode="after")
    def validate_generation_job(self) -> "ProductGenerationJob":
        if {item.object_type for item in self.input_dependencies} != {"web_generation_contract"}:
            raise ValueError("Web generation job requires one Web generation contract dependency")
        dependency = self.input_dependencies[0]
        if self.web_generation_contract_revision_id != f"{dependency.object_id}.r{dependency.revision}":
            raise ValueError("generation job contract dependency does not match its revision")
        if self.workspace_relative_path.startswith(("/", "\\")) or ".." in self.workspace_relative_path.replace("\\", "/").split("/"):
            raise ValueError("generation workspace path must be relative and contained")
        if self.status == "succeeded" and self.manifest is None:
            raise ValueError("succeeded generation job requires an artifact manifest")
        if self.status in {"failed", "budget_exhausted"} and (
            not self.error_code or not self.error_summary
        ):
            raise ValueError(
                "failed or budget-exhausted generation job requires a safe error code and summary"
            )
        if self.status not in {"failed", "budget_exhausted"} and (self.error_code or self.error_summary):
            raise ValueError("only failed or budget-exhausted generation jobs may carry an error")
        if self.manifest is not None:
            if self.manifest.template_id != WEB_TEMPLATE_ID or self.manifest.template_version != WEB_TEMPLATE_VERSION:
                raise ValueError("generation manifest template does not match the B3 template")
            if len(self.manifest.files) > self.budget.max_files or self.manifest.total_bytes > self.budget.max_bytes:
                raise ValueError("generation manifest exceeds the job budget")
        return self
