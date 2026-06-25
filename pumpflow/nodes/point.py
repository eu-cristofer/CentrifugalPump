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

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .. import units
from ..binding import G, pressure_to_pa
from ..signals import PointSample
from .base import BaseNode, PortSpec
from .fluidpick import choice_options, current_choice, resolve_fluid
from . import ui


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
        return {
            "label": "Point",
            "mode": "direct",  # "direct" | "pressures"
            "q": units.convert_display(800.0, "capacity", "m³/h", qu),
            "q_unit": qu,
            "head": units.convert_display(75.0, "head", "m", hu),
            "head_unit": hu,
            "p_suc": 0.5,
            "p_dis": 8.0,
            "p_unit": "bar",
            "fluid_choice": "",  # ""=first wired (default), or a fluid name
            "power": 0.0,
            "power_unit": pu,
            "eff": 0.0,
        }

    # -- payload -----------------------------------------------------------
    def _head_from_pressures(self, fluid_density):
        """Derive head (m) from suction/discharge pressures + fluid density."""
        if fluid_density is None:
            return None
        s = self.settings
        unit = s.get("p_unit") or "bar"
        dp_pa = pressure_to_pa(float(s.get("p_dis") or 0.0), unit) - pressure_to_pa(
            float(s.get("p_suc") or 0.0), unit
        )
        return dp_pa / (fluid_density * G)

    def to_signal(self, fluid_density=None) -> PointSample:
        s = self.settings
        if s.get("mode") == "pressures":
            head_m = self._head_from_pressures(fluid_density)
        else:
            head_m = _std_opt(s.get("head"), "head", s.get("head_unit") or "m")
        return PointSample(
            label=str(s.get("label", "Point")).strip() or "Point",
            q_m3h=units.to_standard(
                float(s.get("q") or 0.0), "capacity", s.get("q_unit") or "m³/h"
            ),
            head_m=head_m,
            power_kw=_std_opt(s.get("power"), "power", s.get("power_unit") or "kW"),
            efficiency_pct=_opt(s.get("eff")),
        )

    def compute(self, inputs) -> Dict[str, object]:
        self._fluids = self.all_of(inputs, "FluidSpec")
        chosen = resolve_fluid(self._fluids, self.settings.get("fluid_choice"))
        self._fluid_density = chosen.density_kgm3 if chosen is not None else None
        pt = self.to_signal(self._fluid_density)
        if pt.q_m3h < 0:
            return self.emit_nothing("Capacity Q must be ≥ 0 m³/h.", "invalid")
        if self.settings.get("mode") == "pressures" and chosen is None:
            return self.emit_nothing(
                "Connect/select a Fluid node to derive head from pressures.", "invalid"
            )
        bits = [f"Q={pt.q_m3h:g}"]
        if pt.head_m is not None:
            bits.append(f"H={pt.head_m:g}")
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
        eff = ui.spin(s.get("eff") or 0, 0, 100, 0.5, 1, None)

        # Head source: direct value, or derived from suction/discharge pressures
        # (the latter needs a connected Fluid node for the density).
        mode = ui.combo(
            [("Direct head", "direct"), ("From pressures + fluid", "pressures")],
            s.get("mode", "direct"),
            None,
        )
        p_suc = ui.spin(s.get("p_suc") or 0, 0, 1e5, 0.1, 3, None)
        p_dis = ui.spin(s.get("p_dis") or 0, 0, 1e5, 0.1, 3, None)
        p_unit = ui.combo(
            [("bar", "bar"), ("kgf/cm²", "kgf/cm**2")], s.get("p_unit", "bar"), None
        )

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
        pbl.addWidget(ui.row("Suction  P_suc", p_suc))
        pbl.addWidget(ui.row("Discharge  P_dis", p_dis))
        pbl.addWidget(ui.row("Pressure unit", p_unit))
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
            s["eff"] = eff.value()
            s["mode"] = mode.currentData()
            s["p_suc"], s["p_dis"] = p_suc.value(), p_dis.value()
            s["p_unit"] = p_unit.currentData()
            s["fluid_choice"] = fluid_pick.currentData() or ""
            refresh_mode()
            on_change()

        label = ui.line_edit(s.get("label", "Point"), None, "marker label")
        label.textChanged.connect(lambda v: (s.__setitem__("label", v), on_change()))
        eff.valueChanged.connect(lambda _=None: apply())
        mode.currentIndexChanged.connect(lambda _=None: apply())
        p_suc.valueChanged.connect(lambda _=None: apply())
        p_dis.valueChanged.connect(lambda _=None: apply())
        p_unit.currentIndexChanged.connect(lambda _=None: apply())
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
        dlg.add(ui.row("Efficiency  η", eff, "%"))
        apply()
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
