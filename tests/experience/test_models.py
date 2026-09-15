import pytest
from pydantic import ValidationError

from psyteardown.experience.models import (
    DesignVariableValue,
    PatchScope,
    ProhibitedExperience,
    ValueMissingReason,
)


def test_frozen_domain_values_cannot_be_mutated():
    value = DesignVariableValue(
        variable_id="feedback.modality",
        value_type="enum",
        normalized_value="private_haptic",
        display_value="private haptic",
    )
    with pytest.raises(ValidationError):
        value.display_value = "audio"


def test_missing_variable_value_is_explicit():
    value = DesignVariableValue(
        variable_id="feedback.duration",
        value_type="number",
        normalized_value=None,
        display_value="not measured",
        missing_reason=ValueMissingReason.NOT_MEASURED,
    )
    assert value.missing_reason == ValueMissingReason.NOT_MEASURED


def test_patch_scope_must_be_explicit():
    with pytest.raises(ValidationError):
        PatchScope()
    assert PatchScope(global_scope=True).global_scope is True
    assert PatchScope(event_ids=("event-1",)).event_ids == ("event-1",)


def test_hard_prohibition_requires_approved_rule():
    with pytest.raises(ValidationError):
        ProhibitedExperience(
            prohibition_id="privacy",
            operational_definition="public audio of private content",
            severity="hard",
            indicator="public_audio_private_content",
            release_condition="remove public audio",
        )
