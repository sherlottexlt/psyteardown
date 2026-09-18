from datetime import datetime, timezone
from pathlib import Path

import pytest

from psyteardown.experience import (
    AnalysisProtocolReview,
    ConditionSnapshot,
    CrossCaseEvidenceRef,
    CrossCaseKnowledgeCoordinator,
    DependencyRef,
    DomainStateError,
    Evidence,
    EvidenceReview,
    ExperienceHypothesis,
    MeasurementObservation,
    RevisionMeta,
    SQLiteExperienceRepository,
)


NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def _save_case(repo, case_id: str, outcome: str = "supported") -> CrossCaseEvidenceRef:
    condition_id = f"{case_id}-condition"
    condition = ConditionSnapshot(
        condition_id=condition_id,
        revision_id=f"{condition_id}.r1",
        meta=RevisionMeta(revision=1, created_by="researcher", reason="condition snapshot"),
        candidate_revision_id=f"{case_id}-candidate.r1",
        environment=f"{case_id} walking condition",
    )
    repo.save("condition", condition.condition_id, condition.revision_id, condition)
    protocol_review = AnalysisProtocolReview(
        review_id=f"{case_id}-protocol-review",
        revision_id=f"{case_id}-protocol-review.r1",
        meta=RevisionMeta(revision=1, created_by="method-lead", reason="approved before data"),
        experiment_revision_id=f"{case_id}-experiment.r1",
        reviewer="method-lead",
        sample_size_reviewed=True,
        stopping_rules_reviewed=True,
        missingness_reviewed=True,
        analysis_family_reviewed=True,
        condition_lineage_reviewed=True,
        status="approved",
        rationale="protocol complete",
        reviewed_at=NOW,
    )
    repo.save("analysis_protocol_review", protocol_review.review_id, protocol_review.revision_id, protocol_review)
    measurement = MeasurementObservation(
        observation_id=f"{case_id}-measurement",
        revision_id=f"{case_id}-measurement.r1",
        meta=RevisionMeta(revision=1, created_by="test-lead", reason="confirmed raw measurement"),
        run_id=f"{case_id}-run",
        measure_id="cancel-time",
        metric="cancellation time",
        method="instrumented timer",
        condition=condition.condition_id,
        value=420,
        unit="ms",
        status="confirmed",
        reviewer="evidence-lead",
        reviewed_at=NOW,
        raw_file_hash="a" * 64,
        condition_snapshot_revision_id=condition.revision_id,
    )
    repo.save("measurement_observation", measurement.observation_id, measurement.revision_id, measurement)
    evidence_review = EvidenceReview(
        review_id=f"{case_id}-evidence-review",
        revision_id=f"{case_id}-evidence-review.r1",
        meta=RevisionMeta(revision=1, created_by="evidence-lead", reason="measurement reviewed"),
        run_id=measurement.run_id,
        observation_ids=(measurement.observation_id,),
        reviewer="evidence-lead",
        decision="accepted",
        evidence_level_after="supported",
        confirmed_observation_ids=(measurement.observation_id,),
        rationale="raw measurement accepted",
        condition_snapshot_ids=(condition.revision_id,),
        analysis_protocol_review_id=protocol_review.revision_id,
    )
    repo.save("evidence_review", evidence_review.review_id, evidence_review.revision_id, evidence_review)
    hypothesis_id = f"{case_id}-hypothesis"
    hypothesis = ExperienceHypothesis(
        hypothesis_id=hypothesis_id,
        revision_id=f"{hypothesis_id}.r1",
        meta=RevisionMeta(revision=1, created_by="research-lead", reason="evidence interpretation"),
        target_population="consented commuters",
        task_condition="cancel while walking",
        environment_condition=condition.environment,
        social_condition="shared setting",
        physical_features=("bounded cancel control",),
        user_actions=("press cancel",),
        construct="control",
        mechanism="bounded response may improve control",
        predicted_outcome="shorter cancellation time",
        alternative_explanations=("practice effect",),
        evidence=(Evidence(
            evidence_id=f"{case_id}-experiment-evidence",
            revision_id=f"{case_id}-experiment-evidence.r1",
            kind="experiment",
            artifact_id=evidence_review.review_id,
            quote_or_locator=f"measurement:{measurement.observation_id}",
            experiment_record=evidence_review.revision_id,
            provenance="prototype_measurement",
            evidence_role="experiment_result",
        ),),
        validation_method="preregistered prototype comparison",
        status=outcome,
        dependencies=(
            DependencyRef(object_type="analysis_protocol_review", object_id=protocol_review.review_id, revision=1),
            DependencyRef(object_type="evidence_review", object_id=evidence_review.review_id, revision=1),
        ),
    )
    repo.save("experience_hypothesis", hypothesis.hypothesis_id, hypothesis.revision_id, hypothesis)
    return CrossCaseEvidenceRef(
        case_id=case_id,
        hypothesis_id=hypothesis.hypothesis_id,
        hypothesis_revision_id=hypothesis.revision_id,
        evidence_review_revision_ids=(evidence_review.revision_id,),
        condition_snapshot_revision_ids=(condition.revision_id,),
        outcome=outcome,
    )


def test_unapproved_candidate_does_not_enter_default_rules(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "knowledge.db") as repo:
        cases = (_save_case(repo, "case-a"), _save_case(repo, "case-b"))
        coordinator = CrossCaseKnowledgeCoordinator(repo)
        candidate = coordinator.propose_rule(
            rule_id="bounded-cancel",
            statement="A bounded cancellation control may reduce cancellation time while walking.",
            applicability=("walking", "consented commuters"),
            counter_conditions=("unverified device latency",),
            source_cases=cases,
        )
        assert candidate.replication_status == "replicated"
        assert coordinator.default_rules() == ()
        with pytest.raises(DomainStateError, match="human reviewer"):
            coordinator.review_candidate(
                candidate,
                reviewer="ai-agent",
                decision="approved",
                rationale="automatic approval forbidden",
                counterexamples_reviewed=True,
            )
        approved = coordinator.review_candidate(
            candidate,
            reviewer="knowledge-review-board",
            decision="approved",
            rationale="two traceable cases replicated the bounded claim",
            counterexamples_reviewed=True,
        )
        assert approved.status == "approved"
        assert coordinator.default_rules() == (approved,)


def test_single_case_cannot_be_approved_as_cross_case_rule(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "single-case.db") as repo:
        candidate = CrossCaseKnowledgeCoordinator(repo).propose_rule(
            rule_id="single-case-rule",
            statement="One observed outcome should remain a candidate.",
            applicability=("walking",),
            counter_conditions=("other environments",),
            source_cases=(_save_case(repo, "case-only"),),
        )
        with pytest.raises(DomainStateError, match="at least two cases"):
            CrossCaseKnowledgeCoordinator(repo).review_candidate(
                candidate,
                reviewer="knowledge-review-board",
                decision="approved",
                rationale="insufficient",
                counterexamples_reviewed=True,
            )


def test_counterexample_requires_review_and_counter_condition(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "counterexample.db") as repo:
        cases = (
            _save_case(repo, "support-a"),
            _save_case(repo, "support-b"),
            _save_case(repo, "counter", outcome="rejected"),
        )
        coordinator = CrossCaseKnowledgeCoordinator(repo)
        candidate = coordinator.propose_rule(
            rule_id="counterexample-rule",
            statement="A bounded cancellation control may reduce cancellation time.",
            applicability=("walking",),
            counter_conditions=(),
            source_cases=cases,
        )
        assert candidate.replication_status == "conflicted"
        with pytest.raises(DomainStateError, match="counterexample review"):
            coordinator.review_candidate(
                candidate,
                reviewer="knowledge-review-board",
                decision="approved",
                rationale="counterexample not reviewed",
                counterexamples_reviewed=False,
            )
