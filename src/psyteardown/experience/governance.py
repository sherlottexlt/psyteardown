"""Deterministic guards for experiment and trust-boundary revisions.

The functions here are intentionally side-effect free.  Application services
can persist the returned immutable records in one command transaction; callers
must never mutate an existing revision or infer a qualification conclusion
from a convenience status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Iterable
from uuid import uuid4
import hashlib
import json

from .models import (
    AnalysisFamily,
    ArbitrationRevision,
    CanaryRevision,
    DependencyGraphRevision,
    DependencyRef,
    ExperimentPlan,
    ExperimentStartEvent,
    GrantRevocationRevision,
    IndependenceAssessment,
    PreregistrationAmendment,
    ProtocolDeviation,
    ReleaseScopeGrant,
    SuspensionRevision,
    RevisionMeta,
    ExternalCallSnapshot,
    JobRecord,
    StaleJobResult,
    OutboxEvent,
    DomainEvent,
    EventLogRecord,
)


# Fields that can be changed by a pre-run amendment.  Identity and lineage
# fields are immutable; changing a protocol-level field still creates a new
# ExperimentPlan revision and must be visible in the amendment record.
AMENDABLE_PREREGISTRATION_FIELDS = frozenset({
    "research_question", "independent_variables", "control_conditions",
    "dependent_measures", "sample_plan", "confounds", "stopping_rules",
    "success_criteria", "ethics_notes", "protocol_snapshot",
    "analysis_family_revision_id", "condition_snapshot_ids",
    # Compatibility names used by early M2 callers.
    "sample", "measures", "analysis", "conditions", "stopping",
})


def validate_amendment_fields(changed_fields: Iterable[str]) -> tuple[str, ...]:
    fields = tuple(dict.fromkeys(str(field).strip() for field in changed_fields if str(field).strip()))
    if not fields:
        raise ValueError("amendment must name changed fields")
    unknown = tuple(field for field in fields if field not in AMENDABLE_PREREGISTRATION_FIELDS)
    if unknown:
        raise ValueError("amendment contains immutable or unknown fields: " + ", ".join(unknown))
    return fields


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def build_dependency_graph(
    *,
    graph_id: str,
    nodes: Iterable[DependencyRef],
    edges: Iterable[tuple[str, str]] = (),
    field_coverage: Iterable[str] = (),
    actor: str = "system",
    status: str = "closed",
    parent_revision_id: str | None = None,
) -> DependencyGraphRevision:
    revision = 1
    if parent_revision_id:
        try:
            revision = int(parent_revision_id.rsplit(".r", 1)[1]) + 1
        except (IndexError, ValueError):
            revision = 1
    return DependencyGraphRevision(
        graph_id=graph_id,
        revision_id=f"{graph_id}.r{revision}",
        meta=RevisionMeta(revision=revision, parent_revision_id=parent_revision_id, created_by=actor, reason="dependency graph revision"),
        nodes=tuple(nodes),
        edges=tuple(edges),
        field_coverage=tuple(field_coverage),
        status=status,
    )


def amend_preregistration(plan: ExperimentPlan, *, changed_fields: Iterable[str], reason: str, approved_by: str, actor: str = "human") -> tuple[ExperimentPlan, PreregistrationAmendment]:
    if plan.status in {"started", "completed", "stale", "suspended"}:
        raise ValueError("preregistration cannot be amended after experiment start")
    fields = validate_amendment_fields(changed_fields)
    next_revision = plan.meta.revision + 1
    amendment_id = _id("amendment")
    updated = plan.model_copy(update={
        "revision_id": f"{plan.experiment_id}.r{next_revision}",
        "meta": RevisionMeta(revision=next_revision, parent_revision_id=plan.revision_id, created_by=actor, reason=reason),
        "amendment_ids": tuple(plan.amendment_ids) + (amendment_id,),
    })
    amendment = PreregistrationAmendment(
        amendment_id=amendment_id, revision_id=f"{amendment_id}.r1",
        meta=RevisionMeta(revision=1, created_by=approved_by, reason=reason),
        experiment_revision_id=updated.revision_id, changed_fields=fields,
        reason=reason, approved_by=approved_by,
    )
    return updated, amendment


def start_experiment(plan: ExperimentPlan, *, trigger: str, actor: str = "system", occurred_at: datetime | None = None) -> tuple[ExperimentPlan, ExperimentStartEvent]:
    if plan.status not in {"preregistered", "approved"}:
        raise ValueError("experiment must be preregistered or approved before start")
    when = occurred_at or datetime.now(timezone.utc)
    event_id = _id("experiment-start")
    event = ExperimentStartEvent(
        event_id=event_id,
        revision_id=f"{event_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="first irreversible research action"),
        experiment_revision_id=plan.revision_id,
        trigger=trigger,
        occurred_at=when,
    )
    next_revision = plan.meta.revision + 1
    started = plan.model_copy(update={
        "revision_id": f"{plan.experiment_id}.r{next_revision}",
        "meta": RevisionMeta(revision=next_revision, parent_revision_id=plan.revision_id, created_by=actor, reason="experiment started"),
        "status": "started", "started_at": when, "start_event_id": event.revision_id,
    })
    return started, event


def record_protocol_deviation(*, experiment_revision_id: str, field: str, planned_value: str | None, actual_value: str | None, impact: str = "unknown", actor: str = "system") -> ProtocolDeviation:
    deviation_id = _id("protocol-deviation")
    return ProtocolDeviation(
        deviation_id=deviation_id, revision_id=f"{deviation_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="protocol deviation recorded"),
        experiment_revision_id=experiment_revision_id, field=field,
        planned_value=planned_value, actual_value=actual_value, impact=impact,
    )


def assess_independence(*, subject_id: str, source_ids: Iterable[str], critical_fields: Iterable[str], covered_fields: Iterable[str], actor: str = "reviewer", shared_dependencies: Iterable[str] = (), common_failure_modes: Iterable[str] = ()) -> IndependenceAssessment:
    source_ids = tuple(dict.fromkeys(source_ids))
    if not source_ids:
        raise ValueError("independence assessment requires at least one source")
    critical, covered = tuple(critical_fields), tuple(covered_fields)
    shared, modes = tuple(shared_dependencies), tuple(common_failure_modes)
    if not set(critical).issubset(covered):
        status = "independence_coverage_gap"
    elif shared or modes:
        status = "correlated_evidence_dependency"
    else:
        status = "independent"
    aid = _id("independence")
    return IndependenceAssessment(
        assessment_id=aid, revision_id=f"{aid}.r1", meta=RevisionMeta(revision=1, created_by=actor, reason="independence assessment"),
        subject_id=subject_id, source_ids=source_ids, critical_fields=critical,
        covered_fields=covered, shared_dependencies=shared, common_failure_modes=modes,
        status=status, reviewer_id=actor,
    )


def classify_canary_failure(canary: CanaryRevision, *, classification: str, technical_failure: bool, actor: str = "reviewer") -> CanaryRevision:
    if technical_failure and not canary.replacement_allowed:
        # A technical label is not itself permission to replace a canary.
        status = "canary_failure_classification_uncertain"
    else:
        status = "failed"
    next_revision = canary.meta.revision + 1
    return canary.model_copy(update={
        "revision_id": f"{canary.canary_id}.r{next_revision}",
        "meta": RevisionMeta(revision=next_revision, parent_revision_id=canary.revision_id, created_by=actor, reason="independent canary failure classification"),
        "status": status, "failure_classification": classification,
    })


def critical_path_coverage(canaries: Iterable[CanaryRevision], required_paths: Iterable[str]) -> tuple[str, ...]:
    covered = {c.path_id for c in canaries if c.criticality == "critical" and c.status in {"passed", "reinstated"}}
    return tuple(path for path in required_paths if path not in covered)


def merge_release_grants(grants: Iterable[ReleaseScopeGrant]) -> tuple[ReleaseScopeGrant, ...]:
    """Apply deterministic precedence; ambiguity is represented as conflict."""
    values = tuple(grants)
    result: list[ReleaseScopeGrant] = []
    for grant in values:
        conflict = next((existing for existing in result if set(existing.allowed_paths) & set(grant.allowed_paths) or set(existing.allowed_interactions) & set(grant.allowed_interactions)), None)
        if conflict is None:
            result.append(grant); continue
        if grant.precedence == "supersede" and grant.meta.revision > conflict.meta.revision:
            result[result.index(conflict)] = grant.model_copy(update={"status": "active"})
        elif conflict.precedence == "supersede" and conflict.meta.revision > grant.meta.revision:
            continue
        else:
            result[result.index(conflict)] = conflict.model_copy(update={"status": "grant_conflict"})
    return tuple(result)


def revoke_grant(grant: ReleaseScopeGrant, *, inventory_node_ids: Iterable[str], receipts: Iterable[str], usage_log_refs: Iterable[str] = (), reason: str = "revoked", actor: str = "security", unregistered: bool = False, watch_gap: bool = False, usage_unknown: bool = False, execution_uncertain: bool = False) -> GrantRevocationRevision:
    inventory, receipt_ids, usage = tuple(inventory_node_ids), tuple(receipts), tuple(usage_log_refs)
    closed = bool(inventory) and set(inventory) == set(receipt_ids) and bool(usage)
    if unregistered:
        status = "execution_inventory_gap"
    elif watch_gap:
        status = "execution_inventory_watch_gap"
    elif usage_unknown:
        status = "authorization_usage_unknown"
    elif execution_uncertain:
        status = "authorization_execution_uncertain"
    else:
        status = "converged" if closed else "grant_revocation_pending"
    rid = _id("grant-revocation")
    return GrantRevocationRevision(
        revocation_id=rid, revision_id=f"{rid}.r1", meta=RevisionMeta(revision=1, created_by=actor, reason=reason),
        grant_id=grant.grant_id, reason=reason, receipt_node_ids=receipt_ids,
        inventory_node_ids=inventory, usage_log_refs=usage,
        status=status,
    )


def create_job_snapshot(*, job_id: str, kind: str, provider: str, model: str, target_object_type: str, target_object_id: str, target_revision_id: str, expected_revision: int | None = None, input_hashes: Iterable[tuple[str, str]] = (), policy_revision_id: str | None = None, consent_scope_revision_id: str | None = None, actor: str = "system") -> tuple[ExternalCallSnapshot, JobRecord]:
    input_hashes = tuple(input_hashes)
    fingerprint_payload = {
        "provider": provider,
        "model": model,
        "inputs": input_hashes,
        "policy": policy_revision_id,
        "consent": consent_scope_revision_id,
        "target": (target_object_type, target_object_id, target_revision_id),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    call = ExternalCallSnapshot(
        call_id=_id("call"), revision_id=f"{job_id}.call.r1", meta=RevisionMeta(revision=1, created_by=actor, reason="external call snapshot"),
        provider=provider, model=model, input_hashes=input_hashes, policy_revision_id=policy_revision_id,
        consent_scope_revision_id=consent_scope_revision_id, target_object_type=target_object_type,
        target_object_id=target_object_id, target_revision_id=target_revision_id,
        fingerprint=fingerprint,
    )
    if expected_revision is None:
        # Revision IDs conventionally end in ``.rN``.  Keep an explicit
        # override for opaque IDs, but never silently pin every job to r1.
        try:
            expected_revision = int(target_revision_id.rsplit(".r", 1)[1])
        except (IndexError, ValueError):
            expected_revision = 1
    if expected_revision < 1:
        raise ValueError("expected_revision must be >= 1")
    job = JobRecord(
        job_id=job_id, revision_id=f"{job_id}.r1", meta=RevisionMeta(revision=1, created_by=actor, reason="job created"),
        kind=kind, external_call_snapshot_id=call.revision_id, target_object_type=target_object_type,
        target_object_id=target_object_id, expected_revision=expected_revision, fingerprint=call.fingerprint,
    )
    return call, job


def commit_job_result(job: JobRecord, *, actual_revision: int, payload: dict, result_revision_id: str | None = None, actor: str = "worker", actual_fingerprint: str | None = None, target_object_type: str | None = None, target_object_id: str | None = None) -> JobRecord | StaleJobResult:
    stale_reasons: list[str] = []
    if actual_revision != job.expected_revision:
        stale_reasons.append("target_revision_changed")
    if actual_fingerprint is not None and actual_fingerprint != job.fingerprint:
        stale_reasons.append("external_call_snapshot_changed")
    if target_object_type is not None and target_object_type != job.target_object_type:
        stale_reasons.append("target_object_type_changed")
    if target_object_id is not None and target_object_id != job.target_object_id:
        stale_reasons.append("target_object_id_changed")
    if stale_reasons:
        stale_id = _id("stale-result")
        return StaleJobResult(
            result_id=stale_id, revision_id=f"{stale_id}.r1", meta=RevisionMeta(revision=1, created_by=actor, reason="optimistic revision mismatch"),
            job_id=job.job_id, target_object_type=job.target_object_type, target_object_id=job.target_object_id,
            expected_revision=job.expected_revision, actual_revision=actual_revision, payload=payload,
            stale_reasons=tuple(stale_reasons),
        )
    return job.model_copy(update={"status": "succeeded", "result_revision_id": result_revision_id})


def build_outbox_event(domain_event: DomainEvent, *, payload: dict | None = None, actor: str = "system") -> OutboxEvent:
    return OutboxEvent(
        outbox_id=_id("outbox"), revision_id=f"{domain_event.event_id}.outbox.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="transactional outbox"),
        event_id=domain_event.event_id, event_type=domain_event.event_type,
        payload={key: value for key, value in domain_event.data} if payload is None else payload,
    )


def validate_event_log_chain(logs: Iterable[EventLogRecord]) -> bool:
    """Validate sequence/hash convergence for an append-only event buffer."""
    ordered = sorted(tuple(logs), key=lambda item: item.sequence)
    if not ordered:
        return True
    for index, item in enumerate(ordered):
        if item.sequence != index + 1 or item.status in {"integrity_uncertain", "overflow"}:
            return False
        if index and item.previous_hash != ordered[index - 1].payload_hash:
            return False
    return True


__all__ = [
    "AMENDABLE_PREREGISTRATION_FIELDS", "validate_amendment_fields",
    "amend_preregistration", "assess_independence", "build_dependency_graph",
    "build_outbox_event", "commit_job_result", "create_job_snapshot",
    "classify_canary_failure", "critical_path_coverage", "merge_release_grants",
    "record_protocol_deviation", "revoke_grant", "start_experiment", "validate_event_log_chain",
]
