"""Parse an SVG document into a flat list of ``DielinePath`` polylines.

Uses the Python standard-library XML parser, so the core pipeline has no
third-party dependencies and can be unit-tested with plain Python.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from ..utils.geometry import MAT_IDENTITY, mat_apply, mat_mul, parse_transform
from ..utils.constants import ARC_SAMPLES
from .svg_path import parse_path
from .types import DielinePath, StrokeStyle

_INKSCAPE_LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"

_SKIP_TAGS = {
    "defs", "symbol", "clipPath", "mask", "marker", "pattern",
    "metadata", "title", "desc", "style", "script",
}

_NAMED_COLORS = {
    "black": (0.0, 0.0, 0.0),
    "white": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 0.5, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0),
    "gray": (0.5, 0.5, 0.5),
    "grey": (0.5, 0.5, 0.5),
}

_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_color(value):
    if not value:
        return None
    v = value.strip().lower()
    if v in ("none", "transparent"):
        return None
    if v in _NAMED_COLORS:
        return _NAMED_COLORS[v]
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) >= 6:
            try:
                return (
                    int(h[0:2], 16) / 255.0,
                    int(h[2:4], 16) / 255.0,
                    int(h[4:6], 16) / 255.0,
                )
            except ValueError:
                return None
    if v.startswith("rgb"):
        nums = _NUM.findall(v)
        if len(nums) >= 3:
            def conv(x):
                f = float(x)
                return f / 255.0 if f > 1.0 else f
            return (conv(nums[0]), conv(nums[1]), conv(nums[2]))
    return None


def _style_props(el, inherited):
    props = dict(inherited)
    for key in ("stroke", "stroke-width", "stroke-dasharray", "fill"):
        val = el.get(key)
        if val is not None:
            props[key] = val
    style = el.get("style")
    if style:
        for part in style.split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                props[k.strip()] = v.strip()
    return props


def _stroke_from(props):
    color = _parse_color(props.get("stroke"))
    width = 1.0
    raw_width = props.get("stroke-width")
    if raw_width:
        match = _NUM.findall(raw_width)
        if match:
            width = float(match[0])
    dash = props.get("stroke-dasharray", "none")
    dashed = dash not in (None, "none", "") and any(ch.isdigit() for ch in dash)
    return StrokeStyle(color=color, width=width, dashed=dashed)


def _shape_subpaths(el):
    tag = _local(el.tag)
    if tag == "path":
        d = el.get("d")
        return parse_path(d) if d else []
    if tag == "line":
        x1 = float(el.get("x1", 0)); y1 = float(el.get("y1", 0))
        x2 = float(el.get("x2", 0)); y2 = float(el.get("y2", 0))
        return [([(x1, y1), (x2, y2)], False)]
    if tag in ("polyline", "polygon"):
        nums = [float(x) for x in _NUM.findall(el.get("points", ""))]
        pts = list(zip(nums[0::2], nums[1::2]))
        return [(pts, tag == "polygon")] if len(pts) >= 2 else []
    if tag == "rect":
        x = float(el.get("x", 0)); y = float(el.get("y", 0))
        w = float(el.get("width", 0)); h = float(el.get("height", 0))
        if w <= 0 or h <= 0:
            return []
        return [([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True)]
    if tag in ("circle", "ellipse"):
        cx = float(el.get("cx", 0)); cy = float(el.get("cy", 0))
        if tag == "circle":
            rx = ry = float(el.get("r", 0))
        else:
            rx = float(el.get("rx", 0)); ry = float(el.get("ry", 0))
        if rx <= 0 or ry <= 0:
            return []
        pts = [
            (cx + rx * math.cos(2 * math.pi * k / ARC_SAMPLES),
             cy + ry * math.sin(2 * math.pi * k / ARC_SAMPLES))
            for k in range(ARC_SAMPLES)
        ]
        return [(pts, True)]
    return []


def parse_svg(svg_text):
    """Return a document-ordered list of ``DielinePath`` from SVG text."""
    root = ET.fromstring(svg_text)
    paths = []
    counter = [0]

    def recurse(el, matrix, style, group):
        tag = _local(el.tag)
        if tag in _SKIP_TAGS:
            return
        matrix = mat_mul(matrix, parse_transform(el.get("transform")))
        style = _style_props(el, style)

        if tag == "g":
            gid = el.get("id") or el.get(_INKSCAPE_LABEL) or group
            for child in el:
                recurse(child, matrix, style, gid)
            return

        subs = _shape_subpaths(el)
        if subs:
            # Dieline lines are strokes with ``fill:none``. Filled shapes are
            # artwork (background, 3D previews, logos) and are ignored so they
            # do not pollute classification or panel detection.
            if _parse_color(style.get("fill")) is not None:
                return
            stroke = _stroke_from(style)
            element_id = el.get("id")
            for pts, closed in subs:
                transformed = [mat_apply(matrix, p) for p in pts]
                if len(transformed) >= 2:
                    paths.append(
                        DielinePath(
                            points=transformed,
                            is_closed=closed,
                            stroke=stroke,
                            element_id=element_id,
                            group=group,
                            source_index=counter[0],
                        )
                    )
                    counter[0] += 1
        else:
            for child in el:
                recurse(child, matrix, style, group)

    recurse(root, MAT_IDENTITY, {}, None)
    return paths
