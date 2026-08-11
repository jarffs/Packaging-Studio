"""Animate the folding of the generated 3D box."""

from __future__ import annotations

import math
import os

import bpy

from ..core.fold_solver import build_fold_plan
from ..core.line_classifier import classify
from ..core.panel_detector import detect_panels
from ..core.pdf_parser import pdf_to_svg
from ..core.svg_parser import parse_svg
from ..core.topology import build_topology
from ..mesh.armature import rebuild_bones
from ..mesh.fold_anim import animate_fold, find_armature


def _load_model(path):
    """Re-read the dieline at ``path`` into a :class:`PanelModel`."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        svg_text = pdf_to_svg(path)
    elif ext == ".svg":
        with open(path, "r", encoding="utf-8") as handle:
            svg_text = handle.read()
    else:
        return None
    return detect_panels(classify(parse_svg(svg_text)))


def reroot_rig(props):
    """Re-root the fold rig on ``props.fold_root_panel`` (-1 = largest panel).

    Used by the base-panel menu so choosing a panel re-roots the armature in
    place. Bone names stay ``panel_{index}`` so the mesh vertex groups still
    bind; only the hierarchy and bone placement change.
    """
    collection = bpy.data.collections.get(props.box_collection)
    if collection is None or not props.source_path:
        return
    try:
        model = _load_model(props.source_path)
    except Exception:  # noqa: BLE001 - best-effort live update
        return
    if not model or not model.panels:
        return
    arm = find_armature(collection)
    if arm is None:
        return
    root = props.fold_root_panel if props.fold_root_panel >= 0 else None
    rebuild_bones(arm, model, build_topology(model, root=root))


class PACKAGING_OT_animate_fold(bpy.types.Operator):
    """Keyframe the box folding up from its flat dieline into a closed box."""

    bl_idname = "packaging_studio.animate_fold"
    bl_label = "Animate Fold"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        props = getattr(context.scene, "packaging_studio", None)
        if not (props and props.source_path and props.box_collection):
            return False
        return props.box_collection in bpy.data.collections

    def execute(self, context):
        props = context.scene.packaging_studio
        collection = bpy.data.collections.get(props.box_collection)
        if collection is None:
            self.report({"WARNING"}, "Generate the 3D box first")
            return {"CANCELLED"}

        try:
            model = _load_model(props.source_path)
        except Exception as exc:  # noqa: BLE001 - report any failure
            self.report({"ERROR"}, f"Failed to read dieline: {exc}")
            return {"CANCELLED"}
        if model is None or not model.panels:
            self.report({"WARNING"}, "Re-import a valid SVG or PDF first")
            return {"CANCELLED"}

        root = props.fold_root_panel if props.fold_root_panel >= 0 else None
        topology = build_topology(model, root=root)
        if topology.root < 0:
            self.report({"WARNING"}, "Could not resolve a fold hierarchy")
            return {"CANCELLED"}

        # Re-root the rig so the chosen base stays static before keyframing.
        arm = find_armature(collection)
        if arm is not None:
            rebuild_bones(arm, model, topology)

        plan = build_fold_plan(
            topology,
            angle=math.radians(props.fold_angle_deg),
            frames_per_fold=props.fold_frames,
            cascade_offset=props.fold_cascade,
        )
        arm = animate_fold(collection, plan, easing=props.fold_easing)
        if arm is None:
            self.report({"WARNING"}, "No armature to animate")
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"🎬 Animated {len(plan.steps)} folds from base {topology.root} "
            f"(frames {plan.frame_start}–{plan.frame_end})",
        )
        return {"FINISHED"}
