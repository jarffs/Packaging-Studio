"""Packaging Studio — turn packaging dielines into render-ready 3D models.

The package ``__init__`` intentionally avoids importing ``bpy`` (or any
Blender-dependent submodule) at module load time. Registration imports those
lazily so the dependency-free ``core`` and ``utils`` subpackages can be
unit-tested with plain Python outside of Blender.
"""

from __future__ import annotations

bl_info = {
    "name": "Packaging Studio",
    "author": "jarffs",
    "version": (0, 5, 0),
    "blender": (4, 2, 0),
    "location": "File > Import > Dieline (SVG/PDF); View3D > Sidebar > Packaging",
    "description": "Turn packaging dielines into render-ready 3D models",
    "category": "Import-Export",
}

_registered_classes = []


def register():
    import bpy

    from .operators import animate_fold, generate_3d, import_dieline
    from .ui import panels, properties

    global _registered_classes
    _registered_classes = [
        properties.PackagingStudioProperties,
        import_dieline.PACKAGING_OT_import_dieline,
        generate_3d.PACKAGING_OT_generate_3d,
        animate_fold.PACKAGING_OT_animate_fold,
        panels.PACKAGING_PT_main,
    ]
    for cls in _registered_classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.packaging_studio = bpy.props.PointerProperty(
        type=properties.PackagingStudioProperties
    )
    bpy.types.TOPBAR_MT_file_import.append(import_dieline.menu_func_import)


def unregister():
    import bpy

    from .operators import import_dieline

    bpy.types.TOPBAR_MT_file_import.remove(import_dieline.menu_func_import)
    if hasattr(bpy.types.Scene, "packaging_studio"):
        del bpy.types.Scene.packaging_studio

    for cls in reversed(_registered_classes):
        bpy.utils.unregister_class(cls)
    _registered_classes.clear()


if __name__ == "__main__":
    register()
