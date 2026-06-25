"""
nodes.point — Point

Source node.  A single ad-hoc Q/H/P/η measurement the user drops on the canvas
to overlay on the Performance Explorer (a guarantee point, a re-test point, a
datasheet value).  Emits a :class:`~pumpflow.signals.PointSample`.

Unlike the Test Points Table — which holds the raw measured rows of a FAT and
derives head/η from suction/discharge pressures — a Point carries the plotted
quantities directly, so it is a lightweight marker rather than a measurement to
correct.

Q/H/P accept any display unit via the reusable ``ui.UnitField`` widget; the
emitted ``PointSample`` is always normalised to m³/h/m/kW, so the marker lands
in the same physical spot regardless of the units typed.
"""

from __future__ import annotations

from typing import Dict

from .. import units
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
        p = units.PREFS
        qu = p.default_unit("capacity")
        hu = p.default_unit("head")
        pu = p.default_unit("power")
        return {
            "label": "Point",
            "q": units.convert_display(800.0, "capacity", "m³/h", qu),
            "q_unit": qu,
            "head": units.convert_display(75.0, "head", "m", hu),
            "head_unit": hu,
            "power": 0.0,
            "power_unit": pu,
            "eff": 0.0,
        }

    # -- payload -----------------------------------------------------------
    def to_signal(self) -> PointSample:
        s = self.settings
        return PointSample(
            label=str(s.get("label", "Point")).strip() or "Point",
            q_m3h=units.to_standard(
                float(s.get("q") or 0.0), "capacity", s.get("q_unit") or "m³/h"
            ),
            head_m=_std_opt(s.get("head"), "head", s.get("head_unit") or "m"),
            power_kw=_std_opt(s.get("power"), "power", s.get("power_unit") or "kW"),
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

        q_field = ui.UnitField(
            "capacity",
            s.get("q") or 0,
            s.get("q_unit"),
            on_change=lambda: apply(),
            hi=1e6,
            step=1,
            decimals=2,
        )
        head_field = ui.UnitField(
            "head",
            s.get("head") or 0,
            s.get("head_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=1,
            decimals=2,
        )
        power_field = ui.UnitField(
            "power",
            s.get("power") or 0,
            s.get("power_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=1,
            decimals=2,
        )
        eff = ui.spin(s.get("eff") or 0, 0, 100, 0.5, 1, None)

        def apply():
            s["q"], s["q_unit"] = q_field.magnitude(), q_field.unit_label()
            s["head"], s["head_unit"] = head_field.magnitude(), head_field.unit_label()
            s["power"], s["power_unit"] = (
                power_field.magnitude(),
                power_field.unit_label(),
            )
            s["eff"] = eff.value()
            on_change()

        label = ui.line_edit(s.get("label", "Point"), None, "marker label")
        label.textChanged.connect(lambda v: (s.__setitem__("label", v), on_change()))
        eff.valueChanged.connect(lambda _=None: apply())

        dlg.add(ui.section("Marker"))
        dlg.add(ui.row("Label", label))
        dlg.add(ui.hline())
        dlg.add(ui.section("Values"))
        dlg.add(q_field.row("Capacity  Q"))
        dlg.add(head_field.row("Head  H"))
        dlg.add(power_field.row("Power  P"))
        dlg.add(ui.row("Efficiency  η", eff, "%"))
        return dlg


def _opt(v):
    """Return a positive float, or ``None`` when blank/zero/non-numeric."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _std_opt(value, dimension: str, unit: str):
    """``_opt`` then normalise to the standard unit — ``None`` stays ``None``."""
    v = _opt(value)
    return None if v is None else units.to_standard(v, dimension, unit)
