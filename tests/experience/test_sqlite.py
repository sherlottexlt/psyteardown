from pathlib import Path

import pytest

from psyteardown.experience.models import (
    DesignBrief,
    DesignIteration,
    DesignVariableValue,
    DivergenceMatrix,
    ExperienceCriterion,
    RevisionMeta,
)
from psyteardown.experience.repositories import RepositoryError
from psyteardown.experience.sqlite import SQLiteExperienceRepository


def make_brief() -> DesignBrief:
    return DesignBrief(
        brief_id="brief-sqlite",
        revision_id="brief-sqlite.r1",
        meta=RevisionMeta(revision=1, created_by="test", reason="draft"),
        goal="test persistence",
        target_segment="researchers",
        researchability_confirmed=True,
        context="local test",
        scenario_ids=("scenario-1",),
        criteria=(
            ExperienceCriterion(
                criterion_id="control",
                name="Control",
                operational_definition="can stop",
                desired_direction="higher",
                priority=1,
            ),
        ),
        divergence_matrix=DivergenceMatrix(
            variable_ids=("feedback.modality",),
            strategy_directions=("quiet", "visible", "controlled"),
        ),
    )


def test_sqlite_round_trip_preserves_immutable_revision_and_current(tmp_path: Path):
    path = tmp_path / "experience.sqlite3"
    brief = make_brief()
    with SQLiteExperienceRepository(path) as repo:
        repo.save("brief", brief.brief_id, brief.revision_id, brief)
        iteration = DesignIteration(
            iteration_id="iteration-1",
            revision_id="iteration-1.r1",
            meta=RevisionMeta(revision=1, created_by="test", reason="created"),
            brief_revision_id=brief.revision_id,
            round_number=1,
        )
        repo.save("iteration", iteration.iteration_id, iteration.revision_id, iteration)
        assert repo.get_current("brief", brief.brief_id) == brief
        assert repo.get_revision("iteration", iteration.revision_id) == iteration
        assert repo.current_revision_id("iteration", iteration.iteration_id) == iteration.revision_id
        assert repo.list_revisions("brief", brief.brief_id) == [brief]
        assert {row[0] for row in repo._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")} >= {
            "experience_revisions",
            "experience_current",
            "experience_domain_events",
            "experience_audit_events",
        }


def test_sqlite_rejects_duplicate_revision(tmp_path: Path):
    repo = SQLiteExperienceRepository(tmp_path / "experience.sqlite3")
    brief = make_brief()
    repo.save("brief", brief.brief_id, brief.revision_id, brief)
    with pytest.raises(RepositoryError):
        repo.save("brief", brief.brief_id, brief.revision_id, brief)
    repo.close()
