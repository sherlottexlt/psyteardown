import json

from psyteardown.experience import (
    DesignVariableValue,
    PatchScope,
    RevisionMeta,
    VariablePatch,
    apply_variable_patches_to_candidate,
    build_design_tool_request,
    create_progressive_design_model,
    generate_initial_design_batch,
    ExperienceApplicationService,
    InMemoryExperienceRepository,
    build_patchable_variable_catalog,
)


def _patch(variable_id: str, value: str) -> VariablePatch:
    return VariablePatch(
        patch_id=f"p-{variable_id}",
        revision_id=f"p-{variable_id}.r1",
        meta=RevisionMeta(revision=1, created_by="human", reason="ergonomic review"),
        review_item_revision_id="review-ergonomic.r1",
        variable_id=variable_id,
        operation="replace",
        to_value=DesignVariableValue(variable_id=variable_id, value_type="enum", normalized_value=value, display_value=value),
        scope=PatchScope(global_scope=True),
        enforcement="should",
        rationale="reduce snag and interruption risk",
        evidence_refs=("movement-rule",),
        expected_effect="improve one-handed control",
        risks=("requires prototype evidence",),
        verification="measure slip, false activation and haptic detection",
    )


def test_parameterized_wrist_revision_changes_declared_shape_and_scene_spec():
    batch = generate_initial_design_batch(
        __import__("psyteardown.experience", fromlist=["InitialDesignRequest"]).InitialDesignRequest(
            goal="support movement", target_segment="commuters", context="crowded transit",
            criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}],
        )
    )
    parent = batch.candidates[0]
    patches = (
        _patch("wearable.body_placement", "dorsal wrist"),
        _patch("wearable.attachment_strategy", "broad vented strap"),
        _patch("control.cancel_action", "recessed press-hold"),
    )
    child = apply_variable_patches_to_candidate(parent, patches)
    assert child.parent_candidate_revision_id == parent.candidate_revision_id
    assert child.candidate_revision_id != parent.candidate_revision_id
    assert child.shape.body_placement == "dorsal wrist"
    assert "cancel" in child.shape.interaction_surface
    request = build_design_tool_request(child, batch.design_rule_set, patches=patches, parent_model_revision_id=batch.progressive_models[0].revision_id)
    assert request.patch_revision_ids == [p.revision_id for p in patches]
    assert request.parent_model_revision_id == batch.progressive_models[0].revision_id
    assert request.scene_spec["ergonomic_intent"]["body_placement"] == "dorsal wrist"
    assert request.scene_spec["geometry"]["wearer_facing_status"] is True
    assert request.scene_spec["variables"]["wearable.body_placement"] == "dorsal wrist"


def test_parameterized_model_resets_stale_assets_and_keeps_lineage():
    batch = generate_initial_design_batch(
        __import__("psyteardown.experience", fromlist=["InitialDesignRequest"]).InitialDesignRequest(
            goal="support movement", target_segment="commuters", context="crowded transit",
            criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}],
        )
    )
    parent = batch.candidates[0]
    model = batch.progressive_models[0]
    patch = _patch("wearable.mass_distribution", "centered over wrist axis")
    child = apply_variable_patches_to_candidate(parent, (patch,))
    from psyteardown.experience import create_patched_progressive_model
    revision = create_patched_progressive_model(model, child, (patch,))
    assert revision.meta.parent_revision_id == model.revision_id
    assert revision.candidate_revision_id == child.candidate_revision_id
    assert revision.applied_patch_revision_ids == (patch.revision_id,)
    assert all(layer.status == "missing" for layer in revision.layers if layer.layer in {"render_assets", "geometry"})


def test_branching_from_same_parent_allocates_distinct_model_revisions():
    repository = InMemoryExperienceRepository()
    batch = generate_initial_design_batch(
        __import__("psyteardown.experience", fromlist=["InitialDesignRequest"]).InitialDesignRequest(
            goal="support movement", target_segment="commuters", context="crowded transit",
            criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}],
        ),
        repository=repository,
    )
    parent = batch.candidates[0]
    model = batch.progressive_models[0]
    service = ExperienceApplicationService(repository)
    first, _, _ = service.apply_variable_patch_revision(parent, model, (_patch("wearable.body_placement", "dorsal wrist"),))
    second, _, _ = service.apply_variable_patch_revision(parent, model, (_patch("wearable.contact_area", "broad underside"),))
    assert first.candidate_revision_id != second.candidate_revision_id
    revisions = [item.meta.revision for item in repository.list_revisions("progressive_model") if item.model_id == model.model_id]
    assert sorted(revisions)[-2:] == [2, 3]


def test_remove_patch_without_to_value_removes_optional_variable():
    batch = generate_initial_design_batch(
        __import__("psyteardown.experience", fromlist=["InitialDesignRequest"]).InitialDesignRequest(
            goal="support movement", target_segment="commuters", context="crowded transit",
            criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}],
        )
    )
    parent = batch.candidates[0]
    patch = _patch("wearable.body_placement", "dorsal wrist").model_copy(update={"operation": "remove", "to_value": None})
    child = apply_variable_patches_to_candidate(parent, (patch,))
    assert all(value.variable_id != "wearable.body_placement" for value in child.variables)


def test_patchable_variable_catalog_is_stable_and_serializable():
    catalog = build_patchable_variable_catalog()
    ids = [item["variable_id"] for item in catalog]
    assert ids[0] == "wearable.form_factor"
    assert "feedback.modality" in ids
    assert all(item["value_type"] == "enum" and item["examples"] for item in catalog)
