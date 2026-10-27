"""
canvas.view
===========

A pannable / zoomable view over the node graph.  All interactive edge creation
is handled here (rather than in the scene/ports) so the view keeps full control
of the mouse and there is no grabber ambiguity:

- press on a port  → begin dragging a new link (or re-wire a single input)
- drag             → rubber-band the link to the cursor
- release on a port → connect if compatible (fan-out / merge supported)
- two-finger / plain scroll → pan;  Ctrl+scroll or pinch → zoom
- middle / Alt+left drag → pan
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QTransform
from PySide6.QtWidgets import QGraphicsView

from . import theme
from .edge_item import EdgeItem
from .port_item import PortItem

# Zoom band shared by the wheel handler and the fit/restore helpers.
ZOOM_MIN = 0.3
ZOOM_MAX = 2.8


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

    # -- zoom / pan (wheel + touchpad) -------------------------------------
    def _zoom_by(self, factor: float) -> None:
        """Apply a multiplicative zoom about the cursor, clamped to the band."""
        new_zoom = self._zoom * factor
        if ZOOM_MIN < new_zoom < ZOOM_MAX:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def _pan_by(self, dx: float, dy: float) -> None:
        """Scroll the viewport by a pixel delta (touchpad / plain wheel pan)."""
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - int(dx)
        )
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() - int(dy)
        )

    def wheelEvent(self, event):
        # Figma-style: Ctrl/Cmd + scroll zooms; a bare two-finger / mouse-wheel
        # scroll pans.  Pinch arrives separately as a native gesture (see event()).
        if event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
            delta = event.angleDelta().y() or event.pixelDelta().y()
            self._zoom_by(1.0015 ** delta)
            event.accept()
            return

        # High-resolution touchpads report pixelDelta; classic wheels only
        # angleDelta (vertical steps of 120, plus horizontal on tilt/two-finger).
        pixel = event.pixelDelta()
        if not pixel.isNull():
            self._pan_by(pixel.x(), pixel.y())
        else:
            angle = event.angleDelta()
            self._pan_by(angle.x(), angle.y())
        event.accept()

    def event(self, event):
        # Trackpad pinch → zoom about the cursor.
        if event.type() == QEvent.NativeGesture and self._handle_native_gesture(event):
            return True
        return super().event(event)

    def _handle_native_gesture(self, event) -> bool:
        if event.gestureType() == Qt.ZoomNativeGesture:
            self._zoom_by(1.0 + event.value())
            return True
        return False

    # -- view state (fit-to-extents + persist/restore last zoom) -----------
    def fit_to_contents(self) -> None:
        """Frame every node in the view (zoom extents), clamped to the zoom band.

        Used when a fresh canvas or a bundled example is loaded so the whole
        pipeline is visible without manual panning.  Falls back to 100 % at the
        origin when the scene is empty.
        """
        rect = self.scene().itemsBoundingRect() if self.scene() else QRectF()
        if rect.isNull() or rect.isEmpty():
            self.resetTransform()
            self._zoom = 1.0
            self.centerOn(0, 0)
            return
        self.fitInView(rect.adjusted(-80, -80, 80, 80), Qt.KeepAspectRatio)
        scale = self.transform().m11()
        if scale < ZOOM_MIN or scale > ZOOM_MAX:
            scale = min(max(scale, ZOOM_MIN), ZOOM_MAX)
            self.setTransform(QTransform().scale(scale, scale))
            self.centerOn(rect.center())
        self._zoom = self.transform().m11()

    def view_state(self) -> dict:
        """Capture the current zoom + scene-space center for ``.pumpflow`` files."""
        center = self.mapToScene(self.viewport().rect().center())
        return {"zoom": self.transform().m11(), "cx": center.x(), "cy": center.y()}

    def apply_view_state(self, state: dict) -> None:
        """Restore a zoom + center previously captured by :meth:`view_state`."""
        if not state:
            self.fit_to_contents()
            return
        zoom = min(max(float(state.get("zoom", 1.0)), ZOOM_MIN), ZOOM_MAX)
        self.setTransform(QTransform().scale(zoom, zoom))
        self.centerOn(float(state.get("cx", 0.0)), float(state.get("cy", 0.0)))
        self._zoom = zoom

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
