"""Sidebar (N-panel) UI for Packaging Studio."""

from __future__ import annotations

import bpy


class PACKAGING_PT_main(bpy.types.Panel):
    bl_label = "Packaging Studio"
    bl_idname = "PACKAGING_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Packaging"

    def draw(self, context):
        layout = self.layout
        props = context.scene.packaging_studio

        col = layout.column(align=True)
        col.operator("packaging_studio.import_dieline", icon="IMPORT")

        if not props.source_file:
            layout.label(text="Import an SVG or PDF dieline.", icon="INFO")
            return

        box = layout.box()
        box.label(text=props.source_file, icon="FILE")
        box.label(text=f"Paths: {props.total_paths}")
        box.label(text=f"Size: {props.width_units:.1f} x {props.height_units:.1f}")

        stats = box.column(align=True)
        stats.label(text=f"Cut: {props.cut_count}")
        stats.label(text=f"Fold: {props.fold_count}")
        stats.label(text=f"Score: {props.score_count}")
        stats.label(text=f"Glue flap: {props.glue_count}")
        stats.label(text=f"Window: {props.window_count}")
        if props.unknown_count:
            stats.label(text=f"Unknown: {props.unknown_count}", icon="ERROR")

        box.label(text=f"Avg confidence: {props.avg_confidence * 100:.0f}%")

        gen = layout.box()
        gen.label(text="3D Model", icon="MESH_CUBE")
        gen.prop(props, "thickness_mm")
        gen.operator("packaging_studio.generate_3d", icon="MOD_SOLIDIFY")
        if props.panel_count:
            gen.label(text=f"Panels: {props.panel_count}")

        if props.box_collection:
            anim = layout.box()
            anim.label(text="Animation", icon="ARMATURE_DATA")

            base = anim.column(align=True)
            if props.fold_root_panel >= 0:
                base.label(text=f"Base panel: {props.fold_root_panel}", icon="PINNED")
            else:
                base.label(text="Base panel: Auto (largest)", icon="AUTO")
            row = base.row(align=True)
            row.operator("packaging_studio.set_fold_base", icon="PINNED")
            row.operator("packaging_studio.clear_fold_base", icon="X", text="")

            anim.prop(props, "fold_angle_deg")
            row = anim.row(align=True)
            row.prop(props, "fold_frames")
            row.prop(props, "fold_cascade")
            anim.prop(props, "fold_easing")
            anim.operator("packaging_studio.animate_fold", icon="PLAY")
