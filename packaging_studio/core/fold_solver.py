"""Plan the fold animation of a box from its :class:`Topology`.

Pure Python (no Blender). The solver turns the fold hierarchy into an ordered
list of :class:`FoldStep` entries — one per hinge — each carrying the target
fold angle and the frame window in which that panel folds. Deeper panels fold
later so the box assembles in a cascade from the root outward.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from .types import Topology

DEFAULT_FOLD_ANGLE = math.radians(90.0)
DEFAULT_FRAME_START = 1
DEFAULT_FRAMES_PER_FOLD = 20
DEFAULT_CASCADE_OFFSET = 5


@dataclass
class FoldStep:
    """A single hinge fold scheduled over a frame window."""

    parent: int
    child: int
    angle: float  # radians, rotation about the bone's local X axis
    depth: int  # BFS depth from the root (drives the cascade order)
    start_frame: int
    end_frame: int


@dataclass
class FoldPlan:
    """An ordered fold schedule with its overall frame range."""

    steps: List[FoldStep] = field(default_factory=list)
    frame_start: int = DEFAULT_FRAME_START
    frame_end: int = DEFAULT_FRAME_START


def _depths(topology: Topology) -> dict:
    """Return the BFS depth of every panel keyed by panel index."""
    depth = {topology.root: 0}
    for joint in topology.joints:
        depth[joint.child] = depth.get(joint.parent, 0) + 1
    return depth


def build_fold_plan(
    topology: Topology,
    angle: float = DEFAULT_FOLD_ANGLE,
    frame_start: int = DEFAULT_FRAME_START,
    frames_per_fold: int = DEFAULT_FRAMES_PER_FOLD,
    cascade_offset: int = DEFAULT_CASCADE_OFFSET,
) -> FoldPlan:
    """Build a :class:`FoldPlan` from a resolved fold ``topology``.

    Each hinge folds by ``angle`` radians over ``frames_per_fold`` frames. A
    panel at BFS depth *d* starts folding ``d * cascade_offset`` frames after
    ``frame_start`` so children wait for their parent to move first.
    """
    frames_per_fold = max(1, frames_per_fold)
    cascade_offset = max(0, cascade_offset)

    depth = _depths(topology)
    steps: List[FoldStep] = []
    frame_end = frame_start
    for joint in topology.joints:
        d = depth.get(joint.child, 1)
        start = frame_start + d * cascade_offset
        end = start + frames_per_fold
        steps.append(
            FoldStep(
                parent=joint.parent,
                child=joint.child,
                angle=angle,
                depth=d,
                start_frame=start,
                end_frame=end,
            )
        )
        frame_end = max(frame_end, end)

    return FoldPlan(steps=steps, frame_start=frame_start, frame_end=frame_end)
