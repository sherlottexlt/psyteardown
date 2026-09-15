from pathlib import Path

import pytest

from psyteardown.experience import (
    DomainStateError,
    EvidenceReview,
    ExperienceApplicationService,
    MeasurementObservation,
    PrototypeAsset,
    PrototypeRun,
    RevisionMeta,
    SQLiteExperienceRepository,
    default_transit_validation_protocol,
    build_portfolio_case_study,
)


def _meta(actor="test", reason="test"):
    return RevisionMeta(revision=1, created_by=actor, reason=reason)


def _run(*, assets=()):
    return PrototypeRun(
        run_id="run-1",
        revision_id="run-1.r1",
        meta=_meta(),
        protocol_id="transit-anchor-physical-validation",
        protocol_revision_id="v1",
        candidate_revision_id="candidate.r1",
        device_revision_id="device.r1",
        conditions=("walking",),
        participant_context="consented adults",
        context="lab proxy",
        source_assets=assets,
    )


def _observation(*, source_asset_ids=(), provenance="prototype_measurement", value=1):
    return MeasurementObservation(
        observation_id="obs-1",
        revision_id="obs-1.r1",
        meta=_meta(),
        run_id="run-1",
        measure_id="stop-path",
        metric="completion time",
        measurement_method="timed task",
        condition="walking",
        measured_value=value,
        unit="ms",
        source_asset_ids=source_asset_ids,
        provenance=provenance,
    )


def test_import_is_draft_and_human_review_creates_confirmed_revision(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        service = ExperienceApplicationService(repo)
        run = _run()
        service.import_prototype_run(run)
        imported = service.import_measurement_observation(_observation(), run=run)
        assert imported.status == "draft"
        review = service.confirm_measurement_observations(run, ["obs-1"])
        assert review.evidence_level_after == "observed"
        assert repo.get_current("measurement_observation", "obs-1").status == "confirmed"
        assert len(repo.list_revisions("measurement_observation", "obs-1")) == 2


def test_observation_must_use_registered_run_condition(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        service = ExperienceApplicationService(repo)
        run = _run()
        service.import_prototype_run(run)
        with pytest.raises(DomainStateError, match="condition is not registered"):
            service.import_measurement_observation(_observation().model_copy(update={"condition": "unregistered"}), run=run)


def test_run_keeps_preregistered_protocol_snapshot(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        service = ExperienceApplicationService(repo)
        protocol = default_transit_validation_protocol()
        run = _run().model_copy(update={"protocol_id": protocol.protocol_id, "protocol_revision": protocol.protocol_revision})
        imported = service.import_prototype_run(run, protocol=protocol)
        assert imported.protocol_snapshot["protocol_id"] == protocol.protocol_id
        assert repo.get_current("prototype_run", run.run_id).protocol_snapshot["protocol_revision"] == protocol.protocol_revision


def test_blender_asset_is_forced_derived_and_cannot_promote(tmp_path: Path):
    asset = PrototypeAsset(
        asset_id="render-1",
        uri="render.glb",
        sha256="a" * 64,
        provider="blender",
        provenance="blender_derived",
    )
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        service = ExperienceApplicationService(repo)
        run = _run(assets=(asset,))
        service.import_prototype_run(run)
        imported = service.import_measurement_observation(_observation(source_asset_ids=(asset.asset_id,)), run=run)
        assert imported.provenance == "blender_derived"
        with pytest.raises(DomainStateError, match="Blender/design-derived"):
            service.confirm_measurement_observations(run, [imported.observation_id])


def test_failed_or_missing_observation_cannot_be_confirmed(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        service = ExperienceApplicationService(repo)
        run = _run()
        service.import_prototype_run(run)
        failed = _observation(value=None).model_copy(
            update={"status": "technical_failure", "missing_reason": "technical_failure", "technical_failure_reason": "sensor disconnected"}
        )
        service.import_measurement_observation(failed, run=run)
        with pytest.raises(DomainStateError, match="only measured draft"):
            service.confirm_measurement_observations(run, [failed.observation_id])


def test_blender_run_does_not_change_portfolio_protocol_status(tmp_path: Path):
    asset = PrototypeAsset(asset_id="render-1", uri="render.glb", sha256="b" * 64, provider="blender", provenance="blender_derived")
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        service = ExperienceApplicationService(repo)
        run = _run(assets=(asset,))
        service.import_prototype_run(run)
        imported = service.import_measurement_observation(_observation(source_asset_ids=(asset.asset_id,)), run=run)
        case = build_portfolio_case_study(
            # Portfolio projection only needs a brief/candidate lineage; use
            # a minimal fake object for this focused workflow assertion.
            type("Brief", (), {"revision_id": "brief.r1", "goal": "test", "scenario_ids": ("s",)})(),
            [type("Candidate", (), {"candidate_revision_id": "candidate.r1", "parent_candidate_revision_id": None, "meta": type("Meta", (), {"created_at": imported.meta.created_at})(), "design": None, "shape": None, "variables": (), "unknowns": (), "name": "candidate", "description": "candidate"})()],
            [], [], [],
            prototype_runs=[run], observations=[imported], evidence_reviews=[],
        )
        assert case.prototype_validation_protocol.status == "planned"
        assert case.evidence_workflow["blender_is_not_evidence"] is True
