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
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainterPath, QPen
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

# State glyph drawn inside the dot, so state never relies on colour alone.
_STATE_GLYPH = {"ok": "✓", "invalid": "!", "error": "✗", "reject": "✗"}

# Verdict pill: (fill, text) per tone.  Amber takes dark text for contrast.
_TONE = {
    "ok": (theme.OK_GREEN, theme.TITLE_TEXT),
    "fail": (theme.REJECT_RED, theme.TITLE_TEXT),
    "warn": (theme.AMBER, theme.BODY_TEXT),
}

# Below this zoom the port labels and status text are unreadable: draw only the
# title and a large verdict (or state glyph) instead.
LOW_DETAIL_LOD = 0.75


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
        title.setFillRule(Qt.WindingFill)  # union the two sub-paths instead of XOR-ing them
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

        lod = option.levelOfDetailFromTransform(painter.worldTransform())
        if lod < LOW_DETAIL_LOD:
            self._paint_overview(painter, w, h)
            return

        # port labels
        painter.setFont(theme.body_font())
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

        # status line: verdict pill (+ qualifier chips) or a state glyph, then text
        sy = h - 26
        painter.setPen(QPen(theme.DIVIDER))
        painter.drawLine(QPointF(10, sy), QPointF(w - 10, sy))

        state = self.logic.state
        cy = sy + 13
        x = 10.0
        badge = getattr(self.logic, "badge", None)
        if badge:
            x = self._paint_pill(painter, x, cy, badge[0], badge[1], 16.0)
            for note in getattr(self.logic, "badge_notes", ()):
                x = self._paint_pill(painter, x + 3, cy, note, "warn", 16.0, outline=True)
            x += 5
        else:
            self._paint_state_glyph(painter, QPointF(17, cy), 6.0, state)
            x = 28.0

        painter.setPen(QPen(theme.BODY_TEXT if state == "ok" else theme.SUBTLE_TEXT))
        painter.setFont(theme.body_font())
        avail = w - 8 - x
        if avail > 12:
            text = QFontMetricsF(painter.font()).elidedText(
                _status_beside(self.logic.status, badge), Qt.ElideRight, avail
            )
            painter.drawText(
                QRectF(x, sy + 4, avail, 18), Qt.AlignVCenter | Qt.AlignLeft, text
            )

    # -- painting helpers --------------------------------------------------
    def _paint_state_glyph(self, painter, center: QPointF, r: float, state: str):
        """A filled dot carrying a glyph (✓ ! ✗); idle is a hollow ring."""
        color = _STATE_COLOR.get(state, theme.SUBTLE_TEXT)
        glyph = _STATE_GLYPH.get(state)
        if glyph is None:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color, max(1.2, r / 4)))
            painter.drawEllipse(center, r - 1, r - 1)
            return
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, r, r)
        font = QFont(theme.body_font())
        font.setPixelSize(max(1, int(r * 1.5)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(theme.BODY_TEXT if state == "invalid" else theme.TITLE_TEXT))
        painter.drawText(QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r),
                         Qt.AlignCenter, glyph)

    def _paint_pill(
        self, painter, x, cy, text, tone, height, outline=False, center=False
    ) -> float:
        """Draw a rounded verdict pill at ``x`` (or centred); return its right edge."""
        fill, ink = _TONE.get(tone, _TONE["warn"])
        font = QFont(theme.body_font())
        font.setPixelSize(max(1, int(height * 0.58)))
        font.setBold(True)
        fm = QFontMetricsF(font)
        room = theme.NODE_W - 8 - x
        label = fm.elidedText(text, Qt.ElideRight, max(0.0, room - height * 0.8))
        width = min(fm.horizontalAdvance(label) + height * 0.8, room)
        if width <= height * 0.8:
            return x
        if center:
            x = (theme.NODE_W - width) / 2
        rect = QRectF(x, cy - height / 2, width, height)
        if outline:
            painter.setBrush(QBrush(theme.NODE_BG))
            painter.setPen(QPen(fill, 1.2))
            ink = theme.BODY_TEXT
        else:
            painter.setBrush(QBrush(fill))
            painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, height / 2, height / 2)
        painter.setFont(font)
        painter.setPen(QPen(ink))
        painter.drawText(rect, Qt.AlignCenter, label)
        return rect.right()

    def _paint_overview(self, painter, w: float, h: float) -> None:
        """Zoomed out: the body shows only the verdict (or a large state glyph)."""
        top = theme.TITLE_H
        body_h = h - top
        cy = top + body_h / 2
        badge = getattr(self.logic, "badge", None)
        if badge:
            pill_h = min(body_h * 0.42, 34.0)
            notes = getattr(self.logic, "badge_notes", ())
            if notes:
                cy -= pill_h * 0.4
            self._paint_pill(painter, 10, cy, badge[0], badge[1], pill_h, center=True)
            if notes:
                self._paint_pill(painter, 10, cy + pill_h * 0.95, " · ".join(notes),
                                 "warn", pill_h * 0.7, outline=True, center=True)
        else:
            self._paint_state_glyph(
                painter, QPointF(w / 2, cy), min(body_h * 0.25, 16.0), self.logic.state
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


def _status_beside(status: str, badge) -> str:
    """The status line without the segment the verdict pill already shows.

    ``"B-1A · APPROVED ✓ (provisional)"`` beside an ``APPROVED`` pill reads
    ``"B-1A"``; segments are the `` · `` separated parts of the status.
    """
    text = (status or "").replace("\n", " ")
    if not badge:
        return text
    word = badge[0]
    kept = [seg for seg in text.split(" · ") if not seg.strip().startswith(word)]
    return " · ".join(kept) if kept else ""
