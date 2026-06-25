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
  (UI_SPEC §3 / §7)
- (de)serializes the whole canvas for ``.pumpflow`` project files (UI_SPEC §6.1)
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtWidgets import QGraphicsScene

from . import theme
from .edge_item import EdgeItem
from .node_item import NodeItem
from .port_item import PortItem
from .. import units


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
        index = {n: i for i, n in enumerate(self.nodes)}
        indeg = {n: 0 for n in self.nodes}
        succ = defaultdict(list)
        for edge in self.edges:
            if edge.source is None or edge.target is None:
                continue
            up = edge.source.node
            down = edge.target.node
            succ[up].append(down)
            indeg[down] += 1
        queue = deque(sorted((n for n in self.nodes if indeg[n] == 0), key=index.get))
        order, seen = [], set()
        while queue:
            n = queue.popleft()
            if n in seen:
                continue
            seen.add(n)
            order.append(n)
            for m in succ[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
        for n in self.nodes:  # any leftover (cycles) appended stably
            if n not in seen:
                order.append(n)
        return order

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
        for item in self._topo_order():
            inputs = self._gather_inputs(item)
            try:
                item.logic.run(inputs)
            except Exception as exc:  # surface as a node error (UI_SPEC §7)
                item.logic.set_error(str(exc))
            item.refresh()

    # ------------------------------------------------------ serialization
    def to_dict(self) -> dict:
        return {
            # Project-level display preference (the active unit preset). Plain
            # magnitudes still live on each node; this only chooses how fresh
            # fields are labelled (units.PREFS — multi-unit philosophy).
            "meta": units.PREFS.to_dict(),
            "nodes": [
                {
                    "id": n.logic.node_id,
                    "kind": n.logic.kind,
                    "x": n.pos().x(),
                    "y": n.pos().y(),
                    "settings": n.logic.serialize_settings(),
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
                settings=nd.get("settings"),
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
