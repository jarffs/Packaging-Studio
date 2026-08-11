"""Non-destructive edge finishing for the panel meshes.

Rounds the panel edges with a **Bevel** modifier and offers an optional
**Subdivision Surface**, both as live modifiers so the base panel mesh stays
flat and editable — nothing is baked in.

A classic Bevel modifier is used instead of a Geometry-Nodes bevel because:

* Catmull-Clark subdivision *balloons* these coarse, watertight hard-surface
  panels (the silhouette shrinks ~30 %), so SubD is off by default; and
* Blender 5.2's Nodes modifier no longer exposes inputs to Python, whereas the
  Bevel/Subsurf modifier properties (width, segments, levels) are directly
  drivable from the sidebar sliders.
"""

from __future__ import annotations

from math import radians

BEVEL_MODIFIER = "PS Bevel"
SUBSURF_MODIFIER = "PS SubD"

DEFAULT_BEVEL_WIDTH = 0.0003  # metres (~0.3 mm rounded edge)
DEFAULT_BEVEL_SEGMENTS = 2
DEFAULT_SUBD_LEVEL = 0  # off by default; SubD balloons hard-surface panels

_ANGLE_LIMIT = radians(30.0)


def apply_finish(obj):
    """Ensure the bevel (+ optional subsurf) finishing modifiers exist.

    Applies the safe defaults (bevel on, subsurf off) so a freshly built panel
    looks correct even before the sidebar sliders sync.
    """
    bevel = obj.modifiers.get(BEVEL_MODIFIER)
    if bevel is None or bevel.type != "BEVEL":
        bevel = obj.modifiers.new(BEVEL_MODIFIER, "BEVEL")
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = _ANGLE_LIMIT
    bevel.width = DEFAULT_BEVEL_WIDTH
    bevel.segments = DEFAULT_BEVEL_SEGMENTS

    subsurf = obj.modifiers.get(SUBSURF_MODIFIER)
    if subsurf is None or subsurf.type != "SUBSURF":
        subsurf = obj.modifiers.new(SUBSURF_MODIFIER, "SUBSURF")
    subsurf.levels = DEFAULT_SUBD_LEVEL
    subsurf.render_levels = DEFAULT_SUBD_LEVEL
    subsurf.show_viewport = DEFAULT_SUBD_LEVEL > 0
    subsurf.show_render = DEFAULT_SUBD_LEVEL > 0
    return bevel, subsurf


def set_finish_values(obj, *, enable, width, segments, subd_level):
    """Push the finishing sliders onto one object's modifiers."""
    bevel = obj.modifiers.get(BEVEL_MODIFIER)
    if bevel is not None:
        bevel.width = float(width)
        bevel.segments = int(segments)
        bevel.show_viewport = bool(enable)
        bevel.show_render = bool(enable)
    subsurf = obj.modifiers.get(SUBSURF_MODIFIER)
    if subsurf is not None:
        subsurf.levels = int(subd_level)
        subsurf.render_levels = int(subd_level)
        on = bool(enable) and int(subd_level) > 0
        subsurf.show_viewport = on
        subsurf.show_render = on


def sync_collection(collection, *, enable, width, segments, subd_level):
    """Apply/update the finishing modifiers on every mesh in ``collection``."""
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        apply_finish(obj)
        set_finish_values(
            obj,
            enable=enable,
            width=width,
            segments=segments,
            subd_level=subd_level,
        )
