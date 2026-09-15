from psyteardown.experience.adapters import FakeDesignToolProvider, attach_design_tool_result, build_design_tool_request
from psyteardown.experience.scaffold import InitialDesignRequest, build_scaffold_brief
from psyteardown.experience.providers import ScaffoldDesignGenerator
from psyteardown.experience.rules import build_candidate
from psyteardown.experience.mobility import generate_initial_design_rules, create_progressive_design_model
def test_fake_provider_exposes_explicit_review_views_and_model_keeps_them_derived():
    source_brief = build_scaffold_brief(InitialDesignRequest(goal="support movement", target_segment="commuters", context="transit", criteria=[{"criterion_id": "control", "name": "Control", "operational_definition": "can stop"}]))
    candidate = build_candidate(ScaffoldDesignGenerator().generate(source_brief, count=1)[0], source_brief, actor="test", reason="import")
    rule_set = generate_initial_design_rules(source_brief.revision_id, source_brief.movement_scenarios)
    model = create_progressive_design_model(candidate, rule_set)
    request = build_design_tool_request(candidate, rule_set)
    result = FakeDesignToolProvider().generate(request)
    assert set(result.derived_review_views) == {"wearer_side", "underside_strap", "stop_control_access", "bystander_state_edge"}
    draft = attach_design_tool_result(model, result, confirmed=False)
    assert next(layer for layer in draft.layers if layer.layer == "render_assets").status == "missing"
    confirmed = attach_design_tool_result(model, result, confirmed=True)
    render_layer = next(layer for layer in confirmed.layers if layer.layer == "render_assets")
    assert set(result.derived_review_views.values()).issubset(render_layer.artifact_refs)
    assert set(result.asset_hashes) >= set(result.derived_review_views.values())
    assert all(len(value) == 64 for value in result.asset_hashes.values())
    assert any("Derived" in note or "derived" in note for note in result.declared_notes)
