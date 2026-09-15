from psyteardown.experience.models import (
    DesignBrief,
    DesignCandidate,
    DivergenceMatrix,
    ExperienceCriterion,
    RevisionMeta,
)
from psyteardown.experience.mobility import (
    FutureMovementScenarioInput,
    MovementPhaseInput,
    build_movement_scenarios,
    create_progressive_design_model,
    generate_initial_design_rules,
)
from psyteardown.experience.providers import ScaffoldDesignGenerator
from psyteardown.experience.adapters import (
    BlenderDesignToolProvider,
    BlenderProviderError,
    DesignToolRequest,
    FakeDesignToolProvider,
    attach_design_tool_result,
    build_design_tool_request,
)


def test_blender_provider_reports_missing_executable(tmp_path):
    provider = BlenderDesignToolProvider(executable=tmp_path / "missing-blender", output_root=tmp_path / "blender")
    request = DesignToolRequest(candidate_revision_id="candidate.r1", prompt_projection="blockout")
    try:
        provider.generate(request)
    except BlenderProviderError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("missing Blender executable should fail explicitly")


def test_blender_provider_maps_headless_outputs(monkeypatch, tmp_path):
    import subprocess

    def fake_run(command, **kwargs):
        script = next(value for value in command if str(value).endswith("scene.py"))
        run_dir = __import__("pathlib").Path(script).parent
        (run_dir / "render-2d.png").write_bytes(b"png")
        (run_dir / "design.blend").write_bytes(b"blend")
        (run_dir / "design.glb").write_bytes(b"glb")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = BlenderDesignToolProvider(executable="blender", output_root=tmp_path / "blender")
    request = DesignToolRequest(candidate_revision_id="candidate.r1", prompt_projection="blockout", scene_spec={"form_factor": "wearable"})
    result = provider.generate(request)
    assert result.provider == "blender"
    assert result.render_asset_refs and result.render_asset_refs[0].endswith("render-2d.png")
    assert {path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for path in result.geometry_asset_refs} == {"design.blend", "design.glb"}
    assert "not validated" in " ".join(result.unknowns)


def scenario_inputs():
    return [
        FutureMovementScenarioInput(
            scenario_id="scenario-transit",
            name="Crowded transit transfer",
            narrative="The user exits a moving vehicle and crosses a public platform while carrying a bag.",
            phases=[
                MovementPhaseInput(
                    phase_id="transit-riding",
                    movement_state="transit_passenger",
                    posture="standing",
                    hands_available="none",
                    visual_attention="intermittent",
                    ambient_motion="high",
                    social_visibility="public",
                    device_relation="worn_wrist",
                    transition_to="transit-exit",
                    hazards=["crowded platform", "moving vehicle"],
                ),
                MovementPhaseInput(
                    phase_id="transit-exit",
                    movement_state="exiting_vehicle",
                    posture="walking_posture",
                    hands_available="intermittent",
                    visual_attention="intermittent",
                    ambient_motion="medium",
                    social_visibility="public",
                    device_relation="worn_wrist",
                    transition_from="transit-riding",
                ),
            ],
            task_goal="cross the platform safely without losing the current task",
            interruption_cost="high",
            recovery_cost="high",
            privacy_sensitivity="high",
        )
    ]


def brief():
    return DesignBrief(
        brief_id="brief-mobility",
        revision_id="brief-mobility.r1",
        meta=RevisionMeta(revision=1, created_by="test", reason="draft"),
        product_category="future wearable assistant",
        goal="support movement without stealing attention",
        target_segment="mobile professionals",
        researchability_confirmed=True,
        context="future movement",
        scenario_ids=("scenario-transit",),
        movement_scenarios=build_movement_scenarios(scenario_inputs()),
        criteria=(ExperienceCriterion(criterion_id="control", name="Control", operational_definition="can stop", desired_direction="higher", priority=1),),
        divergence_matrix=DivergenceMatrix(variable_ids=("feedback.modality",), strategy_directions=("quiet_control", "discoverable", "privacy_first")),
    )


def test_future_movement_scenario_projects_rules_for_motion_and_wearables():
    scenarios = build_movement_scenarios(scenario_inputs())
    rule_set = generate_initial_design_rules("brief-mobility.r1", scenarios)
    names = {rule.name for rule in rule_set.rules}
    assert "Hands-free primary control" in names
    assert "Non-visual primary feedback" in names
    assert "Motion-robust fit and activation" in names
    assert "Public-context privacy boundary" in names
    assert "Body-contact comfort remains unverified" in names
    assert "State continuity across movement transitions" in names
    assert all(rule.status == "candidate" for rule in rule_set.rules)
    assert all(rule.enforcement in {"consider_as_option", "validation_only"} for rule in rule_set.rules)


def test_design_tool_bridge_keeps_provider_output_as_untrusted_until_confirmation():
    generator = ScaffoldDesignGenerator()
    candidate_draft = generator.generate(brief(), count=1)[0]
    candidate = __import__("psyteardown.experience.rules", fromlist=["build_candidate"]).build_candidate(candidate_draft, brief(), actor="test", reason="import")
    rule_set = generate_initial_design_rules(brief().revision_id, brief().movement_scenarios)
    model = create_progressive_design_model(candidate, rule_set)
    request = build_design_tool_request(candidate, rule_set)
    provider = FakeDesignToolProvider()
    result = provider.generate(request)
    assert result.status == "draft"
    assert next(layer for layer in model.layers if layer.layer == "render_assets").status == "missing"
    draft_revision = attach_design_tool_result(model, result, confirmed=False)
    assert draft_revision.stage == "structured_design"
    assert any(layer.status == "missing" for layer in draft_revision.layers if layer.layer == "render_assets")
    confirmed_revision = attach_design_tool_result(model, result, confirmed=True, actor="human")
    assert confirmed_revision.stage == "geometry_ready"
    assert any(layer.status == "complete" for layer in confirmed_revision.layers if layer.layer == "geometry")
    assert result.result_id in confirmed_revision.provider_result_ids
