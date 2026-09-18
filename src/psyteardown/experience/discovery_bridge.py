"""Two-stage bridge from App teardown to cross-device engineering discovery.

The original teardown pipeline analyzes App/digital-service experiences. Its
output first becomes ``DigitalExperienceDiscovery``. A named human then routes
every signal. Only signals explicitly routed as device-interaction candidates
may be projected into a draft ``EngineeringIntake``; no teardown finding
directly becomes a mechanical, material, manufacturing or compliance
requirement.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

from psyteardown.pipeline.schemas import TeardownResult

from psyteardown.experience.engineering import (
    DigitalExperienceDiscovery,
    DigitalExperienceSignal,
    DiscoveryTriageDecision,
    EngineeringIntake,
    EngineeringOrchestrator,
)
from psyteardown.experience.models import DependencyRef, DomainStateError, RevisionMeta
from psyteardown.experience.multimodal import is_named_human_actor


def teardown_source_ref(result: TeardownResult, *, source_ref: str | None = None) -> str:
    """Return a stable provenance ref for one immutable teardown payload."""
    if source_ref:
        return source_ref
    digest = hashlib.sha256(result.model_dump_json().encode("utf-8")).hexdigest()[:16]
    return f"teardown-result:{digest}"


class DigitalExperienceDiscoveryCoordinator:
    """Import, triage and safely project App teardown discoveries."""

    def __init__(self, repository: Any, *, actor: str = "ai-discovery-bridge") -> None:
        self.repository = repository
        self.registry = EngineeringOrchestrator(repository, actor=actor)
        self.actor = actor

    def import_teardown(
        self,
        result: TeardownResult,
        *,
        discovery_id: str,
        source_ref: str | None = None,
    ) -> DigitalExperienceDiscovery:
        if not discovery_id.strip():
            raise ValueError("discovery_id must not be empty")
        if self.repository.get_current("digital_experience_discovery", discovery_id) is not None:
            raise DomainStateError("digital experience discovery already exists")
        source = teardown_source_ref(result, source_ref=source_ref)
        quality = (
            "grounded" if result.grounding.dropped == 0 and result.grounding.kept > 0
            else "partial" if result.grounding.kept > 0
            else "unreliable"
        )
        groups = (
            ("friction", result.assessment.friction_points),
            ("ethics", result.assessment.ethics_warnings),
            ("opportunity", result.assessment.opportunities),
        )
        signals = tuple(
            DigitalExperienceSignal(
                signal_id=f"{discovery_id}:{signal_type}:{index}",
                signal_type=signal_type,
                statement=statement,
                source_refs=(source,),
            )
            for signal_type, statements in groups
            for index, statement in enumerate(statements, start=1)
        )
        mechanisms = tuple(
            f"{mapping.feature}: {mapping.framework_id}.{mapping.principle_id} — {mapping.rationale}"
            for mapping in result.mappings
            if not mapping.error and mapping.framework_id and mapping.principle_id
        )
        discovery = DigitalExperienceDiscovery(
            discovery_id=discovery_id,
            revision_id=f"{discovery_id}.r1",
            meta=RevisionMeta(
                revision=1,
                created_by=self.actor,
                reason="App teardown imported for digital-experience triage",
            ),
            status="draft",
            product_name=result.product.name,
            product_type=result.product.product_type,
            product_summary=result.product.one_liner,
            app_features=tuple(feature.name for feature in result.product.features),
            user_goals=tuple(feature.user_goal for feature in result.product.features),
            digital_touchpoints=tuple(result.product.touchpoints),
            signals=signals,
            mechanism_hypotheses=mechanisms,
            grounding_quality=quality,
            triage_status="pending",
            source_refs=(
                source,
                f"teardown-model:{result.meta.model}",
                f"teardown-generated:{result.meta.generated_at}",
            ),
            assumptions=(
                "The source pipeline analyzes App/digital-service experience.",
                "Mechanism mappings and assessment items are hypotheses, not observed outcomes.",
            ),
            unknowns=(
                "No signal is known to apply to a device or physical product before human triage.",
                "The teardown supplies no physical dimensions, loads, materials, reliability or manufacturing evidence.",
            ),
        )
        return self.registry.register("digital_experience_discovery", discovery)

    def triage(
        self,
        discovery: DigitalExperienceDiscovery,
        *,
        decisions: Iterable[DiscoveryTriageDecision],
        reviewer: str,
        rationale: str,
    ) -> DigitalExperienceDiscovery:
        if not is_named_human_actor(reviewer):
            raise DomainStateError("digital experience triage requires a named human reviewer")
        current = self.repository.get_current("digital_experience_discovery", discovery.discovery_id)
        if current is None or current.revision_id != discovery.revision_id:
            raise DomainStateError("digital experience discovery revision is stale")
        decisions = tuple(decisions)
        signal_ids = {item.signal_id for item in current.signals}
        decision_ids = {item.signal_id for item in decisions}
        if decision_ids != signal_ids or len(decisions) != len(signal_ids):
            missing = sorted(signal_ids - decision_ids)
            unknown = sorted(decision_ids - signal_ids)
            raise DomainStateError(
                "triage must route every discovery signal exactly once: "
                f"missing={missing}, unknown={unknown}"
            )
        revision = current.meta.revision + 1
        reviewed = current.model_copy(update={
            "revision_id": f"{current.discovery_id}.r{revision}",
            "meta": RevisionMeta(
                revision=revision,
                parent_revision_id=current.revision_id,
                created_by=reviewer,
                reason=rationale,
            ),
            "status": "current",
            "reviewer": reviewer,
            "reviewed_at": datetime.now(timezone.utc),
            "triage_status": "complete",
            "triage_decisions": decisions,
        })
        return self.registry.register("digital_experience_discovery", reviewed)

    def build_engineering_intake(
        self,
        discovery: DigitalExperienceDiscovery,
        *,
        project_id: str,
        scenario: str,
        target_segment: str,
        intake_id: str | None = None,
    ) -> EngineeringIntake:
        """Project only human-routed device candidates into a draft intake."""
        current = self.repository.get_current("digital_experience_discovery", discovery.discovery_id)
        if current is None or current.revision_id != discovery.revision_id:
            raise DomainStateError("digital experience discovery revision is stale")
        if current.triage_status != "complete" or not current.reviewer or current.reviewed_at is None:
            raise DomainStateError("engineering intake requires complete named-human discovery triage")
        candidates = tuple(
            decision.candidate_statement
            for decision in current.triage_decisions
            if decision.disposition == "device_interaction_candidate"
            and decision.candidate_statement
        )
        if not candidates:
            raise DomainStateError("discovery has no human-routed device interaction candidates")
        if not project_id.strip() or not scenario.strip() or not target_segment.strip():
            raise DomainStateError("engineering projection requires project, scenario and target segment")
        intake_key = intake_id or f"{project_id}-discovery-intake"
        validation_questions = tuple(
            decision.validation_question
            for decision in current.triage_decisions
            if decision.disposition == "device_interaction_candidate"
            and decision.validation_question
        )
        return EngineeringIntake(
            intake_id=intake_key,
            project_id=project_id,
            revision_id=f"{intake_key}.r1",
            meta=RevisionMeta(
                revision=1,
                created_by=current.reviewer,
                reason="human-triaged digital discovery projected to engineering intake",
            ),
            dependencies=(DependencyRef(
                object_type="digital_experience_discovery",
                object_id=current.discovery_id,
                revision=current.meta.revision,
            ),),
            status="draft",
            scenario=scenario,
            product_purpose=current.product_summary,
            target_segment=target_segment,
            discovery_revision_id=current.revision_id,
            discovery_source_refs=current.source_refs,
            discovery_quality=current.grounding_quality,
            behavioral_mechanisms=current.mechanism_hypotheses,
            device_interaction_candidates=candidates,
            discovery_assumptions=(
                "Only signals explicitly routed by the named reviewer are projected.",
                "Candidates still require system-engineering review before becoming requirements.",
            ),
            discovery_unknowns=validation_questions,
            source_refs=current.source_refs,
            assumptions=(
                "This is a cross-device interaction intake, not a mechanical or manufacturing conclusion.",
            ),
            unknowns=validation_questions,
        )


__all__ = ["DigitalExperienceDiscoveryCoordinator", "teardown_source_ref"]


def build_engineering_intake_from_teardown(
    result: TeardownResult,
    *,
    project_id: str,
    intake_id: str | None = None,
    scenario: str | None = None,
    target_segment: str | None = None,
    created_by: str = "ai-discovery-bridge",
    source_ref: str | None = None,
) -> EngineeringIntake:
    """Deprecated compatibility adapter for the pre-triage API.

    New code should use ``import_teardown`` → ``triage`` →
    ``build_engineering_intake``. This adapter is retained so existing scripts
    can migrate without breaking, and marks the resulting intake explicitly as
    ``legacy_direct_discovery``.
    """
    source = teardown_source_ref(result, source_ref=source_ref)
    assessment = result.assessment
    quality = (
        "grounded" if result.grounding.dropped == 0 and result.grounding.kept > 0
        else "partial" if result.grounding.kept > 0 else "unreliable"
    )
    scenario_value = (scenario or "").strip() or "scenario not declared; requires human confirmation"
    segment_value = (target_segment or "").strip() or "target segment not declared; requires human confirmation"
    unknowns = (
        "Legacy direct bridge retained only for migration; use discovery triage for new work.",
        "Teardown findings are hypotheses and have not been confirmed by users or engineering tests.",
    )
    mechanisms = tuple(
        f"{mapping.feature}: {mapping.framework_id}.{mapping.principle_id} — {mapping.rationale}"
        for mapping in result.mappings
        if not mapping.error and mapping.framework_id and mapping.principle_id
    )
    key = intake_id or f"{project_id}-discovery-intake"
    return EngineeringIntake(
        intake_id=key,
        project_id=project_id,
        revision_id=f"{key}.r1",
        meta=RevisionMeta(revision=1, created_by=created_by, reason="deprecated direct teardown bridge"),
        status="draft",
        scenario=scenario_value,
        product_purpose=result.product.one_liner,
        target_segment=segment_value,
        business_goals=tuple(assessment.opportunities),
        discovery_revision_id=f"{source}.r1",
        discovery_source_refs=(source, f"teardown-model:{result.meta.model}"),
        discovery_quality=quality,
        experience_risks=tuple(assessment.friction_points),
        ethics_risks=tuple(assessment.ethics_warnings),
        experience_opportunities=tuple(assessment.opportunities),
        behavioral_mechanisms=mechanisms,
        discovery_unknowns=unknowns,
        source_refs=(source,),
        assumptions=("Deprecated compatibility path; no physical engineering conclusion is implied.",),
        unknowns=unknowns,
        legacy_direct_discovery=True,
    )


__all__.append("build_engineering_intake_from_teardown")
