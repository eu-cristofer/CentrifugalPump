"""
engine
======

The Qt-free graph engine.

- pure algorithms shared by every front end: :func:`topo_order` (Kahn, stable by
  insertion index, cycle leftovers appended) and :func:`evaluate_in_order`
  (run each node, capture exceptions as node errors)
- :class:`Graph`, a headless project graph of :class:`BaseNode` logic objects
  and :class:`Edge` links, with the same wiring rules, input gathering and
  schema-v2 (de)serialisation as the canvas ``GraphScene``

The desktop canvas, the export CLI, the tests and the browser (002_web) all
evaluate through this module, so there is exactly one implementation.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Sequence, Tuple

from . import persistence, settings_codec, units

if TYPE_CHECKING:
    from .nodes.base import BaseNode


def topo_order(nodes: Sequence, links: Sequence[Tuple[object, object]]) -> list:
    """Topological order of ``nodes`` for ``links`` given as ``(up, down)`` pairs.

    Kahn's algorithm; the initial queue is sorted by insertion index so the
    result is stable.  Nodes left over by a cycle are appended in insertion
    order, so every node is always returned exactly once.

    >>> topo_order(["a", "b", "c"], [("c", "a")])
    ['b', 'c', 'a']
    """
    nodes = list(nodes)
    index = {n: i for i, n in enumerate(nodes)}
    indeg = {n: 0 for n in nodes}
    succ = defaultdict(list)
    for up, down in links:
        succ[up].append(down)
        indeg[down] += 1
    queue = deque(sorted((n for n in nodes if indeg[n] == 0), key=index.get))
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
    for n in nodes:  # any leftover (cycles) appended stably
        if n not in seen:
            order.append(n)
    return order


def evaluate_in_order(
    order: Sequence,
    gather: Callable[[object], Dict[str, list]],
    after: Optional[Callable[[object], None]] = None,
) -> None:
    """Run every node of ``order``; an exception becomes the node's error.

    Each element is a ``BaseNode`` or an object exposing one as ``.logic``.
    ``gather(node)`` returns the input bundle; ``after(node)`` (optional) is
    called once the node has run, e.g. to refresh a canvas item.
    """
    for node in order:
        logic = getattr(node, "logic", node)
        inputs = gather(node)
        try:
            logic.run(inputs)
        except Exception as exc:  # surface as a node error (UI_SPEC §7)
            logic.set_error(str(exc))
        if after is not None:
            after(node)


@dataclass(frozen=True)
class Edge:
    """A link from an output port to an input port, by node id and port name."""

    src_node: str
    src_port: str
    dst_node: str
    dst_port: str


class Graph:
    """A headless project graph (no Qt)."""

    def __init__(self) -> None:
        self.nodes: List["BaseNode"] = []
        self.edges: List[Edge] = []
        self.positions: Dict[str, Tuple[float, float]] = {}
        self._by_id: Dict[str, "BaseNode"] = {}
        self._uid = 0

    # ------------------------------------------------------------------ nodes
    def add_node(
        self,
        kind: str,
        node_id: Optional[str] = None,
        settings: Optional[dict] = None,
        pos: Optional[Tuple[float, float]] = None,
    ) -> "BaseNode":
        """Create a node of ``kind`` (via the registry) and append it."""
        from .nodes.registry import make_node

        logic = make_node(kind)
        self._uid += 1
        logic.node_id = node_id or f"{kind}-{self._uid}"
        if settings:
            logic.settings.update(settings)
        self.nodes.append(logic)
        self._by_id.setdefault(logic.node_id, logic)
        if pos is not None:
            self.positions[logic.node_id] = (float(pos[0]), float(pos[1]))
        return logic

    def node_by_id(self, node_id: str) -> Optional["BaseNode"]:
        return self._by_id.get(node_id)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and every edge touching it (unknown id is ignored)."""
        node = self._by_id.get(node_id)
        if node is None:
            return
        self.edges = [e for e in self.edges if node_id not in (e.src_node, e.dst_node)]
        self.nodes = [n for n in self.nodes if n is not node]
        del self._by_id[node_id]
        self.positions.pop(node_id, None)
        for n in self.nodes:  # a duplicate id may remain: re-index it
            if n.node_id == node_id:
                self._by_id[node_id] = n
                break

    # ------------------------------------------------------------------ edges
    def connect(
        self, src_id: str, src_port: str, dst_id: str, dst_port: str
    ) -> Optional[Edge]:
        """Wire an output port to an input port, like ``PortItem.can_accept``.

        Raises :class:`ValueError` for unknown nodes or ports (the source must be
        an output, the destination an input) and for mismatched signal types
        (``"*"`` matches anything).  Returns ``None`` (no change) for a duplicate
        edge, a same-node link, or a single-connection input already wired.
        """
        src = self._by_id.get(src_id)
        dst = self._by_id.get(dst_id)
        if src is None:
            raise ValueError(f"Unknown node: {src_id!r}")
        if dst is None:
            raise ValueError(f"Unknown node: {dst_id!r}")
        out_spec = next((s for s in src.outputs if s.name == src_port), None)
        if out_spec is None:
            raise ValueError(f"{src_id!r} has no output port {src_port!r}")
        in_spec = next((s for s in dst.inputs if s.name == dst_port), None)
        if in_spec is None:
            raise ValueError(f"{dst_id!r} has no input port {dst_port!r}")
        a, b = out_spec.signal_type, in_spec.signal_type
        if a != "*" and b != "*" and a != b:
            raise ValueError(f"Signal type mismatch: {a!r} -> {b!r}")
        if src is dst:
            return None
        edge = Edge(src_id, src_port, dst_id, dst_port)
        if edge in self.edges:
            return None
        if not in_spec.multi and any(
            e.dst_node == dst_id and e.dst_port == dst_port for e in self.edges
        ):
            return None
        self.edges.append(edge)
        return edge

    def disconnect(
        self, src_id: str, src_port: str, dst_id: str, dst_port: str
    ) -> None:
        """Remove one edge (a missing edge is ignored)."""
        edge = Edge(src_id, src_port, dst_id, dst_port)
        if edge in self.edges:
            self.edges.remove(edge)

    # ------------------------------------------------------------ evaluation
    def topo_order(self) -> List["BaseNode"]:
        links = [
            (self._by_id[e.src_node], self._by_id[e.dst_node])
            for e in self.edges
            if e.src_node in self._by_id and e.dst_node in self._by_id
        ]
        return topo_order(self.nodes, links)

    def gather_inputs(self, node: "BaseNode") -> Dict[str, list]:
        """Upstream payloads per input port, in the order edges were connected."""
        bundle: Dict[str, list] = {spec.name: [] for spec in node.inputs}
        for spec in node.inputs:
            for e in self.edges:
                if e.dst_node != node.node_id or e.dst_port != spec.name:
                    continue
                src = self._by_id.get(e.src_node)
                if src is None:
                    continue
                payload = src.outputs_cache.get(e.src_port)
                if payload is not None:
                    bundle[spec.name].append(payload)
        return bundle

    def evaluate(self) -> None:
        """Recompute every node in topological order."""
        evaluate_in_order(self.topo_order(), self.gather_inputs)

    # ------------------------------------------------------- serialization
    @classmethod
    def from_dict(cls, doc: dict) -> "Graph":
        """Build a graph from a project document (v1 is migrated to v2).

        The graph is **not** evaluated; call :meth:`evaluate`.
        """
        doc = persistence.migrate(doc)
        # Restore the unit preset before nodes are built so their default
        # settings seed fresh fields in the project's display units.
        units.PREFS.load(doc.get("meta"))
        graph = cls()
        for nd in doc.get("nodes", []):
            node = graph.add_node(
                nd["kind"],
                node_id=nd.get("id"),
                settings=settings_codec.decode(nd["kind"], nd.get("settings") or {}),
            )
            graph.positions[node.node_id] = (
                float(nd.get("x", 0)),
                float(nd.get("y", 0)),
            )
        for ed in doc.get("edges", []):
            try:
                graph.connect(
                    ed["src_node"], ed["src_port"], ed["dst_node"], ed["dst_port"]
                )
            except ValueError:
                continue  # missing node / port: skipped, like the canvas
        return graph

    def to_dict(self, view: Optional[dict] = None) -> dict:
        """Serialize as a schema-v2 project document (same as ``GraphScene``)."""
        doc = {
            "meta": {
                **units.PREFS.to_dict(),
                "schema_version": persistence.SCHEMA_VERSION,
            },
            "nodes": [
                {
                    "id": n.node_id,
                    "kind": n.kind,
                    "x": self.positions.get(n.node_id, (0.0, 0.0))[0],
                    "y": self.positions.get(n.node_id, (0.0, 0.0))[1],
                    "settings": settings_codec.encode(n.kind, n.serialize_settings()),
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "src_node": e.src_node,
                    "src_port": e.src_port,
                    "dst_node": e.dst_node,
                    "dst_port": e.dst_port,
                }
                for e in self.edges
            ],
        }
        if view is not None:
            doc["view"] = view
        return doc
