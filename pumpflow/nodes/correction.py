"""
nodes.correction — Speed / Affinity Correction  (UI_SPEC §5.3)

Inputs ``RatedPoint`` + ``TestPointSet`` → outputs ``CorrectedCurve``.
Builds ``TestPoint``s from the raw rows, wraps them in a ``PerformanceCurve``,
then ``.to_speed(rated N)`` (affinity laws) and ``.to_fluid(rated fluid)``.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem

from ..binding import BindingError, correct_curve, make_fluid
from ..numfmt import fmt
from ..signals import RatedPoint, TestPointSet
from .base import BaseNode, PortSpec
from .fluidpick import choice_options, current_choice, resolve_fluid
from . import ui

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
        return {
            "lock_to_rated": True,
            "target_speed": 1750.0,
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
            target = float(s["target_speed"])
            apply_density = s["apply_density"] and override_fluid is not None
        else:
            target = rated.speed_rpm if s["lock_to_rated"] else float(s["target_speed"])
            apply_density = s["apply_density"]
        try:
            corrected = correct_curve(
                rated,
                tps,
                target_speed_rpm=target,
                apply_speed=s["apply_speed"],
                apply_density=apply_density,
                degree=int(s["degree"]),
                target_fluid=override_fluid,
            )
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")

        self._last = corrected
        mode = "" if rated is not None else " · forced"
        fl = " · fluid✓" if override_fluid is not None else ""
        self.status = (
            f"{corrected.pump_tag} · {len(tps.rows)} pts · → {target:g} rpm{mode}{fl}"
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
        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Speed / Affinity Correction",
            "Correct measured points to the rated speed and fluid. "
            "Affinity laws:  Q ∝ N · H ∝ N² · P ∝ N³.",
            width=620,
        )
        banner = ui.Banner()

        target = ui.spin(s["target_speed"], 0, 1e5, 10, 0, None)
        target.setEnabled(not s["lock_to_rated"])
        lock = ui.checkbox("Lock target speed to rated N", s["lock_to_rated"], None)
        sp = ui.checkbox("Speed (affinity) correction", s["apply_speed"], None)
        de = ui.checkbox(
            "Density (ρ_rated / ρ_test) correction", s["apply_density"], None
        )
        vi = ui.checkbox(
            "Viscosity correction (nominal factors)", s["apply_viscosity"], None
        )
        vi.setEnabled(False)
        vi.setToolTip(
            "Viscosity correction is a library TODO — disabled until available."
        )
        degree = ui.int_spin(int(s["degree"]), 2, 5, None)

        fluids = getattr(self, "_fluids", [])
        fluid_pick = ui.combo(
            choice_options(fluids, _DEFAULT_LABEL),
            current_choice(fluids, s.get("fluid_choice")),
            None,
        )

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            ["Q [m³/h]", "Head [m]", "Power [kW]", "η [%]", "stage"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setObjectName("ReadGrid")

        def refresh():
            on_change()
            has_rated = getattr(self, "_has_rated", True)
            has_fluid = getattr(self, "_has_fluid", False)
            # Forced mode (no rated point): manual target is always live; the
            # lock control is disabled.  Density correction needs a target fluid,
            # so it stays available whenever a rated point *or* a Fluid node is
            # connected.
            target.setEnabled(not s["lock_to_rated"] or not has_rated)
            lock.setEnabled(has_rated)
            de.setEnabled(has_rated or has_fluid)
            corrected = getattr(self, "_last", None) if self.state == "ok" else None
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
            banner.show_message(msg, level)
            table.setRowCount(0)
            if not corrected:
                return
            for pair in corrected.before_after:
                m, c = pair["measured"], pair["corrected"]
                _append(
                    table,
                    [
                        fmt(m["q"]),
                        fmt(m["head"]),
                        fmt(m["power"]),
                        fmt(m["eff"], 1) if m["eff"] is not None else "—",
                        "measured",
                    ],
                    muted=True,
                )
                _append(
                    table,
                    [
                        fmt(c["q"]),
                        fmt(c["head"]),
                        fmt(c["power"]),
                        fmt(c["eff"], 1) if c["eff"] is not None else "—",
                        "corrected",
                    ],
                )

        def set_lock(v):
            s["lock_to_rated"] = bool(v)
            refresh()  # refresh() owns the manual-target enabled state

        lock.toggled.connect(set_lock)
        target.valueChanged.connect(
            lambda v: (s.__setitem__("target_speed", v), refresh())
        )
        sp.toggled.connect(lambda v: (s.__setitem__("apply_speed", bool(v)), refresh()))
        de.toggled.connect(
            lambda v: (s.__setitem__("apply_density", bool(v)), refresh())
        )
        degree.valueChanged.connect(
            lambda v: (s.__setitem__("degree", int(v)), refresh())
        )
        fluid_pick.currentIndexChanged.connect(
            lambda _: (s.__setitem__("fluid_choice", fluid_pick.currentData()), refresh())
        )

        dlg.add(ui.section("Target & corrections"))
        dlg.add(ui.row("Target speed", target, "rpm"))
        dlg.add(ui.row("", lock))
        dlg.add(ui.row("", sp))
        dlg.add(ui.row("", de))
        dlg.add(ui.row("", vi))
        dlg.add(ui.row("Fit degree", degree))
        if fluids:
            dlg.add(ui.row("Correct to fluid", fluid_pick))
        dlg.add(ui.hline())
        dlg.add(ui.section("Before / after correction"))
        dlg.add(table)
        dlg.add(banner)
        refresh()
        dlg.resize(660, 560)
        return dlg


def _append(table: QTableWidget, values, muted: bool = False):
    from PySide6.QtGui import QColor

    r = table.rowCount()
    table.insertRow(r)
    for c, v in enumerate(values):
        item = QTableWidgetItem(str(v))
        if muted:
            item.setForeground(QColor("#8a96a3"))
        table.setItem(r, c, item)
