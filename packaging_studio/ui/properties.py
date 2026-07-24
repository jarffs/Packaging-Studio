"""Scene-level properties that store the last imported dieline's statistics."""

from __future__ import annotations

import bpy


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
    panel_count: bpy.props.IntProperty(name="Panels", default=0)
    box_collection: bpy.props.StringProperty(name="Box collection", default="")

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

