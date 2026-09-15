import pytest

from psyteardown.experience import analyze_patch_conflicts, find_patch_conflicts
from psyteardown.experience.models import DesignVariableValue, PatchScope, RevisionMeta, VariablePatch


def _patch(revision, *, enforcement="should", variable="wearable.attachment", value="broad strap"):
    return VariablePatch(
        patch_id=revision,
        revision_id=revision,
        meta=RevisionMeta(revision=1, created_by="test", reason="patch"),
        review_item_revision_id="review.r1",
        variable_id=variable,
        operation="replace",
        to_value=DesignVariableValue(variable_id=variable, value_type="enum", normalized_value=value, display_value=value),
        scope=PatchScope(global_scope=True),
        enforcement=enforcement,
        rationale="test",
        evidence_refs=("review",),
        expected_effect="test",
        verification="test",
    )


def test_attachment_aliases_are_compared_as_one_canonical_variable():
    conflicts = analyze_patch_conflicts((_patch("a", variable="wearable.attachment"), _patch("b", variable="wearable.attachment_strategy", value="clip")))
    assert conflicts[0].variable_id == "wearable.attachment_strategy"
    assert conflicts[0].classification == "blocking"
    assert find_patch_conflicts((_patch("a"), _patch("b", variable="wearable.attachment_strategy", value="clip"))) == (("a", "b"),)


def test_must_shadows_should_and_explore_is_retained_for_review():
    shadowed = analyze_patch_conflicts((_patch("must", enforcement="must"), _patch("should", value="clip")))
    assert shadowed[0].classification == "shadowed"
    assert shadowed[0].winning_revision_id == "must"
    exploratory = analyze_patch_conflicts((_patch("explore", enforcement="explore"), _patch("should", value="clip")))
    assert exploratory[0].classification == "exploratory"
