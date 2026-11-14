"""
nodes.mechanical_run — Mechanical Run  (sprint 6 / UC-11)

Source node.  A time-stamped multi-channel log of the mechanical running test
(vibration, temperatures, pressures, flow, power ...) for one physical pump.
Emits a ``MechanicalRunSet`` and a ``MechanicalRunResultSignal`` (the verdict
against ``pump.mechanical_run`` criteria, plus the trend plot).  The result
connects to Report Export's multi ``branch`` input.

Runtime settings::

    {"pump_tag": str,
     "columns": [{"name", "dimension", "unit" (display label), "role"}, ...],
     "rows": [{"time": "HH:MM", "values": {<name>: float | None}}, ...],
     "overrides": {"min_duration": None | {"value", "unit"},
                   "role_max": {role: {"value", "unit"}},
                   "stabilisation": {role: {"delta": {...}, "window": {...}}}}}
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from pump import Q_
from pump.mechanical_run import ROLES, Channel, MechanicalRunLog, RunReading

from .. import units
from ..binding import check_mechanical_run
from ..numfmt import parse_decimal
from ..settings_codec import DURATION_LABELS, ROLE_DIMENSIONS, delta_pint
from ..signals import MechanicalRunSet
from .base import BaseNode, PortSpec
from . import ui

_TIME = re.compile(r"^\d{1,2}:\d{2}$")
_DIMENSIONS = [
    "capacity",
    "pressure",
    "power",
    "temperature",
    "vibration_velocity",
    "speed",
    "head",
    "length",
]


# ---------------------------------------------------------------------------
# Qt-free helpers
# ---------------------------------------------------------------------------


def _norm_time(text) -> Optional[str]:
    t = str(text or "").strip()
    if not _TIME.match(t):
        return None
    return t.zfill(5)


def _next_time(rows: List[dict]) -> str:
    for r in reversed(rows):
        t = _norm_time(r.get("time"))
        if t:
            h, m = int(t[:2]), int(t[3:])
            total = (h * 60 + m + 15) % (24 * 60)
            return f"{total // 60:02d}:{total % 60:02d}"
    return "00:00"


def _col_pint(col: dict) -> str:
    return units.pint_str(col["dimension"], col["unit"])


def build_log(settings: dict) -> MechanicalRunLog:
    """``pump.mechanical_run.MechanicalRunLog`` from the node settings."""
    cols = [c for c in settings.get("columns") or [] if str(c.get("name", "")).strip()]
    channels = tuple(
        Channel(str(c["name"]).strip(), c.get("role") or "other") for c in cols
    )
    readings = []
    for r in settings.get("rows") or []:
        t = _norm_time(r.get("time"))
        if t is None:
            continue
        raw = r.get("values") or {}
        values = {}
        for c in cols:
            v = raw.get(c["name"])
            if v is not None:
                values[str(c["name"]).strip()] = Q_(float(v), _col_pint(c))
        readings.append(RunReading(time=t, values=values))
    return MechanicalRunLog(channels=channels, readings=tuple(readings))


def overrides_to_quantities(ov: Optional[dict]) -> dict:
    """Runtime override dicts (display labels) -> Quantities for the binding."""
    out: dict = {"min_duration": None, "role_max": {}, "stabilisation": {}}
    if not ov:
        return out
    md = ov.get("min_duration")
    if isinstance(md, dict) and md.get("value") is not None:
        out["min_duration"] = Q_(
            float(md["value"]), DURATION_LABELS.get(md["unit"], md["unit"])
        )
    for role, q in (ov.get("role_max") or {}).items():
        dim = ROLE_DIMENSIONS.get(role)
        if not dim or not isinstance(q, dict):
            continue
        try:
            out["role_max"][role] = Q_(
                float(q["value"]), units.pint_str(dim, q["unit"])
            )
        except Exception:
            continue
    for role, st in (ov.get("stabilisation") or {}).items():
        dim = ROLE_DIMENSIONS.get(role)
        if not dim or not isinstance(st, dict):
            continue
        try:
            d, w = st["delta"], st["window"]
            out["stabilisation"][role] = (
                Q_(float(d["value"]), delta_pint(dim, d["unit"])),
                Q_(float(w["value"]), DURATION_LABELS.get(w["unit"], w["unit"])),
            )
        except Exception:
            continue
    return out


def verdict_label(result) -> str:
    """Status verdict; provisional when the limits are not verified."""
    if not getattr(result, "passed", False):
        text = "FAILED"
    elif not getattr(result, "fully_assessed", True):
        text = "PASSED (not fully assessed)"
    else:
        text = "PASSED"
    if not getattr(result, "verified", True):
        text += " (unverified limits)"
    return text


def _get(row, key, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _cell(v) -> str:
    if v is None:
        return "—"
    mag = getattr(v, "magnitude", None)
    if mag is not None:
        try:
            return f"{float(mag):.4g}"
        except (TypeError, ValueError):
            return str(v)
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _channel_rows(result) -> list:
    for attr in ("channels", "rows", "channel_results", "checks"):
        v = getattr(result, attr, None)
        if v:
            return list(v)
    return []


def _default_columns() -> List[dict]:
    return [
        {
            "name": "Vib filtered",
            "dimension": "vibration_velocity",
            "unit": "mm/s",
            "role": "vibration_filtered",
        },
        {
            "name": "Vib unfiltered",
            "dimension": "vibration_velocity",
            "unit": "mm/s",
            "role": "vibration_unfiltered",
        },
        {
            "name": "Sump",
            "dimension": "temperature",
            "unit": "°C",
            "role": "oil_temperature",
        },
    ]


def _default_rows() -> List[dict]:
    rows = []
    for i in range(5):
        rows.append(
            {
                "time": f"{6 + i:02d}:00",
                "values": {"Vib filtered": 1.0, "Vib unfiltered": 1.5, "Sump": 50.0},
            }
        )
    return rows


class MechanicalRunNode(BaseNode):
    kind = "mechanical_run"
    title = "Mechanical Run"
    glyph = "⟳"
    is_source = True
    inputs = [PortSpec("RatedPoint", "RatedPoint")]
    outputs = [
        PortSpec("MechanicalRunResult", "MechanicalRunResult"),
        PortSpec("MechanicalRunSet", "MechanicalRunSet"),
    ]

    def default_settings(self) -> Dict:
        return {
            "pump_tag": "B-0001",
            "columns": _default_columns(),
            "rows": _default_rows(),
            "overrides": {"min_duration": None, "role_max": {}, "stabilisation": {}},
        }

    def port_label(self, name: str) -> str:
        return {
            "RatedPoint": "Rated",
            "MechanicalRunResult": "Result",
            "MechanicalRunSet": "Log",
        }.get(name, name)

    # -- payload -----------------------------------------------------------
    def compute(self, inputs) -> Dict[str, object]:
        s = self.settings
        self._signal = None
        self._result = None
        self._rated = self.first(inputs, "RatedPoint")
        try:
            log = build_log(s)
        except Exception as exc:
            return self.emit_nothing(f"{type(exc).__name__}: {exc}", "invalid")
        if not log.channels or len(log.readings) < 2:
            return self.emit_nothing("Need ≥ 1 channel and ≥ 2 readings", "invalid")
        # A template whose readings are still blank (e.g. the witness-day sheet)
        # must not report a verdict or appear in the report as a pump.
        filled = [
            r for r in log.readings if any(v is not None for v in r.values.values())
        ]
        if len(filled) < 2:
            return self.emit_nothing("Enter readings: < 2 rows have values", "invalid")
        run_set = MechanicalRunSet(pump_tag=str(s["pump_tag"]).strip(), log=log)
        try:
            sig = check_mechanical_run(
                run_set, self._rated, overrides_to_quantities(s.get("overrides"))
            )
        except Exception as exc:
            return self.emit_nothing(f"{type(exc).__name__}: {exc}", "invalid")
        self._signal = sig
        self._result = sig.result
        duration = getattr(sig.result, "duration", None) or log.duration
        hours = float(duration.to("h").magnitude)
        verdict = verdict_label(sig.result)
        self.status = (
            f"{run_set.pump_tag} · {len(log.readings)} readings · "
            f"{hours:.1f} h · {verdict}"
        )
        self.state = "ok" if getattr(sig.result, "passed", False) else "reject"
        return {"MechanicalRunResult": sig, "MechanicalRunSet": run_set}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        s.setdefault("columns", _default_columns())
        s.setdefault("rows", [])
        ov0 = s.setdefault("overrides", {})
        ov0.setdefault("min_duration", None)
        ov0.setdefault("role_max", {})
        ov0.setdefault("stabilisation", {})
        cols: List[dict] = s["columns"]

        dlg = ui.PropertyDialog(
            parent,
            "Mechanical Run",
            "Time-stamped readings of the mechanical running test, checked "
            "against the acceptance criteria.",
            width=760,
        )
        banner = ui.Banner()
        tag = ui.line_edit(s["pump_tag"], None, "physical unit TAG, e.g. B-34004A")

        col_table = QTableWidget(0, 4)
        col_table.setObjectName("RunColumns")
        col_table.setHorizontalHeaderLabels(["Name", "Dimension", "Unit", "Role"])
        col_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        grid = QTableWidget(0, 1)
        grid.setObjectName("RunGrid")
        grid.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        result_table = QTableWidget(0, 7)
        result_table.setObjectName("RunResult")
        result_table.setHorizontalHeaderLabels(
            ["Channel", "Unit", "Min", "Max", "Last", "Limit", "Status"]
        )
        result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        result_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # -- result / banner ------------------------------------------------
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

        def recompute():
            on_change()
            kind = {"ok": "ok", "reject": "error"}.get(self.state, "warn")
            banner.show_message(self.status, kind)
            fill_result()

        # -- readings grid --------------------------------------------------
        def update_grid_headers():
            grid.setHorizontalHeaderLabels(
                ["Time"] + [f"{c['name']} [{c['unit']}]" for c in cols]
            )

        def fill_grid():
            grid.blockSignals(True)
            grid.setColumnCount(1 + len(cols))
            update_grid_headers()
            grid.setRowCount(len(s["rows"]))
            for i, r in enumerate(s["rows"]):
                grid.setItem(i, 0, QTableWidgetItem(str(r.get("time", ""))))
                vals = r.get("values") or {}
                for j, c in enumerate(cols):
                    v = vals.get(c["name"])
                    grid.setItem(
                        i, 1 + j, QTableWidgetItem("" if v is None else f"{float(v):g}")
                    )
            grid.blockSignals(False)

        def on_grid_changed(item):
            row, col = item.row(), item.column()
            if row >= len(s["rows"]):
                return
            r = s["rows"][row]
            if col == 0:
                r["time"] = item.text().strip()
            elif col - 1 < len(cols):
                val = parse_decimal(item.text(), None)
                r.setdefault("values", {})[cols[col - 1]["name"]] = val
                grid.blockSignals(True)
                item.setText("" if val is None else f"{val:g}")
                grid.blockSignals(False)
            recompute()

        grid.itemChanged.connect(on_grid_changed)

        # -- column definitions ---------------------------------------------
        def fill_cols():
            col_table.blockSignals(True)
            col_table.setRowCount(len(cols))
            for i, c in enumerate(cols):
                col_table.setItem(i, 0, QTableWidgetItem(c["name"]))
                dim = ui.combo([(d, d) for d in _DIMENSIONS], c["dimension"], None)
                unit = ui.combo(units.options_for(c["dimension"]), c["unit"], None)
                role = ui.combo([(r, r) for r in ROLES], c["role"], None)
                dim.currentIndexChanged.connect(
                    lambda _=None, i=i, w=dim: on_dimension(i, w.currentData())
                )
                unit.currentIndexChanged.connect(
                    lambda _=None, i=i, w=unit: on_unit(i, w.currentData())
                )
                role.currentIndexChanged.connect(
                    lambda _=None, i=i, w=role: on_role(i, w.currentData())
                )
                col_table.setCellWidget(i, 1, dim)
                col_table.setCellWidget(i, 2, unit)
                col_table.setCellWidget(i, 3, role)
            col_table.blockSignals(False)

        def on_dimension(i, new):
            if not new or new == cols[i]["dimension"]:
                return
            cols[i]["dimension"] = new
            cols[i]["unit"] = units.PREFS.default_unit(new)
            fill_grid()
            QTimer.singleShot(0, fill_cols)
            recompute()

        def on_unit(i, new):
            c = cols[i]
            if not new or new == c["unit"]:
                return
            for r in s["rows"]:
                v = (r.get("values") or {}).get(c["name"])
                if v is not None:
                    try:
                        r["values"][c["name"]] = units.convert_display(
                            v, c["dimension"], c["unit"], new
                        )
                    except Exception:
                        pass
            c["unit"] = new
            fill_grid()
            recompute()

        def on_role(i, new):
            if new:
                cols[i]["role"] = new
                recompute()

        def on_col_name(item):
            if item.column() != 0 or item.row() >= len(cols):
                return
            c = cols[item.row()]
            new = item.text().strip()
            old = c["name"]
            taken = {x["name"] for x in cols if x is not c}
            if not new or new in taken:
                col_table.blockSignals(True)
                item.setText(old)
                col_table.blockSignals(False)
                return
            if new != old:
                for r in s["rows"]:
                    vals = r.get("values") or {}
                    if old in vals:
                        vals[new] = vals.pop(old)
                c["name"] = new
                fill_grid()
                recompute()

        col_table.itemChanged.connect(on_col_name)

        def add_column():
            n = len(cols) + 1
            while any(c["name"] == f"Channel {n}" for c in cols):
                n += 1
            cols.append(
                {
                    "name": f"Channel {n}",
                    "dimension": "temperature",
                    "unit": units.PREFS.default_unit("temperature"),
                    "role": "other",
                }
            )
            fill_cols()
            fill_grid()
            recompute()

        def del_column():
            idx = sorted({i.row() for i in col_table.selectedItems()}, reverse=True)
            if not idx and cols:
                idx = [len(cols) - 1]
            for i in idx:
                if 0 <= i < len(cols):
                    name = cols[i]["name"]
                    del cols[i]
                    for r in s["rows"]:
                        (r.get("values") or {}).pop(name, None)
            fill_cols()
            fill_grid()
            recompute()

        # -- rows -----------------------------------------------------------
        def add_row():
            s["rows"].append({"time": _next_time(s["rows"]), "values": {}})
            fill_grid()
            recompute()

        def del_rows():
            idx = sorted({i.row() for i in grid.selectedItems()}, reverse=True)
            for i in idx:
                if 0 <= i < len(s["rows"]):
                    del s["rows"][i]
            fill_grid()
            recompute()

        def _find_col(name: str) -> Optional[int]:
            f = name.strip().casefold()
            if not f:
                return None
            for i, c in enumerate(cols):
                if c["name"].casefold() == f:
                    return i
            for i, c in enumerate(cols):
                n = c["name"].casefold()
                if n.startswith(f) or f.startswith(n):
                    return i
            return None

        def _resolve_unit(dim: str, cell: str, unit_text: str) -> Optional[str]:
            try:
                key, label, _ref = units.parse_unit_header(cell)
                if label and units.COLUMN_DIMENSIONS.get(key) == dim:
                    return label
            except ValueError:
                pass
            try:
                return units._match_unit(dim, unit_text)
            except (ValueError, KeyError):
                return None

        def paste():
            text = QGuiApplication.clipboard().text()
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if not lines:
                return

            def split(line: str) -> List[str]:
                return line.replace(";", "\t").split("\t")

            first = split(lines[0])
            mapping = list(range(len(cols)))
            conv: Dict[int, str] = {}
            data = lines
            if _norm_time(first[0]) is None:  # header line
                data = lines[1:]
                mapping = []
                for j, cell in enumerate(first[1:]):
                    name, _, rest = cell.partition("[")
                    unit_text = rest.rstrip("] ").strip()
                    idx = _find_col(name)
                    if idx is None and j < len(cols):
                        idx = j
                    mapping.append(idx)
                    if idx is not None and unit_text:
                        label = _resolve_unit(cols[idx]["dimension"], cell, unit_text)
                        if label and label != cols[idx]["unit"]:
                            conv[idx] = label
            new_rows = []
            for line in data:
                cells = split(line)
                t = _norm_time(cells[0])
                if t is None:
                    continue
                values: Dict[str, Optional[float]] = {}
                for j, idx in enumerate(mapping):
                    if idx is None or j + 1 >= len(cells):
                        continue
                    v = parse_decimal(cells[j + 1], None)
                    if v is not None and idx in conv:
                        try:
                            v = units.convert_display(
                                v, cols[idx]["dimension"], conv[idx], cols[idx]["unit"]
                            )
                        except Exception:
                            pass
                    values[cols[idx]["name"]] = v
                new_rows.append({"time": t, "values": values})
            if new_rows:
                s["rows"] = new_rows
                fill_grid()
                recompute()

        def toolbar(buttons):
            bar = QWidget()
            bl = QHBoxLayout(bar)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(6)
            for label, fn in buttons:
                b = QPushButton(label)
                b.setObjectName("ToolButton")
                b.clicked.connect(lambda _=False, fn=fn: fn())
                bl.addWidget(b)
            bl.addStretch(1)
            return bar

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
            new: dict = {"min_duration": None, "role_max": {}, "stabilisation": {}}
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

        tag.textChanged.connect(lambda v: (s.__setitem__("pump_tag", v), recompute()))

        dlg.add(ui.section("Pump identity"))
        dlg.add(ui.row("Pump TAG", tag))
        dlg.add(ui.hline())
        dlg.add(ui.section("Channels"))
        dlg.add(toolbar([("＋ Channel", add_column), ("－ Channel", del_column)]))
        dlg.add(col_table)
        dlg.add(ui.hline())
        dlg.add(ui.section("Readings"))
        dlg.add(
            toolbar(
                [("＋ Add row", add_row), ("－ Remove", del_rows), ("⎘ Paste", paste)]
            )
        )
        dlg.add(grid)
        dlg.add(ui.hline())
        dlg.add(ui.section("Criteria overrides (blank = library criteria)"))
        dlg.add(og)
        dlg.add(ui.hline())
        dlg.add(ui.section("Verdict"))
        dlg.add(banner)
        dlg.add(result_table)

        fill_cols()
        fill_grid()
        recompute()
        dlg.resize(820, 860)
        return dlg
