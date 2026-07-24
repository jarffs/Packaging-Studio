"""Unit tests for panel detection and topology (no Blender required)."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packaging_studio.core.panel_detector import detect_panels
from packaging_studio.core.topology import build_topology
from packaging_studio.core.types import ClassifiedLine, DielinePath
from packaging_studio.utils.constants import LineType


def _line(points, line_type, closed=False):
    return ClassifiedLine(
        path=DielinePath(points=points, is_closed=closed),
        line_type=line_type,
        confidence=1.0,
    )


def _two_panel_box():
    """Outer 0..200 x 0..100 rectangle split by a vertical fold at x=100."""
    outline = _line(
        [(0, 0), (200, 0), (200, 100), (0, 100)], LineType.CUT, closed=True
    )
    fold = _line([(100, 0), (100, 100)], LineType.FOLD)
    return [outline, fold]


class PanelDetectorTests(unittest.TestCase):
    def test_single_rectangle_is_one_panel(self):
        model = detect_panels(
            [_line([(0, 0), (10, 0), (10, 10), (0, 10)], LineType.CUT, closed=True)]
        )
        self.assertEqual(len(model.panels), 1)
        self.assertAlmostEqual(model.panels[0].area, 100.0, places=6)

    def test_fold_splits_into_two_panels(self):
        model = detect_panels(_two_panel_box())
        self.assertEqual(len(model.panels), 2)
        areas = sorted(p.area for p in model.panels)
        self.assertAlmostEqual(areas[0], 10000.0, places=3)
        self.assertAlmostEqual(areas[1], 10000.0, places=3)

    def test_t_junction_creates_shared_vertices(self):
        model = detect_panels(_two_panel_box())
        # The fold endpoints (100,0) and (100,100) must exist as vertices.
        keys = {(round(x), round(y)) for x, y in model.vertices}
        self.assertIn((100, 0), keys)
        self.assertIn((100, 100), keys)

    def test_fold_edge_recorded(self):
        model = detect_panels(_two_panel_box())
        self.assertTrue(model.fold_edges)

    def test_empty_input(self):
        model = detect_panels([])
        self.assertEqual(model.panels, [])

    def test_three_panel_strip(self):
        outline = _line(
            [(0, 0), (300, 0), (300, 100), (0, 100)], LineType.CUT, closed=True
        )
        f1 = _line([(100, 0), (100, 100)], LineType.FOLD)
        f2 = _line([(200, 0), (200, 100)], LineType.FOLD)
        model = detect_panels([outline, f1, f2])
        self.assertEqual(len(model.panels), 3)

    def test_dashed_score_lines_split_panels(self):
        # Dashed crease lines classify as SCORE and must still divide panels.
        outline = _line(
            [(0, 0), (200, 0), (200, 100), (0, 100)], LineType.CUT, closed=True
        )
        crease = _line([(100, 0), (100, 100)], LineType.SCORE)
        model = detect_panels([outline, crease])
        self.assertEqual(len(model.panels), 2)

    def test_artwork_outside_outline_is_ignored(self):
        # A closed shape sitting outside the main outline (a preview drawing)
        # must not become a panel.
        outline = _line(
            [(0, 0), (100, 0), (100, 100), (0, 100)], LineType.CUT, closed=True
        )
        preview = _line(
            [(200, 200), (260, 200), (260, 260), (200, 260)],
            LineType.CUT,
            closed=True,
        )
        model = detect_panels([outline, preview])
        self.assertEqual(len(model.panels), 1)


class TopologyTests(unittest.TestCase):
    def test_two_panels_are_adjacent(self):
        model = detect_panels(_two_panel_box())
        topo = build_topology(model)
        self.assertEqual(len(topo.joints), 1)
        self.assertEqual(topo.joints[0].parent, topo.root)

    def test_root_is_largest_panel(self):
        # Left panel bigger: fold at x=150 -> areas 15000 vs 5000.
        outline = _line(
            [(0, 0), (200, 0), (200, 100), (0, 100)], LineType.CUT, closed=True
        )
        fold = _line([(150, 0), (150, 100)], LineType.FOLD)
        model = detect_panels([outline, fold])
        topo = build_topology(model)
        root_panel = next(p for p in model.panels if p.index == topo.root)
        self.assertAlmostEqual(root_panel.area, 15000.0, places=3)

    def test_explicit_root_overrides_largest(self):
        model = detect_panels(_two_panel_box())
        indices = sorted(p.index for p in model.panels)
        chosen = indices[-1]
        topo = build_topology(model, root=chosen)
        self.assertEqual(topo.root, chosen)
        self.assertEqual(len(topo.joints), 1)
        self.assertEqual(topo.joints[0].parent, chosen)

    def test_invalid_root_falls_back_to_largest(self):
        model = detect_panels(_two_panel_box())
        topo = build_topology(model, root=999)
        self.assertIn(topo.root, {p.index for p in model.panels})

    def test_strip_hierarchy_has_two_joints(self):
        outline = _line(
            [(0, 0), (300, 0), (300, 100), (0, 100)], LineType.CUT, closed=True
        )
        f1 = _line([(100, 0), (100, 100)], LineType.FOLD)
        f2 = _line([(200, 0), (200, 100)], LineType.FOLD)
        topo = build_topology(detect_panels([outline, f1, f2]))
        self.assertEqual(len(topo.joints), 2)
        # Every child reachable from root exactly once.
        children = [j.child for j in topo.joints]
        self.assertEqual(len(children), len(set(children)))

    def test_empty_model(self):
        topo = build_topology(detect_panels([]))
        self.assertEqual(topo.root, -1)
        self.assertEqual(topo.joints, [])


if __name__ == "__main__":
    unittest.main()
