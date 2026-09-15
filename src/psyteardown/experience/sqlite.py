"""Minimal SQLite adapter for the experience vertical slice.

This adapter owns only the new ``experience`` tables.  It does not inspect,
migrate, or rewrite the legacy pipeline database.  Snapshots are stored as
JSON blobs with an explicit type/revision key; current pointers and the two
event streams are separate projections, matching ADR-0201 and ADR-0097.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from psyteardown.experience.models import (
    AuditEvent,
    CandidateEvaluationRecord,
    CandidateFactsSnapshot,
    CandidatePartialOrder,
    DesignBrief,
    DesignCandidate,
    DesignRuleSet,
    DesignToolRun,
    PrototypeRun,
    MeasurementObservation,
    EvidenceReview,
    PrototypeAsset,
    ExternalAsset,
    ObservationDraft,
    ConfirmedObservation,
    Context,
    PhysicalFeature,
    Evidence,
    Observation,
    ExperienceHypothesis,
    Critique,
    DesignFeedbackSelection,
    ScenarioPolicy,
    DesignIteration,
    DomainEvent,
    NextDesignPrompt,
    ProgressiveDesignModel,
    ReviewItem,
    SelectionDecision,
    VariablePatch,
    VariableRepairTrace,
    UnauthorizedOutput,
    ContaminationMark,
    CleanRerunRecord,
    HypothesisBinding,
    AnalysisFamily,
    ExperimentPlan,
    PreregistrationAmendment,
    ProtocolDeviation,
    ExperimentStartEvent,
    ParticipantRecord,
    ConditionSnapshot,
    ConditionPresentationRecord,
    EventLogRecord,
    OutcomeObservation,
    ResearcherIntervention,
    DependencyGraphRevision,
    IndependenceAssessment,
    ArbitrationRevision,
    CanaryRevision,
    SuspensionRevision,
    ReleaseScopeGrant,
    ExecutionSurfaceReceipt,
    GrantRevocationRevision,
    ExternalCallSnapshot,
    JobRecord,
    StaleJobResult,
    OutboxEvent,
)
from psyteardown.experience.repositories import RepositoryError


T = TypeVar("T", bound=BaseModel)


_MODEL_TYPES: dict[str, type[BaseModel]] = {
    "brief": DesignBrief,
    "candidate": DesignCandidate,
    "rule_set": DesignRuleSet,
    "progressive_model": ProgressiveDesignModel,
    "facts": CandidateFactsSnapshot,
    "review": ReviewItem,
    "iteration": DesignIteration,
    "evaluation": CandidateEvaluationRecord,
    "partial_order": CandidatePartialOrder,
    "selection": SelectionDecision,
    "prompt": NextDesignPrompt,
    "patch": VariablePatch,
    "repair_trace": VariableRepairTrace,
    "design_tool_run": DesignToolRun,
    "prototype_run": PrototypeRun,
    "measurement_observation": MeasurementObservation,
    "evidence_review": EvidenceReview,
    "prototype_asset": PrototypeAsset,
    "external_asset": ExternalAsset,
    "observation_draft": ObservationDraft,
    "confirmed_observation": ConfirmedObservation,
    "context": Context,
    "physical_feature": PhysicalFeature,
    "evidence": Evidence,
    "observation": Observation,
    "experience_hypothesis": ExperienceHypothesis,
    "critique": Critique,
    "feedback_selection": DesignFeedbackSelection,
    "scenario_policy": ScenarioPolicy,
    "unauthorized_output": UnauthorizedOutput,
    "contamination_mark": ContaminationMark,
    "clean_rerun": CleanRerunRecord,
    "hypothesis_binding": HypothesisBinding,
    "analysis_family": AnalysisFamily,
    "experiment_plan": ExperimentPlan,
    "preregistration_amendment": PreregistrationAmendment,
    "protocol_deviation": ProtocolDeviation,
    "experiment_start": ExperimentStartEvent,
    "participant": ParticipantRecord,
    "condition": ConditionSnapshot,
    "condition_presentation": ConditionPresentationRecord,
    "event_log": EventLogRecord,
    "outcome_observation": OutcomeObservation,
    "researcher_intervention": ResearcherIntervention,
    "dependency_graph": DependencyGraphRevision,
    "independence": IndependenceAssessment,
    "arbitration": ArbitrationRevision,
    "canary": CanaryRevision,
    "suspension": SuspensionRevision,
    "release_grant": ReleaseScopeGrant,
    "execution_receipt": ExecutionSurfaceReceipt,
    "grant_revocation": GrantRevocationRevision,
    "external_call": ExternalCallSnapshot,
    "job": JobRecord,
    "stale_job_result": StaleJobResult,
    "outbox": OutboxEvent,
}


_SCHEMA = """
CREATE TABLE IF NOT EXISTS experience_revisions (
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    parent_revision_id TEXT,
    object_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (object_type, revision_id)
);
CREATE INDEX IF NOT EXISTS idx_experience_revisions_object
    ON experience_revisions (object_type, object_id, revision);
CREATE TABLE IF NOT EXISTS experience_current (
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    PRIMARY KEY (object_type, object_id),
    FOREIGN KEY (object_type, revision_id)
      REFERENCES experience_revisions (object_type, revision_id)
);
CREATE TABLE IF NOT EXISTS experience_domain_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_revision_id TEXT NOT NULL,
    event_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experience_domain_events_aggregate
    ON experience_domain_events (aggregate_id, aggregate_revision_id);
CREATE TABLE IF NOT EXISTS experience_audit_events (
    audit_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_revision_id TEXT NOT NULL,
    audit_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experience_audit_events_target
    ON experience_audit_events (target_id, target_revision_id);
CREATE TABLE IF NOT EXISTS experience_outbox (
    outbox_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    object_json TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experience_outbox_status
    ON experience_outbox (status, available_at);
"""


class SQLiteExperienceRepository:
    """SQLite implementation with the same surface as the in-memory store."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SQLiteExperienceRepository":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _model_for(self, object_type: str) -> type[BaseModel]:
        try:
            return _MODEL_TYPES[object_type]
        except KeyError as exc:
            raise RepositoryError(f"unsupported experience object type: {object_type}") from exc

    def save(
        self,
        object_type: str,
        object_id: str,
        revision_id: str,
        value: T,
        *,
        current: bool = True,
    ) -> T:
        model = self._model_for(object_type)
        if not isinstance(value, model):
            raise RepositoryError(
                f"object type {object_type!r} expects {model.__name__}, got {type(value).__name__}"
            )
        meta = getattr(value, "meta", None)
        if meta is None:
            raise RepositoryError("experience revisions require immutable meta")
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO experience_revisions "
                    "(object_type, object_id, revision_id, revision, parent_revision_id, object_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        object_type,
                        object_id,
                        revision_id,
                        meta.revision,
                        meta.parent_revision_id,
                        value.model_dump_json(),
                        meta.created_at.isoformat(),
                    ),
                )
                if current:
                    self._conn.execute(
                        "INSERT INTO experience_current (object_type, object_id, revision_id) "
                        "VALUES (?, ?, ?) "
                        "ON CONFLICT(object_type, object_id) DO UPDATE SET revision_id=excluded.revision_id",
                        (object_type, object_id, revision_id),
                    )
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(f"revision already exists or current pointer is invalid: {revision_id}") from exc
        return value

    def get_revision(self, object_type: str, revision_id: str) -> Any | None:
        model = self._model_for(object_type)
        row = self._conn.execute(
            "SELECT object_json FROM experience_revisions WHERE object_type = ? AND revision_id = ?",
            (object_type, revision_id),
        ).fetchone()
        return model.model_validate_json(row[0]) if row else None

    def get_current(self, object_type: str, object_id: str) -> Any | None:
        row = self._conn.execute(
            "SELECT revision_id FROM experience_current WHERE object_type = ? AND object_id = ?",
            (object_type, object_id),
        ).fetchone()
        return self.get_revision(object_type, row[0]) if row else None

    def list_revisions(self, object_type: str, object_id: str | None = None) -> list[Any]:
        model = self._model_for(object_type)
        if object_id is None:
            rows = self._conn.execute(
                "SELECT object_json FROM experience_revisions WHERE object_type = ? ORDER BY revision",
                (object_type,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT object_json FROM experience_revisions WHERE object_type = ? AND object_id = ? ORDER BY revision",
                (object_type, object_id),
            ).fetchall()
        return [model.model_validate_json(row[0]) for row in rows]

    def set_current(self, object_type: str, object_id: str, revision_id: str) -> None:
        if self.get_revision(object_type, revision_id) is None:
            raise RepositoryError(f"unknown revision: {revision_id}")
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO experience_current (object_type, object_id, revision_id) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(object_type, object_id) DO UPDATE SET revision_id=excluded.revision_id",
                    (object_type, object_id, revision_id),
                )
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(f"current pointer update failed: {revision_id}") from exc

    def emit_domain(self, event: DomainEvent) -> None:
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO experience_domain_events "
                    "(event_id, event_type, aggregate_id, aggregate_revision_id, event_json) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (event.event_id, event.event_type, event.aggregate_id, event.aggregate_revision_id, event.model_dump_json()),
                )
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(f"domain event already exists: {event.event_id}") from exc

    def record_audit(self, event: AuditEvent) -> None:
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO experience_audit_events "
                    "(audit_id, action, target_id, target_revision_id, audit_json) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (event.audit_id, event.action, event.target_id, event.target_revision_id, event.model_dump_json()),
                )
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(f"audit event already exists: {event.audit_id}") from exc

    def enqueue_outbox(self, event: OutboxEvent) -> OutboxEvent:
        """Persist an outbox event idempotently by its domain event ID."""
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO experience_outbox (outbox_id,event_id,object_json,status,attempts,available_at) VALUES (?,?,?,?,?,?)",
                    (event.outbox_id, event.event_id, event.model_dump_json(), event.status, event.attempts, event.available_at.isoformat()),
                )
        except sqlite3.IntegrityError:
            existing = self._conn.execute("SELECT object_json FROM experience_outbox WHERE event_id = ?", (event.event_id,)).fetchone()
            if existing:
                return OutboxEvent.model_validate_json(existing[0])
            raise RepositoryError(f"outbox event already exists: {event.event_id}")
        return event

    def pending_outbox(self, *, limit: int = 100) -> list[OutboxEvent]:
        now = datetime.now(timezone.utc).isoformat()
        rows = self._conn.execute(
            "SELECT object_json FROM experience_outbox WHERE status IN ('pending','failed') AND available_at <= ? ORDER BY available_at LIMIT ?", (now, limit)
        ).fetchall()
        return [OutboxEvent.model_validate_json(row[0]) for row in rows]

    def update_outbox(self, event: OutboxEvent) -> OutboxEvent:
        with self._conn:
            result = self._conn.execute("UPDATE experience_outbox SET object_json=?, status=?, attempts=?, available_at=? WHERE outbox_id=?", (event.model_dump_json(), event.status, event.attempts, event.available_at.isoformat(), event.outbox_id))
            if result.rowcount != 1:
                raise RepositoryError(f"unknown outbox event: {event.event_id}")
        return event

    def save_command(
        self,
        object_type: str,
        object_id: str,
        revision_id: str,
        value: T,
        *,
        expected_revision: int | None = None,
        domain_events: tuple[DomainEvent, ...] = (),
        audit_events: tuple[AuditEvent, ...] = (),
        outbox_events: tuple[OutboxEvent, ...] = (),
    ) -> T:
        """Persist a revision, projections and side effects in one transaction."""
        model = self._model_for(object_type)
        if not isinstance(value, model):
            raise RepositoryError(f"object type {object_type!r} expects {model.__name__}")
        current = self.get_current(object_type, object_id)
        current_revision = getattr(getattr(current, "meta", None), "revision", None)
        if expected_revision is not None and current_revision != expected_revision:
            raise RepositoryError(f"revision conflict: expected {expected_revision}, current {current_revision}")
        meta = getattr(value, "meta", None)
        if meta is None:
            raise RepositoryError("experience revisions require immutable meta")
        try:
            with self._conn:
                self._conn.execute("INSERT INTO experience_revisions (object_type, object_id, revision_id, revision, parent_revision_id, object_json, created_at) VALUES (?,?,?,?,?,?,?)", (object_type, object_id, revision_id, meta.revision, meta.parent_revision_id, value.model_dump_json(), meta.created_at.isoformat()))
                self._conn.execute("INSERT INTO experience_current (object_type, object_id, revision_id) VALUES (?,?,?) ON CONFLICT(object_type, object_id) DO UPDATE SET revision_id=excluded.revision_id", (object_type, object_id, revision_id))
                for event in domain_events:
                    self._conn.execute("INSERT INTO experience_domain_events (event_id,event_type,aggregate_id,aggregate_revision_id,event_json) VALUES (?,?,?,?,?)", (event.event_id, event.event_type, event.aggregate_id, event.aggregate_revision_id, event.model_dump_json()))
                for event in audit_events:
                    self._conn.execute("INSERT INTO experience_audit_events (audit_id,action,target_id,target_revision_id,audit_json) VALUES (?,?,?,?,?)", (event.audit_id, event.action, event.target_id, event.target_revision_id, event.model_dump_json()))
                for event in outbox_events:
                    self._conn.execute("INSERT INTO experience_outbox (outbox_id,event_id,object_json,status,attempts,available_at) VALUES (?,?,?,?,?,?)", (event.outbox_id, event.event_id, event.model_dump_json(), event.status, event.attempts, event.available_at.isoformat()))
        except sqlite3.IntegrityError as exc:
            raise RepositoryError("atomic command failed; transaction rolled back") from exc
        return value

    @property
    def domain_events(self) -> list[DomainEvent]:
        rows = self._conn.execute(
            "SELECT event_json FROM experience_domain_events ORDER BY rowid"
        ).fetchall()
        return [DomainEvent.model_validate_json(row[0]) for row in rows]

    @property
    def audit_events(self) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT audit_json FROM experience_audit_events ORDER BY rowid"
        ).fetchall()
        return [AuditEvent.model_validate_json(row[0]) for row in rows]

    def current_revision_id(self, object_type: str, object_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT revision_id FROM experience_current WHERE object_type = ? AND object_id = ?",
            (object_type, object_id),
        ).fetchone()
        return row[0] if row else None
