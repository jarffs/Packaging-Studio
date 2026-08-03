"""File > Import operator for SVG/PDF packaging dielines."""

import os

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from ..core.line_classifier import classify
from ..core.pdf_parser import pdf_to_svg
from ..core.svg_parser import parse_svg
from ..mesh.viewport import build_dieline
from ..utils.constants import LineType
from ..utils.geometry import bbox

_TYPE_KEYS = {
    LineType.CUT: "cut",
    LineType.FOLD: "fold",
    LineType.SCORE: "score",
    LineType.GLUE_FLAP: "glue",
    LineType.WINDOW: "window",
    LineType.UNKNOWN: "unknown",
}


class PACKAGING_OT_import_dieline(bpy.types.Operator, ImportHelper):
    """Import a packaging dieline (SVG/PDF) and classify its lines."""

    bl_idname = "packaging_studio.import_dieline"
    bl_label = "Import Dieline (SVG/PDF)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".svg"
    filter_glob: StringProperty(default="*.svg;*.pdf", options={"HIDDEN"})
    filepath: StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})

    def execute(self, context):
        path = self.filepath
        ext = os.path.splitext(path)[1].lower()

        try:
            if ext == ".pdf":
                svg_text = pdf_to_svg(path)
            elif ext == ".svg":
                with open(path, "r", encoding="utf-8") as handle:
                    svg_text = handle.read()
            else:
                self.report({"WARNING"}, "Select an SVG or PDF file")
                return {"CANCELLED"}
            paths = parse_svg(svg_text)
        except Exception as exc:  # noqa: BLE001 - report any import failure
            self.report({"ERROR"}, f"Failed to import dieline: {exc}")
            return {"CANCELLED"}

        if not paths:
            self.report(
                {"WARNING"},
                "No vector paths found. Is the file rasterized (an image)?",
            )
            return {"CANCELLED"}

        classified = classify(paths)
        name = os.path.splitext(os.path.basename(path))[0]
        build_dieline(classified, name)

        counts = self._counts(classified)
        self._fill_stats(context, classified, paths, name, counts, path)
        self.report(
            {"INFO"},
            f"📦 Dieline '{name}': {len(paths)} paths — "
            f"cut {counts['cut']}, fold {counts['fold']}, score {counts['score']}, "
            f"glue {counts['glue']}, window {counts['window']}",
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        if self.filepath:
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    @staticmethod
    def _counts(classified):
        counts = {key: 0 for key in ("cut", "fold", "score", "glue", "window", "unknown")}
        for line in classified:
            counts[_TYPE_KEYS[line.line_type]] += 1
        return counts

    @staticmethod
    def _fill_stats(context, classified, paths, name, counts, path):
        props = context.scene.packaging_studio
        props.source_file = name
        props.source_path = path
        props.total_paths = len(paths)
        props.cut_count = counts["cut"]
        props.fold_count = counts["fold"]
        props.score_count = counts["score"]
        props.glue_count = counts["glue"]
        props.window_count = counts["window"]
        props.unknown_count = counts["unknown"]
        props.avg_confidence = (
            sum(line.confidence for line in classified) / len(classified)
            if classified
            else 0.0
        )
        all_points = [pt for path in paths for pt in path.points]
        min_x, min_y, max_x, max_y = bbox(all_points)
        props.width_units = max_x - min_x
        props.height_units = max_y - min_y


def menu_func_import(self, context):
    self.layout.operator(
        PACKAGING_OT_import_dieline.bl_idname, text="Dieline (SVG/PDF)"
    )
