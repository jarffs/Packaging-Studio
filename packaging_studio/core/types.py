"""Core data structures shared across the parsing and classification pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class StrokeStyle:
    """Resolved stroke presentation of a dieline element."""

    color: Optional[Tuple[float, float, float]] = None
    width: float = 1.0
    dashed: bool = False


@dataclass
class DielinePath:
    """A single flattened polyline extracted from the source document.

    Each ``DielinePath`` corresponds to one subpath. Elements containing
    multiple subpaths are split into multiple ``DielinePath`` instances.
    """

    points: List[Tuple[float, float]]
    is_closed: bool
    stroke: StrokeStyle = field(default_factory=StrokeStyle)
    element_id: Optional[str] = None
    group: Optional[str] = None
    source_index: int = 0


@dataclass
class ClassifiedLine:
    """A dieline path annotated with its classified line type and confidence."""

    path: DielinePath
    line_type: "object"  # LineType from utils.constants
    confidence: float


@dataclass
class Panel:
    """A closed region (face) of the dieline that becomes a 3D box panel."""

    index: int
    loop: List[int]  # vertex indices into PanelModel.vertices, CCW order
    centroid: Tuple[float, float]
    area: float


@dataclass
class PanelModel:
    """Planar arrangement of the dieline resolved into panels and fold edges."""

    vertices: List[Tuple[float, float]]
    panels: List["Panel"]
    fold_edges: set = field(default_factory=set)  # frozenset({i, j})
    edge_types: dict = field(default_factory=dict)  # frozenset({i, j}) -> str


@dataclass
class FoldJoint:
    """A hinge between a parent panel and a child panel along a fold edge."""

    parent: int
    child: int
    edge: frozenset  # shared fold-edge vertex indices
    axis: Tuple[Tuple[float, float], Tuple[float, float]]  # hinge endpoints


@dataclass
class Topology:
    """Panel adjacency graph resolved into a fold hierarchy from a root panel."""

    root: int
    joints: List["FoldJoint"]  # in BFS order (parent processed before child)
    adjacency: dict  # panel index -> list of (neighbor index, edge frozenset)

