from pathlib import Path

import pytest

from psyteardown.experience import (
    AnalysisFamily,
    ArbitrationRevision,
    CanaryRevision,
    DependencyRef,
    ExperimentPlan,
    GrantRevocationRevision,
    ReleaseScopeGrant,
    RevisionMeta,
    SQLiteExperienceRepository,
    amend_preregistration,
    assess_independence,
    build_dependency_graph,
    classify_canary_failure,
    critical_path_coverage,
    merge_release_grants,
    revoke_grant,
    start_experiment,
    create_job_snapshot,
    commit_job_result,
    build_outbox_event,
    DomainEvent,
)


def meta(reason: str = "test", revision: int = 1, parent: str | None = None) -> RevisionMeta:
    return RevisionMeta(revision=revision, parent_revision_id=parent, created_by="test", reason=reason)


def plan(status: str = "draft") -> ExperimentPlan:
    return ExperimentPlan(
        experiment_id="exp-1", revision_id="exp-1.r1", meta=meta(),
        brief_revision_id="brief.r1", hypothesis_binding_ids=("binding.r1",), status=status,
    )


def test_content_hash_is_stable_and_distinct_for_revision_payload():
    assert plan().content_hash == plan().content_hash
    assert plan().content_hash != plan().model_copy(update={"brief_revision_id": "brief.r2"}).content_hash
    assert plan().revision_number == 1


def test_preregistration_amendment_before_start_creates_new_revision():
    updated, amendment = amend_preregistration(plan("preregistered"), changed_fields=["sample", "sample"], reason="power update", approved_by="method")
    assert updated.meta.revision == 2
    assert amendment.changed_fields == ("sample",)
    with pytest.raises(ValueError):
        amend_preregistration(plan("started"), changed_fields=["sample"], reason="late", approved_by="method")


def test_start_requires_approved_plan_and_pins_irreversible_event():
    started, event = start_experiment(plan("approved"), trigger="formal_data_written")
    assert started.status == "started"
    assert started.start_event_id == event.revision_id
    with pytest.raises(ValueError):
        start_experiment(plan("draft"), trigger="formal_data_written")


def test_dependency_graph_rejects_cycles_and_requires_coverage_when_closed():
    a = DependencyRef(object_type="candidate", object_id="a", revision=1)
    b = DependencyRef(object_type="review", object_id="b", revision=1)
    graph = build_dependency_graph(graph_id="g", nodes=[a, b], edges=[("candidate:a:1", "review:b:1")], field_coverage=["candidate"])
    assert graph.status == "closed"
    with pytest.raises(ValueError):
        build_dependency_graph(graph_id="cycle", nodes=[a, b], edges=[("candidate:a:1", "review:b:1"), ("review:b:1", "candidate:a:1")], field_coverage=["candidate"])


def test_independence_is_field_closed_and_shared_dependencies_are_limited():
    independent = assess_independence(subject_id="run-2", source_ids=["run-2"], critical_fields=["participants", "analysis"], covered_fields=["participants", "analysis"])
    assert independent.status == "independent"
    limited = assess_independence(subject_id="run-3", source_ids=["run-3"], critical_fields=["participants"], covered_fields=["participants"], shared_dependencies=["recruitment"])
    assert limited.status == "correlated_evidence_dependency"


def test_canary_uncertain_failure_cannot_be_replaced_or_counted():
    canary = CanaryRevision(
        canary_id="canary-1", revision_id="canary-1.r1", meta=meta(), compatibility_revision_id="compat.r1",
        path_id="normal", criticality="critical", steward_id="steward",
    )
    classified = classify_canary_failure(canary, classification="timeout", technical_failure=True)
    assert classified.status == "canary_failure_classification_uncertain"
    assert critical_path_coverage([classified], ["normal"]) == ("normal",)


def test_release_grant_conflict_defaults_to_conflict_and_revocation_fail_closed():
    first = ReleaseScopeGrant(grant_id="grant-1", revision_id="grant-1.r1", meta=meta(), allowed_paths=("path",))
    second = ReleaseScopeGrant(grant_id="grant-2", revision_id="grant-2.r1", meta=meta(), allowed_paths=("path",))
    merged = merge_release_grants([first, second])
    assert merged[0].status == "grant_conflict"
    pending = revoke_grant(first, inventory_node_ids=["node-a", "node-b"], receipts=["node-a"])
    assert pending.status == "grant_revocation_pending"
    converged = revoke_grant(first, inventory_node_ids=["node-a"], receipts=["node-a"], usage_log_refs=["usage-1"])
    assert converged.status == "converged"


def test_governance_records_round_trip_in_sqlite(tmp_path: Path):
    grant = ReleaseScopeGrant(grant_id="grant-db", revision_id="grant-db.r1", meta=meta(), allowed_paths=("p",))
    with SQLiteExperienceRepository(tmp_path / "exp.sqlite") as repo:
        repo.save("release_grant", grant.grant_id, grant.revision_id, grant)
        assert repo.get_revision("release_grant", grant.revision_id) == grant


def test_job_snapshot_pins_revision_and_stale_result_is_preserved():
    call, job = create_job_snapshot(
        job_id="job-1", kind="review", provider="fake", model="m1",
        target_object_type="candidate", target_object_id="c1", target_revision_id="c1.r3",
    )
    assert job.expected_revision == 3
    assert call.fingerprint
    stale = commit_job_result(job, actual_revision=4, payload={"answer": "draft"})
    assert stale.status == "stale_result"
    fresh = commit_job_result(job, actual_revision=3, payload={}, result_revision_id="review.r1")
    assert fresh.status == "succeeded"


def test_outbox_is_idempotent_and_tracks_delivery_state(tmp_path: Path):
    domain = DomainEvent(event_id="event-1", event_type="ReviewRequested", aggregate_id="review-1", aggregate_revision_id="review-1.r1")
    event = build_outbox_event(domain)
    with SQLiteExperienceRepository(tmp_path / "outbox.sqlite") as repo:
        assert repo.enqueue_outbox(event) == event
        assert repo.enqueue_outbox(event) == event
        assert repo.pending_outbox() == [event]
        delivered = event.model_copy(update={"status": "delivered", "attempts": 1})
        repo.update_outbox(delivered)
        assert repo.pending_outbox() == []


def test_job_snapshot_pins_target_revision_and_stale_result_is_retained():
    call, job = create_job_snapshot(
        job_id="job-1", kind="review", provider="fake", model="v1",
        target_object_type="candidate", target_object_id="cand-1",
        target_revision_id="cand-1.r3", input_hashes=[("prompt", "hash-a")],
    )
    assert job.expected_revision == 3
    _, changed_job = create_job_snapshot(
        job_id="job-2", kind="review", provider="fake", model="v1",
        target_object_type="candidate", target_object_id="cand-1",
        target_revision_id="cand-1.r3", input_hashes=[("prompt", "hash-b")],
    )
    assert call.fingerprint != changed_job.fingerprint
    stale = commit_job_result(job, actual_revision=4, payload={"draft": "x"})
    assert stale.status == "stale_result"
