"""
nodes.compliance — API 610 Compliance Check  (UI_SPEC §5.6)

Inputs ``FittedModel`` + ``RatedPoint`` → output ``ComplianceResult``.
Per-parameter Actual / Predicted / Min / Max / Deviation / Tolerance / Verdict,
plus a bold overall APPROVED / REJECTED banner.  Numbers come from
``PerformanceChecker`` so they match the library's report tables.  The criteria
(edition + client overlay) come from the rated point; rows whose criteria are not
yet verified against the standard text carry an amber "unverified" badge.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
)

from pump import Q_

from ..binding import check_compliance, default_tolerances
from ..numfmt import fmt
from ..style import ui_font
from .base import BaseNode, PortSpec
from . import ui

_HEADERS = [
    "Parameter", "Actual", "Predicted", "Min", "Max", "Deviation", "Tol.", "Verdict",
    "Note",
]
_AMBER = "#b7791f"


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
        n_fail = sum(
            1
            for p in result.parameters
            if not p.passed and not p.informational and p.evaluated
        )
        # A verdict against criteria not verified from the standard text is
        # provisional: say so, instead of presenting it as final.
        tail = " (unverified criteria)" if result.unverified else ""
        if result.overall_pass:
            self.status = f"{result.pump_tag} · ✅ APPROVED{tail}"
            self.state = "ok"
        elif result.verdict_label == "NOT FULLY ASSESSED":
            self.status = (
                f"{result.pump_tag} · ⚠ NOT FULLY ASSESSED: "
                + ", ".join(result.not_evaluated)
            )
            self.state = "reject"
        else:
            self.status = f"{result.pump_tag} · ❌ {n_fail} out of tolerance{tail}"
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
            "Deviation δ = (predicted − rated)/rated.  Head min ≤ pred ≤ max · "
            "Power δ≤tol · Shut-off |δ|≤tol · Efficiency: information only unless "
            "a purchaser tolerance is set.",
            width=680,
        )
        verdict = QLabel(objectName="VerdictBanner")
        verdict.setFont(ui_font(15, QFont.Bold))
        criteria_lbl = QLabel("")
        unverified_lbl = QLabel("")
        unverified_lbl.setStyleSheet(f"color: {_AMBER};")
        unverified_lbl.setWordWrap(True)
        parallel_lbl = QLabel("")
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
        # API 610 does not rate efficiency: it is judged only when the purchaser
        # specified a tolerance (e.g. N-553 9.14 for drivers >= 1 MW: -0 %).
        eff_guaranteed = ui.checkbox(
            "Efficiency is guaranteed (purchaser-specified tolerance)",
            cur.get("efficiency") is not None,
        )
        tol_eff = ui.spin((cur.get("efficiency") or 0.0) * 100, 0, 50, 0.5, 1, None)
        tol_eff.setEnabled(eff_guaranteed.isChecked())

        def refresh():
            on_change()
            result = getattr(self, "_last", None) if self.outputs_cache else None
            table.setRowCount(0)
            if not result:
                verdict.setText("—  awaiting inputs")
                verdict.setProperty("verdict", "idle")
                _repolish(verdict)
                criteria_lbl.setVisible(False)
                unverified_lbl.setVisible(False)
                parallel_lbl.setVisible(False)
                return
            for p in result.parameters:
                _append_param(table, p)
            # Show every row without an inner scrollbar (5-6 rows).
            table.resizeRowsToContents()
            rows_h = sum(table.rowHeight(i) for i in range(table.rowCount()))
            table.setMinimumHeight(table.horizontalHeader().height() + rows_h + 6)
            ok = result.overall_pass
            tail = "  (unverified criteria)" if result.unverified else ""
            label = {
                "APPROVED": "APPROVED ✓",
                "NOT FULLY ASSESSED": "NOT FULLY ASSESSED ⚠",
            }.get(result.verdict_label, "REJECTED ✗")
            verdict.setText(f"{label}{tail}   ·   {result.pump_tag}")
            verdict.setProperty("verdict", "pass" if ok else "fail")
            _repolish(verdict)
            criteria_lbl.setText(f"Criteria: {result.criteria_label}")
            criteria_lbl.setVisible(bool(result.criteria_label))
            if result.unverified:
                unverified_lbl.setText(
                    "⚠ Unverified against the standard text: "
                    + ", ".join(str(u) for u in result.unverified)
                )
                unverified_lbl.setVisible(True)
            else:
                unverified_lbl.setVisible(False)
            if result.parallel_ok is None:
                parallel_lbl.setVisible(False)
            else:
                parallel_lbl.setText(
                    "Parallel operation: shut-off head rise "
                    + ("OK ✓" if result.parallel_ok else "NOT MET ✗")
                )
                parallel_lbl.setVisible(True)
            if result.overridden:
                override_chip.show_message(
                    "⚠ Tolerances overridden — differ from the acceptance-criteria defaults.", "warn"
                )
            else:
                override_chip.setVisible(False)

        def write_tol():
            s["tolerances"] = {
                "head": tol_head.value() / 100.0,
                "shutoff": tol_shut.value() / 100.0,
                "power": tol_pow.value() / 100.0,
                "efficiency": (
                    tol_eff.value() / 100.0 if eff_guaranteed.isChecked() else None
                ),
            }
            tol_eff.setEnabled(eff_guaranteed.isChecked())
            refresh()

        for sb in (tol_head, tol_shut, tol_pow, tol_eff):
            sb.valueChanged.connect(lambda _=None: write_tol())
        eff_guaranteed.toggled.connect(lambda _=None: write_tol())

        reset = QPushButton("Reset to API 610 standard")
        reset.setObjectName("ToolButton")

        def do_reset():
            s["tolerances"] = {}
            b = default_tolerances(getattr(self, "_rated", None) or _Fallback())
            for sb, key in ((tol_head, "head"), (tol_shut, "shutoff"),
                            (tol_pow, "power"), (tol_eff, "efficiency")):
                sb.blockSignals(True)
                sb.setValue((b[key] or 0.0) * 100)
                sb.blockSignals(False)
            eff_guaranteed.blockSignals(True)
            eff_guaranteed.setChecked(b["efficiency"] is not None)
            eff_guaranteed.blockSignals(False)
            tol_eff.setEnabled(b["efficiency"] is not None)
            refresh()

        reset.clicked.connect(do_reset)

        dlg.add(verdict)
        dlg.add(criteria_lbl)
        dlg.add(unverified_lbl)
        dlg.add(parallel_lbl)
        dlg.add(override_chip)
        dlg.add(table)
        dlg.add(ui.hline())
        dlg.add(ui.section("Tolerances (editable)"))
        dlg.add(ui.row("Head", tol_head, "%"))
        dlg.add(ui.row("Shut-off head", tol_shut, "%"))
        dlg.add(ui.row("Power", tol_pow, "%"))
        dlg.add(ui.row("", eff_guaranteed))
        dlg.add(ui.row("Efficiency", tol_eff, "%"))
        dlg.add(ui.row("", reset))
        refresh()
        dlg.resize(700, 640)
        return dlg


class _Fallback:
    """Stand-in rated point for the tolerance dialog before a RatedPoint is wired."""

    head = Q_(73.0, "m")
    head_shutoff = Q_(117.0, "m")
    standard_key = "api610:12"
    client = None


def _append_param(table: QTableWidget, p) -> None:
    r = table.rowCount()
    table.insertRow(r)
    notes = []
    if not getattr(p, "verified", True):
        notes.append("unverified")
    if getattr(p, "extrapolated", False):
        notes.append("extrapolated")
    if getattr(p, "note", ""):
        notes.append(p.note)
    info = getattr(p, "informational", False)
    evaluated = getattr(p, "evaluated", True)
    cells = [
        p.name, fmt(p.actual),
        fmt(p.predicted) if p.predicted is not None else "—",
        fmt(p.minimum) if p.minimum is not None else "—",
        fmt(p.maximum) if p.maximum is not None else "—",
        f"{p.deviation * 100:+.2f} %" if p.deviation is not None else "—",
        f"{p.tolerance * 100:.1f} %" if p.tolerance is not None else "—",
        "info" if info else ("n/e ⚠" if not evaluated else ("✅" if p.passed else "❌")),
        " · ".join(notes),
    ]
    for c, text in enumerate(cells):
        item = QTableWidgetItem(str(text))
        if c == 0:
            item.setForeground(QColor("#28323d"))
        if c == 7:
            item.setForeground(
                QColor("#5d6b78") if info
                else QColor("#2e7d5b") if p.passed else QColor("#b4413c")
            )
            f = item.font()
            f.setBold(True)
            item.setFont(f)
        if c == 8 and notes:
            item.setForeground(QColor(_AMBER))
        table.setItem(r, c, item)


def _repolish(w) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
