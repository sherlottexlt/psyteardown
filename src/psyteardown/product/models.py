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


class RevisionImpact(FrozenModel):
    dependent_type: Literal["problem_model", "outcome_contract", "product_thesis"]
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
    recorded_impacts: tuple[RevisionImpact, ...] = ()
