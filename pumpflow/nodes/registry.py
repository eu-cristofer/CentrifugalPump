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
from .mechanical_run import MechanicalRunNode
from .npsh import NPSHNode
from .operating_point import OperatingPointNode
from .performance_plot import PerformancePlotNode
from .point import PointNode
from .rated_point import RatedPointInputNode
from .report_export import ReportExportNode
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
    ComplianceCheckNode,
    MechanicalRunNode,
    NPSHNode,
    ReportExportNode,
    MarkdownNoteNode,
]

_BY_KIND: Dict[str, Type[BaseNode]] = {c.kind: c for c in _CLASSES}

# (kind, title, glyph) — order shown in the toolbox
NODE_KINDS: List[Tuple[str, str, str]] = [(c.kind, c.title, c.glyph) for c in _CLASSES]


def make_node(kind: str) -> BaseNode:
    cls = _BY_KIND.get(kind)
    if cls is None:
        raise KeyError(f"Unknown node kind: {kind!r}")
    return cls()
