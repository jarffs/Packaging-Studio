"""2D geometry helpers, independent of Blender.

Affine transforms are stored as SVG-style tuples ``(a, b, c, d, e, f)``::

    x' = a*x + c*y + e
    y' = b*x + d*y + f
"""

from __future__ import annotations

import math
import re

MAT_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mat_mul(m, n):
    """Return the matrix product ``m @ n`` (``n`` applied first)."""
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def mat_apply(m, point):
    a, b, c, d, e, f = m
    x, y = point
    return (a * x + c * y + e, b * x + d * y + f)


def mat_translate(tx, ty):
    return (1.0, 0.0, 0.0, 1.0, tx, ty)


def mat_scale(sx, sy):
    return (sx, 0.0, 0.0, sy, 0.0, 0.0)


def mat_rotate(deg, cx=0.0, cy=0.0):
    r = math.radians(deg)
    cos = math.cos(r)
    sin = math.sin(r)
    rot = (cos, sin, -sin, cos, 0.0, 0.0)
    if cx == 0.0 and cy == 0.0:
        return rot
    return mat_mul(mat_translate(cx, cy), mat_mul(rot, mat_translate(-cx, -cy)))


def mat_skew_x(deg):
    return (1.0, 0.0, math.tan(math.radians(deg)), 1.0, 0.0, 0.0)


def mat_skew_y(deg):
    return (1.0, math.tan(math.radians(deg)), 0.0, 1.0, 0.0, 0.0)


_TRANSFORM_RE = re.compile(r"(\w+)\s*\(([^)]*)\)")
_NUM_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def parse_transform(text):
    """Parse an SVG ``transform`` attribute into a single affine matrix."""
    matrix = MAT_IDENTITY
    if not text:
        return matrix
    for name, args in _TRANSFORM_RE.findall(text):
        nums = [float(x) for x in _NUM_RE.findall(args)]
        if name == "translate":
            tx = nums[0] if nums else 0.0
            ty = nums[1] if len(nums) > 1 else 0.0
            matrix = mat_mul(matrix, mat_translate(tx, ty))
        elif name == "scale":
            sx = nums[0] if nums else 1.0
            sy = nums[1] if len(nums) > 1 else sx
            matrix = mat_mul(matrix, mat_scale(sx, sy))
        elif name == "rotate":
            angle = nums[0] if nums else 0.0
            if len(nums) >= 3:
                matrix = mat_mul(matrix, mat_rotate(angle, nums[1], nums[2]))
            else:
                matrix = mat_mul(matrix, mat_rotate(angle))
        elif name == "matrix" and len(nums) == 6:
            matrix = mat_mul(matrix, tuple(nums))
        elif name == "skewX":
            matrix = mat_mul(matrix, mat_skew_x(nums[0] if nums else 0.0))
        elif name == "skewY":
            matrix = mat_mul(matrix, mat_skew_y(nums[0] if nums else 0.0))
    return matrix


def bbox(points):
    """Return ``(min_x, min_y, max_x, max_y)`` for a list of points."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def polygon_area(points):
    """Return the signed area of a polygon (shoelace formula)."""
    n = len(points)
    total = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def polygon_centroid(points):
    n = len(points)
    area = polygon_area(points)
    if abs(area) < 1e-12:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (sum(xs) / n, sum(ys) / n)
    cx = cy = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    return (cx / (6.0 * area), cy / (6.0 * area))


def point_in_polygon(point, polygon):
    """Ray-casting point-in-polygon test."""
    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        denom = (yj - yi) or 1e-12
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / denom + xi):
            inside = not inside
        j = i
    return inside


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def polyline_length(points):
    return sum(distance(points[i], points[i + 1]) for i in range(len(points) - 1))


def convex_hull(points):
    """Return the convex hull (counter-clockwise) via Andrew's monotone chain."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return list(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def point_segment_distance(p, a, b):
    """Shortest distance from point ``p`` to segment ``a``-``b``."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx = bx - ax
    dy = by - ay
    if dx == 0.0 and dy == 0.0:
        return distance(p, a)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return distance(p, (ax + t * dx, ay + t * dy))


def segment_angle(a, b):
    """Return the angle of segment ``a``-``b`` in radians."""
    return math.atan2(b[1] - a[1], b[0] - a[0])


def angle_diff(a, b):
    """Return the smallest undirected angle (0..pi/2) between two directions."""
    d = abs(a - b) % math.pi
    return min(d, math.pi - d)


def segment_intersection(p1, p2, p3, p4, eps=1e-9):
    """Return the intersection point of segments ``p1-p2`` and ``p3-p4``.

    Returns ``None`` for parallel/collinear segments or when the segments do
    not cross within their extents. Endpoint touches (T-junctions) are
    included.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(denom) < eps:
        return None
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / denom
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / denom
    if -eps <= t <= 1.0 + eps and -eps <= u <= 1.0 + eps:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None

