"""
nodes.base
==========

The Qt-agnostic logic of a widget node.  A node declares typed input/output
ports, owns its ``settings`` dict, and implements :meth:`compute` — which reads
the payloads gathered from upstream and returns a ``{output_port: payload}``
dict.  It also sets a one-line :attr:`status` and a :attr:`state`
(``idle`` / ``ok`` / ``invalid`` / ``error`` / ``reject``) that the canvas node
renders (UI_SPEC §3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PortSpec:
    name: str
    signal_type: str
    multi: bool = False


class BaseNode:
    # class-level metadata (overridden by subclasses)
    kind: str = "base"
    title: str = "Node"
    glyph: str = "•"
    is_source: bool = False
    inputs: List[PortSpec] = []
    outputs: List[PortSpec] = []

    def __init__(self):
        self.node_id: str = ""
        self.settings: Dict = self.default_settings()
        self.outputs_cache: Dict[str, object] = {}
        self.status: str = "Not configured"
        self.state: str = "idle"
        self.error: str = ""
        self.item = None  # set by NodeItem

    # -- overridable -------------------------------------------------------
    def default_settings(self) -> Dict:
        return {}

    def compute(self, inputs: Dict[str, list]) -> Dict[str, object]:
        """Return ``{output_port_name: payload}``.  Override me."""
        return {}

    def port_label(self, name: str) -> str:
        return name

    def create_dialog(self, parent, on_change):
        """Return a configured ``QDialog`` (or ``None`` if the node has none)."""
        return None

    # -- runtime -----------------------------------------------------------
    def run(self, inputs: Dict[str, list]) -> None:
        self.error = ""
        outputs = self.compute(inputs) or {}
        self.outputs_cache = outputs

    def set_error(self, message: str) -> None:
        self.error = message
        self.status = message
        self.state = "error"
        self.outputs_cache = {}

    def emit_nothing(self, status: str, state: str = "invalid") -> Dict[str, object]:
        """Helper: clear outputs and show an amber/idle status (UI_SPEC §7)."""
        self.status = status
        self.state = state
        return {}

    # -- helpers for gathering single upstream payloads --------------------
    @staticmethod
    def first(inputs: Dict[str, list], name: str):
        items = inputs.get(name) or []
        return items[0] if items else None

    @staticmethod
    def all_of(inputs: Dict[str, list], name: str) -> list:
        return list(inputs.get(name) or [])

    # -- persistence -------------------------------------------------------
    def serialize_settings(self) -> Dict:
        """Plain-JSON view of ``settings`` for ``.pumpflow`` (override if needed)."""
        return dict(self.settings)

    def load_settings(self, data: Dict) -> None:
        self.settings.update(data or {})
