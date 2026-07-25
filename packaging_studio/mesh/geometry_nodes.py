"""Non-destructive Subdivision-Surface finishing via Geometry Nodes.

Builds a reusable ``PS_SubD_Support`` node group that:

1. bevels the crease edges (selected by the ``ps_fold`` boolean attribute the
   mesh builder writes) to create **support edge loops**, and
2. applies **Subdivision Surface** on top.

Because the support loops only ever exist inside the modifier, the base panel
mesh stays flat and editable — nothing is "baked" into the geometry. The
tunable parameters (SubD level, support width, support loops, crease sharpness)
live on internal value nodes of the shared group and are driven by the sidebar
sliders, so a single change updates every panel live.
"""

from __future__ import annotations

import bpy

GROUP_NAME = "PS_SubD_Support"
MODIFIER_NAME = "PS Finish"

DEFAULT_SUBD_LEVEL = 2
DEFAULT_SUPPORT_WIDTH = 0.0006  # metres (~0.6 mm holding loops)
DEFAULT_SUPPORT_LOOPS = 1
DEFAULT_CREASE = 0.0

# Stable node names used to read/write the tunable parameters on the group.
# Blender 5.2's Nodes modifier dropped the ``modifier[socket_id]`` IDProperty
# API, so parameters live on internal value nodes of the shared group instead.
NODE_LEVEL = "PS_Level"
NODE_WIDTH = "PS_Width"
NODE_LOOPS = "PS_Loops"
NODE_CREASE = "PS_Crease"

_GEOMETRY = "Geometry"


def ensure_subd_support_group():
    """Return the ``PS_SubD_Support`` node group, building it once if missing."""
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is not None:
        return group

    group = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")
    group.interface.new_socket(
        _GEOMETRY, in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    group.interface.new_socket(
        _GEOMETRY, in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    _build_nodes(group)
    return group


def _build_nodes(group):
    nodes = group.nodes
    links = group.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-700, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (700, 0)

    fold_attr = nodes.new("GeometryNodeInputNamedAttribute")
    fold_attr.location = (-700, -240)
    fold_attr.data_type = "BOOLEAN"
    fold_attr.inputs["Name"].default_value = "ps_fold"

    level = nodes.new("FunctionNodeInputInt")
    level.name = NODE_LEVEL
    level.location = (-100, 220)
    level.integer = DEFAULT_SUBD_LEVEL

    width = nodes.new("ShaderNodeValue")
    width.name = NODE_WIDTH
    width.location = (-460, -160)
    width.outputs[0].default_value = DEFAULT_SUPPORT_WIDTH

    loops = nodes.new("FunctionNodeInputInt")
    loops.name = NODE_LOOPS
    loops.location = (-460, -320)
    loops.integer = DEFAULT_SUPPORT_LOOPS

    crease = nodes.new("ShaderNodeValue")
    crease.name = NODE_CREASE
    crease.location = (-460, -460)
    crease.outputs[0].default_value = DEFAULT_CREASE

    bevel = nodes.new("GeometryNodeMeshBevel")
    bevel.location = (-200, 0)
    _set_menu(bevel.inputs.get("Affect Kind"), "EDGES")

    crease_mul = nodes.new("ShaderNodeMath")
    crease_mul.location = (100, -420)
    crease_mul.operation = "MULTIPLY"

    subd = nodes.new("GeometryNodeSubdivisionSurface")
    subd.location = (300, 0)
    _set_menu(subd.inputs.get("Boundary Smooth"), "PRESERVE_CORNERS")

    # Bevel the crease edges to create the support loops.
    links.new(group_in.outputs[_GEOMETRY], bevel.inputs["Mesh"])
    links.new(fold_attr.outputs["Attribute"], bevel.inputs["Selection"])
    links.new(width.outputs["Value"], bevel.inputs["Offset"])
    links.new(loops.outputs["Integer"], bevel.inputs["Segments"])

    # Optional edge crease on the fold edges: ps_fold * Crease Sharpness.
    links.new(fold_attr.outputs["Attribute"], crease_mul.inputs[0])
    links.new(crease.outputs["Value"], crease_mul.inputs[1])

    # Subdivide the beveled mesh.
    links.new(bevel.outputs["Mesh"], subd.inputs["Mesh"])
    links.new(level.outputs["Integer"], subd.inputs["Level"])
    links.new(crease_mul.outputs["Value"], subd.inputs["Edge Crease"])

    links.new(subd.outputs["Mesh"], group_out.inputs[_GEOMETRY])


def _set_menu(socket, identifier):
    """Best-effort assignment of a menu-socket default (ignores API drift)."""
    if socket is None:
        return
    try:
        socket.default_value = identifier
    except (TypeError, AttributeError):
        pass


def set_group_values(group, *, level, width, loops, crease):
    """Write the finishing parameters onto the shared group's value nodes."""
    node = group.nodes.get(NODE_LEVEL)
    if node is not None:
        node.integer = int(level)
    node = group.nodes.get(NODE_WIDTH)
    if node is not None:
        node.outputs[0].default_value = float(width)
    node = group.nodes.get(NODE_LOOPS)
    if node is not None:
        node.integer = int(loops)
    node = group.nodes.get(NODE_CREASE)
    if node is not None:
        node.outputs[0].default_value = float(crease)


def apply_subd_support(obj):
    """Add (or fetch) the finishing modifier on ``obj`` and return it."""
    group = ensure_subd_support_group()
    mod = obj.modifiers.get(MODIFIER_NAME)
    if mod is None or mod.type != "NODES":
        mod = obj.modifiers.new(MODIFIER_NAME, "NODES")
    mod.node_group = group
    return mod


def sync_collection(collection, *, enable, level, width, loops, crease):
    """Apply/update the finishing modifier on every mesh in ``collection``."""
    group = ensure_subd_support_group()
    set_group_values(group, level=level, width=width, loops=loops, crease=crease)
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        mod = apply_subd_support(obj)
        mod.show_viewport = bool(enable)
        mod.show_render = bool(enable)

