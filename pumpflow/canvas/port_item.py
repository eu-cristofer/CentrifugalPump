"""
canvas.port_item
================

A single connection point on a node (an Orange-style typed signal port).
Input ports sit on the left edge, output ports on the right.  Output ports may
fan out to many edges; the Report Export input is multi-connection (UI_SPEC §3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem

from . import theme

if TYPE_CHECKING:
    from .node_item import NodeItem
    from .edge_item import EdgeItem


class PortItem(QGraphicsObject):
    def __init__(self, node: "NodeItem", name: str, signal_type: str,
                 is_output: bool, multi: bool = False):
        super().__init__(node)
        self.node = node
        self.name = name
        self.signal_type = signal_type
        self.is_output = is_output
        self.multi = multi
        self.edges: List["EdgeItem"] = []
        self._hover = False
        self.setAcceptHoverEvents(True)
        self.setZValue(3)
        r = theme.PORT_R + 4
        self._rect = QRectF(-r, -r, 2 * r, 2 * r)

    # -- geometry ----------------------------------------------------------
    def boundingRect(self) -> QRectF:
        return self._rect

    def center_scene(self) -> QPointF:
        return self.mapToScene(QPointF(0, 0))

    # -- connection bookkeeping -------------------------------------------
    def can_accept(self, other: "PortItem") -> bool:
        if other is None or other is self:
            return False
        if other.node is self.node:
            return False
        if self.is_output == other.is_output:
            return False
        # type compatibility ("*" accepts anything)
        a, b = self.signal_type, other.signal_type
        if a != "*" and b != "*" and a != b:
            return False
        # a single-connection input may hold only one edge
        inp = self if not self.is_output else other
        if not inp.multi and inp.edges:
            return False
        return True

    def add_edge(self, edge: "EdgeItem") -> None:
        if edge not in self.edges:
            self.edges.append(edge)
        self.update()

    def remove_edge(self, edge: "EdgeItem") -> None:
        if edge in self.edges:
            self.edges.remove(edge)
        self.update()

    # -- painting ----------------------------------------------------------
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        color = theme.port_color(self.signal_type)
        connected = bool(self.edges)
        r = theme.PORT_R + (1.2 if self._hover else 0.0)

        painter.setPen(QPen(color, 1.6))
        painter.setBrush(QBrush(color if connected or self._hover else theme.PORT_EMPTY))
        painter.drawEllipse(QPointF(0, 0), r, r)

        if self.multi and not self.is_output:
            # small "+" hint for multi-connection inputs
            painter.setPen(QPen(theme.PORT_RING if connected else color, 1.3))
            painter.drawLine(QPointF(-2.4, 0), QPointF(2.4, 0))
            painter.drawLine(QPointF(0, -2.4), QPointF(0, 2.4))

    def hoverEnterEvent(self, event):
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)
