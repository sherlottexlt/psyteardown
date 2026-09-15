"""Deterministic engineering preflight for the Transit Anchor concept.

This module intentionally models only first-order mechanics from declared
assumptions.  It is useful for choosing what to prototype next, but its
outputs are not prototype measurements and cannot be promoted to evidence.
"""

from __future__ import annotations

from math import pi
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VirtualDeviceAssumptions(BaseModel):
    """Declared values for a virtual, not-yet-built Round 2 device."""

    model_config = ConfigDict(extra="forbid")

    body_length_mm: float = Field(gt=0)
    body_width_mm: float = Field(gt=0)
    body_height_mm: float = Field(gt=0)
    mass_g: float = Field(gt=0)
    contact_area_cm2: float = Field(gt=0)
    nominal_strap_tension_n: float = Field(gt=0)
    strap_stiffness_n_per_mm: float = Field(gt=0)
    rotational_stiffness_nm_per_rad: float = Field(gt=0)
    center_offset_mm: float = Field(ge=0)
    lift_tab_protrusion_mm: float = Field(ge=0)
    release_force_n: float = Field(gt=0)
    release_travel_mm: float = Field(gt=0)
    hold_target_ms: float = Field(gt=0)


class VirtualCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str = Field(min_length=1)
    peak_acceleration_g: float = Field(ge=0)
    friction_coefficient: float = Field(gt=0, le=1)
    release_time_add_ms: float = Field(ge=0)
    incidental_contact_ms: float = Field(ge=0)
    notes: str = Field(min_length=1)


class VirtualThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_displacement_mm: float = Field(gt=0)
    max_rotation_deg: float = Field(gt=0)
    max_continuous_pressure_kpa: float = Field(gt=0)
    max_transient_pressure_kpa: float = Field(gt=0)
    max_release_force_n: float = Field(gt=0)
    max_release_time_ms: float = Field(gt=0)
    min_false_activation_hold_ratio: float = Field(gt=1)


class VirtualValidationInput(BaseModel):
    """Input contract for a reproducible virtual engineering preflight."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transit-anchor-virtual-validation/v1"] = "transit-anchor-virtual-validation/v1"
    case_id: str = Field(min_length=1)
    candidate_revision_id: str = Field(min_length=1)
    model_revision_id: str = Field(min_length=1)
    patch_revision_id: str = Field(min_length=1)
    device_assumptions: VirtualDeviceAssumptions
    conditions: tuple[VirtualCondition, ...] = Field(min_length=1)
    thresholds: VirtualThresholds
    declared_unknowns: tuple[str, ...] = ()


class VirtualMetricResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    condition_id: str | None = None
    value: float | None = None
    unit: str | None = None
    threshold: float | None = None
    status: Literal["pass_estimate", "risk_estimate", "not_modelled"]
    basis: str
    evidence_eligible: Literal[False] = False


class VirtualValidationReport(BaseModel):
    """Report whose values are explicitly ineligible for prototype evidence."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transit-anchor-virtual-validation-report/v1"] = "transit-anchor-virtual-validation-report/v1"
    case_id: str
    candidate_revision_id: str
    model_revision_id: str
    patch_revision_id: str
    method: str
    evidence_level: Literal["none"] = "none"
    evidence_eligible: Literal[False] = False
    assumptions: VirtualDeviceAssumptions
    conditions: tuple[VirtualCondition, ...]
    thresholds: VirtualThresholds
    results: tuple[VirtualMetricResult, ...]
    decision: Literal["proceed_to_physical_prototype", "revise_before_prototype"]
    limitations: tuple[str, ...]
    next_physical_tests: tuple[str, ...]


_G = 9.80665


def _status(value: float, threshold: float) -> Literal["pass_estimate", "risk_estimate"]:
    return "pass_estimate" if value <= threshold else "risk_estimate"


def run_virtual_validation(spec: VirtualValidationInput) -> VirtualValidationReport:
    """Run first-order mechanics without inventing measurement data.

    The friction model treats the split strap as an equivalent normal force;
    it deliberately does not claim to model skin compliance, buckle geometry,
    sweat film dynamics or fabric snag probability.
    """

    device = spec.device_assumptions
    thresholds = spec.thresholds
    mass_kg = device.mass_g / 1000.0
    contact_area_m2 = device.contact_area_cm2 / 10_000.0
    body_lever_m = max(device.body_width_mm / 2.0, 1.0) / 1000.0
    offset_m = device.center_offset_mm / 1000.0
    results: list[VirtualMetricResult] = []

    max_risk = False
    for condition in spec.conditions:
        inertial_force = mass_kg * condition.peak_acceleration_g * _G
        friction_capacity = device.nominal_strap_tension_n * condition.friction_coefficient
        margin = friction_capacity - inertial_force
        # Below the static-friction limit, treat the body as elastically
        # compliant.  Once the limit is exceeded, report the full elastic
        # excursion as a conservative risk estimate.
        displacement = inertial_force / device.strap_stiffness_n_per_mm
        if margin >= 0:
            displacement *= 0.25
        else:
            displacement *= 1.0 + min(abs(margin) / max(friction_capacity, 1e-9), 2.0)
        torque = inertial_force * offset_m
        resisting_torque = friction_capacity * body_lever_m
        rotation_rad = torque / device.rotational_stiffness_nm_per_rad
        if resisting_torque < torque:
            rotation_rad *= 1.0 + min((torque - resisting_torque) / max(torque, 1e-9), 1.0)
        rotation_deg = rotation_rad * 180.0 / pi

        pressure_kpa = (device.nominal_strap_tension_n + mass_kg * _G) / contact_area_m2 / 1000.0
        pressure_transient_kpa = pressure_kpa * (1.0 + min(condition.peak_acceleration_g / 10.0, 0.5))

        displacement_status = _status(displacement, thresholds.max_displacement_mm)
        rotation_status = _status(rotation_deg, thresholds.max_rotation_deg)
        continuous_pressure_status = _status(pressure_kpa, thresholds.max_continuous_pressure_kpa)
        transient_pressure_status = _status(pressure_transient_kpa, thresholds.max_transient_pressure_kpa)
        max_risk = max_risk or any(
            status == "risk_estimate"
            for status in (
                displacement_status,
                rotation_status,
                continuous_pressure_status,
                transient_pressure_status,
            )
        )
        results.extend(
            (
                VirtualMetricResult(
                    metric_id="fit-displacement",
                    condition_id=condition.condition_id,
                    value=round(displacement, 3),
                    unit="mm",
                    threshold=thresholds.max_displacement_mm,
                    status=displacement_status,
                    basis=(
                        f"m*a={inertial_force:.3f} N; friction capacity={friction_capacity:.3f} N; "
                        f"margin={margin:.3f} N"
                    ),
                ),
                VirtualMetricResult(
                    metric_id="fit-rotation",
                    condition_id=condition.condition_id,
                    value=round(rotation_deg, 3),
                    unit="deg",
                    threshold=thresholds.max_rotation_deg,
                    status=rotation_status,
                    basis=f"inertial torque={torque:.5f} N·m; resisting torque={resisting_torque:.5f} N·m",
                ),
                VirtualMetricResult(
                    metric_id="contact-pressure-continuous",
                    condition_id=condition.condition_id,
                    value=round(pressure_kpa, 3),
                    unit="kPa",
                    threshold=thresholds.max_continuous_pressure_kpa,
                    status=continuous_pressure_status,
                    basis=f"normal load={device.nominal_strap_tension_n + mass_kg * _G:.3f} N over {device.contact_area_cm2:.2f} cm²",
                ),
                VirtualMetricResult(
                    metric_id="contact-pressure-transient",
                    condition_id=condition.condition_id,
                    value=round(pressure_transient_kpa, 3),
                    unit="kPa",
                    threshold=thresholds.max_transient_pressure_kpa,
                    status=transient_pressure_status,
                    basis="continuous pressure multiplied by bounded acceleration transient factor",
                ),
            )
        )

        release_time = device.hold_target_ms + condition.release_time_add_ms
        hold_ratio = device.hold_target_ms / max(condition.incidental_contact_ms, 1e-9)
        release_status = "pass_estimate" if release_time <= thresholds.max_release_time_ms else "risk_estimate"
        activation_status = "pass_estimate" if hold_ratio >= thresholds.min_false_activation_hold_ratio else "risk_estimate"
        force_status = _status(device.release_force_n, thresholds.max_release_force_n)
        max_risk = max_risk or release_status == "risk_estimate" or activation_status == "risk_estimate" or force_status == "risk_estimate"
        results.extend(
            (
                VirtualMetricResult(
                    metric_id="one-hand-release-time",
                    condition_id=condition.condition_id,
                    value=round(release_time, 1),
                    unit="ms",
                    threshold=thresholds.max_release_time_ms,
                    status=release_status,
                    basis=f"hold target={device.hold_target_ms:.0f} ms + condition allowance={condition.release_time_add_ms:.0f} ms",
                ),
                VirtualMetricResult(
                    metric_id="release-force",
                    condition_id=condition.condition_id,
                    value=round(device.release_force_n, 2),
                    unit="N",
                    threshold=thresholds.max_release_force_n,
                    status=force_status,
                    basis=f"assumed lift travel={device.release_travel_mm:.1f} mm; force is a design assumption, not a measurement",
                ),
                VirtualMetricResult(
                    metric_id="false-activation-hold-ratio",
                    condition_id=condition.condition_id,
                    value=round(hold_ratio, 2),
                    unit="ratio",
                    threshold=thresholds.min_false_activation_hold_ratio,
                    status=activation_status,
                    basis=f"intentional hold={device.hold_target_ms:.0f} ms / incidental contact={condition.incidental_contact_ms:.0f} ms",
                ),
            )
        )

    results.extend(
        (
            VirtualMetricResult(
                metric_id="haptic-detectability",
                status="not_modelled",
                basis="skin, vibration, sleeve and attention interactions require a physical detection task",
            ),
            VirtualMetricResult(
                metric_id="sleeve-snag-probability",
                status="not_modelled",
                basis="lift-tab protrusion is declared, but fabric snag needs controlled sleeve trials",
            ),
            VirtualMetricResult(
                metric_id="privacy-content-leakage",
                status="not_modelled",
                basis="bystander inference requires an observer task and cannot be derived from mechanics",
            ),
        )
    )

    return VirtualValidationReport(
        case_id=spec.case_id,
        candidate_revision_id=spec.candidate_revision_id,
        model_revision_id=spec.model_revision_id,
        patch_revision_id=spec.patch_revision_id,
        method="deterministic first-order mechanics with declared assumptions; no sensor, participant or physical-run data",
        assumptions=device,
        conditions=spec.conditions,
        thresholds=thresholds,
        results=tuple(results),
        decision="revise_before_prototype" if max_risk else "proceed_to_physical_prototype",
        limitations=(
            "All numeric values are engineering estimates, not observed measurements.",
            "The equivalent friction model does not represent skin compliance, sweat-film dynamics, buckle geometry or textile snag probability.",
            "Pressure thresholds are pre-registration assumptions and must be reviewed before any human test.",
            "Haptic detectability, long-term comfort, skin safety, privacy leakage and reliability remain unmodelled.",
        ),
        next_physical_tests=(
            "Measure displacement and rotation with wrist circumference, sleeve and sweat proxies.",
            "Measure one-hand release force/time and record sleeve snag events.",
            "Measure contact pressure and temperature during a short controlled wear screen.",
            "Run stop-path and haptic detection tasks; keep their observations separate from this virtual report.",
        ),
    )


def render_virtual_validation_markdown(report: VirtualValidationReport) -> str:
    """Render a report with repeated non-evidence boundaries."""

    lines = [
        "# Transit Anchor — virtual engineering preflight",
        "",
        f"- **Case:** `{report.case_id}`",
        f"- **Candidate:** `{report.candidate_revision_id}`",
        f"- **Model:** `{report.model_revision_id}`",
        f"- **Patch:** `{report.patch_revision_id}`",
        f"- **Decision:** `{report.decision}`",
        "- **Evidence level:** `none`",
        "- **Evidence eligible:** `false`",
        "",
        "> This is a deterministic estimate from declared assumptions. It is not a physical prototype run, participant result or prototype evidence.",
        "",
        "## Declared device assumptions",
        "",
    ]
    for key, value in report.assumptions.model_dump().items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Estimated results", "", "| Metric | Condition | Value | Threshold | Status | Basis |", "| --- | --- | ---: | ---: | --- | --- |"])
    for result in report.results:
        value = "—" if result.value is None else f"{result.value:g} {result.unit or ''}".strip()
        threshold = "—" if result.threshold is None else f"{result.threshold:g} {result.unit or ''}".strip()
        lines.append(f"| {result.metric_id} | {result.condition_id or 'all'} | {value} | {threshold} | `{result.status}` | {result.basis} |")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    lines.extend(["", "## Required physical follow-up", ""])
    lines.extend(f"- {item}" for item in report.next_physical_tests)
    lines.extend(["", "_This report must not be imported through `prototype-import` or promoted by `prototype-review`._"])
    return "\n".join(lines)
