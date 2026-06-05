"""
nodes.test_points — Test Points Table  (UI_SPEC §5.2)

Source node.  An editable, spreadsheet-like grid of raw measured rows for one
**physical pump** (the branch identity).  Emits a ``TestPointSet``.

- comma- or dot-decimals accepted (Excel-friendly paste)
- read-only computed ``Head = (P_dis − P_suc)/(ρ·g)`` and ``η`` columns, live
- ≥ 3 points required for a degree-3 fit; warns if a shut-off point is missing
"""

from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem, QWidget,
)

from ..binding import row_efficiency_pct, row_head_m
from ..numfmt import fmt, parse_decimal
from ..persistence import testset_from_json
from ..sample_data import SINGLE_PUMP_JSON
from ..signals import TestPointSet, TestRow
from .base import BaseNode, PortSpec
from . import ui

_COLS = ["Q", "P_suc", "P_dis", "T_water", "N", "P", "Head", "η"]
_UNITS = ["m³/h", "", "", "°C", "rpm", "kW", "m", "%"]
_EDITABLE = {0, 1, 2, 3, 4, 5}
_KEYS = ["q", "p_suc", "p_dis", "temp_c", "n", "power"]


class TestPointsTableNode(BaseNode):
    kind = "test_points"
    title = "Test Points Table"
    glyph = "▦"
    is_source = True
    inputs = []
    outputs = [PortSpec("TestPointSet", "TestPointSet")]

    def default_settings(self) -> Dict:
        tps = testset_from_json(SINGLE_PUMP_JSON)
        return {
            "pump_tag": tps.pump_tag,
            "unit": tps.pressure_unit,
            "rows": [
                {
                    "q": r.q_m3h, "p_suc": r.p_suction, "p_dis": r.p_discharge,
                    "temp_c": r.temp_c, "n": r.speed_rpm, "power": r.power_kw,
                    "head": r.head_m, "eff": r.efficiency_pct,
                }
                for r in tps.rows
            ],
        }

    # -- payload -----------------------------------------------------------
    def to_signal(self) -> TestPointSet:
        s = self.settings
        rows = []
        for r in s["rows"]:
            rows.append(
                TestRow(
                    q_m3h=float(r.get("q") or 0.0),
                    p_suction=float(r.get("p_suc") or 0.0),
                    p_discharge=float(r.get("p_dis") or 0.0),
                    temp_c=float(r.get("temp_c") or 25.0),
                    speed_rpm=float(r.get("n") or 0.0),
                    power_kw=float(r.get("power") or 0.0),
                    head_m=r.get("head"),
                    efficiency_pct=r.get("eff"),
                )
            )
        return TestPointSet(
            pump_tag=str(s["pump_tag"]).strip(),
            rows=tuple(rows),
            pressure_unit=str(s["unit"]),
        )

    def compute(self, inputs) -> Dict[str, object]:
        tps = self.to_signal()
        ok, msg = tps.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        shutoff = "" if tps.has_shutoff() else " · no shut-off pt"
        self.status = f"{tps.pump_tag} · {len(tps.rows)} points{shutoff}"
        self.state = "ok"
        return {"TestPointSet": tps}

    def port_label(self, name: str) -> str:
        return "TestPoints"

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "Test Points Table",
            "Raw measured rows for one physical pump. Head and η are computed live.",
            width=720,
        )
        banner = ui.Banner()

        tag = ui.line_edit(s["pump_tag"], None, "physical unit TAG, e.g. B-2351105A")
        unit = ui.combo([("bar", "bar"), ("kgf/cm²", "kgf/cm**2")], s["unit"], None)

        table = QTableWidget(len(s["rows"]), len(_COLS))
        table.setHorizontalHeaderLabels(
            [f"{c}\n[{u}]" if u else c for c, u in zip(_COLS, _UNITS)]
        )
        table.verticalHeader().setVisible(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setObjectName("TestGrid")

        def recompute_status():
            ok, msg = self.to_signal().is_valid()
            if ok and not self.to_signal().has_shutoff():
                banner.show_message(
                    "OK — but no shut-off point (Q≈0). Shut-off head check will extrapolate.",
                    "warn",
                )
            else:
                banner.show_message("" if ok else msg, "info" if ok else "error")
            on_change()

        def refresh_computed(row_idx: int):
            r = s["rows"][row_idx]
            tr = TestRow(
                q_m3h=float(r.get("q") or 0.0),
                p_suction=float(r.get("p_suc") or 0.0),
                p_discharge=float(r.get("p_dis") or 0.0),
                temp_c=float(r.get("temp_c") or 25.0),
                speed_rpm=float(r.get("n") or 0.0),
                power_kw=float(r.get("power") or 0.0),
                head_m=r.get("head"),
                efficiency_pct=r.get("eff"),
            )
            try:
                head = row_head_m(tr, s["unit"])
                eff = row_efficiency_pct(tr, head)
            except Exception:
                head, eff = 0.0, None
            _set_ro(table, row_idx, 6, fmt(head, 2))
            _set_ro(table, row_idx, 7, fmt(eff, 1) if eff is not None else "—")

        def fill():
            table.blockSignals(True)
            table.setRowCount(len(s["rows"]))
            for i, r in enumerate(s["rows"]):
                for c, key in enumerate(_KEYS):
                    val = r.get(key)
                    item = QTableWidgetItem("" if val is None else f"{float(val):g}")
                    table.setItem(i, c, item)
                refresh_computed(i)
            table.blockSignals(False)

        def on_cell_changed(item):
            row, col = item.row(), item.column()
            if col not in _EDITABLE or row >= len(s["rows"]):
                return
            val = parse_decimal(item.text(), None)
            s["rows"][row][_KEYS[col]] = val
            table.blockSignals(True)
            item.setText("" if val is None else f"{val:g}")
            refresh_computed(row)
            table.blockSignals(False)
            recompute_status()

        table.itemChanged.connect(on_cell_changed)
        tag.textChanged.connect(lambda v: (s.__setitem__("pump_tag", v), recompute_status()))
        unit.currentIndexChanged.connect(
            lambda _: (s.__setitem__("unit", unit.currentData()), fill(), recompute_status())
        )

        # toolbar
        def add_row():
            s["rows"].append({k: None for k in _KEYS} | {"head": None, "eff": None})
            fill()
            recompute_status()

        def del_rows():
            for idx in sorted({i.row() for i in table.selectedItems()}, reverse=True):
                if 0 <= idx < len(s["rows"]):
                    del s["rows"][idx]
            fill()
            recompute_status()

        def move(delta: int):
            rows = sorted({i.row() for i in table.selectedItems()})
            if not rows:
                return
            for idx in (rows if delta < 0 else reversed(rows)):
                j = idx + delta
                if 0 <= j < len(s["rows"]):
                    s["rows"][idx], s["rows"][j] = s["rows"][j], s["rows"][idx]
            fill()
            recompute_status()

        def paste():
            text = QGuiApplication.clipboard().text()
            if not text.strip():
                return
            new_rows = []
            for line in text.splitlines():
                if not line.strip():
                    continue
                cells = line.replace(";", "\t").split("\t")
                rd = {k: None for k in _KEYS} | {"head": None, "eff": None}
                for c, key in enumerate(_KEYS):
                    if c < len(cells):
                        rd[key] = parse_decimal(cells[c], None)
                new_rows.append(rd)
            if new_rows:
                s["rows"] = new_rows
                fill()
                recompute_status()

        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)
        for label, fn in [
            ("＋ Add row", add_row), ("－ Remove", del_rows),
            ("↑ Up", lambda: move(-1)), ("↓ Down", lambda: move(1)),
            ("⎘ Paste", paste),
        ]:
            b = QPushButton(label)
            b.setObjectName("ToolButton")
            b.clicked.connect(fn)
            bl.addWidget(b)
        bl.addStretch(1)

        dlg.add(ui.section("Pump identity"))
        dlg.add(ui.row("Pump TAG", tag))
        dlg.add(ui.row("Pressure unit", unit))
        dlg.add(ui.hline())
        dlg.add(ui.section("Measured points"))
        dlg.add(bar)
        dlg.add(table)
        dlg.add(banner)
        fill()
        recompute_status()
        dlg.resize(760, 620)
        return dlg


def _set_ro(table: QTableWidget, row: int, col: int, text: str) -> None:
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemIsEnabled)
    item.setForeground(QColor("#3b6ea5"))
    item.setBackground(QColor("#f1f5f9"))
    table.setItem(row, col, item)
