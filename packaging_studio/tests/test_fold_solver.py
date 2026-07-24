"""Tests for the fold solver (pure Python, no Blender)."""

from __future__ import annotations

import math
import unittest

from packaging_studio.core.fold_solver import build_fold_plan
from packaging_studio.core.types import FoldJoint, Topology


def _joint(parent, child):
    edge = frozenset((parent, child))
    return FoldJoint(parent=parent, child=child, edge=edge, axis=((0.0, 0.0), (1.0, 0.0)))


def _chain_topology():
    """root 0 -> 1 -> 2, plus a shallow branch 0 -> 3 (BFS order)."""
    joints = [_joint(0, 1), _joint(0, 3), _joint(1, 2)]
    adjacency = {0: [], 1: [], 2: [], 3: []}
    return Topology(root=0, joints=joints, adjacency=adjacency)


class FoldSolverTests(unittest.TestCase):
    def test_one_step_per_joint(self):
        plan = build_fold_plan(_chain_topology())
        self.assertEqual(len(plan.steps), 3)
        children = {s.child for s in plan.steps}
        self.assertEqual(children, {1, 2, 3})

    def test_depths_follow_hierarchy(self):
        plan = build_fold_plan(_chain_topology())
        depth = {s.child: s.depth for s in plan.steps}
        self.assertEqual(depth[1], 1)
        self.assertEqual(depth[3], 1)
        self.assertEqual(depth[2], 2)

    def test_cascade_delays_deeper_panels(self):
        plan = build_fold_plan(
            _chain_topology(), frame_start=1, frames_per_fold=20, cascade_offset=5
        )
        start = {s.child: s.start_frame for s in plan.steps}
        # depth-1 panels start at 1 + 1*5 = 6, depth-2 at 1 + 2*5 = 11.
        self.assertEqual(start[1], 6)
        self.assertEqual(start[3], 6)
        self.assertEqual(start[2], 11)

    def test_frame_end_is_last_fold(self):
        plan = build_fold_plan(
            _chain_topology(), frame_start=1, frames_per_fold=20, cascade_offset=5
        )
        # deepest fold: start 11 + 20 = 31.
        self.assertEqual(plan.frame_end, 31)

    def test_angle_is_applied(self):
        plan = build_fold_plan(_chain_topology(), angle=math.radians(90))
        self.assertTrue(all(math.isclose(s.angle, math.pi / 2) for s in plan.steps))

    def test_zero_cascade_folds_together(self):
        plan = build_fold_plan(_chain_topology(), cascade_offset=0)
        self.assertTrue(all(s.start_frame == plan.frame_start for s in plan.steps))

    def test_empty_topology(self):
        plan = build_fold_plan(Topology(root=0, joints=[], adjacency={0: []}))
        self.assertEqual(plan.steps, [])
        self.assertEqual(plan.frame_end, plan.frame_start)


if __name__ == "__main__":
    unittest.main()
