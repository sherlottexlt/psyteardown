from datetime import datetime, timezone
from pathlib import Path

import pytest

from psyteardown.experience import (
    BOMRevision,
    DFMReview,
    DVPRevision,
    DomainStateError,
    EngineeringOrchestrator,
    FMEARevision,
    FieldIssue,
    PilotBuildRun,
    QualityReleaseCoordinator,
    ReliabilityCertificationReview,
    RevisionMeta,
    SQLiteExperienceRepository,
    SupplierChangeRecord,
    VerificationTestRun,
    dependency_ref,
)


NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def _meta(reason: str, actor: str = "quality-lead") -> RevisionMeta:
    return RevisionMeta(revision=1, created_by=actor, reason=reason)


def _register_complete_gate_set(registry: EngineeringOrchestrator):
    fmea = registry.register("fmea", FMEARevision(
        fmea_id="fmea-1",
        revision_id="fmea-1.r1",
        meta=_meta("FMEA reviewed"),
        status="approved",
        reviewer="quality-lead",
        reviewed_at=NOW,
        failure_modes=({"mode": "seal leak", "severity": 8, "action": "seal test"},),
        mitigation_actions=("100% seal test",),
    ))
    verification = registry.register("verification_test", VerificationTestRun(
        test_run_id="verification-1",
        revision_id="verification-1.r1",
        meta=_meta("verification passed", "test-lead"),
        status="approved",
        reviewer="test-lead",
        reviewed_at=NOW,
        protocol_id="seal-and-cancel-dvpr",
        test_type="physical verification",
        sample_ids=("prototype-1",),
        raw_measurement_refs=("measurements/seal.csv#sha256:a",),
        result="pass",
        evidence_review_id="evidence-review-1.r1",
    ))
    dvp = registry.register("dvp", DVPRevision(
        dvp_id="dvp-1",
        revision_id="dvp-1.r1",
        meta=_meta("DVP&R complete", "test-lead"),
        status="approved",
        reviewer="test-lead",
        reviewed_at=NOW,
        requirement_ids=("req-seal",),
        critical_requirement_ids=("req-seal",),
        verification_test_run_ids=(verification.revision_id,),
        covered_requirement_ids=("req-seal",),
        passed_requirement_ids=("req-seal",),
        coverage="complete",
    ))
    bom = registry.register("bom", BOMRevision(
        bom_id="bom-1",
        revision_id="bom-1.r1",
        meta=_meta("BOM reviewed", "manufacturing-lead"),
        status="approved",
        reviewer="manufacturing-lead",
        reviewed_at=NOW,
        part_ids=("housing", "seal"),
    ))
    dfm = registry.register("dfm", DFMReview(
        review_id="dfm-1",
        revision_id="dfm-1.r1",
        meta=_meta("DFM reviewed", "manufacturing-lead"),
        status="approved",
        reviewer="manufacturing-lead",
        reviewed_at=NOW,
        recommendation="approved for controlled pilot build",
        dependencies=(dependency_ref("bom_revision", bom.bom_id, bom.meta.revision),),
    ))
    pilot = registry.register("pilot_build", PilotBuildRun(
        pilot_build_id="pilot-1",
        revision_id="pilot-1.r1",
        meta=_meta("pilot build reviewed", "manufacturing-lead"),
        status="approved",
        reviewer="manufacturing-lead",
        reviewed_at=NOW,
        bom_revision_id=bom.revision_id,
        build_lot="EVT-01",
        supplier_ids=("supplier-a",),
        units_started=100,
        units_completed=98,
        units_accepted=95,
        first_pass_yield=0.95,
        target_yield=0.90,
        raw_yield_refs=("pilot/evt-01-yield.csv#sha256:b",),
        result="completed",
        dependencies=(dependency_ref("bom_revision", bom.bom_id, bom.meta.revision),),
    ))
    compliance = registry.register("compliance_review", ReliabilityCertificationReview(
        review_id="compliance-1",
        revision_id="compliance-1.r1",
        meta=_meta("compliance evidence reviewed", "regulatory-lead"),
        status="approved",
        reviewer="regulatory-lead",
        reviewed_at=NOW,
        target_markets=("CN",),
        applicable_standards=("declared applicable standard",),
        reliability_test_revision_ids=(verification.revision_id,),
        certification_evidence_refs=("lab-report-1#sha256:c",),
        decision="approved",
    ))
    return fmea, verification, dvp, bom, dfm, pilot, compliance


def test_complete_human_reviewed_gates_can_create_release(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "release.db") as repo:
        registry = EngineeringOrchestrator(repo)
        objects = _register_complete_gate_set(registry)
        refs = tuple(
            dependency_ref(object_type, item.id, item.meta.revision)
            for object_type, item in zip(
                ("fmea", "verification_test", "dvp", "bom", "dfm", "pilot_build", "compliance_review"),
                objects,
            )
        )
        quality = QualityReleaseCoordinator(repo)
        readiness = quality.assess_manufacturing_readiness(
            review_id="mrr-1",
            gate_refs=refs,
            reviewer="manufacturing-director",
            cost_reviewed=True,
            supplier_ids=("supplier-a",),
            quality_plan_refs=("quality-plan.r1",),
        )
        assert readiness.readiness == "ready"
        release = quality.decide_release(
            readiness,
            decision_id="release-1",
            decision="approved",
            release_scope=("controlled CN release",),
            effective_refs=(
                dependency_ref("bom", objects[3].bom_id, objects[3].meta.revision),
                dependency_ref("dvp", objects[2].dvp_id, objects[2].meta.revision),
                dependency_ref("compliance_review", objects[6].review_id, objects[6].meta.revision),
            ),
            approver="product-quality-director",
            rationale="all declared gates are human-reviewed and current",
        )
        assert release.decision == "approved"
        assert release.blocking_items == ()


def test_missing_compliance_blocks_approved_and_conditional_release(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "blocked-release.db") as repo:
        registry = EngineeringOrchestrator(repo)
        objects = _register_complete_gate_set(registry)
        refs = tuple(
            dependency_ref(object_type, item.id, item.meta.revision)
            for object_type, item in zip(
                ("fmea", "verification_test", "dvp", "bom", "dfm", "pilot_build"),
                objects[:-1],
            )
        )
        quality = QualityReleaseCoordinator(repo)
        readiness = quality.assess_manufacturing_readiness(
            review_id="mrr-blocked",
            gate_refs=refs,
            reviewer="manufacturing-director",
            cost_reviewed=True,
        )
        assert "compliance_not_approved" in readiness.blocking_items
        with pytest.raises(DomainStateError, match="cannot bypass"):
            quality.decide_release(
                readiness,
                decision_id="release-conditional",
                decision="conditional",
                release_scope=("trial",),
                effective_refs=(dependency_ref("bom", objects[3].bom_id, objects[3].meta.revision),),
                approver="product-quality-director",
                rationale="attempted conditional release",
                conditions=("obtain compliance later",),
            )


def test_supplier_change_and_field_issue_invalidate_affected_chain(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "change.db") as repo:
        registry = EngineeringOrchestrator(repo)
        objects = _register_complete_gate_set(registry)
        verification, bom = objects[1], objects[3]
        quality = QualityReleaseCoordinator(repo)
        supplier_change = SupplierChangeRecord(
            change_id="supplier-change-1",
            revision_id="supplier-change-1.r1",
            meta=_meta("supplier material change", "sourcing-lead"),
            status="approved",
            reviewer="sourcing-lead",
            reviewed_at=NOW,
            supplier_id="supplier-a",
            part_id="seal",
            previous_spec="seal-material-a",
            proposed_spec="seal-material-b",
            affected_objects=(dependency_ref("bom", bom.bom_id, bom.meta.revision),),
            qualification_test_revision_ids=(verification.revision_id,),
            decision="approved",
        )
        _, invalidated = quality.register_supplier_change(supplier_change)
        invalidated_types = {type(item).__name__ for item in invalidated}
        assert "BOMRevision" in invalidated_types
        assert "DFMReview" in invalidated_types
        assert "PilotBuildRun" in invalidated_types

        field_issue = FieldIssue(
            issue_id="field-issue-1",
            revision_id="field-issue-1.r1",
            meta=_meta("critical field issue", "service-quality-lead"),
            severity="critical",
            description="unexpected seal failure",
            evidence_refs=("returned-unit-report-1",),
            affected_objects=(dependency_ref("verification_test", verification.test_run_id, verification.meta.revision),),
        )
        _, issue_invalidated = quality.record_field_issue(field_issue)
        assert any(item.status == "invalidated" for item in issue_invalidated)
