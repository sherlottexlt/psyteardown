import json

import pytest
from typer.testing import CliRunner

from psyteardown.experience import (
    DesignBrief,
    DivergenceMatrix,
    ExperienceCriterion,
    RevisionMeta,
    ScaffoldDesignGenerator,
    build_next_prompt,
    build_actionable_patches,
    critique_candidate,
    generate_candidates,
    rank_candidates,
    render_feedback_json,
    run_feedback_loop,
    select_feedback_candidate,
    ExperienceApplicationService,
    InMemoryExperienceRepository,
    ProhibitedExperience,
)
from psyteardown.cli import app


runner = CliRunner()


def brief():
    return DesignBrief(
        brief_id="m3-brief",
        revision_id="m3-brief.r1",
        meta=RevisionMeta(revision=1, created_by="test", reason="m3"),
        goal="reduce interruption",
        target_segment="commuters",
        researchability_confirmed=True,
        context="crowded transit",
        scenario_ids=("transit",),
        criteria=(ExperienceCriterion(
            criterion_id="control",
            name="Control",
            operational_definition="user can stop the intervention",
            desired_direction="higher",
            priority=1,
        ),),
        divergence_matrix=DivergenceMatrix(
            variable_ids=("feedback.modality",),
            strategy_directions=("quiet", "visible", "privacy_first"),
        ),
    )


def test_feedback_loop_is_deterministic_and_does_not_auto_select():
    result = run_feedback_loop(brief(), generator=ScaffoldDesignGenerator(), n=3)
    assert len(result.candidates) == 3
    assert len(result.critiques) == 3
    assert result.ranked_candidate_ids == tuple(sorted(result.ranked_candidate_ids))
    assert result.selected_candidate_id is None
    assert result.next_prompt is None
    payload = json.loads(render_feedback_json(result))
    assert len(payload["candidates"]) == 3
    assert payload["selected_candidate_id"] is None


@pytest.mark.parametrize("goal", ("reduce interruption", "recover from misclassification", "preserve private control"))
def test_three_task_feedback_batches_have_stable_five_candidate_rankings(goal):
    source = brief().model_copy(update={"goal": goal})
    first = run_feedback_loop(source, generator=ScaffoldDesignGenerator(), n=5)
    second = run_feedback_loop(source, generator=ScaffoldDesignGenerator(), n=5)
    assert first.ranked_candidate_ids == second.ranked_candidate_ids
    assert len(first.candidates) == 5
    assert first.selected_candidate_id is None


def test_hard_risk_candidate_is_rejected_by_m3_selection():
    source = brief().model_copy(update={
        "prohibited_experiences": (ProhibitedExperience(
            prohibition_id="no-private-haptic",
            operational_definition="private haptic",
            severity="hard",
            indicator="private haptic feedback",
            approved_rule_id="rule.no-private-haptic",
            release_condition="human remediation review",
        ),),
    })
    result = run_feedback_loop(source, generator=ScaffoldDesignGenerator(), n=5)
    assert any(item.hard_risks for item in result.critiques)
    hard_candidate = next(item.candidate_id for item in result.candidates if any(
        critique.candidate_id == item.candidate_id and critique.hard_risks
        for critique in result.critiques
    ))
    with pytest.raises(ValueError, match="hard-risk"):
        select_feedback_candidate(source, result, hard_candidate)


def test_critique_has_traceable_observations_hypotheses_and_actionable_changes():
    candidate = generate_candidates(brief(), generator=ScaffoldDesignGenerator(), n=1)[0]
    critique = critique_candidate(candidate, brief())
    assert critique.observation_ids
    assert critique.evidence_ids
    assert critique.hypotheses[0].alternative_explanations
    assert any("feedback." in change for change in critique.actionable_changes)


def test_human_selection_is_separate_and_builds_next_prompt():
    result = run_feedback_loop(brief(), generator=ScaffoldDesignGenerator(), n=3)
    selected = result.ranked_candidate_ids[0]
    updated = select_feedback_candidate(brief(), result, selected)
    assert updated.selected_candidate_id == selected
    prompt = json.loads(updated.next_prompt)
    selected_revision = next(item.candidate_revision_id for item in result.candidates if item.candidate_id == selected)
    assert prompt["parent_candidate_revision_id"] == selected_revision
    assert prompt["do_not_claim"]


def test_unknown_candidate_cannot_be_selected():
    result = run_feedback_loop(brief(), generator=ScaffoldDesignGenerator(), n=1)
    with pytest.raises(ValueError):
        select_feedback_candidate(brief(), result, "missing")


def test_selected_feedback_can_be_projected_to_explore_patches():
    result = run_feedback_loop(brief(), generator=ScaffoldDesignGenerator(), n=1)
    result = select_feedback_candidate(brief(), result, result.ranked_candidate_ids[0])
    patches = build_actionable_patches(result)
    assert patches
    assert all(item.enforcement == "explore" for item in patches)
    assert all(item.operation == "constrain" for item in patches)


def test_service_attaches_feedback_batch_to_iteration_when_brief_is_frozen():
    frozen = brief().model_copy(update={"status": "frozen"})
    service = ExperienceApplicationService(InMemoryExperienceRepository())
    service.repository.save("brief", frozen.brief_id, frozen.revision_id, frozen)
    result = service.run_design_feedback(frozen, generator=ScaffoldDesignGenerator(), n=3)
    assert result.iteration_id
    iteration = service.repository.get_current("iteration", result.iteration_id)
    assert iteration.status.value == "candidates_imported"
    assert len(iteration.candidate_revision_ids) == 3


def test_service_projects_m3_selection_into_formal_revision_chain_and_round_two():
    frozen = brief().model_copy(update={"status": "frozen"})
    repository = InMemoryExperienceRepository()
    service = ExperienceApplicationService(repository)
    repository.save("brief", frozen.brief_id, frozen.revision_id, frozen)
    result = service.run_design_feedback(frozen, generator=ScaffoldDesignGenerator(), n=3)
    selected, snapshot = service.select_design_feedback(
        frozen, result, result.ranked_candidate_ids[0]
    )
    assert snapshot.iteration_id == result.iteration_id
    assert snapshot.selection_decision_id
    iteration = repository.get_current("iteration", result.iteration_id)
    assert iteration.status.value == "selected"
    prompt = service.confirm_feedback_next_prompt(selected)
    assert prompt.confirmed_patch_revision_ids
    iteration = repository.get_current("iteration", result.iteration_id)
    assert iteration.status.value == "prompt_confirmed"
    second, candidates = service.generate_second_round(iteration, prompt)
    assert second.round_number == 2
    assert len(candidates) == frozen.round_two_variants_per_direction
    assert all(
        candidate.parent_candidate_revision_id
        == prompt.selected_candidate_revision_ids[0]
        for candidate in candidates
    )


def test_selected_m3_hypothesis_is_explicitly_handed_to_m2_as_draft():
    frozen = brief().model_copy(update={"status": "frozen"})
    repository = InMemoryExperienceRepository()
    service = ExperienceApplicationService(repository)
    repository.save("brief", frozen.brief_id, frozen.revision_id, frozen)
    result = service.run_design_feedback(frozen, generator=ScaffoldDesignGenerator(), n=1)
    selected, _ = service.select_design_feedback(frozen, result, result.ranked_candidate_ids[0])
    plan, binding, family, conditions = service.create_experiment_plan_from_feedback(
        frozen, selected
    )
    assert plan.status == "draft"
    assert plan.generated_from_hypothesis_id == binding.hypothesis_revision_id.split(".r1")[0]
    assert family.locked is False
    assert conditions
    persisted = repository.get_revision("experience_hypothesis", binding.hypothesis_revision_id)
    assert persisted is not None and persisted.status == "exploratory"


def test_m3_cli_exports_then_allows_human_selection(tmp_path):
    brief_file = tmp_path / "brief.json"
    feedback_file = tmp_path / "feedback.json"
    selected_file = tmp_path / "selected.json"
    database = tmp_path / "feedback.sqlite"
    brief_file.write_text(brief().model_dump_json(), encoding="utf-8")
    generated = runner.invoke(app, ["design-feedback", "--brief", str(brief_file), "--count", "3", "--db", str(database), "--out", str(feedback_file)])
    assert generated.exit_code == 0, generated.stdout
    payload = json.loads(feedback_file.read_text(encoding="utf-8"))
    selected = runner.invoke(app, ["design-feedback-select", "--brief", str(brief_file), "--feedback", str(feedback_file), "--db", str(database), "--candidate", payload["ranked_candidate_ids"][0], "--out", str(selected_file)])
    assert selected.exit_code == 0, selected.stdout
    assert json.loads(selected_file.read_text(encoding="utf-8"))["next_prompt"]


def test_m3_cli_frozen_feedback_can_generate_second_round(tmp_path):
    brief_file = tmp_path / "frozen-brief.json"
    feedback_file = tmp_path / "feedback.json"
    selected_file = tmp_path / "selected.json"
    second_file = tmp_path / "second.json"
    database = tmp_path / "feedback.sqlite"
    frozen = brief().model_copy(update={"status": "frozen"})
    brief_file.write_text(frozen.model_dump_json(), encoding="utf-8")
    generated = runner.invoke(app, ["design-feedback", "--brief", str(brief_file), "--count", "3", "--db", str(database), "--out", str(feedback_file)])
    assert generated.exit_code == 0, generated.output
    payload = json.loads(feedback_file.read_text(encoding="utf-8"))
    selected = runner.invoke(app, ["design-feedback-select", "--brief", str(brief_file), "--feedback", str(feedback_file), "--db", str(database), "--candidate", payload["ranked_candidate_ids"][0], "--out", str(selected_file)])
    assert selected.exit_code == 0, selected.output
    generated_second = runner.invoke(app, ["design-feedback-next-round", "--brief", str(brief_file), "--feedback", str(selected_file), "--db", str(database), "--out", str(second_file)])
    assert generated_second.exit_code == 0, generated_second.output
    assert len(json.loads(second_file.read_text(encoding="utf-8"))["candidate_ids"]) == frozen.round_two_variants_per_direction
