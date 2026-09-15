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
    critique_candidate,
    generate_candidates,
    rank_candidates,
    render_feedback_json,
    run_feedback_loop,
    select_feedback_candidate,
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
