from pathlib import Path

import pytest

from psyteardown.experience import (
    DomainStateError,
    ExperienceApplicationService,
    ExternalAsset,
    InitialDesignRequest,
    ObservationDraft,
    SQLiteExperienceRepository,
    generate_initial_design_batch,
    build_external_asset,
)


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
