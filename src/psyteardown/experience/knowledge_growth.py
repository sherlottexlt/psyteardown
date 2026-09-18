"""P5 evidence-gated cross-case engineering knowledge growth."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from psyteardown.experience.engineering import (
    ApprovedKnowledgeRule,
    CrossCaseEvidenceRef,
    CrossCaseKnowledgeCandidate,
    EngineeringOrchestrator,
)
from psyteardown.experience.models import DependencyRef, DomainStateError, RevisionMeta
from psyteardown.experience.multimodal import is_named_human_actor


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\u3400-\u9fff]+", " ", text.lower()).strip()
    words = set(normalized.split())
    # Chinese statements often contain no spaces; character bigrams preserve
    # deterministic near-duplicate detection without an external model.
    compact = normalized.replace(" ", "")
    words.update(compact[index:index + 2] for index in range(max(0, len(compact) - 1)))
    return {item for item in words if item}


def _similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / len(a | b) if a or b else 1.0


class CrossCaseKnowledgeCoordinator:
    """Keeps candidates out of default knowledge until human approval."""

    def __init__(self, repository: Any, *, actor: str = "ai-knowledge-orchestrator") -> None:
        self.repository = repository
        self.registry = EngineeringOrchestrator(repository, actor=actor)
        self.actor = actor

    def _validate_case(self, source: CrossCaseEvidenceRef) -> tuple[Any, tuple[Any, ...]]:
        hypothesis = self.repository.get_revision("experience_hypothesis", source.hypothesis_revision_id)
        current = self.repository.get_current("experience_hypothesis", source.hypothesis_id)
        if hypothesis is None or current is None or current.revision_id != hypothesis.revision_id:
            raise DomainStateError(f"case {source.case_id} references a stale hypothesis")
        if hypothesis.status != source.outcome or source.outcome not in {"supported", "rejected"}:
            raise DomainStateError(f"case {source.case_id} outcome does not match its hypothesis")
        if not any(item.kind == "experiment" for item in hypothesis.evidence):
            raise DomainStateError(f"case {source.case_id} lacks experiment evidence")
        dependency_types = {(item.object_type, item.object_id) for item in hypothesis.dependencies}
        protocol_dependencies = tuple(
            item for item in hypothesis.dependencies if item.object_type == "analysis_protocol_review"
        )
        if not protocol_dependencies:
            raise DomainStateError(f"case {source.case_id} lacks an approved analysis-protocol lineage")
        for dependency in protocol_dependencies:
            protocol_review = self.repository.get_current("analysis_protocol_review", dependency.object_id)
            if (
                protocol_review is None
                or protocol_review.meta.revision != dependency.revision
                or protocol_review.status != "approved"
            ):
                raise DomainStateError(f"case {source.case_id} analysis-protocol lineage is not approved/current")
        reviews = tuple(
            self.repository.get_revision("evidence_review", revision_id)
            for revision_id in source.evidence_review_revision_ids
        )
        if not reviews or any(
            item is None or item.decision not in {"accepted", "modified", "confirmed"}
            for item in reviews
        ):
            raise DomainStateError(f"case {source.case_id} lacks an accepting EvidenceReview")
        if any(("evidence_review", item.review_id) not in dependency_types for item in reviews):
            raise DomainStateError(f"case {source.case_id} EvidenceReview is not bound to the hypothesis")
        if not source.condition_snapshot_revision_ids:
            raise DomainStateError(f"case {source.case_id} lacks condition lineage")
        for condition_revision_id in source.condition_snapshot_revision_ids:
            if self.repository.get_revision("condition", condition_revision_id) is None:
                raise DomainStateError(f"case {source.case_id} references an unknown condition")
        for review in reviews:
            if review.analysis_protocol_review_id not in {
                item.revision_id
                for item in (
                    self.repository.get_current("analysis_protocol_review", dependency.object_id)
                    for dependency in protocol_dependencies
                )
                if item is not None
            }:
                raise DomainStateError(f"case {source.case_id} EvidenceReview uses another analysis protocol")
            if not set(source.condition_snapshot_revision_ids).issubset(review.condition_snapshot_ids):
                raise DomainStateError(f"case {source.case_id} condition is outside its EvidenceReview")
            measurements = tuple(
                self.repository.get_current("measurement_observation", observation_id)
                for observation_id in review.confirmed_observation_ids
            )
            if not measurements or any(
                item is None
                or item.status != "confirmed"
                or not (item.raw_file_hash or item.source_asset_ids)
                for item in measurements
            ):
                raise DomainStateError(f"case {source.case_id} lacks traceable confirmed measurements")
        return hypothesis, reviews

    def propose_rule(
        self,
        *,
        rule_id: str,
        statement: str,
        applicability: Iterable[str],
        counter_conditions: Iterable[str],
        source_cases: Iterable[CrossCaseEvidenceRef],
        conflicting_rule_ids: Iterable[str] = (),
        actor: str | None = None,
    ) -> CrossCaseKnowledgeCandidate:
        sources = tuple(source_cases)
        if len({item.case_id for item in sources}) != len(sources):
            raise DomainStateError("cross-case knowledge requires unique case IDs")
        if not sources:
            raise DomainStateError("cross-case knowledge requires evidence-bearing cases")
        validated = tuple(self._validate_case(source) for source in sources)
        existing_candidates = self.repository.list_revisions("cross_case_knowledge_candidate")
        existing_rules = self.repository.list_revisions("approved_knowledge_rule")
        duplicate_ids = tuple(dict.fromkeys(
            item.rule_id for item in (*existing_candidates, *existing_rules)
            if item.rule_id != rule_id and _similarity(statement, item.statement) >= 0.85
        ))
        supporting = tuple(item.case_id for item in sources if item.outcome == "supported")
        counterexamples = tuple(item.case_id for item in sources if item.outcome == "rejected")
        conflicts = tuple(dict.fromkeys(conflicting_rule_ids))
        replication_count = len(set(supporting))
        replication_status = (
            "conflicted" if conflicts or counterexamples
            else ("replicated" if replication_count >= 2 else "insufficient")
        )
        dependencies: list[DependencyRef] = []
        for source, (hypothesis, reviews) in zip(sources, validated):
            dependencies.append(DependencyRef(
                object_type="experience_hypothesis",
                object_id=hypothesis.hypothesis_id,
                revision=hypothesis.meta.revision,
            ))
            dependencies.extend(
                DependencyRef(
                    object_type="evidence_review",
                    object_id=review.review_id,
                    revision=review.meta.revision,
                )
                for review in reviews
            )
        candidate = CrossCaseKnowledgeCandidate(
            rule_id=rule_id,
            revision_id=f"{rule_id}.r1",
            meta=RevisionMeta(
                revision=1,
                created_by=actor or self.actor,
                reason="cross-case knowledge candidate proposed",
            ),
            dependencies=tuple(dict.fromkeys(dependencies)),
            status="current",
            statement=statement,
            applicability=tuple(applicability),
            counter_conditions=tuple(counter_conditions),
            source_cases=sources,
            supporting_case_ids=supporting,
            counterexample_case_ids=counterexamples,
            duplicate_rule_ids=duplicate_ids,
            conflicting_rule_ids=conflicts,
            replication_count=replication_count,
            replication_status=replication_status,
        )
        return self.registry.register("cross_case_knowledge_candidate", candidate)

    def review_candidate(
        self,
        candidate: CrossCaseKnowledgeCandidate,
        *,
        reviewer: str,
        decision: str,
        rationale: str,
        counterexamples_reviewed: bool,
        resolved_conflict_ids: Iterable[str] = (),
        resolved_duplicate_rule_ids: Iterable[str] = (),
    ) -> CrossCaseKnowledgeCandidate | ApprovedKnowledgeRule:
        if decision not in {"approved", "rejected"}:
            raise DomainStateError("knowledge review decision must be approved or rejected")
        if not is_named_human_actor(reviewer):
            raise DomainStateError("cross-case knowledge review requires a named human reviewer")
        current = self.repository.get_current("cross_case_knowledge_candidate", candidate.rule_id)
        if current is None or current.revision_id != candidate.revision_id:
            raise DomainStateError("cross-case knowledge candidate revision is stale")
        resolved_conflicts = tuple(dict.fromkeys(resolved_conflict_ids))
        resolved_duplicates = tuple(dict.fromkeys(resolved_duplicate_rule_ids))
        if not set(resolved_conflicts).issubset(candidate.conflicting_rule_ids):
            raise DomainStateError("resolved conflict is not declared on the candidate")
        if not set(resolved_duplicates).issubset(candidate.duplicate_rule_ids):
            raise DomainStateError("resolved duplicate is not declared on the candidate")
        unresolved_conflicts = set(candidate.conflicting_rule_ids) - set(resolved_conflicts)
        unresolved_duplicates = set(candidate.duplicate_rule_ids) - set(resolved_duplicates)
        if decision == "approved":
            if candidate.replication_count < 2:
                raise DomainStateError("knowledge approval requires replication across at least two cases")
            if unresolved_conflicts or unresolved_duplicates:
                raise DomainStateError("knowledge approval requires duplicate/conflict resolution")
            if not counterexamples_reviewed:
                raise DomainStateError("knowledge approval requires counterexample review")
            if candidate.counterexample_case_ids and not candidate.counter_conditions:
                raise DomainStateError("counterexamples require explicit counter-conditions")
        revision = candidate.meta.revision + 1
        reviewed_at = datetime.now(timezone.utc)
        reviewed = candidate.model_copy(update={
            "revision_id": f"{candidate.rule_id}.r{revision}",
            "meta": RevisionMeta(
                revision=revision,
                parent_revision_id=candidate.revision_id,
                created_by=reviewer,
                reason=rationale,
            ),
            "status": decision,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "knowledge_status": decision,
            "counterexamples_reviewed": counterexamples_reviewed,
            "resolved_conflict_ids": resolved_conflicts,
            "resolved_duplicate_rule_ids": resolved_duplicates,
            "replication_status": "replicated" if decision == "approved" else candidate.replication_status,
            "decision_rationale": rationale,
        })
        self.registry.register("cross_case_knowledge_candidate", reviewed)
        if decision == "rejected":
            return reviewed
        evidence_review_ids = tuple(dict.fromkeys(
            revision_id
            for source in reviewed.source_cases
            for revision_id in source.evidence_review_revision_ids
        ))
        approved = ApprovedKnowledgeRule(
            rule_id=reviewed.rule_id,
            revision_id=f"{reviewed.rule_id}.approved.r1",
            meta=RevisionMeta(revision=1, created_by=reviewer, reason=rationale),
            dependencies=(DependencyRef(
                object_type="cross_case_knowledge_candidate",
                object_id=reviewed.rule_id,
                revision=reviewed.meta.revision,
            ),),
            status="approved",
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            candidate_revision_id=reviewed.revision_id,
            statement=reviewed.statement,
            applicability=reviewed.applicability,
            counter_conditions=reviewed.counter_conditions,
            source_case_ids=tuple(item.case_id for item in reviewed.source_cases),
            evidence_review_revision_ids=evidence_review_ids,
            replication_count=reviewed.replication_count,
            decision_rationale=rationale,
        )
        return self.registry.register("approved_knowledge_rule", approved)

    def default_rules(self) -> tuple[ApprovedKnowledgeRule, ...]:
        """Only human-approved current rules may influence default behavior."""
        latest: dict[str, ApprovedKnowledgeRule] = {}
        for item in self.repository.list_revisions("approved_knowledge_rule"):
            previous = latest.get(item.rule_id)
            if previous is None or item.meta.revision > previous.meta.revision:
                latest[item.rule_id] = item
        return tuple(
            item for item in latest.values()
            if item.status == "approved" and item.reviewer and item.reviewed_at is not None
        )


__all__ = ["CrossCaseKnowledgeCoordinator"]
