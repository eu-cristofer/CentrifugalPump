"""
canvas.node_item
================

The on-canvas representation of one workflow widget: a compact node with a
title bar, an icon glyph, typed ports, and an Orange-style **status line**
summarizing its output (UI_SPEC §3).  Double-click opens the property dialog.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from PySide6.QtCore import QRectF, Qt, QPointF
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsDropShadowEffect

from . import theme
from .port_item import PortItem

if TYPE_CHECKING:
    from ..nodes.base import BaseNode

_STATE_COLOR = {
    "idle": theme.SUBTLE_TEXT,
    "ok": theme.OK_GREEN,
    "invalid": theme.AMBER,
    "error": theme.REJECT_RED,
    "reject": theme.REJECT_RED,
}


class NodeItem(QGraphicsObject):
    def __init__(self, logic: "BaseNode"):
        super().__init__()
        self.logic = logic
        logic.item = self
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(1)
        self.setAcceptHoverEvents(True)

        self.in_ports: Dict[str, PortItem] = {}
        self.out_ports: Dict[str, PortItem] = {}
        self._build_ports()
        self._height = self._compute_height()
        self._layout_ports()

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 3)
        shadow.setColor(theme.NODE_SHADOW)
        self.setGraphicsEffect(shadow)

    # -- construction ------------------------------------------------------
    def _build_ports(self) -> None:
        for spec in self.logic.inputs:
            self.in_ports[spec.name] = PortItem(
                self, spec.name, spec.signal_type, is_output=False, multi=spec.multi
            )
        for spec in self.logic.outputs:
            self.out_ports[spec.name] = PortItem(
                self, spec.name, spec.signal_type, is_output=True, multi=True
            )

    def _compute_height(self) -> float:
        rows = max(len(self.in_ports), len(self.out_ports), 1)
        ports_block = rows * theme.ROW_H
        status_block = 34
        return theme.TITLE_H + 10 + ports_block + status_block

    def _layout_ports(self) -> None:
        body_top = theme.TITLE_H + 14

        def place(ports: Dict[str, PortItem], x: float):
            n = len(ports)
            for i, port in enumerate(ports.values()):
                y = body_top + i * theme.ROW_H + theme.ROW_H / 2
                port.setPos(x, y)

        place(self.in_ports, 0.0)
        place(self.out_ports, theme.NODE_W)

    # -- geometry ----------------------------------------------------------
    def boundingRect(self) -> QRectF:
        m = 14
        return QRectF(-m, -m, theme.NODE_W + 2 * m, self._height + 2 * m)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for port in list(self.in_ports.values()) + list(self.out_ports.values()):
                for edge in port.edges:
                    edge.update_path()
        return super().itemChange(change, value)

    # -- painting ----------------------------------------------------------
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        w, h, r = theme.NODE_W, self._height, theme.NODE_RADIUS

        body = QPainterPath()
        body.addRoundedRect(QRectF(0, 0, w, h), r, r)
        painter.setBrush(QBrush(theme.NODE_BG))
        border = theme.NODE_BORDER_SEL if self.isSelected() else theme.NODE_BORDER
        painter.setPen(QPen(border, 2.0 if self.isSelected() else 1.3))
        painter.drawPath(body)

        # title bar (rounded only at the top)
        title = QPainterPath()
        title.addRoundedRect(QRectF(0, 0, w, theme.TITLE_H + r), r, r)
        title.addRect(QRectF(0, theme.TITLE_H, w, r))  # square off bottom corners
        painter.setClipPath(body)
        title_color = theme.TITLE_BG_SOURCE if self.logic.is_source else theme.TITLE_BG
        painter.setBrush(QBrush(title_color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(title)
        painter.setClipping(False)

        # icon glyph chip
        painter.setBrush(QBrush(QColor(255, 255, 255, 38)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(8, 6, theme.TITLE_H - 12, theme.TITLE_H - 12), 4, 4)
        painter.setPen(QPen(theme.TITLE_TEXT))
        painter.setFont(theme.title_font())
        painter.drawText(
            QRectF(8, 6, theme.TITLE_H - 12, theme.TITLE_H - 12),
            Qt.AlignCenter,
            self.logic.glyph,
        )

        # title text
        painter.setPen(QPen(theme.TITLE_TEXT))
        painter.setFont(theme.title_font())
        painter.drawText(
            QRectF(theme.TITLE_H + 2, 0, w - theme.TITLE_H - 8, theme.TITLE_H),
            Qt.AlignVCenter | Qt.AlignLeft,
            self.logic.title,
        )

        # port labels
        painter.setFont(theme.body_font(8))
        painter.setPen(QPen(theme.SUBTLE_TEXT))
        for name, port in self.in_ports.items():
            y = port.pos().y()
            painter.drawText(
                QRectF(12, y - 8, w / 2, 16),
                Qt.AlignVCenter | Qt.AlignLeft,
                self.logic.port_label(name),
            )
        for name, port in self.out_ports.items():
            y = port.pos().y()
            painter.drawText(
                QRectF(w / 2 - 12, y - 8, w / 2, 16),
                Qt.AlignVCenter | Qt.AlignRight,
                self.logic.port_label(name),
            )

        # status line + state dot
        sy = h - 26
        painter.setPen(QPen(QColor("#e3e8ee")))
        painter.drawLine(QPointF(10, sy), QPointF(w - 10, sy))

        state = self.logic.state
        dot = _STATE_COLOR.get(state, theme.SUBTLE_TEXT)
        painter.setBrush(QBrush(dot))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(16, sy + 13), 4, 4)

        painter.setPen(QPen(theme.BODY_TEXT if state == "ok" else theme.SUBTLE_TEXT))
        painter.setFont(theme.body_font(8))
        painter.drawText(
            QRectF(28, sy + 4, w - 36, 18),
            Qt.AlignVCenter | Qt.AlignLeft,
            _elide(self.logic.status, 30),
        )

    def refresh(self) -> None:
        self.update()

    def mouseDoubleClickEvent(self, event):
        scene = self.scene()
        if scene is not None and hasattr(scene, "open_node_dialog"):
            scene.open_node_dialog(self)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def _elide(text: str, n: int) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"
