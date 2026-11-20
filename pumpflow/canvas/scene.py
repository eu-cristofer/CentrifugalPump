"""
canvas.scene
============

The reactive node-graph scene.

- holds :class:`NodeItem` / :class:`EdgeItem`
- handles interactive edge creation (drag from a port to a compatible port),
  supporting **fan-out** (one output → many inputs) and **merge**
  (multi-connection inputs) per UI_SPEC §3
- runs a topological **recompute** of the logic graph whenever anything
  changes, so editing an upstream value live-updates every downstream node
  (UI_SPEC §3 / §7); the ordering and run loop are the Qt-free functions in
  :mod:`pumpflow.engine`
- (de)serializes the whole canvas for ``.pumpflow`` project files (UI_SPEC §6.1)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtWidgets import QGraphicsScene

from . import theme
from .edge_item import EdgeItem
from .node_item import NodeItem
from .port_item import PortItem
from .. import persistence, settings_codec, units
from ..engine import evaluate_in_order, topo_order


class GraphScene(QGraphicsScene):
    graph_changed = Signal()
    dialog_requested = Signal(object)  # emits a BaseNode
    node_removed = Signal(object)  # emits the removed node's BaseNode logic

    def __init__(self, node_factory):
        super().__init__()
        self.setBackgroundBrush(theme.CANVAS_BG)
        self._node_factory = node_factory  # kind -> BaseNode()
        self.nodes: List[NodeItem] = []
        self.edges: List[EdgeItem] = []
        self._uid = 0

    # ------------------------------------------------------------------ nodes
    def add_node(
        self,
        kind: str,
        pos: QPointF,
        node_id: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> NodeItem:
        logic = self._node_factory(kind)
        self._uid += 1
        logic.node_id = node_id or f"{kind}-{self._uid}"
        if settings:
            logic.settings.update(settings)
        item = NodeItem(logic)
        item.setPos(pos)
        self.addItem(item)
        self.nodes.append(item)
        self.graph_changed.emit()
        return item

    def remove_node(self, item: NodeItem) -> None:
        for port in list(item.in_ports.values()) + list(item.out_ports.values()):
            for edge in list(port.edges):
                self.remove_edge(edge)
        if item in self.nodes:
            self.nodes.remove(item)
        self.removeItem(item)
        self.node_removed.emit(item.logic)

    def node_by_id(self, node_id: str) -> Optional[NodeItem]:
        for n in self.nodes:
            if n.logic.node_id == node_id:
                return n
        return None

    # ------------------------------------------------------------------ edges
    def connect_ports(self, src: PortItem, dst: PortItem) -> Optional[EdgeItem]:
        """Connect an output port to an input port (orientation-tolerant)."""
        out_port = src if src.is_output else dst
        in_port = dst if src.is_output else src
        if not out_port.can_accept(in_port):
            return None
        edge = EdgeItem(out_port, in_port)
        self.addItem(edge)
        edge.attach()
        self.edges.append(edge)
        self.graph_changed.emit()
        return edge

    def remove_edge(self, edge: EdgeItem) -> None:
        edge.detach()
        if edge in self.edges:
            self.edges.remove(edge)
        self.removeItem(edge)

    def dispose(self) -> None:
        """Empty the scene in a controlled way before it is discarded.

        ``EdgeItem`` is a ``QGraphicsPathItem`` (not a QObject): if Qt deletes
        it together with the scene, its Python wrapper is not told and may be
        freed a second time when the node <-> logic reference cycles are
        collected, corrupting the heap (seen as a segfault in a *later* test on
        PySide6 6.12).  Removing every item first hands ownership back to
        Python, and clearing ``logic.item`` breaks the cycles.
        """
        for edge in list(self.edges):
            self.remove_edge(edge)
        for node in list(self.nodes):
            self.nodes.remove(node)
            self.removeItem(node)
            if getattr(node.logic, "item", None) is node:
                node.logic.item = None

    # -- delete selection --------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in list(self.selectedItems()):
                if isinstance(item, EdgeItem):
                    self.remove_edge(item)
            for item in list(self.selectedItems()):
                if isinstance(item, NodeItem):
                    self.remove_node(item)
            self.evaluate()
            self.graph_changed.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------- dialogs
    def open_node_dialog(self, item: NodeItem) -> None:
        self.dialog_requested.emit(item.logic)

    # ------------------------------------------------------ reactive eval
    def _topo_order(self) -> List[NodeItem]:
        links = [
            (edge.source.node, edge.target.node)
            for edge in self.edges
            if edge.source is not None and edge.target is not None
        ]
        return topo_order(self.nodes, links)

    def _gather_inputs(self, item: NodeItem) -> Dict[str, list]:
        bundle: Dict[str, list] = {spec.name: [] for spec in item.logic.inputs}
        for name, in_port in item.in_ports.items():
            for edge in in_port.edges:
                src = edge.source
                if src is None:
                    continue
                payload = src.node.logic.outputs_cache.get(src.name)
                if payload is not None:
                    bundle[name].append(payload)
        return bundle

    def evaluate(self) -> None:
        """Recompute every node in topological order and refresh the canvas."""
        evaluate_in_order(
            self._topo_order(), self._gather_inputs, after=lambda item: item.refresh()
        )

    # ------------------------------------------------------ serialization
    def to_dict(self) -> dict:
        """Serialize the canvas as a schema-v2 project document.

        Node runtime settings are translated to the on-disk shape by
        :func:`pumpflow.settings_codec.encode` (``{"value", "unit"}`` quantities).
        """
        return {
            # Project-level display preference (the active unit preset) plus the
            # schema version. Plain magnitudes + units live on each node; the
            # preset only chooses how fresh fields are labelled (units.PREFS).
            "meta": {
                **units.PREFS.to_dict(),
                "schema_version": persistence.SCHEMA_VERSION,
            },
            "nodes": [
                {
                    "id": n.logic.node_id,
                    "kind": n.logic.kind,
                    "x": n.pos().x(),
                    "y": n.pos().y(),
                    "settings": settings_codec.encode(
                        n.logic.kind, n.logic.serialize_settings()
                    ),
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "src_node": e.source.node.logic.node_id,
                    "src_port": e.source.name,
                    "dst_node": e.target.node.logic.node_id,
                    "dst_port": e.target.name,
                }
                for e in self.edges
                if e.source and e.target
            ],
        }

    def load_dict(self, doc: dict) -> None:
        """Rebuild the canvas from a project document (v1 is migrated to v2)."""
        doc = persistence.migrate(doc)
        # Restore the unit preset *before* nodes are built so their
        # default_settings seed fresh fields in the project's display units.
        # An empty/new project (no "meta") resets to the SI default.
        units.PREFS.load(doc.get("meta"))
        for edge in list(self.edges):
            self.remove_edge(edge)
        for node in list(self.nodes):
            self.remove_node(node)
        for nd in doc.get("nodes", []):
            self.add_node(
                nd["kind"],
                QPointF(nd.get("x", 0), nd.get("y", 0)),
                node_id=nd.get("id"),
                settings=settings_codec.decode(nd["kind"], nd.get("settings") or {}),
            )
        for ed in doc.get("edges", []):
            up = self.node_by_id(ed["src_node"])
            down = self.node_by_id(ed["dst_node"])
            if not up or not down:
                continue
            src = up.out_ports.get(ed["src_port"])
            dst = down.in_ports.get(ed["dst_port"])
            if src and dst:
                self.connect_ports(src, dst)
        self.evaluate()
