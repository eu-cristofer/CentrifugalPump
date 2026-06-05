"""
nodes.rated_point — Rated Point Input  (UI_SPEC §5.1)

Source node.  Captures the shared rated (design) point + rated fluid and emits a
``RatedPoint`` signal.  Density is entered as relative density **and** kg/m³ kept
in sync; pressure-unit selector drives the head-from-pressure conversion.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt

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
        return {
            "tag": "B-2351105",
            "standard": "API610 (12a ed.) / ISO 13709 + N-553",
            "q": 833.0, "head": 73.0, "n": 1750.0, "power": 252.0,
            "eff": 61.0, "head_shutoff": 117.0,
            "dens_rel": 0.736, "visc": 0.567,
            "unit": "bar", "parallel": False, "fluid_name": "Rated fluid",
        }

    # -- payload -----------------------------------------------------------
    def to_signal(self) -> RatedPoint:
        s = self.settings
        return RatedPoint(
            tag=str(s["tag"]).strip(),
            standard=str(s["standard"]),
            q_m3h=float(s["q"]), head_m=float(s["head"]),
            speed_rpm=float(s["n"]), power_kw=float(s["power"]),
            efficiency_pct=_opt(s.get("eff")),
            head_shutoff_m=_opt(s.get("head_shutoff")),
            density_rel=float(s["dens_rel"]), viscosity_cst=float(s["visc"]),
            pressure_unit=str(s["unit"]),
            parallel_operation=bool(s["parallel"]),
            fluid_name=str(s.get("fluid_name", "Rated fluid")),
        )

    def compute(self, inputs) -> Dict[str, object]:
        rated = self.to_signal()
        ok, msg = rated.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        par = " · ∥-op" if rated.parallel_operation else ""
        self.status = f"{rated.tag} · {rated.q_m3h:g} m³/h · {rated.head_m:g} m · {rated.speed_rpm:g} rpm{par}"
        self.state = "ok"
        return {"RatedPoint": rated}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "Rated Point Input",
            "Shared rated/design point and fluid — entered once, reused by every pump branch.",
            width=480,
        )
        banner = ui.Banner()

        def apply():
            ok, msg = self.to_signal().is_valid()
            banner.show_message("" if ok else msg, "error" if not ok else "info")
            on_change()

        tag = ui.line_edit(s["tag"], None, "service / datasheet TAG")
        tag.textChanged.connect(lambda v: (s.__setitem__("tag", v), apply()))
        std = ui.line_edit(s["standard"], None)
        std.textChanged.connect(lambda v: (s.__setitem__("standard", v), apply()))

        q = ui.spin(s["q"], 0, 1e6, 1, 2, None)
        q.valueChanged.connect(lambda v: (s.__setitem__("q", v), apply()))
        head = ui.spin(s["head"], 0, 1e5, 1, 2, None)
        head.valueChanged.connect(lambda v: (s.__setitem__("head", v), apply()))
        n = ui.spin(s["n"], 0, 1e5, 10, 0, None)
        n.valueChanged.connect(lambda v: (s.__setitem__("n", v), apply()))
        power = ui.spin(s["power"], 0, 1e5, 1, 2, None)
        power.valueChanged.connect(lambda v: (s.__setitem__("power", v), apply()))
        eff = ui.spin(s.get("eff") or 0, 0, 100, 0.5, 1, None)
        eff.valueChanged.connect(lambda v: (s.__setitem__("eff", v), apply()))
        hso = ui.spin(s.get("head_shutoff") or 0, 0, 1e5, 1, 2, None)
        hso.valueChanged.connect(lambda v: (s.__setitem__("head_shutoff", v), apply()))

        # density: relative <-> absolute kept in sync
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

        visc = ui.spin(s["visc"], 0.0, 1e5, 0.01, 3, None)
        visc.valueChanged.connect(lambda v: (s.__setitem__("visc", v), apply()))

        unit = ui.combo([("bar", "bar"), ("kgf/cm²", "kgf/cm**2")], s["unit"], None)
        unit.currentIndexChanged.connect(
            lambda _: (s.__setitem__("unit", unit.currentData()), apply())
        )
        parallel = ui.checkbox("Parallel-operation unit (A/B)", s["parallel"], None)
        parallel.toggled.connect(lambda v: (s.__setitem__("parallel", bool(v)), apply()))

        dlg.add(ui.section("Identification"))
        dlg.add(ui.row("Service TAG", tag))
        dlg.add(ui.row("Standard", std))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated duty"))
        dlg.add(ui.row("Capacity  Q", q, "m³/h"))
        dlg.add(ui.row("Diff. head  H", head, "m"))
        dlg.add(ui.row("Speed  N", n, "rpm"))
        dlg.add(ui.row("Power  P", power, "kW"))
        dlg.add(ui.row("Efficiency  η", eff, "%"))
        dlg.add(ui.row("Shut-off head", hso, "m"))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated fluid"))
        dlg.add(ui.row("Relative density", dens_rel, "—"))
        dlg.add(ui.row("Density", dens_abs, "kg/m³"))
        dlg.add(ui.row("Nominal viscosity", visc, "cSt"))
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
