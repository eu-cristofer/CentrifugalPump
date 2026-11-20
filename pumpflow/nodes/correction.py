"""
nodes.correction — Speed / Affinity Correction  (UI_SPEC §5.3)

Inputs ``RatedPoint`` + ``TestPointSet`` → outputs ``CorrectedCurve``.
Builds ``TestPoint``s from the raw rows, wraps them in a ``PerformanceCurve``,
then ``.to_speed(rated N)`` (affinity laws) and ``.to_fluid(rated fluid)``
(or ``.to_viscous(rated fluid)``, HI 9.6.7, when the viscosity correction is on).
"""

from __future__ import annotations

from typing import Dict

from pump import Q_

from .. import explain, units
from ..binding import BindingError, correct_curve, make_fluid
from ..signals import RatedPoint, TestPointSet
from .base import BaseNode, PortSpec
from .fluidpick import choice_options, current_choice, resolve_fluid

_DEFAULT_LABEL = "Rated fluid"


class SpeedCorrectionNode(BaseNode):
    kind = "correction"
    title = "Speed / Affinity Correction"
    glyph = "↻"
    # RatedPoint is optional: with no rated point the node runs a *forced* speed
    # correction — manual target speed, density correction skipped (there is no
    # rated fluid to correct to).
    # An optional FluidSpec (from a Fluid node) overrides the fluid the curve is
    # corrected *to*; with it connected, density correction can run even with no
    # rated point.
    inputs = [
        PortSpec("RatedPoint", "RatedPoint"),
        PortSpec("TestPointSet", "TestPointSet"),
        PortSpec("FluidSpec", "FluidSpec", multi=True),
    ]
    outputs = [PortSpec("CorrectedCurve", "CorrectedCurve")]

    def default_settings(self) -> Dict:
        su = units.PREFS.default_unit("speed")
        return {
            "lock_to_rated": True,
            "target_speed": units.convert_display(1750.0, "speed", "rpm", su),
            "target_speed_unit": su,
            "apply_speed": True,
            "apply_density": True,
            "apply_viscosity": False,
            "degree": 3,
            "fluid_choice": "",  # ""=first wired (default), "__default__"=rated, or a name
        }

    def _resolve(self, inputs):
        rated = self.first(inputs, "RatedPoint")
        tps = self.first(inputs, "TestPointSet")
        return rated, tps

    def _manual_target(self):
        """The manual target speed as a Quantity in rpm."""
        s = self.settings
        unit = s.get("target_speed_unit") or "rpm"
        return Q_(float(s["target_speed"]), units.pint_str("speed", unit)).to("rpm")

    def compute(self, inputs) -> Dict[str, object]:
        rated, tps = self._resolve(inputs)
        if tps is None:
            return self.emit_nothing("Waiting for test points", "idle")

        self._fluids = self.all_of(inputs, "FluidSpec")
        chosen = resolve_fluid(self._fluids, self.settings.get("fluid_choice"))
        override_fluid = make_fluid(chosen) if chosen is not None else None

        s = self.settings
        self._has_rated = rated is not None
        self._has_fluid = chosen is not None
        if rated is None:
            # Forced speed correction: no rated point → manual target speed.
            # Density correction needs a target fluid, so it runs only when a
            # Fluid node is connected.
            target = self._manual_target()
            apply_density = s["apply_density"] and override_fluid is not None
        else:
            target = rated.speed if s["lock_to_rated"] else self._manual_target()
            apply_density = s["apply_density"]
        try:
            corrected = correct_curve(
                rated,
                tps,
                target_speed=target,
                apply_speed=s["apply_speed"],
                apply_density=apply_density,
                degree=int(s["degree"]),
                target_fluid=override_fluid,
                # Viscosity is folded into the fluid step, so it needs density on.
                apply_viscosity=bool(s.get("apply_viscosity")) and bool(apply_density),
            )
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")

        self._last = corrected
        mode = "" if rated is not None else " · forced"
        fl = " · fluid✓" if override_fluid is not None else ""
        visc = ""
        if corrected.viscous and corrected.viscous["B"] > 1.0:
            visc = f" · visc B={corrected.viscous['B']:.1f}"
        self.status = (
            f"{corrected.pump_tag} · {len(tps.rows)} pts · "
            f"→ {target.to('rpm').magnitude:g} rpm{mode}{fl}{visc}"
        )
        self.state = "ok"
        return {"CorrectedCurve": corrected}

    def port_label(self, name: str) -> str:
        return {
            "RatedPoint": "Rated",
            "TestPointSet": "Tests",
            "FluidSpec": "Fluid",
            "CorrectedCurve": "Corrected",
        }.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        from PySide6.QtWidgets import QLabel

        from . import ui

        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Speed / Affinity Correction",
            "Correct measured points to the rated speed and fluid. "
            "Affinity laws:  Q ∝ N · H ∝ N² · P ∝ N³.",
            width=620,
        )
        banner = ui.Banner()

        target = ui.UnitField(
            "speed",
            s["target_speed"],
            s.get("target_speed_unit"),
            on_change=lambda: on_target(),
            hi=1e5,
            step=10,
            decimals=3,
        )

        def set_target_enabled(flag: bool) -> None:
            target.spin.setEnabled(flag)
            target.combo.setEnabled(flag)

        set_target_enabled(not s["lock_to_rated"])
        lock = ui.checkbox("Lock target speed to rated N", s["lock_to_rated"], None)
        sp = ui.checkbox("Speed (affinity) correction", s["apply_speed"], None)
        de = ui.checkbox(
            "Density (ρ_rated / ρ_test) correction", s["apply_density"], None
        )
        vi = ui.checkbox(
            "Viscosity correction (HI 9.6.7)", s["apply_viscosity"], None
        )
        vi.setToolTip(
            "HI 9.6.7 / ISO TR 17766, applied with the density step. "
            "Factors apply only for 1 < B < 40; B <= 1 leaves the curve unchanged."
        )
        visc_info = QLabel("—")
        visc_info.setToolTip(explain.tooltip("viscosity_b"))  # UC-10
        visc_info.setWordWrap(True)
        degree = ui.int_spin(int(s["degree"]), 2, 5, None)

        fluids = getattr(self, "_fluids", [])
        fluid_pick = ui.combo(
            choice_options(fluids, _DEFAULT_LABEL),
            current_choice(fluids, s.get("fluid_choice")),
            None,
        )

        grid = ui.BeforeAfterTable(s)
        table = grid.table

        def refresh():
            on_change()
            has_rated = getattr(self, "_has_rated", True)
            has_fluid = getattr(self, "_has_fluid", False)
            # Forced mode (no rated point): manual target is always live; the
            # lock control is disabled.  Density correction needs a target fluid,
            # so it stays available whenever a rated point *or* a Fluid node is
            # connected.
            set_target_enabled(not s["lock_to_rated"] or not has_rated)
            lock.setEnabled(has_rated)
            de.setEnabled(has_rated or has_fluid)
            vi.setEnabled(bool(s["apply_density"]) and (has_rated or has_fluid))
            corrected = getattr(self, "_last", None) if self.state == "ok" else None
            visc = getattr(corrected, "viscous", None) if corrected else None
            if self.state == "ok" and not has_rated and has_fluid:
                msg, level = (
                    "No rated point — forced speed correction, density corrected "
                    "to the connected Fluid node.",
                    "info",
                )
            elif self.state == "ok" and not has_rated:
                msg, level = (
                    "No rated point connected — forced speed correction "
                    "(manual target speed, density correction skipped).",
                    "info",
                )
            elif self.state == "ok" and has_fluid:
                msg, level = (
                    "Correcting to the fluid from the connected Fluid node "
                    "(overrides the rated fluid).",
                    "info",
                )
            else:
                msg, level = (
                    "" if self.state == "ok" else self.status,
                    "info" if self.state in ("ok", "idle") else "error",
                )
            if visc and visc["B"] >= 40.0:
                msg, level = (
                    f"Viscosity parameter B = {visc['B']:.1f} is outside the "
                    "HI 9.6.7 method validity (B < 40); factors are extrapolated.",
                    "warn",
                )
            banner.show_message(msg, level)
            if visc:
                note = "" if visc["B"] > 1.0 else "  (B ≤ 1: no correction)"
                visc_info.setText(
                    f"B = {visc['B']:.2f} · C_Q = {visc['C_Q']:.3f} · "
                    f"C_H = {visc['C_H']:.3f} · C_η = {visc['C_eta']:.3f}{note}"
                )
            else:
                visc_info.setText("—")
            grid.fill(corrected.before_after if corrected else (), ("measured", "corrected"))

        def set_lock(v):
            s["lock_to_rated"] = bool(v)
            refresh()  # refresh() owns the manual-target enabled state

        def on_target():
            s["target_speed"] = target.magnitude()
            s["target_speed_unit"] = target.unit_label()
            refresh()

        lock.toggled.connect(set_lock)
        sp.toggled.connect(lambda v: (s.__setitem__("apply_speed", bool(v)), refresh()))
        de.toggled.connect(
            lambda v: (s.__setitem__("apply_density", bool(v)), refresh())
        )
        vi.toggled.connect(
            lambda v: (s.__setitem__("apply_viscosity", bool(v)), refresh())
        )
        degree.valueChanged.connect(
            lambda v: (s.__setitem__("degree", int(v)), refresh())
        )
        fluid_pick.currentIndexChanged.connect(
            lambda _: (s.__setitem__("fluid_choice", fluid_pick.currentData()), refresh())
        )

        dlg.add(ui.section("Target & corrections"))
        dlg.add(target.row("Target speed"))
        dlg.add(ui.row("", lock))
        dlg.add(ui.row("", sp))
        dlg.add(ui.row("", de))
        dlg.add(ui.row("", vi))
        dlg.add(ui.row("HI 9.6.7 factors", visc_info))
        dlg.add(ui.row("Fit degree", degree))
        if fluids:
            dlg.add(ui.row("Correct to fluid", fluid_pick))
        dlg.add(ui.hline())
        dlg.add(ui.section("Before / after correction"))
        dlg.add(grid.strip)
        dlg.add(table)
        dlg.add(banner)
        refresh()
        dlg.resize(660, 560)
        return dlg
