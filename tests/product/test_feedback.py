from datetime import datetime, timezone

import pytest

from psyteardown.experience.models import DomainStateError
from psyteardown.product import (
    PREVIEW_FEEDBACK_CONSENT_VERSION,
    InMemoryPreviewFeedbackRepository,
    ProductPreviewFeedbackService,
    ProductRepositoryError,
    SQLiteProductRepository,
)
from .test_delivery import SequenceIds, _delivery_service, _executed


NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _bundle_setup(tmp_path, repository=None):
    execution_service, project, _, executed = _executed(tmp_path)
    delivery = _delivery_service(tmp_path, execution_service)
    bundle = delivery.create_bundle(
        project_id=project.project_id, execution_job_id=executed.job_id, actor="user", reason="deliver"
    )
    service = ProductPreviewFeedbackService(
        execution_service.application,
        repository or InMemoryPreviewFeedbackRepository(),
        delivery,
        clock=lambda: NOW,
        id_factory=SequenceIds(),
    )
    contract = execution_service.application.get_project_view(project.project_id).web_generation_contract
    return service, project, bundle, contract


def _submit(service, project, bundle, contract, **overrides):
    screen = contract.screens[0]
    values = dict(
        project_id=project.project_id,
        bundle_id=bundle.bundle_id,
        screen_id=screen.screen_id,
        task_id=screen.task_ids[0],
        state_id=screen.state_ids[0],
        category="confusing",
        text="  The urgent-contact option is hard to find.  ",
        actor="user-li",
        consent_version=PREVIEW_FEEDBACK_CONSENT_VERSION,
        consent_granted=True,
    )
    values.update(overrides)
    return service.submit_feedback(**values)


def test_preview_serves_only_hash_checked_build_files(tmp_path):
    service, project, bundle, _ = _bundle_setup(tmp_path)

    index, media_type = service.preview_file(project.project_id, bundle.bundle_id, "")
    assert media_type.startswith("text/html")
    assert b"<div id=root>" in index
    script, script_type = service.preview_file(project.project_id, bundle.bundle_id, "assets/index.js")
    assert script.startswith(b"console.log('built');")
    assert script_type.startswith("text/javascript")

    for path in ("../source/package.json", "DELIVERY.md", "assets//index.js", "assets\\index.js", "missing.js"):
        with pytest.raises(DomainStateError, match="unknown preview file"):
            service.preview_file(project.project_id, bundle.bundle_id, path)

    archive = tmp_path / "exports" / f"{bundle.archive_sha256}.zip"
    archive.write_bytes(b"tampered")
    with pytest.raises(DomainStateError, match="integrity"):
        service.preview_file(project.project_id, bundle.bundle_id, "index.html")


def test_preview_rewrites_root_asset_references_only_in_served_index(tmp_path):
    from psyteardown.product.feedback import _ROOT_ASSET_REFERENCE

    html = '<script type="module" crossorigin src="/assets/a.js"></script><link rel="stylesheet" href="/assets/a.css"><a href="//cdn">'
    assert _ROOT_ASSET_REFERENCE.sub(r"\1./", html) == (
        '<script type="module" crossorigin src="./assets/a.js"></script>'
        '<link rel="stylesheet" href="./assets/a.css"><a href="//cdn">'
    )


def test_feedback_is_anchored_to_bundle_and_contract_revisions(tmp_path):
    service, project, bundle, contract = _bundle_setup(tmp_path)
    feedback = _submit(service, project, bundle, contract)

    assert feedback.revision_id == f"{feedback.feedback_id}.r1"
    assert feedback.delivery_bundle_revision_id == bundle.revision_id
    assert feedback.execution_job_revision_id == bundle.execution_job_revision_id
    assert feedback.web_generation_contract_revision_id == contract.revision_id
    assert feedback.anchor.screen_id == contract.screens[0].screen_id
    assert feedback.text == "The urgent-contact option is hard to find."
    assert feedback.evidence_level == "user_report"
    assert feedback.automatic_capture == "none"
    assert feedback.consent.version == PREVIEW_FEEDBACK_CONSENT_VERSION
    assert feedback.consent.granted_by == "user-li"
    assert service.list_feedback(project.project_id, bundle_id=bundle.bundle_id) == (feedback,)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"consent_granted": False}, "explicit consent"),
        ({"consent_version": "b7-explicit-v0"}, "explicit consent"),
        ({"text": "   "}, "text"),
        ({"screen_id": "screen-not-in-contract"}, "screen"),
        ({"task_id": "task-not-on-screen"}, "task"),
        ({"state_id": "state-not-on-screen"}, "state"),
        ({"bundle_id": "delivery-bundle-missing"}, "unknown product delivery bundle"),
    ],
)
def test_feedback_gates_reject_without_writing(tmp_path, overrides, message):
    service, project, bundle, contract = _bundle_setup(tmp_path)
    with pytest.raises(DomainStateError, match=message):
        _submit(service, project, bundle, contract, **overrides)
    assert service.list_feedback(project.project_id) == ()


def test_withdrawal_erases_content_and_is_limited_to_submitter(tmp_path):
    service, project, bundle, contract = _bundle_setup(tmp_path)
    feedback = _submit(service, project, bundle, contract)

    with pytest.raises(DomainStateError, match="submitter"):
        service.withdraw_feedback(
            project_id=project.project_id, feedback_id=feedback.feedback_id, actor="someone-else", expected_revision=1
        )
    with pytest.raises(ProductRepositoryError, match="revision conflict"):
        service.withdraw_feedback(
            project_id=project.project_id, feedback_id=feedback.feedback_id, actor="user-li", expected_revision=2
        )
    withdrawn = service.withdraw_feedback(
        project_id=project.project_id, feedback_id=feedback.feedback_id, actor="user-li", expected_revision=1
    )
    assert withdrawn.status == "withdrawn"
    assert withdrawn.revision_id == f"{feedback.feedback_id}.r2"
    assert withdrawn.meta.parent_revision_id == feedback.revision_id
    assert withdrawn.text is None and withdrawn.category is None
    assert withdrawn.anchor == feedback.anchor
    assert service.get_feedback(project.project_id, feedback.feedback_id) == withdrawn
    with pytest.raises(DomainStateError, match="already withdrawn"):
        service.withdraw_feedback(
            project_id=project.project_id, feedback_id=feedback.feedback_id, actor="user-li", expected_revision=2
        )
    with pytest.raises(DomainStateError, match="unknown preview feedback"):
        service.get_feedback("other-project", feedback.feedback_id)


def test_sqlite_withdrawal_leaves_no_text_in_database_file(tmp_path):
    database = tmp_path / "product.sqlite3"
    repository = SQLiteProductRepository(database)
    try:
        service, project, bundle, contract = _bundle_setup(tmp_path, repository)
        secret = "distinctive-withdrawn-phrase-7f3a"
        kept = _submit(service, project, bundle, contract, text="This one stays.")
        feedback = _submit(service, project, bundle, contract, text=secret)
        assert secret.encode() in database.read_bytes()

        service.withdraw_feedback(
            project_id=project.project_id, feedback_id=feedback.feedback_id, actor="user-li", expected_revision=1
        )
        assert secret.encode() not in database.read_bytes()
    finally:
        repository.close()

    reopened = SQLiteProductRepository(database)
    try:
        listed = reopened.list_preview_feedback(project_id=project.project_id, bundle_id=bundle.bundle_id)
        assert [item.feedback_id for item in listed] == [kept.feedback_id, feedback.feedback_id]
        assert listed[0].text == "This one stays."
        assert listed[1].status == "withdrawn" and listed[1].text is None
        with pytest.raises(ProductRepositoryError, match="revision conflict"):
            reopened.save_preview_feedback(listed[1], expected_revision=1)
        with pytest.raises(ProductRepositoryError):
            reopened.save_preview_feedback(kept, expected_revision=None)
    finally:
        reopened.close()
