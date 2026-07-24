"""Detect closed panels (faces) from classified dieline geometry.

This is a pure-Python planar arrangement / polygonize implementation — no
Blender and no third-party dependencies — so it can be unit-tested directly.

Pipeline:
    1. Collect boundary segments from cut/fold/glue lines.
    2. "Node" the arrangement: split every segment at intersections and
       T-junctions so shared points become shared vertices.
    3. Deduplicate vertices on a tolerance grid and build an undirected graph.
    4. Traverse minimal cycles (faces) of the planar graph.
    5. Discard the unbounded outer face; the rest are panels.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from ..utils.constants import LineType
from ..utils.geometry import (
    point_in_polygon,
    polygon_area,
    polygon_centroid,
    segment_intersection,
)
from .types import Panel, PanelModel

# Line types whose geometry bounds a panel. Scores/creases are dashed fold
# lines that divide the sheet into panels, so they must be treated as
# boundaries alongside cuts, folds and glue flaps.
_BOUNDARY_TYPES = (
    LineType.CUT,
    LineType.FOLD,
    LineType.SCORE,
    LineType.GLUE_FLAP,
)
# Line types that act as a hinge (fold) between two panels.
_FOLD_TYPES = (LineType.FOLD, LineType.GLUE_FLAP, LineType.SCORE)

_SNAP_TOL = 1e-4  # relative snapping tolerance applied to the bounding box


def detect_panels(
    classified: Sequence,
    boundary_types: Sequence = _BOUNDARY_TYPES,
) -> PanelModel:
    """Resolve ``classified`` lines into a :class:`PanelModel`."""
    segments = _collect_segments(classified, boundary_types)
    if not segments:
        return PanelModel(vertices=[], panels=[])

    tol = _tolerance(segments)
    noded = _node_segments(segments, tol)
    vertices, edges, edge_types = _build_graph(noded, tol)
    if not edges:
        return PanelModel(vertices=vertices, panels=[])

    faces = _extract_faces(vertices, edges)
    outer_poly = _outer_polygon(classified, boundary_types)
    panels = _faces_to_panels(faces, vertices, outer_poly)

    fold_edges = {
        edge
        for edge, lt in edge_types.items()
        if lt in {t.value for t in _FOLD_TYPES}
    }
    return PanelModel(
        vertices=vertices,
        panels=panels,
        fold_edges=fold_edges,
        edge_types=edge_types,
    )


def _outer_polygon(classified, boundary_types):
    """Return the vertices of the largest closed boundary path, if any.

    This is the main die-cut outline. Faces whose centroid falls outside it are
    treated as artwork (3D previews, logos) and discarded.
    """
    wanted = set(boundary_types)
    best = None
    best_area = 0.0
    for line in classified:
        path = line.path
        if line.line_type not in wanted:
            continue
        if path.is_closed and len(path.points) >= 3:
            area = abs(polygon_area(path.points))
            if area > best_area:
                best_area = area
                best = path.points
    return best


def _collect_segments(classified, boundary_types):
    """Return a list of ``(a, b, line_type_value)`` boundary segments."""
    wanted = set(boundary_types)
    segments = []
    for line in classified:
        if line.line_type not in wanted:
            continue
        pts = line.path.points
        n = len(pts)
        if n < 2:
            continue
        limit = n if line.path.is_closed else n - 1
        for i in range(limit):
            a = pts[i]
            b = pts[(i + 1) % n]
            if a != b:
                segments.append((a, b, line.line_type.value))
    return segments


def _tolerance(segments):
    xs = [p[0] for s in segments for p in (s[0], s[1])]
    ys = [p[1] for s in segments for p in (s[0], s[1])]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    return diag * _SNAP_TOL


def _node_segments(segments, tol):
    """Split each segment at every intersection/T-junction with the others."""
    noded = []
    for i, (a, b, lt) in enumerate(segments):
        cuts = [0.0, 1.0]
        abx, aby = b[0] - a[0], b[1] - a[1]
        length_sq = abx * abx + aby * aby
        if length_sq == 0.0:
            continue
        for j, (c, d, _) in enumerate(segments):
            if i == j:
                continue
            hit = segment_intersection(a, b, c, d, eps=1e-9)
            if hit is None:
                continue
            t = ((hit[0] - a[0]) * abx + (hit[1] - a[1]) * aby) / length_sq
            t = max(0.0, min(1.0, t))
            cuts.append(t)
        cuts = _dedupe_sorted(cuts, tol / math.sqrt(length_sq))
        for k in range(len(cuts) - 1):
            t0, t1 = cuts[k], cuts[k + 1]
            p0 = (a[0] + t0 * abx, a[1] + t0 * aby)
            p1 = (a[0] + t1 * abx, a[1] + t1 * aby)
            noded.append((p0, p1, lt))
    return noded


def _dedupe_sorted(values, min_gap):
    values = sorted(values)
    out = [values[0]]
    for v in values[1:]:
        if v - out[-1] > min_gap:
            out.append(v)
    return out


def _build_graph(noded, tol):
    """Deduplicate vertices and build the undirected edge set."""
    vertices: List[Tuple[float, float]] = []
    lookup = {}

    def vid(pt):
        key = (round(pt[0] / tol), round(pt[1] / tol))
        idx = lookup.get(key)
        if idx is None:
            idx = len(vertices)
            lookup[key] = idx
            vertices.append(pt)
        return idx

    edges = set()
    edge_types = {}
    for a, b, lt in noded:
        ia, ib = vid(a), vid(b)
        if ia == ib:
            continue
        edge = frozenset((ia, ib))
        edges.add(edge)
        # Fold/glue wins over cut when two lines coincide on an edge.
        prev = edge_types.get(edge)
        if prev is None or lt in {t.value for t in _FOLD_TYPES}:
            edge_types[edge] = lt
    return vertices, edges, edge_types


def _extract_faces(vertices, edges):
    """Return every minimal cycle (face) of the planar graph as vertex loops."""
    adjacency = {i: [] for i in range(len(vertices))}
    for edge in edges:
        i, j = tuple(edge)
        adjacency[i].append(j)
        adjacency[j].append(i)

    # Sort neighbors around each vertex by angle (CCW).
    for v, neigh in adjacency.items():
        vx, vy = vertices[v]
        neigh.sort(key=lambda w: math.atan2(vertices[w][1] - vy, vertices[w][0] - vx))

    faces = []
    visited = set()  # directed half-edges (a, b)
    for edge in edges:
        for a, b in (tuple(edge), tuple(edge)[::-1]):
            if (a, b) in visited:
                continue
            loop = _trace_face(a, b, adjacency, vertices, visited)
            if loop and len(loop) >= 3:
                faces.append(loop)
    return faces


def _trace_face(start_a, start_b, adjacency, vertices, visited):
    """Trace one face beginning with directed half-edge ``start_a -> start_b``."""
    loop = []
    a, b = start_a, start_b
    guard = 0
    max_steps = sum(len(n) for n in adjacency.values()) + 4
    while True:
        visited.add((a, b))
        loop.append(a)
        c = _next_neighbor(b, a, adjacency, vertices)
        if c is None:
            return None
        a, b = b, c
        if (a, b) == (start_a, start_b):
            break
        guard += 1
        if guard > max_steps:
            return None
    return loop


def _next_neighbor(b, a, adjacency, vertices):
    """At vertex ``b`` arriving from ``a``, return the next CCW-face neighbor."""
    neigh = adjacency[b]
    if not neigh:
        return None
    idx = neigh.index(a)
    # The neighbor immediately clockwise of the incoming edge keeps the face
    # interior on the left (CCW traversal for bounded faces).
    return neigh[(idx - 1) % len(neigh)]


def _faces_to_panels(faces, vertices, outer_poly=None):
    """Drop the outer (largest-area) face and return the bounded panels."""
    scored = []
    for loop in faces:
        poly = [vertices[i] for i in loop]
        area = polygon_area(poly)
        scored.append((loop, poly, area))

    if not scored:
        return []

    # The unbounded outer face has the largest absolute area.
    outer_idx = max(range(len(scored)), key=lambda k: abs(scored[k][2]))

    panels = []
    for k, (loop, poly, area) in enumerate(scored):
        if k == outer_idx:
            continue
        if abs(area) < 1e-9:
            continue
        if area < 0:  # normalize to CCW
            loop = list(reversed(loop))
            poly = list(reversed(poly))
            area = -area
        centroid = polygon_centroid(poly)
        # Discard faces outside the main die-cut outline (preview artwork).
        if outer_poly is not None and not point_in_polygon(centroid, outer_poly):
            continue
        panels.append(
            Panel(
                index=len(panels),
                loop=loop,
                centroid=centroid,
                area=area,
            )
        )
    return panels
