"""Build a fold armature: one bone per panel, hinged on the shared fold edge.

Each child bone's **head sits on the fold crease** (edge midpoint) and its tail
points **into the panel** (toward the panel centroid). The roll is set so the
bone's local **X axis runs along the crease**, which makes folding a clean
rotation about that single local axis. Bone parenting follows the BFS fold
hierarchy so folding a parent carries its children along.
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from ..utils.constants import VIEWPORT_SCALE


def bone_name(index: int) -> str:
    return f"panel_{index}"


def _p3(x, y, s):
    """Dieline (mm, y-down) point to Blender world coords."""
    return Vector((x * s, -y * s, 0.0))


def build_armature(model, topology, name, collection):
    """Create an armature for ``topology`` and return ``(object, {panel: bone})``."""
    arm_data = bpy.data.armatures.new(f"Rig_{name}")
    arm_obj = bpy.data.objects.new(f"Rig_{name}", arm_data)
    collection.objects.link(arm_obj)

    names = _populate_bones(arm_obj, model, topology)

    # Make the fold hierarchy easy to read in the viewport.
    arm_data.show_names = True
    arm_data.display_type = "OCTAHEDRAL"
    arm_obj.show_in_front = True

    return arm_obj, names


def rebuild_bones(arm_obj, model, topology):
    """Re-create ``arm_obj``'s bones for a new ``topology`` (e.g. a new base).

    Bone names stay ``panel_{index}`` so mesh vertex-group bindings are kept;
    only the head/tail placement and parent hierarchy change to re-root the rig
    on ``topology.root``. Any existing pose animation is cleared.
    """
    if arm_obj.animation_data and arm_obj.animation_data.action:
        arm_obj.animation_data_clear()
    return _populate_bones(arm_obj, model, topology, clear=True)


def _populate_bones(arm_obj, model, topology, clear=False):
    """(Re)build the edit bones of ``arm_obj`` from ``topology``."""
    s = VIEWPORT_SCALE
    root_len = s * 30.0  # 30 mm marker bone for panels without a hinge
    min_len = s * 10.0
    arm_data = arm_obj.data

    view_layer = bpy.context.view_layer
    prev_active = view_layer.objects.active
    view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = arm_data.edit_bones
    if clear:
        for bone in list(edit_bones):
            edit_bones.remove(bone)

    bones = {}
    panel_by_index = {p.index: p for p in model.panels}

    def centroid3(index):
        cx, cy = panel_by_index[index].centroid
        return _p3(cx, cy, s)

    # Root panel: marker bone at its centroid (no fold).
    root_c = centroid3(topology.root)
    root = edit_bones.new(bone_name(topology.root))
    root.head = root_c
    root.tail = root_c + Vector((0.0, -root_len, 0.0))
    root.align_roll(Vector((0.0, 0.0, 1.0)))
    bones[topology.root] = root

    for joint in topology.joints:
        (x1, y1), (x2, y2) = joint.axis
        h1 = _p3(x1, y1, s)
        h2 = _p3(x2, y2, s)
        mid = (h1 + h2) * 0.5

        into = centroid3(joint.child) - mid
        into.z = 0.0
        if into.length < 1e-6:
            edge = h2 - h1
            into = Vector((-edge.y, edge.x, 0.0))
        length = max(into.length, min_len)
        into.normalize()

        bone = edit_bones.new(bone_name(joint.child))
        bone.head = mid
        bone.tail = mid + into * length
        bone.use_connect = False
        bone.parent = bones.get(joint.parent)
        # Local X along the crease -> folding is a rotation about local X.
        bone.align_roll(Vector((0.0, 0.0, 1.0)))
        bones[joint.child] = bone

    # Panels not reached from the root (disconnected components) still need a
    # bone so every mesh can be rigged.
    for panel in model.panels:
        if panel.index in bones:
            continue
        c = centroid3(panel.index)
        bone = edit_bones.new(bone_name(panel.index))
        bone.head = c
        bone.tail = c + Vector((0.0, -root_len, 0.0))
        bone.align_roll(Vector((0.0, 0.0, 1.0)))
        bones[panel.index] = bone

    bpy.ops.object.mode_set(mode="OBJECT")
    if prev_active is not None:
        view_layer.objects.active = prev_active

    return {index: bone_name(index) for index in bones}
