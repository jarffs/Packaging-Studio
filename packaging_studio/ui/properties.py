"""Scene-level properties that store the last imported dieline's statistics."""

from __future__ import annotations

import bpy


def _sync_finish(self, context):
    """Push the edge finishing sliders onto every panel modifier live."""
    collection = bpy.data.collections.get(self.box_collection)
    if collection is None:
        return
    from ..mesh.finishing import sync_collection

    sync_collection(
        collection,
        enable=self.finish_enable,
        width=self.bevel_width,
        segments=self.bevel_segments,
        subd_level=self.subd_level,
    )


# Kept referenced so Blender doesn't free the dynamic enum item strings.
_fold_base_items = [("-1", "Auto (largest)", "Use the largest panel as the base")]


def _fold_base_enum(self, context):
    items = [("-1", "Auto (largest)", "Use the largest panel as the static base")]
    for index in range(self.panel_count):
        items.append((str(index), f"Panel {index}", f"Panel {index} stays static"))
    _fold_base_items[:] = items
    return _fold_base_items


def _fold_base_update(self, context):
    """Sync the numeric base index and re-root the rig on the chosen panel."""
    self.fold_root_panel = int(self.fold_base)
    from ..operators.animate_fold import reroot_rig

    reroot_rig(self)


class PackagingStudioProperties(bpy.types.PropertyGroup):
    source_file: bpy.props.StringProperty(name="Source", default="")
    source_path: bpy.props.StringProperty(name="Source path", default="", subtype="FILE_PATH")
    total_paths: bpy.props.IntProperty(name="Paths", default=0)
    cut_count: bpy.props.IntProperty(name="Cut", default=0)
    fold_count: bpy.props.IntProperty(name="Fold", default=0)
    score_count: bpy.props.IntProperty(name="Score", default=0)
    glue_count: bpy.props.IntProperty(name="Glue", default=0)
    window_count: bpy.props.IntProperty(name="Window", default=0)
    unknown_count: bpy.props.IntProperty(name="Unknown", default=0)
    avg_confidence: bpy.props.FloatProperty(name="Avg confidence", default=0.0)
    width_units: bpy.props.FloatProperty(name="Width", default=0.0)
    height_units: bpy.props.FloatProperty(name="Height", default=0.0)

    thickness_mm: bpy.props.FloatProperty(
        name="Thickness (mm)",
        description="Material thickness used when generating the 3D model",
        default=0.3,
        min=0.01,
        max=20.0,
        soft_max=5.0,
    )
    crease_width_mm: bpy.props.FloatProperty(
        name="Crease Width (mm)",
        description="Width of the baked support loops along each fold (0 = none)",
        default=1.5,
        min=0.0,
        soft_max=5.0,
        max=20.0,
    )
    panel_count: bpy.props.IntProperty(name="Panels", default=0)
    box_collection: bpy.props.StringProperty(name="Box collection", default="")
    fold_root_panel: bpy.props.IntProperty(
        name="Base Panel",
        description="Panel index that stays static; -1 uses the largest panel",
        default=-1,
    )
    fold_base: bpy.props.EnumProperty(
        name="Base Panel",
        description="Which panel stays static while the rest fold around it",
        items=_fold_base_enum,
        update=_fold_base_update,
    )

    fold_angle_deg: bpy.props.FloatProperty(
        name="Fold Angle",
        description="Target fold angle for each hinge, in degrees",
        default=90.0,
        min=0.0,
        max=180.0,
    )
    fold_frames: bpy.props.IntProperty(
        name="Frames / Fold",
        description="How many frames each hinge takes to fold",
        default=20,
        min=1,
        soft_max=120,
    )
    fold_cascade: bpy.props.IntProperty(
        name="Cascade Offset",
        description="Frame delay added per hierarchy level for the cascade effect",
        default=5,
        min=0,
        soft_max=60,
    )
    fold_easing: bpy.props.EnumProperty(
        name="Easing",
        description="Interpolation used for the fold animation",
        items=[
            ("LINEAR", "Linear", "Constant speed"),
            ("SMOOTH", "Smooth", "Bezier ease in and out"),
            ("EASE_IN", "Ease In", "Start slow"),
            ("EASE_OUT", "Ease Out", "End slow"),
            ("EASE_IN_OUT", "Ease In-Out", "Slow at both ends"),
            ("BOUNCE", "Bounce", "Bounce at the end"),
        ],
        default="SMOOTH",
    )

    finish_enable: bpy.props.BoolProperty(
        name="Edge Finish",
        description="Non-destructive rounded-edge bevel (and optional Subdivision Surface)",
        default=True,
        update=_sync_finish,
    )
    bevel_width: bpy.props.FloatProperty(
        name="Edge Round",
        description="Bevel width that rounds the panel edges",
        default=0.0003,
        min=0.0,
        soft_max=0.003,
        max=0.02,
        subtype="DISTANCE",
        update=_sync_finish,
    )
    bevel_segments: bpy.props.IntProperty(
        name="Round Segments",
        description="Bevel segments (higher = smoother rounded edge)",
        default=2,
        min=1,
        max=8,
        update=_sync_finish,
    )
    subd_level: bpy.props.IntProperty(
        name="SubD Level",
        description="Optional Subdivision Surface level (0 = off; note: SubD "
        "rounds and shrinks these hard-surface panels)",
        default=0,
        min=0,
        soft_max=3,
        max=6,
        update=_sync_finish,
    )

