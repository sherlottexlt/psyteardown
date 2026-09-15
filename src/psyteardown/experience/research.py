"""Generic M1 experience-research commands and deterministic checks.

This module deliberately sits beside the prototype-evidence workflow.  It
turns source-backed records into revisioned snapshots, but never promotes a
claim merely because it parses or because a design render exists.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

from psyteardown.experience.models import (
    Critique,
    Evidence,
    ExperienceHypothesis,
    Observation,
)
from psyteardown.experience.repositories import InMemoryExperienceRepository


OVERSTRONG_TERMS = (
    "必然", "证明", "一定导致", "必定导致", "必然导致",
    "inevitably", "proves", "proven", "definitely causes",
    "always causes", "guarantees", "guaranteed to",
)
_VARIABLE_HINT = re.compile(r"(?:[a-z][a-z0-9_-]*\.)?[a-z][a-z0-9_-]*", re.I)


@dataclass(frozen=True)
class ResearchIssue:
    code: str
    object_id: str
    message: str
    severity: str = "error"


def _has_overstrong(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in OVERSTRONG_TERMS)


def validate_evidence(evidence: Evidence) -> tuple[ResearchIssue, ...]:
    """Check source semantics after Pydantic schema validation."""
    issues: list[ResearchIssue] = []
    if not evidence.artifact_id.strip() or not evidence.quote_or_locator.strip():
        issues.append(ResearchIssue("missing_source_locator", evidence.evidence_id, "evidence needs an artifact and locator"))
    if evidence.kind in {"text", "interview"} and not (evidence.source_text or evidence.quote_or_locator):
        issues.append(ResearchIssue("missing_quote", evidence.evidence_id, "text/interview evidence needs a quote or locator"))
    if evidence.kind == "sensor" and not evidence.sensor_file and not evidence.quote_or_locator:
        issues.append(ResearchIssue("missing_sensor_file", evidence.evidence_id, "sensor evidence needs a file or record locator"))
    if evidence.kind == "experiment" and not evidence.experiment_record and not evidence.quote_or_locator:
        issues.append(ResearchIssue("missing_experiment_record", evidence.evidence_id, "experiment evidence needs a record locator"))
    return tuple(issues)


def validate_observation(observation: Observation) -> tuple[ResearchIssue, ...]:
    issues = [issue for item in observation.evidence for issue in validate_evidence(item)]
    if not observation.evidence:
        issues.append(ResearchIssue("observation_without_evidence", observation.observation_id, "an observation cannot be a fact without a source"))
    if observation.certainty in {"supported", "tested"} and not any(item.kind == "experiment" for item in observation.evidence):
        issues.append(ResearchIssue("unsupported_observation_status", observation.observation_id, "tested/supported observation requires real experiment evidence"))
    return tuple(issues)


def validate_hypothesis(hypothesis: ExperienceHypothesis) -> tuple[ResearchIssue, ...]:
    issues = [issue for item in hypothesis.evidence for issue in validate_evidence(item)]
    if not hypothesis.alternative_explanations:
        issues.append(ResearchIssue("missing_alternative", hypothesis.hypothesis_id, "hypothesis needs at least one alternative explanation"))
    if hypothesis.status == "supported" and not any(item.kind == "experiment" for item in hypothesis.evidence):
        issues.append(ResearchIssue("supported_without_experiment", hypothesis.hypothesis_id, "supported requires real experiment evidence"))
    if _has_overstrong(" ".join((hypothesis.mechanism, hypothesis.predicted_outcome))):
        severity = "error" if hypothesis.status == "supported" else "warning"
        issues.append(ResearchIssue("overstrong_causal_language", hypothesis.hypothesis_id, "replace deterministic causal language with a conditional prediction", severity))
    return tuple(issues)


def validate_critique(critique: Critique) -> tuple[ResearchIssue, ...]:
    issues = [issue for item in critique.hypotheses for issue in validate_hypothesis(item)]
    for change in critique.actionable_changes:
        if not _VARIABLE_HINT.search(change) or len(change.split()) < 2:
            issues.append(ResearchIssue("non_actionable_change", critique.critique_id, f"actionable change is not tied to an operational variable: {change!r}"))
    if critique.status == "approved" and not critique.reviewer:
        issues.append(ResearchIssue("approval_without_reviewer", critique.critique_id, "approved critique requires a human reviewer"))
    return tuple(issues)


def validate_research_records(
    *,
    evidence: Iterable[Evidence] = (),
    observations: Iterable[Observation] = (),
    hypotheses: Iterable[ExperienceHypothesis] = (),
    critiques: Iterable[Critique] = (),
) -> tuple[ResearchIssue, ...]:
    records = [*evidence, *observations, *hypotheses, *critiques]
    issues: list[ResearchIssue] = []
    for item in records:
        if isinstance(item, Evidence):
            issues.extend(validate_evidence(item))
        elif isinstance(item, Observation):
            issues.extend(validate_observation(item))
        elif isinstance(item, ExperienceHypothesis):
            issues.extend(validate_hypothesis(item))
        elif isinstance(item, Critique):
            issues.extend(validate_critique(item))
    return tuple(issues)


class ResearchApplicationService:
    """Revision-safe persistence boundary for generic M1 records."""

    def __init__(self, repository: InMemoryExperienceRepository | object | None = None):
        self.repository = repository or InMemoryExperienceRepository()

    def _save(self, object_type: str, object_id: str, value: object, *, expected_revision: int | None = None):
        slot = {
            "evidence": "evidence",
            "observation": "observations",
            "experience_hypothesis": "hypotheses",
            "critique": "critiques",
        }.get(object_type)
        if slot is None:
            raise ValueError(f"unsupported research object type: {object_type}")
        issues = validate_research_records(**{slot: [value]})
        errors = tuple(issue for issue in issues if issue.severity == "error")
        if errors:
            raise ValueError("; ".join(issue.message for issue in errors))
        # Small JSON fixtures commonly use the model's compatibility default
        # (e.g. ``evidence.r1``).  Revision IDs are unique within an object
        # type, so materialize that shorthand as an aggregate-scoped ID before
        # writing; explicit IDs remain untouched and preserve branching.
        revision_id = getattr(value, "revision_id", None)
        if revision_id in {"evidence.r1", "observation.r1", "hypothesis.r1", "critique.r1"}:
            value = value.model_copy(
                update={
                    "revision_id": f"{object_id}.r1",
                    "meta": value.meta.model_copy(update={"reason": value.meta.reason}),
                }
            )
        return self.repository.save_command(object_type, object_id, value.revision_id, value, expected_revision=expected_revision)

    def save_evidence(self, value: Evidence, *, expected_revision: int | None = None) -> Evidence:
        return self._save("evidence", value.evidence_id, value, expected_revision=expected_revision)

    def save_observation(self, value: Observation, *, expected_revision: int | None = None) -> Observation:
        return self._save("observation", value.observation_id, value, expected_revision=expected_revision)

    def save_hypothesis(self, value: ExperienceHypothesis, *, expected_revision: int | None = None) -> ExperienceHypothesis:
        return self._save("experience_hypothesis", value.hypothesis_id, value, expected_revision=expected_revision)

    def save_critique(self, value: Critique, *, expected_revision: int | None = None) -> Critique:
        return self._save("critique", value.critique_id, value, expected_revision=expected_revision)


def render_research_markdown(*, evidence=(), observations=(), hypotheses=(), critiques=()) -> str:
    lines = ["# Experience Research", ""]
    for heading, values in (("Evidence", evidence), ("Observations", observations), ("Experience hypotheses", hypotheses), ("Critiques", critiques)):
        lines += [f"## {heading}", ""]
        for item in values:
            payload = item.model_dump(mode="json")
            ident = payload.get("evidence_id") or payload.get("observation_id") or payload.get("hypothesis_id") or payload.get("critique_id")
            lines.append(f"- `{ident}`: {json.dumps(payload, ensure_ascii=False, sort_keys=True)}")
        if not values:
            lines.append("- none")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_research_json(*, evidence=(), observations=(), hypotheses=(), critiques=()) -> str:
    return json.dumps({"evidence": [x.model_dump(mode="json") for x in evidence], "observations": [x.model_dump(mode="json") for x in observations], "hypotheses": [x.model_dump(mode="json") for x in hypotheses], "critiques": [x.model_dump(mode="json") for x in critiques]}, ensure_ascii=False, indent=2)
