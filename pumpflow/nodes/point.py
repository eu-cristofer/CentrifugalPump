"""
nodes.point — Point

Source node.  A single ad-hoc Q/H/P/η measurement the user drops on the canvas
to overlay on the Performance Explorer (a guarantee point, a re-test point, a
datasheet value).  Emits a :class:`~pumpflow.signals.PointSample`.

Unlike the Test Points Table — which holds the raw measured rows of a FAT and
derives head/η from suction/discharge pressures — a Point carries the plotted
quantities directly, so it is a lightweight marker rather than a measurement to
correct.

Q/H/P/η (and the suction/discharge pressures) accept any display unit via the
reusable ``ui.UnitField`` / ``ui.PressureField`` widgets; the emitted
``PointSample`` carries Pint Quantities normalised to m³/h/m/kW/%, so the
marker lands in the same physical spot regardless of the units typed.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pump import Q_, Pressure

from .. import units
from ..binding import head_from_pressures
from ..signals import PointSample
from .base import BaseNode, PortSpec
from .fluidpick import choice_options, current_choice, resolve_fluid
from . import ui


def _p_label(s) -> str:
    """The stored pressure display label, tolerating legacy Pint-string values."""
    raw = s.get("p_unit") or units.PREFS.default_unit("pressure")
    labels = [lab for lab, _ in units.UNIT_OPTIONS["pressure"]]
    if raw in labels:
        return raw
    return units.label_for("pressure", raw) or "bar"


def _unit_combo(pf):
    """The unit combo of a ``ui.PressureField`` (tolerant of its internals)."""
    c = getattr(pf, "combo", None)
    if c is None:
        inner = getattr(pf, "field", None) or getattr(pf, "unit_field", None)
        c = getattr(inner, "combo", None)
    return c


def _ref_combo(pf):
    for name in ("ref_combo", "ref_cb", "gauge_combo"):
        c = getattr(pf, name, None)
        if c is not None:
            return c
    return None


class PointNode(BaseNode):
    kind = "point"
    title = "Point"
    glyph = "•"
    is_source = True
    # Optional Fluid input (multi): in "pressures" mode the chosen fluid's density
    # derives Head from suction/discharge pressures (UC-00).  No "own fluid", so
    # the picker lists only the wired fluids.
    inputs = [PortSpec("FluidSpec", "FluidSpec", multi=True)]
    outputs = [PortSpec("Point", "PointSample")]

    def default_settings(self) -> Dict:
        p = units.PREFS
        qu = p.default_unit("capacity")
        hu = p.default_unit("head")
        pu = p.default_unit("power")
        pru = p.default_unit("pressure")
        eu = p.default_unit("efficiency")
        return {
            "label": "Point",
            "mode": "direct",  # "direct" | "pressures"
            "q": units.convert_display(800.0, "capacity", "m³/h", qu),
            "q_unit": qu,
            "head": units.convert_display(75.0, "head", "m", hu),
            "head_unit": hu,
            "p_suc": units.convert_display(0.5, "pressure", "bar", pru),
            "p_dis": units.convert_display(8.0, "pressure", "bar", pru),
            "p_unit": pru,
            "p_ref": "g",
            "fluid_choice": "",  # ""=first wired (default), or a fluid name
            "power": 0.0,
            "power_unit": pu,
            "eff": 0.0,
            "eff_unit": eu,
        }

    # -- payload -----------------------------------------------------------
    def _head_from_pressures(self, fluid_density):
        """Derive head (m) from suction/discharge pressures + fluid density."""
        if fluid_density is None:
            return None
        s = self.settings
        pint = units.pint_str("pressure", _p_label(s))
        ref = s.get("p_ref") or "g"
        p_suc = Pressure(Q_(float(s.get("p_suc") or 0.0), pint), ref)
        p_dis = Pressure(Q_(float(s.get("p_dis") or 0.0), pint), ref)
        return head_from_pressures(p_suc, p_dis, fluid_density)

    def to_signal(self, fluid_density=None) -> PointSample:
        s = self.settings
        if s.get("mode") == "pressures":
            head = self._head_from_pressures(fluid_density)
        else:
            head = _std_opt(s.get("head"), "head", s.get("head_unit") or "m", "m")
        eff = _opt(s.get("eff"))
        eff_unit = s.get("eff_unit") or "%"
        return PointSample(
            label=str(s.get("label", "Point")).strip() or "Point",
            q=Q_(
                units.to_standard(
                    float(s.get("q") or 0.0), "capacity", s.get("q_unit") or "m³/h"
                ),
                "m**3/h",
            ),
            head=head,
            power=_std_opt(s.get("power"), "power", s.get("power_unit") or "kW", "kW"),
            efficiency=(
                None
                if eff is None
                else Q_(eff, units.pint_str("efficiency", eff_unit)).to("percent")
            ),
        )

    def compute(self, inputs) -> Dict[str, object]:
        self._fluids = self.all_of(inputs, "FluidSpec")
        chosen = resolve_fluid(self._fluids, self.settings.get("fluid_choice"))
        self._fluid_density = chosen.density if chosen is not None else None
        pt = self.to_signal(self._fluid_density)
        q_m3h = pt.q.to("m**3/h").magnitude
        if q_m3h < 0:
            return self.emit_nothing("Capacity Q must be ≥ 0 m³/h.", "invalid")
        if self.settings.get("mode") == "pressures" and chosen is None:
            return self.emit_nothing(
                "Connect/select a Fluid node to derive head from pressures.", "invalid"
            )
        bits = [f"Q={q_m3h:g}"]
        if pt.head is not None:
            bits.append(f"H={pt.head.to('m').magnitude:g}")
        fl = f" · {chosen.name}" if chosen is not None else ""
        self.status = f"{pt.label} · " + " · ".join(bits) + fl
        self.state = "ok"
        return {"Point": pt}

    def port_label(self, name: str) -> str:
        return "Fluid" if name == "FluidSpec" else "Point"

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
        eff_field = ui.UnitField(
            "efficiency",
            s.get("eff") or 0,
            s.get("eff_unit"),
            on_change=lambda: apply(),
            hi=100,
            step=0.5,
            decimals=3,
        )

        # Head source: direct value, or derived from suction/discharge pressures
        # (the latter needs a connected Fluid node for the density).
        mode = ui.combo(
            [("Direct head", "direct"), ("From pressures + fluid", "pressures")],
            s.get("mode", "direct"),
            None,
        )
        p_unit0 = _p_label(s)
        p_ref0 = s.get("p_ref") or "g"
        p_suc = ui.PressureField(
            s.get("p_suc") or 0,
            p_unit0,
            p_ref0,
            on_change=lambda: on_pressure(p_suc),
            hi=1e5,
            step=0.1,
            decimals=3,
        )
        p_dis = ui.PressureField(
            s.get("p_dis") or 0,
            p_unit0,
            p_ref0,
            on_change=lambda: on_pressure(p_dis),
            hi=1e5,
            step=0.1,
            decimals=3,
        )
        _guard = {"busy": False}

        def on_pressure(src):
            """Keep both pressure fields on one shared unit and g/a reference."""
            if _guard["busy"]:
                return
            other = p_dis if src is p_suc else p_suc
            _guard["busy"] = True
            try:
                if other.unit_label() != src.unit_label():
                    cb = _unit_combo(other)
                    if cb is not None:
                        i = cb.findData(src.unit_label())
                        if i >= 0:
                            cb.setCurrentIndex(i)
                if other.ref() != src.ref():
                    cb = _ref_combo(other)
                    if cb is not None:
                        i = cb.findData(src.ref())
                        if i >= 0:
                            cb.setCurrentIndex(i)
            finally:
                _guard["busy"] = False
            apply()

        # Fluid picker (pressures mode) — Point has no own fluid, so wired-only.
        fluids = getattr(self, "_fluids", [])
        fluid_pick = ui.combo(
            choice_options(fluids, None),
            current_choice(fluids, s.get("fluid_choice")),
            None,
        )

        direct_box = QWidget()
        dbl = QVBoxLayout(direct_box)
        dbl.setContentsMargins(0, 0, 0, 0)
        dbl.addWidget(head_field.row("Head  H"))

        press_box = QWidget()
        pbl = QVBoxLayout(press_box)
        pbl.setContentsMargins(0, 0, 0, 0)
        pbl.addWidget(p_suc.row("Suction  P_suc"))
        pbl.addWidget(p_dis.row("Discharge  P_dis"))
        if fluids:
            pbl.addWidget(ui.row("Fluid", fluid_pick))

        def refresh_mode():
            press = mode.currentData() == "pressures"
            direct_box.setVisible(not press)
            press_box.setVisible(press)

        def apply():
            s["q"], s["q_unit"] = q_field.magnitude(), q_field.unit_label()
            s["head"], s["head_unit"] = head_field.magnitude(), head_field.unit_label()
            s["power"], s["power_unit"] = (
                power_field.magnitude(),
                power_field.unit_label(),
            )
            s["eff"], s["eff_unit"] = eff_field.magnitude(), eff_field.unit_label()
            s["mode"] = mode.currentData()
            s["p_suc"], s["p_dis"] = p_suc.magnitude(), p_dis.magnitude()
            s["p_unit"] = p_suc.unit_label()
            s["p_ref"] = p_suc.ref()
            s["fluid_choice"] = fluid_pick.currentData() or ""
            refresh_mode()
            on_change()

        label = ui.line_edit(s.get("label", "Point"), None, "marker label")
        label.textChanged.connect(lambda v: (s.__setitem__("label", v), on_change()))
        mode.currentIndexChanged.connect(lambda _=None: apply())
        fluid_pick.currentIndexChanged.connect(lambda _=None: apply())

        dlg.add(ui.section("Marker"))
        dlg.add(ui.row("Label", label))
        dlg.add(ui.hline())
        dlg.add(ui.section("Values"))
        dlg.add(q_field.row("Capacity  Q"))
        dlg.add(ui.row("Head source", mode))
        dlg.add(direct_box)
        dlg.add(press_box)
        dlg.add(power_field.row("Power  P"))
        dlg.add(eff_field.row("Efficiency  η"))
        apply()
        return dlg


def _opt(v):
    """Return a positive float, or ``None`` when blank/zero/non-numeric."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _std_opt(value, dimension: str, unit: str, out_unit: str):
    """``_opt``, normalise to the standard unit and wrap as a Quantity in
    ``out_unit`` — ``None`` stays ``None``."""
    v = _opt(value)
    return None if v is None else Q_(units.to_standard(v, dimension, unit), out_unit)
