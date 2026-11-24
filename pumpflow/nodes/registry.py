"""
nodes.registry
==============

Maps a node ``kind`` to its class, and provides the catalog used by the
"Add node" menu / toolbox.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Type

from .base import BaseNode
from .compliance import ComplianceCheckNode
from .correction import SpeedCorrectionNode
from .curve_fit import CurveFitNode
from .explore_plot import ExploreChartNode
from .fluid import FluidNode
from .markdown_note import MarkdownNoteNode
from .mechanical_run_check import MechanicalRunCheckNode
from .mechanical_run import MechanicalRunNode
from .npsh import NPSHNode
from .operating_point import OperatingPointNode
from .performance_plot import PerformancePlotNode
from .point import PointNode
from .rated_point import RatedPointInputNode
from .report_export import ReportExportNode
from .selection import SelectionNode
from .system_curve import SystemCurveNode
from .test_points import TestPointsTableNode
from .trim import TrimNode

_CLASSES: List[Type[BaseNode]] = [
    RatedPointInputNode,
    FluidNode,
    TestPointsTableNode,
    PointNode,
    SpeedCorrectionNode,
    TrimNode,
    CurveFitNode,
    PerformancePlotNode,
    ExploreChartNode,
    SystemCurveNode,
    OperatingPointNode,
    SelectionNode,
    ComplianceCheckNode,
    MechanicalRunNode,
    MechanicalRunCheckNode,
    NPSHNode,
    ReportExportNode,
    MarkdownNoteNode,
]

_BY_KIND: Dict[str, Type[BaseNode]] = {c.kind: c for c in _CLASSES}

# (kind, title, glyph) — order shown in the toolbox
NODE_KINDS: List[Tuple[str, str, str]] = [(c.kind, c.title, c.glyph) for c in _CLASSES]

# Toolbox / "Add node" sections, in the order a FAT is built (UI_SPEC §2).
NODE_GROUPS: List[Tuple[str, Tuple[str, ...]]] = [
    ("Inputs", ("rated_point", "fluid", "test_points", "mechanical_run", "point")),
    ("Corrections", ("correction", "trim")),
    (
        "Curves & analysis",
        (
            "curve_fit",
            "performance_plot",
            "explore_plot",
            "system_curve",
            "operating_point",
            "selection",
        ),
    ),
    ("Checks", ("compliance", "mechanical_run_check", "npsh")),
    ("Output", ("report_export", "markdown_note")),
]


def grouped_node_kinds() -> List[Tuple[str, List[Tuple[str, str, str]]]]:
    """``NODE_KINDS`` split into :data:`NODE_GROUPS`; any kind not listed goes
    into a trailing "Other" group, so a new node is never hidden."""
    by_kind = {k[0]: k for k in NODE_KINDS}
    out, seen = [], set()
    for name, kinds in NODE_GROUPS:
        items = [by_kind[k] for k in kinds if k in by_kind]
        seen.update(k for k, *_ in items)
        if items:
            out.append((name, items))
    rest = [k for k in NODE_KINDS if k[0] not in seen]
    if rest:
        out.append(("Other", rest))
    return out


def make_node(kind: str) -> BaseNode:
    cls = _BY_KIND.get(kind)
    if cls is None:
        raise KeyError(f"Unknown node kind: {kind!r}")
    return cls()
