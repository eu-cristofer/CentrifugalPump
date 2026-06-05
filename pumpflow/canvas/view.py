"""
canvas.view
===========

A pannable / zoomable view over the node graph.  All interactive edge creation
is handled here (rather than in the scene/ports) so the view keeps full control
of the mouse and there is no grabber ambiguity:

- press on a port  → begin dragging a new link (or re-wire a single input)
- drag             → rubber-band the link to the cursor
- release on a port → connect if compatible (fan-out / merge supported)
- middle / Alt+left drag → pan;  wheel → zoom
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QGraphicsView

from . import theme
from .edge_item import EdgeItem
from .port_item import PortItem


class GraphView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(theme.CANVAS_BG)
        self.setSceneRect(-2400, -1800, 4800, 3600)
        self._zoom = 1.0
        self._panning = False
        self._pan_start = None
        self._temp_edge: Optional[EdgeItem] = None
        self._drag_src: Optional[PortItem] = None

    # -- zoom --------------------------------------------------------------
    def wheelEvent(self, event):
        factor = 1.0015 ** event.angleDelta().y()
        new_zoom = self._zoom * factor
        if 0.3 < new_zoom < 2.8:
            self._zoom = new_zoom
            self.scale(factor, factor)

    # -- port hit testing --------------------------------------------------
    def _port_under(self, view_pos) -> Optional[PortItem]:
        for item in self.items(view_pos):
            if isinstance(item, PortItem):
                return item
        # tolerant fallback (ports are small)
        scene_pos = self.mapToScene(view_pos)
        nearest, best = None, 14.0
        for item in self.scene().items():
            if isinstance(item, PortItem):
                d = item.center_scene() - scene_pos
                dist = (d.x() ** 2 + d.y() ** 2) ** 0.5
                if dist < best:
                    best, nearest = dist, item
        return nearest

    # -- mouse -------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            port = self._port_under(event.position().toPoint())
            if port is not None:
                self._begin_edge(port, self.mapToScene(event.position().toPoint()))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        if self._temp_edge is not None:
            self._temp_edge.set_drag_end(self.mapToScene(event.position().toPoint()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self._pan_start = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        if self._temp_edge is not None:
            target = self._port_under(event.position().toPoint())
            self.scene().removeItem(self._temp_edge)
            self._temp_edge = None
            src = self._drag_src
            self._drag_src = None
            if target is not None and src is not None and target is not src:
                edge = self.scene().connect_ports(src, target)
                if edge is not None:
                    self.scene().evaluate()
                    self.scene().graph_changed.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _begin_edge(self, port: PortItem, scene_pos: QPointF) -> None:
        scene = self.scene()
        # re-wire: dragging off a connected single-input detaches its link
        if (not port.is_output) and (not port.multi) and port.edges:
            edge = port.edges[0]
            src = edge.other(port)
            scene.remove_edge(edge)
        else:
            src = port
        self._drag_src = src
        self._temp_edge = EdgeItem(
            source=src if src.is_output else None,
            target=src if not src.is_output else None,
        )
        scene.addItem(self._temp_edge)
        self._temp_edge.set_drag_end(scene_pos)

    # -- dotted grid -------------------------------------------------------
    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        step = theme.GRID_SIZE
        left = int(rect.left()) - (int(rect.left()) % step)
        top = int(rect.top()) - (int(rect.top()) % step)
        painter.setPen(Qt.NoPen)
        y = top
        while y < rect.bottom():
            x = left
            while x < rect.right():
                strong = (x % (step * 5) == 0) and (y % (step * 5) == 0)
                painter.setBrush(theme.GRID_DOT_STRONG if strong else theme.GRID_DOT)
                r = 1.5 if strong else 1.0
                painter.drawEllipse(QPointF(x, y), r, r)
                x += step
            y += step
