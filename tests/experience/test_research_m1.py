import json

import pytest

from psyteardown.experience import (
    Critique,
    Evidence,
    ExperienceHypothesis,
    Observation,
    ResearchApplicationService,
    SQLiteExperienceRepository,
    validate_hypothesis,
)


def evidence(kind="text", **kwargs):
    return Evidence(
        evidence_id=kwargs.pop("evidence_id", "ev-1"),
        kind=kind,
        artifact_id=kwargs.pop("artifact_id", "brief.txt"),
        quote_or_locator=kwargs.pop("quote_or_locator", "lines 1-2"),
        **kwargs,
    )


def test_observation_requires_traceable_source_and_hypothesis_is_conditional():
    source = evidence()
    observation = Observation(
        observation_id="obs-1", subject="strap", predicate="has", value="quick release", evidence=(source,),
        observation_type="physical_feature",
    )
    assert observation.evidence[0].artifact_id == "brief.txt"
    hypothesis = ExperienceHypothesis(
        hypothesis_id="hyp-1", target_population="commuters", task_condition="boarding",
        environment_condition="crowded transit", social_condition="shared", physical_features=("quick release",),
        user_actions=("press release",), construct="control", mechanism="reduces action steps",
        predicted_outcome="users can stop the interaction within the task window", alternative_explanations=("familiarity",),
        evidence=(source,), validation_method="timed task comparison",
    )
    assert validate_hypothesis(hypothesis) == ()


def test_supported_hypothesis_requires_real_experiment_and_overstrong_claim_is_rejected():
    with pytest.raises(ValueError):
        ExperienceHypothesis(
            hypothesis_id="hyp-2", target_population="users", task_condition="task", environment_condition="lab", social_condition="private",
            construct="safety", mechanism="this proves", predicted_outcome="always causes safety", alternative_explanations=("expectancy",),
            validation_method="experiment", status="supported", evidence=(evidence(),),
        )


def test_sqlite_repository_round_trip_for_generic_records(tmp_path):
    path = tmp_path / "m1.sqlite3"
    source = evidence()
    obs = Observation(observation_id="obs-1", subject="button", predicate="has", value="feedback", evidence=(source,))
    with SQLiteExperienceRepository(path) as repo:
        service = ResearchApplicationService(repo)
        service.save_evidence(source)
        service.save_observation(obs)
        persisted_obs = repo.get_current("observation", "obs-1")
        persisted_ev = repo.get_current("evidence", "ev-1")
        assert persisted_obs.observation_id == obs.observation_id
        assert persisted_obs.revision_id == "obs-1.r1"
        assert persisted_ev.evidence_id == source.evidence_id


def test_critique_approval_requires_human_reviewer():
    with pytest.raises(ValueError):
        Critique(critique_id="c-1", candidate_id="candidate-1", status="approved")
