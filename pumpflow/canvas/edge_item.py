"""
canvas.edge_item
================

A bezier link carrying a signal from an output port to an input port.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from . import theme

if TYPE_CHECKING:
    from .port_item import PortItem


class EdgeItem(QGraphicsPathItem):
    def __init__(self, source: Optional["PortItem"] = None,
                 target: Optional["PortItem"] = None):
        super().__init__()
        self.source = source
        self.target = target
        self._drag_end: Optional[QPointF] = None
        self.setZValue(0)
        self.setFlag(QGraphicsPathItem.ItemIsSelectable, True)
        self._build_pen(False)

    def _build_pen(self, active: bool) -> None:
        color = theme.EDGE_ACTIVE if active else theme.EDGE
        pen = QPen(color, 2.2 if active else 2.0)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)

    # -- endpoints ---------------------------------------------------------
    def set_drag_end(self, scene_pos: QPointF) -> None:
        self._drag_end = scene_pos
        self.update_path()

    def attach(self) -> None:
        if self.source:
            self.source.add_edge(self)
        if self.target:
            self.target.add_edge(self)
        self.update_path()

    def detach(self) -> None:
        if self.source:
            self.source.remove_edge(self)
        if self.target:
            self.target.remove_edge(self)

    def other(self, port: "PortItem") -> Optional["PortItem"]:
        return self.target if port is self.source else self.source

    # -- geometry ----------------------------------------------------------
    def update_path(self) -> None:
        if self.source is not None:
            p1 = self.source.center_scene()
        else:
            p1 = self._drag_end or QPointF(0, 0)
        if self.target is not None:
            p2 = self.target.center_scene()
        else:
            p2 = self._drag_end or p1

        # orient control handles based on which side is the output
        out_on_left = True
        if self.source is not None:
            out_on_left = self.source.is_output
        dx = max(40.0, abs(p2.x() - p1.x()) * 0.5)
        c1 = QPointF(p1.x() + (dx if out_on_left else -dx), p1.y())
        c2 = QPointF(p2.x() - (dx if out_on_left else -dx), p2.y())

        path = QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        self.setPath(path)

    def paint(self, painter, option, widget=None):
        self._build_pen(self.isSelected())
        super().paint(painter, option, widget)
