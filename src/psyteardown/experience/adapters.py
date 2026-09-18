"""Stable bridge for future design tools and render/geometry providers.

The adapter returns an untrusted derived asset.  A human confirmation command
is required before the asset is attached to a progressive design model.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import Field

from psyteardown.experience.models import (
    BoundaryModel,
    DesignCandidate,
    DesignRuleSet,
    ModelLayerStatus,
    ProgressiveDesignModel,
    RevisionMeta,
    VariablePatch,
    ExternalAsset,
)


class DesignToolRequest(BoundaryModel):
    request_id: str = Field(default_factory=lambda: f"design-tool-request-{uuid4().hex[:12]}")
    candidate_revision_id: str
    prompt_projection: str
    requested_outputs: list[str] = Field(default_factory=lambda: ["render_2d", "geometry_3d"])
    constraints: list[str] = Field(default_factory=list)
    scene_spec: dict[str, object] | None = None
    parent_model_revision_id: str | None = None
    patch_revision_ids: list[str] = Field(default_factory=list)


class DesignToolResult(BoundaryModel):
    result_id: str = Field(default_factory=lambda: f"design-tool-result-{uuid4().hex[:12]}")
    request_id: str
    candidate_revision_id: str
    provider: str
    model: str
    status: Literal["draft"] = "draft"
    render_asset_refs: list[str] = Field(default_factory=list)
    geometry_asset_refs: list[str] = Field(default_factory=list)
    derived_review_views: dict[str, str] = Field(default_factory=dict)
    asset_hashes: dict[str, str] = Field(default_factory=dict)
    engineering_spec_refs: list[str] = Field(default_factory=list)
    declared_notes: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class DesignToolProvider(Protocol):
    def generate(self, request: DesignToolRequest) -> DesignToolResult: ...


class BlenderProviderError(RuntimeError):
    """Blender executable, script or export failed."""


def build_external_asset(
    path: str | Path,
    *,
    provider: str,
    asset_id: str | None = None,
    request_id: str | None = None,
    candidate_revision_id: str | None = None,
    model_revision_id: str | None = None,
    asset_kind: str | None = None,
    actor: str = "system",
) -> ExternalAsset:
    """Create a hash-addressed external asset descriptor from a local file."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    inferred_kind = asset_kind or (file_path.suffix.lower().lstrip(".") or "other")
    if inferred_kind not in {
        "glb", "gltf", "png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif",
        "mp4", "mov", "webm", "mkv", "m4v", "avi", "wav", "mp3", "cad", "other",
    }:
        inferred_kind = "other"
    stable_id = asset_id or f"external-asset-{digest[:12]}"
    return ExternalAsset(
        asset_id=stable_id,
        revision_id=f"{stable_id}.r1",
        meta=RevisionMeta(revision=1, created_by=actor, reason="external asset hashed"),
        uri=str(file_path.resolve()),
        sha256=digest,
        provider=provider,
        request_id=request_id,
        asset_kind=inferred_kind,
        provenance="blender_derived" if provider.lower() == "blender" else "external",
        candidate_revision_id=candidate_revision_id,
        model_revision_id=model_revision_id,
    )


def resolve_blender_executable(executable: str | Path | None = None) -> str:
    """Resolve Blender from an explicit path, env var, or PATH."""

    if executable is not None:
        return str(executable)
    configured = os.environ.get("PSYTEARDOWN_BLENDER")
    if configured:
        return configured
    return shutil.which("blender") or "blender"


def _blender_scene_script(request: DesignToolRequest, output_dir: Path) -> str:
    """Build a self-contained Blender Python script from a safe JSON spec."""

    scene_json = json.dumps(request.scene_spec or {}, ensure_ascii=False, sort_keys=True)
    output_json = json.dumps(str(output_dir.resolve()), ensure_ascii=False)
    request_json = json.dumps(request.request_id, ensure_ascii=False)
    outputs_json = json.dumps(request.requested_outputs, ensure_ascii=False)
    # The script intentionally uses only bpy primitives.  It is a first-pass
    # blockout, not a claim that the physical proportions or materials are
    # production-ready.
    return f'''import bpy
import json
import math
import os
import mathutils

OUTPUT_DIR = {output_json}
SCENE_SPEC = json.loads({scene_json!r})
REQUEST_ID = {request_json!r}
REQUESTED_OUTPUTS = json.loads({outputs_json!r})
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, color, metallic=0.0, roughness=0.48):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)
    mat.metallic = metallic
    mat.roughness = roughness
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf is not None:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

shell = material('Soft-touch shell', (0.12, 0.18, 0.24), metallic=0.08, roughness=0.55)
accent = material('Status edge', (0.08, 0.55, 0.82), metallic=0.15, roughness=0.3)
surface = material('Confirmation surface', (0.18, 0.22, 0.26), metallic=0.0, roughness=0.7)

def cube(name, location, scale, mat, bevel=0.16):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel_mod = obj.modifiers.new('Softened edges', 'BEVEL')
    bevel_mod.width = bevel
    bevel_mod.segments = 4
    obj.data.materials.append(mat)
    return obj

def cylinder(name, location, radius, depth, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj

form = SCENE_SPEC.get('form_factor', 'portable_object')
geometry = SCENE_SPEC.get('geometry', {{}}) or {{}}
body_scale = tuple(geometry.get('body_scale', (1.25, 0.72, 0.35)))
strap_scale = tuple(geometry.get('strap_scale', (1.48, 0.18, 0.10)))
button_radius = float(geometry.get('button_radius', 0.23))
body_z = float(geometry.get('body_z', 0.45))
if form in ('wearable', 'worn_wrist', 'worn_neck', 'worn_torso'):
    body = cube('Low-profile wrist pod', (0, 0, body_z), body_scale, shell, min(0.22, body_scale[2] * 0.6))
    # A neutral wrist context proxy makes the wrap direction legible. It is
    # deliberately marked as derived/non-anatomical: no scale, fit or comfort
    # claim is inferred from this visualization.
    wrist_proxy_mat = material('Wrist context proxy (derived)', (0.28, 0.20, 0.16), roughness=0.82)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.70, depth=4.4, location=(0, 0, -0.20), rotation=(0, math.radians(90), 0))
    wrist_proxy = bpy.context.object
    wrist_proxy.name = 'Wrist context proxy (derived; non-anatomical scale)'
    wrist_proxy.data.materials.append(wrist_proxy_mat)
    wrist_proxy['review_note'] = 'context proxy only; not an anatomical or dimensional reference'
    # A torus around the forearm axis gives the review image a clear
    # wrap-around strap while keeping exact curvature and retention unknown.
    bpy.ops.mesh.primitive_torus_add(major_radius=0.78, minor_radius=max(strap_scale[1] * 0.62, 0.10), major_segments=64, minor_segments=16, location=(0, 0, -0.20), rotation=(0, math.radians(90), 0))
    strap = bpy.context.object
    strap.name = 'Broad vented reversible wrist strap (derived)'
    strap.scale = (1.0, 0.82, 0.72)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    strap.data.materials.append(surface)
    attachment_strategy = str((SCENE_SPEC.get('variables', {{}}) or {{}}).get('wearable.attachment_strategy', ''))
    if attachment_strategy == 'broad_vented_split_strap_low_profile_lift_release':
        # Derived review geometry for the Round 2 retention/release discussion:
        # two wrist-axis-separated bands, a low-profile lift tab and subtle
        # underside texture markers. These are not dimensional or retention
        # claims. Hide the baseline single band so the split construction is
        # legible in the GLB and review views.
        strap.hide_render = True
        strap.hide_viewport = True
        for band_name, x in (('proximal', -0.34), ('distal', 0.34)):
            bpy.ops.mesh.primitive_torus_add(
                major_radius=0.78,
                minor_radius=max(strap_scale[1] * 0.42, 0.08),
                major_segments=64,
                minor_segments=16,
                location=(x, 0, -0.20),
                rotation=(0, math.radians(90), 0),
            )
            band = bpy.context.object
            band.name = 'Split strap ' + band_name + ' band (derived)'
            band.scale = (1.0, 0.82, 0.72)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            band.data.materials.append(surface)
            band['review_note'] = 'split-band presentation geometry; slip and rotation require prototype measurement'
        lift_tab = cube('Low-profile lift-tab release (derived)', (0.34, -0.18, -0.83), (0.16, 0.055, 0.03), accent, 0.025)
        lift_tab['review_note'] = 'quick-release intent only; snag and one-hand release require prototype measurement'
        for index, x in enumerate((-0.50, -0.34, -0.18, 0.18, 0.34, 0.50)):
            texture = cube('Anti-rotation underside texture marker ' + str(index), (x, 0, -0.84), (0.045, 0.025, 0.012), accent, 0.008)
            texture['review_note'] = 'underside texture marker; pressure and friction remain unknown'
    # A small, recessed side control communicates the one-handed stop path.
    # Its dimensions are intentionally presentation parameters, not claims
    # about activation force or manufacturability.  The stop-control patch
    # adds raised front/back shoulders so the guard is visible in access views
    # and can be discussed separately from the press surface.
    cancel_action = str((SCENE_SPEC.get('variables', {{}}) or {{}}).get('control.cancel_action', ''))
    side_x = body_scale[0] + 0.035
    control = cube('Recessed tactile stop control', (side_x, 0, body_z), (0.035, body_scale[1] * 0.30, 0.06), accent, 0.02)
    control['review_note'] = 'derived presentation geometry; activation force and manufacturability remain unknown'
    if cancel_action == 'side_flush_guarded_press_hold':
        shoulder_y = body_scale[1] * 0.34
        shoulder_scale_y = max(body_scale[1] * 0.08, 0.045)
        for shoulder_name, y in (('front', -shoulder_y), ('back', shoulder_y)):
            shoulder = cube(
                'Stop-control ' + shoulder_name + ' shoulder (derived)',
                (body_scale[0] + 0.02, y, body_z + 0.025),
                (0.045, shoulder_scale_y, 0.095),
                shell,
                0.025,
            )
            shoulder['review_note'] = 'guard shoulder for side-flush press-hold; no force or snag claim'
elif form == 'handheld':
    body = cube('Handheld body', (0, 0, 0.55), (0.82, 1.25, 0.30), shell, 0.24)
elif form == 'earbud_case':
    body = cube('Earbud case body', (0, 0, 0.42), (0.92, 0.78, 0.28), shell, 0.25)
elif form == 'phone_case':
    body = cube('Phone case body', (0, 0, 0.42), (0.88, 1.60, 0.13), shell, 0.12)
else:
    body = cube('Portable body', (0, 0, 0.50), (1.0, 0.82, 0.38), shell, 0.22)

if form in ('wearable', 'worn_wrist', 'worn_neck', 'worn_torso'):
    confirm = cube('Concave confirmation pad (derived)', (0, -0.04, body_z + body_scale[2] + 0.035), (body_scale[0] * 0.30, body_scale[1] * 0.30, 0.025), surface, 0.04)
else:
    confirm = cylinder('Confirmation surface', (0, -0.78, 0.78), button_radius, 0.10, surface)
    confirm.rotation_euler[0] = math.radians(90)
status_z = body_z + body_scale[2] + 0.035 if form in ('wearable', 'worn_wrist', 'worn_neck', 'worn_torso') else 0.90
status = cube('Status edge', (0, 0, status_z), (body_scale[0] * 0.82 if form in ('wearable', 'worn_wrist', 'worn_neck', 'worn_torso') else 1.05, 0.035, 0.025), accent, 0.02)
if geometry.get('wearer_facing_status', True):
    status['visibility'] = 'wearer-facing state indicator only'

for index, component in enumerate(SCENE_SPEC.get('components', [])):
    empty = bpy.data.objects.new('Component: ' + str(component.get('name', index)), None)
    empty.empty_display_type = 'CUBE'
    empty.empty_display_size = 0.12
    empty['role'] = str(component.get('role', ''))
    empty['placement'] = str(component.get('placement', ''))
    bpy.context.collection.objects.link(empty)

# Ground and lighting make the render useful for visual review while keeping
# the original design facts separate from derived pixels.
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
ground = bpy.context.object
ground.name = 'Review ground (derived)'
ground.data.materials.append(material('Ground', (0.025, 0.03, 0.04), roughness=0.9))
bpy.ops.object.light_add(type='AREA', location=(3.5, -4.0, 5.0))
bpy.context.object.data.energy = 420
bpy.context.object.data.shape = 'DISK'
bpy.context.object.data.size = 4.0
bpy.ops.object.light_add(type='AREA', location=(-3.0, 1.5, 2.5))
bpy.context.object.data.energy = 180
bpy.context.object.data.size = 3.0
underside_light = None
if attachment_strategy == 'broad_vented_split_strap_low_profile_lift_release':
    bpy.ops.object.light_add(type='AREA', location=(0.0, -2.8, -3.0))
    underside_light = bpy.context.object
    underside_light.name = 'Underside strap review light (derived)'
    underside_light.data.energy = 280
    underside_light.data.shape = 'DISK'
    underside_light.data.size = 3.0
bpy.ops.object.camera_add(location=(4.5, -5.5, 3.8))
camera = bpy.context.object
bpy.context.scene.camera = camera
def point_camera(obj, target=(0, 0, 0.45)):
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
point_camera(camera)
try:
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
except TypeError:
    # Blender 5.x exposes the Eevee engine as BLENDER_EEVEE; older builds use
    # BLENDER_EEVEE_NEXT.  Keep the generated scene portable across both.
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.resolution_x = 900
bpy.context.scene.render.resolution_y = 700
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, 'render-2d.png')
bpy.context.scene['psyteardown_request_id'] = REQUEST_ID
bpy.context.scene['psyteardown_scene_spec'] = json.dumps(SCENE_SPEC, ensure_ascii=False)

if 'render_2d' in REQUESTED_OUTPUTS:
    bpy.ops.render.render(write_still=True)
    # Additional views are deliberately review material.  They make the
    # wear/stop-path discussion concrete without implying dimensions or fit.
    REVIEW_VIEWS = {{
        'wearer_side': ((4.8, -6.2, 2.8), (0, 0, 0.45)),
        'underside_strap': ((0.0, -4.8, -3.2), (0, 0, -0.48)),
        'stop_control_access': ((6.2, -1.2, 1.4), (0.3, 0, 0.45)),
        'bystander_state_edge': ((-4.8, 5.8, 3.0), (0, 0, 0.55)),
    }}
    for view_name, (location, target) in REVIEW_VIEWS.items():
        ground.hide_render = view_name == 'underside_strap'
        if underside_light is not None:
            underside_light.hide_render = view_name != 'underside_strap'
        camera.location = location
        point_camera(camera, target)
        bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, 'review-' + view_name + '.png')
        bpy.ops.render.render(write_still=True)
if 'geometry_3d' in REQUESTED_OUTPUTS:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUTPUT_DIR, 'design.blend'))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUTPUT_DIR, 'design.glb'), export_format='GLB')
'''


class BlenderDesignToolProvider:
    """Run Blender headlessly to create a reviewable first-pass blockout."""

    def __init__(
        self,
        executable: str | Path | None = None,
        *,
        output_root: str | Path = "output/experience/blender",
        timeout_seconds: int = 300,
        keep_script: bool = True,
    ) -> None:
        self.executable = resolve_blender_executable(executable)
        self.output_root = Path(output_root)
        self.timeout_seconds = timeout_seconds
        self.keep_script = keep_script
        self.calls: list[DesignToolRequest] = []

    def generate(self, request: DesignToolRequest) -> DesignToolResult:
        self.calls.append(request)
        self.output_root.mkdir(parents=True, exist_ok=True)
        run_dir = Path(tempfile.mkdtemp(prefix=f"{request.request_id}-", dir=self.output_root))
        script_path = run_dir / "scene.py"
        script_path.write_text(_blender_scene_script(request, run_dir), encoding="utf-8")
        try:
            completed = subprocess.run(
                [self.executable, "--background", "--python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BlenderProviderError(
                f"Blender executable not found: {self.executable!r}; install Blender or pass --blender-executable"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise BlenderProviderError(
                f"Blender timed out after {self.timeout_seconds}s: {request.request_id}"
            ) from exc
        (run_dir / "blender.stdout.log").write_text(completed.stdout or "", encoding="utf-8")
        (run_dir / "blender.stderr.log").write_text(completed.stderr or "", encoding="utf-8")
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout or "unknown Blender error").strip()
            raise BlenderProviderError(f"Blender failed ({completed.returncode}): {details[-2000:]}")
        if not self.keep_script:
            script_path.unlink(missing_ok=True)
        render_refs = [str(run_dir / "render-2d.png")] if (run_dir / "render-2d.png").exists() else []
        review_refs = {
            name: str(run_dir / f"review-{name}.png")
            for name in ("wearer_side", "underside_strap", "stop_control_access", "bystander_state_edge")
            if (run_dir / f"review-{name}.png").exists()
        }
        geometry_refs = []
        for name in ("design.blend", "design.glb"):
            path = run_dir / name
            if path.exists():
                geometry_refs.append(str(path))
        asset_hashes = {}
        for path_text in [*render_refs, *geometry_refs, *review_refs.values()]:
            path = Path(path_text)
            if path.exists():
                asset_hashes[path_text] = hashlib.sha256(path.read_bytes()).hexdigest()
        requested = set(request.requested_outputs)
        missing_outputs: list[str] = []
        if "render_2d" in requested and not render_refs:
            missing_outputs.append("render_2d")
        if "geometry_3d" in requested and len(geometry_refs) < 2:
            missing_outputs.append("geometry_3d")
        if missing_outputs:
            details = (completed.stderr or completed.stdout or "no output files").strip()
            raise BlenderProviderError(
                f"Blender completed without requested outputs {missing_outputs}: {details[-2000:]}"
            )
        unknowns = [
            "camera framing and render appearance require human review",
            "geometry dimensions and physical scale are not validated",
            "material, comfort, fit and motion performance are not proven by the blockout",
        ]
        if "engineering_spec" in requested:
            unknowns.append("Blender blockout does not produce an engineering specification")
        return DesignToolResult(
            request_id=request.request_id,
            candidate_revision_id=request.candidate_revision_id,
            provider="blender",
            model="headless-bpy-blockout",
            render_asset_refs=render_refs,
            geometry_asset_refs=geometry_refs,
            derived_review_views=review_refs,
            asset_hashes=asset_hashes,
            declared_notes=[
                "Derived Blender assets are untrusted review material.",
                "No physical dimensions, material performance or user outcome is inferred from the render.",
                "Multi-view exports are derived review material for wearer-side, underside/strap, stop-control access and bystander-state discussion.",
            ],
            unknowns=unknowns,
        )


class FakeDesignToolProvider:
    """Queue-based external-tool stand-in; no rendering or network calls."""

    def __init__(self, responses: list[DesignToolResult | dict] | None = None):
        self._responses = list(responses or [])
        self.calls: list[DesignToolRequest] = []

    def generate(self, request: DesignToolRequest) -> DesignToolResult:
        self.calls.append(request)
        if not self._responses:
            # A deterministic placeholder is useful for wiring tests while
            # keeping the result explicitly draft/untrusted.
            return DesignToolResult(
                request_id=request.request_id,
                candidate_revision_id=request.candidate_revision_id,
                provider="fake-design-tool",
                model="scaffold-render-draft",
                render_asset_refs=[f"derived://{request.request_id}/render-2d"],
                geometry_asset_refs=[f"derived://{request.request_id}/geometry-3d"],
                derived_review_views={
                    "wearer_side": f"derived://{request.request_id}/review-wearer-side",
                    "underside_strap": f"derived://{request.request_id}/review-underside-strap",
                    "stop_control_access": f"derived://{request.request_id}/review-stop-control-access",
                    "bystander_state_edge": f"derived://{request.request_id}/review-bystander-state-edge",
                },
                asset_hashes={
                    f"derived://{request.request_id}/render-2d": hashlib.sha256(f"render:{request.request_id}".encode()).hexdigest(),
                    f"derived://{request.request_id}/geometry-3d": hashlib.sha256(f"geometry:{request.request_id}".encode()).hexdigest(),
                    **{f"derived://{request.request_id}/review-{name.replace('_', '-')}": hashlib.sha256(f"review:{name}:{request.request_id}".encode()).hexdigest() for name in ("wearer_side", "underside_strap", "stop_control_access", "bystander_state_edge")},
                },
                declared_notes=["Derived review views are untrusted visual material; no physical result is inferred."],
                unknowns=["render fidelity", "geometry dimensions", "material appearance"],
            )
        value = self._responses.pop(0)
        return value if isinstance(value, DesignToolResult) else DesignToolResult.model_validate(value)


def build_design_tool_request(
    candidate: DesignCandidate,
    rule_set: DesignRuleSet,
    *,
    requested_outputs: list[str] | None = None,
    patches: list[VariablePatch] | tuple[VariablePatch, ...] = (),
    parent_model_revision_id: str | None = None,
) -> DesignToolRequest:
    """Project only the minimum design context needed by an external tool."""

    if candidate.design is None:
        raise ValueError("candidate must include a complete structured design")
    patch_tuple = tuple(patches)
    variable_values = {
        value.variable_id: (value.normalized_value if value.normalized_value is not None else value.display_value)
        for value in candidate.variables
    }
    display_values = {value.variable_id: value.display_value for value in candidate.variables}
    # A request may be exported before the child candidate is materialized;
    # project patch targets into the provider projection without mutating the
    # parent snapshot.
    for patch in patch_tuple:
        if patch.to_value is not None:
            variable_values[patch.variable_id] = patch.to_value.normalized_value if patch.to_value.normalized_value is not None else patch.to_value.display_value
            display_values[patch.variable_id] = patch.to_value.display_value
    rule_lines = "\n".join(f"- {rule.recommendation}" for rule in rule_set.rules)
    prompt_projection = "\n".join(
        [
            f"Product concept: {candidate.design.concept_summary}",
            f"Form: {candidate.design.shape.silhouette}",
            f"Components: {', '.join(component.name for component in candidate.design.components)}",
            f"Movement adaptation: {'; '.join(candidate.design.adaptation_behavior)}",
            "Initial rule options (not approved facts):",
            rule_lines or "- none",
            "Declared iteration variables:",
            "; ".join(f"{key}={display_values.get(key, value)}" for key, value in sorted(variable_values.items())),
            "Ergonomic boundary: low-profile dorsal-wrist placement, broad compliant contact, centered mass and one-handed recessed stop are hypotheses; validate pressure, slip, false activation and haptic detectability with a prototype.",
            "Preserve explicit unknowns; do not invent engineering measurements or user outcomes.",
        ]
    )
    # Keep both spellings in the projection: older mobility rules use
    # wearable.attachment while the handoff's canonical patch uses the more
    # explicit attachment_strategy name.
    attachment = display_values.get("wearable.attachment_strategy", display_values.get("wearable.attachment"))
    body_placement = display_values.get("wearable.body_placement", "dorsal wrist")
    contact_area = display_values.get("wearable.contact_area", "broad vented soft contact")
    mass_distribution = display_values.get("wearable.mass_distribution", "centered over wrist axis")
    modality = display_values.get("feedback.modality", "private_haptic")
    timing = display_values.get("feedback.timing", "bounded boundary pulse")
    confirmation = display_values.get("feedback.confirmation", "recessed press-hold")
    visible_state = display_values.get("device.visible_state", "wearer-facing state edge")
    cancel_action = display_values.get("control.cancel_action", "one-handed side press-hold")
    form_factor = variable_values.get("wearable.form_factor", candidate.design.shape.form_factor)
    if not isinstance(form_factor, str):
        form_factor = candidate.design.shape.form_factor
    geometry = {
        # Presentation-only proportions; no physical dimensions are implied.
        "body_scale": (1.10, 0.62, 0.22) if "low" in mass_distribution.lower() or "wrist" in body_placement.lower() else (1.25, 0.72, 0.35),
        "strap_scale": (1.42, 0.26, 0.08) if "broad" in contact_area.lower() or "vent" in contact_area.lower() else (1.48, 0.18, 0.10),
        "button_radius": 0.18 if "recess" in confirmation.lower() or "hold" in confirmation.lower() else 0.23,
        "body_z": 0.34 if "low" in mass_distribution.lower() else 0.45,
        "wearer_facing_status": True,
    }
    scene_spec = {
        "form_factor": form_factor,
        "components": [
            {"name": component.name, "role": component.role, "placement": component.placement}
            for component in candidate.design.components
        ],
        "candidate_revision_id": candidate.candidate_revision_id,
        "variables": variable_values,
        "ergonomic_intent": {
            "body_placement": body_placement,
            "attachment_strategy": attachment,
            "contact_area": contact_area,
            "mass_distribution": mass_distribution,
            "feedback_modality": modality,
            "feedback_timing": timing,
            "feedback_confirmation": confirmation,
            "visible_state": visible_state,
            "cancel_action": cancel_action,
        },
        "geometry": geometry,
        "patch_revision_ids": [patch.revision_id for patch in patch_tuple],
        "review_boundary": "derived blockout only; dimensions, comfort, fit and motion stability require evidence",
    }
    return DesignToolRequest(
        request_id="design-tool-request-"
        + hashlib.sha256(
            f"{candidate.candidate_revision_id}|{rule_set.revision_id}|{parent_model_revision_id or ''}|{'|'.join(p.revision_id for p in patch_tuple)}".encode("utf-8")
        ).hexdigest()[:12],
        candidate_revision_id=candidate.candidate_revision_id,
        prompt_projection=prompt_projection,
        requested_outputs=requested_outputs or ["render_2d", "geometry_3d"],
        constraints=list(candidate.design.declared_unknowns),
        scene_spec=scene_spec,
        parent_model_revision_id=parent_model_revision_id,
        patch_revision_ids=[patch.revision_id for patch in patch_tuple],
    )


def attach_design_tool_result(
    model: ProgressiveDesignModel,
    result: DesignToolResult,
    *,
    actor: str = "human",
    confirmed: bool = False,
) -> ProgressiveDesignModel:
    """Create a new model revision after optional human asset confirmation."""

    if result.candidate_revision_id != model.candidate_revision_id:
        raise ValueError("design-tool result belongs to another candidate revision")
    next_revision = model.meta.revision + 1
    def attach_layer(layer: ModelLayerStatus) -> ModelLayerStatus:
        if not confirmed:
            return layer
        if layer.layer == "render_assets":
            refs = tuple(dict.fromkeys((*result.render_asset_refs, *result.derived_review_views.values())))
        elif layer.layer == "geometry":
            refs = tuple(result.geometry_asset_refs)
        else:
            return layer
        return layer.model_copy(
            update={
                "status": "complete" if confirmed and refs else "partial" if refs else "missing",
                "artifact_refs": refs,
                "gaps": tuple(result.unknowns) + (() if confirmed else ("provider draft requires human confirmation",)),
            }
        )

    updated_layers = tuple(attach_layer(layer) for layer in model.layers)
    if confirmed and result.geometry_asset_refs:
        next_stage = "geometry_ready"
    elif confirmed and result.render_asset_refs:
        next_stage = "render_ready"
    else:
        next_stage = model.stage
    return model.model_copy(
        update={
            "revision_id": f"{model.model_id}.r{next_revision}",
            "meta": RevisionMeta(revision=next_revision, parent_revision_id=model.revision_id, created_by=actor, reason="design-tool result attached"),
            "stage": next_stage,
            "layers": updated_layers,
            "provider_result_ids": model.provider_result_ids + (result.result_id,),
            "unresolved_gaps": tuple(dict.fromkeys(model.unresolved_gaps + tuple(result.unknowns))),
        }
    )
