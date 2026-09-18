from datetime import datetime, timezone
from pathlib import Path

from psyteardown.experience import (
    EngineeringOrchestrator,
    EngineeringProjectRevision,
    EngineeringRequirement,
    RevisionMeta,
    SQLiteExperienceRepository,
    VerificationTestRun,
    build_engineering_traceability_report,
    dependency_ref,
    render_engineering_traceability_markdown,
)


NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def _requirement(revision: int = 1) -> EngineeringRequirement:
    return EngineeringRequirement(
        requirement_id="req-trace",
        revision_id=f"req-trace.r{revision}",
        meta=RevisionMeta(
            revision=revision,
            parent_revision_id=f"req-trace.r{revision - 1}" if revision > 1 else None,
            created_by="system-engineer",
            reason="reviewed requirement",
        ),
        status="approved",
        reviewer="system-engineer",
        reviewed_at=NOW,
        title="explicit cancellation",
        requirement_type="must",
        hard_constraint=True,
        source_type="user_declared",
        source_refs=("owner-interview",),
        acceptance_criteria=("instrumented task confirms cancellation",),
        verification_methods=("physical task test",),
    )


def test_traceability_report_links_requirement_to_reviewed_raw_test(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "trace.db") as repo:
        registry = EngineeringOrchestrator(repo)
        requirement = registry.register("requirement", _requirement())
        test = registry.register("verification_test", VerificationTestRun(
            test_run_id="test-trace",
            revision_id="test-trace.r1",
            meta=RevisionMeta(revision=1, created_by="test-lead", reason="physical test reviewed"),
            status="approved",
            reviewer="test-lead",
            reviewed_at=NOW,
            protocol_id="cancel-protocol.r1",
            test_type="physical task test",
            sample_ids=("prototype-1",),
            raw_measurement_refs=("measurements/cancel.csv#sha256:a",),
            result="pass",
            evidence_review_id="evidence-review-1.r1",
            dependencies=(dependency_ref("requirement", requirement.requirement_id, 1),),
        ))
        project = registry.register("project", EngineeringProjectRevision(
            project_id="project-trace",
            revision_id="project-trace.r1",
            meta=RevisionMeta(revision=1, created_by="system-engineer", reason="trace project"),
            intake_revision_id="intake-trace.r1",
            scenario="walking",
            product_purpose="bounded cancellation",
            requirement_revision_ids=(requirement.revision_id,),
            dependencies=(dependency_ref("requirement", requirement.requirement_id, 1),),
        ))

        report = build_engineering_traceability_report(repo, project.project_id)
        assert report.status == "traceable"
        trace = report.requirement_traces[0]
        assert trace.verification_test_revision_ids == (test.revision_id,)
        assert trace.evidence_review_ids == ("evidence-review-1.r1",)
        assert trace.issue_codes == ()
        assert "This projection reports traceability and gaps" in render_engineering_traceability_markdown(report)


def test_requirement_change_makes_report_blocked_and_preserves_old_trace(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "stale-trace.db") as repo:
        registry = EngineeringOrchestrator(repo)
        first = registry.register("requirement", _requirement())
        registry.register("verification_test", VerificationTestRun(
            test_run_id="test-stale",
            revision_id="test-stale.r1",
            meta=RevisionMeta(revision=1, created_by="test-lead", reason="old test"),
            status="approved",
            reviewer="test-lead",
            reviewed_at=NOW,
            protocol_id="old-protocol",
            test_type="physical",
            sample_ids=("prototype-1",),
            raw_measurement_refs=("old.csv#sha256:a",),
            result="pass",
            evidence_review_id="old-review.r1",
            dependencies=(dependency_ref("requirement", first.requirement_id, 1),),
        ))
        project = registry.register("project", EngineeringProjectRevision(
            project_id="project-stale",
            revision_id="project-stale.r1",
            meta=RevisionMeta(revision=1, created_by="system-engineer", reason="project"),
            intake_revision_id="intake.r1",
            scenario="walking",
            product_purpose="cancel",
            requirement_revision_ids=(first.revision_id,),
            dependencies=(dependency_ref("requirement", first.requirement_id, 1),),
        ))
        registry.register("requirement", _requirement(2))

        report = build_engineering_traceability_report(repo, project.project_id)
        assert report.status == "blocked"
        assert "requirement_revision_stale" in report.requirement_traces[0].issue_codes
        assert any(node.object_type == "verification_test_run" for node in report.stale_nodes)
