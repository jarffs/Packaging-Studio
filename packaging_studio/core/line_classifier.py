"""Heuristic classification of dieline geometry.

Three passes:
 1. Topological — the largest closed path is the outer cut contour.
 2. Per-line     — classify remaining paths (window / score / fold).
 3. Refinement  — reclassify fold candidates that sit parallel and close to
                  an outer edge as glue flaps.

The heuristic is geometry-based and does not rely on color or layer naming
conventions, so it works across dielines from different vendors.
"""

from __future__ import annotations

import math

from ..utils.constants import LineType
from ..utils.geometry import (
    angle_diff,
    bbox,
    point_in_polygon,
    point_segment_distance,
    polygon_area,
    polygon_centroid,
    segment_angle,
)
from .types import ClassifiedLine

# Refinement thresholds.
_GLUE_NEAR_FRACTION = 0.08     # distance to edge as a fraction of the bbox diagonal
_GLUE_PARALLEL_RAD = math.radians(12)
_WINDOW_MAX_AREA_FRACTION = 0.9


def classify(paths):
    """Return a list of ``ClassifiedLine`` for the given dieline paths."""
    if not paths:
        return []

    all_points = [pt for path in paths for pt in path.points]
    min_x, min_y, max_x, max_y = bbox(all_points)
    diagonal = math.hypot(max_x - min_x, max_y - min_y) or 1.0

    closed_paths = [p for p in paths if p.is_closed and len(p.points) >= 3]
    outer = max(closed_paths, key=lambda p: abs(polygon_area(p.points))) if closed_paths else None
    outer_poly = outer.points if outer else None
    outer_area = abs(polygon_area(outer.points)) if outer else 0.0

    results = [
        ClassifiedLine(path=p, line_type=lt, confidence=conf)
        for p in paths
        for lt, conf in (_classify_one(p, outer, outer_poly, outer_area),)
    ]
    _refine_glue_flaps(results, outer_poly, diagonal)
    return results


def _classify_one(path, outer, outer_poly, outer_area):
    if outer is not None and path is outer:
        return LineType.CUT, 0.95

    # Closed shapes lying outside the main die outline are decorative artwork
    # (e.g. an embedded 3D preview), not die geometry.
    if (
        outer_poly is not None
        and path is not outer
        and path.is_closed
        and len(path.points) >= 3
        and not point_in_polygon(polygon_centroid(path.points), outer_poly)
    ):
        return LineType.UNKNOWN, 0.3

    if path.is_closed and len(path.points) >= 3:
        area = abs(polygon_area(path.points))
        if outer_poly is not None:
            centroid = polygon_centroid(path.points)
            if point_in_polygon(centroid, outer_poly) and area < outer_area * _WINDOW_MAX_AREA_FRACTION:
                return LineType.WINDOW, 0.8
        return LineType.CUT, 0.6

    if path.stroke and path.stroke.dashed:
        return LineType.SCORE, 0.75
    return LineType.FOLD, 0.65


def _refine_glue_flaps(results, outer_poly, diagonal):
    if outer_poly is None:
        return
    edges = [
        (outer_poly[i], outer_poly[(i + 1) % len(outer_poly)])
        for i in range(len(outer_poly))
    ]
    near_threshold = diagonal * _GLUE_NEAR_FRACTION

    for line in results:
        if line.line_type is not LineType.FOLD:
            continue
        pts = line.path.points
        if len(pts) < 2:
            continue
        start, end = pts[0], pts[-1]
        mid = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        seg_angle = segment_angle(start, end)

        best_edge = None
        best_dist = float("inf")
        for e0, e1 in edges:
            d = point_segment_distance(mid, e0, e1)
            if d < best_dist:
                best_dist = d
                best_edge = (e0, e1)
        if best_edge is None:
            continue

        edge_angle = segment_angle(best_edge[0], best_edge[1])
        if best_dist < near_threshold and angle_diff(seg_angle, edge_angle) < _GLUE_PARALLEL_RAD:
            line.line_type = LineType.GLUE_FLAP
            line.confidence = 0.6
