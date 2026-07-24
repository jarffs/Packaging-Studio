"""Resolve panel adjacency into a fold hierarchy.

Pure Python (no Blender). Two panels are adjacent when they share an edge that
is a fold. A breadth-first traversal from the largest panel (the box base)
produces a parent/child hierarchy; each child is connected to its parent by a
:class:`FoldJoint` describing the hinge axis.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List

from .types import FoldJoint, PanelModel, Topology


def build_topology(model: PanelModel, root: int = None) -> Topology:
    """Return the fold :class:`Topology` for a :class:`PanelModel`.

    ``root`` optionally forces which panel stays static (the base). When it is
    ``None`` or not a valid panel index, the largest-area panel is used.
    """
    panels = model.panels
    if not panels:
        return Topology(root=-1, joints=[], adjacency={})

    edge_to_panels = _edge_to_panels(panels)
    adjacency = _build_adjacency(panels, model.fold_edges, edge_to_panels)

    valid = {p.index for p in panels}
    if root not in valid:
        root = max(panels, key=lambda p: p.area).index
    joints = _bfs_joints(root, adjacency, model)
    return Topology(root=root, joints=joints, adjacency=adjacency)


def _edge_to_panels(panels) -> Dict[frozenset, List[int]]:
    """Map every panel boundary edge to the panels that use it."""
    mapping: Dict[frozenset, List[int]] = {}
    for panel in panels:
        loop = panel.loop
        n = len(loop)
        for i in range(n):
            edge = frozenset((loop[i], loop[(i + 1) % n]))
            mapping.setdefault(edge, []).append(panel.index)
    return mapping


def _build_adjacency(panels, fold_edges, edge_to_panels):
    adjacency = {panel.index: [] for panel in panels}
    for edge in fold_edges:
        users = edge_to_panels.get(edge)
        if not users or len(users) < 2:
            continue
        for a in users:
            for b in users:
                if a != b:
                    adjacency[a].append((b, edge))
    return adjacency


def _bfs_joints(root, adjacency, model) -> List[FoldJoint]:
    joints: List[FoldJoint] = []
    visited = {root}
    queue = deque([root])
    while queue:
        parent = queue.popleft()
        for child, edge in adjacency[parent]:
            if child in visited:
                continue
            visited.add(child)
            i, j = tuple(edge)
            axis = (model.vertices[i], model.vertices[j])
            joints.append(FoldJoint(parent=parent, child=child, edge=edge, axis=axis))
            queue.append(child)
    return joints
