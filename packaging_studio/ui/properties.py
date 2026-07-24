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

