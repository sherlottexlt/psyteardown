"""Deterministic engineering traceability projections and gap checks."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from pydantic import Field

from psyteardown.experience.engineering import (
    ENGINEERING_MODEL_TYPES,
    DVPRevision,
    EngineeringProjectRevision,
    EngineeringRequirement,
    EngineeringRecord,
    RawEngineeringToolResult,
    ReleaseDecision,
    VerificationTestRun,
    _record_id,
    canonical_object_type,
)
from psyteardown.experience.models import DependencyRef, DomainStateError, FrozenModel


class TraceabilityIssue(FrozenModel):
    code: str
    severity: Literal["blocker", "warning", "info"]
    object_type: str
    object_id: str
    revision_id: str
    message: str


class TraceabilityNode(FrozenModel):
    object_type: str
    object_id: str
    revision_id: str
    revision: int = Field(ge=1)
    status: str
    created_by: str
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    source_refs: tuple[str, ...] = ()
    dependencies: tuple[DependencyRef, ...] = ()


class RequirementTrace(FrozenModel):
    requirement_id: str
    requirement_revision_id: str
    title: str
    requirement_type: str
    hard_constraint: bool
    source_type: str
    source_refs: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    verification_methods: tuple[str, ...]
    downstream_nodes: tuple[TraceabilityNode, ...]
    verification_test_revision_ids: tuple[str, ...] = ()
    raw_result_revision_ids: tuple[str, ...] = ()
    evidence_review_ids: tuple[str, ...] = ()
    issue_codes: tuple[str, ...] = ()


class EngineeringTraceabilityReport(FrozenModel):
    project_id: str
    project_revision_id: str
    stage: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requirement_traces: tuple[RequirementTrace, ...]
    gate_revision_ids: tuple[str, ...] = ()
    open_conflict_ids: tuple[str, ...] = ()
    stale_nodes: tuple[TraceabilityNode, ...] = ()
    issues: tuple[TraceabilityIssue, ...] = ()
    release_decision_revision_ids: tuple[str, ...] = ()
    status: Literal["traceable", "gaps", "blocked"] = "gaps"


def _node_key(object_type: str, object_id: str, revision: int) -> str:
    return f"{canonical_object_type(object_type)}:{object_id}:{revision}"


def _latest_engineering_objects(repository: Any) -> dict[str, tuple[str, str, EngineeringRecord]]:
    latest: dict[str, tuple[str, str, EngineeringRecord]] = {}
    for object_type in ENGINEERING_MODEL_TYPES:
        for item in repository.list_revisions(object_type):
            object_id = _record_id(object_type, item)
            key = f"{object_type}:{object_id}"
            previous = latest.get(key)
            if previous is None or item.meta.revision > previous[2].meta.revision:
                latest[key] = (object_type, object_id, item)
    return latest


def _trace_node(object_type: str, object_id: str, item: EngineeringRecord) -> TraceabilityNode:
    return TraceabilityNode(
        object_type=object_type,
        object_id=object_id,
        revision_id=item.revision_id,
        revision=item.meta.revision,
        status=item.status,
        created_by=item.meta.created_by,
        reviewer=item.reviewer,
        reviewed_at=item.reviewed_at,
        source_refs=item.source_refs,
        dependencies=item.dependencies,
    )


def build_engineering_traceability_report(
    repository: Any,
    project_id: str,
) -> EngineeringTraceabilityReport:
    project = repository.get_current("engineering_project", project_id)
    if project is None or not isinstance(project, EngineeringProjectRevision):
        raise DomainStateError("engineering project is unavailable")

    current = _latest_engineering_objects(repository)
    by_revision_id = {
        item.revision_id: (object_type, object_id, item)
        for object_type, object_id, item in current.values()
    }
    reverse: dict[str, set[str]] = {}
    node_by_key: dict[str, tuple[str, str, EngineeringRecord]] = {}
    for object_type, object_id, item in current.values():
        key = _node_key(object_type, object_id, item.meta.revision)
        node_by_key[key] = (object_type, object_id, item)
        for dependency in item.dependencies:
            dep_key = _node_key(dependency.object_type, dependency.object_id, dependency.revision)
            reverse.setdefault(dep_key, set()).add(key)

    # Some formal domain relationships are stored as named revision IDs rather
    # than generic dependencies.  Project them into the query graph without
    # rewriting their immutable source objects.
    for object_type, object_id, item in current.values():
        key = _node_key(object_type, object_id, item.meta.revision)
        requirement_ids = tuple(getattr(item, "requirement_ids", ()))
        for requirement_id in requirement_ids:
            requirement = repository.get_current("engineering_requirement", requirement_id)
            if requirement is not None:
                reverse.setdefault(
                    _node_key("engineering_requirement", requirement_id, requirement.meta.revision), set()
                ).add(key)
        if isinstance(item, DVPRevision):
            for test_revision_id in item.verification_test_run_ids:
                target = by_revision_id.get(test_revision_id)
                if target is not None:
                    target_type, target_id, target_item = target
                    reverse.setdefault(key, set()).add(
                        _node_key(target_type, target_id, target_item.meta.revision)
                    )

    issues: list[TraceabilityIssue] = []
    traces: list[RequirementTrace] = []
    for revision_id in project.requirement_revision_ids:
        requirement = repository.get_revision("engineering_requirement", revision_id)
        if requirement is None or not isinstance(requirement, EngineeringRequirement):
            issues.append(TraceabilityIssue(
                code="requirement_revision_missing",
                severity="blocker",
                object_type="engineering_project",
                object_id=project.project_id,
                revision_id=project.revision_id,
                message=f"Project requirement revision is unavailable: {revision_id}",
            ))
            continue
        current_requirement = repository.get_current("engineering_requirement", requirement.requirement_id)
        start_revision = current_requirement.meta.revision if current_requirement is not None else requirement.meta.revision
        start_key = _node_key("engineering_requirement", requirement.requirement_id, start_revision)
        queue: deque[str] = deque(reverse.get(start_key, ()))
        reachable: set[str] = set()
        while queue:
            key = queue.popleft()
            if key in reachable:
                continue
            reachable.add(key)
            queue.extend(reverse.get(key, ()))
        downstream = tuple(
            _trace_node(*node_by_key[key])
            for key in sorted(reachable)
            if key in node_by_key
        )
        tests = tuple(
            item for _, _, item in (node_by_key[key] for key in reachable if key in node_by_key)
            if isinstance(item, VerificationTestRun)
        )
        raw_results = tuple(
            item for _, _, item in (node_by_key[key] for key in reachable if key in node_by_key)
            if isinstance(item, RawEngineeringToolResult)
        )
        requirement_issue_codes: list[str] = []
        if current_requirement is None or current_requirement.revision_id != revision_id:
            requirement_issue_codes.append("requirement_revision_stale")
        if requirement.status != "approved" or not requirement.reviewer or requirement.reviewed_at is None:
            requirement_issue_codes.append("requirement_not_human_approved")
        if not downstream:
            requirement_issue_codes.append("requirement_has_no_downstream_trace")
        passing_tests = tuple(
            item for item in tests
            if item.status == "approved"
            and item.result == "pass"
            and item.raw_measurement_refs
            and item.evidence_review_id
            and item.reviewer
        )
        if (requirement.hard_constraint or requirement.requirement_type == "must") and not passing_tests:
            requirement_issue_codes.append("must_requirement_has_no_reviewed_passing_test")
        if any(node.status in {"stale", "invalidated", "blocked", "rejected"} for node in downstream):
            requirement_issue_codes.append("requirement_downstream_not_current")
        for code in requirement_issue_codes:
            issues.append(TraceabilityIssue(
                code=code,
                severity="blocker" if code != "requirement_has_no_downstream_trace" or requirement.hard_constraint else "warning",
                object_type="engineering_requirement",
                object_id=requirement.requirement_id,
                revision_id=requirement.revision_id,
                message=f"Traceability gap for requirement '{requirement.title}': {code}",
            ))
        traces.append(RequirementTrace(
            requirement_id=requirement.requirement_id,
            requirement_revision_id=requirement.revision_id,
            title=requirement.title,
            requirement_type=requirement.requirement_type,
            hard_constraint=requirement.hard_constraint,
            source_type=requirement.source_type,
            source_refs=requirement.source_refs,
            acceptance_criteria=requirement.acceptance_criteria,
            verification_methods=requirement.verification_methods,
            downstream_nodes=downstream,
            verification_test_revision_ids=tuple(item.revision_id for item in tests),
            raw_result_revision_ids=tuple(item.revision_id for item in raw_results),
            evidence_review_ids=tuple(
                dict.fromkeys(item.evidence_review_id for item in tests if item.evidence_review_id)
            ),
            issue_codes=tuple(requirement_issue_codes),
        ))

    for object_type, object_id, item in current.values():
        if item.status == "approved" and (not item.reviewer or item.reviewed_at is None):
            issues.append(TraceabilityIssue(
                code="approved_object_missing_human_review",
                severity="blocker",
                object_type=object_type,
                object_id=object_id,
                revision_id=item.revision_id,
                message="Approved engineering object lacks a named reviewer or review timestamp.",
            ))
        if isinstance(item, RawEngineeringToolResult) and item.execution_status == "succeeded":
            if not item.artifacts or any(not artifact.sha256 for artifact in item.artifacts):
                issues.append(TraceabilityIssue(
                    code="raw_tool_result_missing_hash",
                    severity="blocker",
                    object_type=object_type,
                    object_id=object_id,
                    revision_id=item.revision_id,
                    message="Successful raw tool result lacks a hash-addressed artifact.",
                ))
        if isinstance(item, VerificationTestRun) and item.result == "pass":
            if not item.raw_measurement_refs or not item.evidence_review_id:
                issues.append(TraceabilityIssue(
                    code="passing_test_missing_raw_evidence",
                    severity="blocker",
                    object_type=object_type,
                    object_id=object_id,
                    revision_id=item.revision_id,
                    message="Passing verification test lacks raw measurements or EvidenceReview.",
                ))

    stale_nodes = tuple(
        _trace_node(object_type, object_id, item)
        for object_type, object_id, item in current.values()
        if item.status in {"stale", "invalidated"}
    )
    release_decisions = tuple(
        item for _, _, item in current.values()
        if isinstance(item, ReleaseDecision)
    )
    if any(item.decision == "approved" for item in release_decisions) and any(
        issue.severity == "blocker" for issue in issues
    ):
        issues.append(TraceabilityIssue(
            code="approved_release_has_traceability_blockers",
            severity="blocker",
            object_type="engineering_project",
            object_id=project.project_id,
            revision_id=project.revision_id,
            message="An approved release exists while traceability blockers remain.",
        ))

    status: Literal["traceable", "gaps", "blocked"]
    if project.status == "blocked" or any(issue.severity == "blocker" for issue in issues):
        status = "blocked"
    elif issues:
        status = "gaps"
    else:
        status = "traceable"
    return EngineeringTraceabilityReport(
        project_id=project.project_id,
        project_revision_id=project.revision_id,
        stage=project.stage,
        requirement_traces=tuple(traces),
        gate_revision_ids=project.gate_decision_revision_ids,
        open_conflict_ids=project.open_conflict_ids,
        stale_nodes=stale_nodes,
        issues=tuple(issues),
        release_decision_revision_ids=tuple(item.revision_id for item in release_decisions),
        status=status,
    )


def render_engineering_traceability_json(report: EngineeringTraceabilityReport) -> str:
    return report.model_dump_json(indent=2)


def render_engineering_traceability_markdown(report: EngineeringTraceabilityReport) -> str:
    lines = [
        f"# Engineering Traceability — {report.project_id}",
        "",
        f"- Project revision: `{report.project_revision_id}`",
        f"- Stage: `{report.stage}`",
        f"- Traceability status: `{report.status}`",
        f"- Open conflicts: {', '.join(report.open_conflict_ids) if report.open_conflict_ids else 'none'}",
        "",
        "## Requirements",
    ]
    for trace in report.requirement_traces:
        lines.extend([
            "",
            f"### {trace.title} (`{trace.requirement_revision_id}`)",
            "",
            f"- Source: `{trace.source_type}` — {', '.join(trace.source_refs) or 'none'}",
            f"- Type: `{trace.requirement_type}`; hard constraint: `{str(trace.hard_constraint).lower()}`",
            f"- Downstream revisions: {', '.join(item.revision_id for item in trace.downstream_nodes) or 'none'}",
            f"- Verification tests: {', '.join(trace.verification_test_revision_ids) or 'none'}",
            f"- Evidence reviews: {', '.join(trace.evidence_review_ids) or 'none'}",
            f"- Issues: {', '.join(trace.issue_codes) or 'none'}",
        ])
    lines.extend(["", "## Issues", ""])
    if report.issues:
        lines.extend(
            f"- **{item.severity}** `{item.code}` — {item.object_type}:{item.revision_id}: {item.message}"
            for item in report.issues
        )
    else:
        lines.append("- none")
    lines.extend([
        "",
        "> This projection reports traceability and gaps. It is not a physical-test, manufacturing, certification or release approval.",
    ])
    return "\n".join(lines)


__all__ = [
    "TraceabilityIssue", "TraceabilityNode", "RequirementTrace",
    "EngineeringTraceabilityReport", "build_engineering_traceability_report",
    "render_engineering_traceability_json", "render_engineering_traceability_markdown",
]
