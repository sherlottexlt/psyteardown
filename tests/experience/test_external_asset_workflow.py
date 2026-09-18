from pathlib import Path

import pytest

from psyteardown.experience import (
    DomainStateError,
    ExperienceApplicationService,
    ExternalAsset,
    InitialDesignRequest,
    ObservationDraft,
    ImageRegion,
    VideoTimeSegment,
    SQLiteExperienceRepository,
    generate_initial_design_batch,
    build_external_asset,
)


def _candidate(repo):
    batch = generate_initial_design_batch(
        InitialDesignRequest(
            goal="test",
            target_segment="users",
            context="lab",
            criteria=[{
                "criterion_id": "control",
                "name": "Control",
                "operational_definition": "can stop",
            }],
        ),
        repository=repo,
    )
    return batch.candidates[0]


def test_external_asset_requires_manual_observation_confirmation(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        batch = generate_initial_design_batch(InitialDesignRequest(goal="test", target_segment="users", context="lab", criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}]), repository=repo)
        candidate = batch.candidates[0]
        service = ExperienceApplicationService(repo)
        asset = service.import_external_asset(ExternalAsset(
            asset_id="cad-1", revision_id="cad-1.r1", uri="device.glb", sha256="c" * 64,
            provider="cad-tool", asset_kind="glb", candidate_revision_id=candidate.candidate_revision_id,
        ))
        fact = candidate.declared_facts[0]
        draft = service.import_observation_draft(ObservationDraft(
            draft_id="draft-1", revision_id="draft-1.r1", asset_ids=(asset.asset_id,),
            candidate_revision_id=candidate.candidate_revision_id, source_fact_id=fact.fact_id,
            subject=fact.subject, predicate=fact.predicate, proposed_value=fact.value,
            method="manual visual inspection",
        ))
        with pytest.raises(DomainStateError):
            service.confirm_observation_draft(draft, confirmation="rejected")
        observation = service.confirm_observation_draft(draft)
        assert observation.provenance == "external_asset"
        assert repo.get_current("observation_draft", draft.draft_id).confirmation == "accepted"
        facts = service.freeze_facts_from_asset_observations(candidate, [observation.observation_id])
        assert facts.evidence_review_ids == ()
        assert any(dep.object_type == "observation_draft" for dep in facts.dependencies)
        assert any(dep.object_type == "external_asset" for dep in facts.dependencies)


def test_external_asset_builder_hashes_file_and_marks_blender_derived(tmp_path: Path):
    file_path = tmp_path / "render.glb"
    file_path.write_bytes(b"glb-bytes")
    asset = build_external_asset(file_path, provider="blender")
    assert asset.sha256
    assert asset.asset_kind == "glb"
    assert asset.provenance == "blender_derived"


def test_rejected_asset_observation_is_tracked_without_fact(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "case.db") as repo:
        batch = generate_initial_design_batch(InitialDesignRequest(goal="test", target_segment="users", context="lab", criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}]), repository=repo)
        candidate = batch.candidates[0]
        service = ExperienceApplicationService(repo)
        asset = service.import_external_asset(ExternalAsset(asset_id="cad-2", revision_id="cad-2.r1", uri="device.png", sha256="d" * 64, provider="manual", asset_kind="png", candidate_revision_id=candidate.candidate_revision_id))
        fact = candidate.declared_facts[0]
        draft = service.import_observation_draft(ObservationDraft(draft_id="draft-2", revision_id="draft-2.r1", asset_ids=(asset.asset_id,), candidate_revision_id=candidate.candidate_revision_id, source_fact_id=fact.fact_id, subject=fact.subject, predicate=fact.predicate, proposed_value=fact.value, method="visual inspection"))
        reviewed = service.review_observation_draft(draft, decision="rejected")
        assert reviewed.confirmation == "rejected"
        assert repo.list_revisions("confirmed_observation") == []


def test_video_observation_retains_time_segment_provenance(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "video.db") as repo:
        candidate = _candidate(repo)
        service = ExperienceApplicationService(repo)
        asset = service.import_external_asset(ExternalAsset(
            asset_id="video-1",
            revision_id="video-1.r1",
            uri="walkthrough.mp4",
            sha256="e" * 64,
            provider="manual",
            asset_kind="mp4",
            duration_ms=8_000,
            candidate_revision_id=candidate.candidate_revision_id,
        ))
        fact = candidate.declared_facts[0]
        draft = service.import_observation_draft(ObservationDraft(
            draft_id="video-draft",
            revision_id="video-draft.r1",
            asset_ids=(asset.asset_id,),
            candidate_revision_id=candidate.candidate_revision_id,
            source_fact_id=fact.fact_id,
            subject=fact.subject,
            predicate="indicator visibility changes during rotation",
            proposed_value="indicator is occluded after rotation",
            method="bounded video inspection",
            required_modalities=("video",),
            video_segment=VideoTimeSegment(start_ms=1_200, end_ms=2_400),
            claim_category="motion",
        ))
        observation = service.confirm_observation_draft(draft, actor="reviewer-li")
        assert observation.video_segment == VideoTimeSegment(start_ms=1_200, end_ms=2_400)
        assert "#time:1200-2400ms" in observation.source_locator
        assert observation.asset_ids == ("video-1",)


def test_missing_modality_downgrades_to_unknown_and_cannot_be_confirmed(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "missing.db") as repo:
        candidate = _candidate(repo)
        service = ExperienceApplicationService(repo)
        image = service.import_external_asset(ExternalAsset(
            asset_id="image-only",
            revision_id="image-only.r1",
            uri="front.png",
            sha256="f" * 64,
            provider="manual",
            asset_kind="png",
            candidate_revision_id=candidate.candidate_revision_id,
        ))
        fact = candidate.declared_facts[0]
        draft = service.import_observation_draft(ObservationDraft(
            draft_id="missing-video",
            revision_id="missing-video.r1",
            asset_ids=(image.asset_id,),
            candidate_revision_id=candidate.candidate_revision_id,
            source_fact_id=fact.fact_id,
            subject=fact.subject,
            predicate=fact.predicate,
            proposed_value=fact.value,
            method="multimodal inspection",
            required_modalities=("image", "video"),
        ))
        assert draft.observable_status == "unknown"
        assert draft.missing_modalities == ("video",)
        with pytest.raises(DomainStateError, match="required_modality_missing"):
            service.confirm_observation_draft(draft, actor="reviewer-li")


@pytest.mark.parametrize("claim_category", ["pressure", "strength", "comfort"])
def test_design_media_cannot_establish_physical_or_comfort_claims(tmp_path: Path, claim_category: str):
    with SQLiteExperienceRepository(tmp_path / f"{claim_category}.db") as repo:
        candidate = _candidate(repo)
        service = ExperienceApplicationService(repo)
        image = service.import_external_asset(ExternalAsset(
            asset_id=f"{claim_category}-image",
            revision_id=f"{claim_category}-image.r1",
            uri="wear.png",
            sha256="a" * 64,
            provider="manual",
            asset_kind="png",
            candidate_revision_id=candidate.candidate_revision_id,
        ))
        fact = candidate.declared_facts[0]
        draft = service.import_observation_draft(ObservationDraft(
            draft_id=f"{claim_category}-draft",
            revision_id=f"{claim_category}-draft.r1",
            asset_ids=(image.asset_id,),
            candidate_revision_id=candidate.candidate_revision_id,
            source_fact_id=fact.fact_id,
            subject=fact.subject,
            predicate=f"{claim_category} assessment",
            proposed_value="passes",
            method="visual inspection",
            image_region=ImageRegion(x=0.1, y=0.1, width=0.5, height=0.5),
            claim_category=claim_category,
        ))
        with pytest.raises(DomainStateError, match=f"cannot_establish_{claim_category}"):
            service.confirm_observation_draft(draft, actor="reviewer-li")


def test_uncalibrated_image_cannot_establish_dimensions_but_calibrated_image_can(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "dimension.db") as repo:
        candidate = _candidate(repo)
        service = ExperienceApplicationService(repo)
        fact = candidate.declared_facts[0]
        uncalibrated = service.import_external_asset(ExternalAsset(
            asset_id="uncalibrated",
            revision_id="uncalibrated.r1",
            uri="top.png",
            sha256="b" * 64,
            provider="manual",
            asset_kind="png",
            candidate_revision_id=candidate.candidate_revision_id,
        ))
        rejected = service.import_observation_draft(ObservationDraft(
            draft_id="dimension-draft-1",
            revision_id="dimension-draft-1.r1",
            asset_ids=(uncalibrated.asset_id,),
            candidate_revision_id=candidate.candidate_revision_id,
            source_fact_id=fact.fact_id,
            subject=fact.subject,
            predicate="housing width",
            proposed_value="42 mm",
            method="image measurement",
            image_region=ImageRegion(x=10, y=10, width=100, height=50, coordinate_space="pixels"),
            claim_category="dimension",
        ))
        with pytest.raises(DomainStateError, match="uncalibrated_media"):
            service.confirm_observation_draft(rejected, actor="reviewer-li")

        calibrated = service.import_external_asset(ExternalAsset(
            asset_id="calibrated",
            revision_id="calibrated.r1",
            uri="top-calibrated.png",
            sha256="c" * 64,
            provider="manual",
            asset_kind="png",
            calibration_status="calibrated",
            calibration_ref="calibration-board-2026-09-17.r1",
            width_px=1000,
            height_px=800,
            candidate_revision_id=candidate.candidate_revision_id,
        ))
        accepted = service.import_observation_draft(rejected.model_copy(update={
            "draft_id": "dimension-draft-2",
            "revision_id": "dimension-draft-2.r1",
            "asset_ids": (calibrated.asset_id,),
        }))
        observation = service.confirm_observation_draft(accepted, actor="reviewer-li")
        assert observation.claim_category == "dimension"
        assert observation.calibration_refs == ("calibration-board-2026-09-17.r1",)
        assert "#region:10.0,10.0,100.0,50.0:pixels" in observation.source_locator
