"""P4 manufacturing, compliance, change-control and release gates."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from psyteardown.experience.engineering import (
    BOMRevision,
    DFMReview,
    DVPRevision,
    EngineeringChangeOrder,
    EngineeringOrchestrator,
    EngineeringRecord,
    FMEARevision,
    FieldIssue,
    ManufacturingReadinessReview,
    PilotBuildRun,
    ReleaseDecision,
    ReliabilityCertificationReview,
    SupplierChangeRecord,
    VerificationTestRun,
    canonical_object_type,
)
from psyteardown.experience.models import DependencyRef, DomainStateError, RevisionMeta
from psyteardown.experience.multimodal import is_named_human_actor


_HARD_BLOCK_CODES = (
    "safety_", "regulatory_", "critical_", "verification_", "compliance_",
    "fmea_", "dvp_", "pilot_yield_",
)


class QualityReleaseCoordinator:
    """Deterministic gate checks; all approvals remain named human actions."""

    def __init__(self, repository: Any, *, actor: str = "ai-quality-orchestrator") -> None:
        self.repository = repository
        self.registry = EngineeringOrchestrator(repository, actor=actor)
        self.actor = actor

    def _resolve(self, reference: DependencyRef) -> EngineeringRecord:
        object_type = canonical_object_type(reference.object_type)
        current = self.repository.get_current(object_type, reference.object_id)
        if current is None:
            raise DomainStateError(f"quality gate reference is unavailable: {object_type}:{reference.object_id}")
        if current.meta.revision != reference.revision:
            raise DomainStateError(f"quality gate reference is stale: {object_type}:{reference.object_id}")
        return current

    def assess_manufacturing_readiness(
        self,
        *,
        review_id: str,
        gate_refs: Iterable[DependencyRef],
        reviewer: str,
        cost_reviewed: bool,
        supplier_ids: Iterable[str] = (),
        quality_plan_refs: Iterable[str] = (),
        capacity_assumptions: Iterable[str] = (),
        rationale: str = "manufacturing readiness reviewed",
    ) -> ManufacturingReadinessReview:
        references = tuple(gate_refs)
        resolved = tuple((ref, self._resolve(ref)) for ref in references)
        by_type: dict[type[Any], list[EngineeringRecord]] = {}
        for _, item in resolved:
            by_type.setdefault(type(item), []).append(item)
        blockers: list[str] = []
        conditions: list[str] = []

        fmeas = by_type.get(FMEARevision, [])
        if not fmeas or any(item.status != "approved" or not item.reviewer for item in fmeas):
            blockers.append("fmea_not_approved")
        dvps = by_type.get(DVPRevision, [])
        if not dvps or any(item.status != "approved" or item.coverage != "complete" for item in dvps):
            blockers.append("dvp_not_complete")
        tests = by_type.get(VerificationTestRun, [])
        if not tests:
            blockers.append("verification_tests_missing")
        elif any(item.status != "approved" or item.result != "pass" or not item.evidence_review_id for item in tests):
            blockers.append("verification_tests_not_passed")
        dfm_reviews = by_type.get(DFMReview, [])
        if not dfm_reviews or any(item.status != "approved" or not item.reviewer for item in dfm_reviews):
            blockers.append("dfm_not_approved")
        boms = by_type.get(BOMRevision, [])
        if not boms or any(item.status != "approved" or not item.part_ids for item in boms):
            blockers.append("bom_not_approved")
        pilot_builds = by_type.get(PilotBuildRun, [])
        if not pilot_builds or any(item.result != "completed" or item.status != "approved" for item in pilot_builds):
            blockers.append("pilot_build_not_approved")
        else:
            for item in pilot_builds:
                if item.target_yield is None:
                    conditions.append("pilot_yield_target_not_declared")
                elif item.first_pass_yield is None or item.first_pass_yield < item.target_yield:
                    blockers.append("pilot_yield_below_target")
        compliance = by_type.get(ReliabilityCertificationReview, [])
        if not compliance or any(item.decision != "approved" or item.status != "approved" for item in compliance):
            blockers.append("compliance_not_approved")
        if not cost_reviewed:
            blockers.append("cost_not_reviewed")

        human = is_named_human_actor(reviewer)
        if not human:
            raise DomainStateError("manufacturing readiness requires a named human reviewer")
        readiness = "ready" if not blockers and not conditions else ("blocked" if blockers else "conditional")
        pilot = pilot_builds[0] if pilot_builds else None
        review = ManufacturingReadinessReview(
            review_id=review_id,
            revision_id=f"{review_id}.r1",
            meta=RevisionMeta(revision=1, created_by=reviewer, reason=rationale),
            dependencies=references,
            status="approved" if readiness == "ready" else ("blocked" if blockers else "conditional"),
            reviewer=reviewer,
            reviewed_at=datetime.now(timezone.utc),
            pilot_build=pilot.revision_id if pilot else "not available",
            supplier_ids=tuple(supplier_ids),
            yield_data_refs=pilot.raw_yield_refs if pilot else (),
            quality_plan_refs=tuple(quality_plan_refs),
            capacity_assumptions=tuple(capacity_assumptions),
            cost_reviewed=cost_reviewed,
            readiness=readiness,
            blocking_items=tuple(dict.fromkeys(blockers)),
            conditional_items=tuple(dict.fromkeys(conditions)),
            gate_revision_ids=tuple(item.revision_id for _, item in resolved),
        )
        return self.registry.register("manufacturing_readiness_review", review)

    def decide_release(
        self,
        readiness: ManufacturingReadinessReview,
        *,
        decision_id: str,
        decision: str,
        release_scope: Iterable[str],
        effective_refs: Iterable[DependencyRef],
        approver: str,
        rationale: str,
        remaining_risks: Iterable[str] = (),
        conditions: Iterable[str] = (),
    ) -> ReleaseDecision:
        if decision not in {"approved", "conditional", "blocked", "rejected"}:
            raise DomainStateError("release decision is invalid")
        if not is_named_human_actor(approver):
            raise DomainStateError("release gate requires a named human approver")
        release_scope = tuple(release_scope)
        remaining_risks = tuple(remaining_risks)
        conditions = tuple(conditions)
        current_readiness = self.repository.get_current("manufacturing_readiness_review", readiness.review_id)
        if current_readiness is None or current_readiness.revision_id != readiness.revision_id:
            raise DomainStateError("manufacturing readiness revision is stale")
        effective = tuple(effective_refs)
        effective_objects = tuple(self._resolve(ref) for ref in effective)
        blockers = list(readiness.blocking_items)
        if readiness.readiness != "ready":
            blockers.append(f"manufacturing_readiness_{readiness.readiness}")
        if any(item.status in {"stale", "invalidated", "blocked", "rejected"} for item in effective_objects):
            blockers.append("effective_revision_not_current")
        hard_blocked = any(code.startswith(_HARD_BLOCK_CODES) for code in blockers)
        if decision == "approved" and blockers:
            raise DomainStateError("release cannot be approved while gate blockers remain")
        if decision == "conditional" and hard_blocked:
            raise DomainStateError("conditional release cannot bypass safety, regulatory or critical verification blockers")
        if decision == "conditional" and not conditions:
            raise DomainStateError("conditional release requires explicit conditions")
        release = ReleaseDecision(
            decision_id=decision_id,
            revision_id=f"{decision_id}.r1",
            meta=RevisionMeta(revision=1, created_by=approver, reason=rationale),
            dependencies=(
                DependencyRef(
                    object_type="manufacturing_readiness_review",
                    object_id=readiness.review_id,
                    revision=readiness.meta.revision,
                ),
                *effective,
            ),
            status=decision,
            reviewer=approver,
            reviewed_at=datetime.now(timezone.utc),
            release_scope=release_scope,
            blocking_items=tuple(dict.fromkeys(blockers)),
            effective_revision_ids=tuple(item.revision_id for item in effective_objects),
            approver=approver,
            decision=decision,
            rationale=rationale,
            remaining_risks=remaining_risks,
            conditions=conditions,
            gate_revision_ids=(readiness.revision_id, *readiness.gate_revision_ids),
        )
        return self.registry.register("release_decision", release)

    def register_change_order(self, change: EngineeringChangeOrder) -> tuple[EngineeringChangeOrder, tuple[EngineeringRecord, ...]]:
        if change.approval == "approved" and not is_named_human_actor(change.reviewer or ""):
            raise DomainStateError("approved engineering change requires a named human reviewer")
        persisted = self.registry.register("engineering_change_order", change)
        invalidated = ()
        if change.approval == "approved":
            invalidated = self.registry.invalidate_objects(
                change.affected_objects,
                reason=f"approved engineering change {change.change_order_id}",
                actor=change.reviewer,
            )
        return persisted, invalidated

    def register_supplier_change(self, change: SupplierChangeRecord) -> tuple[SupplierChangeRecord, tuple[EngineeringRecord, ...]]:
        if change.decision == "approved" and not is_named_human_actor(change.reviewer or ""):
            raise DomainStateError("approved supplier change requires a named human reviewer")
        if change.decision == "approved":
            qualification_tests = tuple(
                self.repository.get_revision("verification_test_run", revision_id)
                for revision_id in change.qualification_test_revision_ids
            )
            if any(
                item is None or item.result != "pass" or item.status != "approved"
                for item in qualification_tests
            ):
                raise DomainStateError("supplier change qualification tests must be approved and passing")
        persisted = self.registry.register("supplier_change", change)
        invalidated = ()
        if change.decision == "approved":
            invalidated = self.registry.invalidate_objects(
                change.affected_objects,
                reason=f"approved supplier change {change.change_id}",
                actor=change.reviewer,
            )
        return persisted, invalidated

    def record_field_issue(self, issue: FieldIssue) -> tuple[FieldIssue, tuple[EngineeringRecord, ...]]:
        persisted = self.registry.register("field_issue", issue)
        invalidated = ()
        if issue.severity in {"critical", "major"} and issue.affected_objects:
            invalidated = self.registry.invalidate_objects(
                issue.affected_objects,
                reason=f"{issue.severity} field issue {issue.issue_id}",
                invalidated=issue.severity == "critical",
                actor=issue.meta.created_by,
            )
        return persisted, invalidated


__all__ = ["QualityReleaseCoordinator"]
