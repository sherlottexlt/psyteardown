import json

from psyteardown.experience import (
    ExperienceApplicationService,
    InitialDesignRequest,
    SQLiteExperienceRepository,
    build_portfolio_case_study,
    generate_initial_design_batch,
    render_portfolio_markdown,
)
from psyteardown.experience.adapters import FakeDesignToolProvider, build_design_tool_request
from psyteardown.experience.iteration import apply_variable_patches_to_candidate
from psyteardown.experience.models import DesignVariableValue, PatchScope, RevisionMeta, VariablePatch


def _patch(variable_id: str, value: str, index: int) -> VariablePatch:
    return VariablePatch(
        patch_id=f"portfolio-patch-{index}",
        revision_id=f"portfolio-patch-{index}.r1",
        meta=RevisionMeta(revision=1, created_by="human", reason="portfolio test"),
        review_item_revision_id="review-portfolio.r1",
        variable_id=variable_id,
        operation="replace",
        to_value=DesignVariableValue(variable_id=variable_id, value_type="enum", normalized_value=value, display_value=value),
        scope=PatchScope(global_scope=True),
        enforcement="should",
        rationale="make the design change explicit",
        evidence_refs=("review-portfolio",),
        expected_effect="preserve a bounded stop path",
        risks=("requires prototype evidence",),
        verification="run the prototype validation protocol",
    )


def test_portfolio_projection_contains_evolution_state_machine_and_protocol(tmp_path):
    repository = SQLiteExperienceRepository(tmp_path / "case.db")
    request = InitialDesignRequest(
        goal="support movement", target_segment="commuters", context="crowded transit",
        criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}],
    )
    batch = generate_initial_design_batch(request, repository=repository)
    parent = batch.candidates[0]
    model = batch.progressive_models[0]
    patches = (_patch("wearable.body_placement", "dorsal wrist", 1), _patch("feedback.modality", "private_haptic", 2))
    service = ExperienceApplicationService(repository)
    child, child_model, _trace = service.apply_variable_patch_revision(parent, model, patches)
    rule_set = batch.design_rule_set
    design_request = build_design_tool_request(child, rule_set, patches=patches, parent_model_revision_id=model.revision_id)
    result = FakeDesignToolProvider().generate(design_request)
    service.attach_design_tool_result(child_model, result, request=design_request, confirmed=False)

    case = build_portfolio_case_study(
        batch.brief,
        repository.list_revisions("candidate"),
        repository.list_revisions("progressive_model"),
        repository.list_revisions("patch"),
        repository.list_revisions("design_tool_run"),
    )
    payload = json.loads(case.model_dump_json())
    assert payload["schema_version"] == "portfolio-case-study/v1"
    assert any(change["kind"] == "variable_patch" for change in payload["changes"])
    assert any(change["kind"] == "visual_asset" and change["status"] == "draft" for change in payload["changes"])
    assert len(payload["scenario_state_machine"]["transitions"]) >= 6
    assert len(payload["prototype_validation_protocol"]["measures"]) >= 5
    assert payload["executable_scenario_policy"]["decisions"]
    assert payload["executable_scenario_policy"]["out_of_scope"]
    markdown = render_portfolio_markdown(case)
    assert "Scenario state machine" in markdown
    assert "Prototype validation protocol" in markdown
    assert "does not validate dimensions" in markdown
    repository.close()
