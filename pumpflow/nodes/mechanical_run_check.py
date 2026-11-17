"""
nodes.mechanical_run_check — MRT Check  (UC-11)

Judges a mechanical-run log against the acceptance criteria.  The log comes
from an **MRT Log** node (``MechanicalRunSet``).  The rated point selects the
edition, the client overlay and the pump type, and with them the vibration
limits.  The optional fitted curve gives the BEP power for the
11th/12th-edition high-speed rule.  Emits a ``MechanicalRunResult`` (the
verdict, per-channel table and trend plot) for Report Export.

Runtime settings::

    {"overrides": {"min_duration": None | {"value", "unit"},
                   "role_max": {role: {"value", "unit"}},
                   "stabilisation": {role: {"delta": {...}, "window": {...}}}}}

Overrides are the witness's own limits on top of the criteria; any override
makes the verdict provisional ("unverified limits").
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from pump.mechanical_run import ROLES

from .. import units
from ..binding import check_mechanical_run
from ..settings_codec import ROLE_DIMENSIONS
from .base import BaseNode, PortSpec
from .mechanical_run import (
    _cell,
    _channel_rows,
    _get,
    overrides_to_quantities,
    verdict_label,
)
from . import ui


def _empty_overrides() -> dict:
    return {"min_duration": None, "role_max": {}, "stabilisation": {}}


class MechanicalRunCheckNode(BaseNode):
    kind = "mechanical_run_check"
    title = "MRT Check"
    glyph = "✓"
    inputs = [
        PortSpec("MechanicalRunSet", "MechanicalRunSet"),
        PortSpec("RatedPoint", "RatedPoint"),
        PortSpec("FittedModel", "FittedModel"),
    ]
    outputs = [PortSpec("MechanicalRunResult", "MechanicalRunResult")]

    def default_settings(self) -> Dict:
        return {"overrides": _empty_overrides()}

    def port_label(self, name: str) -> str:
        return {
            "MechanicalRunSet": "Log",
            "RatedPoint": "Rated",
            "FittedModel": "Model",
            "MechanicalRunResult": "Result",
        }.get(name, name)

    # -- payload -----------------------------------------------------------
    def compute(self, inputs) -> Dict[str, object]:
        self._signal = None
        self._result = None
        run_set = self.first(inputs, "MechanicalRunSet")
        self._run_set = run_set
        self._rated = self.first(inputs, "RatedPoint")
        self._fitted = self.first(inputs, "FittedModel")
        if run_set is None:
            return self.emit_nothing("Connect an MRT Log", "idle")
        try:
            sig = check_mechanical_run(
                run_set,
                self._rated,
                overrides_to_quantities(self.settings.get("overrides")),
                fitted=self._fitted,
            )
        except Exception as exc:
            return self.emit_nothing(f"{type(exc).__name__}: {exc}", "invalid")
        self._signal = sig
        self._result = sig.result
        log = run_set.log
        duration = getattr(sig.result, "duration", None) or log.duration
        hours = float(duration.to("h").magnitude)
        self.status = (
            f"{run_set.pump_tag} · {len(log.readings)} readings · "
            f"{hours:.1f} h · {verdict_label(sig.result)}"
        )
        self.state = "ok" if getattr(sig.result, "passed", False) else "reject"
        return {"MechanicalRunResult": sig}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        ov0 = s.setdefault("overrides", _empty_overrides())
        ov0.setdefault("min_duration", None)
        ov0.setdefault("role_max", {})
        ov0.setdefault("stabilisation", {})

        dlg = ui.PropertyDialog(
            parent,
            "MRT Check",
            "The mechanical running test judged against the acceptance criteria "
            "of the rated point's edition, client overlay and pump type.",
            width=820,
            maximizable=True,
        )
        banner = ui.Banner()
        source = QLabel()
        source.setObjectName("Hint")
        source.setWordWrap(True)

        result_table = QTableWidget(0, 7)
        result_table.setObjectName("RunResult")
        result_table.setHorizontalHeaderLabels(
            ["Channel", "Unit", "Min", "Max", "Last", "Limit", "Status"]
        )
        result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        result_table.setMinimumHeight(300)  # every channel without scrolling

        trend = QLabel()
        trend.setObjectName("RunTrend")
        trend.setAlignment(Qt.AlignCenter)
        trend.setMinimumHeight(260)

        def fill_source():
            run_set = getattr(self, "_run_set", None)
            if run_set is None:
                source.setText("No log connected: wire an MRT Log into this node.")
                return
            rated = getattr(self, "_rated", None)
            fitted = getattr(self, "_fitted", None)
            parts = [
                f"Log: {run_set.pump_tag}, {len(run_set.log.readings)} readings.",
                (
                    (
                        f"Criteria: {rated.standard_key}"
                        + (f" + {rated.client}" if rated.client else "")
                        + (f", pump type {rated.pump_type}" if rated.pump_type else "")
                        + "."
                    )
                    if rated is not None
                    else "Criteria: library default (no rated point wired)."
                ),
                (
                    "High-speed rule power: BEP of the fitted curve."
                    if fitted is not None
                    else "High-speed rule power: rated power (no fitted curve wired)."
                ),
            ]
            source.setText("  ".join(parts))

        def fill_result():
            result = getattr(self, "_result", None)
            rows = _channel_rows(result) if result is not None else []
            result_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                status = str(_get(row, "status", "") or "")
                vals = [
                    _get(row, "name"),
                    _get(row, "unit"),
                    _cell(_get(row, "min")),
                    _cell(_get(row, "max")),
                    _cell(_get(row, "last")),
                    _cell(_get(row, "limit")),
                    status.upper(),
                ]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem("" if v is None else str(v))
                    item.setFlags(Qt.ItemIsEnabled)
                    if c == 6 and status.lower() == "fail":
                        item.setForeground(QColor("#b91c1c"))
                    result_table.setItem(i, c, item)
            sig = getattr(self, "_signal", None)
            png = getattr(sig, "plot_png", None) if sig is not None else None
            if png is not None:
                pix = QPixmap()
                pix.loadFromData(png.getvalue())
                trend.setPixmap(
                    pix.scaledToWidth(760, Qt.SmoothTransformation)
                    if pix.width() > 760
                    else pix
                )
            else:
                trend.clear()

        def recompute():
            on_change()
            kind = {"ok": "ok", "reject": "error"}.get(self.state, "warn")
            banner.show_message(self.status, kind)
            fill_source()
            fill_result()

        # -- criteria overrides ---------------------------------------------
        ov = s["overrides"]
        md = ov.get("min_duration") or {}
        md_chk = QCheckBox("Min duration")
        md_chk.setChecked(bool(md))
        md_spin = ui.spin(md.get("value", 4.0), 0.0, 1.0e5, 0.5, 2, None)
        md_unit = ui.combo([("h", "h"), ("min", "min")], md.get("unit", "h"), None)

        widgets: Dict[str, dict] = {}
        og = QWidget()
        gl = QGridLayout(og)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.addWidget(md_chk, 0, 0)
        gl.addWidget(md_spin, 0, 1)
        gl.addWidget(md_unit, 0, 2)
        grow = 1
        for role in ROLES:
            dim = ROLE_DIMENSIONS.get(role)
            if not dim:
                continue
            mx = (ov.get("role_max") or {}).get(role) or {}
            st = (ov.get("stabilisation") or {}).get(role) or {}
            w = {
                "dim": dim,
                "mx_chk": QCheckBox(f"{role}  max"),
                "mx_spin": ui.spin(mx.get("value", 0.0), -1.0e6, 1.0e6, 0.1, 3, None),
                "mx_unit": ui.combo(
                    units.options_for(dim),
                    mx.get("unit", units.canonical_unit(dim)),
                    None,
                ),
                "st_chk": QCheckBox("stab. Δ ≤"),
                "st_spin": ui.spin(
                    (st.get("delta") or {}).get("value", 2.0), 0.0, 1.0e6, 0.1, 3, None
                ),
                "st_unit": ui.combo(
                    units.options_for(dim),
                    (st.get("delta") or {}).get("unit", units.canonical_unit(dim)),
                    None,
                ),
                "win_spin": ui.spin(
                    (st.get("window") or {}).get("value", 60.0),
                    1.0,
                    1.0e5,
                    5.0,
                    1,
                    None,
                ),
            }
            w["mx_chk"].setChecked(bool(mx))
            w["st_chk"].setChecked(bool(st))
            gl.addWidget(w["mx_chk"], grow, 0)
            gl.addWidget(w["mx_spin"], grow, 1)
            gl.addWidget(w["mx_unit"], grow, 2)
            gl.addWidget(w["st_chk"], grow, 3)
            gl.addWidget(w["st_spin"], grow, 4)
            gl.addWidget(w["st_unit"], grow, 5)
            gl.addWidget(w["win_spin"], grow, 6)
            gl.addWidget(QLabel("min window"), grow, 7)
            widgets[role] = w
            grow += 1

        def apply_overrides(*_):
            new: dict = _empty_overrides()
            if md_chk.isChecked():
                new["min_duration"] = {
                    "value": md_spin.value(),
                    "unit": md_unit.currentData(),
                }
            for role, w in widgets.items():
                if w["mx_chk"].isChecked():
                    new["role_max"][role] = {
                        "value": w["mx_spin"].value(),
                        "unit": w["mx_unit"].currentData(),
                    }
                if w["st_chk"].isChecked():
                    new["stabilisation"][role] = {
                        "delta": {
                            "value": w["st_spin"].value(),
                            "unit": w["st_unit"].currentData(),
                        },
                        "window": {"value": w["win_spin"].value(), "unit": "min"},
                    }
            s["overrides"] = new
            recompute()

        md_chk.toggled.connect(apply_overrides)
        md_spin.valueChanged.connect(apply_overrides)
        md_unit.currentIndexChanged.connect(apply_overrides)
        for w in widgets.values():
            w["mx_chk"].toggled.connect(apply_overrides)
            w["mx_spin"].valueChanged.connect(apply_overrides)
            w["mx_unit"].currentIndexChanged.connect(apply_overrides)
            w["st_chk"].toggled.connect(apply_overrides)
            w["st_spin"].valueChanged.connect(apply_overrides)
            w["st_unit"].currentIndexChanged.connect(apply_overrides)
            w["win_spin"].valueChanged.connect(apply_overrides)

        dlg.add(ui.section("Verdict"))
        dlg.add(banner)
        dlg.add(source)
        dlg.add(result_table)
        dlg.add(ui.section("Trend"))
        dlg.add(trend)
        dlg.add(ui.hline())
        dlg.add(
            ui.section("Criteria overrides (unticked = criteria from the standard)")
        )
        dlg.add(og)

        recompute()
        dlg.resize(880, 860)
        return dlg
