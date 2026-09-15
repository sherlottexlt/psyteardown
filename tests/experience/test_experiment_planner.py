import json

import pytest

from psyteardown.experience import (
    Evidence,
    ExperienceHypothesis,
    ExperimentVariable,
    build_experiment_plan,
    plan_completeness,
    preregister_plan,
    render_experiment_plan_json,
)


def hypothesis(status="exploratory"):
    source = Evidence(kind="text", artifact_id="brief.md", quote_or_locator="section 1")
    return ExperienceHypothesis(
        id="hyp-m2", target_users="commuters", task="boarding", environment="crowded transit", social="shared",
        physical_features=["private haptic"], actions=["press stop"], construct="control",
        mechanism="a bounded signal may reduce interruption cost", predicted_outcome="fewer public-facing interruptions",
        alternative_explanations=["familiarity"], evidence=[source], validation="task comparison", status=status,
    )


def test_builder_maps_hypothesis_to_variables_measure_and_controls():
    plan = build_experiment_plan(hypothesis())
    assert plan.generated_from_hypothesis_id == "hyp-m2"
    assert len(plan.independent_variables) == 1
    assert plan.independent_variables[0].levels == ("baseline", "proposed")
    assert plan.dependent_measures[0].primary is True
    assert plan_completeness(plan) == ()


def test_preregister_requires_complete_plan_and_creates_new_revision():
    plan = build_experiment_plan(hypothesis())
    frozen = preregister_plan(plan, actor="researcher")
    assert frozen.status == "preregistered"
    assert frozen.meta.parent_revision_id == plan.revision_id
    with pytest.raises(ValueError):
        preregister_plan(frozen)


def test_rejected_hypothesis_cannot_be_planned():
    with pytest.raises(ValueError):
        build_experiment_plan(hypothesis("rejected"))


def test_json_export_is_machine_readable():
    plan = build_experiment_plan(hypothesis())
    payload = json.loads(render_experiment_plan_json(plan))
    assert payload["status"] == "draft"
    assert payload["research_question"]
