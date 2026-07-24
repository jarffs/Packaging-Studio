"""Unit tests for the line classifier (no Blender required)."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packaging_studio.core.line_classifier import classify
from packaging_studio.core.svg_parser import parse_svg
from packaging_studio.utils.constants import LineType

SVG_NS = 'xmlns="http://www.w3.org/2000/svg"'


def _by_id(classified, element_id):
    for line in classified:
        if line.path.element_id == element_id:
            return line
    raise AssertionError(f"no classified line with id {element_id!r}")


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        example = ROOT / "packaging_studio" / "examples" / "simple_tuck_end.svg"
        self.classified = classify(parse_svg(example.read_text(encoding="utf-8")))

    def test_outer_contour_is_cut(self):
        self.assertIs(_by_id(self.classified, "outline").line_type, LineType.CUT)

    def test_internal_dividers_are_folds(self):
        for fid in ("fold-1", "fold-2", "fold-3"):
            self.assertIs(_by_id(self.classified, fid).line_type, LineType.FOLD)

    def test_dashed_line_is_score(self):
        self.assertIs(_by_id(self.classified, "score").line_type, LineType.SCORE)

    def test_inner_rect_is_window(self):
        self.assertIs(_by_id(self.classified, "window").line_type, LineType.WINDOW)

    def test_near_parallel_edge_line_is_glue_flap(self):
        self.assertIs(_by_id(self.classified, "glue").line_type, LineType.GLUE_FLAP)

    def test_empty_input(self):
        self.assertEqual(classify([]), [])

    def test_largest_closed_path_wins_as_outer(self):
        svg = (
            f'<svg {SVG_NS}>'
            f'<rect id="small" x="0" y="0" width="10" height="10"/>'
            f'<rect id="big" x="-50" y="-50" width="200" height="200"/>'
            f'</svg>'
        )
        classified = classify(parse_svg(svg))
        big = _by_id(classified, "big")
        small = _by_id(classified, "small")
        self.assertIs(big.line_type, LineType.CUT)
        self.assertIs(small.line_type, LineType.WINDOW)


if __name__ == "__main__":
    unittest.main()
