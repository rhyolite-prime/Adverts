"""Builds the RhyolitePrime advert inside Blender (tested against the Blender 5.x Python API).

Layout of the timeline
----------------------
* 9 stages (see shots.py), 5 seconds each, 120 frames at 24 fps.
* Stage i owns frames [1 + 120*i, 120*(i+1)].
* Each stage has its own camera. Camera markers on the timeline switch the
  active camera at each stage start.
* Every object in a stage is keyframed to be visible only inside that stage's
  frame range (hide_viewport / hide_render), so all stages can live in one scene.
* The on-screen text (key selling point, spec line, label) and the progress bar
  are parented to the stage camera, so they stay put on screen.

Coordinate conventions
----------------------
* 1 unit = 1 metre. Z is up. Floor is z = 0.
* Characters face -Y when their yaw is 0. yaw = pi faces +Y.
* Arm joints rotate about X. A negative shoulder angle swings the arm forward (-Y).
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import geometry as G
import shots as S

FRAMES = int(round(S.SHOT_SECONDS * S.FPS))  # 120
OVERLAY_DEPTH = 3.0          # distance of the overlay plane in front of the camera
SENSOR_HALF = 18.0           # 36 mm sensor, half width, for 16:9 frames
PI = math.pi
SUBJECT_DROP = 0.22          # metres the camera aim is lowered for application stages


def stage_frames(index):
    f0 = 1 + index * FRAMES
    return f0, f0 + FRAMES - 1


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

MATERIAL_DEFS = {
    "concrete": dict(color=(0.24, 0.24, 0.25), rough=0.9),
    "wall_dark": dict(color=(0.09, 0.11, 0.14), rough=0.85),
    "wall_light": dict(color=(0.55, 0.55, 0.52), rough=0.8),
    "steel": dict(color=(0.5, 0.5, 0.54), rough=0.3, metal=1.0),
    "dark_steel": dict(color=(0.08, 0.08, 0.09), rough=0.4, metal=0.6),
    "wood": dict(color=(0.42, 0.26, 0.13), rough=0.6),
    "wood_dark": dict(color=(0.2, 0.12, 0.07), rough=0.7),
    "skin_light": dict(color=(0.42, 0.27, 0.19), rough=0.5),
    "skin_mid": dict(color=(0.3, 0.19, 0.13), rough=0.5),
    "skin_deep": dict(color=(0.2, 0.125, 0.085), rough=0.5),
    "hair_coily": dict(color=(0.02, 0.014, 0.011), rough=0.85),
    "navy": dict(color=(0.08, 0.1, 0.22), rough=0.8),
    "cap": dict(color=(0.2, 0.3, 0.5), rough=0.7),
    "black": dict(color=(0.02, 0.02, 0.02), rough=0.6),
    "leather": dict(color=(0.32, 0.18, 0.09), rough=0.8),
    "overalls": dict(color=(0.1, 0.27, 0.55), rough=0.8),
    "apron_red": dict(color=(0.6, 0.07, 0.07), rough=0.8),
    "chef_white": dict(color=(0.93, 0.93, 0.92), rough=0.7),
    "hi_vis": dict(color=(1.0, 0.8, 0.05), rough=0.5, emit=(1.0, 0.7, 0.0), emit_strength=0.3),
    "hardhat": dict(color=(1.0, 0.75, 0.05), rough=0.4),
    "straw": dict(color=(0.75, 0.6, 0.3), rough=0.9),
    "grey_shirt": dict(color=(0.4, 0.42, 0.45), rough=0.8),
    "hose_orange": dict(color=(1.0, 0.36, 0.04), rough=0.35),
    "hose_red": dict(color=(0.75, 0.05, 0.04), rough=0.35),
    "hose_blue": dict(color=(0.03, 0.22, 0.8), rough=0.35),
    "cyl_grey": dict(color=(0.42, 0.43, 0.47), rough=0.35, metal=0.6),
    "cyl_red": dict(color=(0.6, 0.05, 0.04), rough=0.35, metal=0.4),
    "cyl_blue": dict(color=(0.04, 0.17, 0.62), rough=0.35, metal=0.4),
    "brass": dict(color=(0.8, 0.6, 0.25), rough=0.3, metal=1.0),
    "band_white": dict(color=(0.95, 0.95, 0.95), rough=0.5),
    "grass": dict(color=(0.13, 0.36, 0.09), rough=0.95),
    "bark": dict(color=(0.25, 0.15, 0.08), rough=0.9),
    "leaf": dict(color=(0.1, 0.3, 0.1), rough=0.9),
    "tent": dict(color=(0.52, 0.56, 0.32), rough=0.9),
    "tile": dict(color=(0.9, 0.88, 0.83), rough=0.4),
    "cabinet": dict(color=(0.78, 0.72, 0.6), rough=0.5),
    "counter": dict(color=(0.14, 0.14, 0.15), rough=0.3),
    "stainless": dict(color=(0.65, 0.66, 0.68), rough=0.22, metal=1.0),
    "straw_floor": dict(color=(0.55, 0.42, 0.2), rough=0.95),
    "barn_wood": dict(color=(0.3, 0.18, 0.1), rough=0.8),
    "chick": dict(color=(1.0, 0.82, 0.2), rough=0.6),
    "cardboard": dict(color=(0.6, 0.45, 0.28), rough=0.8),
    "conveyor": dict(color=(0.07, 0.07, 0.08), rough=0.6),
    "pipe_silver": dict(color=(0.7, 0.7, 0.72), rough=0.3, metal=1.0),
    "steam": dict(color=(0.9, 0.9, 0.92), rough=1.0, emit=(0.9, 0.9, 0.95), emit_strength=0.25),
    "visor": dict(color=(0.02, 0.05, 0.12), rough=0.05, metal=0.5, emit=(0.2, 0.5, 1.0), emit_strength=0.6),
    "wordmark": dict(color=(1.0, 0.42, 0.08), rough=0.2, metal=1.0),
    # Outro on a near-black stage: a metal would reflect the dark world, so use an emissive, non-metal copy.
    "wordmark_outro": dict(color=(1.0, 0.42, 0.08), rough=0.35, metal=0.0, emit=(1.0, 0.42, 0.08), emit_strength=1.4),
    "glow_orange": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.42, 0.06), emit_strength=22.0),
    "glow_blue": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(0.3, 0.62, 1.0), emit_strength=30.0),
    "glow_red": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.15, 0.05), emit_strength=18.0),
    "spark": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.7, 0.25), emit_strength=40.0),
    "text_white": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 1.0, 1.0), emit_strength=1.6),
    "text_accent": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.45, 0.1), emit_strength=2.4),
    "bar_accent": dict(color=(0.0, 0.0, 0.0), rough=1.0, emit=(1.0, 0.45, 0.1), emit_strength=3.0),
}

_MATS = {}


def _set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value
    else:
        print(f"[advert] warning: shader input '{name}' not found")


def M(name):
    """Return (creating on first use) the named material."""
    if name in _MATS:
        return _MATS[name]
    d = MATERIAL_DEFS[name]
    mat = bpy.data.materials.new(f"ad_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    _set_input(bsdf, "Base Color", (*d["color"], 1.0))
    _set_input(bsdf, "Roughness", d.get("rough", 0.5))
    _set_input(bsdf, "Metallic", d.get("metal", 0.0))
    if name.startswith("skin"):
        # Light scattering under the skin softens the CG look.
        _set_input(bsdf, "Subsurface Weight", 0.06)
        _set_input(bsdf, "Subsurface Radius", (0.8, 0.35, 0.2))
        _set_input(bsdf, "Specular IOR Level", 0.4)
    if "emit" in d:
        _set_input(bsdf, "Emission Color", (*d["emit"], 1.0))
        _set_input(bsdf, "Emission Strength", d.get("emit_strength", 1.0))
    _MATS[name] = mat
    return mat


def band_material():
    """Dark translucent bar behind the overlay text (Mix of Transparent and Principled)."""
    mat = bpy.data.materials.new("ad_overlay_band")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    _set_input(principled, "Base Color", (0.01, 0.012, 0.02, 1.0))
    _set_input(principled, "Roughness", 1.0)
    mix.inputs[0].default_value = 0.8  # 80% opaque
    nt.links.new(transparent.outputs[0], mix.inputs[1])
    nt.links.new(principled.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
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
    def __init__(self, scene):
        self.scene = scene
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
            parent=None, smooth=False, bevel=0.0):
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
                mod.segments = 2
                mod.limit_method = "ANGLE"
        o.location = loc
        o.rotation_euler = rot
        o.scale = scale
        if parent is not None:
            o.parent = parent
        return self.link(o)

    def segment(self, name, p0, p1, radius, mat, cone=False, radius_top=None):
        """Cylinder (or cone, apex at p1) from p0 to p1."""
        p0v, p1v = Vector(p0), Vector(p1)
        length = (p1v - p0v).length
        if cone:
            geom = G.cone(radius, length, 12)
        else:
            geom = G.cylinder(radius, length, 12, r_top=radius_top)
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

    def world(self, color):
        self.world_color = color
        bg = self.scene.world.node_tree.nodes["Background"]
        sock = bg.inputs["Color"]
        sock.default_value = (*color, 1.0)
        sock.keyframe_insert("default_value", frame=self.f0)
        sock.keyframe_insert("default_value", frame=self.f1)

    # --- camera -----------------------------------------------------------
    def camera(self, start, end, target, lens=35.0, drop=SUBJECT_DROP):
        """`drop` tilts the aim down so the subject sits higher, above the lower-third band."""
        target = (target[0], target[1], target[2] - drop)
        name = f"Cam{self.index + 1:02d}"
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 300.0
        cam = bpy.data.objects.new(name, cd)
        mid = (Vector(start) + Vector(end)) / 2
        cam.rotation_euler = (Vector(target) - mid).to_track_quat("-Z", "Y").to_euler()
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
        cu.materials.append(mat)
        o = bpy.data.objects.new(name, cu)
        o.parent = self.cam
        o.location = loc
        return self.link(o)

    def overlay(self, shot, stagger=0, title_size=0.13):
        """Lower-third overlay: label, key selling point, spec line, progress bar.

        Everything sits on the camera at OVERLAY_DEPTH, so it stays on screen.
        """
        f0, f1 = self.f0, self.f1
        half_w = OVERLAY_DEPTH * SENSOR_HALF / self.lens
        z = -OVERLAY_DEPTH + 0.02          # text and bar sit slightly in front of the band
        band = self.obj("OverlayBand", G.box(2 * half_w + 0.4, 0.62, 0.001), band_material(),
                        loc=(0, -0.64, -OVERLAY_DEPTH - 0.02), parent=self.cam)

        self.obj("OverlayTopBand", G.box(2 * half_w + 0.4, 0.16, 0.001), band_material(),
                 loc=(0, 0.72, -OVERLAY_DEPTH - 0.02), parent=self.cam)
        label = self.text("OverlayLabel", shot["label"], 0.05, M("text_accent"),
                          (-half_w + 0.14, 0.72, z), align_x="LEFT", align_y="CENTER")
        key(label, f0, location=(-half_w - 0.6, 0.72, z))
        key(label, f0 + 12, location=(-half_w + 0.14, 0.72, z))

        lines = shot["title"].split("\n")
        base = title_size if len(lines) == 1 else min(title_size, 0.33 / (len(lines) * 1.3))
        title_objs = [self.text(f"OverlayTitle{i}", ln, base, M("text_white"), (0, 0, z))
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
            key(o, f1 - 10, scale=(1.0, 1.0, 1.0))
            key(o, f1, scale=(0.01, 0.01, 0.01))

        spec_top = -0.4 - len(lines) * pitch - 0.02
        spec = self.text("OverlaySpec", shot["spec"], 0.05, M("text_white"), (0, spec_top, z))
        key(spec, f0 + 8, scale=(0.01, 0.01, 0.01))
        key(spec, f0 + 24, scale=(1.0, 1.0, 1.0))
        key(spec, f1 - 10, scale=(1.0, 1.0, 1.0))
        key(spec, f1, scale=(0.01, 0.01, 0.01))

        bar = self.obj("OverlayProgress", G.box(1.0, 0.02, 0.001, origin="left"), M("bar_accent"),
                       loc=(-half_w, -0.85, z), parent=self.cam, scale=(0.001, 1, 1))
        key(bar, f0, scale=(0.001, 1, 1))
        key(bar, f1, scale=(2 * half_w, 1, 1))
        return band


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------

SIDE = {"r": -1.0, "l": 1.0}   # 'r' = character's right; at yaw 0 that is -X
UPPER, FORE = 0.3, 0.3          # arm segment lengths used for IK


class Human:
    """Stylised person built from primitives, with shoulder/elbow/hip/knee pivots."""

    def __init__(self, b, name, loc, yaw, skin, top, bottom, shoe=None, hat=None, hat_style=None,
                 apron=None, vest=None, visor=None, gloves=None, hair=True):
        self.b = b
        self.loc = Vector(loc)
        self.yaw = yaw
        root = b.obj(name, None, loc=tuple(loc), rot=(0, 0, yaw))
        self.root = root
        self.j = {}
        shoe = shoe or M("black")

        b.obj(name + "_torso", G.box(0.44, 0.26, 0.62), top, loc=(0, 0, 1.24), parent=root, bevel=0.03)
        b.obj(name + "_neck", G.cylinder(0.055, 0.2, 10, z0=0.0), skin, loc=(0, 0, 1.5), parent=root,
              smooth=True)
        b.obj(name + "_head", G.sphere(0.13, 16, 10), skin, loc=(0, 0, 1.72), parent=root, smooth=True)
        b.obj(name + "_nose", G.sphere(0.022, 8, 5), skin, loc=(0, -0.135, 1.7), parent=root, smooth=True)
        if apron is not None:
            b.obj(name + "_apron", G.box(0.36, 0.02, 0.5), apron, loc=(0, -0.14, 1.05), parent=root)
        if vest is not None:
            b.obj(name + "_vest", G.box(0.47, 0.28, 0.5), vest, loc=(0, 0, 1.3), parent=root)
        if visor is not None:
            b.obj(name + "_visor", G.box(0.2, 0.03, 0.09), visor, loc=(0, -0.14, 1.73), parent=root)
        if hair and hat is None:
            self._coily_hair(name)
        self._hat(name, hat, hat_style)

        for side, sx in SIDE.items():
            sh = self._pivot(f"sh_{side}", (sx * 0.27, 0, 1.5), root, name)
            b.obj(f"{name}_ua_{side}", G.cylinder(0.065, UPPER, 10, z0=-UPPER), top, parent=sh, smooth=True)
            el = self._pivot(f"el_{side}", (0, 0, -UPPER), sh, name)
            b.obj(f"{name}_fa_{side}", G.cylinder(0.058, FORE, 10, z0=-FORE), top, parent=el, smooth=True)
            b.obj(f"{name}_hand_{side}", G.sphere(0.065 if gloves else 0.06, 10, 6), gloves or skin,
                  loc=(0, 0, -FORE - 0.02), parent=el, smooth=True)
            hp = self._pivot(f"hp_{side}", (sx * 0.12, 0, 0.95), root, name)
            b.obj(f"{name}_th_{side}", G.cylinder(0.085, 0.46, 10, z0=-0.46), bottom, parent=hp, smooth=True)
            kn = self._pivot(f"kn_{side}", (0, 0, -0.46), hp, name)
            b.obj(f"{name}_sh_{side}", G.cylinder(0.075, 0.42, 10, z0=-0.42), bottom, parent=kn, smooth=True)
            b.obj(f"{name}_ft_{side}", G.box(0.12, 0.27, 0.08), shoe, loc=(0, -0.06, -0.46), parent=kn)

        self.inv = Matrix.Translation(self.loc) @ Matrix.Rotation(yaw, 4, "Z")
        self.inv.invert()
        self.to_world_m = self.inv.inverted()

    def _coily_hair(self, name):
        """Short, tightly curled hair: a cluster of small spheres over the crown of the head."""
        n = 16
        for i in range(n):
            phi = 0.25 + 0.85 * math.sqrt((i + 0.5) / n)        # polar angle from the crown
            a = i * 2.39996                                       # golden angle around the head
            r = 0.125
            pos = (r * math.sin(phi) * math.cos(a), r * math.sin(phi) * math.sin(a),
                   1.72 + r * math.cos(phi))
            self.b.obj(f"{name}_curl{i}", G.sphere(0.047, 8, 5), M("hair_coily"), loc=pos,
                       parent=self.root, smooth=True)

    def _pivot(self, key_name, pos, parent, prefix):
        p = self.b.obj(f"{prefix}_{key_name}", None, loc=pos, parent=parent)
        self.j[key_name] = p
        return p

    def _hat(self, name, mat, style):
        b = self.b
        if style == "helmet":
            b.obj(name + "_helmet", G.sphere(0.155, 16, 10), mat, loc=(0, 0.01, 1.74), parent=self.root, smooth=True)
        elif style == "toque":
            b.obj(name + "_toque", G.cylinder(0.12, 0.2, 14, z0=1.85), mat, parent=self.root, smooth=True)
            b.obj(name + "_toque_top", G.sphere(0.14, 12, 8), mat, loc=(0, 0, 2.08), parent=self.root, smooth=True)
        elif style == "hardhat":
            b.obj(name + "_hardhat", G.sphere(0.15, 14, 8, sz=0.62), mat, loc=(0, 0, 1.8), parent=self.root,
                  smooth=True)
        elif style == "straw":
            b.obj(name + "_brim", G.cylinder(0.27, 0.02, 20, z0=1.84), mat, parent=self.root, smooth=True)
            b.obj(name + "_crown", G.cylinder(0.14, 0.14, 14, z0=1.84), mat, parent=self.root, smooth=True)
        elif style == "cap":
            b.obj(name + "_cap", G.sphere(0.14, 14, 8, sz=0.6), mat, loc=(0, 0, 1.8), parent=self.root, smooth=True)
            b.obj(name + "_peak", G.box(0.14, 0.12, 0.02), mat, loc=(0, -0.16, 1.78), parent=self.root)

    # --- posing -------------------------------------------------------------
    def pose(self, frame, **joints):
        """Key joint rotations. Values are (x, y, z) tuples or a single x angle."""
        for name, v in joints.items():
            e = tuple(v) if isinstance(v, (tuple, list)) else (v, 0.0, 0.0)
            key(self.j[name], frame, rotation_euler=e)

    def rest(self, frame):
        for side in SIDE:
            self.pose(frame, **{f"sh_{side}": (0.05, 0, 0), f"el_{side}": (0, 0, 0),
                                f"hp_{side}": (0, 0, 0), f"kn_{side}": (0, 0, 0)})

    def reach(self, frame, side, world_target):
        """Key the arm of `side` so the hand reaches `world_target`. Returns the hand's world position."""
        a, e = self._ik(side, world_target)
        self.pose(frame, **{f"sh_{side}": (a, 0, 0), f"el_{side}": (e, 0, 0)})
        return self.hand_world(side, a, e)

    def hand_world(self, side, a, e):
        sx = SIDE[side] * 0.27
        d1 = (0.0, math.sin(a), -math.cos(a))
        d2 = (0.0, math.sin(a + e), -math.cos(a + e))
        elbow = (sx, UPPER * d1[1], 1.5 + UPPER * d1[2])
        hand = (sx, elbow[1] + FORE * d2[1], elbow[2] + FORE * d2[2])
        return self.to_world_m @ Vector(hand)

    def _ik(self, side, world_target):
        tl = self.inv @ Vector(world_target)     # local space
        uy = tl.y
        uz = tl.z - 1.5
        d = math.hypot(uy, uz)
        d = min(max(d, 0.05), UPPER + FORE - 0.01)
        cos_g = (UPPER * UPPER + d * d - FORE * FORE) / (2 * UPPER * d)
        gamma = math.acos(max(-1.0, min(1.0, cos_g)))
        cos_t = (UPPER * UPPER + FORE * FORE - d * d) / (2 * UPPER * FORE)
        beta = math.pi - math.acos(max(-1.0, min(1.0, cos_t)))
        base = math.atan2(uy, -uz)
        best = None
        for sgn in (1.0, -1.0):          # two solutions; keep the one with the lower elbow
            a = base + sgn * gamma
            elbow_z = 1.5 + UPPER * (-math.cos(a))
            if best is None or elbow_z < best[0]:
                best = (elbow_z, (a, -beta))
        return best[1]

    def breathe(self, f0, f1, step=12, amount=0.012):
        base = self.loc
        f = f0
        up = True
        while f <= f1:
            key(self.root, f, location=(base.x, base.y, base.z + (amount if up else 0.0)))
            up = not up
            f += step


# ---------------------------------------------------------------------------
# Props
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


def hose(b, name, points, mat, radius, reveal=None):
    """Bezier hose through `points` (world coordinates). `reveal` = (f0, f1) to animate it growing."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 12
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
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
    return o


def torch(b, name, grip, tip, body_mat=None):
    """Hand torch: handle from the grip towards the tip, with a nozzle at the tip."""
    g, t = Vector(grip), Vector(tip)
    d = (t - g).normalized()
    handle_end = g + d * (t - g).length * 0.6
    b.segment(name + "_handle", tuple(g), tuple(handle_end), 0.024, body_mat or M("brass"))
    b.segment(name + "_nozzle", tuple(handle_end), tuple(t), 0.008, M("brass"))


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

def stage_intro(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(0.0, -7.6, 1.5), end=(0.0, -6.6, 1.6), target=(0.0, 0.0, 1.4), drop=0.0)
    b.world((0.015, 0.015, 0.02))
    b.floor(M("dark_steel"))
    b.light("KeyTop", "AREA", (0, -1.0, 6.0), (1.0, 0.95, 0.9), 900.0, size=4.0, target=(0, 0, 0))
    b.light("RimOrange", "AREA", (4.0, 3.0, 3.0), (1.0, 0.5, 0.15), 500.0, size=3.0, target=(0, 0, 1.2))

    # Wordmark rises from the floor
    cu = bpy.data.curves.new("Wordmark", "FONT")
    cu.body = "RhyolitePrime"
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.08
    cu.bevel_depth = 0.012
    cu.bevel_resolution = 2
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

    # Hose uncoils across the floor and forms an underline
    path = [(-4.8, -0.4, 0.25), (-3.2, -0.3, 0.95), (-1.2, -0.25, 1.02), (1.2, -0.25, 1.02),
            (3.2, -0.3, 0.95), (4.8, -0.4, 0.25)]
    hose(b, "HoseIntro", path, M("hose_orange"), 0.035, reveal=(f0 + 4, f0 + 60))


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
    plate = b.obj("SteelPlate", G.box(1.4, 0.4, 0.03), M("steel"), loc=(0.0, 0.0, 0.98), bevel=0.004)

    valve = gas_cylinder(b, "CylOrange", (-2.3, -0.9, 0.2), M("cyl_grey"), M("band_white"))
    trolley(b, "Trolley", (-2.3, -0.9, 0.0))

    welder = Human(b, "Welder", (0.0, 0.42, 0.0), 0.0, skin=M("skin_mid"), top=M("leather"),
                   bottom=M("leather"), shoe=M("black"), hat=M("black"), hat_style="helmet", visor=M("visor"),
                   apron=M("leather"), gloves=M("leather"))
    welder.breathe(f0, f1)
    welder.rest(f0)
    hand = welder.reach(f0, "r", (0.25, 0.05, 1.1))
    welder.reach(f0, "l", (-0.1, 0.05, 1.1))
    tip = Vector((0.2, 0.0, 1.03))
    torch(b, "CuttingTorch", tuple(hand), tuple(tip))
    hose(b, "HoseOrange", [valve, (-1.2, -0.7, 0.35), (-0.3, -0.4, 0.55), tuple(hand)],
         M("hose_orange"), 0.03, reveal=(f0, f0 + 20))

    sparks(b, M("spark"), lambda fr: (0.2, 0.0, 1.05), f0, f1, 60, random.Random(11), spread=1.3, lift=1.4)
    b.light("CutGlow", "POINT", (0.2, -0.1, 1.3), (1.0, 0.6, 0.25), 60.0, size=0.6)
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
    seam = b.obj("WeldBead", G.box(1.8, 0.05, 0.03, origin="left"), M("glow_orange"),
                 loc=(-0.9, 0.0, 1.2), scale=(0.01, 1, 1))
    key(seam, f0 + 6, scale=(0.01, 1, 1))
    key(seam, f1 - 20, scale=(1.0, 1, 1))

    red = gas_cylinder(b, "CylRed", (-1.95, -0.9, 0.2), M("cyl_red"), M("band_white"))
    blue = gas_cylinder(b, "CylBlue", (-1.5, -0.9, 0.2), M("cyl_blue"), M("band_white"))
    trolley(b, "CartA", (-1.72, -0.9, 0.0), width=0.9)

    welder = Human(b, "OxyWelder", (0.1, 0.42, 0.0), 0.0, skin=M("skin_deep"), top=M("leather"),
                   bottom=M("leather"), shoe=M("black"), hat=M("black"), hat_style="helmet", visor=M("visor"),
                   apron=M("leather"), gloves=M("leather"))
    welder.breathe(f0, f1)
    welder.rest(f0)
    hand = welder.reach(f0, "r", (0.25, 0.05, 1.22))
    welder.reach(f0, "l", (-0.05, 0.05, 1.22))
    tip = Vector((0.25, 0.0, 1.24))
    torch(b, "OxyTorch", tuple(hand), tuple(tip))
    oxy_flame = flame(b, "OxyFlame", tuple(tip), (0.25, -0.1, 1.22), M("glow_blue"), radius=0.03)
    flicker(oxy_flame, f0, f1, (1, 1, 1), 0.15, random.Random(3))
    b.light("FlameGlow", "POINT", (0.3, -0.1, 1.3), (0.45, 0.7, 1.0), 80.0, size=0.5)

    # Two hoses: red (fuel) from the acetylene valve, blue (oxygen) from the oxygen valve
    hose(b, "HoseRed", [red, (-1.2, -0.6, 0.25), (-0.4, -0.2, 0.5), tuple(hand)], M("hose_red"), 0.025,
         reveal=(f0, f0 + 20))
    hose(b, "HoseBlue", [blue, (-1.1, -0.6, 0.25), (-0.3, -0.2, 0.45), (0.05, -0.05, 0.95), tuple(hand)],
         M("hose_blue"), 0.025, reveal=(f0 + 4, f0 + 24))
    sparks(b, M("spark"), lambda fr: (0.25, 0.0, 1.22), f0, f1, 20, random.Random(5), spread=0.7, lift=0.8)
    b.light("BenchFill", "AREA", (0.0, -2.0, 3.0), (1.0, 0.92, 0.85), 300.0, size=3.0, target=(0, 0.5, 0.8))
    b.overlay(shot, title_size=0.13)


def stage_domestic(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(2.2, -3.4, 1.7), end=(1.8, -3.0, 1.7), target=(-0.4, 1.4, 1.0), lens=40)
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
    b.obj("Pot", G.cylinder(0.13, 0.14, 16), M("stainless"), loc=(-0.2, 1.35, stove_top + 0.02), smooth=True)
    b.obj("PotLid", G.cylinder(0.14, 0.02, 16), M("stainless"), loc=(-0.2, 1.35, stove_top + 0.16), smooth=True)

    valve = gas_cylinder(b, "CylKitchen", (-2.1, 1.75, 0.2), M("cyl_grey"), M("band_white"))
    trolley(b, "CylStand", (-2.1, 1.75, 0.0), width=0.5)
    inlet = (-0.6, 1.55, 1.0)
    b.obj("StoveInlet", G.cylinder(0.03, 0.12, 10), M("brass"), loc=(-0.46, 1.55, 1.0),
          rot=(0, -PI / 2, 0), smooth=True)
    hose(b, "HoseKitchen", [valve, (-1.85, 1.75, 1.0), (-1.1, 1.7, 1.0), inlet],
         M("hose_orange"), 0.03, reveal=(f0, f0 + 24))

    cook = Human(b, "Cook", (1.0, 2.25, 0.0), 0.0, skin=M("skin_light"), top=M("grey_shirt"),
                 bottom=M("navy"), apron=M("apron_red"))
    cook.breathe(f0, f1)
    cook.rest(f0)
    cook.reach(f0, "r", (0.9, 1.95, 1.05))
    cook.reach(f0, "l", (1.2, 1.95, 1.0))
    b.light("KitchenLight", "AREA", (0.0, -0.5, 3.0), (1.0, 0.92, 0.8), 500.0, size=3.0, target=(0, 1.2, 0.8))
    b.light("StoveGlow", "POINT", (-0.2, 1.4, 1.2), (0.45, 0.7, 1.0), 40.0, size=0.6)
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
    hose(b, "HoseRange", [wall_outlet, (-2.2, 1.2, 0.12), (-1.8, 1.25, 0.12), (-1.62, 1.9, 0.3)],
         M("hose_orange"), 0.03, reveal=(f0, f0 + 24))

    # Pass counter between the chef and the camera
    b.obj("PassTop", G.box(2.0, 0.6, 0.06), M("steel"), loc=(0.6, -0.15, 1.0), bevel=0.01)
    for x in (-0.3, 1.5):
        for y in (-0.4, 0.1):
            b.obj("PassLeg", G.box(0.06, 0.06, 0.95), M("dark_steel"), loc=(x, y, 0.47))
    chef = Human(b, "Chef", (0.6, 0.3, 0.0), 0.0, skin=M("skin_light"), top=M("chef_white"),
                 bottom=M("navy"), apron=M("black"), hat=M("chef_white"), hat_style="toque")
    chef.breathe(f0, f1)
    chef.rest(f0)
    chef.reach(f0, "r", (0.3, -0.1, 1.07))
    chef.reach(f0, "l", (0.9, -0.1, 1.07))
    b.light("PassLight", "AREA", (0.0, -1.0, 3.2), (1.0, 0.95, 0.85), 450.0, size=3.0, target=(0, 1.5, 0.9))
    b.overlay(shot, title_size=0.13)


def stage_outdoor(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(-0.6, -7.2, 2.0), end=(-0.1, -6.4, 2.0), target=(0.0, 1.0, 1.1), lens=35)
    b.world((0.45, 0.62, 0.9))
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

    # Propane cylinder and red hose to the grill
    valve = gas_cylinder(b, "Propane", (-1.3, 0.6, 0.0), M("cyl_grey"), M("band_white"), h=0.8, r=0.14)
    hose(b, "HoseGrill", [valve, (-0.9, 0.2, 0.15), (-0.45, 0.1, 0.2), (-0.08, 0.6, 0.6)],
         M("hose_red"), 0.025, reveal=(f0, f0 + 24))
    # Small generator and camp stove
    b.obj("Generator", G.box(0.7, 0.45, 0.5), M("dark_steel"), loc=(2.6, -0.4, 0.25), bevel=0.02)
    b.obj("GenHandle", G.box(0.5, 0.04, 0.04), M("black"), loc=(2.6, -0.65, 0.55))

    camper_a = Human(b, "CamperA", (-0.6, -0.2, 0.0), 0.0, skin=M("skin_mid"), top=M("hi_vis"),
                     bottom=M("navy"))
    camper_a.breathe(f0, f1)
    camper_a.rest(f0)
    camper_a.reach(f0, "r", (-0.3, -0.55, 1.15))
    camper_a.reach(f0, "l", (-0.75, -0.55, 1.1))
    camper_b = Human(b, "CamperB", (1.5, -0.2, 0.0), 0.0, skin=M("skin_deep"), top=M("overalls"),
                     bottom=M("navy"), hat=M("straw"), hat_style="straw")
    camper_b.breathe(f0, f1)
    camper_b.rest(f0)
    camper_b.reach(f0, "r", (1.2, -0.55, 1.1))
    camper_b.reach(f0, "l", (1.5, -0.55, 1.05))

    b.light("SunsetFill", "AREA", (-3.0, -3.0, 4.0), (1.0, 0.8, 0.6), 400.0, size=5.0, target=(0, 1, 1))
    b.overlay(shot, title_size=0.13)


def stage_agriculture(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(-0.6, -6.0, 1.8), end=(-0.1, -5.2, 1.8), target=(0.2, 0.9, 1.2), lens=38)
    b.world((0.2, 0.2, 0.18))
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

    farmer = Human(b, "Farmer", (1.2, -0.6, 0.0), 0.0, skin=M("skin_deep"), top=M("overalls"),
                   bottom=M("overalls"), hat=M("straw"), hat_style="straw", gloves=M("leather"))
    farmer.breathe(f0, f1)
    farmer.rest(f0)
    farmer.reach(f0, "r", (0.95, -0.5, 1.1))
    farmer.reach(f0, "l", (1.35, -0.5, 1.1))
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
    rng = random.Random(90)
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

    worker = Human(b, "Worker", (0.6, 0.88, 0.0), 0.0, skin=M("skin_light"), top=M("grey_shirt"),
                   bottom=M("navy"), hat=M("hardhat"), hat_style="hardhat", vest=M("hi_vis"),
                   gloves=M("leather"))
    worker.breathe(f0, f1)
    worker.rest(f0)
    hand = worker.reach(f0, "r", (0.4, 0.5, 1.04))
    worker.reach(f0, "l", (0.8, 0.5, 1.04))
    tool_tip = hand + (Vector((0.4, 0.3, 1.0)) - hand).normalized() * 0.4
    torch(b, "AirTool", tuple(hand), tuple(tool_tip), body_mat=M("steel"))
    hose(b, "HoseAir", [outlet, (-0.7, 1.5, 1.6), (-0.1, 0.5, 1.7), tuple(hand)], M("hose_blue"), 0.025,
         reveal=(f0, f0 + 24))
    b.light("LineLight", "AREA", (0.0, -1.5, 3.5), (0.95, 0.95, 1.0), 500.0, size=4.0, target=(0, 0.8, 0.8))
    b.overlay(shot, title_size=0.13)


def stage_outro(b, shot):
    f0, f1 = b.f0, b.f1
    b.camera(start=(0.0, -7.2, 2.0), end=(0.0, -6.4, 2.0), target=(0.0, 0.0, 1.9), drop=0.0)
    b.world((0.015, 0.015, 0.02))
    b.floor(M("dark_steel"))
    b.light("KeyTop", "AREA", (0, -1.0, 6.0), (1.0, 0.95, 0.9), 800.0, size=4.0, target=(0, 0, 0))
    # The hose from the intro loops into a circle
    pts = []
    for i in range(8):
        a = 2 * PI * i / 8
        pts.append((0.0 + 0.85 * math.cos(a), 0.0, 2.05 + 0.85 * math.sin(a)))
    ring = hose(b, "HoseLoop", pts, M("hose_orange"), 0.035, reveal=(f0, f0 + 36))
    ring.data.splines[0].use_cyclic_u = True
    # Small wordmark above the loop
    cu = bpy.data.curves.new("OutroWordmark", "FONT")
    cu.body = "RhyolitePrime"
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.materials.append(M("wordmark_outro"))
    cu.size = 0.35
    wm = bpy.data.objects.new("OutroWordmark", cu)
    wm.rotation_euler = (PI / 2, 0, 0)
    wm.location = (0, 0.0, 3.1)
    b.link(wm)
    key(wm, f0 + 30, scale=(0.01, 0.01, 0.01))
    key(wm, f0 + 50, scale=(1, 1, 1))
    b.overlay(shot, stagger=14, title_size=0.13)


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


def build_scene(scene):
    """Populate the current scene with all nine stages. Returns the number of stages built."""
    assert len(STAGE_BUILDERS) == len(S.SHOTS), "every shot needs a builder"
    # global lighting shared by all stages
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 2.6
    sun.color = (1.0, 0.95, 0.9)
    sun.angle = math.radians(3.0)
    sun_obj = bpy.data.objects.new("Sun", sun)
    sun_obj.rotation_euler = (math.radians(55), math.radians(15), math.radians(-35))
    scene.collection.objects.link(sun_obj)

    world = bpy.data.worlds.new("AdWorld")
    world.use_nodes = True
    scene.world = world

    b = Builder(scene)
    for i, (shot, fn) in enumerate(zip(S.SHOTS, STAGE_BUILDERS)):
        b.begin(i, shot)
        fn(b, shot)
        b.finish()
        print(f"[advert] stage {i + 1}/{len(S.SHOTS)} built: {shot['id']} ({len(b.objs)} objects)")

    scene.camera = bpy.data.objects[f"Cam01"]
    return len(S.SHOTS)
