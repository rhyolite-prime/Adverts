"""Builds the RhyolitePrime advert inside Blender (tested against the Blender 5.x Python API).

Layout of the timeline
----------------------
* 9 stages (see shots.py), 5 seconds each, 120 frames at 24 fps.
* Stage i owns frames [1 + 120*i, 120*(i+1)].
* Each stage has its own camera with Depth of Field focused on the stage subject.
  Camera markers on the timeline switch the active camera at each stage start.
* Every object in a stage is keyframed to be visible only inside that stage's
  frame range (hide_viewport / hide_render), so all stages can live in one scene.
* The on-screen text (key selling point, spec line, label, brand corner pill) and
  the progress bar are parented to the stage camera, so they stay put on screen.

Coordinate conventions
----------------------
* 1 unit = 1 metre. Z is up. Floor is z = 0.
* Characters face -Y when their yaw is 0. yaw = pi faces +Y.
* Characters are rigged (rig_characters.py). Wrist targets are world metres, given to
  `Person.reach` or `Person.work_motion`. Character 'r' is the character's right hand
  (-X when facing -Y).
"""

import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import geometry as G
import rig_characters as R
import shots as S

FRAMES = int(round(S.SHOT_SECONDS * S.FPS))  # 120
OVERLAY_DEPTH = 3.0          # distance of the overlay plane in front of the camera
SENSOR_HALF = 18.0           # 36 mm sensor, half width, for 16:9 frames
PI = math.pi

PALETTE = {"primary": "#80004d", "accent": "#cc6699", "light": "#f8f9fa", "dark": "#212529", "success": "#4bb543"}

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgb(h):
    """'#rrggbb' (sRGB) to a linear RGB tuple for Blender."""
    h = h.lstrip("#")
    return tuple(_srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


PRIMARY = hex_rgb(PALETTE["primary"])
ACCENT = hex_rgb(PALETTE["accent"])
LIGHT = hex_rgb(PALETTE["light"])
DARK = hex_rgb(PALETTE["dark"])
SUCCESS = hex_rgb(PALETTE["success"])
SUBJECT_DROP = 0.22          # metres the camera aim is lowered for application stages


def stage_frames(index):
    f0 = 1 + index * FRAMES
    return f0, f0 + FRAMES - 1


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

MATERIAL_DEFS = {
    "concrete": dict(color=(0.24, 0.24, 0.25), rough=0.9, bump=0.25, var=(0.3, 0.3, 0.31), tex_scale=25),
    "wall_dark": dict(color=(0.09, 0.11, 0.14), rough=0.85, bump=0.06, tex_scale=15),
    "wall_light": dict(color=(0.55, 0.55, 0.52), rough=0.8, bump=0.06, tex_scale=15),
    "steel": dict(color=(0.5, 0.5, 0.54), rough=0.28, metal=1.0, bump=0.03, tex_scale=60),
    "dark_steel": dict(color=(0.08, 0.08, 0.09), rough=0.38, metal=0.65),
    "wood": dict(color=(0.42, 0.26, 0.13), rough=0.6, bump=0.12, var=(0.55, 0.36, 0.2), tex_scale=12),
    "wood_dark": dict(color=(0.2, 0.12, 0.07), rough=0.7, bump=0.1, tex_scale=12),
    # Dark skin tones (sRGB hex, converted to linear). Subsurface is added in M() for names starting skin.
    "skin_warm": dict(color=hex_rgb("#5e3822"), var=hex_rgb("#2b170f"), rough=0.5, bump=0.04, tex_scale=150),
    "skin_mid": dict(color=hex_rgb("#4d2c1c"), var=hex_rgb("#26140c"), rough=0.5, bump=0.04, tex_scale=150),
    "skin_deep": dict(color=hex_rgb("#3a2116"), var=hex_rgb("#1d0f08"), rough=0.5, bump=0.04, tex_scale=150),
    "hair_coily": dict(color=(0.02, 0.014, 0.011), rough=0.85, bump=0.35, tex_scale=90),
    "navy": dict(color=(0.08, 0.1, 0.22), rough=0.8, bump=0.06, tex_scale=120),
    "cap": dict(color=(0.2, 0.3, 0.5), rough=0.7, bump=0.06, tex_scale=120),
    "black": dict(color=(0.02, 0.02, 0.02), rough=0.55),
    "leather": dict(color=(0.32, 0.18, 0.09), rough=0.8, bump=0.2, tex_scale=60),
    "overalls": dict(color=(0.1, 0.27, 0.55), rough=0.8, bump=0.06, tex_scale=120),
    "apron_red": dict(color=(0.6, 0.07, 0.07), rough=0.8, bump=0.06, tex_scale=120),
    "chef_white": dict(color=(0.93, 0.93, 0.92), rough=0.7, bump=0.05, tex_scale=120),
    "hi_vis": dict(color=(1.0, 0.8, 0.05), rough=0.5, emit=(1.0, 0.7, 0.0), emit_strength=0.3, bump=0.05, tex_scale=120),
    "hardhat": dict(color=(1.0, 0.75, 0.05), rough=0.35, coat=0.5),
    "straw": dict(color=(0.75, 0.6, 0.3), rough=0.9),
    "grey_shirt": dict(color=(0.4, 0.42, 0.45), rough=0.8, bump=0.06, tex_scale=120),
    # Reinforced PVC gas hoses with glossy clearcoat and fine braided/ribbed surface texture
    "hose_orange": dict(color=(1.0, 0.36, 0.04), var=(0.92, 0.30, 0.02), rough=0.26, coat=0.65, bump=0.08, tex_scale=140),
    "hose_red": dict(color=(0.78, 0.05, 0.04), var=(0.65, 0.03, 0.03), rough=0.26, coat=0.65, bump=0.08, tex_scale=140),
    "hose_blue": dict(color=(0.03, 0.24, 0.84), var=(0.02, 0.18, 0.70), rough=0.26, coat=0.65, bump=0.08, tex_scale=140),
    "cyl_grey": dict(color=(0.42, 0.43, 0.47), rough=0.32, metal=0.65),
    "cyl_red": dict(color=(0.6, 0.05, 0.04), rough=0.32, metal=0.45),
    "cyl_blue": dict(color=(0.04, 0.17, 0.62), rough=0.32, metal=0.45),
    "brass": dict(color=(0.84, 0.63, 0.24), rough=0.25, metal=1.0),
    "band_white": dict(color=(0.95, 0.95, 0.95), rough=0.45, bump=0.12, tex_scale=160),
    "smile_white": dict(color=(1.0, 1.0, 1.0), rough=0.2, emit=(1.0, 1.0, 1.0), emit_strength=2.2),
    "eye_white": dict(color=(0.90, 0.88, 0.85), rough=0.22, coat=0.4, emit=(0.90, 0.88, 0.85), emit_strength=0.08),
    "eye_dark": dict(color=(0.012, 0.008, 0.006), rough=0.08, coat=0.85),
    "grass": dict(color=(0.13, 0.36, 0.09), rough=0.95, bump=0.3, var=(0.22, 0.45, 0.12), tex_scale=30),
    "bark": dict(color=(0.25, 0.15, 0.08), rough=0.9, bump=0.4, tex_scale=20),
    "leaf": dict(color=(0.1, 0.3, 0.1), rough=0.9),
    "tent": dict(color=(0.52, 0.56, 0.32), rough=0.9, bump=0.08, tex_scale=40),
    "tile": dict(color=(0.9, 0.88, 0.83), rough=0.38, bump=0.05, tex_scale=30),
    "cabinet": dict(color=(0.78, 0.72, 0.6), rough=0.5),
    "counter": dict(color=(0.14, 0.14, 0.15), rough=0.28, bump=0.04, tex_scale=40),
    "stainless": dict(color=(0.68, 0.69, 0.72), rough=0.20, metal=1.0),
    "straw_floor": dict(color=(0.55, 0.42, 0.2), rough=0.95, bump=0.3, var=(0.72, 0.55, 0.25), tex_scale=25),
    "barn_wood": dict(color=(0.3, 0.18, 0.1), rough=0.8, bump=0.15, tex_scale=12),
    "chick": dict(color=(1.0, 0.82, 0.2), rough=0.6),
    "cardboard": dict(color=(0.6, 0.45, 0.28), rough=0.8, bump=0.15, tex_scale=40),
    "conveyor": dict(color=(0.07, 0.07, 0.08), rough=0.6, bump=0.12, tex_scale=30),
    "pipe_silver": dict(color=(0.72, 0.72, 0.75), rough=0.26, metal=1.0),
    "steam": dict(color=(0.9, 0.9, 0.92), rough=1.0, emit=(0.9, 0.9, 0.95), emit_strength=0.25),
    "visor": dict(color=(0.02, 0.05, 0.12), rough=0.05, metal=0.5, emit=(0.2, 0.5, 1.0), emit_strength=0.6),
    "wordmark": dict(color=PRIMARY, rough=0.22, coat=0.5, emit=PRIMARY, emit_strength=1.1),
    # Outro on a near-black stage: a metal would reflect the dark world, so use an emissive, non-metal copy.
    "wordmark_outro": dict(color=PRIMARY, rough=0.32, emit=PRIMARY, emit_strength=3.8),
    "glow_orange": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.42, 0.06), emit_strength=24.0),
    "glow_blue": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(0.3, 0.62, 1.0), emit_strength=32.0),
    "glow_red": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.15, 0.05), emit_strength=20.0),
    "spark": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.72, 0.28), emit_strength=44.0),
    "text_white": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=LIGHT, emit_strength=1.7),
    "text_accent": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=ACCENT, emit_strength=2.5),
    "bar_accent": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=ACCENT, emit_strength=3.0),
    "brand_primary": dict(color=PRIMARY, rough=0.28, emit=PRIMARY, emit_strength=3.0),
    "bar_success": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=SUCCESS, emit_strength=3.2),
    "check_green": dict(color=SUCCESS, rough=0.25, emit=SUCCESS, emit_strength=2.0),
    "check_badge_bg": dict(color=DARK, rough=0.35, emit=DARK, emit_strength=0.45),
    "check_badge_rim": dict(color=LIGHT, rough=0.25, emit=LIGHT, emit_strength=1.5),
}

_MATS = {}
_FONT = None


def _get_font():
    """Load a bold broadcast sans-serif font when available; fall back to Blender's built-in font."""
    global _FONT
    if _FONT is not None and _FONT.name in bpy.data.fonts:
        return _FONT
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                _FONT = bpy.data.fonts.load(path, check_existing=True)
                return _FONT
            except Exception:
                continue
    return None


def _set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value
    else:
        print(f"[advert] warning: shader input '{name}' not found")


def _texture(mat, bsdf, d):
    """Procedural detail: colour variation (var) and bump from noise (bump). Scale: tex_scale."""
    if "var" not in d and "bump" not in d:
        return
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    scale = d.get("tex_scale", 40.0)
    if "var" in d:
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = scale * 0.5
        nz.inputs["Detail"].default_value = 6.0
        nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.inputs[1].default_value = (*d["color"], 1.0)
        mix.inputs[2].default_value = (*d["var"], 1.0)
        nt.links.new(nz.outputs["Fac"], mix.inputs[0])
        nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    if "bump" in d:
        nz2 = nt.nodes.new("ShaderNodeTexNoise")
        nz2.inputs["Scale"].default_value = scale
        nz2.inputs["Detail"].default_value = 10.0
        nt.links.new(tc.outputs["Generated"], nz2.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = d["bump"]
        bump.inputs["Distance"].default_value = 0.05
        nt.links.new(nz2.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def M(name):
    """Return (creating on first use) the named material."""
    if name in _MATS and _MATS[name].name in bpy.data.materials:
        return _MATS[name]
    d = MATERIAL_DEFS[name]
    mat = bpy.data.materials.new(f"ad_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    _set_input(bsdf, "Base Color", (*d["color"], 1.0))
    _set_input(bsdf, "Roughness", d.get("rough", 0.5))
    _set_input(bsdf, "Metallic", d.get("metal", 0.0))
    if "coat" in d:
        _set_input(bsdf, "Coat Weight", d["coat"])
        _set_input(bsdf, "Coat Roughness", d.get("coat_rough", 0.12))
    if name.startswith("skin"):
        # Light scattering under the skin softens the CG look.
        _set_input(bsdf, "Subsurface Weight", 0.06)
        _set_input(bsdf, "Subsurface Radius", (0.8, 0.35, 0.2))
        _set_input(bsdf, "Specular IOR Level", 0.4)
    if "emit" in d:
        _set_input(bsdf, "Emission Color", (*d["emit"], 1.0))
        _set_input(bsdf, "Emission Strength", d.get("emit_strength", 1.0))
    _texture(mat, bsdf, d)
    _MATS[name] = mat
    return mat


def band_material():
    """Dark translucent bar behind the overlay text (Mix of Transparent and Principled)."""
    if "_overlay_band" in _MATS and _MATS["_overlay_band"].name in bpy.data.materials:
        return _MATS["_overlay_band"]
    mat = bpy.data.materials.new("ad_overlay_band")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    _set_input(principled, "Base Color", (*DARK, 1.0))
    _set_input(principled, "Roughness", 1.0)
    mix.inputs[0].default_value = 0.84  # 84% opaque for crisp contrast
    nt.links.new(transparent.outputs[0], mix.inputs[1])
    nt.links.new(principled.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    _MATS["_overlay_band"] = mat
    return mat


# ---------------------------------------------------------------------------
# Keyframe helpers
# ---------------------------------------------------------------------------

def key(obj, frame, **values):
    """Set properties and keyframe them at `frame`. Values may be tuples."""
    for name, value in values.items():
        setattr(obj, name, value)
        obj.keyframe_insert(data_path=name, frame=frame)


def key_index(obj, frame, name, index, value):
    getattr(obj, name)[index] = value
    obj.keyframe_insert(data_path=name, index=index, frame=frame)


def set_visible(obj, f0, f1):
    """Show `obj` only between frames f0 and f1 (inclusive)."""
    if f0 > 1:
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=1)
        obj.keyframe_insert(data_path="hide_render", frame=1)
    obj.hide_viewport = False
    obj.hide_render = False
    obj.keyframe_insert(data_path="hide_viewport", frame=f0)
    obj.keyframe_insert(data_path="hide_render", frame=f0)
    obj.hide_viewport = True
    obj.hide_render = True
    obj.keyframe_insert(data_path="hide_viewport", frame=f1 + 1)
    obj.keyframe_insert(data_path="hide_render", frame=f1 + 1)


def _mesh_from(name, geom, smooth):
    verts, faces = geom
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bverts = [bm.verts.new(v) for v in verts]
    bm.verts.ensure_lookup_table()
    for f in faces:
        try:
            bm.faces.new([bverts[i] for i in f])
        except ValueError:
            pass  # duplicate face; skip
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.update()
    return me


def aim_quat(direction, axis="Z"):
    """Rotation (Euler) that turns the local +Z (or +X) axis to `direction`."""
    d = Vector(direction).normalized()
    if axis == "Z":
        return Vector((0, 0, 1)).rotation_difference(d).to_euler()
    return Vector((1, 0, 0)).rotation_difference(d).to_euler()


# ---------------------------------------------------------------------------
# Builder: creates objects and records them for the current stage
# ---------------------------------------------------------------------------

class Builder:
    def __init__(self, scene, sun_data=None):
        self.scene = scene
        self.sun_data = sun_data
        self.col = None
        self.objs = []
        self.cam = None
        self.lens = 35.0
        self.f0 = 1
        self.f1 = FRAMES
        self.world_color = None

    # --- stage bookkeeping ------------------------------------------------
    def begin(self, index, shot):
        self.index = index
        self.shot = shot
        self.f0, self.f1 = stage_frames(index)
        self.col = bpy.data.collections.new(f"Stage{index + 1:02d}_{shot['id']}")
        self.scene.collection.children.link(self.col)
        self.objs = []

    def finish(self):
        for o in self.objs:
            set_visible(o, self.f0, self.f1)

    def link(self, o):
        self.col.objects.link(o)
        self.objs.append(o)
        return o

    # --- primitives -------------------------------------------------------
    def obj(self, name, geom=None, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
            parent=None, smooth=False, bevel=0.0, subdiv=0):
        if geom is None:
            o = bpy.data.objects.new(name, None)
            o.empty_display_type = "PLAIN_AXES"
            o.empty_display_size = 0.08
        else:
            o = bpy.data.objects.new(name, _mesh_from(name, geom, smooth))
            if mat is not None:
                o.data.materials.append(mat)
            if bevel > 0:
                mod = o.modifiers.new("Bevel", "BEVEL")
                mod.width = bevel
                mod.segments = 3
                mod.limit_method = "ANGLE"
            if subdiv > 0:
                sd = o.modifiers.new("Subsurf", "SUBSURF")
                sd.levels = subdiv
                sd.render_levels = subdiv
        o.location = loc
        o.rotation_euler = rot
        o.scale = scale
        if parent is not None:
            o.parent = parent
        return self.link(o)

    def segment(self, name, p0, p1, radius, mat, cone=False, radius_top=None):
        """Cylinder (or cone, apex at p1) from p0 to p1."""
        p0v, p1v = Vector(p0), Vector(p1)
        length = max(1e-4, (p1v - p0v).length)
        if cone:
            geom = G.cone(radius, length, 20)
        else:
            geom = G.cylinder(radius, length, 20, r_top=radius_top)
        return self.obj(name, geom, mat, loc=tuple(p0v), rot=aim_quat(p1v - p0v), smooth=True)

    def light(self, name, kind, loc, color, energy, size=1.0, target=None):
        ld = bpy.data.lights.new(name, kind)
        ld.color = color
        ld.energy = energy
        if kind == "AREA":
            ld.shape = "SQUARE"
            ld.size = size
        elif kind == "POINT":
            ld.shadow_soft_size = size
        o = bpy.data.objects.new(name, ld)
        o.location = loc
        if target is not None:
            o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return self.link(o)

    def floor(self, mat, size=60.0):
        return self.obj("floor", G.box(size, size, 0.1), mat, loc=(0, 0, -0.05))

    def world(self, color, sun_energy=None):
        """Keyframe the world sky/ground gradient and per-stage Sun energy."""
        self.world_color = color
        nt = self.scene.world.node_tree
        mix = nt.nodes.get("WorldGradientMix")
        if mix is not None:
            low = tuple(max(0.005, c * 0.45) for c in color)
            high = tuple(min(1.0, c * 1.35 + 0.015) for c in color)
            mix.inputs[1].default_value = (*low, 1.0)
            mix.inputs[2].default_value = (*high, 1.0)
            mix.inputs[1].keyframe_insert("default_value", frame=self.f0)
            mix.inputs[1].keyframe_insert("default_value", frame=self.f1)
            mix.inputs[2].keyframe_insert("default_value", frame=self.f0)
            mix.inputs[2].keyframe_insert("default_value", frame=self.f1)
        else:
            bg = nt.nodes["Background"]
            sock = bg.inputs["Color"]
            sock.default_value = (*color, 1.0)
            sock.keyframe_insert("default_value", frame=self.f0)
            sock.keyframe_insert("default_value", frame=self.f1)

        if self.sun_data is not None:
            if sun_energy is None:
                if self.index in (0, len(S.SHOTS) - 1):
                    sun_energy = 0.0   # dark studio stages: no sunlight bleed
                elif self.index in (5, 6):
                    sun_energy = 2.6   # outdoor & farm stages: warm sunlight
                else:
                    sun_energy = 0.55  # indoor workshop/kitchens: gentle directional fill
            self.sun_data.energy = sun_energy
            self.sun_data.keyframe_insert("energy", frame=self.f0)
            self.sun_data.keyframe_insert("energy", frame=self.f1)

    # --- camera -----------------------------------------------------------
    def camera(self, start, end, target, lens=35.0, drop=SUBJECT_DROP, fstop=None):
        """`drop` tilts the aim down so the subject sits higher, above the lower-third band."""
        aim = (target[0], target[1], target[2] - drop)
        name = f"Cam{self.index + 1:02d}"
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 300.0
        mid = (Vector(start) + Vector(end)) / 2
        if hasattr(cd, "dof"):
            cd.dof.use_dof = True
            cd.dof.focus_distance = max(2.0, (Vector(target) - mid).length)
            cd.dof.aperture_fstop = fstop if fstop is not None else (5.6 if drop == 0.0 else 3.8)
        cam = bpy.data.objects.new(name, cd)
        cam.rotation_euler = (Vector(aim) - mid).to_track_quat("-Z", "Y").to_euler()
        cam.location = start
        key(cam, self.f0, location=tuple(start))
        key(cam, self.f1, location=tuple(end))
        self.col.objects.link(cam)  # not recorded: cameras are never hidden
        marker = self.scene.timeline_markers.new(name, frame=self.f0)
        marker.camera = cam
        self.cam = cam
        self.lens = lens
        return cam

    # --- on-screen text ---------------------------------------------------
    def text(self, name, body, size, mat, loc, align_x="CENTER", align_y="TOP"):
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = body
        cu.size = size
        cu.align_x = align_x
        cu.align_y = align_y
        font = _get_font()
        if font is not None:
            cu.font = font
        cu.materials.append(mat)
        o = bpy.data.objects.new(name, cu)
        o.parent = self.cam
        o.location = loc
        return self.link(o)

    def overlay(self, shot, stagger=0, title_size=0.13, title_material="text_white", hold_end=None):
        """Lower-third overlay: label, brand corner pill, key selling point, spec line, progress bar.

        Everything sits on the camera at OVERLAY_DEPTH, so it stays on screen.
        When `hold_end` is True (default on the final Outro stage), the title and
        spec line stay at full scale through `f1` so the final frame never goes blank.
        """
        f0, f1 = self.f0, self.f1
        if hold_end is None:
            hold_end = (self.index == len(S.SHOTS) - 1)
        half_w = OVERLAY_DEPTH * SENSOR_HALF / self.lens
        z = -OVERLAY_DEPTH + 0.02          # text and bar sit slightly in front of the band
        band = self.obj("OverlayBand", G.box(2 * half_w + 0.4, 0.62, 0.001), band_material(),
                        loc=(0, -0.64, -OVERLAY_DEPTH - 0.02), parent=self.cam)
        # Thin accent top rule along the lower-third band
        self.obj("OverlayBandRule", G.box(2 * half_w + 0.4, 0.008, 0.0015), M("brand_primary"),
                 loc=(0, -0.33, -OVERLAY_DEPTH - 0.01), parent=self.cam)

        self.obj("OverlayTopBand", G.box(2 * half_w + 0.4, 0.16, 0.001), band_material(),
                 loc=(0, 0.72, -OVERLAY_DEPTH - 0.02), parent=self.cam)
        label = self.text("OverlayLabel", shot["label"], 0.05, M("text_accent"),
                          (-half_w + 0.14, 0.72, z), align_x="LEFT", align_y="CENTER")
        key(label, f0, location=(-half_w - 0.6, 0.72, z))
        key(label, f0 + 12, location=(-half_w + 0.14, 0.72, z))

        # Persistent top-right brand corner badge on application stages
        if 0 < self.index < len(S.SHOTS) - 1:
            self.text("OverlayBrandCorner", "RhyolitePrime", 0.044, M("text_white"),
                      (half_w - 0.14, 0.72, z), align_x="RIGHT", align_y="CENTER")

        lines = shot["title"].split("\n")
        base = title_size if len(lines) == 1 else min(title_size, 0.33 / (len(lines) * 1.3))
        title_objs = [self.text(f"OverlayTitle{i}", ln, base, M(title_material), (0, 0, z))
                      for i, ln in enumerate(lines)]
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        widths = [o.evaluated_get(depsgraph).dimensions.x for o in title_objs]
        max_w = max(widths) if widths else 0.0
        fit = min(1.0, (2 * half_w - 0.5) / max_w) if max_w > 0 else 1.0
        size = base * fit
        pitch = size * 1.3
        for i, o in enumerate(title_objs):
            o.data.size = size
            o.location = (0, -0.4 - i * pitch, z)
            s0 = f0 + i * stagger
            key(o, s0, scale=(0.01, 0.01, 0.01))
            key(o, s0 + 14, scale=(1.0, 1.0, 1.0))
            if hold_end:
                key(o, f1, scale=(1.0, 1.0, 1.0))
            else:
                key(o, f1 - 10, scale=(1.0, 1.0, 1.0))
                key(o, f1, scale=(0.01, 0.01, 0.01))

        spec_top = -0.4 - len(lines) * pitch - 0.02
        spec = self.text("OverlaySpec", shot["spec"], 0.05, M("text_white"), (0, spec_top, z))
        key(spec, f0 + 8, scale=(0.01, 0.01, 0.01))
        key(spec, f0 + 24, scale=(1.0, 1.0, 1.0))
        if hold_end:
            key(spec, f1, scale=(1.0, 1.0, 1.0))
        else:
            key(spec, f1 - 10, scale=(1.0, 1.0, 1.0))
            key(spec, f1, scale=(0.01, 0.01, 0.01))

        bar = self.obj("OverlayProgress", G.box(1.0, 0.02, 0.001, origin="left"), M("bar_success"),
                       loc=(-half_w, -0.85, z), parent=self.cam, scale=(0.001, 1, 1))
        key(bar, f0, scale=(0.001, 1, 1))
        key(bar, f1, scale=(2 * half_w, 1, 1))
        return band


# ---------------------------------------------------------------------------
# Characters: rigged figures (see rig_characters.py)
# ---------------------------------------------------------------------------

def outfit(skin, torso, trousers=None, sleeves=None, shoes="black", hands=None, apron=None, hair="hair_coily"):
    """Material slots for a rigged character. Names refer to MATERIAL_DEFS."""
    m = {
        "skin": M(skin),
        "torso": M(torso),
        "eye_white": M("eye_white"),
        "eye_dark": M("eye_dark"),
        "eye_glint": M("smile_white"),
    }
    if trousers:
        m["trousers"] = M(trousers)
    if sleeves:
        m["sleeves"] = M(sleeves)
    if shoes:
        m["shoes"] = M(shoes)
    if hands:
        m["hands"] = M(hands)
    if apron:
        m["apron"] = M(apron)
    if hair:
        m["hair"] = M(hair)
    return m


def _celebrate(person, b):
    """After the thumbs-up: a bright smile and a circular green check badge."""
    person.smile(b.f1 - 22, M("smile_white"))
    person.check(b.f1 - 20, M("check_green"), badge_mat=M("check_badge_bg"), rim_mat=M("check_badge_rim"))


# ---------------------------------------------------------------------------
# Props & Hero Hose Details
# ---------------------------------------------------------------------------

def gas_cylinder(b, name, base, body_mat, band_mat, h=0.9, r=0.13):
    """Gas cylinder standing at `base` (bottom centre). Returns the valve's world point."""
    x, y, z = base
    b.obj(name, G.cylinder(r, h, 20), body_mat, loc=(x, y, z), smooth=True)
    b.obj(name + "_foot", G.cylinder(r + 0.01, 0.05, 20), M("dark_steel"), loc=(x, y, z), smooth=True)
    b.obj(name + "_band", G.cylinder(r + 0.003, 0.22, 20, z0=0.0), band_mat, loc=(x, y, z + h * 0.35),
          smooth=True)
    b.obj(name + "_neck", G.cylinder(0.045, 0.06, 12, z0=0.0), M("brass"), loc=(x, y, z + h), smooth=True)
    b.obj(name + "_valve", G.cylinder(0.03, 0.1, 12, z0=0.0), M("brass"), loc=(x, y, z + h + 0.06), smooth=True)
    return (x, y, z + h + 0.16)


def trolley(b, name, base, width=0.6):
    x, y, z = base
    b.obj(name + "_base", G.box(width, 0.48, 0.05), M("dark_steel"), loc=(x, y, z + 0.1), bevel=0.01)
    for dx in (-width / 2 + 0.06, width / 2 - 0.06):
        for dy in (-0.2, 0.2):
            b.obj(name + "_wheel", G.cylinder(0.05, 0.03, 12, z0=-0.015), M("black"),
                  loc=(x + dx, y + dy, z + 0.05), rot=(PI / 2, 0, 0), smooth=True)


def hose_fitting(b, name, p0, p1, radius):
    """Brass hex nut + crimped steel ferrule at a hose connection point."""
    p0v, p1v = Vector(p0), Vector(p1)
    d = p1v - p0v
    if d.length < 1e-5:
        return
    rot = aim_quat(d)
    b.obj(f"{name}_hex", G.ring(radius * 0.85, radius * 1.48, 0.038, segments=6, z0=0.0),
          M("brass"), loc=tuple(p0v), rot=rot, smooth=False)
    b.obj(f"{name}_ferrule", G.cylinder(radius * 1.22, 0.045, 18, z0=0.035),
          M("steel"), loc=tuple(p0v), rot=rot, smooth=True)


def hose_end_cap(b, name, loc, direction, outer_mat, radius=0.035, pop_in=None):
    """Three-layer reinforced hose cross-section matching `images/all-products.jpg`:
    1. Colored outer PVC jacket
    2. White braided high-tensile fiber reinforcement middle ring
    3. Dark black rubber/PVC inner core and hollow bore
    """
    rot = aim_quat(direction)
    root = b.obj(f"{name}_cap_root", None, loc=loc, rot=rot)
    b.obj(f"{name}_outer_layer", G.ring(radius * 0.72, radius * 1.02, 0.036, 28, z0=0.0),
          outer_mat, parent=root, smooth=True)
    b.obj(f"{name}_braid_layer", G.ring(radius * 0.55, radius * 0.73, 0.038, 28, z0=0.0),
          M("band_white"), parent=root, smooth=True)
    b.obj(f"{name}_inner_core", G.ring(radius * 0.36, radius * 0.56, 0.040, 28, z0=0.0),
          M("black"), parent=root, smooth=True)
    b.obj(f"{name}_bore", G.cylinder(radius * 0.36, 0.025, 24, z0=0.0),
          M("black"), parent=root, smooth=True)
    if pop_in is not None:
        key(root, pop_in, scale=(0.01, 0.01, 0.01))
        key(root, pop_in + 10, scale=(1.0, 1.0, 1.0))
    return root


def hose(b, name, points, mat, radius, reveal=None, fittings=True):
    """Bezier hose through `points` (world coordinates). `reveal` = (f0, f1) to animate it growing."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 24
    cu.bevel_depth = radius
    cu.bevel_resolution = 5
    cu.use_fill_caps = True
    cu.materials.append(mat)
    sp = cu.splines.new("BEZIER")
    sp.bezier_points[0].co = Vector(points[0])
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = Vector(p)
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu)
    b.link(o)
    if reveal is not None:
        f0, f1 = reveal
        cu.bevel_factor_end = 0.0
        cu.keyframe_insert("bevel_factor_end", frame=f0)
        cu.bevel_factor_end = 1.0
        cu.keyframe_insert("bevel_factor_end", frame=f1)
    if fittings and len(points) >= 2:
        hose_fitting(b, f"{name}_fit_start", points[0], points[1], radius)
    return o


def torch(b, name, grip, tip, body_mat=None):
    """Hand torch: handle from the grip towards the tip, with a nozzle at the tip."""
    g, t = Vector(grip), Vector(tip)
    d = (t - g).normalized()
    length = (t - g).length
    handle_end = g + d * length * 0.6
    h_obj = b.segment(name + "_handle", tuple(g), tuple(handle_end), 0.024, body_mat or M("brass"))
    n_obj = b.segment(name + "_nozzle", tuple(handle_end), tuple(t), 0.008, M("brass"))
    return h_obj, n_obj


def animate_torch(b, name, keyframes, body_mat=None, hide_at=None):
    """Create a torch and animate its position/orientation through `(frame, grip, tip)` tuples."""
    f_first, g0, t0 = keyframes[0]
    h_obj, n_obj = torch(b, name, g0, t0, body_mat=body_mat)
    for fr, g, t in keyframes:
        gv, tv = Vector(g), Vector(t)
        d = (tv - gv).normalized()
        hend = gv + d * (tv - gv).length * 0.6
        rot = aim_quat(tv - gv)
        key(h_obj, fr, location=tuple(gv), rotation_euler=tuple(rot), scale=(1, 1, 1))
        key(n_obj, fr, location=tuple(hend), rotation_euler=tuple(rot), scale=(1, 1, 1))
    if hide_at is not None:
        for o in (h_obj, n_obj):
            key(o, hide_at - 1, scale=(1, 1, 1))
            key(o, hide_at, scale=(0.001, 0.001, 0.001))
    return h_obj, n_obj


def flame(b, name, base, tip, mat, radius=0.035):
    return b.segment(name, base, tip, radius, mat, cone=True)


def flicker(obj, f0, f1, base_scale, amp, rng, step=2):
    for f in range(f0, f1 + 1, step):
        s = 1 + amp * (2 * rng.random() - 1)
        t = 1 + amp * 0.5 * (2 * rng.random() - 1)
        key(obj, f, scale=(base_scale[0] * s, base_scale[1] * s, base_scale[2] * t))


def sparks(b, mat, origin_at, f0, f1, count, rng, spread=1.2, lift=1.0):
    """Short-lived sparks thrown from `origin_at(frame)` with simple ballistic motion."""
    gravity = Vector((0, 0, -6.0))
    for i in range(count):
        start = rng.randint(f0, max(f0, f1 - 16))
        dur = rng.randint(7, 13)
        p0 = Vector(origin_at(start))
        v = Vector((rng.uniform(-spread, spread), rng.uniform(-spread * 0.6, spread * 0.6),
                    rng.uniform(0.3, 1.2) * lift))

        def pos(sec):
            return p0 + v * sec + gravity * (0.5 * sec * sec)

        s = b.obj(f"spark_{i}", G.sphere(0.012, 6, 4), mat, loc=tuple(p0), scale=(0.01, 0.01, 0.01))
        mid, end = dur / 2 / S.FPS, dur / S.FPS
        key(s, start, location=tuple(p0), scale=(0.01, 0.01, 0.01))
        key(s, start + dur // 2, location=tuple(pos(mid)), scale=(1, 1, 1))
        key(s, start + dur, location=tuple(pos(end)), scale=(0.01, 0.01, 0.01))


def puffs(b, mat, origin, f0, f1, count, rng, rise=0.9, radius=0.12):
    """Soft steam puffs that drift up and grow, then fade by shrinking."""
    for i in range(count):
        start = rng.randint(f0, max(f0, f1 - 40))
        life = rng.randint(30, 44)
        x = origin[0] + rng.uniform(-0.15, 0.15)
        y = origin[1] + rng.uniform(-0.15, 0.15)
        z0 = origin[2]
        p = b.obj(f"steam_{i}", G.sphere(radius, 8, 6), M("steam"), loc=(x, y, z0), scale=(0.01, 0.01, 0.01))
        key(p, start, location=(x, y, z0), scale=(0.01, 0.01, 0.01))
        key(p, start + life // 2, location=(x, y, z0 + rise * 0.5), scale=(1.4, 1.4, 1.4))
        key(p, start + life, location=(x + rng.uniform(-0.2, 0.2), y, z0 + rise), scale=(0.01, 0.01, 0.01))


def tree(b, name, loc, height=2.4, crown=1.0):
    b.obj(name + "_trunk", G.cylinder(0.14, height, 10), M("bark"), loc=loc, smooth=True)
    b.obj(name + "_crown", G.sphere(crown, 12, 8, center=(0, 0, 0), sz=1.2), M("leaf"),
          loc=(loc[0], loc[1], loc[2] + height + crown * 0.6), smooth=True)


def tent_geom(w=1.1, d=1.0, h=1.5):
    v = [(-w, -d, 0), (w, -d, 0), (w, d, 0), (-w, d, 0), (0, 0, h)]
    f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (0, 1, 2, 3)]
    return v, f


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images")
PRODUCT_PHOTO = os.path.join(IMAGES_DIR, "all-products.jpg")


def photo_card(b, name, path, loc, width, pop_in):
    """Framed product photo facing the camera (-Y). `loc` is its centre; the frame is primary-coloured.

    The photo is shown unlit (emission) with mild AgX highlight compensation so the red, blue, and
    yellow/orange hoses retain their crisp product colours.
    """
    img = bpy.data.images.load(path, check_existing=True)
    img.pack()                      # keep the photo inside the .blend, so it opens anywhere
    aspect = img.size[1] / img.size[0]
    w, h = width, width * aspect
    mat = bpy.data.materials.new(f"ad_{name}_photo")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.25
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])

    # Quad with UVs, in the XY plane; rotated so it faces -Y like the rest of the set.
    me = bpy.data.meshes.new(f"{name}_quad")
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)],
                   [], [(0, 1, 2, 3)])
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    for li, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[li].uv = (u, v)
    me.materials.append(mat)
    photo = bpy.data.objects.new(name, me)
    photo.rotation_euler = (PI / 2, 0, 0)
    photo.location = loc
    b.link(photo)

    border_w = 0.045
    border = b.obj(f"{name}_frame", G.box(w + 2 * border_w, h + 2 * border_w, 0.016), M("brand_primary"),
                   loc=(loc[0], loc[1] + 0.02, loc[2]), rot=(PI / 2, 0, 0), bevel=0.004)
    backing = b.obj(f"{name}_backing", G.box(w + 2 * border_w + 0.03, h + 2 * border_w + 0.03, 0.01),
                    M("dark_steel"), loc=(loc[0], loc[1] + 0.035, loc[2]), rot=(PI / 2, 0, 0))
    for o in (photo, border, backing):
        key(o, pop_in, scale=(0.01, 0.01, 0.01))
        key(o, pop_in + 16, scale=(1.0, 1.0, 1.0))
    return photo


def stage_intro(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(0.0, -7.6, 1.5), end=(0.0, -6.6, 1.6), target=(0.0, 0.0, 1.4), drop=0.0)
    b.world((0.015, 0.015, 0.02), sun_energy=0.0)
    b.floor(M("dark_steel"))
    b.light("KeyTop", "AREA", (0, -1.0, 6.0), (1.0, 0.95, 0.9), 900.0, size=4.0, target=(0, 0, 0))
    b.light("RimOrange", "AREA", (4.0, 3.0, 3.0), (1.0, 0.5, 0.15), 500.0, size=3.0, target=(0, 0, 1.2))
    b.light("FrontAccent", "AREA", (-3.2, -3.5, 2.2), (0.95, 0.85, 1.0), 260.0, size=2.5, target=(0, 0, 1.2))

    # Wordmark rises from the floor
    cu = bpy.data.curves.new("Wordmark", "FONT")
    cu.body = "RhyolitePrime"
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.08
    cu.bevel_depth = 0.012
    cu.bevel_resolution = 2
    font = _get_font()
    if font is not None:
        cu.font = font
    cu.materials.append(M("wordmark"))
    cu.size = 1.0
    word = bpy.data.objects.new("Wordmark", cu)
    word.rotation_euler = (PI / 2, 0, 0)
    b.link(word)
    bpy.context.view_layer.update()
    width = word.evaluated_get(bpy.context.evaluated_depsgraph_get()).dimensions.x
    cu.size = 4.6 / width if width > 0 else 1.0
    key(word, f0 + 4, location=(0, 0.0, -0.9))
    key(word, f0 + 40, location=(0, 0.0, 1.45))

    # Hose sweeps across the frame above the lower-third band to underline the 3D wordmark,
    # ending in a prominent 3-layer reinforced cross-section angled toward the camera.
    path = [
        (-3.6, 0.2, 0.92),
        (-2.2, -0.15, 1.00),
        (-0.8, -0.25, 1.04),
        (0.8, -0.25, 1.04),
        (2.1, -0.35, 1.00),
        (2.85, -0.85, 1.02),
    ]
    hose(b, "HoseIntro", path, M("hose_orange"), 0.045, reveal=(f0 + 4, f0 + 56), fittings=False)
    hose_end_cap(b, "IntroHoseCap", loc=(2.85, -0.85, 1.02), direction=(0.45, -0.88, 0.05),
                 outer_mat=M("hose_orange"), radius=0.052, pop_in=f0 + 52)

    # Product photo above the wordmark, kept below the top label band at every camera position
    photo_card(b, "IntroPhoto", PRODUCT_PHOTO, loc=(0.0, 0.3, 2.36), width=1.1, pop_in=f0 + 44)
    b.overlay(shot, title_size=0.13, title_material="brand_primary")


def stage_welding(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(-3.6, -4.8, 1.9), end=(-3.0, -4.2, 1.9), target=(0.1, 0.4, 0.8), lens=40)
    b.world((0.03, 0.035, 0.045))
    b.floor(M("concrete"))
    b.obj("BackWall", G.box(18, 0.3, 7), M("wall_dark"), loc=(0, 3.4, 3.5))
    b.obj("HoseReel", G.torus(0.3, 0.03, 24, 8), M("hose_orange"), loc=(-2.4, 3.2, 1.6), rot=(PI / 2, 0, 0))
    # Workbench in front of the welder; he stands behind it, facing the camera
    b.obj("BenchTop", G.box(2.8, 0.5, 0.08), M("steel"), loc=(0, 0.0, 0.92), bevel=0.01)
    for x in (-1.3, 1.3):
        for y in (-0.2, 0.2):
            b.obj("BenchLeg", G.box(0.08, 0.08, 0.9), M("dark_steel"), loc=(x, y, 0.45))
    b.obj("SteelPlate", G.box(1.4, 0.4, 0.03), M("steel"), loc=(0.0, 0.0, 0.98), bevel=0.004)
    # Glowing cut kerf advancing across the steel plate as the torch cuts
    kerf = b.obj("CutKerf", G.box(0.55, 0.025, 0.015, origin="left"), M("glow_orange"),
                 loc=(-0.15, 0.0, 0.996), scale=(0.01, 1, 1))
    key(kerf, f0 + 4, scale=(0.01, 1, 1))
    key(kerf, f0 + 72, scale=(1.0, 1, 1))

    valve = gas_cylinder(b, "CylOrange", (-2.3, -0.9, 0.2), M("cyl_grey"), M("band_white"))
    trolley(b, "Trolley", (-2.3, -0.9, 0.0))

    welder = R.Person(b, "Welder", "jack", (0.0, 0.42, 0.0), 0.0,
                      outfit("skin_mid", "leather", apron="leather", hands="leather"), f0=f0)
    welder.hat("helmet", M("black"))
    welder.visor(M("visor"), flip_frame=f1 - 38)
    welder.breathe(f0, f1)

    # Active cutting motion across the plate from x = -0.10 to x = +0.35
    cut_frames = [
        (f0, (-0.05, 0.05, 1.12), (-0.15, 0.0, 1.01)),
        (f0 + 24, (0.10, 0.05, 1.11), (0.02, 0.0, 1.01)),
        (f0 + 48, (0.24, 0.05, 1.11), (0.18, 0.0, 1.01)),
        (f0 + 72, (0.36, 0.05, 1.12), (0.32, 0.0, 1.01)),
    ]
    torch_kfs = []
    for fr, wrist_pt, tip_pt in cut_frames:
        gp = welder.reach(fr, "l", wrist_pt)
        torch_kfs.append((fr, gp, tip_pt))
    welder.work_motion("r", [
        (f0, (-0.22, 0.06, 1.08)),
        (f0 + 36, (-0.16, 0.05, 1.10)),
        (f0 + 72, (-0.12, 0.06, 1.08)),
    ])
    animate_torch(b, "CuttingTorch", torch_kfs)
    hand_end = torch_kfs[-1][1]
    hose(b, "HoseOrange", [valve, (-1.2, -0.7, 0.35), (-0.3, -0.4, 0.55), tuple(hand_end)],
         M("hose_orange"), 0.03, reveal=(f0, f0 + 20))

    def cut_tip_at(fr):
        u = max(0.0, min(1.0, (fr - f0) / 72.0))
        return (-0.15 + 0.47 * u, 0.0, 1.03)

    sparks(b, M("spark"), cut_tip_at, f0 + 4, f0 + 78, 65, random.Random(11), spread=1.3, lift=1.4)
    welder.thumbs_up(b.f1 - 36, b.f1, side="r")
    _celebrate(welder, b)
    glow = b.light("CutGlow", "POINT", (0.1, -0.1, 1.3), (1.0, 0.6, 0.25), 65.0, size=0.6)
    key(glow, f0, location=(-0.1, -0.1, 1.25))
    key(glow, f0 + 72, location=(0.3, -0.1, 1.25))
    b.light("BenchFill", "AREA", (0.0, -2.0, 3.0), (1.0, 0.9, 0.8), 350.0, size=3.0, target=(0, 0.5, 0.8))
    b.overlay(shot, title_size=0.13)


def stage_oxyacetylene(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(-3.4, -4.2, 1.8), end=(-2.9, -3.6, 1.8), target=(0.1, 0.1, 1.0), lens=40)
    b.world((0.04, 0.035, 0.03))
    b.floor(M("concrete"))
    b.obj("BackWall", G.box(18, 0.3, 7), M("wall_light"), loc=(0, 3.4, 3.5))
    pipe_geom = G.cylinder(0.14, 2.8, 20)
    b.obj("SeamPipe", pipe_geom, M("pipe_silver"), loc=(0.0, 0.0, 1.05), rot=(0, PI / 2, 0), smooth=True)
    for x in (-1.0, 1.0):
        b.obj("PipeStand", G.box(0.2, 0.4, 0.9), M("dark_steel"), loc=(x, 0.0, 0.45))
    seam = b.obj("WeldBead", G.box(0.85, 0.05, 0.03, origin="left"), M("glow_orange"),
                 loc=(-0.35, 0.0, 1.2), scale=(0.01, 1, 1))
    key(seam, f0 + 6, scale=(0.01, 1, 1))
    key(seam, f0 + 74, scale=(1.0, 1, 1))

    red = gas_cylinder(b, "CylRed", (-1.95, -0.9, 0.2), M("cyl_red"), M("band_white"))
    blue = gas_cylinder(b, "CylBlue", (-1.5, -0.9, 0.2), M("cyl_blue"), M("band_white"))
    trolley(b, "CartA", (-1.72, -0.9, 0.0), width=0.9)

    welder = R.Person(b, "OxyWelder", "jill", (0.1, 0.42, 0.0), 0.0,
                      outfit("skin_deep", "leather", apron="leather", hands="leather"), f0=f0)
    welder.hat("helmet", M("black"))
    welder.visor(M("visor"), flip_frame=f1 - 38)
    welder.breathe(f0, f1)

    # Track the welding torch along the pipe seam in lockstep with WeldBead
    weld_frames = [
        (f0, (-0.18, 0.06, 1.23), (-0.30, 0.0, 1.22)),
        (f0 + 25, (0.02, 0.06, 1.23), (-0.06, 0.0, 1.22)),
        (f0 + 50, (0.20, 0.06, 1.23), (0.18, 0.0, 1.22)),
        (f0 + 74, (0.36, 0.06, 1.23), (0.42, 0.0, 1.22)),
    ]
    torch_kfs = []
    for fr, wrist_pt, tip_pt in weld_frames:
        gp = welder.reach(fr, "l", wrist_pt)
        torch_kfs.append((fr, gp, tip_pt))
    welder.work_motion("r", [
        (f0, (-0.25, 0.05, 1.20)),
        (f0 + 38, (-0.12, 0.05, 1.22)),
        (f0 + 74, (-0.04, 0.05, 1.21)),
    ])
    animate_torch(b, "OxyTorch", torch_kfs)
    oxy_flame = flame(b, "OxyFlame", (-0.30, 0.0, 1.22), (-0.30, -0.1, 1.20), M("glow_blue"), radius=0.03)
    for fr, _gp, tip_pt in torch_kfs:
        key(oxy_flame, fr, location=tip_pt)
    flicker(oxy_flame, f0, f0 + 78, (1, 1, 1), 0.15, random.Random(3))
    key(oxy_flame, f0 + 80, scale=(0.01, 0.01, 0.01))

    fglow = b.light("FlameGlow", "POINT", (0.1, -0.1, 1.3), (0.45, 0.7, 1.0), 85.0, size=0.5)
    key(fglow, f0, location=(-0.25, -0.1, 1.3))
    key(fglow, f0 + 74, location=(0.38, -0.1, 1.3))

    hand_end = torch_kfs[-1][1]
    # Two hoses: red (fuel) from the acetylene valve, blue (oxygen) from the oxygen valve
    hose(b, "HoseRed", [red, (-1.2, -0.6, 0.25), (-0.4, -0.2, 0.5), tuple(hand_end)], M("hose_red"), 0.025,
         reveal=(f0, f0 + 20))
    hose(b, "HoseBlue", [blue, (-1.1, -0.6, 0.25), (-0.3, -0.2, 0.45), (0.05, -0.05, 0.95), tuple(hand_end)],
         M("hose_blue"), 0.025, reveal=(f0 + 4, f0 + 24))
    welder.thumbs_up(b.f1 - 36, b.f1, side="r")
    _celebrate(welder, b)

    def oxy_tip_at(fr):
        u = max(0.0, min(1.0, (fr - f0) / 74.0))
        return (-0.30 + 0.72 * u, 0.0, 1.22)

    sparks(b, M("spark"), oxy_tip_at, f0 + 6, f0 + 78, 28, random.Random(5), spread=0.7, lift=0.8)
    b.light("BenchFill", "AREA", (0.0, -2.0, 3.0), (1.0, 0.92, 0.85), 300.0, size=3.0, target=(0, 0.5, 0.8))
    b.overlay(shot, title_size=0.13)


def stage_domestic(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(2.2, -3.4, 1.7), end=(1.8, -3.0, 1.7), target=(-0.2, 1.4, 1.0), lens=40)
    b.world((0.28, 0.27, 0.25))
    b.floor(M("wood"))
    b.obj("KitchenWall", G.box(12, 0.3, 4.5), M("tile"), loc=(0, 2.6, 2.25))
    b.obj("Counter", G.box(3.4, 0.75, 0.9), M("cabinet"), loc=(0, 1.55, 0.45), bevel=0.01)
    b.obj("CounterTop", G.box(3.45, 0.8, 0.05), M("counter"), loc=(0, 1.55, 0.92))
    b.obj("UpperCabinet", G.box(1.4, 0.4, 0.8), M("cabinet"), loc=(-1.2, 2.2, 1.9), bevel=0.01)
    stove_top = 1.065
    b.obj("Stove", G.box(0.9, 0.6, 0.12), M("stainless"), loc=(0, 1.55, 1.005), bevel=0.01)
    burners = [(-0.2, 1.35), (0.2, 1.35), (-0.2, 1.75), (0.2, 1.75)]
    for i, (bx, by) in enumerate(burners):
        b.obj("BurnerRing", G.torus(0.09, 0.012, 20, 6), M("dark_steel"), loc=(bx, by, stove_top + 0.02))
        fl = flame(b, f"StoveFlame{i}", (bx, by, stove_top + 0.03), (bx, by, stove_top + 0.16), M("glow_blue"),
                   radius=0.035)
        flicker(fl, f0, f1, (1, 1, 1), 0.2, random.Random(20 + i))
    b.obj("Pot", G.cylinder(0.13, 0.14, 16), M("stainless"), loc=(0.2, 1.35, stove_top + 0.02), smooth=True)
    puffs(b, M("steam"), (0.2, 1.35, stove_top + 0.18), f0, f1, 5, random.Random(25), rise=0.65, radius=0.08)

    valve = gas_cylinder(b, "CylKitchen", (-2.1, 1.75, 0.2), M("cyl_grey"), M("band_white"))
    trolley(b, "CylStand", (-2.1, 1.75, 0.0), width=0.5)
    inlet = (-0.46, 1.55, 1.0)
    b.obj("StoveInlet", G.cylinder(0.03, 0.12, 10), M("brass"), loc=(-0.46, 1.55, 1.0),
          rot=(0, -PI / 2, 0), smooth=True)
    hose(b, "HoseKitchen", [valve, (-1.85, 1.75, 1.0), (-1.1, 1.7, 1.0), inlet],
         M("hose_orange"), 0.03, reveal=(f0, f0 + 24))

    cook = R.Person(b, "Cook", "jill", (0.65, 2.02, 0.0), 0.0,
                    outfit("skin_deep", "grey_shirt", trousers="navy", apron="apron_red"), f0=f0)
    cook.breathe(f0, f1)
    # Stirring motion over the simmering pot before transitioning to the thumbs-up
    stir_kfs = [
        (f0, (0.36, 1.58, 1.24), (0.20, 1.35, 1.15)),
        (f0 + 22, (0.42, 1.62, 1.25), (0.24, 1.38, 1.15)),
        (f0 + 44, (0.34, 1.60, 1.24), (0.17, 1.33, 1.15)),
        (f0 + 66, (0.40, 1.58, 1.24), (0.21, 1.36, 1.15)),
    ]
    spoon_kfs = []
    for fr, wrist_pt, tip_pt in stir_kfs:
        gp = cook.reach(fr, "r", wrist_pt)
        spoon_kfs.append((fr, gp, tip_pt))
    cook.work_motion("l", [
        (f0, (0.85, 1.72, 1.02)),
        (f0 + 36, (0.82, 1.68, 1.05)),
        (f0 + 68, (0.85, 1.72, 1.02)),
    ])
    animate_torch(b, "StirSpoon", spoon_kfs, body_mat=M("stainless"), hide_at=f1 - 48)
    cook.thumbs_up(b.f1 - 36, b.f1, side="r")
    _celebrate(cook, b)
    b.light("KitchenLight", "AREA", (0.0, -0.5, 3.0), (1.0, 0.92, 0.8), 500.0, size=3.0, target=(0, 1.2, 0.8))
    b.light("StoveGlow", "POINT", (0.0, 1.4, 1.25), (0.45, 0.7, 1.0), 45.0, size=0.6)
    b.overlay(shot, title_size=0.13)


def stage_commercial(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(-2.8, -3.2, 1.9), end=(-2.4, -2.8, 1.9), target=(0.0, 1.5, 1.0), lens=38)
    b.world((0.05, 0.05, 0.055))
    b.floor(M("concrete"))
    b.obj("KitchenBack", G.box(14, 0.3, 6), M("tile"), loc=(0, 2.7, 3.0))
    b.obj("Range", G.box(3.0, 0.9, 0.9), M("stainless"), loc=(0, 2.0, 0.45), bevel=0.01)
    b.obj("Griddle", G.box(2.4, 0.7, 0.04), M("dark_steel"), loc=(-0.3, 2.0, 0.92))
    for i, x in enumerate((-1.0, -0.3, 0.4)):
        b.obj("BurnerSlot", G.box(0.5, 0.02, 0.05), M("glow_blue"), loc=(x, 1.545, 0.25))
        fl = flame(b, f"GridFlame{i}", (x, 2.0, 0.94), (x, 2.0, 1.12), M("glow_blue"), radius=0.035)
        flicker(fl, f0, f1, (1, 1, 1), 0.2, random.Random(30 + i))
    b.obj("FryerBody", G.box(0.6, 0.7, 0.6), M("stainless"), loc=(1.45, 1.5, 0.3), bevel=0.01)
    b.obj("FryerOil", G.cylinder(0.22, 0.03, 16), M("wood"), loc=(1.45, 1.5, 0.58), smooth=True)
    b.obj("Hood", G.box(3.8, 1.0, 0.25), M("stainless"), loc=(0, 1.8, 2.6), bevel=0.02)
    for x in (-1.5, 1.5):
        b.obj("HoodDuct", G.cylinder(0.12, 1.5, 12), M("stainless"), loc=(x, 1.8, 2.6), smooth=True)
    for i in range(3):
        puffs(b, M("steam"), (-0.8 + i * 0.6, 1.9, 0.9), f0, f1, 4, random.Random(40 + i), rise=1.1)

    # Gas feed from a wall manifold to the range inlet
    wall_outlet = (-2.7, 2.3, 0.9)
    b.obj("WallOutlet", G.cylinder(0.05, 0.2, 10), M("brass"), loc=(-2.7, 2.55, 0.9), rot=(PI / 2, 0, 0))
    b.obj("RangeInlet", G.cylinder(0.04, 0.12, 10), M("brass"), loc=(-1.5, 1.9, 0.3), rot=(0, -PI / 2, 0))
    hose(b, "HoseRange", [wall_outlet, (-2.2, 1.2, 0.12), (-1.8, 1.25, 0.12), (-1.54, 1.9, 0.3)],
         M("hose_orange"), 0.03, reveal=(f0, f0 + 24))

    # Pass counter between the chef and the camera
    b.obj("PassTop", G.box(2.0, 0.6, 0.06), M("steel"), loc=(0.6, -0.15, 1.0), bevel=0.01)
    for x in (-0.3, 1.5):
        for y in (-0.4, 0.1):
            b.obj("PassLeg", G.box(0.06, 0.06, 0.95), M("dark_steel"), loc=(x, y, 0.47))
    chef = R.Person(b, "Chef", "jack", (0.6, 0.3, 0.0), 0.0,
                    outfit("skin_mid", "chef_white", trousers="navy", apron="black"), f0=f0)
    chef.hat("toque", M("chef_white"))
    chef.breathe(f0, f1)
    # Chef works the pass/griddle with a spatula before giving the thumbs-up
    spatula_frames = [
        (f0, (0.28, -0.06, 1.12), (0.12, -0.22, 1.04)),
        (f0 + 24, (0.42, -0.05, 1.14), (0.30, -0.20, 1.05)),
        (f0 + 48, (0.24, -0.06, 1.12), (0.10, -0.22, 1.04)),
        (f0 + 68, (0.36, -0.06, 1.13), (0.22, -0.21, 1.04)),
    ]
    spat_kfs = []
    for fr, wrist_pt, tip_pt in spatula_frames:
        gp = chef.reach(fr, "r", wrist_pt)
        spat_kfs.append((fr, gp, tip_pt))
    chef.work_motion("l", [
        (f0, (0.88, -0.08, 1.07)),
        (f0 + 34, (0.82, -0.12, 1.10)),
        (f0 + 68, (0.88, -0.08, 1.07)),
    ])
    animate_torch(b, "ChefSpatula", spat_kfs, body_mat=M("stainless"), hide_at=f1 - 48)
    chef.thumbs_up(b.f1 - 36, b.f1, side="r")
    _celebrate(chef, b)
    b.light("PassLight", "AREA", (0.0, -1.0, 3.2), (1.0, 0.95, 0.85), 450.0, size=3.0, target=(0, 1.5, 0.9))
    b.overlay(shot, title_size=0.13)


def stage_outdoor(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(-0.6, -7.2, 2.0), end=(-0.1, -6.4, 2.0), target=(0.0, 1.0, 1.1), lens=35)
    b.world((0.45, 0.62, 0.9), sun_energy=2.6)
    b.floor(M("grass"), size=80)
    tree(b, "TreeA", (-3.8, 4.5, 0.0), height=2.4, crown=1.2)
    tree(b, "TreeB", (3.5, 5.0, 0.0), height=2.0, crown=1.0)
    tree(b, "TreeC", (-1.0, 8.0, 0.0), height=3.0, crown=1.5)
    b.obj("Tent", tent_geom(), M("tent"), loc=(-1.4, 3.0, 0.0))

    # Grill and sausages
    b.obj("GrillBowl", G.sphere(0.36, 16, 8, center=(0, 0, 0), sz=0.5), M("steel"), loc=(0.3, 0.6, 0.92), smooth=True)
    for dx, dy in ((-0.25, -0.2), (0.25, -0.2), (0.0, 0.25)):
        b.obj("GrillLeg", G.cylinder(0.02, 0.85, 8), M("dark_steel"), loc=(0.3 + dx, 0.6 + dy, 0.0))
    b.obj("GrillGrate", G.cylinder(0.33, 0.02, 20), M("dark_steel"), loc=(0.3, 0.6, 0.95), smooth=True)
    for i, (sx, sy) in enumerate(((0.15, 0.55), (0.35, 0.7), (0.45, 0.5), (0.2, 0.7))):
        b.obj("Sausage", G.cylinder(0.035, 0.22, 10), M("apron_red"), loc=(sx, sy, 1.0),
              rot=(PI / 2, 0, 0.4 * i), smooth=True)
    for i, x in enumerate((0.1, 0.3, 0.5)):
        fl = flame(b, f"GrillFire{i}", (x, 0.6, 0.55), (x, 0.6, 0.85), M("glow_orange"), radius=0.05)
        flicker(fl, f0, f1, (1, 1, 1), 0.25, random.Random(60 + i))
    puffs(b, M("steam"), (0.3, 0.6, 1.02), f0, f1, 4, random.Random(65), rise=0.8, radius=0.09)

    # Propane cylinder and red hose to the grill
    valve = gas_cylinder(b, "Propane", (-1.3, 0.6, 0.0), M("cyl_grey"), M("band_white"), h=0.8, r=0.14)
    hose(b, "HoseGrill", [valve, (-0.9, 0.2, 0.15), (-0.45, 0.1, 0.2), (-0.06, 0.6, 0.6)],
         M("hose_red"), 0.025, reveal=(f0, f0 + 24))
    # Small generator and camp stove
    b.obj("Generator", G.box(0.7, 0.45, 0.5), M("dark_steel"), loc=(2.6, -0.4, 0.25), bevel=0.02)
    b.obj("GenHandle", G.box(0.5, 0.04, 0.04), M("black"), loc=(2.6, -0.65, 0.55))

    camper_a = R.Person(b, "CamperA", "jack", (-0.6, -0.2, 0.0), 0.0,
                        outfit("skin_mid", "hi_vis", trousers="navy", sleeves="hi_vis"), f0=f0)
    camper_a.breathe(f0, f1)
    camper_a.work_motion("l", [
        (f0, (-0.22, -0.45, 1.14)),
        (f0 + 24, (-0.12, -0.35, 1.18)),
        (f0 + 48, (-0.25, -0.45, 1.14)),
        (f0 + 68, (-0.16, -0.38, 1.16)),
    ])
    camper_a.work_motion("r", [
        (f0, (-0.78, -0.52, 1.08)),
        (f0 + 36, (-0.72, -0.55, 1.12)),
        (f0 + 68, (-0.78, -0.52, 1.08)),
    ])
    camper_b = R.Person(b, "CamperB", "jill", (1.5, -0.2, 0.0), 0.0,
                        outfit("skin_deep", "overalls", trousers="overalls", sleeves="grey_shirt"), f0=f0)
    camper_b.hat("straw", M("straw"))
    camper_b.breathe(f0, f1)
    camper_b.work_motion("r", [
        (f0, (1.18, -0.52, 1.10)),
        (f0 + 26, (1.08, -0.42, 1.16)),
        (f0 + 52, (1.20, -0.50, 1.10)),
        (f0 + 68, (1.15, -0.48, 1.12)),
    ])
    camper_b.work_motion("l", [
        (f0, (1.72, -0.52, 1.05)),
        (f0 + 36, (1.68, -0.56, 1.09)),
        (f0 + 68, (1.72, -0.52, 1.05)),
    ])

    camper_a.thumbs_up(b.f1 - 36, b.f1, side="r")
    _celebrate(camper_a, b)
    camper_b.thumbs_up(b.f1 - 36, b.f1, side="r")
    _celebrate(camper_b, b)
    b.light("SunsetFill", "AREA", (-3.0, -3.0, 4.0), (1.0, 0.8, 0.6), 400.0, size=5.0, target=(0, 1, 1))
    b.overlay(shot, title_size=0.13)


def stage_agriculture(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(-0.6, -6.0, 1.8), end=(-0.1, -5.2, 1.8), target=(0.2, 0.9, 1.2), lens=38)
    b.world((0.2, 0.2, 0.18), sun_energy=1.8)
    b.floor(M("straw_floor"))
    b.obj("BarnBack", G.box(14, 0.3, 4.5), M("barn_wood"), loc=(0, 3.0, 2.25))
    b.obj("BarnSide", G.box(0.3, 14, 4.5), M("barn_wood"), loc=(-3.2, 2.0, 2.25))
    b.obj("RoofBeam", G.box(14, 0.2, 0.2), M("wood_dark"), loc=(0, 1.2, 3.9))

    # Brooder heater: an inverted hood hanging from the beam
    b.obj("BrooderHood", G.cone(0.45, 0.4, 20), M("steel"), loc=(0.0, 1.2, 1.9), rot=(PI, 0, 0), smooth=True)
    b.obj("BrooderRod", G.cylinder(0.02, 2.0, 8), M("dark_steel"), loc=(0.0, 1.2, 1.9))
    fl = flame(b, "BrooderFlame", (0.0, 1.2, 1.5), (0.0, 1.2, 1.25), M("glow_orange"), radius=0.09)
    flicker(fl, f0, f1, (1, 1, 1), 0.2, random.Random(70))
    b.light("BrooderGlow", "POINT", (0.0, 1.2, 1.3), (1.0, 0.55, 0.2), 80.0, size=0.5)

    rng = random.Random(77)
    chicks = []
    for i in range(14):
        ang = rng.uniform(0, 2 * PI)
        rad = rng.uniform(0.2, 1.0)
        cx, cy = 0.0 + rad * math.cos(ang), 1.2 + rad * math.sin(ang) * 0.8
        c = b.obj(f"Chick{i}", G.sphere(0.07, 10, 6), M("chick"), loc=(cx, cy, 0.07), smooth=True)
        bob = rng.randint(0, 10)
        for fr in range(f0 + bob, f1, 12):
            key(c, fr, location=(cx, cy, 0.07))
            key(c, fr + 6, location=(cx, cy, 0.14))
        chicks.append(c)

    valve = gas_cylinder(b, "CylFarm", (-2.1, 0.2, 0.0), M("cyl_grey"), M("band_white"))
    trolley(b, "FarmStand", (-2.1, 0.2, 0.0), width=0.5)
    inlet = (-0.45, 1.2, 1.9)
    hose(b, "HoseBrooder", [valve, (-1.6, 0.5, 0.2), (-1.4, 0.8, 1.2), (-0.9, 1.0, 1.7), inlet],
         M("hose_orange"), 0.03, reveal=(f0, f0 + 24))

    # Crop dryer drum in the next bay
    b.obj("CropDrum", G.cylinder(0.6, 2.2, 20, z0=-1.1), M("steel"), loc=(3.6, 2.2, 1.0), rot=(0, PI / 2, 0),
          smooth=True)
    dfl = flame(b, "DryerFlame", (3.6, 2.2, 0.5), (3.6, 2.2, 0.1), M("glow_orange"), radius=0.2)
    flicker(dfl, f0, f1, (1, 1, 1), 0.2, random.Random(71))

    farmer = R.Person(b, "Farmer", "jack", (1.2, -0.6, 0.0), 0.0,
                      outfit("skin_deep", "overalls", trousers="overalls", sleeves="grey_shirt", hands="leather"),
                      f0=f0)
    farmer.hat("straw", M("straw"))
    farmer.breathe(f0, f1)
    farmer.work_motion("r", [
        (f0, (0.92, -0.48, 1.12)),
        (f0 + 24, (0.78, -0.35, 1.26)),
        (f0 + 48, (0.88, -0.42, 1.18)),
        (f0 + 68, (0.94, -0.48, 1.12)),
    ])
    farmer.work_motion("l", [
        (f0, (1.38, -0.52, 1.06)),
        (f0 + 36, (1.34, -0.48, 1.12)),
        (f0 + 68, (1.38, -0.52, 1.06)),
    ])
    farmer.thumbs_up(b.f1 - 36, b.f1, side="r")
    _celebrate(farmer, b)
    b.light("BarnSun", "AREA", (0.0, -2.0, 3.6), (1.0, 0.85, 0.65), 380.0, size=4.0, target=(0, 1, 0.8))
    b.overlay(shot, title_size=0.13)


def stage_manufacturing(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(2.6, -5.2, 2.0), end=(2.1, -4.6, 2.0), target=(-0.2, 1.0, 1.3), lens=38)
    b.world((0.05, 0.055, 0.065))
    b.floor(M("concrete"))
    b.obj("FactoryWall", G.box(16, 0.3, 6), M("wall_dark"), loc=(0, 3.6, 3.0))
    for x in (-3.0, 0.0, 3.0):
        b.obj("RoofBeam", G.box(0.25, 10, 0.25), M("dark_steel"), loc=(x, 0.5, 4.2))
    b.obj("Conveyor", G.box(6.0, 0.4, 0.1), M("conveyor"), loc=(0, 0.5, 0.92), bevel=0.01)
    for x in (-2.8, 2.8):
        for y in (0.2, 0.8):
            b.obj("ConvLeg", G.box(0.1, 0.1, 0.9), M("steel"), loc=(x, y, 0.45))
    for i in range(5):
        start_x = -3.2 + i * 1.3
        box = b.obj("Crate", G.box(0.4, 0.35, 0.3), M("cardboard"), loc=(start_x, 0.5, 1.12), bevel=0.01)
        key(box, f0, location=(-3.2 + i * 1.3, 0.5, 1.12))
        key(box, f1, location=(3.2 + i * 1.3 - 0.5, 0.5, 1.12))
    b.obj("Furnace", G.box(1.2, 0.9, 1.4), M("steel"), loc=(2.6, 2.0, 0.7), bevel=0.02)
    b.obj("FurnaceDoor", G.box(0.6, 0.02, 0.5), M("glow_orange"), loc=(2.6, 1.54, 0.7))
    b.light("FurnaceGlow", "POINT", (2.6, 1.2, 1.0), (1.0, 0.45, 0.15), 120.0, size=0.6)

    # Compressed-air pipe rack and drop to the tool
    b.obj("AirPipe", G.cylinder(0.05, 6.0, 12), M("pipe_silver"), loc=(-3.0, 2.4, 2.6), rot=(0, PI / 2, 0),
          smooth=True)
    b.obj("AirDrop", G.cylinder(0.04, 1.2, 12), M("pipe_silver"), loc=(-0.9, 2.4, 1.4), smooth=True)
    outlet = (-0.9, 2.4, 1.4)

    # Worker stands behind the conveyor belt so moving crates never clip her hands
    worker = R.Person(b, "Worker", "jill", (0.6, 1.02, 0.0), 0.0,
                      outfit("skin_mid", "hi_vis", trousers="navy", sleeves="grey_shirt", hands="leather"), f0=f0)
    worker.hat("hardhat", M("hardhat"))
    worker.breathe(f0, f1)

    # Rhythmic pneumatic tool actuations over the passing crates
    tool_frames = [
        (f0, (0.42, 0.68, 1.36), (0.42, 0.52, 1.28)),
        (f0 + 18, (0.42, 0.66, 1.28), (0.42, 0.50, 1.18)),
        (f0 + 36, (0.42, 0.68, 1.36), (0.42, 0.52, 1.28)),
        (f0 + 54, (0.42, 0.66, 1.28), (0.42, 0.50, 1.18)),
        (f0 + 72, (0.42, 0.68, 1.34), (0.42, 0.52, 1.26)),
    ]
    air_kfs = []
    for fr, wrist_pt, tip_pt in tool_frames:
        gp = worker.reach(fr, "r", wrist_pt)
        air_kfs.append((fr, gp, tip_pt))
    worker.work_motion("l", [
        (f0, (0.82, 0.72, 1.16)),
        (f0 + 36, (0.78, 0.70, 1.20)),
        (f0 + 70, (0.82, 0.72, 1.16)),
    ])
    animate_torch(b, "AirTool", air_kfs, body_mat=M("steel"))
    hand0 = air_kfs[0][1]
    hose(b, "HoseAir", [outlet, (-0.7, 1.5, 1.6), (-0.1, 0.75, 1.7), tuple(hand0)], M("hose_blue"), 0.025,
         reveal=(f0, f0 + 24))
    worker.thumbs_up(b.f1 - 36, b.f1, side="l")
    _celebrate(worker, b)
    b.light("LineLight", "AREA", (0.0, -1.5, 3.5), (0.95, 0.95, 1.0), 500.0, size=4.0, target=(0, 0.8, 0.8))
    b.overlay(shot, title_size=0.13)


def stage_outro(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(0.0, -7.2, 2.0), end=(0.0, -6.4, 2.0), target=(0.0, 0.0, 1.9), drop=0.0)
    b.world((0.015, 0.015, 0.02), sun_energy=0.0)
    b.floor(M("dark_steel"))
    b.light("KeyTop", "AREA", (0, -1.0, 6.0), (1.0, 0.95, 0.9), 850.0, size=4.0, target=(0, 0, 0))
    b.light("RimAccent", "AREA", (3.5, 2.5, 3.2), (1.0, 0.45, 0.2), 420.0, size=3.0, target=(0, 0, 2.0))
    # The hose from the intro coils into a clean circular emblem framing the three product hoses
    pts = []
    for i in range(8):
        a = 2 * PI * i / 8
        pts.append((0.0 + 0.85 * math.cos(a), 0.0, 2.05 + 0.85 * math.sin(a)))
    ring = hose(b, "HoseLoop", pts, M("hose_orange"), 0.038, reveal=(f0, f0 + 36), fittings=False)
    ring.data.splines[0].use_cyclic_u = True
    # Trio of red, blue, and orange 3-layer reinforced hose tips inside the emblem (matching all-products.jpg)
    for idx, (hx, hmat, hrad) in enumerate((
        (-0.22, M("hose_red"), 0.044),
        (0.0, M("hose_blue"), 0.044),
        (0.24, M("hose_orange"), 0.052),
    )):
        b.segment(f"OutroHeroStub_{idx}", (hx - 0.12, 0.35, 2.22), (hx, -0.15, 1.92), hrad, hmat)
        hose_end_cap(b, f"OutroHeroCap_{idx}", loc=(hx, -0.15, 1.92), direction=(0.22, -0.92, -0.32),
                     outer_mat=hmat, radius=hrad, pop_in=f0 + 20 + idx * 5)

    # Wordmark above the loop, flanked by subtle glowing accent rules
    cu = bpy.data.curves.new("OutroWordmark", "FONT")
    cu.body = "RhyolitePrime"
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.03
    cu.bevel_depth = 0.005
    font = _get_font()
    if font is not None:
        cu.font = font
    cu.materials.append(M("wordmark_outro"))
    cu.size = 0.36
    wm = bpy.data.objects.new("OutroWordmark", cu)
    wm.rotation_euler = (PI / 2, 0, 0)
    wm.location = (0, 0.0, 3.1)
    b.link(wm)
    key(wm, f0 + 24, scale=(0.01, 0.01, 0.01))
    key(wm, f0 + 44, scale=(1, 1, 1))
    # Hold the three commitments and WhatsApp / Call / Email CTA right to the final frame (1080)
    b.overlay(shot, stagger=12, title_size=0.13, hold_end=True)


STAGE_BUILDERS = [
    stage_intro,
    stage_welding,
    stage_oxyacetylene,
    stage_domestic,
    stage_commercial,
    stage_outdoor,
    stage_agriculture,
    stage_manufacturing,
    stage_outro,
]


def setup_world_nodes(world):
    """Build a vertical ground-to-zenith gradient in `AdWorld` so metals reflect a horizon."""
    nt = world.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.name = "WorldGradientMix"
    mix.inputs[1].default_value = (0.01, 0.01, 0.015, 1.0)
    mix.inputs[2].default_value = (0.04, 0.04, 0.06, 1.0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.name = "Background"
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mix.inputs[0])
    nt.links.new(mix.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_compositor(scene):
    """Enable a subtle Fog Glow bloom in the Blender compositor for sparks, flames, and wordmarks."""
    try:
        scene.use_nodes = True
    except Exception:
        pass
    try:
        if hasattr(scene, "compositing_node_group"):
            tree = bpy.data.node_groups.new("AdCompositor", "CompositorNodeTree")
            scene.compositing_node_group = tree
            tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            rl = tree.nodes.new("CompositorNodeRLayers")
            glare = tree.nodes.new("CompositorNodeGlare")
            out = tree.nodes.new("NodeGroupOutput")
            if "Type" in glare.inputs:
                glare.inputs["Type"].default_value = "Fog Glow"
            if "Threshold" in glare.inputs:
                glare.inputs["Threshold"].default_value = 1.6
            if "Strength" in glare.inputs:
                glare.inputs["Strength"].default_value = 0.32
            tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
            tree.links.new(glare.outputs["Image"], out.inputs["Image"])
    except Exception as exc:
        print("[advert] compositor glare skipped:", exc)


def build_scene(scene):
    """Populate the current scene with all nine stages. Returns the number of stages built."""
    assert len(STAGE_BUILDERS) == len(S.SHOTS), "every shot needs a builder"
    _MATS.clear()
    # Global directional light whose energy is keyframed per stage (0 in dark studio stages)
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 0.0
    sun.color = (1.0, 0.95, 0.9)
    sun.angle = math.radians(3.0)
    sun_obj = bpy.data.objects.new("Sun", sun)
    sun_obj.rotation_euler = (math.radians(55), math.radians(15), math.radians(-35))
    scene.collection.objects.link(sun_obj)

    world = bpy.data.worlds.new("AdWorld")
    world.use_nodes = True
    setup_world_nodes(world)
    scene.world = world

    b = Builder(scene, sun_data=sun)
    for i, (shot, fn) in enumerate(zip(S.SHOTS, STAGE_BUILDERS)):
        b.begin(i, shot)
        fn(b, shot)
        b.finish()
        print(f"[advert] stage {i + 1}/{len(S.SHOTS)} built: {shot['id']} ({len(b.objs)} objects)")

    setup_compositor(scene)
    scene.camera = bpy.data.objects["Cam01"]
    return len(S.SHOTS)
