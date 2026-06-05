"""
canvas.theme
============

Central palette + metrics for the workbench — a clean, calm, professional
desktop look in an industrial blue/steel key on a light background.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont


# --- surfaces ---------------------------------------------------------------
WINDOW_BG = QColor("#eef1f4")
CANVAS_BG = QColor("#e7ebf0")
GRID_DOT = QColor("#d3dae2")
GRID_DOT_STRONG = QColor("#c2ccd6")

# --- nodes ------------------------------------------------------------------
NODE_BG = QColor("#ffffff")
NODE_BG_ALT = QColor("#f7f9fb")
NODE_BORDER = QColor("#c3ccd6")
NODE_BORDER_SEL = QColor("#2f6fb0")
NODE_SHADOW = QColor(40, 55, 75, 45)
TITLE_BG = QColor("#2b3a4a")          # steel
TITLE_BG_SOURCE = QColor("#3b6ea5")   # source nodes get a lighter steel-blue
TITLE_TEXT = QColor("#ffffff")
SUBTLE_TEXT = QColor("#5a6573")
BODY_TEXT = QColor("#28323d")

# --- accents / state --------------------------------------------------------
ACCENT = QColor("#2f6fb0")            # industrial blue
STEEL = QColor("#5b7185")
OK_GREEN = QColor("#2e7d5b")
REJECT_RED = QColor("#b4413c")
AMBER = QColor("#c08a2e")

# --- ports (by signal type) -------------------------------------------------
PORT_COLORS = {
    "RatedPoint": QColor("#2f6fb0"),
    "TestPointSet": QColor("#5b7185"),
    "CorrectedCurve": QColor("#3f8f8a"),
    "FittedModel": QColor("#6a6fb0"),
    "ComplianceResult": QColor("#b06a3f"),
    "BranchBundle": QColor("#7a8694"),
    "*": QColor("#7a8694"),
}
PORT_RING = QColor("#ffffff")
PORT_EMPTY = QColor("#ffffff")
EDGE = QColor("#9aa7b4")
EDGE_ACTIVE = QColor("#2f6fb0")

# --- metrics ----------------------------------------------------------------
NODE_W = 196
TITLE_H = 30
ROW_H = 22
PORT_R = 6.0
NODE_RADIUS = 9.0
GRID_SIZE = 26


def port_color(signal_type: str) -> QColor:
    return PORT_COLORS.get(signal_type, PORT_COLORS["*"])


def title_font() -> QFont:
    f = QFont("Segoe UI", 9, QFont.DemiBold)
    f.setStyleHint(QFont.SansSerif)
    return f


def body_font(size: int = 8) -> QFont:
    f = QFont("Segoe UI", size)
    f.setStyleHint(QFont.SansSerif)
    return f


def mono_font(size: int = 8) -> QFont:
    f = QFont("Consolas", size)
    f.setStyleHint(QFont.Monospace)
    return f
