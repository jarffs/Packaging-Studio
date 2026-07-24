"""Unit tests for the SVG parser (no Blender required)."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packaging_studio.core.svg_parser import parse_svg
from packaging_studio.core.svg_path import parse_path

SVG_NS = 'xmlns="http://www.w3.org/2000/svg"'


class PathDataTests(unittest.TestCase):
    def test_absolute_line_and_close(self):
        subs = parse_path("M0,0 L10,0 L10,10 L0,10 Z")
        self.assertEqual(len(subs), 1)
        points, closed = subs[0]
        self.assertTrue(closed)
        self.assertEqual(points[0], (0.0, 0.0))
        self.assertEqual(points[1], (10.0, 0.0))
        self.assertEqual(points[-1], (0.0, 0.0))  # closing point

    def test_relative_commands(self):
        subs = parse_path("m5,5 l10,0 l0,10")
        points, closed = subs[0]
        self.assertFalse(closed)
        self.assertEqual(points[0], (5.0, 5.0))
        self.assertEqual(points[1], (15.0, 5.0))
        self.assertEqual(points[2], (15.0, 15.0))

    def test_horizontal_vertical(self):
        subs = parse_path("M0,0 H20 V20")
        points, _ = subs[0]
        self.assertEqual(points[1], (20.0, 0.0))
        self.assertEqual(points[2], (20.0, 20.0))

    def test_multiple_subpaths(self):
        subs = parse_path("M0,0 L5,0 Z M10,10 L15,10")
        self.assertEqual(len(subs), 2)
        self.assertTrue(subs[0][1])
        self.assertFalse(subs[1][1])

    def test_cubic_is_flattened(self):
        subs = parse_path("M0,0 C0,10 10,10 10,0")
        points, _ = subs[0]
        self.assertGreater(len(points), 2)
        self.assertAlmostEqual(points[-1][0], 10.0, places=6)
        self.assertAlmostEqual(points[-1][1], 0.0, places=6)


class SvgParserTests(unittest.TestCase):
    def test_rect_is_closed_with_four_corners(self):
        svg = f'<svg {SVG_NS}><rect x="0" y="0" width="10" height="20"/></svg>'
        paths = parse_svg(svg)
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].is_closed)
        self.assertEqual(len(paths[0].points), 4)

    def test_line_is_open(self):
        svg = f'<svg {SVG_NS}><line x1="0" y1="0" x2="10" y2="0"/></svg>'
        paths = parse_svg(svg)
        self.assertFalse(paths[0].is_closed)
        self.assertEqual(paths[0].points, [(0.0, 0.0), (10.0, 0.0)])

    def test_group_transform_is_applied(self):
        svg = (
            f'<svg {SVG_NS}><g transform="translate(5,5)">'
            f'<line x1="0" y1="0" x2="10" y2="0"/></g></svg>'
        )
        paths = parse_svg(svg)
        self.assertEqual(paths[0].points, [(5.0, 5.0), (15.0, 5.0)])

    def test_dashed_stroke_detected(self):
        svg = (
            f'<svg {SVG_NS}>'
            f'<line x1="0" y1="0" x2="10" y2="0" stroke-dasharray="3 2"/>'
            f'</svg>'
        )
        paths = parse_svg(svg)
        self.assertTrue(paths[0].stroke.dashed)

    def test_defs_are_skipped(self):
        svg = (
            f'<svg {SVG_NS}><defs><rect x="0" y="0" width="5" height="5"/></defs>'
            f'<rect x="0" y="0" width="10" height="10"/></svg>'
        )
        paths = parse_svg(svg)
        self.assertEqual(len(paths), 1)

    def test_example_file_parses(self):
        example = ROOT / "packaging_studio" / "examples" / "simple_tuck_end.svg"
        paths = parse_svg(example.read_text(encoding="utf-8"))
        # outline + 3 folds + glue + score + window = 7 paths
        self.assertEqual(len(paths), 7)


if __name__ == "__main__":
    unittest.main()
