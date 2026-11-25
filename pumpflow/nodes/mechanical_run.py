"""
nodes.mechanical_run — MRT Log  (sprint 6 / UC-11)

Source node.  A time-stamped multi-channel log of the mechanical running test
(vibration, temperatures, pressures, flow, power ...) for one physical pump.
It is data entry only and emits a ``MechanicalRunSet``.  The verdict is
produced by an **MRT Check** node (:mod:`.mechanical_run_check`) wired after it.

Runtime settings::

    {"pump_tag": str,
     "lubrication": "ring_oil" | "pressurized" | "oil_mist" | "grease"  (optional),
     "channel_groups": ["ambient", "bearing_metal", "vibration", ...]  (optional),
     "columns": [{"name", "dimension", "unit" (display label), "role",
                  "key" (standard channel id, optional),
                  "location" (bearing, optional)}, ...],
     "rows": [{"time": "HH:MM", "values": {<name>: float | None}}, ...]}

Like the Test Points table, the log offers **standard channels**: the
lubrication system adds its temperature channels (oil inlet / outlet per
bearing, sump, or bearing housing; plus the ambient the rise rules need), the
optional Rated Point input gives the pump type and with it the API 610
vibration locations, and a few optional groups add the rest
(:func:`standard_channels`, :func:`apply_standard_channels`).  Custom channels
(no ``key``) can still be added for anything else.

Projects saved before the split had one ``mechanical_run`` node holding the
criteria overrides too.  ``persistence.migrate`` splits such a node into this
log and an MRT Check that receives the overrides and the Report Export wire.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from pump import Q_
from pump.mechanical_run import (
    LUBRICATION,
    LUBRICATION_LABELS,
    ROLES,
    Channel,
    MechanicalRunLog,
    RunReading,
)
from pump.vibration import location_of_key, vibration_keys

from .. import units
from ..numfmt import parse_decimal
from ..settings_codec import DURATION_LABELS, ROLE_DIMENSIONS, delta_pint
from ..signals import MechanicalRunSet
from .base import BaseNode, PortSpec

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


def _find_col(cols: List[dict], name: str) -> Optional[int]:
    """Index of the channel a pasted header names (exact, then prefix match)."""
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
    """Display label of a pasted header's unit for a channel of dimension ``dim``."""
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


def paste_rows(text: str, cols: List[dict]) -> List[dict]:
    """MRT Log paste: tab- or ``;``-separated spreadsheet text -> readings.

    An optional header line (first cell not a ``HH:MM`` time) maps the columns to
    channels by name and may carry units (``"Flow [m³/h]"``); values are then
    converted into each channel's own unit.  Without a header the columns follow
    the channel order.  Returns ``[{"time": "HH:MM", "values": {name: float | None}}]``
    (rows without a valid time are dropped), ``[]`` when nothing is usable.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    def split(line: str) -> List[str]:
        return line.replace(";", "\t").split("\t")

    first = split(lines[0])
    mapping: List[Optional[int]] = list(range(len(cols)))
    conv: Dict[int, str] = {}
    data = lines
    if _norm_time(first[0]) is None:  # header line
        data = lines[1:]
        mapping = []
        for j, cell in enumerate(first[1:]):
            name, _, rest = cell.partition("[")
            unit_text = rest.rstrip("] ").strip()
            idx = _find_col(cols, name)
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
    return new_rows


def _col_pint(col: dict) -> str:
    return units.pint_str(col["dimension"], col["unit"])


# ---------------------------------------------------------------------------
# Standard channels (the Test Points idea: known columns, chosen by context)
# ---------------------------------------------------------------------------

#: Optional channel groups, in display order: (id, label).
CHANNEL_GROUPS = (
    ("vibration", "Vibration at the API 610 locations of the pump type"),
    ("ambient", "Ambient temperature (test cell)"),
    ("bearing_metal", "Bearing metal temperatures (sensors supplied)"),
    ("oil_pressure", "Oil pressure"),
    ("seal_pressure", "Seal / barrier pressure"),
    ("power", "Power"),
)
_GROUP_IDS = tuple(g for g, _ in CHANNEL_GROUPS)
# The lubrication systems whose rules are rises above the ambient temperature.
_NEEDS_AMBIENT = ("ring_oil", "oil_mist", "grease")


def _col(key, name, dimension, role, location="", unit=None) -> dict:
    col = {
        "key": key,
        "name": name,
        "dimension": dimension,
        "unit": unit or units.PREFS.default_unit(dimension),
        "role": role,
    }
    if location:
        col["location"] = location
    return col


def standard_channels(
    lubrication: Optional[str], groups=(), pump_type: Optional[str] = None
) -> List[dict]:
    """The standard MRT Log columns for a lubrication system and groups.

    Flow always; vibration (overall and filtered, RMS) at the API 610
    measurement locations of ``pump_type``; the temperature channels of the
    lubrication system (pressurized: oil inlet + oil outlet per bearing;
    ring-oil / splash: oil sump; oil mist and grease: bearing housing per
    bearing) and the ambient temperature their rise rules need; then the
    optional ``groups`` (:data:`CHANNEL_GROUPS`).

    >>> [c["name"] for c in standard_channels("pressurized", ("vibration", "ambient"), "OH6")]
    ['Flow', 'Gearbox overall', 'Gearbox filt.', 'Oil inlet', 'Oil outlet DE', 'Oil outlet NDE', 'Ambient']
    >>> [c["role"] for c in standard_channels("ring_oil")][1:]
    ['oil_temperature', 'ambient_temperature']
    """
    groups = set(groups or ())
    cols = [_col("flow", "Flow", "capacity", "flow")]
    if "vibration" in groups:
        for key in vibration_keys(pump_type):
            loc, filtered = location_of_key(key)
            cols.append(
                _col(
                    key,
                    f"{loc.short} {'filt.' if filtered else 'overall'}",
                    "vibration_velocity",
                    "vibration_filtered" if filtered else "vibration_unfiltered",
                    loc.short,
                    unit="mm/s",
                )
            )
    temp = "temperature"
    if lubrication == "pressurized":
        cols.append(_col("oil_in", "Oil inlet", temp, "oil_inlet_temperature"))
        for b in ("DE", "NDE"):
            cols.append(
                _col(f"oil_out_{b.lower()}", f"Oil outlet {b}", temp,
                     "oil_outlet_temperature", b)
            )
    elif lubrication == "ring_oil":
        cols.append(_col("oil_sump", "Oil sump", temp, "oil_temperature"))
    elif lubrication in ("oil_mist", "grease"):
        for b in ("DE", "NDE"):
            cols.append(
                _col(f"housing_{b.lower()}", f"Housing {b}", temp,
                     "housing_temperature", b)
            )
    if "bearing_metal" in groups:
        for b in ("DE", "NDE"):
            cols.append(
                _col(f"bearing_{b.lower()}", f"Bearing {b}", temp,
                     "bearing_temperature", b)
            )
    if "ambient" in groups or lubrication in _NEEDS_AMBIENT:
        cols.append(_col("ambient", "Ambient", temp, "ambient_temperature"))
    if "oil_pressure" in groups:
        cols.append(_col("oil_pressure", "Oil pressure", "pressure", "oil_pressure"))
    if "seal_pressure" in groups:
        cols.append(_col("seal_pressure", "Seal pressure", "pressure", "seal_pressure"))
    if "power" in groups:
        cols.append(_col("power", "Power", "power", "power"))
    return cols


def _has_data(rows, name) -> bool:
    return any((r.get("values") or {}).get(name) is not None for r in rows or [])


def apply_standard_channels(settings: dict, pump_type: Optional[str] = None) -> List[dict]:
    """New ``columns`` after a change of lubrication system or channel groups.

    Standard channels that are wanted are added in their canonical order (a
    custom channel with the same name is adopted: it gets the standard role
    and key, and keeps its unit and readings).  Standard channels no longer
    wanted are dropped, unless they hold readings (nothing entered is ever
    hidden).  Custom channels stay, after the standard ones.
    """
    rows = settings.get("rows") or []
    current = [dict(c) for c in settings.get("columns") or []]
    wanted = standard_channels(
        settings.get("lubrication"), settings.get("channel_groups") or (), pump_type
    )
    by_key = {c["key"]: c for c in current if c.get("key")}
    by_name = {c["name"]: c for c in current if not c.get("key")}
    out, used = [], set()
    for w in wanted:
        have = by_key.get(w["key"]) or by_name.get(w["name"])
        if have is not None:
            used.add(id(have))
            merged = {**w, "name": have["name"], "unit": have["unit"]}
            if have.get("dimension") != w["dimension"]:
                merged["unit"] = w["unit"]
            out.append(merged)
        else:
            out.append(w)
    for c in current:
        if id(c) in used:
            continue
        if c.get("key") and not _has_data(rows, c["name"]):
            continue  # an unwanted standard channel without readings
        out.append(c)
    return out


def build_log(settings: dict) -> MechanicalRunLog:
    """``pump.mechanical_run.MechanicalRunLog`` from the node settings."""
    cols = [c for c in settings.get("columns") or [] if str(c.get("name", "")).strip()]
    channels = tuple(
        Channel(
            str(c["name"]).strip(),
            c.get("role") or "other",
            str(c.get("location") or "").strip(),
        )
        for c in cols
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
    lube = settings.get("lubrication") or None
    return MechanicalRunLog(
        channels=channels,
        readings=tuple(readings),
        lubrication=lube if lube in LUBRICATION else None,
    )


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
    """The witness-sheet channels: flow, vibration (overall and filtered, both
    limited by API 610) and oil temperature (stabilisation).  Time is the row
    key.  More channels can be added in the dialog."""
    return [
        {
            "name": "Flow",
            "dimension": "capacity",
            "unit": units.PREFS.default_unit("capacity"),
            "role": "flow",
        },
        {
            "name": "Vib overall",
            "dimension": "vibration_velocity",
            "unit": "mm/s",
            "role": "vibration_unfiltered",
        },
        {
            "name": "Vib filtered",
            "dimension": "vibration_velocity",
            "unit": "mm/s",
            "role": "vibration_filtered",
        },
        {
            "name": "Oil temperature",
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
                "values": {
                    "Flow": 100.0,
                    "Vib overall": 1.5,
                    "Vib filtered": 1.0,
                    "Oil temperature": 50.0,
                },
            }
        )
    return rows


class MechanicalRunNode(BaseNode):
    kind = "mechanical_run"
    title = "MRT Log"
    glyph = "⟳"
    is_source = True
    # Optional: the rated point's pump type selects the vibration locations.
    inputs = [PortSpec("RatedPoint", "RatedPoint")]
    outputs = [PortSpec("MechanicalRunSet", "MechanicalRunSet")]

    def default_settings(self) -> Dict:
        return {
            "pump_tag": "B-0001",
            "columns": _default_columns(),
            "rows": _default_rows(),
        }

    def port_label(self, name: str) -> str:
        return {"MechanicalRunSet": "Log", "RatedPoint": "Rated"}.get(name, name)

    # -- payload -----------------------------------------------------------
    def compute(self, inputs) -> Dict[str, object]:
        s = self.settings
        rated = self.first(inputs, "RatedPoint") if inputs else None
        self._pump_type = getattr(rated, "pump_type", None) if rated else None
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
        hours = float(log.duration.to("h").magnitude)
        lube = LUBRICATION_LABELS.get(log.lubrication or "", "lubrication not stated")
        self.status = (
            f"{run_set.pump_tag} · {len(log.readings)} readings · {hours:.1f} h"
            f" · {lube.lower() if log.lubrication else lube}"
        )
        self.state = "ok"
        return {"MechanicalRunSet": run_set}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import (
            QHBoxLayout,
            QHeaderView,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        from . import ui

        s = self.settings
        s.setdefault("columns", _default_columns())
        s.setdefault("rows", [])
        cols: List[dict] = s["columns"]

        dlg = ui.PropertyDialog(
            parent,
            "MRT Log",
            "Time-stamped readings of the mechanical running test.  Wire it "
            "into an MRT Check for the verdict.",
            width=760,
            maximizable=True,
        )
        banner = ui.Banner()
        tag = ui.line_edit(s["pump_tag"], None, "physical unit TAG, e.g. P-9001A")

        col_table = QTableWidget(0, 4)
        col_table.setObjectName("RunColumns")
        col_table.setHorizontalHeaderLabels(["Name", "Dimension", "Role", "Location"])
        col_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        grid = QTableWidget(0, 1)
        grid.setObjectName("RunGrid")
        grid.verticalHeader().setVisible(True)
        grid.setMinimumHeight(380)
        grid.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # One unit combo above each channel column, as in Test Points: picking
        # another unit converts that column's readings.
        strip = ui.UnitHeaderStrip(grid)
        unit_headers: List[ui.UnitColumnHeader] = []

        def rebuild_unit_strip():
            for h in unit_headers:
                h.combo.setParent(None)
                h.combo.deleteLater()
            unit_headers.clear()
            for j, c in enumerate(cols):
                unit_headers.append(
                    ui.UnitColumnHeader(
                        grid,
                        1 + j,
                        c["dimension"],
                        c["unit"],
                        lambda _old, new, j=j: on_unit(j, new),
                        strip=strip,
                    )
                )
            strip.headers = list(unit_headers)
            QTimer.singleShot(0, strip.sync)

        def recompute():
            on_change()
            kind = {"ok": "ok", "reject": "error"}.get(self.state, "warn")
            banner.show_message(self.status, kind)

        # -- readings grid --------------------------------------------------
        def update_grid_headers():
            grid.setHorizontalHeaderLabels(
                ["Time"] + [f"{c['name']} [{c['unit']}]" for c in cols]
            )

        def fill_grid():
            grid.blockSignals(True)
            if grid.columnCount() != 1 + len(cols) or len(unit_headers) != len(cols):
                grid.setColumnCount(1 + len(cols))
                rebuild_unit_strip()
            else:
                for h, c in zip(unit_headers, cols):
                    if h.dimension != c["dimension"]:
                        rebuild_unit_strip()
                        break
                    h.set_unit(c["unit"], notify=False)
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
                role = ui.combo([(r, r) for r in ROLES], c["role"], None)
                dim.currentIndexChanged.connect(
                    lambda _=None, i=i, w=dim: on_dimension(i, w.currentData())
                )
                role.currentIndexChanged.connect(
                    lambda _=None, i=i, w=role: on_role(i, w.currentData())
                )
                col_table.setCellWidget(i, 1, dim)
                col_table.setCellWidget(i, 2, role)
                col_table.setItem(i, 3, QTableWidgetItem(str(c.get("location") or "")))
            col_table.blockSignals(False)

        def on_dimension(i, new):
            if not new or new == cols[i]["dimension"]:
                return
            cols[i]["dimension"] = new
            cols[i]["unit"] = units.PREFS.default_unit(new)
            rebuild_unit_strip()
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
            if item.column() == 3 and item.row() < len(cols):
                loc = item.text().strip()
                if loc:
                    cols[item.row()]["location"] = loc
                else:
                    cols[item.row()].pop("location", None)
                recompute()
                return
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

        def paste():
            new_rows = paste_rows(QGuiApplication.clipboard().text(), cols)
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

        tag.textChanged.connect(lambda v: (s.__setitem__("pump_tag", v), recompute()))

        # -- standard channels (lubrication system + groups) ------------------
        pump_type = getattr(self, "_pump_type", None)
        lube = ui.combo(
            [("Not stated", "")] + [(LUBRICATION_LABELS[k], k) for k in LUBRICATION],
            s.get("lubrication") or "",
            None,
        )
        group_boxes = {}
        groups_box = QWidget()
        gb = QVBoxLayout(groups_box)
        gb.setContentsMargins(0, 0, 0, 0)
        gb.setSpacing(2)
        for gid, label in CHANNEL_GROUPS:
            if gid == "vibration":
                label += f" ({pump_type or 'pump type not set: DE / NDE'})"
            box = ui.checkbox(label, gid in (s.get("channel_groups") or ()))
            group_boxes[gid] = box
            gb.addWidget(box)

        def on_standard(*_):
            value = lube.currentData() or ""
            if value:
                s["lubrication"] = value
            else:
                s.pop("lubrication", None)
            chosen = [g for g in _GROUP_IDS if group_boxes[g].isChecked()]
            if chosen:
                s["channel_groups"] = chosen
            else:
                s.pop("channel_groups", None)
            s["columns"] = apply_standard_channels(s, pump_type)
            cols[:] = s["columns"]
            s["columns"] = cols
            fill_cols()
            fill_grid()
            recompute()

        lube.currentIndexChanged.connect(on_standard)
        for box in group_boxes.values():
            box.toggled.connect(on_standard)

        # Readings first, units above each column (the Test Points layout);
        # the channel definitions (name, dimension, role) below.
        readings = QWidget()
        rl = QVBoxLayout(readings)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)
        rl.addWidget(strip)
        rl.addWidget(grid)

        dlg.add(ui.section("Pump identity"))
        dlg.add(ui.row("Pump TAG", tag))
        dlg.add(ui.hline())
        dlg.add(ui.section("Readings"))
        dlg.add(
            toolbar(
                [("＋ Add row", add_row), ("－ Remove", del_rows), ("⎘ Paste", paste)]
            )
        )
        dlg.add(readings)
        dlg.add(banner)
        dlg.add(ui.hline())
        dlg.add(ui.section("Standard channels (API 610)"))
        dlg.add(
            ui.Banner(
                "The lubrication system selects the temperature channels its "
                "bearing temperature rules need (API 610 8th 2.9.2.3, 11th "
                "6.10.2.4, 12th 6.10.2.7).  Readings already entered are kept.",
                "info",
            )
        )
        dlg.add(ui.row("Lubrication", lube))
        dlg.add(groups_box)
        dlg.add(ui.hline())
        dlg.add(ui.section("Channels (name, dimension, role, bearing location)"))
        dlg.add(toolbar([("＋ Channel", add_column), ("－ Channel", del_column)]))
        dlg.add(col_table)

        fill_cols()
        fill_grid()
        recompute()
        dlg.resize(980, 860)
        QTimer.singleShot(0, strip.sync)
        return dlg
