"""Small mesh generators that return (verts, faces) lists.

Everything here is plain Python so it does not depend on Blender's primitive
operators (which need a UI context). `scene_builder.py` turns these into mesh
objects. Shapes are centred on the origin unless a `z0` offset is given, so
limbs can be pivoted at their top end.
"""

import math


def box(sx, sy, sz, origin="center"):
    """Axis-aligned box. origin='left' puts the x=0 edge at the origin."""
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    ox = hx if origin == "left" else 0.0
    v = [
        (-hx + ox, -hy, -hz), (hx + ox, -hy, -hz), (hx + ox, hy, -hz), (-hx + ox, hy, -hz),
        (-hx + ox, -hy, hz), (hx + ox, -hy, hz), (hx + ox, hy, hz), (-hx + ox, hy, hz),
    ]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


def cylinder(r, h, segments=16, z0=0.0, r_top=None, caps=True):
    """Cylinder (or truncated cone) from z0 to z0+h. r_top defaults to r."""
    r_top = r if r_top is None else r_top
    v, f = [], []
    for k in range(segments):
        a = 2 * math.pi * k / segments
        v.append((r * math.cos(a), r * math.sin(a), z0))
    for k in range(segments):
        a = 2 * math.pi * k / segments
        v.append((r_top * math.cos(a), r_top * math.sin(a), z0 + h))
    for k in range(segments):
        k2 = (k + 1) % segments
        f.append((k, k2, segments + k2, segments + k))
    if caps:
        if r > 1e-9:
            f.append(tuple(range(segments)))
        if r_top > 1e-9:
            f.append(tuple(range(segments, 2 * segments)))
    return v, f


def cone(r, h, segments=16, z0=0.0):
    """Cone with its base at z0 and tip at z0+h (used for flames and hoods)."""
    return cylinder(r, h, segments, z0, r_top=0.0, caps=True)


def sphere(r, segments=16, rings=10, center=(0.0, 0.0, 0.0), sx=1.0, sy=1.0, sz=1.0):
    v = []
    f = []
    cx, cy, cz = center
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            x = r * math.sin(phi) * math.cos(theta) * sx
            y = r * math.sin(phi) * math.sin(theta) * sy
            z = r * math.cos(phi) * sz
            v.append((cx + x, cy + y, cz + z))
    for i in range(rings):
        for j in range(segments):
            j2 = (j + 1) % segments
            a = i * segments + j
            b = i * segments + j2
            c = (i + 1) * segments + j2
            d = (i + 1) * segments + j
            if i == 0:
                f.append((a, c, d))
            elif i == rings - 1:
                f.append((a, b, d))
            else:
                f.append((a, b, c, d))
    return v, f


def torus(major, minor, segments=24, rings=10, z0=0.0):
    """Torus lying flat in the XY plane, centred at z0."""
    v = []
    f = []
    for i in range(segments):
        u = 2 * math.pi * i / segments
        for j in range(rings):
            w = 2 * math.pi * j / rings
            x = (major + minor * math.cos(w)) * math.cos(u)
            y = (major + minor * math.cos(w)) * math.sin(u)
            z = minor * math.sin(w) + z0
            v.append((x, y, z))
    for i in range(segments):
        i2 = (i + 1) % segments
        for j in range(rings):
            j2 = (j + 1) % rings
            f.append((i * rings + j, i2 * rings + j, i2 * rings + j2, i * rings + j2))
    return v, f


def plane(sx, sy, origin="center"):
    """Flat quad in the XY plane facing +Z."""
    return box(sx, sy, 0.0005, origin=origin)


def merge(*parts):
    """Combine several (verts, faces) pairs into one."""
    verts, faces = [], []
    for v, f in parts:
        offset = len(verts)
        verts.extend(v)
        faces.extend(tuple(i + offset for i in face) for face in f)
    return verts, faces


def translate(geom, dx=0.0, dy=0.0, dz=0.0):
    v, f = geom
    return [(x + dx, y + dy, z + dz) for x, y, z in v], f
