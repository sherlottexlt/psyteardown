from psyteardown.experience import (
    CleanRerunClosure,
    build_clean_rerun,
    propagate_contamination,
    quarantine_output,
    SQLiteExperienceRepository,
)


def complete_closure(**overrides):
    values = {
        "direct_inputs_closed": True,
        "prompts_closed": True,
        "caches_closed": True,
        "retrieval_indexes_closed": True,
        "dependency_data_closed": True,
        "environment_closed": True,
        "model_context_closed": True,
        "output_storage_closed": True,
        "new_workspace": True,
        "independent_environment": True,
        "frozen_parameters": True,
        "reproducible_logs": True,
    }
    values.update(overrides)
    return CleanRerunClosure(**values)


def test_unauthorized_output_is_quarantined_even_without_human_view():
    output = quarantine_output(
        output_id="out-1",
        revision_id="out-1.r1",
        output_type="candidate",
        execution_id="exec-1",
        access_control="acl-1",
    )
    assert output.status == "unauthorized_output_quarantined"
    assert output.isolation_state == "quarantined"


def test_contamination_mark_requires_source_and_pauses_support():
    mark = propagate_contamination(
        object_id="review-1",
        revision_id="review-1.r2",
        object_type="review_item",
        source_output_ids=["out-1", "out-1"],
    )
    assert mark.status == "unauthorized_output_contaminated"
    assert mark.source_output_ids == ("out-1",)
    assert mark.support_paused is True


def test_incomplete_clean_rerun_is_uncertain_and_not_confirmed():
    rerun = build_clean_rerun(
        rerun_id="rerun-1",
        revision_id="rerun-1.r1",
        source_object_id="review-1",
        source_revision_id="review-1.r2",
        new_object_id="review-1",
        new_object_revision_id="review-1.r3",
        closure=complete_closure(caches_closed=False),
        source_payload_hash="hash-a",
        rerun_payload_hash="hash-a",
        key_results_consistent=True,
    )
    assert rerun.status == "clean_rerun_contamination_uncertain"
    assert rerun.confirmed is False


def test_matching_clean_rerun_creates_new_clean_rederived_revision():
    rerun = build_clean_rerun(
        rerun_id="rerun-1",
        revision_id="rerun-1.r1",
        source_object_id="review-1",
        source_revision_id="review-1.r2",
        new_object_id="review-1",
        new_object_revision_id="review-1.r3",
        closure=complete_closure(),
        source_payload_hash="hash-a",
        rerun_payload_hash="hash-a",
        key_results_consistent=True,
    )
    assert rerun.status == "clean_rederived"
    assert rerun.confirmed is True


def test_divergent_clean_rerun_requires_impact_analysis_and_stays_unconfirmed():
    rerun = build_clean_rerun(
        rerun_id="rerun-1",
        revision_id="rerun-1.r1",
        source_object_id="order-1",
        source_revision_id="order-1.r2",
        new_object_id="order-1",
        new_object_revision_id="order-1.r3",
        closure=complete_closure(),
        source_payload_hash="hash-old",
        rerun_payload_hash="hash-new",
        key_results_consistent=False,
        impact_analysis_id="impact-1",
    )
    assert rerun.status == "clean_rederivation_divergence"
    assert rerun.impact_analysis_required is True
    assert rerun.confirmed is False


def test_quarantine_and_clean_rerun_records_round_trip_in_sqlite(tmp_path):
    output = quarantine_output(
        output_id="out-1",
        revision_id="out-1.r1",
        output_type="review_draft",
        execution_id="exec-1",
        access_control="incident-only",
    )
    rerun = build_clean_rerun(
        rerun_id="rerun-1",
        revision_id="rerun-1.r1",
        source_object_id="review-1",
        source_revision_id="review-1.r1",
        new_object_id="review-1",
        new_object_revision_id="review-1.r2",
        closure=complete_closure(),
        source_payload_hash="hash-a",
        rerun_payload_hash="hash-a",
        key_results_consistent=True,
    )
    with SQLiteExperienceRepository(tmp_path / "experience.db") as repository:
        repository.save("unauthorized_output", output.output_id, output.revision_id, output)
        repository.save("clean_rerun", rerun.rerun_id, rerun.revision_id, rerun)
        assert repository.get_revision("unauthorized_output", output.revision_id) == output
        assert repository.get_revision("clean_rerun", rerun.revision_id) == rerun
