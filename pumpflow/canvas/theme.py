"""
canvas.theme
============

Palette and metrics of the node canvas, read from the design system
(:mod:`pump.design`, ``pump/design/tokens.json``).  The names below are the
canvas code's vocabulary; their values live only in the token file.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont

from pump import design

from ..style import mono_font as _mono_font, qcolor, ui_font

# --- surfaces ---------------------------------------------------------------
WINDOW_BG = qcolor("window-bg")
CANVAS_BG = qcolor("canvas-bg")
GRID_DOT = qcolor("grid-dot")
GRID_DOT_STRONG = qcolor("grid-dot-strong")

# --- nodes ------------------------------------------------------------------
NODE_BG = qcolor("surface")
NODE_BG_ALT = qcolor("surface-alt")
NODE_BORDER = qcolor("border")
NODE_BORDER_SEL = qcolor("accent")
NODE_SHADOW = qcolor("node-shadow")
TITLE_BG = qcolor("title-bg")  # steel
TITLE_BG_SOURCE = qcolor("title-bg-source")  # source nodes: lighter steel-blue
TITLE_TEXT = qcolor("title-text")
SUBTLE_TEXT = qcolor("subtle-text")
BODY_TEXT = qcolor("body-text")
DIVIDER = qcolor("divider")  # status-line rule inside a node

# --- accents / state --------------------------------------------------------
ACCENT = qcolor("accent")  # industrial blue
STEEL = qcolor("steel")
OK_GREEN = qcolor("ok-green")
REJECT_RED = qcolor("reject-red")
AMBER = qcolor("amber")

# --- ports (by signal type) -------------------------------------------------
PORT_COLORS = {
    "RatedPoint": qcolor("port-rated-point"),
    "FluidSpec": qcolor("port-fluid-spec"),
    "TestPointSet": qcolor("port-test-point-set"),
    "CorrectedCurve": qcolor("port-corrected-curve"),
    "FittedModel": qcolor("port-fitted-model"),
    "ComplianceResult": qcolor("port-compliance-result"),
    "BranchBundle": qcolor("port-branch-bundle"),
    "*": qcolor("port-branch-bundle"),
}
PORT_RING = qcolor("port-ring")
PORT_EMPTY = qcolor("port-ring")
EDGE = qcolor("edge")
EDGE_ACTIVE = qcolor("edge-active")

# --- metrics ----------------------------------------------------------------
NODE_W = int(design.length("node-width"))
TITLE_H = int(design.length("node-title-height"))
ROW_H = int(design.length("node-row-height"))
PORT_R = design.length("port-radius")
NODE_RADIUS = design.length("radius-node")
GRID_SIZE = int(design.length("canvas-grid"))

# Canvas fonts are painted in points; the tokens give pixels at 96 dpi.
_PT_PER_PX = 0.75


def _pt(style: str) -> int:
    return max(1, round(design.font_px(style) * _PT_PER_PX))


def port_color(signal_type: str) -> QColor:
    return PORT_COLORS.get(signal_type, PORT_COLORS["*"])


def title_font() -> QFont:
    return ui_font(_pt("node-title"), QFont.DemiBold)


def body_font(size: int | None = None) -> QFont:
    return ui_font(size if size is not None else _pt("node-body"))


def mono_font(size: int | None = None) -> QFont:
    return _mono_font(size if size is not None else _pt("node-mono"))
