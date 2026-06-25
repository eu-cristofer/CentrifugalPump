"""
nodes.rated_point — Rated Point Input  (UI_SPEC §5.1)

Source node.  Captures the shared rated (design) point + rated fluid and emits a
``RatedPoint`` signal.  Density is entered as relative density **and** kg/m³ kept
in sync; pressure-unit selector drives the head-from-pressure conversion.

Unit selection for Q, H, P, and viscosity is handled by the reusable
``ui.UnitField`` widget, backed by the central :mod:`pumpflow.units` registry —
the single place that knows which display units are offered and how they map to
the library's canonical units.  ``to_signal`` always normalises Q/H/P to
m³/h/m/kW (and viscosity to cSt) so every downstream node sees standard units.
A fresh node opens in whatever display units the active project preset selects.
"""

from __future__ import annotations

from typing import Dict

from .. import units
from ..signals import RatedPoint
from .base import BaseNode, PortSpec
from . import ui


class RatedPointInputNode(BaseNode):
    kind = "rated_point"
    title = "Rated Point Input"
    glyph = "◆"
    is_source = True
    inputs = []
    outputs = [PortSpec("RatedPoint", "RatedPoint")]

    def default_settings(self) -> Dict:
        p = units.PREFS
        qu = p.default_unit("capacity")
        hu = p.default_unit("head")
        pu = p.default_unit("power")
        vu = p.default_unit("viscosity")
        return {
            "tag": "B-2351105",
            "service": "",
            "standard": "API610 (12a ed.) / ISO 13709 + N-553",
            "q": units.convert_display(833.0, "capacity", "m³/h", qu),
            "q_unit": qu,
            "head": units.convert_display(73.0, "head", "m", hu),
            "head_unit": hu,
            "n": 1750.0,
            "power": units.convert_display(252.0, "power", "kW", pu),
            "power_unit": pu,
            "eff": 61.0,
            "head_shutoff": 117.0,
            "dens_rel": 0.736,
            "visc": 0.567,
            "visc_unit": vu,
            "unit": "bar",
            "parallel": False,
            "fluid_name": "Rated fluid",
        }

    # -- payload -----------------------------------------------------------
    def to_signal(self) -> RatedPoint:
        s = self.settings
        dens_rel = float(s["dens_rel"])
        return RatedPoint(
            tag=str(s["tag"]).strip(),
            service=str(s.get("service", "")),
            standard=str(s["standard"]),
            q_m3h=units.to_standard(
                float(s["q"]), "capacity", s.get("q_unit") or "m³/h"
            ),
            head_m=units.to_standard(
                float(s["head"]), "head", s.get("head_unit") or "m"
            ),
            speed_rpm=float(s["n"]),
            power_kw=units.to_standard(
                float(s["power"]), "power", s.get("power_unit") or "kW"
            ),
            efficiency_pct=_opt(s.get("eff")),
            head_shutoff_m=_opt(s.get("head_shutoff")),
            density_rel=dens_rel,
            viscosity_cst=units.to_standard(
                float(s["visc"]), "viscosity", s.get("visc_unit") or "cSt", dens_rel
            ),
            pressure_unit=str(s["unit"]),
            parallel_operation=bool(s["parallel"]),
            fluid_name=str(s.get("fluid_name", "Rated fluid")),
        )

    def compute(self, inputs) -> Dict[str, object]:
        rated = self.to_signal()
        ok, msg = rated.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        s = self.settings
        par = " · ∥-op" if rated.parallel_operation else ""
        self.status = (
            f"{rated.tag} · {float(s['q']):g} {s.get('q_unit', 'm³/h')}"
            f" · {float(s['head']):g} {s.get('head_unit', 'm')}"
            f" · {rated.speed_rpm:g} rpm{par}"
        )
        self.state = "ok"
        return {"RatedPoint": rated}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Rated Point Input",
            "Shared rated/design point and fluid — entered once, reused by every pump branch.",
            width=500,
        )
        banner = ui.Banner()

        # Unit-aware fields (Q, H, P, viscosity).  Viscosity reads the live
        # relative density for its kinematic↔dynamic conversion.
        q_field = ui.UnitField(
            "capacity",
            s["q"],
            s.get("q_unit"),
            on_change=lambda: apply(),
            hi=1e6,
            step=1,
            decimals=3,
        )
        head_field = ui.UnitField(
            "head",
            s["head"],
            s.get("head_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=1,
            decimals=3,
        )
        power_field = ui.UnitField(
            "power",
            s["power"],
            s.get("power_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=1,
            decimals=3,
        )
        visc_field = ui.UnitField(
            "viscosity",
            s["visc"],
            s.get("visc_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=0.01,
            decimals=3,
            dens_rel_getter=lambda: float(s["dens_rel"]),
        )

        def sync_fields():
            s["q"], s["q_unit"] = q_field.magnitude(), q_field.unit_label()
            s["head"], s["head_unit"] = head_field.magnitude(), head_field.unit_label()
            s["power"], s["power_unit"] = (
                power_field.magnitude(),
                power_field.unit_label(),
            )
            s["visc"], s["visc_unit"] = visc_field.magnitude(), visc_field.unit_label()

        def apply():
            sync_fields()
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

        # ---- plain spinboxes (no alternate units) ----
        n_spin = ui.spin(s["n"], 0, 1e5, 10, 0, None)
        eff_spin = ui.spin(s.get("eff") or 0, 0, 100, 0.5, 1, None)
        hso_spin = ui.spin(s.get("head_shutoff") or 0, 0, 1e5, 1, 2, None)
        n_spin.valueChanged.connect(lambda v: (s.__setitem__("n", v), apply()))
        eff_spin.valueChanged.connect(lambda v: (s.__setitem__("eff", v), apply()))
        hso_spin.valueChanged.connect(
            lambda v: (s.__setitem__("head_shutoff", v), apply())
        )

        # ---- RATED FLUID — relative ↔ absolute density kept in sync ----
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

        fluid_name = ui.line_edit(
            s.get("fluid_name", "Rated fluid"), None, "e.g. Light Hydrocarbon"
        )
        fluid_name.textChanged.connect(
            lambda v: (s.__setitem__("fluid_name", v), apply())
        )

        unit = ui.combo([("bar", "bar"), ("kgf/cm²", "kgf/cm**2")], s["unit"], None)
        unit.currentIndexChanged.connect(
            lambda _: (s.__setitem__("unit", unit.currentData()), apply())
        )
        parallel = ui.checkbox("Parallel-operation unit (A/B)", s["parallel"], None)
        parallel.toggled.connect(
            lambda v: (s.__setitem__("parallel", bool(v)), apply())
        )

        # ---- Layout ----
        dlg.add(ui.section("Identification"))
        dlg.add(ui.row("Service", service))
        dlg.add(ui.row("Service TAG", tag))
        dlg.add(ui.row("Standard", std))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated duty"))
        dlg.add(q_field.row("Capacity  Q"))
        dlg.add(head_field.row("Diff. head  H"))
        dlg.add(ui.row("Speed  N", n_spin, "rpm"))
        dlg.add(power_field.row("Power  P"))
        dlg.add(ui.row("Efficiency  η", eff_spin, "%"))
        dlg.add(ui.row("Shut-off head", hso_spin, "m"))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated fluid"))
        dlg.add(ui.row("Fluid name", fluid_name))
        dlg.add(ui.row("Relative density", dens_rel, "—"))
        dlg.add(ui.row("Density", dens_abs, "kg/m³"))
        dlg.add(visc_field.row("Nominal viscosity"))
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
