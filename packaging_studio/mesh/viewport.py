"""Build colored Blender curve objects to visualize a classified dieline."""

from __future__ import annotations

import bpy

from ..utils.constants import LINE_COLORS, VIEWPORT_SCALE, LineType


def _material(line_type):
    """Return a cached material tinted for the given line type."""
    name = f"PS_{line_type.value}"
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat

    mat = bpy.data.materials.new(name)
    color = LINE_COLORS[line_type]
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color
            bsdf.inputs["Emission Strength"].default_value = 1.0
    mat["packaging_studio"] = True
    return mat


def build_dieline(classified, name):
    """Create a collection of curve objects, one per classified line.

    Returns the created collection.
    """
    collection = bpy.data.collections.new(f"Dieline_{name}")
    bpy.context.scene.collection.children.link(collection)
    bevel = VIEWPORT_SCALE * 0.5

    for index, line in enumerate(classified):
        pts = line.path.points
        if len(pts) < 2:
            continue

        curve = bpy.data.curves.new(f"{line.line_type.value}_{index}", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = bevel
        curve.fill_mode = "FULL"

        spline = curve.splines.new("POLY")
        spline.points.add(len(pts) - 1)
        for j, (x, y) in enumerate(pts):
            spline.points[j].co = (x * VIEWPORT_SCALE, -y * VIEWPORT_SCALE, 0.0, 1.0)
        spline.use_cyclic_u = line.path.is_closed

        curve.materials.append(_material(line.line_type))

        obj = bpy.data.objects.new(f"{line.line_type.value}_{index}", curve)
        obj["ps_line_type"] = line.line_type.value
        obj["ps_confidence"] = round(float(line.confidence), 3)
        obj.color = LINE_COLORS[line.line_type]
        collection.objects.link(obj)

    _show_object_colors()
    return collection


def _show_object_colors():
    """Switch every 3D viewport's Solid shading to color-by-object.

    Without this, Blender's default Solid shading renders all objects in a
    uniform clay color, hiding the per-line classification colors.
    """
    window_manager = bpy.context.window_manager
    if window_manager is None:
        return
    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.color_type = "OBJECT"

