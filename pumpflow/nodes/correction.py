"""
nodes.correction — Speed / Affinity Correction  (UI_SPEC §5.3)

Inputs ``RatedPoint`` + ``TestPointSet`` → outputs ``CorrectedCurve``.
Builds ``TestPoint``s from the raw rows, wraps them in a ``PerformanceCurve``,
then ``.to_speed(rated N)`` (affinity laws) and ``.to_fluid(rated fluid)``.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem

from ..binding import BindingError, correct_curve
from ..numfmt import fmt
from ..signals import RatedPoint, TestPointSet
from .base import BaseNode, PortSpec
from . import ui


class SpeedCorrectionNode(BaseNode):
    kind = "correction"
    title = "Speed / Affinity Correction"
    glyph = "↻"
    inputs = [PortSpec("RatedPoint", "RatedPoint"), PortSpec("TestPointSet", "TestPointSet")]
    outputs = [PortSpec("CorrectedCurve", "CorrectedCurve")]

    def default_settings(self) -> Dict:
        return {
            "lock_to_rated": True,
            "target_speed": 1750.0,
            "apply_speed": True,
            "apply_density": True,
            "apply_viscosity": False,
            "degree": 3,
        }

    def _resolve(self, inputs):
        rated = self.first(inputs, "RatedPoint")
        tps = self.first(inputs, "TestPointSet")
        return rated, tps

    def compute(self, inputs) -> Dict[str, object]:
        rated, tps = self._resolve(inputs)
        if rated is None or tps is None:
            return self.emit_nothing("Waiting for rated point + test points", "idle")

        s = self.settings
        target = rated.speed_rpm if s["lock_to_rated"] else float(s["target_speed"])
        try:
            corrected = correct_curve(
                rated, tps,
                target_speed_rpm=target,
                apply_speed=s["apply_speed"],
                apply_density=s["apply_density"],
                degree=int(s["degree"]),
            )
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")

        self._last = corrected
        self.status = f"{corrected.pump_tag} · {len(tps.rows)} pts · → {target:g} rpm"
        self.state = "ok"
        return {"CorrectedCurve": corrected}

    def port_label(self, name: str) -> str:
        return {"RatedPoint": "Rated", "TestPointSet": "Tests",
                "CorrectedCurve": "Corrected"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "Speed / Affinity Correction",
            "Correct measured points to the rated speed and fluid. "
            "Affinity laws:  Q ∝ N · H ∝ N² · P ∝ N³.",
            width=620,
        )
        banner = ui.Banner()

        target = ui.spin(s["target_speed"], 0, 1e5, 10, 0, None)
        target.setEnabled(not s["lock_to_rated"])
        lock = ui.checkbox("Lock target speed to rated N", s["lock_to_rated"], None)
        sp = ui.checkbox("Speed (affinity) correction", s["apply_speed"], None)
        de = ui.checkbox("Density (ρ_rated / ρ_test) correction", s["apply_density"], None)
        vi = ui.checkbox("Viscosity correction (nominal factors)", s["apply_viscosity"], None)
        vi.setEnabled(False)
        vi.setToolTip("Viscosity correction is a library TODO — disabled until available.")
        degree = ui.int_spin(int(s["degree"]), 2, 5, None)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Q [m³/h]", "Head [m]", "Power [kW]", "η [%]", "stage"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setObjectName("ReadGrid")

        def refresh():
            on_change()
            corrected = getattr(self, "_last", None) if self.state == "ok" else None
            banner.show_message(
                "" if self.state == "ok" else self.status,
                "info" if self.state in ("ok", "idle") else "error",
            )
            table.setRowCount(0)
            if not corrected:
                return
            for pair in corrected.before_after:
                m, c = pair["measured"], pair["corrected"]
                _append(table, [fmt(m["q"]), fmt(m["head"]), fmt(m["power"]),
                                fmt(m["eff"], 1) if m["eff"] is not None else "—", "measured"], muted=True)
                _append(table, [fmt(c["q"]), fmt(c["head"]), fmt(c["power"]),
                                fmt(c["eff"], 1) if c["eff"] is not None else "—", "corrected"])

        def set_lock(v):
            s["lock_to_rated"] = bool(v)
            target.setEnabled(not bool(v))
            refresh()

        lock.toggled.connect(set_lock)
        target.valueChanged.connect(lambda v: (s.__setitem__("target_speed", v), refresh()))
        sp.toggled.connect(lambda v: (s.__setitem__("apply_speed", bool(v)), refresh()))
        de.toggled.connect(lambda v: (s.__setitem__("apply_density", bool(v)), refresh()))
        degree.valueChanged.connect(lambda v: (s.__setitem__("degree", int(v)), refresh()))

        dlg.add(ui.section("Target & corrections"))
        dlg.add(ui.row("Target speed", target, "rpm"))
        dlg.add(ui.row("", lock))
        dlg.add(ui.row("", sp))
        dlg.add(ui.row("", de))
        dlg.add(ui.row("", vi))
        dlg.add(ui.row("Fit degree", degree))
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
