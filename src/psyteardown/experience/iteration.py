"""Deterministic, reviewable design-iteration helpers.

The iteration layer deliberately edits only declared design variables.  It
does not infer dimensions, comfort, fit or user outcomes from a render.  A
patched candidate and its progressive model are immutable children of their
parents; the caller can then send the child to Blender as a new draft.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from psyteardown.experience.models import (
    DesignCandidate,
    DesignVariableValue,
    ModelLayerStatus,
    ProgressiveDesignModel,
    RevisionMeta,
    VariablePatch,
)


# These are intentionally a small, explicit contract.  Unknown variable IDs
# fail instead of being silently ignored, which keeps a patch trace useful.
PATCHABLE_VARIABLES = frozenset(
    {
        "wearable.form_factor",
        "wearable.body_placement",
        "wearable.attachment_strategy",
        "wearable.attachment",
        "wearable.contact_area",
        "wearable.mass_distribution",
        "feedback.modality",
        "feedback.timing",
        "feedback.confirmation",
        "device.visible_state",
        "control.cancel_action",
    }
)
ALLOWED_FORM_FACTORS = frozenset(
    {"desktop_device", "wearable", "handheld", "earbud_case", "phone_case", "portable_object"}
)
ALLOWED_FEEDBACK_MODALITIES = frozenset(
    {"private_haptic", "public_audio", "visual", "in_ear_voice", "none"}
)
VARIABLE_ALIASES = {"wearable.attachment": "wearable.attachment_strategy"}


def canonical_variable_id(variable_id: str) -> str:
    """Return the canonical design-variable name for compatibility aliases."""
    return VARIABLE_ALIASES.get(variable_id, variable_id)


def _child_id(parent: DesignCandidate, patches: tuple[VariablePatch, ...]) -> str:
    digest = hashlib.sha256(
        (parent.candidate_revision_id + "|" + "|".join(p.revision_id for p in patches)).encode()
    ).hexdigest()[:12]
    return f"{parent.candidate_id}.iter-{digest}"


def _display(value: DesignVariableValue | None) -> str | None:
    return None if value is None else value.display_value


def _replace_variable(
    values: tuple[DesignVariableValue, ...], patch: VariablePatch
) -> tuple[DesignVariableValue, ...]:
    if patch.operation in {"constrain", "relax"}:
        # Constraints change the review contract, not the candidate fact.
        return values
    if patch.to_value is None and patch.operation != "remove":
        raise ValueError(f"patch {patch.revision_id} requires to_value")
    changed = False
    result: list[DesignVariableValue] = []
    for value in values:
        if value.variable_id == patch.variable_id:
            if patch.operation in {"add", "remove"}:
                if patch.operation == "remove" and patch.to_value is None:
                    # A remove without a delta removes the declared variable
                    # entirely.  This is useful for dropping an optional
                    # control from a child candidate and is valid under the
                    # VariablePatch contract.
                    changed = True
                    continue
                if value.value_type != "set" or patch.to_value is None or patch.to_value.value_type != "set":
                    raise ValueError(f"patch {patch.revision_id} add/remove requires set values")
                current = tuple(value.normalized_value or ())
                delta = tuple(patch.to_value.normalized_value or ())
                merged = tuple(dict.fromkeys((*current, *delta))) if patch.operation == "add" else tuple(item for item in current if item not in delta)
                result.append(value.model_copy(update={"normalized_value": merged, "display_value": ", ".join(merged), "missing_reason": None}))
            else:
                result.append(patch.to_value)
            changed = True
        else:
            result.append(value)
    if not changed:
        if patch.operation != "remove":
            result.append(patch.to_value)
    return tuple(result)


def apply_variable_patches_to_candidate(
    parent: DesignCandidate,
    patches: Iterable[VariablePatch],
    *,
    actor: str = "system",
) -> DesignCandidate:
    """Create a child candidate by applying confirmed variable patches.

    Scope and confirmation are checked here, while the semantic review gate
    remains in :mod:`rules`.  A patch that cannot be projected is retained in
    the child declaration but does not pretend to have changed geometry.
    """

    patch_tuple = tuple(
        patch.model_copy(
            update={
                "variable_id": canonical_variable_id(patch.variable_id),
                "from_value": patch.from_value.model_copy(update={"variable_id": canonical_variable_id(patch.from_value.variable_id)}) if patch.from_value else None,
                "to_value": patch.to_value.model_copy(update={"variable_id": canonical_variable_id(patch.to_value.variable_id)}) if patch.to_value else None,
            }
        )
        for patch in patches
    )
    if not patch_tuple:
        raise ValueError("at least one VariablePatch is required")
    invalid = [p.revision_id for p in patch_tuple if p.status != "confirmed"]
    if invalid:
        raise ValueError("only confirmed patches can create a child candidate: " + ", ".join(invalid))
    unknown = [p.variable_id for p in patch_tuple if p.variable_id not in PATCHABLE_VARIABLES]
    if unknown:
        raise ValueError("unsupported patch variable(s): " + ", ".join(sorted(set(unknown))))

    values = tuple(parent.variables)
    current_values = {value.variable_id: value for value in values}
    shape = parent.shape
    design = parent.design
    for patch in patch_tuple:
        current = current_values.get(patch.variable_id)
        if patch.from_value is not None:
            if current is None or current.normalized_value != patch.from_value.normalized_value:
                raise ValueError(
                    f"stale patch {patch.revision_id}: from_value does not match parent variable {patch.variable_id}"
                )
        values = _replace_variable(values, patch)
        current_values = {value.variable_id: value for value in values}
        if shape is not None and patch.operation == "remove" and patch.to_value is None:
            optional_fields = {
                "wearable.body_placement": "body_placement",
                "wearable.attachment_strategy": "attachment_strategy",
                "wearable.attachment": "attachment_strategy",
                "wearable.contact_area": "contact_area",
                "wearable.mass_distribution": "mass_distribution",
                "feedback.modality": "feedback_modality",
                "feedback.timing": "feedback_timing",
                "feedback.confirmation": "confirmation_action",
            }
            field = optional_fields.get(patch.variable_id)
            if field:
                shape = shape.model_copy(update={field: None})
            elif patch.variable_id in {"wearable.form_factor", "device.visible_state", "control.cancel_action"}:
                raise ValueError(f"patch {patch.revision_id} cannot remove required variable {patch.variable_id}")
        if shape is not None and patch.to_value is not None and patch.operation not in {"constrain", "relax"}:
            target = patch.to_value.normalized_value
            text = _display(patch.to_value) or str(target)
            if patch.variable_id == "wearable.form_factor":
                if target not in ALLOWED_FORM_FACTORS:
                    raise ValueError(f"unsupported wearable.form_factor value: {target!r}")
                shape = shape.model_copy(update={"form_factor": target})
            elif patch.variable_id == "wearable.body_placement":
                shape = shape.model_copy(update={"body_placement": text})
            elif patch.variable_id in {"wearable.attachment_strategy", "wearable.attachment"}:
                shape = shape.model_copy(update={"attachment_strategy": text})
            elif patch.variable_id == "device.visible_state":
                shape = shape.model_copy(update={"visible_state": text})
            elif patch.variable_id in {"wearable.contact_area", "wearable.mass_distribution"}:
                marker = f"{patch.variable_id}={text} (declared; requires physical validation)"
                unknowns = tuple(item for item in shape.physical_unknowns if not item.startswith(patch.variable_id + "="))
                field = "contact_area" if patch.variable_id.endswith("contact_area") else "mass_distribution"
                shape = shape.model_copy(update={field: text, "physical_unknowns": unknowns + (marker,)})
            elif patch.variable_id == "control.cancel_action":
                shape = shape.model_copy(update={"interaction_surface": f"{shape.interaction_surface}; cancel: {text}"})
            elif patch.variable_id == "feedback.confirmation":
                shape = shape.model_copy(update={"interaction_surface": f"{shape.interaction_surface}; confirmation: {text}", "confirmation_action": text})
            elif patch.variable_id in {"feedback.modality", "feedback.timing"}:
                if patch.variable_id == "feedback.modality":
                    if target not in ALLOWED_FEEDBACK_MODALITIES:
                        raise ValueError(f"unsupported feedback.modality value: {target!r}")
                    shape = shape.model_copy(update={"feedback_surface": f"{text} feedback with optional state light", "feedback_modality": text})
                else:
                    shape = shape.model_copy(update={"feedback_timing": text})

        if design is not None:
            updates: dict[str, object] = {}
            if shape is not None:
                updates["shape"] = shape
            if patch.variable_id == "feedback.modality" and patch.to_value is not None:
                modality = str(patch.to_value.normalized_value)
                allowed = {"private_haptic", "public_audio", "visual", "in_ear_voice", "none"}
                if modality in allowed:
                    updates["feedback_behavior"] = tuple(design.feedback_behavior) + (f"primary modality: {modality}",)
            elif patch.variable_id == "feedback.timing" and patch.to_value is not None:
                updates["feedback_behavior"] = tuple(design.feedback_behavior) + (f"timing policy: {patch.to_value.display_value}",)
            elif patch.variable_id == "control.cancel_action" and patch.to_value is not None:
                updates["privacy_and_control"] = tuple(design.privacy_and_control) + (f"cancel action: {patch.to_value.display_value}",)
            if updates:
                design = design.model_copy(update=updates)

    # Apply event-level changes for variables whose semantics are explicit in
    # the domain model.  Other physical variables stay as declared values.
    events = list(parent.events)
    for patch in patch_tuple:
        if patch.to_value is None or patch.operation in {"constrain", "relax"}:
            continue
        if patch.variable_id == "feedback.modality" and patch.to_value.normalized_value in ALLOWED_FEEDBACK_MODALITIES:
            modality = patch.to_value.normalized_value
            events = [
                event.model_copy(
                    update={
                        "feedback_steps": tuple(
                            step.model_copy(update={"modality": modality})
                            if patch.variable_id in step.variable_refs else step
                            for step in event.feedback_steps
                        )
                    }
                )
                for event in events
            ]
        elif patch.variable_id == "feedback.timing":
            timing = patch.to_value.display_value
            events = [
                event.model_copy(
                    update={
                        "feedback_steps": tuple(
                            step.model_copy(update={"timing": timing})
                            if patch.variable_id in step.variable_refs else step
                            for step in event.feedback_steps
                        )
                    }
                )
                for event in events
            ]

    child_id = _child_id(parent, patch_tuple)
    if design is not None:
        design = design.model_copy(update={"design_id": f"{child_id}.design", "shape": shape})
    reason = "parameterized VariablePatch iteration"
    declarations = dict(parent.generator_application_declarations)
    declarations.update({p.patch_id: "parameterized projection generated; requires human confirmation" for p in patch_tuple})
    return parent.model_copy(
        update={
            "candidate_id": child_id,
            "candidate_revision_id": f"{child_id}.r1",
            "meta": RevisionMeta(revision=1, parent_revision_id=parent.candidate_revision_id, created_by=actor, reason=reason),
            "parent_candidate_revision_id": parent.candidate_revision_id,
            "status": "generation_invalid" if parent.validation_issues else "input_valid",
            "changed_variable_ids": tuple(dict.fromkeys((*parent.changed_variable_ids, *(p.variable_id for p in patch_tuple)))),
            "variables": values,
            "events": tuple(events),
            "shape": shape,
            "design": design,
            "generator_application_declarations": tuple(sorted(declarations.items())),
        }
    )


def create_patched_progressive_model(
    parent: ProgressiveDesignModel,
    child: DesignCandidate,
    patches: Iterable[VariablePatch],
    *,
    actor: str = "system",
    revision: int | None = None,
) -> ProgressiveDesignModel:
    """Create a child convergence snapshot and invalidate stale render assets."""

    patch_tuple = tuple(patches)
    if child.parent_candidate_revision_id != parent.candidate_revision_id:
        raise ValueError("child candidate must point at the progressive model candidate revision")
    next_revision = revision if revision is not None else parent.meta.revision + 1
    if next_revision <= parent.meta.revision:
        raise ValueError("patched progressive-model revision must advance the parent revision")
    reset_layers: list[ModelLayerStatus] = []
    for layer in parent.layers:
        if layer.layer == "structured_design":
            reset_layers.append(layer.model_copy(update={"status": "complete" if child.design else "missing", "artifact_refs": ((child.design.design_id,) if child.design else ())}))
        elif layer.layer in {"render_assets", "geometry"}:
            reset_layers.append(layer.model_copy(update={"status": "missing", "artifact_refs": (), "gaps": ("new parameterized revision requires a fresh provider draft",)}))
        else:
            reset_layers.append(layer)
    return parent.model_copy(
        update={
            "revision_id": f"{parent.model_id}.r{next_revision}",
            "meta": RevisionMeta(revision=next_revision, parent_revision_id=parent.revision_id, created_by=actor, reason="parameterized VariablePatch revision"),
            "candidate_revision_id": child.candidate_revision_id,
            "stage": "structured_design",
            "layers": tuple(reset_layers),
            "applied_patch_revision_ids": tuple(dict.fromkeys((*parent.applied_patch_revision_ids, *(p.revision_id for p in patch_tuple)))),
            "provider_result_ids": (),
            "scenario_policy_revision_ids": parent.scenario_policy_revision_ids,
            "unresolved_gaps": tuple(dict.fromkeys((*parent.unresolved_gaps, "parameterized geometry requires human review", "contact pressure, fit and motion stability remain unverified"))),
        }
    )


def build_patchable_variable_catalog() -> tuple[dict[str, object], ...]:
    """Return the UI/provider contract without exposing Pydantic internals."""

    return (
        {"variable_id": "wearable.form_factor", "value_type": "enum", "examples": sorted(ALLOWED_FORM_FACTORS)},
        {"variable_id": "wearable.body_placement", "value_type": "enum", "examples": ["dorsal wrist"]},
        {"variable_id": "wearable.attachment_strategy", "value_type": "enum", "examples": ["broad vented strap with keyed clasp"]},
        {"variable_id": "wearable.contact_area", "value_type": "enum", "examples": ["broad compliant underside"]},
        {"variable_id": "wearable.mass_distribution", "value_type": "enum", "examples": ["centered over wrist axis"]},
        {"variable_id": "feedback.modality", "value_type": "enum", "examples": sorted(ALLOWED_FEEDBACK_MODALITIES)},
        {"variable_id": "feedback.timing", "value_type": "enum", "examples": ["bounded boundary pulse"]},
        {"variable_id": "feedback.confirmation", "value_type": "enum", "examples": ["recessed press-hold"]},
        {"variable_id": "device.visible_state", "value_type": "enum", "examples": ["wearer-facing state edge"]},
        {"variable_id": "control.cancel_action", "value_type": "enum", "examples": ["recessed one-handed press-hold"]},
    )
