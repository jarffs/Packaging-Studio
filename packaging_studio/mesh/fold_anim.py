"""Bake a :class:`FoldPlan` into pose-bone keyframes on the fold armature.

Each panel bone was built so that folding is a clean rotation about its **local
X axis** (see :mod:`packaging_studio.mesh.armature`). This module inserts two
keyframes per hinge — flat at the step's start frame and folded at its end
frame — and applies the chosen easing to every keyframe.
"""

from __future__ import annotations

import bpy

from .armature import bone_name

# Maps a Packaging Studio easing name to a Blender (interpolation, easing) pair.
_EASING = {
    "LINEAR": ("LINEAR", "AUTO"),
    "SMOOTH": ("BEZIER", "AUTO"),
    "EASE_IN": ("SINE", "EASE_IN"),
    "EASE_OUT": ("SINE", "EASE_OUT"),
    "EASE_IN_OUT": ("SINE", "EASE_IN_OUT"),
    "BOUNCE": ("BOUNCE", "EASE_OUT"),
}


def find_armature(collection):
    """Return the first armature object inside ``collection`` (or ``None``)."""
    if collection is None:
        return None
    for obj in collection.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def animate_fold(collection, plan, easing="SMOOTH"):
    """Keyframe the fold ``plan`` onto the armature in ``collection``.

    Returns the armature object, or ``None`` if no armature/steps are found.
    """
    arm = find_armature(collection)
    if arm is None or not plan.steps:
        return None

    view_layer = bpy.context.view_layer
    prev_active = view_layer.objects.active
    prev_mode = arm.mode
    view_layer.objects.active = arm

    # Clear any previous fold animation so re-running is idempotent.
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data_clear()

    bpy.ops.object.mode_set(mode="POSE")
    try:
        for step in plan.steps:
            pbone = arm.pose.bones.get(bone_name(step.child))
            if pbone is None:
                continue
            pbone.rotation_mode = "XYZ"
            pbone.rotation_euler = (0.0, 0.0, 0.0)
            pbone.keyframe_insert("rotation_euler", index=0, frame=step.start_frame)
            pbone.rotation_euler.x = step.angle
            pbone.keyframe_insert("rotation_euler", index=0, frame=step.end_frame)
    finally:
        bpy.ops.object.mode_set(mode=prev_mode if prev_mode else "OBJECT")
        if prev_active is not None:
            view_layer.objects.active = prev_active

    _apply_easing(arm, easing)
    _set_scene_range(plan)
    return arm


def _iter_fcurves(arm):
    """Yield every fcurve of ``arm``'s action across legacy and slotted APIs."""
    ad = arm.animation_data
    action = ad.action if ad else None
    if action is None:
        return
    # Legacy actions (Blender < 4.4) expose fcurves directly.
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        yield from legacy
        return
    # Slotted actions (Blender 4.4+): fcurves live in channelbags.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                yield from bag.fcurves


def _apply_easing(arm, easing):
    interp, ease = _EASING.get(easing, _EASING["SMOOTH"])
    for fcurve in _iter_fcurves(arm):
        for kp in fcurve.keyframe_points:
            kp.interpolation = interp
            kp.easing = ease
        fcurve.update()


def _set_scene_range(plan):
    scene = bpy.context.scene
    scene.frame_start = plan.frame_start
    scene.frame_end = plan.frame_end
    scene.frame_set(plan.frame_start)
