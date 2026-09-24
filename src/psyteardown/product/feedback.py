"""B7 preview of delivered builds and explicit, consented preview feedback.

The preview reads only the ``build/`` entries of an integrity-checked B6
archive, so what the user sees is exactly what was delivered.  Feedback is
recorded only when the user writes it and grants the current consent version;
nothing is captured from the preview automatically (PS-O007).  Withdrawal
replaces the stored record with a tombstone, erasing the text.
"""

from __future__ import annotations

import hashlib
import re
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from psyteardown.experience.models import DomainStateError, RevisionMeta
from psyteardown.product.delivery import ProductDeliveryBundleService
from psyteardown.product.models import (
    PREVIEW_FEEDBACK_CONSENT_VERSION,
    PREVIEW_FEEDBACK_MAX_TEXT,
    PreviewFeedback,
    PreviewFeedbackAnchor,
    PreviewFeedbackConsent,
    WebProductGenerationContract,
)
from psyteardown.product.repositories import ProductRepositoryError


class PreviewFeedbackRepository(Protocol):
    def save_preview_feedback(
        self, feedback: PreviewFeedback, *, expected_revision: int | None
    ) -> PreviewFeedback: ...

    def get_preview_feedback(self, feedback_id: str) -> PreviewFeedback | None: ...

    def list_preview_feedback(
        self, *, project_id: str | None = None, bundle_id: str | None = None
    ) -> list[PreviewFeedback]: ...


class InMemoryPreviewFeedbackRepository:
    """Single-record-per-feedback adapter used by unit tests."""

    def __init__(self) -> None:
        self._feedback: dict[str, PreviewFeedback] = {}

    def save_preview_feedback(
        self, feedback: PreviewFeedback, *, expected_revision: int | None
    ) -> PreviewFeedback:
        current = self._feedback.get(feedback.feedback_id)
        _check_revision(current, feedback, expected_revision)
        self._feedback[feedback.feedback_id] = feedback
        return feedback

    def get_preview_feedback(self, feedback_id: str) -> PreviewFeedback | None:
        return self._feedback.get(feedback_id)

    def list_preview_feedback(
        self, *, project_id: str | None = None, bundle_id: str | None = None
    ) -> list[PreviewFeedback]:
        return sorted(
            [
                value
                for value in self._feedback.values()
                if (project_id is None or value.project_id == project_id)
                and (bundle_id is None or value.delivery_bundle_id == bundle_id)
            ],
            key=lambda item: (item.submitted_at, item.feedback_id),
        )


def _check_revision(
    current: PreviewFeedback | None, value: PreviewFeedback, expected_revision: int | None
) -> None:
    if current is None:
        if expected_revision is not None:
            raise ProductRepositoryError(f"revision conflict: expected {expected_revision}, current None")
        if value.meta.revision != 1:
            raise ProductRepositoryError("first preview feedback revision must be revision 1")
        return
    if expected_revision is None or current.meta.revision != expected_revision:
        raise ProductRepositoryError(
            f"revision conflict: expected {expected_revision}, current {current.meta.revision}"
        )
    if value.meta.revision != current.meta.revision + 1 or value.meta.parent_revision_id != current.revision_id:
        raise ProductRepositoryError("preview feedback revision must follow the current revision")


# Only static build output is previewable; anything else is refused rather
# than guessed.
_PREVIEW_MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}
# Vite's default base emits root-absolute asset URLs; the preview is mounted
# under an API path, so only the served copy of index.html is made relative.
_ROOT_ASSET_REFERENCE = re.compile(r'(\s(?:src|href)=")/(?!/)')


class ProductPreviewFeedbackService:
    def __init__(
        self,
        application,
        feedback_repository: PreviewFeedbackRepository,
        delivery_service: ProductDeliveryBundleService,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        self.application = application
        self.feedback_repository = feedback_repository
        self.delivery_service = delivery_service
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda prefix: f"{prefix}-{uuid4().hex}")

    def preview_file(self, project_id: str, bundle_id: str, path: str) -> tuple[bytes, str]:
        """Return one delivered build file and its media type after hash checks."""

        bundle = self.delivery_service.get_bundle(project_id, bundle_id)
        relative = path or "index.html"
        parts = relative.split("/")
        if "\\" in relative or any(part in {"", ".", ".."} for part in parts):
            raise DomainStateError(f"unknown preview file: {relative}")
        suffix = "." + parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
        media_type = _PREVIEW_MEDIA_TYPES.get(suffix)
        entry = next((item for item in bundle.files if item.path == f"build/{relative}"), None)
        if entry is None or media_type is None:
            raise DomainStateError(f"unknown preview file: {relative}")
        archive = self.delivery_service.archive_path(project_id, bundle_id)
        with zipfile.ZipFile(archive) as reader:
            data = reader.read(entry.path)
        if len(data) != entry.byte_count or hashlib.sha256(data).hexdigest() != entry.sha256:
            raise DomainStateError("preview file failed integrity validation")
        if relative == "index.html":
            data = _ROOT_ASSET_REFERENCE.sub(r"\1./", data.decode("utf-8")).encode("utf-8")
        return data, media_type

    def submit_feedback(
        self,
        *,
        project_id: str,
        bundle_id: str,
        screen_id: str,
        task_id: str | None,
        state_id: str | None,
        category: str,
        text: str,
        actor: str,
        consent_version: str,
        consent_granted: bool,
    ) -> PreviewFeedback:
        if not consent_granted or consent_version != PREVIEW_FEEDBACK_CONSENT_VERSION:
            raise DomainStateError(
                f"preview feedback requires explicit consent to policy {PREVIEW_FEEDBACK_CONSENT_VERSION}"
            )
        body = text.strip()
        if not body or len(body) > PREVIEW_FEEDBACK_MAX_TEXT:
            raise DomainStateError(f"preview feedback text must be 1-{PREVIEW_FEEDBACK_MAX_TEXT} characters")
        bundle = self.delivery_service.get_bundle(project_id, bundle_id)
        contract = self.application.repository.get_revision(
            "web_generation_contract", bundle.web_generation_contract_revision_id
        )
        if not isinstance(contract, WebProductGenerationContract):
            raise DomainStateError("preview feedback requires the bundle's Web generation contract revision")
        anchor = PreviewFeedbackAnchor(screen_id=screen_id, task_id=task_id, state_id=state_id)
        _validate_anchor(contract, anchor)
        now = self._now()
        feedback_id = self._id("preview-feedback")
        feedback = PreviewFeedback(
            feedback_id=feedback_id,
            revision_id=f"{feedback_id}.r1",
            meta=RevisionMeta(revision=1, created_at=now, created_by=actor, reason="Explicit preview feedback"),
            project_id=project_id,
            delivery_bundle_id=bundle.bundle_id,
            delivery_bundle_revision_id=bundle.revision_id,
            execution_job_revision_id=bundle.execution_job_revision_id,
            web_generation_contract_revision_id=bundle.web_generation_contract_revision_id,
            anchor=anchor,
            category=category,  # type: ignore[arg-type]
            text=body,
            submitted_by=actor,
            submitted_at=now,
            consent=PreviewFeedbackConsent(granted_by=actor, granted_at=now),
        )
        return self.feedback_repository.save_preview_feedback(feedback, expected_revision=None)

    def withdraw_feedback(
        self, *, project_id: str, feedback_id: str, actor: str, expected_revision: int
    ) -> PreviewFeedback:
        current = self.get_feedback(project_id, feedback_id)
        if current.submitted_by != actor:
            raise DomainStateError("preview feedback can only be withdrawn by its submitter")
        if current.status == "withdrawn":
            raise DomainStateError("preview feedback is already withdrawn")
        now = self._now()
        revision = current.meta.revision + 1
        tombstone = current.model_copy(
            update={
                "revision_id": f"{feedback_id}.r{revision}",
                "meta": RevisionMeta(
                    revision=revision,
                    parent_revision_id=current.revision_id,
                    created_at=now,
                    created_by=actor,
                    reason="Withdrawn by submitter; content erased",
                ),
                "status": "withdrawn",
                "category": None,
                "text": None,
                "withdrawn_at": now,
                "disposition": "pending",
            }
        )
        tombstone = PreviewFeedback.model_validate(tombstone.model_dump())
        return self.feedback_repository.save_preview_feedback(tombstone, expected_revision=expected_revision)

    def get_feedback(self, project_id: str, feedback_id: str) -> PreviewFeedback:
        feedback = self.feedback_repository.get_preview_feedback(feedback_id)
        if feedback is None or feedback.project_id != project_id:
            raise DomainStateError(f"unknown preview feedback: {feedback_id}")
        return feedback

    def list_feedback(self, project_id: str, *, bundle_id: str | None = None) -> tuple[PreviewFeedback, ...]:
        self.application.get_project_view(project_id)
        return tuple(self.feedback_repository.list_preview_feedback(project_id=project_id, bundle_id=bundle_id))

    def set_disposition(
        self,
        *,
        project_id: str,
        feedback_id: str,
        disposition: str,
        actor: str,
        reason: str,
        expected_revision: int,
    ) -> PreviewFeedback:
        """Record a human decision about how a report was handled (B8).

        Creating an iteration job never changes feedback; only this explicit
        command does, and the text stays withdrawable afterwards.
        """

        current = self.get_feedback(project_id, feedback_id)
        if current.status != "submitted":
            raise DomainStateError("only submitted preview feedback can be given a disposition")
        if disposition not in {"pending", "incorporated", "deferred"}:
            raise DomainStateError(f"unknown preview feedback disposition: {disposition}")
        now = self._now()
        revision = current.meta.revision + 1
        updated = current.model_copy(
            update={
                "revision_id": f"{feedback_id}.r{revision}",
                "meta": RevisionMeta(
                    revision=revision,
                    parent_revision_id=current.revision_id,
                    created_at=now,
                    created_by=actor,
                    reason=reason,
                ),
                "disposition": disposition,
            }
        )
        updated = PreviewFeedback.model_validate(updated.model_dump())
        return self.feedback_repository.save_preview_feedback(updated, expected_revision=expected_revision)

    def _id(self, prefix: str) -> str:
        value = self._id_factory(prefix)
        if not value:
            raise ValueError("preview feedback identifier cannot be empty")
        return value

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("preview feedback clock must be timezone-aware")
        return value


def _validate_anchor(contract: WebProductGenerationContract, anchor: PreviewFeedbackAnchor) -> None:
    screen = next((item for item in contract.screens if item.screen_id == anchor.screen_id), None)
    if screen is None:
        raise DomainStateError("preview feedback anchor screen is not part of the bundle's contract revision")
    if anchor.task_id is not None and anchor.task_id not in screen.task_ids:
        raise DomainStateError("preview feedback anchor task is not part of the anchored screen")
    if anchor.state_id is not None and anchor.state_id not in screen.state_ids:
        raise DomainStateError("preview feedback anchor state is not part of the anchored screen")
