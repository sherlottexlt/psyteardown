"""Deterministic P1 rules for image/video observation drafts.

Multimodal providers produce drafts and locators, never confirmed facts.  The
functions in this module make missing modalities and non-observable physical
claims explicit before a named human can review the draft.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from psyteardown.experience.models import ExternalAsset, ImageRegion, ObservationDraft


_PROTECTED_TERMS: dict[str, tuple[str, ...]] = {
    "dimension": (
        "dimension", "dimensions", "length", "width", "height", "thickness",
        "diameter", "radius", "clearance", "tolerance", "尺寸", "长度", "宽度",
        "高度", "厚度", "直径", "半径", "间隙", "公差",
    ),
    "pressure": (
        "pressure", "compression", "contact load", "压强", "压力", "压迫", "接触载荷",
    ),
    "strength": (
        "strength", "tensile", "yield stress", "stress", "load capacity", "structural load",
        "强度", "拉伸", "屈服", "应力", "承重", "载荷", "刚度",
    ),
    "comfort": (
        "comfort", "comfortable", "comfortableness", "ergonomic fit", "舒适", "舒服", "佩戴感受",
    ),
}


def classify_observation_claim(draft: ObservationDraft, *, value: str | None = None) -> str:
    """Return the strongest protected claim category found in a draft."""
    text = " ".join((draft.subject, draft.predicate, value or draft.proposed_value)).lower()
    for category in ("comfort", "pressure", "strength", "dimension"):
        if any(term in text for term in _PROTECTED_TERMS[category]):
            return category
    if re.search(r"(?:^|\s)\d+(?:\.\d+)?\s*(?:mm|cm|m|in|inch|英寸|毫米|厘米)(?:\s|$)", text):
        return "dimension"
    return draft.claim_category


def normalize_multimodal_draft(
    draft: ObservationDraft,
    assets: Mapping[str, ExternalAsset],
) -> ObservationDraft:
    """Validate locators and explicitly downgrade missing input modalities."""
    referenced = tuple(assets[asset_id] for asset_id in draft.asset_ids)
    available = {asset.modality for asset in referenced if asset.status == "imported"}
    required = set(draft.required_modalities)
    if draft.image_region is not None:
        required.add("image")
    segment = draft.effective_video_segment
    if segment is not None:
        required.add("video")

    missing = set(draft.missing_modalities)
    missing.update(required - available)
    for asset in referenced:
        if asset.status != "imported":
            if asset.modality in {"image", "video", "audio", "geometry", "cad"}:
                missing.add(asset.modality)

    if segment is not None:
        for asset in referenced:
            if asset.modality == "video" and asset.duration_ms is not None and segment.end_ms > asset.duration_ms:
                raise ValueError(f"video segment exceeds duration of asset {asset.asset_id}")

    if isinstance(draft.image_region, ImageRegion) and draft.image_region.coordinate_space == "pixels":
        for asset in referenced:
            if asset.modality != "image" or asset.width_px is None or asset.height_px is None:
                continue
            if (
                draft.image_region.x + draft.image_region.width > asset.width_px
                or draft.image_region.y + draft.image_region.height > asset.height_px
            ):
                raise ValueError(f"image region exceeds pixel bounds of asset {asset.asset_id}")

    if not missing:
        return draft
    limitation = "required source modality unavailable: " + ", ".join(sorted(missing))
    return draft.model_copy(update={
        "observable_status": "unknown" if draft.observable_status == "draft" else draft.observable_status,
        "missing_modalities": tuple(sorted(missing)),
        "not_observable_items": tuple(dict.fromkeys((*draft.not_observable_items, draft.predicate))),
        "limitations": tuple(dict.fromkeys((*draft.limitations, limitation))),
    })


def multimodal_confirmation_issues(
    draft: ObservationDraft,
    assets: Iterable[ExternalAsset],
    *,
    value: str | None = None,
) -> tuple[str, ...]:
    """Return deterministic reasons why a media draft cannot become a fact."""
    assets = tuple(assets)
    issues: list[str] = []
    if draft.observable_status != "draft":
        issues.append(f"observable_status_{draft.observable_status}")
    if draft.missing_modalities:
        issues.append("required_modality_missing")

    category = classify_observation_claim(draft, value=value)
    visual = tuple(asset for asset in assets if asset.modality in {"image", "video"})
    design_media = tuple(asset for asset in assets if asset.modality in {"image", "video", "geometry", "cad"})

    if category == "dimension":
        if any(asset.modality == "geometry" or asset.provenance in {"blender_derived", "design_derived"} for asset in design_media):
            issues.append("derived_design_asset_cannot_establish_dimensions")
        if any(asset.calibration_status != "calibrated" or not asset.calibration_ref for asset in visual):
            issues.append("uncalibrated_media_cannot_establish_dimensions")
    elif category in {"pressure", "strength", "comfort"} and design_media:
        issues.append(f"design_media_cannot_establish_{category}")
    return tuple(dict.fromkeys(issues))


def multimodal_source_locator(draft: ObservationDraft, assets: Iterable[ExternalAsset]) -> str:
    """Render stable region/time/calibration provenance for a confirmation."""
    parts: list[str] = []
    segment = draft.effective_video_segment
    for asset in assets:
        locator = f"asset:{asset.asset_id}#sha256:{asset.sha256}"
        if asset.modality == "image" and draft.image_region is not None:
            if isinstance(draft.image_region, ImageRegion):
                region = draft.image_region
                locator += f"#region:{region.x},{region.y},{region.width},{region.height}:{region.coordinate_space}"
            else:
                locator += f"#region:{draft.image_region}"
        if asset.modality == "video" and segment is not None:
            locator += f"#time:{segment.start_ms}-{segment.end_ms}ms"
        if asset.calibration_ref:
            locator += f"#calibration:{asset.calibration_ref}"
        parts.append(locator)
    return ";".join(parts)


def is_named_human_actor(actor: str) -> bool:
    """Reject obvious automated principals at the human review boundary."""
    normalized = actor.strip().lower()
    if not normalized:
        return False
    exact_automated = {"ai", "system", "model", "provider", "assistant", "agent", "automation", "worker"}
    automated_prefixes = (
        "ai-", "model-", "provider-", "assistant-", "agent-", "automation-", "worker-",
        "system-bot", "system-agent", "system-worker", "system-automation",
    )
    return normalized not in exact_automated and not normalized.startswith(automated_prefixes)


__all__ = [
    "classify_observation_claim",
    "normalize_multimodal_draft",
    "multimodal_confirmation_issues",
    "multimodal_source_locator",
    "is_named_human_actor",
]
