"""M3 AI design-feedback loop.

The loop is intentionally deterministic at its policy boundaries.  A design
generator may be stochastic, but candidate critique, hard-risk screening,
ordering, and prompt projection are reproducible and never auto-approve a
candidate or a hypothesis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Protocol

from psyteardown.experience.models import (
    Critique,
    DesignFeedbackSelection,
    DeclaredFact,
    DesignBrief,
    DesignCandidate,
    ExperienceHypothesis,
    CandidateDraft,
    Evidence,
    Observation,
    RevisionMeta,
    VariablePatch,
    PatchScope,
)
from psyteardown.experience.rules import build_candidate


class CandidateGenerator(Protocol):
    def generate(self, brief: DesignBrief, *, round_number: int = 1, count: int | None = None, n: int | None = None, prompt: object | None = None) -> list[CandidateDraft]: ...


@dataclass(frozen=True)
class DesignFeedbackResult:
    brief_revision_id: str
    candidate_ids: tuple[str, ...]
    critique_ids: tuple[str, ...]
    ranked_candidate_ids: tuple[str, ...]
    selected_candidate_id: str | None
    next_prompt: str | None
    critiques: tuple[Critique, ...]
    candidates: tuple[DesignCandidate, ...] = ()
    iteration_id: str | None = None


def generate_candidates(brief: DesignBrief, *, generator: CandidateGenerator, n: int | None = None, count: int | None = None, actor: str = "system", round_number: int = 1, prompt: object | None = None) -> tuple[DesignCandidate, ...]:
    """Generate and validate an immutable candidate batch through a provider."""
    requested = count if count is not None else n
    if requested is None:
        requested = brief.round_one_size if round_number == 1 else brief.round_two_variants_per_direction
    if requested < 1:
        raise ValueError("candidate count must be positive")
    drafts = generator.generate(brief, round_number=round_number, count=requested, prompt=prompt)
    if len(drafts) != requested:
        raise ValueError(f"generator returned {len(drafts)} candidates; expected {requested}")
    candidates = tuple(build_candidate(item, brief, actor=actor, reason=f"M3 round {round_number} candidate imported") for item in drafts)
    if len({item.candidate_id for item in candidates}) != len(candidates):
        raise ValueError("candidate IDs must be unique within a feedback batch")
    return candidates


def _evidence_for_fact(fact: DeclaredFact, *, index: int) -> Evidence:
    return Evidence(
        evidence_id=f"{fact.fact_id}.e{index}",
        kind="text",
        artifact_id=fact.source_locator.split(":", 1)[0] or fact.fact_id,
        quote_or_locator=fact.source_locator,
        provenance="declared",
        evidence_role="design_observation",
    )


def _candidate_text(candidate: DesignCandidate) -> str:
    values = [candidate.name, candidate.description, candidate.interaction_story, candidate.target_context, candidate.strategy_direction]
    values.extend(f.value for f in candidate.declared_facts)
    values.extend(v.display_value for v in candidate.variables)
    return " ".join(values).lower()


def critique_candidate(candidate: DesignCandidate, brief: DesignBrief, *, actor: str = "system") -> Critique:
    """Build an evidence-linked candidate critique without psychological scoring."""
    text = _candidate_text(candidate)
    hard_risks: list[str] = []
    for prohibition in brief.prohibited_experiences:
        terms = tuple(term for term in prohibition.operational_definition.lower().split() if len(term) > 2)
        if terms and all(term in text for term in terms[:2]):
            hard_risks.append(f"{prohibition.prohibition_id}: candidate text matches prohibited condition")
    if candidate.status == "generation_invalid":
        hard_risks.append("candidate_generation_invalid")
    unknowns = list(candidate.unknowns)
    if candidate.shape:
        unknowns.extend(candidate.shape.physical_unknowns)
    unknowns = list(dict.fromkeys(unknowns))
    observations: list[Observation] = []
    evidence_ids: list[str] = []
    for index, fact in enumerate(candidate.declared_facts, start=1):
        source = _evidence_for_fact(fact, index=index)
        evidence_ids.append(source.evidence_id)
        observations.append(Observation(
            observation_id=f"{fact.fact_id}.observation",
            subject=fact.subject,
            predicate=fact.predicate,
            value=fact.value,
            evidence=(source,),
            certainty="observed",
            observation_type="physical_feature",
            unknowns=("declared fact does not establish physical performance",),
        ))
    hypotheses: list[ExperienceHypothesis] = []
    source_evidence = tuple(_evidence_for_fact(fact, index=i) for i, fact in enumerate(candidate.declared_facts, start=1))
    for criterion in brief.criteria:
        hypotheses.append(ExperienceHypothesis(
            hypothesis_id=f"{candidate.candidate_id}.{criterion.criterion_id}.hypothesis",
            target_population=brief.target_segment,
            task_condition=candidate.target_context,
            environment_condition=brief.context,
            social_condition="as declared by the brief; social exposure remains unknown" if not brief.movement_scenarios else ", ".join(sorted({phase.social_visibility for scenario in brief.movement_scenarios for phase in scenario.phases})),
            physical_features=tuple(candidate.changed_variable_ids),
            user_actions=tuple(event.expected_user_response for event in candidate.events[:2]),
            construct=criterion.name,
            mechanism=f"the candidate's {candidate.strategy_direction} direction may affect {criterion.operational_definition}",
            predicted_outcome=criterion.operational_definition,
            alternative_explanations=("task familiarity", "environmental interruption"),
            evidence=source_evidence,
            unknowns=tuple(unknowns),
            validation_method=f"compare candidate against a declared control on {criterion.operational_definition}",
            status="exploratory",
        ))
    actionable = tuple(
        f"adjust {variable_id} and compare its effect on the brief criterion"
        for variable_id in candidate.changed_variable_ids
    )
    if not actionable and brief.divergence_matrix.variable_ids:
        actionable = tuple(f"vary {variable_id} to test the brief tradeoff" for variable_id in brief.divergence_matrix.variable_ids)
    critique = Critique(
        critique_id=f"{candidate.candidate_id}.critique",
        candidate_id=candidate.candidate_id,
        hypotheses=tuple(hypotheses),
        observation_ids=tuple(item.observation_id for item in observations),
        evidence_ids=tuple(evidence_ids),
        hard_risks=tuple(hard_risks),
        tradeoffs=(f"strategy direction: {candidate.strategy_direction}", *brief.tradeoff_priorities),
        actionable_changes=actionable,
        unknowns=tuple(unknowns),
        human_decision_required=("confirm critique and choose candidate",) if not hard_risks else ("human review required for hard risk",),
        status="draft",
        revision_id=f"{candidate.candidate_id}.critique.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="M3 deterministic candidate critique"),
    )
    return critique


def rank_candidates(brief: DesignBrief, critiques: Iterable[Critique]) -> tuple[str, ...]:
    """Return an explainable partial ranking; ties are broken only by ID."""
    values = tuple(critiques)
    def key(critique: Critique) -> tuple[int, int, int, str]:
        # Hard risks first isolate candidates from preferred/viable options;
        # unknowns are surfaced before a candidate can be preferred.
        return (
            1 if critique.hard_risks else 0,
            1 if critique.unknowns else 0,
            0 if critique.actionable_changes else 1,
            critique.candidate_id,
        )
    return tuple(item.candidate_id for item in sorted(values, key=key))


def rank_reasons(critique: Critique) -> tuple[str, ...]:
    """Return the exact deterministic factors used by ``rank_candidates``."""
    return (
        "hard_risk" if critique.hard_risks else "no_hard_risk",
        "unknowns_present" if critique.unknowns else "no_unknowns",
        "actionable_feedback" if critique.actionable_changes else "no_actionable_feedback",
        "stable_candidate_id_tiebreak",
    )


def build_next_prompt(brief: DesignBrief, selected: DesignCandidate, critique: Critique) -> str:
    """Project only confirmed-safe, operational feedback into the next prompt."""
    changes = tuple(change for change in critique.actionable_changes if any(variable in change for variable in selected.changed_variable_ids))
    if not changes:
        changes = ("keep the selected candidate's variables explicit and generate a controlled alternative",)
    payload = {
        "brief_revision_id": brief.revision_id,
        "parent_candidate_revision_id": selected.candidate_revision_id,
        "goal": brief.goal,
        "target_segment": brief.target_segment,
        "context": brief.context,
        "preserve": list(selected.changed_variable_ids),
        "actionable_changes": list(changes),
        "unknowns": list(critique.unknowns),
        "do_not_claim": ["user psychology as fact", "physical performance without measurement", "automatic approval"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def run_feedback_loop(brief: DesignBrief, *, generator: CandidateGenerator, n: int | None = None, actor: str = "system") -> DesignFeedbackResult:
    candidates = generate_candidates(brief, generator=generator, n=n, actor=actor)
    critiques = tuple(critique_candidate(candidate, brief, actor=actor) for candidate in candidates)
    ranked = rank_candidates(brief, critiques)
    return DesignFeedbackResult(
        brief_revision_id=brief.revision_id,
        candidate_ids=tuple(item.candidate_id for item in candidates),
        critique_ids=tuple(item.critique_id for item in critiques),
        ranked_candidate_ids=ranked,
        # Generation and critique do not imply human selection.  The prompt
        # is created only by ``select_feedback_candidate`` below.
        selected_candidate_id=None,
        next_prompt=None,
        critiques=critiques,
        candidates=candidates,
        # The standalone loop has not yet been attached to an iteration
        # aggregate; the application service adds that lineage when the brief
        # is frozen and persisted.
        iteration_id=None,
    )


def select_feedback_candidate(
    brief: DesignBrief,
    result: DesignFeedbackResult,
    candidate_id: str,
    *,
    actor: str = "human",
    ) -> DesignFeedbackResult:
    """Record a human choice and project a prompt for the next round."""
    candidate = next((item for item in result.candidates if item.candidate_id == candidate_id), None)
    if candidate is None:
        raise ValueError(f"unknown candidate: {candidate_id}")
    critique = next(item for item in result.critiques if item.candidate_id == candidate_id)
    if critique.hard_risks:
        raise ValueError("hard-risk candidates require explicit remediation before selection")
    prompt = build_next_prompt(brief, candidate, critique)
    return DesignFeedbackResult(
        brief_revision_id=result.brief_revision_id,
        candidate_ids=result.candidate_ids,
        critique_ids=result.critique_ids,
        ranked_candidate_ids=result.ranked_candidate_ids,
        selected_candidate_id=candidate_id,
        next_prompt=prompt,
        critiques=result.critiques,
        candidates=result.candidates,
        iteration_id=result.iteration_id,
    )


def build_feedback_selection(result: DesignFeedbackResult, *, actor: str = "human") -> DesignFeedbackSelection:
    """Convert a selected feedback result into an immutable DB snapshot."""
    if not result.selected_candidate_id or not result.next_prompt:
        raise ValueError("feedback selection requires a human-selected candidate and next prompt")
    candidate = next(item for item in result.candidates if item.candidate_id == result.selected_candidate_id)
    critique = next(item for item in result.critiques if item.candidate_id == result.selected_candidate_id)
    selection_id = f"{result.selected_candidate_id}.feedback-selection"
    return DesignFeedbackSelection(
        selection_id=selection_id,
        revision_id=f"{selection_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="M3 human candidate selection"),
        brief_revision_id=result.brief_revision_id,
        candidate_id=candidate.candidate_id,
        candidate_revision_id=candidate.candidate_revision_id,
        critique_id=critique.critique_id,
        ranked_candidate_ids=result.ranked_candidate_ids,
        next_prompt_json=result.next_prompt,
        actor=actor,
    )


def build_actionable_patches(
    result: DesignFeedbackResult,
    *,
    actor: str = "human",
) -> tuple[VariablePatch, ...]:
    """Translate selected critique changes into reviewable explore patches.

    The planner never invents a target value.  ``constrain`` patches preserve
    the current value while making the variable an explicit subject of the
    next controlled comparison; a researcher may later replace them with a
    concrete confirmed value.
    """
    if not result.selected_candidate_id:
        raise ValueError("actionable patches require a human-selected candidate")
    candidate = next(item for item in result.candidates if item.candidate_id == result.selected_candidate_id)
    critique = next(item for item in result.critiques if item.candidate_id == result.selected_candidate_id)
    patches: list[VariablePatch] = []
    for index, variable_id in enumerate(candidate.changed_variable_ids, start=1):
        matching_change = next(
            (change for change in critique.actionable_changes if variable_id in change),
            None,
        )
        if matching_change is None:
            continue
        current = next((value for value in candidate.variables if value.variable_id == variable_id), None)
        patches.append(VariablePatch(
            patch_id=f"{candidate.candidate_id}.m3-patch-{index}",
            revision_id=f"{candidate.candidate_id}.m3-patch-{index}.r1",
            meta=RevisionMeta(revision=1, created_by=actor, reason="M3 actionable feedback captured"),
            review_item_revision_id=critique.revision_id,
            variable_id=variable_id,
            operation="constrain",
            from_value=current,
            to_value=None,
            scope=PatchScope(global_scope=True),
            enforcement="explore",
            rationale=matching_change,
            evidence_refs=critique.evidence_ids,
            expected_effect="make the variable explicit for a controlled next-round comparison",
            verification="compare the selected candidate with a matched alternative",
        ))
    return tuple(patches)


def render_feedback_json(result: DesignFeedbackResult) -> str:
    return json.dumps({
        "brief_revision_id": result.brief_revision_id,
        "iteration_id": result.iteration_id,
        "candidate_ids": list(result.candidate_ids),
        "critique_ids": list(result.critique_ids),
        "ranked_candidate_ids": list(result.ranked_candidate_ids),
        "selected_candidate_id": result.selected_candidate_id,
        "next_prompt": json.loads(result.next_prompt) if result.next_prompt else None,
        "critiques": [item.model_dump(mode="json") for item in result.critiques],
        "candidates": [item.model_dump(mode="json") for item in result.candidates],
    }, ensure_ascii=False, indent=2)


def render_feedback_markdown(result: DesignFeedbackResult) -> str:
    """Render a compact, auditable cross-candidate comparison report."""
    lines = [
        "# Design feedback", "",
        f"- Brief revision: `{result.brief_revision_id}`",
        f"- Ranked candidates: {', '.join(result.ranked_candidate_ids) or 'none'}",
        f"- Human selection: `{result.selected_candidate_id or 'pending'}`", "",
        "## Candidate comparison", "",
        "| Candidate | Evidence | Hard risks | Unknowns | Tradeoffs | Actionable changes |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for critique in result.critiques:
        lines.append(
            f"| `{critique.candidate_id}` | {len(critique.evidence_ids)} | {len(critique.hard_risks)} | {len(critique.unknowns)} | {len(critique.tradeoffs)} | {len(critique.actionable_changes)} |"
        )
    lines += ["", "## Review notes", ""]
    for critique in result.critiques:
        lines.append(f"### `{critique.candidate_id}`")
        if critique.evidence_ids:
            lines.append("- evidence: " + "; ".join(critique.evidence_ids))
        if critique.hard_risks:
            lines.append("- hard risks: " + "; ".join(critique.hard_risks))
        if critique.tradeoffs:
            lines.append("- tradeoffs: " + "; ".join(critique.tradeoffs))
        if critique.actionable_changes:
            lines.append("- actionable changes: " + "; ".join(critique.actionable_changes))
        if critique.unknowns:
            lines.append("- unknowns: " + "; ".join(critique.unknowns))
        lines.append("- rank factors: " + "; ".join(rank_reasons(critique)))
        lines.append("")
    if result.next_prompt:
        lines += ["## Next-round prompt", "", "```json", result.next_prompt, "```", ""]
    lines.append("_Generation and ranking do not constitute human approval or experiment evidence._")
    return "\n".join(lines) + "\n"
