"""Shared constants for Packaging Studio (independent of Blender)."""

from __future__ import annotations

from enum import Enum


class LineType(Enum):
    """Classification categories for dieline geometry."""

    CUT = "cut"
    FOLD = "fold"
    SCORE = "score"
    GLUE_FLAP = "glue_flap"
    WINDOW = "window"
    UNKNOWN = "unknown"


# RGBA viewport colors used to visualize each line type.
LINE_COLORS = {
    LineType.CUT: (1.0, 0.0, 0.0, 1.0),        # red
    LineType.FOLD: (0.0, 0.4, 1.0, 1.0),       # blue
    LineType.SCORE: (1.0, 0.8, 0.0, 1.0),      # yellow
    LineType.GLUE_FLAP: (0.0, 0.8, 0.2, 1.0),  # green
    LineType.WINDOW: (0.6, 0.0, 0.8, 1.0),     # purple
    LineType.UNKNOWN: (0.5, 0.5, 0.5, 1.0),    # gray
}

# SVG user-unit table (90 dpi, matches Blender's io_curve_svg importer).
SVG_DPI = 90.0
SVG_UNITS = {
    "": 1.0,
    "px": 1.0,
    "in": 90.0,
    "mm": 90.0 / 25.4,
    "cm": 90.0 / 2.54,
    "pt": 1.25,
    "pc": 15.0,
    "em": 1.0,
    "ex": 1.0,
}

# Viewport scale: dieline user units are assumed to be millimeters, mapped to
# Blender meters (1 unit = 1 mm). Real-unit handling arrives in Phase 2.
VIEWPORT_SCALE = 0.001

# Material thickness presets (millimeters).
MATERIAL_PRESETS = {
    "CARDBOARD": 0.3,     # folding carton
    "CORRUGATED": 3.0,    # corrugated board
    "MICRO_FLUTE": 1.5,   # micro-flute
}
DEFAULT_THICKNESS_MM = 0.3

# Curve flattening resolution for beziers and arcs.
BEZIER_SAMPLES = 16
ARC_SAMPLES = 24
