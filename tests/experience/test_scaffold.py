from types import SimpleNamespace

from psyteardown.experience.models import (
    DesignBrief,
    DivergenceMatrix,
    ExperienceCriterion,
    RevisionMeta,
)
from psyteardown.experience.providers import ScaffoldDesignGenerator
from psyteardown.experience.rules import REQUIRED_EVENT_TYPES, validate_event_sequence


def make_brief() -> DesignBrief:
    return DesignBrief(
        brief_id="brief-scaffold",
        revision_id="brief-scaffold.r1",
        meta=RevisionMeta(revision=1, created_by="test", reason="draft"),
        goal="reduce interruption during focused work",
        target_segment="knowledge workers",
        researchability_confirmed=True,
        context="attention task",
        scenario_ids=("scenario-focus",),
        criteria=(
            ExperienceCriterion(
                criterion_id="control",
                name="Control",
                operational_definition="the user can stop or defer an intervention",
                desired_direction="higher",
                priority=1,
            ),
        ),
        divergence_matrix=DivergenceMatrix(
            variable_ids=("feedback.modality", "feedback.timing"),
            strategy_directions=("quiet", "discoverable", "privacy_first"),
        ),
    )


def test_scaffold_generates_complete_design_not_just_a_shape():
    generator = ScaffoldDesignGenerator()
    drafts = generator.generate(make_brief(), round_number=1, count=5)

    assert len(drafts) == 5
    assert len({draft.candidate_id for draft in drafts}) == 5
    for draft in drafts:
        assert draft.design is not None
        assert draft.shape == draft.design.shape
        design = draft.design
        assert design.concept_summary
        assert design.intended_user_and_context
        assert len(design.components) >= 3
        assert design.material_and_finish
        assert design.interaction_flow
        assert design.feedback_behavior
        assert design.privacy_and_control
        assert design.power_and_connectivity
        assert design.manufacturing_assumptions
        assert design.declared_unknowns
        assert {event.event_type for event in draft.events} == REQUIRED_EVENT_TYPES
        assert all(not validate_event_sequence(event) for event in draft.events)
        assert draft.declared_facts
        assert draft.variables
        # Physical measurements remain explicit unknowns in the first-pass
        # design instead of being invented by the scaffold.
        assert "exact dimensions" in design.declared_unknowns


def test_scaffold_second_round_preserves_parent_revision_and_count():
    generator = ScaffoldDesignGenerator()
    brief = make_brief()
    parents = generator.generate(brief, round_number=1, count=5)
    selected_parents = (parents[0].candidate_id + ".r1", parents[1].candidate_id + ".r1")
    prompt = SimpleNamespace(selected_candidate_revision_ids=selected_parents)

    variants = generator.generate(brief, round_number=2, count=6, prompt=prompt)

    assert len(variants) == 6
    assert {variant.parent_candidate_revision_id for variant in variants} == set(selected_parents)
    assert all(sum(variant.parent_candidate_revision_id == parent for variant in variants) == 3 for parent in selected_parents)
    assert all(variant.design is not None for variant in variants)
    assert generator.calls[-1]["round_number"] == 2
