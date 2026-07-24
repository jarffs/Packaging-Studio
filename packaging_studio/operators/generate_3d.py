"""Generate the 3D box from the last imported dieline."""

from __future__ import annotations

import os

import bpy

from ..core.line_classifier import classify
from ..core.panel_detector import detect_panels
from ..core.pdf_parser import pdf_to_svg
from ..core.svg_parser import parse_svg
from ..mesh.panel_mesh import build_3d


class PACKAGING_OT_generate_3d(bpy.types.Operator):
    """Detect panels from the imported dieline and build a folded 3D box."""

    bl_idname = "packaging_studio.generate_3d"
    bl_label = "Generate 3D Box"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        props = getattr(context.scene, "packaging_studio", None)
        return bool(props and props.source_path)

    def execute(self, context):
        props = context.scene.packaging_studio
        path = props.source_path
        ext = os.path.splitext(path)[1].lower()

        try:
            if ext == ".pdf":
                svg_text = pdf_to_svg(path)
            elif ext == ".svg":
                with open(path, "r", encoding="utf-8") as handle:
                    svg_text = handle.read()
            else:
                self.report({"WARNING"}, "Re-import a valid SVG or PDF first")
                return {"CANCELLED"}
            paths = parse_svg(svg_text)
        except Exception as exc:  # noqa: BLE001 - report any failure
            self.report({"ERROR"}, f"Failed to read dieline: {exc}")
            return {"CANCELLED"}

        classified = classify(paths)
        model = detect_panels(classified)
        if not model.panels:
            self.report(
                {"WARNING"},
                "No closed panels found. Check the cut/fold lines.",
            )
            return {"CANCELLED"}

        name = os.path.splitext(os.path.basename(path))[0]
        box = build_3d(model, name, thickness_mm=props.thickness_mm)
        if box is None:
            self.report({"WARNING"}, "Could not build a fold hierarchy.")
            return {"CANCELLED"}

        props.panel_count = len(model.panels)
        props.box_collection = box.name
        props.fold_root_panel = -1
        _apply_finish(box, props)
        _show_relationship_lines(context)
        self.report(
            {"INFO"},
            f"📦 Built '{name}': {len(model.panels)} panels "
            f"@ {props.thickness_mm:.2f} mm",
        )
        return {"FINISHED"}


def _show_relationship_lines(context):
    """Turn on bone parent (relationship) lines so the fold hierarchy shows."""
    for area in context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.overlay.show_relationship_lines = True


def _apply_finish(box, props):
    """Sync the SubD finishing sliders onto the freshly built panels."""
    from ..mesh.geometry_nodes import sync_collection

    sync_collection(
        box,
        enable=props.subd_enable,
        level=props.subd_level,
        width=props.support_width,
        loops=props.support_loops,
        crease=props.crease_sharpness,
    )
