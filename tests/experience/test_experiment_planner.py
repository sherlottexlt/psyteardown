import json

import pytest

from psyteardown.experience import (
    Evidence,
    ExperienceHypothesis,
    ExperimentVariable,
    build_experiment_plan,
    build_experiment_plan_bundle,
    revise_condition_snapshot,
    review_analysis_protocol,
    validate_analysis_protocol,
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


def test_bundle_creates_binding_analysis_family_and_hashed_conditions():
    plan, binding, family, conditions = build_experiment_plan_bundle(hypothesis())
    assert plan.hypothesis_binding_ids == (binding.binding_id,)
    assert plan.analysis_family_revision_id == family.revision_id
    assert plan.condition_snapshot_ids == tuple(item.revision_id for item in conditions)
    assert family.primary_binding_ids == (binding.binding_id,)
    assert all(item.content_hash_value == item.content_hash for item in conditions)
    assert validate_analysis_protocol(plan.model_copy(update={"status": "preregistered"}), family=family, bindings=[binding], conditions=conditions) == ("analysis_family_not_locked",)


def test_condition_revision_preserves_parent_and_changes_hash():
    plan, _, _, conditions = build_experiment_plan_bundle(hypothesis())
    child = revise_condition_snapshot(conditions[0], variable_values=conditions[0].variable_values, reason="clarify condition")
    assert child.meta.parent_revision_id == conditions[0].revision_id
    assert child.revision_id != conditions[0].revision_id


def test_analysis_protocol_review_requires_human_gate():
    plan, binding, family, conditions = build_experiment_plan_bundle(hypothesis())
    preregistered = plan.model_copy(update={"status": "preregistered"})
    pending = review_analysis_protocol(preregistered, reviewer="method", family=family, bindings=[binding], conditions=conditions)
    assert pending.status == "pending"
    locked = family.model_copy(update={"locked": True})
    approved = review_analysis_protocol(preregistered, reviewer="method", family=locked, bindings=[binding], conditions=conditions, approved=True)
    assert approved.status == "approved"
