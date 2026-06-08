"""
nodes.rated_point — Rated Point Input  (UI_SPEC §5.1)

Source node.  Captures the shared rated (design) point + rated fluid and emits a
``RatedPoint`` signal.  Density is entered as relative density **and** kg/m³ kept
in sync; pressure-unit selector drives the head-from-pressure conversion.

Unit selectors for Q, H, P, and viscosity let the user enter values in their
preferred units; ``quantity_factory`` normalises Q/H/P to m³/h/m/kW before
building the signal.  Viscosity (kinematic ↔ dynamic) is converted explicitly
because kinematic viscosity is not in STANDARD_UNITS.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt

from pump.utilities.unit_conversion import Q_, quantity_factory
from ..signals import RatedPoint
from .base import BaseNode, PortSpec
from . import ui

# ---------------------------------------------------------------------------
# Unit mapping: display label → Pint unit string
# ---------------------------------------------------------------------------

_Q_PINT = {
    "m³/h": "m**3/h",
    "l/s": "L/s",
    "l/min": "L/min",
    "US GPM": "gallon/min",
}
_H_PINT = {
    "m": "m",
    "ft": "ft",
}
_P_PINT = {
    "kW": "kW",
    "hp": "hp",
    "CV": "metric_horsepower",
}


def _to_m3h(value: float, unit: str) -> float:
    return quantity_factory(Q_(value, _Q_PINT[unit])).magnitude


def _to_m(value: float, unit: str) -> float:
    return quantity_factory(Q_(value, _H_PINT[unit])).magnitude


def _to_kw(value: float, unit: str) -> float:
    return quantity_factory(Q_(value, _P_PINT[unit])).magnitude


def _to_cst(value: float, unit: str, dens_rel: float) -> float:
    if unit == "cP":
        rho = Q_(dens_rel, "g/cm**3")
        return (Q_(value, "cP") / rho).to("cSt").magnitude
    return value


class RatedPointInputNode(BaseNode):
    kind = "rated_point"
    title = "Rated Point Input"
    glyph = "◆"
    is_source = True
    inputs = []
    outputs = [PortSpec("RatedPoint", "RatedPoint")]

    def default_settings(self) -> Dict:
        return {
            "tag": "B-2351105",
            "service": "",
            "standard": "API610 (12a ed.) / ISO 13709 + N-553",
            "q": 833.0,       "q_unit": "m³/h",
            "head": 73.0,     "head_unit": "m",
            "n": 1750.0,
            "power": 252.0,   "power_unit": "kW",
            "eff": 61.0, "head_shutoff": 117.0,
            "dens_rel": 0.736,
            "visc": 0.567,    "visc_unit": "cSt",
            "unit": "bar", "parallel": False, "fluid_name": "Rated fluid",
        }

    # -- payload -----------------------------------------------------------
    def to_signal(self) -> RatedPoint:
        s = self.settings
        q_unit    = s.get("q_unit",    "m³/h")
        head_unit = s.get("head_unit", "m")
        power_unit = s.get("power_unit", "kW")
        visc_unit  = s.get("visc_unit",  "cSt")
        dens_rel   = float(s["dens_rel"])
        return RatedPoint(
            tag=str(s["tag"]).strip(),
            service=str(s.get("service", "")),
            standard=str(s["standard"]),
            q_m3h=_to_m3h(float(s["q"]), q_unit),
            head_m=_to_m(float(s["head"]), head_unit),
            speed_rpm=float(s["n"]),
            power_kw=_to_kw(float(s["power"]), power_unit),
            efficiency_pct=_opt(s.get("eff")),
            head_shutoff_m=_opt(s.get("head_shutoff")),
            density_rel=dens_rel,
            viscosity_cst=_to_cst(float(s["visc"]), visc_unit, dens_rel),
            pressure_unit=str(s["unit"]),
            parallel_operation=bool(s["parallel"]),
            fluid_name=str(s.get("fluid_name", "Rated fluid")),
        )

    def compute(self, inputs) -> Dict[str, object]:
        rated = self.to_signal()
        ok, msg = rated.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        q_unit    = self.settings.get("q_unit",    "m³/h")
        head_unit = self.settings.get("head_unit", "m")
        par = " · ∥-op" if rated.parallel_operation else ""
        q_disp    = float(self.settings["q"])
        head_disp = float(self.settings["head"])
        self.status = (
            f"{rated.tag} · {q_disp:g} {q_unit} · {head_disp:g} {head_unit}"
            f" · {rated.speed_rpm:g} rpm{par}"
        )
        self.state = "ok"
        return {"RatedPoint": rated}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "Rated Point Input",
            "Shared rated/design point and fluid — entered once, reused by every pump branch.",
            width=500,
        )
        banner = ui.Banner()

        def apply():
            ok, msg = self.to_signal().is_valid()
            banner.show_message("" if ok else msg, "error" if not ok else "info")
            on_change()

        # ---- IDENTIFICATION ----
        service = ui.line_edit(s.get("service", ""), None, "e.g. Crude Oil Transfer")
        service.textChanged.connect(lambda v: (s.__setitem__("service", v), apply()))
        tag = ui.line_edit(s["tag"], None, "service / datasheet TAG")
        tag.textChanged.connect(lambda v: (s.__setitem__("tag", v), apply()))
        std = ui.line_edit(s["standard"], None)
        std.textChanged.connect(lambda v: (s.__setitem__("standard", v), apply()))

        # ---- RATED DUTY spinboxes ----
        q_spin = ui.spin(s["q"], 0, 1e6, 1, 3, None)
        head_spin = ui.spin(s["head"], 0, 1e5, 1, 3, None)
        n_spin = ui.spin(s["n"], 0, 1e5, 10, 0, None)
        power_spin = ui.spin(s["power"], 0, 1e5, 1, 3, None)
        eff_spin = ui.spin(s.get("eff") or 0, 0, 100, 0.5, 1, None)
        hso_spin = ui.spin(s.get("head_shutoff") or 0, 0, 1e5, 1, 2, None)

        # ---- Unit combos ----
        def _ucb(mapping, setting_key):
            """Build a unit QComboBox from a label→pint mapping dict."""
            return ui.combo([(k, k) for k in mapping], s.get(setting_key, next(iter(mapping))), None)

        q_ucb    = _ucb(_Q_PINT, "q_unit")
        head_ucb = _ucb(_H_PINT, "head_unit")
        power_ucb = _ucb(_P_PINT, "power_unit")

        # ---- Unit-change callbacks (Q, H, P) ----
        def on_q_unit(idx):
            new_unit = q_ucb.currentData()
            old_unit = s.get("q_unit", "m³/h")
            if new_unit != old_unit:
                std_val = quantity_factory(Q_(s["q"], _Q_PINT[old_unit]))
                new_disp = std_val.to(_Q_PINT[new_unit]).magnitude
                q_spin.blockSignals(True); q_spin.setValue(new_disp); q_spin.blockSignals(False)
                s["q"] = new_disp
                s["q_unit"] = new_unit
            apply()

        def on_head_unit(idx):
            new_unit = head_ucb.currentData()
            old_unit = s.get("head_unit", "m")
            if new_unit != old_unit:
                std_val = quantity_factory(Q_(s["head"], _H_PINT[old_unit]))
                new_disp = std_val.to(_H_PINT[new_unit]).magnitude
                head_spin.blockSignals(True); head_spin.setValue(new_disp); head_spin.blockSignals(False)
                s["head"] = new_disp
                s["head_unit"] = new_unit
            apply()

        def on_power_unit(idx):
            new_unit = power_ucb.currentData()
            old_unit = s.get("power_unit", "kW")
            if new_unit != old_unit:
                std_val = quantity_factory(Q_(s["power"], _P_PINT[old_unit]))
                new_disp = std_val.to(_P_PINT[new_unit]).magnitude
                power_spin.blockSignals(True); power_spin.setValue(new_disp); power_spin.blockSignals(False)
                s["power"] = new_disp
                s["power_unit"] = new_unit
            apply()

        q_spin.valueChanged.connect(lambda v: (s.__setitem__("q", v), apply()))
        head_spin.valueChanged.connect(lambda v: (s.__setitem__("head", v), apply()))
        n_spin.valueChanged.connect(lambda v: (s.__setitem__("n", v), apply()))
        power_spin.valueChanged.connect(lambda v: (s.__setitem__("power", v), apply()))
        eff_spin.valueChanged.connect(lambda v: (s.__setitem__("eff", v), apply()))
        hso_spin.valueChanged.connect(lambda v: (s.__setitem__("head_shutoff", v), apply()))
        q_ucb.currentIndexChanged.connect(on_q_unit)
        head_ucb.currentIndexChanged.connect(on_head_unit)
        power_ucb.currentIndexChanged.connect(on_power_unit)

        # ---- RATED FLUID ----
        dens_rel = ui.spin(s["dens_rel"], 0.0, 5.0, 0.001, 3, None)
        dens_abs = ui.spin(s["dens_rel"] * 1000.0, 0.0, 5000.0, 1, 1, None)

        def on_rel(v):
            s["dens_rel"] = float(v)
            dens_abs.blockSignals(True)
            dens_abs.setValue(float(v) * 1000.0)
            dens_abs.blockSignals(False)
            apply()

        def on_abs(v):
            s["dens_rel"] = float(v) / 1000.0
            dens_rel.blockSignals(True)
            dens_rel.setValue(float(v) / 1000.0)
            dens_rel.blockSignals(False)
            apply()

        dens_rel.valueChanged.connect(on_rel)
        dens_abs.valueChanged.connect(on_abs)

        visc_spin = ui.spin(s["visc"], 0.0, 1e5, 0.01, 3, None)
        visc_ucb  = ui.combo([("cSt", "cSt"), ("cP", "cP")], s.get("visc_unit", "cSt"), None)

        def on_visc_unit(idx):
            new_unit = visc_ucb.currentData()
            old_unit = s.get("visc_unit", "cSt")
            if new_unit != old_unit:
                rho = Q_(s["dens_rel"], "g/cm**3")
                if old_unit == "cSt":
                    new_disp = (Q_(s["visc"], "cSt") * rho).to("cP").magnitude
                else:
                    new_disp = (Q_(s["visc"], "cP") / rho).to("cSt").magnitude
                visc_spin.blockSignals(True); visc_spin.setValue(new_disp); visc_spin.blockSignals(False)
                s["visc"] = new_disp
                s["visc_unit"] = new_unit
            apply()

        visc_spin.valueChanged.connect(lambda v: (s.__setitem__("visc", v), apply()))
        visc_ucb.currentIndexChanged.connect(on_visc_unit)

        fluid_name = ui.line_edit(s.get("fluid_name", "Rated fluid"), None, "e.g. Light Hydrocarbon")
        fluid_name.textChanged.connect(lambda v: (s.__setitem__("fluid_name", v), apply()))

        unit = ui.combo([("bar", "bar"), ("kgf/cm²", "kgf/cm**2")], s["unit"], None)
        unit.currentIndexChanged.connect(
            lambda _: (s.__setitem__("unit", unit.currentData()), apply())
        )
        parallel = ui.checkbox("Parallel-operation unit (A/B)", s["parallel"], None)
        parallel.toggled.connect(lambda v: (s.__setitem__("parallel", bool(v)), apply()))

        # ---- Layout ----
        dlg.add(ui.section("Identification"))
        dlg.add(ui.row("Service", service))
        dlg.add(ui.row("Service TAG", tag))
        dlg.add(ui.row("Standard", std))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated duty"))
        dlg.add(ui.unit_row("Capacity  Q", q_spin, q_ucb))
        dlg.add(ui.unit_row("Diff. head  H", head_spin, head_ucb))
        dlg.add(ui.row("Speed  N", n_spin, "rpm"))
        dlg.add(ui.unit_row("Power  P", power_spin, power_ucb))
        dlg.add(ui.row("Efficiency  η", eff_spin, "%"))
        dlg.add(ui.row("Shut-off head", hso_spin, "m"))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated fluid"))
        dlg.add(ui.row("Fluid name", fluid_name))
        dlg.add(ui.row("Relative density", dens_rel, "—"))
        dlg.add(ui.row("Density", dens_abs, "kg/m³"))
        dlg.add(ui.unit_row("Nominal viscosity", visc_spin, visc_ucb))
        dlg.add(ui.row("Pressure unit", unit))
        dlg.add(ui.row("", parallel))
        dlg.add(banner)
        apply()
        return dlg


def _opt(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None
