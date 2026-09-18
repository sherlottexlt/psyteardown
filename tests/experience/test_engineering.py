from pathlib import Path

import pytest

from psyteardown.experience import (
    BOMRevision,
    CADArtifact,
    DomainStateError,
    EngineeringOrchestrator,
    EngineeringRequirement,
    EngineeringTask,
    RevisionMeta,
    SQLiteExperienceRepository,
    dependency_ref,
)
from psyteardown.experience.repositories import InMemoryExperienceRepository


def requirement(revision: int = 1) -> EngineeringRequirement:
    return EngineeringRequirement(
        requirement_id="req-1",
        revision_id=f"req-1.r{revision}",
        meta=RevisionMeta(
            revision=revision,
            parent_revision_id=f"req-1.r{revision - 1}" if revision > 1 else None,
            created_by="system-engineer",
            reason="declared requirement",
        ),
        title="maintain bounded cancellation",
        requirement_type="must",
        acceptance_criteria=("cancel completes within 500 ms",),
        verification_methods=("verification_test",),
    )


def test_dependency_graph_and_transitive_stale_propagation():
    repo = InMemoryExperienceRepository()
    orchestrator = EngineeringOrchestrator(repo)
    orchestrator.register("requirement", requirement())
    cad = CADArtifact(
        artifact_id="cad-1",
        revision_id="cad-1.r1",
        meta=RevisionMeta(revision=1, created_by="industrial-design", reason="cad draft"),
        dependencies=(dependency_ref("engineering_requirement", "req-1", 1),),
    )
    orchestrator.register("cad", cad)
    bom = BOMRevision(
        bom_id="bom-1",
        revision_id="bom-1.r1",
        meta=RevisionMeta(revision=1, created_by="dfm", reason="bom draft"),
        dependencies=(dependency_ref("cad_artifact", "cad-1", 1),),
    )
    orchestrator.register("bom", bom)

    assert orchestrator.build_dependency_graph().status == "closed"
    orchestrator.register("requirement", requirement(2))
    stale = orchestrator.propagate_invalidation(dependency_ref("engineering_requirement", "req-1", 2))

    assert {item.revision_id for item in stale} == {"cad-1.r2", "bom-1.r2"}
    assert all(item.status == "stale" for item in stale)
    assert {item.revision_id for item in orchestrator.stale_objects()} == {"cad-1.r2", "bom-1.r2"}


def test_ai_cannot_complete_human_gate_and_human_can_approve():
    orchestrator = EngineeringOrchestrator(InMemoryExperienceRepository())
    task = orchestrator.create_task(
        task_id="release-review",
        role="quality",
        action="review release evidence",
        human_gate_required=True,
    )
    with pytest.raises(DomainStateError):
        orchestrator.update_task(task, status="completed")
    completed = orchestrator.update_task(task, status="completed", actor="quality-lead")
    assert completed.task_status == "completed"
    gate = orchestrator.approve_gate(
        target_object_type="release_decision",
        target_object_id="release-1",
        target_revision_id="release-1.r1",
        from_stage="manufacturing_ready",
        to_stage="released",
        reviewer="quality-lead",
        evidence_refs=("test-run-1.r1",),
        rationale="named reviewer accepted the evidence boundary",
    )
    assert gate.status == "approved"


def test_engineering_objects_round_trip_in_sqlite(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "engineering.db") as repo:
        orchestrator = EngineeringOrchestrator(repo)
        orchestrator.register("engineering_requirement", requirement())
        restored = repo.get_current("engineering_requirement", "req-1")
        assert restored is not None
        assert restored.acceptance_criteria == ("cancel completes within 500 ms",)


def test_engineering_registration_and_stale_propagation_are_audited(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "engineering-audit.db") as repo:
        orchestrator = EngineeringOrchestrator(repo)
        orchestrator.register("requirement", requirement())
        cad = CADArtifact(
            artifact_id="cad-audit",
            revision_id="cad-audit.r1",
            meta=RevisionMeta(revision=1, created_by="cad-engineer", reason="CAD created"),
            dependencies=(dependency_ref("requirement", "req-1", 1),),
        )
        orchestrator.register("cad", cad)
        orchestrator.register("requirement", requirement(2))

        assert any(
            event.event_type == "EngineeringObjectStale"
            and event.aggregate_id == cad.artifact_id
            for event in repo.domain_events
        )
        stale_cad = repo.get_current("cad_artifact", cad.artifact_id)
        assert stale_cad.status == "stale"
        audit = next(
            event for event in repo.audit_events
            if event.target_revision_id == stale_cad.revision_id
        )
        assert audit.action == "EngineeringObjectStale"
        assert audit.actor == "ai-orchestrator"
