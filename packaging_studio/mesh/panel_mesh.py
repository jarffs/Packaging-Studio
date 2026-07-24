"""Build the solid 3D box mesh from a detected :class:`PanelModel`.

Each panel becomes a separate solid object made of an n-gon face extruded to
the material thickness. Solidify produces quad side walls and n-gon caps — the
mesh is intentionally **quad-only, never triangulated**. Panels are rigged to a
fold armature via a single full-weight vertex group each, so they fold cleanly
in later phases.
"""

from __future__ import annotations

import bmesh
import bpy

from ..core.topology import build_topology
from ..utils.constants import (
    CUT_EDGE_CODES,
    EDGE_TYPE_CODES,
    FOLD_EDGE_CODES,
    VIEWPORT_SCALE,
)
from ..utils.geometry import bbox
from .armature import build_armature
from .geometry_nodes import apply_subd_support


def build_3d(model, name, thickness_mm=0.3):
    """Create a collection with the rigged 3D box and return it."""
    topology = build_topology(model)
    if topology.root < 0:
        return None

    s = VIEWPORT_SCALE
    thickness_m = thickness_mm * s
    box = bpy.data.collections.new(f"Box_{name}")
    bpy.context.scene.collection.children.link(box)

    arm_obj, bone_names = build_armature(model, topology, name, box)

    bounds = bbox(model.vertices) if model.vertices else (0.0, 0.0, 1.0, 1.0)
    material = _material(name)

    for panel in model.panels:
        obj = _build_panel_object(
            panel, model.vertices, model.edge_types, thickness_m, s, bounds, name
        )
        box.objects.link(obj)
        _rig_panel(obj, arm_obj, bone_names[panel.index])
        apply_subd_support(obj)
        if material is not None:
            obj.data.materials.append(material)

    return box


def _build_panel_object(panel, vertices, edge_types, thickness_m, scale, bounds, name):
    bm = bmesh.new()
    ring = [
        bm.verts.new((vertices[i][0] * scale, -vertices[i][1] * scale, 0.0))
        for i in panel.loop
    ]
    face = bm.faces.new(ring)

    type_layer = bm.edges.layers.int.new("ps_edge_type")
    count = len(panel.loop)
    for i in range(count):
        edge = bm.edges.get((ring[i], ring[(i + 1) % count]))
        if edge is None:
            continue
        key = frozenset((panel.loop[i], panel.loop[(i + 1) % count]))
        edge[type_layer] = EDGE_TYPE_CODES.get(edge_types.get(key), 0)

    bmesh.ops.solidify(bm, geom=[face], thickness=thickness_m)
    bm.normal_update()

    mesh = bpy.data.meshes.new(f"{name}_panel_{panel.index}")
    bm.to_mesh(mesh)
    bm.free()

    _mark_edges(mesh)
    _assign_uv(mesh, scale, bounds)
    return bpy.data.objects.new(f"{name}_panel_{panel.index}", mesh)


def _mark_edges(mesh):
    """Add ``ps_fold`` / ``ps_cut`` boolean edge attributes for Geometry Nodes.

    Derived from the ``ps_edge_type`` integer attribute so a non-destructive
    bevel node group can select creases or the cut silhouette by name.
    """
    type_attr = mesh.attributes.get("ps_edge_type")
    if type_attr is None:
        return
    codes = [item.value for item in type_attr.data]
    fold_attr = mesh.attributes.new("ps_fold", "BOOLEAN", "EDGE")
    cut_attr = mesh.attributes.new("ps_cut", "BOOLEAN", "EDGE")
    for i, code in enumerate(codes):
        fold_attr.data[i].value = code in FOLD_EDGE_CODES
        cut_attr.data[i].value = code in CUT_EDGE_CODES



def _assign_uv(mesh, scale, bounds):
    min_x, min_y, max_x, max_y = bounds
    span_x = (max_x - min_x) or 1.0
    span_y = (max_y - min_y) or 1.0
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        co = mesh.vertices[loop.vertex_index].co
        u = (co.x / scale - min_x) / span_x
        v = (-co.y / scale - min_y) / span_y
        uv_layer.data[loop.index].uv = (u, v)


def _rig_panel(obj, arm_obj, bone):
    group = obj.vertex_groups.new(name=bone)
    group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    modifier = obj.modifiers.new("Fold", "ARMATURE")
    modifier.object = arm_obj
    obj.parent = arm_obj


def _material(name):
    mat_name = "PS_Cardboard"
    mat = bpy.data.materials.get(mat_name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(mat_name)
    mat.diffuse_color = (0.78, 0.65, 0.45, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.78, 0.65, 0.45, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.9
    mat["packaging_studio"] = True
    return mat
