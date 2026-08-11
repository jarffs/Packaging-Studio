"""Build the solid 3D box mesh from a detected :class:`PanelModel`.

All panels are welded into a **single connected mesh object**: adjacent panels
share their crease vertices, and each crease edge is beveled to bake in
**support loops** (the "vincos") that keep the fold clean under smoothing. Every
vertex is weighted to the fold bone(s) of the panel(s) it belongs to via
``panel_{index}`` vertex groups — crease vertices are shared between two panels,
so their blended weights make a smooth hinge while the single Armature modifier
folds the whole box. The mesh is intentionally **quad-only, never triangulated**.
"""

from __future__ import annotations

from collections import defaultdict

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
from .finishing import apply_finish

# Bevel segments used to bake the crease support loops.
_CREASE_SEGMENTS = 2


def build_3d(model, name, thickness_mm=0.3, crease_width_mm=1.5):
    """Create a collection with the rigged 3D box and return it."""
    topology = build_topology(model)
    if topology.root < 0:
        return None

    s = VIEWPORT_SCALE
    thickness_m = thickness_mm * s
    crease_m = crease_width_mm * s
    box = bpy.data.collections.new(f"Box_{name}")
    bpy.context.scene.collection.children.link(box)

    arm_obj, bone_names = build_armature(model, topology, name, box)

    bounds = bbox(model.vertices) if model.vertices else (0.0, 0.0, 1.0, 1.0)

    obj, vert_panels = _build_box_object(model, thickness_m, crease_m, s, bounds, name)
    box.objects.link(obj)
    _rig_box(obj, arm_obj, bone_names, vert_panels)
    apply_finish(obj)

    material = _material(name)
    if material is not None:
        obj.data.materials.append(material)

    return box


def _xy_key(co, scale):
    """Stable dieline-space key for a vertex (Z is dropped by Solidify)."""
    return (round(co.x / scale, 3), round(-co.y / scale, 3))


def _point_in_poly(x, y, poly):
    inside = False
    count = len(poly)
    j = count - 1
    for i in range(count):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def _panel_at(dx, dy, polys, centroids):
    """Return the index of the panel whose polygon contains ``(dx, dy)``."""
    for index, poly in polys.items():
        if _point_in_poly(dx, dy, poly):
            return index
    return min(
        centroids,
        key=lambda k: (centroids[k][0] - dx) ** 2 + (centroids[k][1] - dy) ** 2,
    )


def _build_box_object(model, thickness_m, crease_m, scale, bounds, name):
    """Build the connected box mesh and map each vertex to its panel(s)."""
    bm = bmesh.new()
    type_layer = bm.edges.layers.int.new("ps_edge_type")

    vmap = {}

    def _vert(index):
        vert = vmap.get(index)
        if vert is None:
            vert = bm.verts.new(
                (model.vertices[index][0] * scale, -model.vertices[index][1] * scale, 0.0)
            )
            vmap[index] = vert
        return vert

    for panel in model.panels:
        ring = [_vert(i) for i in panel.loop]
        try:
            bm.faces.new(ring)
        except ValueError:
            pass  # a coincident face already exists for this loop
        count = len(panel.loop)
        for i in range(count):
            edge = bm.edges.get((ring[i], ring[(i + 1) % count]))
            if edge is None:
                continue
            key = frozenset((panel.loop[i], panel.loop[(i + 1) % count]))
            edge[type_layer] = EDGE_TYPE_CODES.get(model.edge_types.get(key), 0)

    # Bake the support loops ("vincos") parallel to every crease.
    fold_edges = [edge for edge in bm.edges if edge[type_layer] in FOLD_EDGE_CODES]
    if crease_m > 0.0 and fold_edges:
        bmesh.ops.bevel(
            bm,
            geom=fold_edges,
            offset=crease_m,
            offset_type="OFFSET",
            segments=_CREASE_SEGMENTS,
            profile=0.5,
            affect="EDGES",
        )

    # Resolve panel ownership per vertex (crease vertices belong to two panels).
    polys = {p.index: [model.vertices[i] for i in p.loop] for p in model.panels}
    centroids = {p.index: p.centroid for p in model.panels}
    xy_owner = {}
    for face in bm.faces:
        center = face.calc_center_median()
        panel = _panel_at(center.x / scale, -center.y / scale, polys, centroids)
        for vert in face.verts:
            xy_owner.setdefault(_xy_key(vert.co, scale), set()).add(panel)

    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thickness_m)
    bm.normal_update()

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    _mark_edges(mesh)
    _assign_uv(mesh, scale, bounds)
    obj = bpy.data.objects.new(name, mesh)

    vert_panels = {}
    for vertex in mesh.vertices:
        panels = xy_owner.get(_xy_key(vertex.co, scale))
        if panels:
            vert_panels[vertex.index] = panels
    return obj, vert_panels


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


def _rig_box(obj, arm_obj, bone_names, vert_panels):
    """Weight every vertex to its panel bone(s) and add one Armature modifier."""
    per_bone = defaultdict(list)
    for vert_index, panels in vert_panels.items():
        for panel_index in panels:
            bone = bone_names.get(panel_index)
            if bone is not None:
                per_bone[bone].append(vert_index)

    for bone, vert_ids in per_bone.items():
        group = obj.vertex_groups.new(name=bone)
        group.add(vert_ids, 1.0, "REPLACE")

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
