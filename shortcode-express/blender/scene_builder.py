"""Builds the 40-second ShortCode Express ("Be Fluent") advert in Blender.

Seven 3D stages are laid out along the +X axis, spaced `STAGE_STEP` metres apart,
matching the 7 scenes in `shortcode_express_ad.md` and `shots.py`:
  1. 0:00-0:04 (4s):  A dial connects a customer (Shop USSD dial *714*14#)
  2. 0:04-0:09 (5s):  The engineering bottleneck (Tangled if-else branches)
  3. 0:09-0:13 (4s):  The reveal (ShortCode Express / Sapo DSL Engine)
  4. 0:13-0:21 (8s):  From short code to working flow (Get/Port code -> Drag. Drop. Connect.)
  5. 0:21-0:29 (8s):  Connect the services behind the menu (Plugin marketplace + Your Plugin)
  6. 0:29-0:35 (6s):  Engineering control (Simulate · Validate · Deploy · Track · Roll back)
  7. 0:35-0:40 (5s):  The customer outcome and brand close (Shop payment success + CTA)
"""

import math
import os

import bpy
from mathutils import Euler, Vector

import geometry as G
import rig_characters as RC
import shots as S

STAGE_STEP = 28.0
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
SCREENSHOT_DIR = os.path.abspath(os.path.join(HERE, ".."))


# ---------------------------------------------------------------------------
# Materials & Image Texture Helpers
# ---------------------------------------------------------------------------

def _principled(name, color, metallic=0.0, roughness=0.45, emission=None, emission_strength=0.0,
                coat=0.0, transmission=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    if "Transmission Weight" in bsdf.inputs and transmission > 0:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        if hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"
    if emission is not None and emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def _image_material(name, img_path, emission_strength=0.78, roughness=0.18):
    """Create a crisp unlit screen material textured with a real UI screenshot PNG.

    Using an Emission shader (as in `advert/blender/scene_builder.py`'s `photo_card`) keeps
    white UI backgrounds from being blown out by studio area lights while preserving exact
    brand colours under AgX tone mapping.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = emission_strength
    if os.path.isfile(img_path):
        img = bpy.data.images.load(img_path, check_existing=True)
        try:
            img.pack()
        except Exception:
            pass
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.extension = "CLIP"
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = (0.10, 0.11, 0.15, 1.0)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def build_palette():
    p = {
        # ShortCode Express brand colors (from actual screenshots)
        "sce_plum": _principled("sce_plum", (0.42, 0.01, 0.25), roughness=0.32, coat=0.35,
                                emission=(0.42, 0.01, 0.25), emission_strength=0.35),
        "sce_plum_glow": _principled("sce_plum_glow", (0.68, 0.06, 0.42), roughness=0.22,
                                     emission=(0.75, 0.08, 0.46), emission_strength=1.8),
        "sce_cyan": _principled("sce_cyan", (0.01, 0.45, 0.72), roughness=0.28, coat=0.3,
                                emission=(0.02, 0.48, 0.78), emission_strength=0.40),
        "sce_cyan_glow": _principled("sce_cyan_glow", (0.06, 0.64, 0.92), roughness=0.22,
                                     emission=(0.08, 0.70, 0.96), emission_strength=1.8),
        "sce_sidebar": _principled("sce_sidebar", (0.065, 0.070, 0.090), roughness=0.45),
        "sce_canvas": _principled("sce_canvas", (0.88, 0.90, 0.94), roughness=0.45),
        "node_card": _principled("node_card", (0.92, 0.93, 0.96), roughness=0.35, coat=0.20),
        "node_amber": _principled("node_amber", (0.78, 0.40, 0.02), roughness=0.32,
                                  emission=(0.85, 0.45, 0.04), emission_strength=0.55),
        "node_green": _principled("node_green", (0.06, 0.56, 0.24), roughness=0.32,
                                  emission=(0.08, 0.65, 0.28), emission_strength=0.65),
        "node_red": _principled("node_red", (0.82, 0.09, 0.24), roughness=0.32,
                                emission=(0.88, 0.12, 0.28), emission_strength=1.1),

        # Architectural & studio materials
        "floor_concrete": _principled("floor_concrete", (0.20, 0.22, 0.25), roughness=0.55),
        "floor_tile": _principled("floor_tile", (0.68, 0.71, 0.76), roughness=0.35, coat=0.20),
        "floor_shop": _principled("floor_shop", (0.44, 0.35, 0.26), roughness=0.48),
        "floor_dark": _principled("floor_dark", (0.08, 0.09, 0.12), roughness=0.50),
        "wall_warm": _principled("wall_warm", (0.76, 0.69, 0.58), roughness=0.70),
        "wall_slate": _principled("wall_slate", (0.09, 0.11, 0.15), roughness=0.65),
        "wall_cream": _principled("wall_cream", (0.72, 0.75, 0.81), roughness=0.65),
        "wood_warm": _principled("wood_warm", (0.42, 0.25, 0.12), roughness=0.45),
        "wood_dark": _principled("wood_dark", (0.16, 0.10, 0.07), roughness=0.42),
        "desk_modern": _principled("desk_modern", (0.14, 0.15, 0.19), roughness=0.35, metallic=0.15),

        # Metals, devices & props
        "steel": _principled("steel", (0.68, 0.71, 0.75), metallic=0.88, roughness=0.26),
        "dark_steel": _principled("dark_steel", (0.12, 0.13, 0.16), metallic=0.80, roughness=0.32),
        "brass": _principled("brass", (0.85, 0.64, 0.20), metallic=0.92, roughness=0.22),
        "rubber_black": _principled("rubber_black", (0.05, 0.05, 0.06), roughness=0.68),
        "phone_body": _principled("phone_body", (0.10, 0.11, 0.14), metallic=0.25, roughness=0.35, coat=0.3),
        "phone_key": _principled("phone_key", (0.20, 0.22, 0.26), roughness=0.35),
        "phone_screen_bg": _principled("phone_screen_bg", (0.04, 0.12, 0.10), roughness=0.20,
                                       emission=(0.05, 0.18, 0.14), emission_strength=0.55),
        "phone_screen_ok": _principled("phone_screen_ok", (0.03, 0.18, 0.09), roughness=0.20,
                                       emission=(0.05, 0.35, 0.16), emission_strength=0.75),
        "code_screen_bg": _principled("code_screen_bg", (0.04, 0.05, 0.08), roughness=0.22,
                                      emission=(0.04, 0.05, 0.08), emission_strength=0.45),
        "glass": _principled("glass", (0.85, 0.93, 0.98), roughness=0.06, transmission=0.82, alpha=0.32),

        # Text & UI badges (crisp non-blooming emission)
        "text_gold": _principled("text_gold", (1.0, 0.78, 0.18), metallic=0.35, roughness=0.25,
                                 emission=(1.0, 0.76, 0.16), emission_strength=1.15),
        "text_white": _principled("text_white", (0.98, 0.98, 1.0), roughness=0.25,
                                  emission=(0.98, 0.98, 1.0), emission_strength=1.05),
        "text_dark": _principled("text_dark", (0.05, 0.06, 0.08), roughness=0.35),
        "banner_bg": _principled("banner_bg", (0.04, 0.05, 0.08), roughness=0.45,
                                 emission=(0.03, 0.04, 0.06), emission_strength=0.25),
        "ok_green": _principled("ok_green", (0.10, 0.85, 0.34), roughness=0.25,
                                emission=(0.12, 0.88, 0.36), emission_strength=1.6),
        "badge_green_bg": _principled("badge_green_bg", (0.03, 0.22, 0.10), roughness=0.3,
                                      emission=(0.04, 0.28, 0.12), emission_strength=0.75),

        # Authentic rich African skin tones, facial features & wardrobe
        "skin_deep": _principled("skin_deep", (0.13, 0.07, 0.04), roughness=0.46),
        "skin_warm": _principled("skin_warm", (0.19, 0.10, 0.06), roughness=0.44),
        "skin_rich": _principled("skin_rich", (0.10, 0.05, 0.03), roughness=0.48),
        "hair_black": _principled("hair_black", (0.03, 0.025, 0.02), roughness=0.65),
        "eye_white": _principled("eye_white", (0.98, 0.98, 0.99), roughness=0.14,
                                 emission=(0.98, 0.98, 1.0), emission_strength=0.55),
        "eye_dark": _principled("eye_dark", (0.02, 0.015, 0.01), roughness=0.08, coat=0.8),
        "eye_glint": _principled("eye_glint", (1.0, 1.0, 1.0), roughness=0.05,
                                 emission=(1.0, 1.0, 1.0), emission_strength=4.0),
        "shirt_plum": _principled("shirt_plum", (0.48, 0.04, 0.28), roughness=0.62),
        "shirt_teal": _principled("shirt_teal", (0.08, 0.42, 0.54), roughness=0.60),
        "shirt_gold": _principled("shirt_gold", (0.84, 0.56, 0.14), roughness=0.62),
        "shirt_indigo": _principled("shirt_indigo", (0.16, 0.22, 0.48), roughness=0.62),
        "denim": _principled("denim", (0.11, 0.17, 0.28), roughness=0.72),
    }

    # Real product screenshot materials
    p["screen_onboarding"] = _image_material(
        "screen_onboarding",
        os.path.join(SCREENSHOT_DIR, "onboarding-acquiring-porting-buy_code.png"),
        emission_strength=0.72,
    )
    p["screen_flow_builder"] = _image_material(
        "screen_flow_builder",
        os.path.join(SCREENSHOT_DIR, "flow-builder.png"),
        emission_strength=0.72,
    )
    p["screen_dashboard"] = _image_material(
        "screen_dashboard",
        os.path.join(SCREENSHOT_DIR, "dashboard.png"),
        emission_strength=0.72,
    )
    return p


# ---------------------------------------------------------------------------
# Scene Builder Helper
# ---------------------------------------------------------------------------

class Builder:
    def __init__(self, scene, palette):
        self.scene = scene
        self.col = scene.collection
        self.p = palette
        self.stage_objs = []
        self.f0 = 1
        self.f1 = S.total_frames()
        self.font_bold = bpy.data.fonts.load(FONT_BOLD) if os.path.exists(FONT_BOLD) else None
        self.font_reg = bpy.data.fonts.load(FONT_REG) if os.path.exists(FONT_REG) else None

    def begin_stage(self, idx):
        shot = S.SHOTS[idx]
        self.f0, self.f1 = S.stage_frames(idx)
        self.col = bpy.data.collections.new(f"Stage{idx + 1:02d}_{shot['id']}")
        self.scene.collection.children.link(self.col)
        self.stage_objs = []

    def finish_stage(self):
        f0, f1 = self.f0, self.f1
        total_f = S.total_frames()
        for o in self.stage_objs:
            if f0 > 1:
                o.hide_viewport = True
                o.hide_render = True
                o.keyframe_insert(data_path="hide_viewport", frame=1)
                o.keyframe_insert(data_path="hide_render", frame=1)
            o.hide_viewport = False
            o.hide_render = False
            o.keyframe_insert(data_path="hide_viewport", frame=f0)
            o.keyframe_insert(data_path="hide_render", frame=f0)
            if f1 < total_f:
                o.hide_viewport = True
                o.hide_render = True
                o.keyframe_insert(data_path="hide_viewport", frame=f1 + 1)
                o.keyframe_insert(data_path="hide_render", frame=f1 + 1)

    def link(self, obj):
        self.col.objects.link(obj)
        self.stage_objs.append(obj)
        return obj

    def obj(self, name, geom, mat, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
            parent=None, smooth=False):
        verts, faces = geom
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.update()
        if smooth:
            for poly in me.polygons:
                poly.use_smooth = True
        if mat is not None:
            me.materials.append(self.p[mat] if isinstance(mat, str) else mat)
        o = bpy.data.objects.new(name, me)
        o.location = loc
        o.rotation_euler = rot
        o.scale = scale
        if parent is not None:
            o.parent = parent
        return self.link(o)

    def screen_panel(self, name, width, height, depth, screen_mat, frame_mat="sce_sidebar",
                     loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), parent=None, bezel=0.05):
        """Build a 3D monitor/display card with a UV-mapped front screenshot face."""
        frame = self.obj(
            f"{name}_frame",
            G.box(width + bezel * 2, height + bezel * 2, depth),
            frame_mat,
            loc=loc,
            rot=rot,
            parent=parent,
        )
        hx, hy = width / 2.0, height / 2.0
        z_front = depth / 2.0 + 0.004
        verts = [(-hx, -hy, z_front), (hx, -hy, z_front), (hx, hy, z_front), (-hx, hy, z_front)]
        faces = [(0, 1, 2, 3)]
        me = bpy.data.meshes.new(f"{name}_face")
        me.from_pydata(verts, [], faces)
        me.update()
        uv_layer = me.uv_layers.new(name="UVMap")
        uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        for loop_idx, uv in enumerate(uvs):
            uv_layer.data[loop_idx].uv = uv
        me.materials.append(self.p[screen_mat] if isinstance(screen_mat, str) else screen_mat)
        face_obj = bpy.data.objects.new(f"{name}_face", me)
        face_obj.parent = frame
        self.link(face_obj)
        return frame

    def curve_tube(self, name, points, radius, mat, loc=(0, 0, 0), bevel_res=5, parent=None, poly=False):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = radius
        cu.bevel_resolution = bevel_res
        cu.resolution_u = 16
        cu.use_fill_caps = True
        if poly:
            sp = cu.splines.new("POLY")
            sp.points.add(len(points) - 1)
            for idx, pt in enumerate(points):
                sp.points[idx].co = (*pt, 1.0)
        else:
            sp = cu.splines.new("BEZIER")
            sp.bezier_points.add(len(points) - 1)
            for idx, pt in enumerate(points):
                bp = sp.bezier_points[idx]
                bp.co = pt
                bp.handle_left_type = "AUTO"
                bp.handle_right_type = "AUTO"
        cu.materials.append(self.p[mat] if isinstance(mat, str) else mat)
        o = bpy.data.objects.new(name, cu)
        o.location = loc
        if parent is not None:
            o.parent = parent
        return self.link(o)

    def text3d(self, name, body, size, mat, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0),
               extrude=0.015, align="CENTER", bold=True, parent=None):
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = body
        cu.size = size
        cu.extrude = extrude
        cu.bevel_depth = 0.002
        cu.align_x = align
        cu.align_y = "CENTER"
        font = self.font_bold if bold else self.font_reg
        if font is not None:
            cu.font = font
        cu.materials.append(self.p[mat] if isinstance(mat, str) else mat)
        o = bpy.data.objects.new(name, cu)
        o.location = loc
        o.rotation_euler = rot
        if parent is not None:
            o.parent = parent
        return self.link(o)


def key_linear(obj, path, frame, value):
    setattr(obj, path, value)
    obj.keyframe_insert(data_path=path, frame=frame)


def pop_in(obj, f_start, duration=10, target_scale=(1.0, 1.0, 1.0)):
    obj.scale = (0.001, 0.001, 0.001)
    obj.keyframe_insert("scale", frame=max(1, f_start - 1))
    obj.scale = tuple(v * 1.08 for v in target_scale)
    obj.keyframe_insert("scale", frame=f_start + int(duration * 0.65))
    obj.scale = target_scale
    obj.keyframe_insert("scale", frame=f_start + duration)


def stage_x(idx):
    return idx * STAGE_STEP


def stage_frames(idx):
    return S.stage_frames(idx)


def focus_camera(b, idx, start_loc, end_loc, start_target, end_target, lens=35.0):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    s_loc = (cx + start_loc[0], start_loc[1], start_loc[2])
    e_loc = (cx + end_loc[0], end_loc[1], end_loc[2])
    s_tgt = (cx + start_target[0], start_target[1], start_target[2])
    e_tgt = (cx + end_target[0], end_target[1], end_target[2])

    tgt = bpy.data.objects.new(f"CamTarget_{idx:02d}", None)
    b.link(tgt)
    key_linear(tgt, "location", f0, s_tgt)
    key_linear(tgt, "location", f1, e_tgt)

    cam_data = bpy.data.cameras.new(f"Cam_{idx:02d}")
    cam_data.lens = lens
    cam_data.clip_start = 0.05
    cam_data.clip_end = 200.0
    cam = bpy.data.objects.new(f"Cam_{idx:02d}", cam_data)
    b.link(cam)
    key_linear(cam, "location", f0, s_loc)
    key_linear(cam, "location", f1, e_loc)

    con = cam.constraints.new(type="TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    marker = b.scene.timeline_markers.new(name=f"shot_{idx:02d}", frame=f0)
    marker.camera = cam
    if idx == 0:
        b.scene.camera = cam
    return cam


def stage_room(b, idx, floor_mat, wall_mat, accent_mat="sce_plum"):
    cx = stage_x(idx)
    b.obj(f"s{idx}_floor", G.box(16.0, 12.0, 0.2), floor_mat, loc=(cx, 0, -0.1))
    b.obj(f"s{idx}_wall_back", G.box(16.0, 0.25, 7.0), wall_mat, loc=(cx, 4.5, 3.5))
    b.obj(f"s{idx}_wall_left", G.box(0.25, 12.0, 7.0), wall_mat, loc=(cx - 8.0, 0, 3.5))
    b.obj(f"s{idx}_wall_right", G.box(0.25, 12.0, 7.0), wall_mat, loc=(cx + 8.0, 0, 3.5))
    b.obj(f"s{idx}_skirting", G.box(15.8, 0.08, 0.18), accent_mat, loc=(cx, 4.35, 0.09))
    b.obj(f"s{idx}_header_bar", G.box(15.8, 0.08, 0.14), accent_mat, loc=(cx, 4.35, 5.15))


def stage_banners(b, idx, persist_end=False):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    shot = S.SHOTS[idx]

    root = bpy.data.objects.new(f"s{idx}_banner_root", None)
    root.location = (cx + 0.10, 0.85, 3.22)
    b.link(root)

    b.obj(f"s{idx}_banner_card", G.box(5.9, 0.08, 0.90), "banner_bg", loc=(0, 0, 0), parent=root)
    b.obj(f"s{idx}_banner_bar_l", G.box(0.11, 0.10, 0.90), "sce_plum_glow", loc=(-2.90, -0.02, 0), parent=root)
    b.obj(f"s{idx}_banner_bar_r", G.box(0.11, 0.10, 0.90), "sce_cyan_glow", loc=(2.90, -0.02, 0), parent=root)
    b.obj(f"s{idx}_banner_rule", G.box(5.5, 0.10, 0.022), "text_gold", loc=(0, -0.02, -0.20), parent=root)

    b.text3d(f"s{idx}_label", S.display_label(shot["label"]), 0.135, "text_gold",
             loc=(-2.72, -0.06, 0.29), align="LEFT", parent=root)
    lines = shot["title"].split("\n")
    if len(lines) == 1:
        b.text3d(f"s{idx}_title_0", lines[0], 0.205, "text_white",
                 loc=(-2.72, -0.06, 0.03), align="LEFT", parent=root)
    else:
        b.text3d(f"s{idx}_title_0", lines[0], 0.175, "text_white",
                 loc=(-2.72, -0.06, 0.09), align="LEFT", parent=root)
        b.text3d(f"s{idx}_title_1", lines[1], 0.155, "text_gold",
                 loc=(-2.72, -0.06, -0.09), align="LEFT", parent=root)
    b.text3d(f"s{idx}_spec", shot["spec"], 0.115, "text_gold",
             loc=(-2.72, -0.06, -0.33), align="LEFT", bold=False, parent=root)

    key_linear(root, "scale", f0, (0.01, 0.01, 0.01))
    key_linear(root, "scale", f0 + 10, (1.03, 1.03, 1.03))
    key_linear(root, "scale", f0 + 15, (1.0, 1.0, 1.0))
    if persist_end:
        key_linear(root, "scale", f1, (1.0, 1.0, 1.0))
    else:
        key_linear(root, "scale", f1 - 8, (1.0, 1.0, 1.0))
        key_linear(root, "scale", f1, (0.01, 0.01, 0.01))


def human(b, name, loc, yaw=0.0, shirt="shirt_plum", trousers="denim", skin="skin_deep",
          apron=None, hair=True, kind="jack", f0=1, f1=96):
    p = b.p
    mats = {
        "skin": p[skin],
        "torso": p[shirt],
        "sleeves": p[shirt],
        "trousers": p[trousers],
        "shoes": p["rubber_black"],
        "hands": p[skin],
        "apron": p[apron] if apron else p[shirt],
        "hair": p["hair_black"],
        "eye_white": p["eye_white"],
        "eye_dark": p["eye_dark"],
        "eye_glint": p["eye_glint"],
    }
    person = RC.Person(b, name, kind, loc, yaw, mats, f0, hair=hair)
    person.breathe(f0, f1)
    return person


# ---------------------------------------------------------------------------
# Reusable 3D Props: Feature Phone, Flow Node Card, Workstation
# ---------------------------------------------------------------------------

def build_feature_phone(b, name, loc, rot=(math.pi / 2, 0, 0), scale=1.0,
                        lines=("Welcome", "1. Pay merchant", "2. Check balance"),
                        screen_mat="phone_screen_bg", parent=None):
    """Build a 3D classic feature phone with physical keypad, call/end buttons, and USSD text."""
    root = b.obj(
        f"{name}_body",
        G.box(0.56 * scale, 1.08 * scale, 0.09 * scale),
        "phone_body",
        loc=loc,
        rot=rot,
        parent=parent,
    )
    # Screen bezel + illuminated LCD
    b.obj(f"{name}_bezel", G.box(0.46 * scale, 0.42 * scale, 0.02 * scale), "sce_sidebar",
          loc=(0, 0.24 * scale, 0.045 * scale), parent=root)
    b.obj(f"{name}_lcd", G.box(0.42 * scale, 0.36 * scale, 0.022 * scale), screen_mat,
          loc=(0, 0.24 * scale, 0.048 * scale), parent=root)
    for idx, line in enumerate(lines):
        b.text3d(
            f"{name}_line_{idx}",
            line,
            0.052 * scale,
            "text_white" if idx > 0 else "text_gold",
            loc=(-0.19 * scale, (0.34 - idx * 0.095) * scale, 0.064 * scale),
            rot=(0, 0, 0),
            extrude=0.004 * scale,
            align="LEFT",
            bold=(idx == 0),
            parent=root,
        )
    # Call (green) and End (red) buttons + 3x4 keypad grid
    b.obj(f"{name}_btn_call", G.box(0.13 * scale, 0.06 * scale, 0.025 * scale), "node_green",
          loc=(-0.14 * scale, -0.01 * scale, 0.048 * scale), parent=root)
    b.obj(f"{name}_btn_nav", G.box(0.12 * scale, 0.07 * scale, 0.028 * scale), "steel",
          loc=(0.0, -0.01 * scale, 0.048 * scale), parent=root)
    b.obj(f"{name}_btn_end", G.box(0.13 * scale, 0.06 * scale, 0.025 * scale), "node_red",
          loc=(0.14 * scale, -0.01 * scale, 0.048 * scale), parent=root)
    for r_idx in range(4):
        for c_idx in range(3):
            kx = (-0.14 + c_idx * 0.14) * scale
            ky = (-0.12 - r_idx * 0.095) * scale
            b.obj(f"{name}_key_{r_idx}_{c_idx}", G.box(0.11 * scale, 0.068 * scale, 0.024 * scale),
                  "phone_key", loc=(kx, ky, 0.048 * scale), parent=root)
    return root


def build_flow_node_card(b, name, badge_text, title_text, sub_text, header_mat="sce_plum",
                         loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), width=1.18, height=0.56):
    """Build a 3D Sapo DSL flow node card matching the nodes in `flow-builder.png`."""
    card = b.obj(f"{name}_card", G.box(width, height, 0.05), "node_card", loc=loc, rot=rot)
    b.obj(f"{name}_hdr", G.box(width, 0.15, 0.056), header_mat,
          loc=(0, height / 2 - 0.075, 0.004), parent=card)
    b.obj(f"{name}_port_in", G.sphere(0.042, 14, 10), "sce_cyan_glow",
          loc=(-width / 2, 0.0, 0.02), parent=card)
    b.obj(f"{name}_port_out", G.sphere(0.042, 14, 10), "sce_plum_glow",
          loc=(width / 2, 0.0, 0.02), parent=card)
    b.text3d(f"{name}_badge", badge_text, 0.078, "text_white",
             loc=(-width / 2 + 0.08, height / 2 - 0.08, 0.035), rot=(0, 0, 0),
             extrude=0.006, align="LEFT", parent=card)
    b.text3d(f"{name}_title", title_text, 0.092, "text_dark",
             loc=(-width / 2 + 0.08, 0.01, 0.032), rot=(0, 0, 0),
             extrude=0.006, align="LEFT", parent=card)
    b.text3d(f"{name}_sub", sub_text, 0.068, "sce_plum",
             loc=(-width / 2 + 0.08, -0.15, 0.032), rot=(0, 0, 0),
             extrude=0.005, align="LEFT", bold=False, parent=card)
    return card


# ---------------------------------------------------------------------------
# Scene 1 (0:00-0:04): A dial connects a customer
# ---------------------------------------------------------------------------

def stage_01_dial_connects(b, idx=0):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    stage_room(b, idx, "floor_shop", "wall_warm", accent_mat="sce_plum")
    stage_banners(b, idx)

    # Neighborhood shop counter & shelves with merchant goods
    b.obj("s1_counter", G.box(2.5, 0.85, 0.96), "wood_warm", loc=(cx - 0.35, -0.15, 0.48))
    b.obj("s1_counter_top", G.box(2.6, 0.92, 0.06), "wood_dark", loc=(cx - 0.35, -0.15, 0.98))
    b.obj("s1_shelf_back", G.box(3.2, 0.38, 2.2), "wood_dark", loc=(cx - 0.8, 2.2, 1.1))
    for r_i, z_h in enumerate((0.65, 1.18, 1.70)):
        b.obj(f"s1_shelf_plank_{r_i}", G.box(3.0, 0.42, 0.05), "wood_warm", loc=(cx - 0.8, 2.15, z_h))
        for c_i, col_mat in enumerate(("sce_plum", "shirt_gold", "sce_cyan", "node_green")):
            b.obj(f"s1_item_{r_i}_{c_i}", G.cylinder(0.09, 0.24, 18), col_mat,
                  loc=(cx - 1.75 + c_i * 0.62, 2.05, z_h + 0.03))
    # Shop USSD payment sign on counter
    sign = b.obj("s1_pay_sign", G.box(0.55, 0.06, 0.38), "sce_plum", loc=(cx - 0.15, -0.25, 1.19))
    b.text3d("s1_sign_txt1", "DIAL *714*14#", 0.072, "text_gold",
             loc=(0, -0.035, 0.06), align="CENTER", parent=sign)
    b.text3d("s1_sign_txt2", "Pay Merchant", 0.062, "text_white",
             loc=(0, -0.035, -0.06), align="CENTER", bold=False, parent=sign)

    # Customer (left of counter) dialing basic phone & Merchant (behind counter)
    customer = human(b, "s1_customer", (cx - 1.55, -0.45, 0), yaw=-0.52,
                     shirt="shirt_gold", trousers="denim", skin="skin_warm",
                     kind="jill", f0=f0, f1=f1)
    merchant = human(b, "s1_merchant", (cx + 0.35, 0.55, 0), yaw=0.35,
                     shirt="shirt_teal", trousers="denim", skin="skin_deep",
                     apron="sce_plum", kind="jack", f0=f0, f1=f1)

    # Handheld basic feature phone in customer's left hand while right thumb dials
    hand_phone_pos = (cx - 1.18, -0.78, 1.18)
    customer.reach(f0, "l", (cx - 1.24, -0.76, 1.15), grip=0.8)
    customer.reach(f1, "l", (cx - 1.22, -0.76, 1.17), grip=0.8)
    build_feature_phone(
        b, "s1_hand_phone", hand_phone_pos,
        rot=(1.22, 0.0, -0.35), scale=0.36,
        lines=("*714*14#", "1. Pay merchant", "2. Check balance"),
    )
    customer.work_motion("r", [
        (f0, (cx - 1.15, -0.80, 1.14)),
        (f0 + 18, (cx - 1.12, -0.78, 1.17)),
        (f0 + 36, (cx - 1.16, -0.81, 1.15)),
        (f0 + 56, (cx - 1.13, -0.79, 1.18)),
        (f1, (cx - 1.15, -0.80, 1.16)),
    ], grip=0.45)

    # Merchant rests hand on counter and gives an expectant nod
    merchant.work_motion("r", [
        (f0, (cx - 0.05, -0.05, 1.03)),
        (f0 + 48, (cx - 0.12, -0.08, 1.06)),
        (f1, (cx - 0.08, -0.06, 1.04)),
    ], grip=0.5)
    merchant.nod(f0 + 48, amount=0.16)

    # Hero 3D Feature Phone Callout on the right so the keypad & USSD menu are crystal clear
    hero_phone = build_feature_phone(
        b, "s1_hero_phone", (cx + 1.85, -0.15, 1.55),
        rot=(math.pi / 2, 0.0, -0.18), scale=1.55,
        lines=("Welcome", "1. Pay merchant", "2. Check balance"),
    )
    pop_in(hero_phone, f0 + 16, duration=14)

    # Outgoing signal pulse rings & wave traveling from the phone
    for p_idx in range(3):
        ring_obj = b.obj(
            f"s1_pulse_ring_{p_idx}",
            G.torus(0.45 + p_idx * 0.25, 0.018, 32, 12),
            "sce_cyan_glow" if p_idx % 2 == 0 else "sce_plum_glow",
            loc=(cx + 1.85, -0.22, 1.85),
            rot=(math.pi / 2, 0, -0.18),
        )
        pf = f0 + 42 + p_idx * 10
        key_linear(ring_obj, "scale", f0, (0.01, 0.01, 0.01))
        key_linear(ring_obj, "scale", pf, (0.2, 0.2, 0.2))
        key_linear(ring_obj, "scale", pf + 28, (1.65, 1.65, 1.65))

    focus_camera(
        b, idx,
        start_loc=(-0.20, -5.25, 1.88),
        end_loc=(0.20, -4.95, 1.90),
        start_target=(0.15, 0.25, 1.82),
        end_target=(0.25, 0.25, 1.85),
        lens=29.0,
    )


# ---------------------------------------------------------------------------
# Scene 2 (0:04-0:09): The engineering bottleneck
# ---------------------------------------------------------------------------

def stage_02_engineering_bottleneck(b, idx=1):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    stage_room(b, idx, "floor_dark", "wall_slate", accent_mat="node_red")
    stage_banners(b, idx)

    # Ergonomic engineering workstation desk + dual monitors + keyboard + handwritten flow notes
    b.obj("s2_desk_top", G.box(3.4, 1.15, 0.07), "desk_modern", loc=(cx + 0.2, 0.15, 0.92))
    b.obj("s2_desk_leg_l", G.box(0.08, 0.95, 0.90), "dark_steel", loc=(cx - 1.35, 0.15, 0.45))
    b.obj("s2_desk_leg_r", G.box(0.08, 0.95, 0.90), "dark_steel", loc=(cx + 1.75, 0.15, 0.45))
    b.obj("s2_keyboard", G.box(0.52, 0.20, 0.03), "sce_sidebar", loc=(cx - 0.35, -0.18, 0.97))
    b.obj("s2_notes", G.box(0.36, 0.28, 0.015), "sce_canvas", loc=(cx + 0.32, -0.16, 0.96), rot=(0, 0, -0.22))

    # Main code monitor showing nested if-else blocks
    mon = b.obj("s2_monitor", G.box(2.35, 0.08, 1.25), "sce_sidebar", loc=(cx + 0.35, 0.48, 1.62))
    b.obj("s2_mon_stand", G.box(0.18, 0.22, 0.35), "dark_steel", loc=(cx + 0.35, 0.52, 0.98))
    b.obj("s2_mon_screen", G.box(2.22, 0.02, 1.12), "code_screen_bg", loc=(cx + 0.35, 0.43, 1.62))

    code_lines = [
        ("if (input == '1') {", 0.0, "text_gold"),
        ("  if (session.pin_ok) {", 0.18, "text_white"),
        ("    else if (err == 'TIMEOUT') {", 0.36, "node_amber"),
        ("      if (retry < 3) { else {", 0.54, "node_red"),
        ("        else if (menu == 'PAY_MOMO') {", 0.72, "node_red"),
        ("          // TODO: untangle 47 branches!", 0.88, "text_gold"),
    ]
    for l_idx, (txt, indent, col) in enumerate(code_lines):
        b.text3d(
            f"s2_code_{l_idx}", txt, 0.078, col,
            loc=(cx - 0.68 + indent, 0.40, 2.02 - l_idx * 0.155),
            rot=(math.pi / 2, 0, 0), extrude=0.006, align="LEFT",
        )

    # Tangled 3D conditional branch tubes crossing out of the monitor
    tangle_specs = [
        ([(-0.45, 0.35, 1.98), (0.15, -0.25, 2.12), (0.95, -0.15, 1.42), (1.65, -0.35, 1.95)], "node_red"),
        ([(-0.35, 0.35, 1.72), (0.35, -0.35, 1.32), (1.15, -0.20, 2.08), (1.80, -0.25, 1.38)], "node_amber"),
        ([(-0.20, 0.35, 1.45), (0.55, -0.30, 2.05), (1.05, -0.40, 1.28), (1.75, -0.18, 1.82)], "node_red"),
        ([(0.05, 0.35, 2.05), (0.65, -0.22, 1.42), (1.35, -0.35, 1.98), (1.90, -0.30, 1.50)], "sce_plum_glow"),
        ([(-0.50, 0.35, 1.32), (0.25, -0.18, 1.80), (0.85, -0.38, 1.52), (1.55, -0.22, 1.28)], "node_amber"),
    ]
    for t_idx, (pts, mat_name) in enumerate(tangle_specs):
        world_pts = [(cx + x, y, z) for (x, y, z) in pts]
        tube = b.curve_tube(f"s2_tangle_{t_idx}", world_pts, 0.022, mat_name)
        cu = tube.data
        cu.bevel_factor_end = 0.15
        cu.keyframe_insert("bevel_factor_end", frame=f0 + t_idx * 6)
        cu.bevel_factor_end = 1.0
        cu.keyframe_insert("bevel_factor_end", frame=f0 + 48 + t_idx * 8)

    # Floating warning labels around the tangle: 'New menu', 'API error', 'Another change'
    alerts = [
        ("New menu", (cx + 0.55, -0.38, 2.12), "node_amber", f0 + 28),
        ("API error", (cx + 1.45, -0.42, 1.76), "node_red", f0 + 46),
        ("Another change", (cx + 1.05, -0.38, 1.28), "sce_plum", f0 + 64),
    ]
    for a_idx, (label_txt, aloc, amat, af) in enumerate(alerts):
        card = b.obj(f"s2_alert_{a_idx}", G.box(0.82, 0.05, 0.24), amat, loc=aloc)
        b.text3d(f"s2_alert_txt_{a_idx}", label_txt, 0.088, "text_white",
                 loc=(0, -0.032, 0), align="CENTER", parent=card)
        pop_in(card, af, duration=10)

    # Engineer typing, then rubbing forehead in restrained frustration, then pausing over keyboard
    eng = human(b, "s2_engineer", (cx - 1.15, -0.55, 0), yaw=-0.42,
                shirt="shirt_indigo", trousers="denim", skin="skin_deep",
                kind="jack", f0=f0, f1=f1)
    eng.work_motion("l", [
        (f0, (cx - 0.52, -0.22, 1.02)),
        (f0 + 24, (cx - 0.46, -0.18, 1.04)),
        (f0 + 48, (cx - 0.52, -0.20, 1.02)),
        (f0 + 84, (cx - 0.50, -0.22, 1.06)),
        (f1, (cx - 0.50, -0.22, 1.06)),
    ], grip=0.55)
    eng.work_motion("r", [
        (f0, (cx - 0.22, -0.22, 1.02)),
        (f0 + 24, (cx - 0.18, -0.18, 1.04)),
        (f0 + 44, (cx - 0.24, -0.20, 1.02)),
        # Rubs forehead briefly in restrained frustration, then pauses over keyboard
        (f0 + 68, (cx - 1.02, -0.62, 1.56)),
        (f0 + 84, (cx - 1.04, -0.60, 1.55)),
        (f0 + 102, (cx - 0.22, -0.22, 1.06)),
        (f1, (cx - 0.22, -0.22, 1.06)),
    ], grip=0.45)

    focus_camera(
        b, idx,
        start_loc=(-0.25, -5.25, 1.88),
        end_loc=(0.15, -4.85, 1.88),
        start_target=(0.15, 0.25, 1.82),
        end_target=(0.25, 0.25, 1.84),
        lens=29.0,
    )


# ---------------------------------------------------------------------------
# Scene 3 (0:09-0:13): The reveal — Meet ShortCode Express (Sapo DSL Engine)
# ---------------------------------------------------------------------------

def stage_03_the_reveal(b, idx=2):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    stage_room(b, idx, "floor_tile", "wall_cream", accent_mat="sce_plum")
    stage_banners(b, idx)

    # Open, bright workstation with the actual Flow Builder interface (`flow-builder.png`)
    b.obj("s3_desk", G.box(3.8, 1.05, 0.06), "desk_modern", loc=(cx + 0.35, 0.35, 0.72))
    b.screen_panel(
        "s3_flow_screen", width=3.10, height=1.56, depth=0.06,
        screen_mat="screen_flow_builder", frame_mat="sce_sidebar",
        loc=(cx + 0.65, 0.68, 1.85),
    )

    # 3D Flow Nodes & clean glowing connectors untangling in the foreground
    n1 = build_flow_node_card(
        b, "s3_node_menu", "MENU", "Welcome menu", "1. Balance  2. Bundle",
        header_mat="sce_plum", loc=(cx - 0.55, -0.05, 1.02), width=1.08, height=0.48,
    )
    n2 = build_flow_node_card(
        b, "s3_node_cond", "CONDITION", "Confirmed?", "confirm == '1'",
        header_mat="node_amber", loc=(cx + 0.70, -0.05, 1.02), width=1.08, height=0.48,
    )
    n3 = build_flow_node_card(
        b, "s3_node_api", "HTTP API", "Charge via MoMo", "POST /api/momo/pay",
        header_mat="sce_cyan", loc=(cx + 1.95, -0.05, 1.02), width=1.08, height=0.48,
    )
    for n_idx, node_obj in enumerate((n1, n2, n3)):
        pop_in(node_obj, f0 + 8 + n_idx * 10, duration=12)

    for c_idx, (x0, x1) in enumerate(((-0.01, 0.16), (1.24, 1.41))):
        conn = b.curve_tube(
            f"s3_conn_{c_idx}",
            [(cx + x0, -0.08, 1.02), (cx + (x0 + x1) / 2, -0.14, 1.08), (cx + x1, -0.08, 1.02)],
            0.016, "sce_plum_glow" if c_idx == 0 else "sce_cyan_glow",
        )
        cu = conn.data
        cu.bevel_factor_end = 0.0
        cu.keyframe_insert("bevel_factor_end", frame=f0 + 18 + c_idx * 12)
        cu.bevel_factor_end = 1.0
        cu.keyframe_insert("bevel_factor_end", frame=f0 + 36 + c_idx * 12)

    # 3D Brand Badge on the left above the engineer: ShortCode Express — Powered by Sapo DSL Engine
    badge = b.obj("s3_brand_plaque", G.box(2.15, 0.07, 0.44), "sce_sidebar",
                  loc=(cx - 1.85, 0.20, 2.22))
    icon_box = b.obj("s3_brand_icon", G.box(0.32, 0.09, 0.32), "sce_plum",
                     loc=(-0.84, -0.02, 0.0), parent=badge)
    for b_i, bz in enumerate((0.08, 0.0, -0.08)):
        b.obj(f"s3_icon_bar_{b_i}", G.box(0.18, 0.02, 0.028), "text_white",
              loc=(0.0, -0.05, bz), parent=icon_box)
    b.text3d("s3_brand_title", "ShortCode Express", 0.145, "text_white",
             loc=(-0.60, -0.04, 0.05), align="LEFT", parent=badge)
    b.text3d("s3_brand_sub", "Powered by Sapo DSL Engine", 0.092, "text_gold",
             loc=(-0.60, -0.04, -0.10), align="LEFT", bold=False, parent=badge)
    pop_in(badge, f0 + 14, duration=14)

    # Engineer straightens posture and makes one purposeful mouse movement + smile
    eng = human(b, "s3_engineer", (cx - 1.65, -0.45, 0), yaw=-0.38,
                shirt="shirt_indigo", trousers="denim", skin="skin_deep",
                kind="jack", f0=f0, f1=f1)
    eng.work_motion("l", [
        (f0, (cx - 1.28, -0.62, 1.05)),
        (f0 + 36, (cx - 1.15, -0.66, 1.18)),
        (f1, (cx - 1.20, -0.64, 1.12)),
    ], grip=0.35)
    eng.thumbs_up(f0 + 36, f1, side="r")
    eng.smile(f0 + 38, b.p["text_white"])
    eng.check(f0 + 48, b.p["ok_green"], badge_mat=b.p["badge_green_bg"], rim_mat=b.p["text_white"])

    focus_camera(
        b, idx,
        start_loc=(0.05, -5.25, 1.88),
        end_loc=(-0.05, -5.45, 1.90),
        start_target=(0.10, 0.25, 1.82),
        end_target=(0.15, 0.25, 1.84),
        lens=28.0,
    )


# ---------------------------------------------------------------------------
# Scene 4 (0:13-0:21): From short code to working flow (Drag. Drop. Connect.)
# ---------------------------------------------------------------------------

def stage_04_short_code_to_flow(b, idx=3):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    stage_room(b, idx, "floor_tile", "wall_cream", accent_mat="sce_cyan")
    stage_banners(b, idx)

    # Left-center: Onboarding / Short-code provisioning screen (`onboarding-acquiring-porting-buy_code.png`)
    b.screen_panel(
        "s4_onboarding_screen", width=1.95, height=1.16, depth=0.05,
        screen_mat="screen_onboarding", frame_mat="sce_sidebar",
        loc=(cx - 1.05, 0.58, 1.88), rot=(math.pi / 2, 0, 0.10),
    )
    # Center: Visual Flow Builder screen (`flow-builder.png`)
    b.screen_panel(
        "s4_builder_screen", width=2.15, height=1.24, depth=0.05,
        screen_mat="screen_flow_builder", frame_mat="sce_sidebar",
        loc=(cx + 1.08, 0.58, 1.88),
    )

    # Bottom row of 4 compact cards: Get Short Code | Bring Code | Drag Menu | Drop & Connect
    c_get = build_flow_node_card(
        b, "s4_choice_get", "INSTANT POOL", "Get a short code", "*714*14# · Live",
        header_mat="sce_plum", loc=(cx - 1.55, 0.05, 0.88), width=0.92, height=0.44,
    )
    c_port = build_flow_node_card(
        b, "s4_choice_port", "ZERO DOWNTIME", "Bring your code", "Port *714*42#",
        header_mat="sce_cyan", loc=(cx - 0.52, 0.05, 0.88), width=0.92, height=0.44,
    )
    pop_in(c_get, f0 + 8, duration=10)
    pop_in(c_port, f0 + 18, duration=10)

    n_drag = build_flow_node_card(
        b, "s4_drag_menu", "DRAG · MENU", "Welcome menu", "1. Pay  2. Balance",
        header_mat="sce_plum", loc=(cx + 0.52, 0.05, 0.88), width=0.92, height=0.44,
    )
    key_linear(n_drag, "location", f0, (cx + 0.25, 0.05, 1.32))
    key_linear(n_drag, "location", f0 + 48, (cx + 0.25, 0.05, 1.32))
    key_linear(n_drag, "location", f0 + 68, (cx + 0.52, 0.05, 0.88))

    n_drop = build_flow_node_card(
        b, "s4_drop_input", "DROP & CONNECT", "Confirmed?", "confirm == '1'",
        header_mat="node_amber", loc=(cx + 1.55, 0.05, 0.88), width=0.92, height=0.44,
    )
    pop_in(n_drop, f0 + 72, duration=12)

    conn = b.curve_tube(
        "s4_conn_0",
        [(cx + 0.98, -0.02, 0.88), (cx + 1.03, -0.08, 0.94), (cx + 1.09, -0.02, 0.88)],
        0.016, "sce_plum_glow",
    )
    conn.data.bevel_factor_end = 0.0
    conn.data.keyframe_insert("bevel_factor_end", frame=f0 + 84)
    conn.data.bevel_factor_end = 1.0
    conn.data.keyframe_insert("bevel_factor_end", frame=f0 + 104)

    # Live 3D Feature Phone Simulator on the right updating with the resulting menu
    sim_phone = build_feature_phone(
        b, "s4_sim_phone", (cx + 2.55, -0.05, 1.55),
        rot=(math.pi / 2, 0, -0.18), scale=1.12,
        lines=("*714*14# Live", "1. My balance", "2. Buy bundle"),
    )
    pop_in(sim_phone, f0 + 96, duration=12)

    # Engineer at left console gesturing Drag -> Drop -> Connect (fully inside frame!)
    eng = human(b, "s4_engineer", (cx - 2.35, -0.42, 0), yaw=-0.42,
                shirt="shirt_plum", trousers="denim", skin="skin_deep",
                kind="jack", f0=f0, f1=f1)
    eng.work_motion("l", [
        (f0, (cx - 1.98, -0.58, 1.08)),
        (f0 + 62, (cx - 1.88, -0.62, 1.22)),
        (f0 + 96, (cx - 1.85, -0.60, 1.16)),
        (f1, (cx - 1.92, -0.58, 1.12)),
    ], grip=0.35)
    eng.smile(f0 + 105, b.p["text_white"])

    focus_camera(
        b, idx,
        start_loc=(-0.10, -5.55, 1.88),
        end_loc=(0.20, -5.45, 1.88),
        start_target=(0.10, 0.25, 1.80),
        end_target=(0.20, 0.25, 1.80),
        lens=27.5,
    )


# ---------------------------------------------------------------------------
# Scene 5 (0:21-0:29): Connect the services behind the menu (Plugin marketplace)
# ---------------------------------------------------------------------------

def stage_05_plugin_marketplace(b, idx=4):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    stage_room(b, idx, "floor_tile", "wall_cream", accent_mat="sce_plum")
    stage_banners(b, idx)

    # Workflow canvas on the left-center
    b.screen_panel(
        "s5_flow_canvas", width=2.15, height=1.24, depth=0.05,
        screen_mat="screen_flow_builder", frame_mat="sce_sidebar",
        loc=(cx - 0.85, 0.58, 1.88),
    )

    # Plugin Marketplace panel beside it with 4 clearly labelled tiles
    tiles = [
        ("PLUGIN · MOMO", "Mobile Money", "Instant collection", "sce_plum", (cx + 0.85, 0.25, 2.02), f0 + 12),
        ("PLUGIN · BANK", "Core Banking", "Account & ledger", "sce_cyan", (cx + 1.85, 0.25, 2.02), f0 + 24),
        ("PLUGIN · MSG", "SMS / OTP", "2FA & alerts", "node_amber", (cx + 0.85, 0.25, 1.48), f0 + 36),
        ("PLUGIN · ID", "KYC", "Verify subscriber", "node_green", (cx + 1.85, 0.25, 1.48), f0 + 48),
    ]
    for t_idx, (badge_t, title_t, sub_t, h_mat, t_loc, tf) in enumerate(tiles):
        tile = build_flow_node_card(
            b, f"s5_tile_{t_idx}", badge_t, title_t, sub_t,
            header_mat=h_mat, loc=t_loc, width=0.92, height=0.44,
        )
        pop_in(tile, tf, duration=10)

    # Secondary category strip: OTP · Vouchers · Commerce · Logistics
    cat_bar = b.obj("s5_cat_bar", G.box(2.05, 0.05, 0.22), "sce_sidebar", loc=(cx + 1.35, 0.22, 2.42))
    b.text3d("s5_cat_txt", "OTP · Vouchers · Commerce · Logistics", 0.072, "text_gold",
             loc=(0, -0.032, 0), align="CENTER", parent=cat_bar)
    pop_in(cat_bar, f0 + 62, duration=10)

    # Connected journey at bottom: Customer Input -> Mobile Money -> Your Plugin -> Result
    j_input = build_flow_node_card(
        b, "s5_j_input", "CUSTOMER INPUT", "Dial *714*14#", "Select option 1",
        header_mat="sce_sidebar", loc=(cx - 1.45, -0.05, 0.86), width=0.92, height=0.44,
    )
    j_momo = build_flow_node_card(
        b, "s5_j_momo", "INTEGRATION", "Mobile Money", "Charge GHS 50",
        header_mat="sce_plum", loc=(cx - 0.38, -0.05, 0.86), width=0.92, height=0.44,
    )
    j_custom = build_flow_node_card(
        b, "s5_j_custom", "EXTENSIBLE SDK", "Your Plugin", "Custom logic",
        header_mat="sce_cyan", loc=(cx + 0.68, -0.05, 0.86), width=0.92, height=0.44,
    )
    j_res = build_flow_node_card(
        b, "s5_j_res", "RESULT", "Receipt Sent", "200 OK · Confirmed",
        header_mat="node_green", loc=(cx + 1.75, -0.05, 0.86), width=0.92, height=0.44,
    )
    pop_in(j_input, f0 + 10, duration=10)
    pop_in(j_momo, f0 + 38, duration=10)
    pop_in(j_custom, f0 + 70, duration=10)
    pop_in(j_res, f0 + 84, duration=10)

    # Glowing connector line + traveling data pulse sphere
    b.curve_tube(
        "s5_journey_line",
        [(cx - 0.98, -0.08, 0.86), (cx - 0.38, -0.08, 0.86), (cx + 0.68, -0.08, 0.86), (cx + 1.32, -0.08, 0.86)],
        0.015, "sce_cyan_glow", poly=True,
    )
    pulse = b.obj("s5_data_pulse", G.sphere(0.048, 18, 12), "text_gold", loc=(cx - 0.98, -0.10, 0.86))
    key_linear(pulse, "location", f0 + 50, (cx - 0.98, -0.10, 0.86))
    key_linear(pulse, "location", f0 + 140, (cx + 1.32, -0.10, 0.86))

    # Lead engineer (left) and teammate (right) collaborating inside the camera frame
    eng = human(b, "s5_engineer", (cx - 2.35, -0.45, 0), yaw=-0.40,
                shirt="shirt_indigo", trousers="denim", skin="skin_deep",
                kind="jack", f0=f0, f1=f1)
    mate = human(b, "s5_teammate", (cx + 2.65, -0.45, 0), yaw=0.42,
                 shirt="shirt_teal", trousers="denim", skin="skin_warm",
                 kind="jill", f0=f0, f1=f1)

    eng.work_motion("l", [
        (f0, (cx - 1.98, -0.60, 1.08)),
        (f0 + 55, (cx - 1.88, -0.64, 1.22)),
        (f0 + 115, (cx - 1.85, -0.62, 1.18)),
        (f1, (cx - 1.92, -0.60, 1.12)),
    ], grip=0.4)
    mate.work_motion("r", [
        (f0, (cx + 2.28, -0.60, 1.08)),
        (f0 + 75, (cx + 2.18, -0.64, 1.26)),
        (f0 + 125, (cx + 2.22, -0.62, 1.20)),
        (f1, (cx + 2.26, -0.60, 1.12)),
    ], grip=0.35)
    eng.nod(f0 + 88, amount=0.15)
    eng.smile(f0 + 100, b.p["text_white"])
    mate.smile(f0 + 100, b.p["text_white"])

    focus_camera(
        b, idx,
        start_loc=(0.05, -5.55, 1.88),
        end_loc=(0.20, -5.45, 1.88),
        start_target=(0.15, 0.25, 1.80),
        end_target=(0.20, 0.25, 1.80),
        lens=27.5,
    )


# ---------------------------------------------------------------------------
# Scene 6 (0:29-0:35): Engineering control, not just a canvas
# ---------------------------------------------------------------------------

def stage_06_engineering_control(b, idx=5):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    stage_room(b, idx, "floor_tile", "wall_cream", accent_mat="sce_cyan")
    stage_banners(b, idx)

    # Dual operational screens: Flow Builder on left, Operations Dashboard (`dashboard.png`) on right
    b.screen_panel(
        "s6_builder_panel", width=1.95, height=1.16, depth=0.05,
        screen_mat="screen_flow_builder", frame_mat="sce_sidebar",
        loc=(cx - 1.02, 0.58, 1.88), rot=(math.pi / 2, 0, 0.08),
    )
    b.screen_panel(
        "s6_dashboard_panel", width=2.15, height=1.24, depth=0.05,
        screen_mat="screen_dashboard", frame_mat="sce_sidebar",
        loc=(cx + 1.12, 0.58, 1.88), rot=(math.pi / 2, 0, -0.06),
    )

    # 5-Beat Choreography across the foreground:
    # 1. Simulate (3D feature phone)
    sim = build_feature_phone(
        b, "s6_beat1_sim", (cx - 1.75, -0.05, 0.98),
        rot=(math.pi / 2, 0, 0.12), scale=0.76,
        lines=("1 · SIMULATE", "1. Pay merchant ✓", "Amount: GHS 50"),
    )
    pop_in(sim, f0 + 4, duration=10)

    # 2. Validate
    c_val = build_flow_node_card(
        b, "s6_beat2_val", "2 · VALIDATE", "v1.0.0 Validated ✓", "0 errors · Sapo OK",
        header_mat="node_green", loc=(cx - 0.82, -0.05, 0.86), width=0.86, height=0.42,
    )
    pop_in(c_val, f0 + 18, duration=10)

    # 3. Deploy
    c_dep = build_flow_node_card(
        b, "s6_beat3_dep", "3 · DEPLOY", "Release to Live", "Zero hosting fees",
        header_mat="sce_plum", loc=(cx + 0.12, -0.05, 0.86), width=0.86, height=0.42,
    )
    pop_in(c_dep, f0 + 34, duration=10)

    # 4. Track sessions
    c_trk = build_flow_node_card(
        b, "s6_beat4_trk", "4 · TRACK", "90.3% Completion", "292.4k completed",
        header_mat="sce_cyan", loc=(cx + 1.06, -0.05, 0.86), width=0.86, height=0.42,
    )
    pop_in(c_trk, f0 + 50, duration=10)

    # 5. Roll back with confidence
    c_rb = build_flow_node_card(
        b, "s6_beat5_rb", "5 · ROLL BACK", "Instant Rollback", "v0.9.4 Stable ✓",
        header_mat="node_amber", loc=(cx + 2.00, -0.05, 0.86), width=0.86, height=0.42,
    )
    pop_in(c_rb, f0 + 66, duration=10)

    # Engineer and teammate flanking the control wall inside the frame
    eng = human(b, "s6_engineer", (cx - 2.40, -0.45, 0), yaw=-0.40,
                shirt="shirt_indigo", trousers="denim", skin="skin_deep",
                kind="jack", f0=f0, f1=f1)
    mate = human(b, "s6_teammate", (cx + 2.72, -0.45, 0), yaw=0.40,
                 shirt="shirt_plum", trousers="denim", skin="skin_warm",
                 kind="jill", f0=f0, f1=f1)
    eng.thumbs_up(f0 + 68, f1, side="r")
    mate.thumbs_up(f0 + 68, f1, side="l")
    mate.nod(f0 + 75, amount=0.16)
    for person in (eng, mate):
        person.smile(f0 + 72, b.p["text_white"])
        person.check(f0 + 76, b.p["ok_green"], badge_mat=b.p["badge_green_bg"], rim_mat=b.p["text_white"])

    focus_camera(
        b, idx,
        start_loc=(0.0, -5.55, 1.88),
        end_loc=(0.15, -5.45, 1.88),
        start_target=(0.15, 0.25, 1.80),
        end_target=(0.20, 0.25, 1.80),
        lens=27.5,
    )


# ---------------------------------------------------------------------------
# Scene 7 (0:35-0:40): The customer outcome and brand close
# ---------------------------------------------------------------------------

def stage_07_customer_outcome_outro(b, idx=6):
    cx = stage_x(idx)
    f0, f1 = stage_frames(idx)
    stage_room(b, idx, "floor_shop", "wall_warm", accent_mat="sce_plum")
    stage_banners(b, idx, persist_end=True)

    # Left-center: Shop counter exchange with Payment Successful phone & purchased package
    b.obj("s7_counter", G.box(2.05, 0.80, 0.92), "wood_warm", loc=(cx - 1.25, -0.10, 0.46))
    b.obj("s7_counter_top", G.box(2.15, 0.86, 0.06), "wood_dark", loc=(cx - 1.25, -0.10, 0.94))
    b.obj("s7_parcel", G.box(0.36, 0.26, 0.24), "sce_plum", loc=(cx - 1.25, -0.12, 1.09))
    b.obj("s7_parcel_ribbon", G.box(0.38, 0.06, 0.25), "text_gold", loc=(cx - 1.25, -0.12, 1.09))

    # Hero basic phone showing 'Payment successful ✓'
    ok_phone = build_feature_phone(
        b, "s7_ok_phone", (cx - 0.05, -0.12, 1.48),
        rot=(math.pi / 2, 0, 0.08), scale=1.18,
        lines=("Payment successful ✓", "Paid GHS 50.00", "Ref: SCE-90421"),
        screen_mat="phone_screen_ok",
    )
    pop_in(ok_phone, f0 + 6, duration=12)

    # Right-center: Brand Close Monument + Live Product Screen + Glowing Workflow Underline
    b.screen_panel(
        "s7_brand_screen", width=2.15, height=1.22, depth=0.05,
        screen_mat="screen_flow_builder", frame_mat="sce_sidebar",
        loc=(cx + 1.55, 0.48, 1.92), rot=(math.pi / 2, 0, -0.10),
    )
    end_card = b.obj("s7_end_card", G.box(2.35, 0.08, 0.68), "sce_sidebar",
                     loc=(cx + 1.50, -0.05, 0.92))
    logo_box = b.obj("s7_end_logo_box", G.box(0.38, 0.10, 0.38), "sce_plum",
                     loc=(-0.88, -0.02, 0.06), parent=end_card)
    for b_i, bz in enumerate((0.09, 0.0, -0.09)):
        b.obj(f"s7_icon_bar_{b_i}", G.box(0.22, 0.02, 0.032), "text_white",
              loc=(0.0, -0.06, bz), parent=logo_box)
    b.text3d("s7_end_title", "ShortCode Express", 0.165, "text_white",
             loc=(-0.58, -0.04, 0.12), align="LEFT", parent=end_card)
    b.text3d("s7_end_fluent", "Be fluent.  ·  Powered by Sapo DSL Engine", 0.095, "text_gold",
             loc=(-0.58, -0.04, -0.04), align="LEFT", parent=end_card)
    b.text3d("s7_end_cta", "Build your first USSD flow  |  rhyoliteprime.com", 0.088, "text_white",
             loc=(-1.02, -0.04, -0.22), align="LEFT", bold=False, parent=end_card)
    pop_in(end_card, f0 + 16, duration=12)

    # Completed workflow line sweeping across to underline the ShortCode Express wordmark
    underline = b.curve_tube(
        "s7_workflow_underline",
        [(cx - 0.05, -0.15, 0.52), (cx + 0.70, -0.15, 0.52), (cx + 2.55, -0.15, 0.52)],
        0.020, "sce_plum_glow", poly=True,
    )
    underline.data.bevel_factor_end = 0.0
    underline.data.keyframe_insert("bevel_factor_end", frame=f0 + 12)
    underline.data.bevel_factor_end = 1.0
    underline.data.keyframe_insert("bevel_factor_end", frame=f0 + 42)

    # Customer and merchant smiling, handing over purchase, thumbs-up, and check badges
    customer = human(b, "s7_customer", (cx - 2.15, -0.40, 0), yaw=-0.42,
                     shirt="shirt_gold", trousers="denim", skin="skin_warm",
                     kind="jill", f0=f0, f1=f1)
    merchant = human(b, "s7_merchant", (cx - 0.85, 0.52, 0), yaw=0.25,
                     shirt="shirt_teal", trousers="denim", skin="skin_deep",
                     apron="sce_plum", kind="jack", f0=f0, f1=f1)
    customer.reach(f0, "l", (cx - 1.50, -0.15, 1.10), grip=0.5)
    merchant.reach(f0, "l", (cx - 1.15, -0.05, 1.10), grip=0.5)
    for person in (customer, merchant):
        person.thumbs_up(f0 + 24, f1, side="r")
        person.smile(f0 + 20, b.p["text_white"])
        person.check(f0 + 26, b.p["ok_green"], badge_mat=b.p["badge_green_bg"], rim_mat=b.p["text_white"])

    focus_camera(
        b, idx,
        start_loc=(-0.05, -5.35, 1.88),
        end_loc=(0.15, -5.15, 1.90),
        start_target=(0.15, 0.25, 1.80),
        end_target=(0.20, 0.25, 1.82),
        lens=28.0,
    )


# ---------------------------------------------------------------------------
# Lighting, World, Compositor & Scene Entry Point
# ---------------------------------------------------------------------------

def setup_Stage_light(b, idx):
    cx = stage_x(idx)
    is_bottleneck = (idx == 1)

    key_data = bpy.data.lights.new(f"Key_{idx:02d}", type="AREA")
    key_data.energy = 620.0 if is_bottleneck else 950.0
    key_data.shape = "RECTANGLE"
    key_data.size = 4.5
    key_data.size_y = 2.8
    key_data.color = (0.92, 0.94, 1.0) if is_bottleneck else (1.0, 0.97, 0.92)
    key = bpy.data.objects.new(f"Key_{idx:02d}", key_data)
    key.location = (cx - 2.6, -3.6, 4.6)
    key.rotation_euler = (math.radians(48), 0, math.radians(-24))
    b.link(key)

    fill_data = bpy.data.lights.new(f"Fill_{idx:02d}", type="AREA")
    fill_data.energy = 260.0 if is_bottleneck else 460.0
    fill_data.size = 3.6
    fill_data.color = (0.85, 0.92, 1.0)
    fill = bpy.data.objects.new(f"Fill_{idx:02d}", fill_data)
    fill.location = (cx + 3.2, -3.0, 3.4)
    fill.rotation_euler = (math.radians(55), 0, math.radians(30))
    b.link(fill)

    rim_data = bpy.data.lights.new(f"Rim_{idx:02d}", type="SPOT")
    rim_data.energy = 550.0
    rim_data.spot_size = math.radians(58)
    rim_data.color = (1.0, 0.78, 0.92) if idx >= 2 else (1.0, 0.92, 0.80)
    rim = bpy.data.objects.new(f"Rim_{idx:02d}", rim_data)
    rim.location = (cx, 2.8, 4.4)
    rim.rotation_euler = (math.radians(-35), 0, 0)
    b.link(rim)


def setup_world_and_compositor(scene):
    world = bpy.data.worlds.new("ShortCodeExpressWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.04, 0.05, 0.07, 1.0)
        bg.inputs["Strength"].default_value = 0.40

    try:
        tree = bpy.data.node_groups.new("AdvertCompositor", "CompositorNodeTree")
        scene.compositing_node_group = tree
        rl = tree.nodes.new("CompositorNodeRLayers")
        glare = tree.nodes.new("CompositorNodeGlare")
        if "Type" in glare.inputs:
            glare.inputs["Type"].default_value = "Fog Glow"
        if "Threshold" in glare.inputs:
            glare.inputs["Threshold"].default_value = 1.65
        if "Strength" in glare.inputs:
            glare.inputs["Strength"].default_value = 0.22
        out = tree.nodes.new("NodeGroupOutput")
        tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
        tree.links.new(glare.outputs["Image"], out.inputs["Image"])
    except Exception as exc:
        print(f"[shortcode-express] compositor setup skipped: {exc}")


def configure_render(scene, width=1920, height=1080, fps=S.FPS, samples=32, engine="CYCLES", device="CPU"):
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = S.total_frames()
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        scene.view_settings.view_transform = "Filmic"

    if engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.02
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 2
        scene.cycles.glossy_bounces = 2
        scene.cycles.transmission_bounces = 4
        scene.cycles.device = "CPU"
        if device == "GPU":
            try:
                prefs = bpy.context.preferences.addons["cycles"].preferences
                for dev_type in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
                    try:
                        prefs.compute_device_type = dev_type
                        prefs.get_devices()
                        if any(d.type == dev_type for d in prefs.devices):
                            for d in prefs.devices:
                                d.use = True
                            scene.cycles.device = "GPU"
                            print(f"[shortcode-express] Using Cycles GPU backend: {dev_type}")
                            break
                    except Exception:
                        continue
            except Exception:
                pass
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = samples


STAGE_BUILDERS = [
    stage_01_dial_connects,
    stage_02_engineering_bottleneck,
    stage_03_the_reveal,
    stage_04_short_code_to_flow,
    stage_05_plugin_marketplace,
    stage_06_engineering_control,
    stage_07_customer_outcome_outro,
]


def build_full_scene(width=1920, height=1080, samples=32, engine="CYCLES", device="CPU"):
    try:
        bpy.ops.preferences.addon_enable(module="cycles")
    except Exception:
        pass
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "ShortCodeExpress_Advert"

    palette = build_palette()
    b = Builder(scene, palette)

    for idx, fn in enumerate(STAGE_BUILDERS):
        b.begin_stage(idx)
        fn(b, idx)
        setup_Stage_light(b, idx)
        b.finish_stage()
        print(f"[shortcode-express] stage {idx + 1}/7 built: {S.SHOTS[idx]['id']} ({len(b.stage_objs)} objects)")

    setup_world_and_compositor(scene)
    configure_render(scene, width=width, height=height, samples=samples, engine=engine, device=device)

    for obj in bpy.data.objects:
        if obj.animation_data and obj.animation_data.action:
            act = obj.animation_data.action
            fcurves = getattr(act, "fcurves", [])
            if not fcurves and hasattr(act, "layers"):
                for layer in act.layers:
                    for strip in getattr(layer, "strips", []):
                        for bag in getattr(strip, "channelbags", []):
                            fcurves = list(fcurves) + list(getattr(bag, "fcurves", []))
            for fc in fcurves:
                for kp in fc.keyframe_points:
                    if fc.data_path in ("hide_viewport", "hide_render"):
                        kp.interpolation = "CONSTANT"
                    else:
                        kp.interpolation = "BEZIER"

    return scene
