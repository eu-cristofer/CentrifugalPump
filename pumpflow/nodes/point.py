"""
nodes.point — Point

Source node.  A single ad-hoc Q/H/P/η measurement the user drops on the canvas
to overlay on the Performance Explorer (a guarantee point, a re-test point, a
datasheet value).  Emits a :class:`~pumpflow.signals.PointSample`.

Unlike the Test Points Table — which holds the raw measured rows of a FAT and
derives head/η from suction/discharge pressures — a Point carries the plotted
quantities directly, so it is a lightweight marker rather than a measurement to
correct.
"""

from __future__ import annotations

from typing import Dict

from ..signals import PointSample
from .base import BaseNode, PortSpec
from . import ui


class PointNode(BaseNode):
    kind = "point"
    title = "Point"
    glyph = "•"
    is_source = True
    inputs = []
    outputs = [PortSpec("Point", "PointSample")]

    def default_settings(self) -> Dict:
        return {"label": "Point", "q": 800.0, "head": 75.0, "power": 0.0, "eff": 0.0}

    # -- payload -----------------------------------------------------------
    def to_signal(self) -> PointSample:
        s = self.settings
        return PointSample(
            label=str(s.get("label", "Point")).strip() or "Point",
            q_m3h=float(s.get("q") or 0.0),
            head_m=_opt(s.get("head")),
            power_kw=_opt(s.get("power")),
            efficiency_pct=_opt(s.get("eff")),
        )

    def compute(self, inputs) -> Dict[str, object]:
        pt = self.to_signal()
        if pt.q_m3h < 0:
            return self.emit_nothing("Capacity Q must be ≥ 0 m³/h.", "invalid")
        bits = [f"Q={pt.q_m3h:g}"]
        if pt.head_m is not None:
            bits.append(f"H={pt.head_m:g}")
        self.status = f"{pt.label} · " + " · ".join(bits)
        self.state = "ok"
        return {"Point": pt}

    def port_label(self, name: str) -> str:
        return "Point"

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Point",
            "A single ad-hoc point to overlay on the Performance Explorer.",
            width=420,
        )

        label = ui.line_edit(s.get("label", "Point"), None, "marker label")
        label.textChanged.connect(lambda v: (s.__setitem__("label", v), on_change()))
        q = ui.spin(s.get("q") or 0, 0, 1e6, 1, 2, None)
        q.valueChanged.connect(lambda v: (s.__setitem__("q", v), on_change()))
        head = ui.spin(s.get("head") or 0, 0, 1e5, 1, 2, None)
        head.valueChanged.connect(lambda v: (s.__setitem__("head", v), on_change()))
        power = ui.spin(s.get("power") or 0, 0, 1e5, 1, 2, None)
        power.valueChanged.connect(lambda v: (s.__setitem__("power", v), on_change()))
        eff = ui.spin(s.get("eff") or 0, 0, 100, 0.5, 1, None)
        eff.valueChanged.connect(lambda v: (s.__setitem__("eff", v), on_change()))

        dlg.add(ui.section("Marker"))
        dlg.add(ui.row("Label", label))
        dlg.add(ui.hline())
        dlg.add(ui.section("Values"))
        dlg.add(ui.row("Capacity  Q", q, "m³/h"))
        dlg.add(ui.row("Head  H", head, "m"))
        dlg.add(ui.row("Power  P", power, "kW"))
        dlg.add(ui.row("Efficiency  η", eff, "%"))
        return dlg


def _opt(v):
    """Return a positive float, or ``None`` when blank/zero/non-numeric."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None
