"""Repository contract and in-memory adapter for Product Studio aggregates."""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol, TypeVar

from psyteardown.experience.models import AuditEvent, DomainEvent
from psyteardown.product.models import (
    OutcomeContract,
    ProblemModel,
    ProductIntent,
    ProductProject,
    ProductThesis,
    RevisionImpact,
)


ProductSnapshot = ProductProject | ProductIntent | ProblemModel | OutcomeContract | ProductThesis
T = TypeVar("T", bound=ProductSnapshot)


PRODUCT_MODEL_TYPES: dict[str, type[ProductSnapshot]] = {
    "product_project": ProductProject,
    "product_intent": ProductIntent,
    "problem_model": ProblemModel,
    "outcome_contract": OutcomeContract,
    "product_thesis": ProductThesis,
}


class ProductRepositoryError(RuntimeError):
    """Repository lookup, revision-chain, or optimistic-concurrency error."""


class ProductRepository(Protocol):
    def save_command(
        self,
        object_type: str,
        object_id: str,
        revision_id: str,
        value: T,
        *,
        project_id: str,
        expected_revision: int | None,
        domain_events: tuple[DomainEvent, ...] = (),
        audit_events: tuple[AuditEvent, ...] = (),
        impacts: tuple[RevisionImpact, ...] = (),
    ) -> T: ...

    def get_revision(self, object_type: str, revision_id: str) -> T | None: ...

    def get_current(self, object_type: str, object_id: str) -> T | None: ...

    def list_current(self, object_type: str, *, project_id: str | None = None) -> list[T]: ...

    def list_revisions(self, object_type: str, object_id: str) -> list[T]: ...

    def list_impacts(self, *, project_id: str | None = None) -> list[RevisionImpact]: ...

    @property
    def domain_events(self) -> list[DomainEvent]: ...

    @property
    def audit_events(self) -> list[AuditEvent]: ...


def model_for(object_type: str) -> type[ProductSnapshot]:
    try:
        return PRODUCT_MODEL_TYPES[object_type]
    except KeyError as exc:
        raise ProductRepositoryError(
            f"unsupported product object type: {object_type}"
        ) from exc


def validate_snapshot_type(
    object_type: str, value: ProductSnapshot, *, project_id: str
) -> None:
    model = model_for(object_type)
    if not isinstance(value, model):
        raise ProductRepositoryError(
            f"object type {object_type!r} expects {model.__name__}, "
            f"got {type(value).__name__}"
        )
    if value.project_id != project_id:
        raise ProductRepositoryError(
            f"snapshot project {value.project_id!r} does not match command project {project_id!r}"
        )


def validate_revision_chain(
    current: ProductSnapshot | None,
    value: ProductSnapshot,
    *,
    expected_revision: int | None,
) -> None:
    if current is None:
        if expected_revision is not None:
            raise ProductRepositoryError(
                f"revision conflict: expected {expected_revision}, current None"
            )
        if value.meta.revision != 1 or value.meta.parent_revision_id is not None:
            raise ProductRepositoryError(
                "first aggregate revision must be revision 1 without a parent"
            )
        return

    if expected_revision is None:
        raise ProductRepositoryError("expected_revision is required for an existing aggregate")
    if current.meta.revision != expected_revision:
        raise ProductRepositoryError(
            f"revision conflict: expected {expected_revision}, current {current.meta.revision}"
        )
    if value.meta.revision != current.meta.revision + 1:
        raise ProductRepositoryError("revision numbers must increase by exactly one")
    if value.meta.parent_revision_id != current.revision_id:
        raise ProductRepositoryError("new revision must reference the current revision as parent")


def impact_key(impact: RevisionImpact) -> tuple[object, ...]:
    changed = impact.changed_dependency
    return (
        changed.object_type,
        changed.object_id,
        changed.revision,
        impact.dependent_type,
        impact.dependent_id,
        impact.dependent_revision_id,
    )


class InMemoryProductRepository:
    """Atomic in-memory adapter used by domain/application tests."""

    def __init__(self) -> None:
        self._objects: dict[str, dict[str, ProductSnapshot]] = defaultdict(dict)
        self._current: dict[tuple[str, str], str] = {}
        self._domain_events: list[DomainEvent] = []
        self._audit_events: list[AuditEvent] = []
        self._impacts: list[tuple[str, RevisionImpact]] = []

    def get_revision(self, object_type: str, revision_id: str) -> T | None:
        model_for(object_type)
        return self._objects.get(object_type, {}).get(revision_id)  # type: ignore[return-value]

    def get_current(self, object_type: str, object_id: str) -> T | None:
        model_for(object_type)
        revision_id = self._current.get((object_type, object_id))
        return self.get_revision(object_type, revision_id) if revision_id else None

    def list_current(
        self, object_type: str, *, project_id: str | None = None
    ) -> list[T]:
        model_for(object_type)
        values: list[ProductSnapshot] = []
        for (candidate_type, object_id), revision_id in self._current.items():
            if candidate_type != object_type:
                continue
            value = self._objects[candidate_type][revision_id]
            if project_id is None or value.project_id == project_id:
                values.append(value)
        return sorted(values, key=lambda item: _stable_id(item))  # type: ignore[return-value]

    def list_revisions(self, object_type: str, object_id: str) -> list[T]:
        model_for(object_type)
        values = [
            value
            for value in self._objects.get(object_type, {}).values()
            if _stable_id(value) == object_id
        ]
        return sorted(values, key=lambda item: item.meta.revision)  # type: ignore[return-value]

    def current_revision_id(self, object_type: str, object_id: str) -> str | None:
        model_for(object_type)
        return self._current.get((object_type, object_id))

    def list_impacts(
        self, *, project_id: str | None = None
    ) -> list[RevisionImpact]:
        return [
            impact
            for stored_project_id, impact in self._impacts
            if project_id is None or stored_project_id == project_id
        ]

    @property
    def domain_events(self) -> list[DomainEvent]:
        return list(self._domain_events)

    @property
    def audit_events(self) -> list[AuditEvent]:
        return list(self._audit_events)

    def save_command(
        self,
        object_type: str,
        object_id: str,
        revision_id: str,
        value: T,
        *,
        project_id: str,
        expected_revision: int | None,
        domain_events: tuple[DomainEvent, ...] = (),
        audit_events: tuple[AuditEvent, ...] = (),
        impacts: tuple[RevisionImpact, ...] = (),
    ) -> T:
        validate_snapshot_type(object_type, value, project_id=project_id)
        if revision_id != value.revision_id:
            raise ProductRepositoryError("revision_id does not match snapshot")
        if object_id != _stable_id(value):
            raise ProductRepositoryError("object_id does not match snapshot stable identity")
        current = self.get_current(object_type, object_id)
        validate_revision_chain(current, value, expected_revision=expected_revision)

        if revision_id in self._objects.get(object_type, {}):
            raise ProductRepositoryError(f"revision already exists: {revision_id}")
        existing_domain_ids = {event.event_id for event in self._domain_events}
        if any(event.event_id in existing_domain_ids for event in domain_events):
            raise ProductRepositoryError("domain event already exists")
        if len({event.event_id for event in domain_events}) != len(domain_events):
            raise ProductRepositoryError("command contains duplicate domain event IDs")
        existing_audit_ids = {event.audit_id for event in self._audit_events}
        if any(event.audit_id in existing_audit_ids for event in audit_events):
            raise ProductRepositoryError("audit event already exists")
        if len({event.audit_id for event in audit_events}) != len(audit_events):
            raise ProductRepositoryError("command contains duplicate audit event IDs")
        existing_impact_keys = {impact_key(impact) for _, impact in self._impacts}
        new_impact_keys = [impact_key(impact) for impact in impacts]
        if any(key in existing_impact_keys for key in new_impact_keys) or len(
            set(new_impact_keys)
        ) != len(new_impact_keys):
            raise ProductRepositoryError("revision impact already exists")

        # All validation happens before these mutations, making one command
        # all-or-nothing in the in-memory adapter as well.
        self._objects[object_type][revision_id] = value
        self._current[(object_type, object_id)] = revision_id
        self._domain_events.extend(domain_events)
        self._audit_events.extend(audit_events)
        self._impacts.extend((project_id, impact) for impact in impacts)
        return value


def _stable_id(value: ProductSnapshot) -> str:
    if isinstance(value, ProductProject):
        return value.project_id
    if isinstance(value, ProductIntent):
        return value.intent_id
    if isinstance(value, ProblemModel):
        return value.problem_model_id
    if isinstance(value, OutcomeContract):
        return value.outcome_contract_id
    return value.thesis_id
