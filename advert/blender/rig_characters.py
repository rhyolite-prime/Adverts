"""Rigged characters for the advert, built from the Rigify file in advert/rigs/.

The figures are Jack and Jill from `rigs/Body Mechanics Rigs.blend`. Each person in a stage is
appended fresh from that file, so every character has its own armature, drivers and mesh.

Units and frames
----------------
* The rig is about 20 "rig units" tall. `S` converts rig units to metres (figure = FIGURE_HEIGHT).
* "Figure-local" space: origin at the feet, +Z up, faces -Y when yaw = 0. Positions passed to
  this module are figure-local metres unless the name says `world`.
* The character's right hand is '.R' in the rig, and sits at -X when facing -Y.

Posing
------
* Arms are posed with the FK controls (upper_arm_fk, forearm_fk, hand_fk, fingers, thumb). A small
  Levenberg-Marquardt solver finds joint angles that put the wrist on a target. The rig's IK
  constraints are not used: they did not reach their targets reliably in this file.
* Torso, chest and head stay in their rest pose. Breathing moves only the chest.

Clothing and skin
-----------------
* The mesh has one material in the file. Here each face is assigned to a slot (skin, torso,
  sleeves, trousers, shoes, hands, apron, hair) from the bone weights and body position, and each
  slot gets its own material per person.
* Smile and check mark are small meshes or curves parented to the armature (see `Person.smile`
  and `Person.check`). The rig has no face controls and no shape keys.
"""

import math
import os
from collections import Counter

import bpy
from mathutils import Matrix, Vector

import geometry as G

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
RIG_BLEND = os.path.abspath(os.path.join(HERE, "..", "rigs", "Body Mechanics Rigs.blend"))

RIG_HEIGHT_UNITS = 20.03      # standing height of the rig mesh, measured in rig units
FIGURE_HEIGHT = 1.75          # metres
S = FIGURE_HEIGHT / RIG_HEIGHT_UNITS

SIDE_SUFFIX = {"r": ".R", "l": ".L"}   # character's right is '.R'
SIDE_SIGN = {"r": -1.0, "l": 1.0}      # character's right is -X when facing -Y

SLOTS = ("skin", "torso", "sleeves", "trousers", "shoes", "hands", "apron", "hair")
SLOT_INDEX = {name: i for i, name in enumerate(SLOTS)}
# The rig has FK controls for index, middle and pinky. The ring finger has no FK control, so its
# deform bones are posed directly (see _fk_only_arms).
FINGERS = ("f_index", "f_middle", "f_pinky")

NECK_Z = 16.3     # rig units: spine vertices above this are neck/head (skin)
HAIR_Z = 18.7     # rig units: head above this is hair
APRON_Z = (7.5, 12.9)
APRON_FRONT_Y = -0.55

REST_WRIST = (0.19, -0.02, 0.92)   # figure-local metres, for the right side (sign applied per side)
REST_ELBOW = (0.17, 0.02, 1.12)
FIST_WRIST = (0.22, -0.20, 1.36)
FIST_ELBOW = (0.22, 0.02, 1.10)
SHOULDER = (0.14, 0.0, 1.39)       # figure-local metres, shoulder joint (sign applied per side)


def _region_for_vertex(group, z):
    """Map the dominant vertex group of a vertex (and its height) to a material slot name."""
    if group is None:
        return "trousers" if z < 9.5 else "torso"
    if group.startswith(("DEF-hand", "DEF-palm", "DEF-f_", "DEF-thumb")):
        return "hands"
    if group.startswith(("DEF-upper_arm", "DEF-forearm", "DEF-shoulder")):
        return "sleeves"
    if group.startswith(("DEF-foot", "DEF-toe")):
        return "shoes"
    if group.startswith(("DEF-pelvis", "DEF-thigh", "DEF-shin")):
        return "trousers"
    # spine groups: torso below the neck, skin above it
    return "skin" if z >= NECK_Z else "torso"


def _face_slots(mesh_obj):
    """Material slot index for each polygon of a rig mesh (positions in rig units)."""
    me = mesh_obj.data
    names = {g.index: g.name for g in mesh_obj.vertex_groups}
    basis = mesh_obj.matrix_basis
    pos, vslot = [], []
    for v in me.vertices:
        p = basis @ v.co
        pos.append(p)
        best, best_w = None, 0.0
        for g in v.groups:
            if g.weight > best_w:
                best, best_w = names.get(g.group), g.weight
        vslot.append(_region_for_vertex(best, p.z))

    out = []
    for poly in me.polygons:
        slot = Counter(vslot[i] for i in poly.vertices).most_common(1)[0][0]
        c = Vector((0.0, 0.0, 0.0))
        for i in poly.vertices:
            c += pos[i]
        c /= len(poly.vertices)
        if slot == "skin" and (c.z > HAIR_Z or (c.z > HAIR_Z - 0.7 and c.y > 0.3)):
            slot = "hair"
        if slot in ("torso", "trousers") and c.y < APRON_FRONT_Y and abs(c.x) < 0.95 \
                and APRON_Z[0] < c.z < APRON_Z[1]:
            slot = "apron"
        out.append(SLOT_INDEX[slot])
    return out


def _append_rig(kind):
    """Append a fresh copy of the Jack or Jill mesh and armature from the rig file (not linked)."""
    names = {"jack": ("Jack", "Jack Controls"), "jill": ("Jill", "Jill Controls")}[kind]
    with bpy.data.libraries.load(RIG_BLEND, link=False) as (src, dst):
        dst.objects = list(names)
    loaded = [o for o in dst.objects if o is not None]
    mesh = next(o for o in loaded if o.type == "MESH")
    arm = next(o for o in loaded if o.type == "ARMATURE")
    return mesh, arm


def _solve_linear(a, b):
    """Solve a x = b by Gaussian elimination with partial pivoting. Returns None if singular."""
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        for r in range(n):
            if r != col:
                f = m[r][col] / m[col][col]
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] / m[i][i] for i in range(n)]


def _fk_only_arms(arm):
    """Pose the arms from FK only.

    In the file, each arm bone has an IK copy ("Copy Transforms.001") whose influence is driven by
    the IK_FK switch. Those drivers do not re-evaluate reliably once the rig is appended, so the IK
    copy would stay at full strength and override the FK pose. The IK copy is removed from the arm
    chains (its driver too) and the FK copy is kept at full strength. Legs keep the rig's setup.
    """
    ad = arm.animation_data
    for side in ("L", "R"):
        for i in (1, 2, 3):
            # ring finger: the deform bone is posed directly so it can curl with the fist
            arm.pose.bones[f"DEF-f_ring.0{i}.{side}"].constraints[0].influence = 0.0
        for bone in (f"ORG-upper_arm.{side}", f"ORG-forearm.{side}", f"ORG-hand.{side}"):
            pb = arm.pose.bones[bone]
            fk = [c for c in pb.constraints if c.type == "COPY_TRANSFORMS" and c.subtarget.endswith(f"_fk.{side}")]
            ik = [c for c in pb.constraints if c.type == "COPY_TRANSFORMS" and c.subtarget and not c.subtarget.endswith(f"_fk.{side}")]
            assert fk, f"{bone}: no FK copy constraint"
            for c in fk:
                c.influence = 1.0
            for c in ik:
                if ad:
                    fc = ad.drivers.find(f'pose.bones["{bone}"].constraints["{c.name}"].influence')
                    if fc is not None:
                        ad.drivers.remove(fc)
                c.influence = 0.0


def _rz(yaw):
    return Matrix.Rotation(yaw, 4, "Z")


class Person:
    """One rigged character inside a stage. Positions are figure-local metres unless noted."""

    def __init__(self, b, name, kind, loc, yaw, mats, f0, hair=True):
        self.b = b
        self.name = name
        self.loc = Vector(loc)
        self.yaw = yaw
        self.f0 = f0
        mesh, arm = _append_rig(kind)
        self.mesh = mesh
        self.arm = arm
        b.link(arm)
        b.link(mesh)
        _fk_only_arms(arm)
        arm.name = f"{name}_rig"
        mesh.name = name
        arm.location = tuple(self.loc)
        arm.rotation_euler = (0.0, 0.0, yaw)
        arm.scale = (S, S, S)
        arm.show_in_front = False
        for pb in arm.pose.bones:
            pb.rotation_mode = "XYZ"
        self._assign_materials(mats, hair)
        bpy.context.view_layer.update()
        self.bones = arm.pose.bones
        self._warm = {}
        # Face front and mouth height measured on the Jack and Jill meshes (figure metres).
        self.face_y, self.mouth_z = (-0.136, 1.47) if kind == "jack" else (-0.120, 1.44)
        self.chest_y = -0.095 if kind == "jack" else -0.125     # torso front at chest height, plus a margin
        self.rest(f0)

    # --- materials -------------------------------------------------------
    def _assign_materials(self, mats, hair):
        m = dict(mats)
        m.setdefault("sleeves", m["torso"])
        m.setdefault("trousers", m["torso"])
        m.setdefault("shoes", m["trousers"])
        m.setdefault("hands", m["skin"])
        m.setdefault("apron", m["torso"])
        m.setdefault("hair", m["skin"])
        if not hair:
            m["hair"] = m["skin"]
        me = self.mesh.data
        me.materials.clear()
        for slot in SLOTS:
            me.materials.append(m[slot])
        for poly, idx in zip(me.polygons, _face_slots(self.mesh)):
            poly.material_index = idx
        for p in me.polygons:
            p.use_smooth = True

    # --- coordinates -------------------------------------------------------
    def to_local(self, world_point):
        """World point -> figure-local metres."""
        return _rz(-self.yaw) @ (Vector(world_point) - self.loc)

    def to_world(self, local_point):
        """Figure-local metres -> world metres."""
        return self.loc + _rz(self.yaw) @ Vector(local_point)

    def _rig(self, local_m):
        """Figure-local metres -> rig units (armature space)."""
        return Vector(local_m) / S

    # --- bone access -------------------------------------------------------
    def _bone_head(self, name):
        return self.bones[name].matrix.translation.copy()

    def _bone_tail(self, name):
        pb = self.bones[name]
        return (pb.matrix @ Vector((0.0, pb.bone.length, 0.0))).copy()

    def _limb_names(self, side):
        sfx = SIDE_SUFFIX[side]
        names = [f"upper_arm_fk{sfx}", f"forearm_fk{sfx}", f"hand_fk{sfx}"]
        names += self._finger_names(side)
        return names

    def _finger_names(self, side):
        sfx = SIDE_SUFFIX[side]
        names = []
        for f in FINGERS:
            names += [f"{f}.0{i}{sfx}" for i in (1, 2, 3)]
        names += [f"DEF-f_ring.0{i}{sfx}" for i in (1, 2, 3)]
        names += [f"thumb.0{i}{sfx}" for i in (1, 2, 3)]
        return names

    def _set_fingers(self, side, curl, thumb=0.0):
        """Curl the four fingers by `curl` (radians, about X). The thumb is set to `thumb`."""
        sfx = SIDE_SUFFIX[side]
        for f in FINGERS:
            for i in (1, 2, 3):
                self.bones[f"{f}.0{i}{sfx}"].rotation_euler = (curl, 0.0, 0.0)
        for i in (1, 2, 3):
            self.bones[f"DEF-f_ring.0{i}{sfx}"].rotation_euler = (curl, 0.0, 0.0)
            self.bones[f"thumb.0{i}{sfx}"].rotation_euler = (thumb, 0.0, 0.0)

    def _key_limb(self, side, frame):
        for n in self._limb_names(side):
            self.bones[n].keyframe_insert("rotation_euler", frame=frame)

    def _set_angles(self, names_xyz, x):
        """names_xyz: list of bone names, each takes 3 values from x."""
        for i, n in enumerate(names_xyz):
            self.bones[n].rotation_euler = (x[3 * i], x[3 * i + 1], x[3 * i + 2])

    # --- solver ------------------------------------------------------------
    def _lm(self, fn, x, iters=25):
        """Levenberg-Marquardt with finite-difference Jacobian. fn(x) -> list of residuals."""
        n = len(x)
        lam = 1e-2
        r = fn(x)
        cost = sum(v * v for v in r)
        for _ in range(iters):
            if cost < 1e-9:
                break
            eps = 1e-4
            jac = []
            for j in range(n):
                xp = list(x)
                xp[j] += eps
                rp = fn(xp)
                jac.append([(rp[k] - r[k]) / eps for k in range(len(r))])
            # normal equations
            a = [[sum(jac[i][k] * jac[j][k] for k in range(len(r))) for j in range(n)] for i in range(n)]
            g = [sum(jac[i][k] * r[k] for k in range(len(r))) for i in range(n)]
            improved = False
            for _try in range(6):
                m = [[a[i][j] + (lam if i == j else 0.0) for j in range(n)] for i in range(n)]
                dx = _solve_linear(m, [-v for v in g])
                if dx is None:
                    lam *= 10
                    continue
                xn = [x[i] + dx[i] for i in range(n)]
                rn = fn(xn)
                cn = sum(v * v for v in rn)
                if cn < cost:
                    x, r, cost = xn, rn, cn
                    lam = max(lam * 0.3, 1e-7)
                    improved = True
                    break
                lam *= 8
            if not improved:
                break
        fn(x)
        return x, cost

    def _solve_arm(self, side, wrist_local, elbow_local, thumb_up=False, fist=False):
        sfx = SIDE_SUFFIX[side]
        up_n, fore_n, hand_n = f"upper_arm_fk{sfx}", f"forearm_fk{sfx}", f"hand_fk{sfx}"
        wrist_t = self._rig(wrist_local)
        elbow_t = self._rig(elbow_local)
        thumb_base, thumb_tip = f"thumb.01{sfx}", f"thumb.03{sfx}"

        if fist:
            self._set_fingers(side, 1.25)

        def arm_residuals(x):
            self._set_angles([up_n, fore_n], x)
            bpy.context.view_layer.update()
            wrist = self._bone_head(hand_n)
            elbow = self._bone_head(fore_n)
            r = [wrist[k] - wrist_t[k] for k in range(3)] + [0.12 * (elbow[k] - elbow_t[k]) for k in range(3)]
            if thumb_up:
                base = self._bone_head(thumb_base)
                tip = self._bone_tail(thumb_tip)
                d = (tip - base)
                d = d / d.length if d.length > 1e-9 else d
                r += [0.6 * (d[k] - (1.0 if k == 2 else 0.0)) for k in range(3)]
            return r

        # Start from the last solution for this arm; try other starts only if that did not converge.
        best = None
        for seed in [self._warm.get(side, [0.0] * 6)]:
            x, cost = self._lm(arm_residuals, seed)
            if best is None or cost < best[1]:
                best = (x, cost)
        if best[1] > 1e-5:
            for seed in ([0.0] * 6, [0.0, 0.0, 1.4, 0.0, 0.0, 0.0], [0.0, 0.0, -1.4, 0.0, 0.0, 0.0],
                         [0.6, 0.0, 0.6, 0.6, 0.0, 0.0]):
                x, cost = self._lm(arm_residuals, seed)
                if cost < best[1]:
                    best = (x, cost)
                if best[1] <= 1e-5:
                    break
        x = best[0]
        self._warm[side] = list(x)
        self._set_angles([up_n, fore_n], x)

        if thumb_up:
            # Second pass: turn the hand so the thumb points up, keeping the wrist on target.
            def hand_residuals(y):
                self._set_angles([up_n, fore_n, hand_n], y)
                bpy.context.view_layer.update()
                wrist = self._bone_head(hand_n)
                elbow = self._bone_head(fore_n)
                base = self._bone_head(thumb_base)
                tip = self._bone_tail(thumb_tip)
                d = tip - base
                d = d / d.length if d.length > 1e-9 else d
                r = [3.0 * (wrist[k] - wrist_t[k]) for k in range(3)]
                r += [0.12 * (elbow[k] - elbow_t[k]) for k in range(3)]
                r += [1.5 * (d[k] - (1.0 if k == 2 else 0.0)) for k in range(3)]
                return r
            y0 = list(x) + [0.0, 0.0, 0.0]
            y, _cost = self._lm(hand_residuals, y0)
            self._warm[side] = list(y[:6])
            self._set_angles([up_n, fore_n, hand_n], y)
            x = y

        bpy.context.view_layer.update()
        wrist = self._bone_head(hand_n)
        return (wrist - wrist_t).length * S    # metres of error

    # --- posing API ----------------------------------------------------------
    def rest(self, frame):
        """Arms hang at the sides; legs and torso stay in the rig's rest pose."""
        for side in SIDE_SIGN:
            sg = SIDE_SIGN[side]
            wrist = (sg * REST_WRIST[0], REST_WRIST[1], REST_WRIST[2])
            elbow = (sg * REST_ELBOW[0], REST_ELBOW[1], REST_ELBOW[2])
            self._set_fingers(side, 0.2)
            self._solve_arm(side, wrist, elbow)
            self._key_limb(side, frame)

    def reach(self, frame, side, world_target, grip=0.6):
        """Key the arm so the wrist reaches `world_target`. Returns the wrist's world position."""
        sfx = SIDE_SUFFIX[side]
        sg = SIDE_SIGN[side]
        target = self.to_local(world_target)
        shoulder = Vector((sg * SHOULDER[0], SHOULDER[1], SHOULDER[2]))
        hint = shoulder + (target - shoulder) * 0.5 + Vector((sg * 0.10, 0.10, -0.05))
        self._set_fingers(side, grip)
        err = self._solve_arm(side, target, hint)
        self._key_limb(side, frame)
        self.last_error = err
        return self.grip_point(side)

    def grip_point(self, side):
        """World point in the middle of the hand (between the wrist and the middle finger's base)."""
        sfx = SIDE_SUFFIX[side]
        mid = (self._bone_head(f"hand_fk{sfx}") + self._bone_head(f"f_middle.01{sfx}")) / 2.0
        return self.to_world(mid * S)

    def thumbs_up(self, f_start, f_end, side="r"):
        """Make a fist with the thumb up. The pose is held from f_start until f_end."""
        sg = SIDE_SIGN[side]
        self._key_limb(side, f_start - 14)                  # hold the current pose first
        wrist = (sg * FIST_WRIST[0], FIST_WRIST[1], FIST_WRIST[2])
        elbow = (sg * FIST_ELBOW[0], FIST_ELBOW[1], FIST_ELBOW[2])
        err = self._solve_arm(side, wrist, elbow, thumb_up=True, fist=True)
        self._key_limb(side, f_start)
        self._key_limb(side, f_end)
        self.thumb_error = err
        return err

    def breathe(self, f0, f1, step=12, amount=0.12):
        """Chest rises and falls slightly. Only the chest moves, so the feet stay on the floor."""
        chest = self.bones["chest"]
        f = f0
        up = True
        while f <= f1:
            chest.location = (0.0, 0.0, amount if up else 0.0)
            chest.keyframe_insert("location", frame=f)
            up = not up
            f += step

    # --- attached props ------------------------------------------------------
    def _attach(self, name, geom, mat, loc_m=(0, 0, 0), rot=(0, 0, 0), scale_m=(1, 1, 1), smooth=True):
        """Mesh that stays with the figure. `geom` is in metres; the object is scaled back to metres."""
        return self.b.obj(name, geom, mat, loc=tuple(self._rig(loc_m)), rot=rot,
                          scale=tuple(v / S for v in scale_m), parent=self.arm, smooth=smooth)

    def hat(self, style, mat):
        """Headwear sitting on the head (head top is about 1.75 m, face front is at y = -0.14 m)."""
        if style == "helmet":
            self._attach(f"{self.name}_helmet", G.sphere(0.158, 28, 18), mat, loc_m=(0, 0.0, 1.63))
        elif style == "toque":
            self._attach(f"{self.name}_toque", G.cylinder(0.125, 0.22, 20, z0=0.0), mat, loc_m=(0, 0.0, 1.70))
            self._attach(f"{self.name}_toque_top", G.sphere(0.135, 16, 10), mat, loc_m=(0, 0.0, 1.92))
        elif style == "hardhat":
            self._attach(f"{self.name}_hardhat", G.sphere(0.16, 20, 12, sz=0.6), mat, loc_m=(0, 0.0, 1.68))
        elif style == "straw":
            self._attach(f"{self.name}_brim", G.cylinder(0.27, 0.02, 24, z0=0.0), mat, loc_m=(0, 0.0, 1.73))
            self._attach(f"{self.name}_crown", G.cylinder(0.14, 0.13, 18, z0=0.0), mat, loc_m=(0, 0.0, 1.73))
        elif style == "cap":
            self._attach(f"{self.name}_cap", G.sphere(0.14, 20, 12, sz=0.6), mat, loc_m=(0, 0.0, 1.70))
            self._attach(f"{self.name}_peak", G.box(0.14, 0.12, 0.02), mat, loc_m=(0, -0.16, 1.68))
        else:
            raise ValueError(style)

    def visor(self, mat):
        """Welding visor across the face (in front of the helmet's brow)."""
        self._attach(f"{self.name}_visor", G.box(0.2, 0.03, 0.09), mat, loc_m=(0, -0.155, 1.645))

    def smile(self, frame, mat):
        """Smile: a short curved arc across the mouth. The rig has no face controls or shape keys."""
        # Measured front of the face at mouth height (figure metres), set per figure in __init__.
        y, z = self.face_y, self.mouth_z
        pts = [(-0.035, y, z + 0.014), (0.0, y - 0.004, z), (0.035, y, z + 0.014)]
        return self._curve(f"{self.name}_smile", pts, mat, bevel=0.0048, frame=frame, poly=False)

    def check(self, frame, mat):
        """Green check mark on the chest, facing the camera (-Y). Kept low in the frame, clear of the head."""
        y = self.chest_y
        pts = [(-0.10, y, 1.24), (-0.03, y, 1.15), (0.11, y, 1.35)]
        return self._curve(f"{self.name}_check", pts, mat, bevel=0.02, frame=frame, poly=True)

    def _curve(self, name, pts, mat, bevel, frame, poly=True):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = bevel
        cu.bevel_resolution = 3
        cu.resolution_u = 8
        cu.use_fill_caps = True
        cu.materials.append(mat)
        sp = cu.splines.new("POLY" if poly else "BEZIER")
        if poly:
            sp.points.add(len(pts) - 1)
            for p, co in zip(sp.points, pts):
                p.co = (co[0], co[1], co[2], 1.0)
        else:
            sp.bezier_points.add(len(pts) - 1)
            for bp, co in zip(sp.bezier_points, pts):
                bp.co = Vector(co)
                bp.handle_left_type = "AUTO"
                bp.handle_right_type = "AUTO"
        o = bpy.data.objects.new(name, cu)
        self.b.link(o)
        o.parent = self.arm
        o.scale = (1.0 / S, 1.0 / S, 1.0 / S)
        # pop in: tiny at `frame`, full size 8 frames later
        start = frame
        o.scale = (0.001, 0.001, 0.001)
        o.keyframe_insert("scale", frame=start)
        o.scale = (1.0 / S, 1.0 / S, 1.0 / S)
        o.keyframe_insert("scale", frame=start + 8)
        return o
