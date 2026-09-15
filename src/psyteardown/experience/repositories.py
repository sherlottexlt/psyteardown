"""In-memory revision repository used by the first vertical slice."""

from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

from psyteardown.experience.models import AuditEvent, DomainEvent, OutboxEvent

T = TypeVar("T")


class RepositoryError(RuntimeError):
    """Repository lookup or optimistic-revision error."""


class InMemoryExperienceRepository:
    """Stores immutable snapshots and current pointers without persistence."""

    def __init__(self) -> None:
        self._objects: dict[str, dict[str, object]] = defaultdict(dict)
        self._current: dict[str, str] = {}
        self.domain_events: list[DomainEvent] = []
        self.audit_events: list[AuditEvent] = []
        self._outbox: dict[str, OutboxEvent] = {}

    def save(self, object_type: str, object_id: str, revision_id: str, value: T, *, current: bool = True) -> T:
        if revision_id in self._objects[object_type]:
            raise RepositoryError(f"revision already exists: {revision_id}")
        self._objects[object_type][revision_id] = value
        if current:
            self._current[f"{object_type}:{object_id}"] = revision_id
        return value

    def get_revision(self, object_type: str, revision_id: str) -> T | None:
        return self._objects.get(object_type, {}).get(revision_id)  # type: ignore[return-value]

    def get_current(self, object_type: str, object_id: str) -> T | None:
        revision_id = self._current.get(f"{object_type}:{object_id}")
        return self.get_revision(object_type, revision_id) if revision_id else None

    def list_revisions(self, object_type: str, object_id: str | None = None) -> list[T]:
        values = list(self._objects.get(object_type, {}).values())
        if object_id is None:
            return values  # type: ignore[return-value]
        # Aggregate identifier field names are not uniform (e.g. ``facts``
        # uses ``candidate_id`` and ``review`` uses ``review_item_id``).  Match
        # any top-level ``*_id`` field while excluding revision/meta links;
        # this keeps newly added governance aggregates queryable without a
        # brittle per-type allowlist.
        def belongs(value: object) -> bool:
            if getattr(value, "revision_id", None) == object_id:
                return True
            fields = getattr(type(value), "model_fields", {})
            for field in fields:
                if not field.endswith("_id") or field in {"revision_id", "parent_revision_id"}:
                    continue
                if getattr(value, field, None) == object_id:
                    return True
            return False

        return [value for value in values if belongs(value)]  # type: ignore[return-value]

    def set_current(self, object_type: str, object_id: str, revision_id: str) -> None:
        if revision_id not in self._objects.get(object_type, {}):
            raise RepositoryError(f"unknown revision: {revision_id}")
        self._current[f"{object_type}:{object_id}"] = revision_id

    def emit_domain(self, event: DomainEvent) -> None:
        self.domain_events.append(event)

    def record_audit(self, event: AuditEvent) -> None:
        self.audit_events.append(event)

    def current_revision_id(self, object_type: str, object_id: str) -> str | None:
        return self._current.get(f"{object_type}:{object_id}")

    def enqueue_outbox(self, event: OutboxEvent) -> OutboxEvent:
        return self._outbox.setdefault(event.event_id, event)

    def pending_outbox(self, *, limit: int = 100) -> list[OutboxEvent]:
        return [event for event in self._outbox.values() if event.status in {"pending", "failed"}][:limit]

    def update_outbox(self, event: OutboxEvent) -> OutboxEvent:
        if event.event_id not in self._outbox:
            raise RepositoryError(f"unknown outbox event: {event.event_id}")
        self._outbox[event.event_id] = event
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
        """Atomically apply a revision and its side effects in memory."""
        current = self.get_current(object_type, object_id)
        current_revision = getattr(getattr(current, "meta", None), "revision", None)
        if expected_revision is not None and current_revision != expected_revision:
            raise RepositoryError(f"revision conflict: expected {expected_revision}, current {current_revision}")
        if revision_id in self._objects.get(object_type, {}):
            raise RepositoryError(f"revision already exists: {revision_id}")
        # Validate duplicate event/outbox IDs before mutating any state.
        if any(event.event_id in {item.event_id for item in self.domain_events} for event in domain_events):
            raise RepositoryError("domain event already exists")
        if any(event.audit_id in {item.audit_id for item in self.audit_events} for event in audit_events):
            raise RepositoryError("audit event already exists")
        self.save(object_type, object_id, revision_id, value)
        self.domain_events.extend(domain_events)
        self.audit_events.extend(audit_events)
        for event in outbox_events:
            self.enqueue_outbox(event)
        return value
