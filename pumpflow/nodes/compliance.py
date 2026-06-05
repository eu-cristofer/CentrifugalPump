"""
nodes.compliance — API 610 Compliance Check  (UI_SPEC §5.6)

Inputs ``FittedModel`` + ``RatedPoint`` → output ``ComplianceResult``.
Per-parameter Actual / Predicted / Min / Max / Deviation / Tolerance / Verdict,
plus a bold overall APPROVED / REJECTED banner.  Numbers come from
``PerformanceChecker`` so they match the library's report tables.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
)

from ..binding import check_compliance, default_tolerances
from ..numfmt import fmt
from .base import BaseNode, PortSpec
from . import ui

_HEADERS = ["Parameter", "Actual", "Predicted", "Min", "Max", "Deviation", "Tol.", "Verdict"]


class ComplianceCheckNode(BaseNode):
    kind = "compliance"
    title = "API 610 Compliance Check"
    glyph = "✓"
    inputs = [PortSpec("FittedModel", "FittedModel"), PortSpec("RatedPoint", "RatedPoint")]
    outputs = [PortSpec("ComplianceResult", "ComplianceResult")]

    def default_settings(self) -> Dict:
        return {"tolerances": {}}   # empty → use library defaults

    def compute(self, inputs) -> Dict[str, object]:
        fitted = self.first(inputs, "FittedModel")
        rated = self.first(inputs, "RatedPoint")
        if fitted is None or rated is None:
            return self.emit_nothing("Waiting for model + rated point", "idle")
        result = check_compliance(fitted, rated, self.settings.get("tolerances") or None)
        self._last = result
        self._rated = rated
        n_fail = sum(1 for p in result.parameters if not p.passed)
        if result.overall_pass:
            self.status = f"{result.pump_tag} · ✅ APPROVED"
            self.state = "ok"
        else:
            self.status = f"{result.pump_tag} · ❌ {n_fail} out of tolerance"
            self.state = "reject"
        return {"ComplianceResult": result}

    def port_label(self, name: str) -> str:
        return {"FittedModel": "Model", "RatedPoint": "Rated",
                "ComplianceResult": "Verdict"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "API 610 Compliance Check",
            "Deviation δ = 1 − nominal/predicted.  Head |δ|≤tol · Power δ≤tol · "
            "Efficiency δ≥−tol · Shut-off |δ|≤tol.",
            width=680,
        )
        verdict = QLabel(objectName="VerdictBanner")
        verdict.setFont(QFont("Segoe UI", 15, QFont.Bold))
        override_chip = ui.Banner()

        table = QTableWidget(0, len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setObjectName("ResultGrid")

        # tolerance editors (defaults depend on the rated head band)
        base = default_tolerances(getattr(self, "_rated", None) or _Fallback())
        cur = {**base, **(s.get("tolerances") or {})}
        tol_head = ui.spin(cur["head"] * 100, 0, 50, 0.5, 1, None)
        tol_shut = ui.spin(cur["shutoff"] * 100, 0, 50, 0.5, 1, None)
        tol_pow = ui.spin(cur["power"] * 100, 0, 50, 0.5, 1, None)
        tol_eff = ui.spin(cur["efficiency"] * 100, 0, 50, 0.5, 1, None)

        def refresh():
            on_change()
            result = getattr(self, "_last", None) if self.outputs_cache else None
            table.setRowCount(0)
            if not result:
                verdict.setText("—  awaiting inputs")
                verdict.setProperty("verdict", "idle")
                _repolish(verdict)
                return
            for p in result.parameters:
                _append_param(table, p)
            ok = result.overall_pass
            verdict.setText(f"{'APPROVED ✓' if ok else 'REJECTED ✗'}   ·   {result.pump_tag}")
            verdict.setProperty("verdict", "pass" if ok else "fail")
            _repolish(verdict)
            if result.overridden:
                override_chip.show_message(
                    "⚠ Tolerances overridden — differ from PerformanceChecker defaults.", "warn"
                )
            else:
                override_chip.setVisible(False)

        def write_tol():
            s["tolerances"] = {
                "head": tol_head.value() / 100.0,
                "shutoff": tol_shut.value() / 100.0,
                "power": tol_pow.value() / 100.0,
                "efficiency": tol_eff.value() / 100.0,
            }
            refresh()

        for sb in (tol_head, tol_shut, tol_pow, tol_eff):
            sb.valueChanged.connect(lambda _=None: write_tol())

        reset = QPushButton("Reset to API 610 standard")
        reset.setObjectName("ToolButton")

        def do_reset():
            s["tolerances"] = {}
            b = default_tolerances(getattr(self, "_rated", None) or _Fallback())
            for sb, key in ((tol_head, "head"), (tol_shut, "shutoff"),
                            (tol_pow, "power"), (tol_eff, "efficiency")):
                sb.blockSignals(True)
                sb.setValue(b[key] * 100)
                sb.blockSignals(False)
            refresh()

        reset.clicked.connect(do_reset)

        dlg.add(verdict)
        dlg.add(override_chip)
        dlg.add(table)
        dlg.add(ui.hline())
        dlg.add(ui.section("Tolerances (editable)"))
        dlg.add(ui.row("Head", tol_head, "%"))
        dlg.add(ui.row("Shut-off head", tol_shut, "%"))
        dlg.add(ui.row("Power", tol_pow, "%"))
        dlg.add(ui.row("Efficiency", tol_eff, "%"))
        dlg.add(ui.row("", reset))
        refresh()
        dlg.resize(700, 640)
        return dlg


class _Fallback:
    head_m = 73.0
    head_shutoff_m = 117.0


def _append_param(table: QTableWidget, p) -> None:
    r = table.rowCount()
    table.insertRow(r)
    cells = [
        p.name, fmt(p.actual), fmt(p.predicted),
        fmt(p.minimum) if p.minimum is not None else "—",
        fmt(p.maximum) if p.maximum is not None else "—",
        f"{p.deviation * 100:+.2f} %", f"{p.tolerance * 100:.1f} %",
        "✅" if p.passed else "❌",
    ]
    for c, text in enumerate(cells):
        item = QTableWidgetItem(str(text))
        if c == 0:
            item.setForeground(QColor("#28323d"))
        if c == 7:
            item.setForeground(QColor("#2e7d5b") if p.passed else QColor("#b4413c"))
            f = item.font()
            f.setBold(True)
            item.setFont(f)
        table.setItem(r, c, item)


def _repolish(w) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
