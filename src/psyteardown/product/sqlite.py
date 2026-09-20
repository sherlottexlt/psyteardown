"""SQLite persistence adapter for Product Studio upper-domain revisions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypeVar

from psyteardown.experience.models import AuditEvent, DomainEvent
from psyteardown.product.models import RevisionImpact
from psyteardown.product.repositories import (
    ProductRepositoryError,
    ProductSnapshot,
    _stable_id,
    impact_key,
    model_for,
    validate_revision_chain,
    validate_snapshot_type,
)


T = TypeVar("T", bound=ProductSnapshot)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS product_revisions (
    object_type TEXT NOT NULL,
    project_id TEXT NOT NULL,
    object_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    parent_revision_id TEXT,
    object_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (object_type, revision_id),
    UNIQUE (object_type, object_id, revision)
);
CREATE INDEX IF NOT EXISTS idx_product_revisions_project
    ON product_revisions (project_id, object_type, object_id, revision);
CREATE TABLE IF NOT EXISTS product_current (
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    PRIMARY KEY (object_type, object_id),
    FOREIGN KEY (object_type, revision_id)
      REFERENCES product_revisions (object_type, revision_id)
);
CREATE INDEX IF NOT EXISTS idx_product_current_project
    ON product_current (project_id, object_type, object_id);
CREATE TABLE IF NOT EXISTS product_domain_events (
    event_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_revision_id TEXT NOT NULL,
    event_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_product_domain_events_project
    ON product_domain_events (project_id, aggregate_id, aggregate_revision_id);
CREATE TABLE IF NOT EXISTS product_audit_events (
    audit_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_revision_id TEXT NOT NULL,
    audit_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_product_audit_events_project
    ON product_audit_events (project_id, target_id, target_revision_id);
CREATE TABLE IF NOT EXISTS product_revision_impacts (
    project_id TEXT NOT NULL,
    changed_object_type TEXT NOT NULL,
    changed_object_id TEXT NOT NULL,
    changed_revision INTEGER NOT NULL,
    dependent_type TEXT NOT NULL,
    dependent_id TEXT NOT NULL,
    dependent_revision_id TEXT NOT NULL,
    impact_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (
      changed_object_type, changed_object_id, changed_revision,
      dependent_type, dependent_id, dependent_revision_id
    )
);
CREATE INDEX IF NOT EXISTS idx_product_impacts_project
    ON product_revision_impacts (project_id, dependent_type, dependent_id);
"""


class SQLiteProductRepository:
    """Product repository with command-level SQLite transactions."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SQLiteProductRepository":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def get_revision(self, object_type: str, revision_id: str) -> T | None:
        model = model_for(object_type)
        row = self._conn.execute(
            "SELECT object_json FROM product_revisions "
            "WHERE object_type = ? AND revision_id = ?",
            (object_type, revision_id),
        ).fetchone()
        return model.model_validate_json(row[0]) if row else None  # type: ignore[return-value]

    def get_current(self, object_type: str, object_id: str) -> T | None:
        model_for(object_type)
        row = self._conn.execute(
            "SELECT revision_id FROM product_current "
            "WHERE object_type = ? AND object_id = ?",
            (object_type, object_id),
        ).fetchone()
        return self.get_revision(object_type, row[0]) if row else None

    def list_current(
        self, object_type: str, *, project_id: str | None = None
    ) -> list[T]:
        model = model_for(object_type)
        if project_id is None:
            rows = self._conn.execute(
                "SELECT r.object_json FROM product_current c "
                "JOIN product_revisions r ON r.object_type=c.object_type "
                "AND r.revision_id=c.revision_id "
                "WHERE c.object_type=? ORDER BY c.object_id",
                (object_type,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT r.object_json FROM product_current c "
                "JOIN product_revisions r ON r.object_type=c.object_type "
                "AND r.revision_id=c.revision_id "
                "WHERE c.object_type=? AND c.project_id=? ORDER BY c.object_id",
                (object_type, project_id),
            ).fetchall()
        return [model.model_validate_json(row[0]) for row in rows]  # type: ignore[return-value]

    def list_revisions(self, object_type: str, object_id: str) -> list[T]:
        model = model_for(object_type)
        rows = self._conn.execute(
            "SELECT object_json FROM product_revisions "
            "WHERE object_type=? AND object_id=? ORDER BY revision",
            (object_type, object_id),
        ).fetchall()
        return [model.model_validate_json(row[0]) for row in rows]  # type: ignore[return-value]

    def current_revision_id(self, object_type: str, object_id: str) -> str | None:
        model_for(object_type)
        row = self._conn.execute(
            "SELECT revision_id FROM product_current "
            "WHERE object_type=? AND object_id=?",
            (object_type, object_id),
        ).fetchone()
        return row[0] if row else None

    def list_impacts(
        self, *, project_id: str | None = None
    ) -> list[RevisionImpact]:
        if project_id is None:
            rows = self._conn.execute(
                "SELECT impact_json FROM product_revision_impacts ORDER BY rowid"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT impact_json FROM product_revision_impacts "
                "WHERE project_id=? ORDER BY rowid",
                (project_id,),
            ).fetchall()
        return [RevisionImpact.model_validate_json(row[0]) for row in rows]

    @property
    def domain_events(self) -> list[DomainEvent]:
        rows = self._conn.execute(
            "SELECT event_json FROM product_domain_events ORDER BY rowid"
        ).fetchall()
        return [DomainEvent.model_validate_json(row[0]) for row in rows]

    @property
    def audit_events(self) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT audit_json FROM product_audit_events ORDER BY rowid"
        ).fetchall()
        return [AuditEvent.model_validate_json(row[0]) for row in rows]

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

        try:
            self._conn.execute("BEGIN IMMEDIATE")
            current_row = self._conn.execute(
                "SELECT r.object_json FROM product_current c "
                "JOIN product_revisions r ON r.object_type=c.object_type "
                "AND r.revision_id=c.revision_id "
                "WHERE c.object_type=? AND c.object_id=?",
                (object_type, object_id),
            ).fetchone()
            current = (
                model_for(object_type).model_validate_json(current_row[0])
                if current_row
                else None
            )
            validate_revision_chain(
                current, value, expected_revision=expected_revision
            )
            self._conn.execute(
                "INSERT INTO product_revisions "
                "(object_type,project_id,object_id,revision_id,revision,parent_revision_id,object_json,created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    object_type,
                    project_id,
                    object_id,
                    revision_id,
                    value.meta.revision,
                    value.meta.parent_revision_id,
                    value.model_dump_json(),
                    value.meta.created_at.isoformat(),
                ),
            )
            self._conn.execute(
                "INSERT INTO product_current (object_type,object_id,project_id,revision_id) "
                "VALUES (?,?,?,?) ON CONFLICT(object_type,object_id) DO UPDATE SET "
                "project_id=excluded.project_id,revision_id=excluded.revision_id",
                (object_type, object_id, project_id, revision_id),
            )
            for event in domain_events:
                self._conn.execute(
                    "INSERT INTO product_domain_events "
                    "(event_id,project_id,event_type,aggregate_id,aggregate_revision_id,event_json) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        event.event_id,
                        project_id,
                        event.event_type,
                        event.aggregate_id,
                        event.aggregate_revision_id,
                        event.model_dump_json(),
                    ),
                )
            for event in audit_events:
                self._conn.execute(
                    "INSERT INTO product_audit_events "
                    "(audit_id,project_id,action,target_id,target_revision_id,audit_json) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        event.audit_id,
                        project_id,
                        event.action,
                        event.target_id,
                        event.target_revision_id,
                        event.model_dump_json(),
                    ),
                )
            for impact in impacts:
                changed_type, changed_id, changed_revision, dependent_type, dependent_id, dependent_revision_id = impact_key(impact)
                self._conn.execute(
                    "INSERT INTO product_revision_impacts "
                    "(project_id,changed_object_type,changed_object_id,changed_revision,"
                    "dependent_type,dependent_id,dependent_revision_id,impact_json,recorded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        project_id,
                        changed_type,
                        changed_id,
                        changed_revision,
                        dependent_type,
                        dependent_id,
                        dependent_revision_id,
                        impact.model_dump_json(),
                        value.meta.created_at.isoformat(),
                    ),
                )
            self._conn.commit()
        except ProductRepositoryError:
            self._conn.rollback()
            raise
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            raise ProductRepositoryError(
                "atomic product command failed; transaction rolled back"
            ) from exc
        except Exception:
            self._conn.rollback()
            raise
        return value
