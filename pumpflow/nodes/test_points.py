"""
nodes.test_points — Test Points Table  (UI_SPEC §5.2)

Source node.  An editable, spreadsheet-like grid of raw measured rows for one
**physical pump** (the branch identity).  Emits a ``TestPointSet``.

- comma- or dot-decimals accepted (Excel-friendly paste)
- every column has its own display unit (combo above the column); the rows are
  stored in those units and converted only when the unit is changed
- read-only computed ``Head = ΔP/(ρ·g) [+ velocity + elevation]`` and ``η``
  columns, live (velocity/elevation only with the optional bench geometry)
- ≥ 3 points required for a degree-3 fit; warns if a shut-off point is missing
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pump import Q_, Pressure

from .. import explain, units
from ..binding import row_efficiency, row_head, row_head_components
from ..numfmt import fmt, parse_decimal
from ..persistence import testset_from_json, testset_pressure_unit
from ..sample_data import SINGLE_PUMP_JSON
from ..signals import BenchGeometry, TestPointSet, TestRow
from .base import BaseNode, PortSpec
from .fluidpick import choice_options, current_choice, resolve_fluid
from pump.vibration import ALL_VIBRATION_KEYS, location_of_key, vibration_keys

_NAMES = ["Q", "P_suc", "P_dis", "T_water", "N", "P", "Head", "η"]
_ALL_KEYS = ["q", "p_suc", "p_dis", "temp_c", "n", "power", "head", "eff"]
_KEYS = _ALL_KEYS[:6]  # hydraulic input columns (also the header-less paste order)
_EDITABLE = {0, 1, 2, 3, 4, 5}
# Optional vibration columns (bearing-housing velocity, RMS): one overall and
# one filtered column per API 610 measurement location of the pump type.
_VIB_KEYS = list(ALL_VIBRATION_KEYS)


def vibration_columns(pump_type: Optional[str], rows=()) -> List[str]:
    """Vibration column keys to show: the pump type's locations, plus any
    location that already holds data (so nothing entered is ever hidden)."""
    keys = vibration_keys(pump_type)
    for k in _VIB_KEYS:
        if k not in keys and any(r.get(k) is not None for r in rows):
            keys.append(k)
    return keys


def vibration_column_title(key: str) -> str:
    """'Gearbox overall', 'DE filt.', ..."""
    loc, filtered = location_of_key(key)
    return f"{loc.short} {'filt.' if filtered else 'overall'}"
_PRESSURE_KEYS = ("p_suc", "p_dis")
_DEFAULT_LABEL = "Water at T_water"

# Optional bench geometry (runtime settings keys; value None = unset).
_GEO_KEYS = ("suction_id", "discharge_id", "suction_z", "discharge_z")
_GEO_ID_KEYS = ("suction_id", "discharge_id")


def default_geometry_settings(prefs=None) -> Dict:
    """Runtime defaults of the geometry keys: values unset, units from the preset."""
    prefs = prefs if prefs is not None else units.PREFS
    out: Dict = {}
    for k in _GEO_KEYS:
        out[k] = None
        out[f"{k}_unit"] = prefs.default_unit("length") if k in _GEO_ID_KEYS else "m"
    return out


def _geo_quantity(s: dict, key: str) -> Optional[Q_]:
    """One geometry setting as a length Quantity (``None`` when unset).

    A non-positive pipe ID counts as "not entered" (it would divide by zero);
    a zero elevation is a legitimate value.
    """
    v = s.get(key)
    if v is None:
        return None
    v = float(v)
    if key in _GEO_ID_KEYS and v <= 0:
        return None
    label = s.get(f"{key}_unit") or default_geometry_settings()[f"{key}_unit"]
    return Q_(v, units.pint_str("length", label))


def geometry_from_settings(s: dict) -> Optional[BenchGeometry]:
    """``BenchGeometry`` from node settings, or ``None`` when nothing is set."""
    geom = BenchGeometry(
        suction_id=_geo_quantity(s, "suction_id"),
        discharge_id=_geo_quantity(s, "discharge_id"),
        suction_elevation=_geo_quantity(s, "suction_z"),
        discharge_elevation=_geo_quantity(s, "discharge_z"),
    )
    return None if geom.is_empty else geom


def canonical_columns(pressure_label: str = "bar") -> Dict[str, str]:
    """Exchange/canonical column units: m³/h · pressure · °C · rpm · kW · m · %."""
    cols = {
        k: units.canonical_unit(dim) for k, dim in units.ALL_COLUMN_DIMENSIONS.items()
    }
    cols["p_suc"] = cols["p_dis"] = pressure_label
    for k in _VIB_KEYS:  # vibration is exchanged in mm/s (RMS)
        cols[k] = "mm/s"
    return cols


def default_columns(prefs=None) -> Dict[str, str]:
    """Column units of a fresh table: the active preset's display units."""
    prefs = prefs if prefs is not None else units.PREFS
    return {k: prefs.default_unit(dim) for k, dim in units.ALL_COLUMN_DIMENSIONS.items()}


def _pint_of(columns: dict, key: str) -> str:
    dim = units.ALL_COLUMN_DIMENSIONS[key]
    return units.pint_str(dim, columns.get(key) or units.canonical_unit(dim))


def _row_from_dict(r: dict, columns: dict, pressure_ref: str = "g") -> TestRow:
    """Wrap one settings row (plain numbers in the column units) into a ``TestRow``.

    Blank cells become 0.0 (temperature: 25 °C converted to the column unit),
    exactly as before.  ``head`` / ``eff`` overrides stay ``None`` when blank.
    """
    cols = {**canonical_columns(), **(columns or {})}

    def num(key: str, default: float = 0.0) -> float:
        v = r.get(key)
        return default if v is None else float(v)

    if cols["temp_c"] == "°C":
        t_default = 25.0
    else:
        t_default = Q_(25.0, "degC").to(_pint_of(cols, "temp_c")).magnitude

    head = r.get("head")
    eff = r.get("eff")
    return TestRow(
        q=Q_(num("q"), _pint_of(cols, "q")),
        p_suction=Pressure(Q_(num("p_suc"), _pint_of(cols, "p_suc")), pressure_ref),
        p_discharge=Pressure(Q_(num("p_dis"), _pint_of(cols, "p_dis")), pressure_ref),
        temperature=Q_(num("temp_c", t_default), _pint_of(cols, "temp_c")),
        speed=Q_(num("n"), _pint_of(cols, "n")),
        power=Q_(num("power"), _pint_of(cols, "power")),
        head=None if head is None else Q_(float(head), _pint_of(cols, "head")),
        efficiency=None if eff is None else Q_(float(eff), _pint_of(cols, "eff")),
        vibration={
            k: Q_(float(r[k]), _pint_of(cols, k))
            for k in _VIB_KEYS
            if r.get(k) is not None
        },
    )


def testset_settings(tps: TestPointSet, columns: Optional[dict] = None) -> dict:
    """Flatten a ``TestPointSet`` to the node-settings ``columns`` / ``rows`` shape.

    Without ``columns`` the exchange-canonical units are used (m³/h, the set's
    bar / kgf/cm² pressure unit, °C, rpm, kW, m, %) so values are untouched.
    With ``columns`` (display labels) every value is converted into them.

    Returns ``{"columns", "pressure_ref", "rows"}``.
    """
    pu = testset_pressure_unit(tps)  # "bar" | "kgf/cm**2"
    base = canonical_columns(units.label_for("pressure", pu) or "bar")
    ref = tps.rows[0].p_suction.reference if tps.rows else "g"

    def p_mag(p: Pressure) -> float:
        q = p.gauge() if ref == "g" else p.absolute()
        return q.to(pu).magnitude

    rows = []
    for r in tps.rows:
        rows.append(
            {
                "q": r.q.to("m**3/h").magnitude,
                "p_suc": p_mag(r.p_suction),
                "p_dis": p_mag(r.p_discharge),
                "temp_c": r.temperature.to("degC").magnitude,
                "n": r.speed.to("rpm").magnitude,
                "power": r.power.to("kW").magnitude,
                "head": None if r.head is None else r.head.to("m").magnitude,
                "eff": None
                if r.efficiency is None
                else r.efficiency.to("percent").magnitude,
                **{
                    k: v.to("mm/s").magnitude
                    for k, v in (getattr(r, "vibration", None) or {}).items()
                },
            }
        )
    target = dict(base)
    if columns:
        target.update(columns)
        for key, dim in units.ALL_COLUMN_DIMENSIONS.items():
            if target.get(key, base[key]) == base[key]:
                continue
            for row in rows:
                if row.get(key) is not None:
                    row[key] = units.convert_display(
                        row[key], dim, base[key], target[key]
                    )
    return {"columns": target, "pressure_ref": ref, "rows": rows}


def parse_paste_header(cells: List[str]):
    """Parse the first pasted line as unit headers.

    Returns ``[(key, label, ref), ...]`` when **every** cell parses as a known
    column header (unique keys), else ``None`` (the line is data).
    """
    if not cells or any(not c.strip() for c in cells):
        return None
    parsed = []
    for c in cells:
        try:
            parsed.append(units.parse_unit_header(c))
        except ValueError:
            return None
    keys = [p[0] for p in parsed]
    if len(set(keys)) != len(keys):
        return None
    return parsed


class TestPointsTableNode(BaseNode):
    kind = "test_points"
    title = "Test Points Table"
    glyph = "▦"
    is_source = True
    # Optional Fluid input (multi): wired Fluid nodes set the TEST fluid density,
    # used to derive Head/η instead of per-row water at T_water (UC-00).  A
    # "Fluid source" picker chooses water-at-T_water or one of the wired fluids.
    # Optional RatedPoint: its API 610 pump type selects the vibration columns.
    inputs = [
        PortSpec("FluidSpec", "FluidSpec", multi=True),
        PortSpec("RatedPoint", "RatedPoint"),
    ]
    outputs = [PortSpec("TestPointSet", "TestPointSet")]

    def default_settings(self) -> Dict:
        tps = testset_from_json(SINGLE_PUMP_JSON)
        shape = testset_settings(tps, default_columns())
        return {
            "pump_tag": tps.pump_tag,
            "fluid_choice": "",  # ""=first wired (default), "__default__"=water, or a name
            "columns": shape["columns"],
            "pressure_ref": shape["pressure_ref"],
            "rows": shape["rows"],
            **default_geometry_settings(),
        }

    # -- payload -----------------------------------------------------------
    def geometry(self) -> Optional[BenchGeometry]:
        """The optional bench geometry from the current settings (or ``None``)."""
        return geometry_from_settings(self.settings)

    def to_signal(self, test_density=None) -> TestPointSet:
        s = self.settings
        columns = s.get("columns") or canonical_columns()
        ref = s.get("pressure_ref", "g")
        rows = [_row_from_dict(r, columns, ref) for r in s["rows"]]
        return TestPointSet(
            pump_tag=str(s["pump_tag"]).strip(),
            rows=tuple(rows),
            test_density=test_density,
            geometry=self.geometry(),
        )

    def compute(self, inputs) -> Dict[str, object]:
        rated = self.first(inputs, "RatedPoint")
        self._pump_type = getattr(rated, "pump_type", None) if rated else None
        self._fluids = self.all_of(inputs, "FluidSpec")
        chosen = resolve_fluid(self._fluids, self.settings.get("fluid_choice"))
        self._test_density = chosen.density if chosen is not None else None
        tps = self.to_signal(self._test_density)
        ok, msg = tps.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        shutoff = "" if tps.has_shutoff() else " · no shut-off pt"
        fl = (
            f" · {chosen.name} {self._test_density.to('kg/m**3').magnitude:.0f} kg/m³"
            if chosen
            else ""
        )
        self.status = f"{tps.pump_tag} · {len(tps.rows)} points{shutoff}{fl}"
        self.state = "ok"
        return {"TestPointSet": tps}

    def port_label(self, name: str) -> str:
        return {"FluidSpec": "Fluid", "RatedPoint": "Rated"}.get(name, "TestPoints")

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
        s["columns"] = {**canonical_columns(), **(s.get("columns") or {})}
        s.setdefault("pressure_ref", "g")
        for k, v in default_geometry_settings().items():
            s.setdefault(k, v)
        cols = s["columns"]
        pump_type = getattr(self, "_pump_type", None)
        vib_keys = vibration_columns(pump_type, s["rows"])
        for k in vib_keys:  # runtime labels for the shown vibration columns
            cols.setdefault(k, units.PREFS.default_unit("vibration_velocity"))
        dims = units.ALL_COLUMN_DIMENSIONS
        # Table columns: hydraulic + head/eff + this pump type's vibration.
        col_keys_all = _ALL_KEYS + vib_keys
        names = _NAMES + [vibration_column_title(k) for k in vib_keys]
        vib_cols = range(len(_ALL_KEYS), len(col_keys_all))
        editable = set(_EDITABLE) | set(vib_cols)

        dlg = ui.PropertyDialog(
            parent,
            "Test Points Table",
            "Raw measured rows for one physical pump. Head and η are computed live.",
            width=720,
            maximizable=True,
        )
        banner = ui.Banner()

        tag = ui.line_edit(s["pump_tag"], None, "physical unit TAG, e.g. B-2351105A")
        ref_combo = ui.combo(
            [("g (gauge)", "g"), ("a (absolute)", "a")], s["pressure_ref"], None
        )
        ref_combo.setObjectName("PressureRef")

        fluids = getattr(self, "_fluids", [])
        fluid_pick = ui.combo(
            choice_options(fluids, _DEFAULT_LABEL),
            current_choice(fluids, s.get("fluid_choice")),
            None,
        )

        table = QTableWidget(len(s["rows"]), len(names))
        table.verticalHeader().setVisible(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setObjectName("TestGrid")

        def header_text(i: int) -> str:
            key = col_keys_all[i]
            lab = cols[key]
            if key in _PRESSURE_KEYS:
                lab = f"{lab} {s['pressure_ref']}"
            return f"{names[i]} [{lab}]"

        def update_headers():
            table.setHorizontalHeaderLabels([header_text(i) for i in range(len(names))])
            for c in vib_cols:  # where API 610 measures, for this pump type
                item = table.horizontalHeaderItem(c)
                if item is not None:
                    loc, filt = location_of_key(col_keys_all[c])
                    item.setToolTip(
                        f"{loc.label}: {'filtered (largest discrete frequency)' if filt else 'overall'}"
                        f" bearing-housing velocity, RMS. {loc.where}"
                    )
            head_item = table.horizontalHeaderItem(_NAMES.index("Head"))
            if head_item is not None:  # formula tooltip (UC-10)
                head_item.setToolTip(explain.tooltip("head"))

        update_headers()

        def recompute_status():
            ok, msg = self.to_signal().is_valid()
            test_rho = getattr(self, "_test_density", None)
            if ok and test_rho is not None:
                banner.show_message(
                    f"Test fluid overridden by connected Fluid node "
                    f"({test_rho.to('kg/m**3').magnitude:.0f} kg/m³) — Head/η use it; "
                    f"T_water is informational.",
                    "info",
                )
            elif ok and not self.to_signal().has_shutoff():
                banner.show_message(
                    "OK — but no shut-off point (Q≈0). Shut-off head check will extrapolate.",
                    "warn",
                )
            else:
                banner.show_message("" if ok else msg, "info" if ok else "error")
            on_change()

        def refresh_computed(row_idx: int):
            r = s["rows"][row_idx]
            tr = _row_from_dict(r, cols, s["pressure_ref"])
            test_rho = getattr(self, "_test_density", None)
            geom = geometry_from_settings(s)
            tip = ""
            try:
                head_q = row_head(tr, test_rho, geom)
                eff_q = row_efficiency(tr, head_q, test_rho)
                head = head_q.to(_pint_of(cols, "head")).magnitude
                eff = (
                    None if eff_q is None else eff_q.to(_pint_of(cols, "eff")).magnitude
                )
                if geom is not None:
                    comps = row_head_components(tr, test_rho, geom)
                    hp = _pint_of(cols, "head")
                    v = {k: c.to(hp).magnitude for k, c in comps.items()}
                    tip = (
                        f"pressure {v['pressure']:.3f} + velocity {v['velocity']:.3f}"
                        f" + elevation {v['elevation']:.3f} = {v['total']:.3f}"
                        f" {cols['head']}"
                    )
            except Exception:
                head, eff = 0.0, None
            _set_ro(table, row_idx, 6, fmt(head, 2), tip)
            _set_ro(table, row_idx, 7, fmt(eff, 1) if eff is not None else "—")

        def fill():
            table.blockSignals(True)
            table.setRowCount(len(s["rows"]))
            for i, r in enumerate(s["rows"]):
                for c in sorted(editable):
                    key = col_keys_all[c]
                    val = r.get(key)
                    item = QTableWidgetItem("" if val is None else f"{float(val):g}")
                    table.setItem(i, c, item)
                refresh_computed(i)
            table.blockSignals(False)

        def on_cell_changed(item):
            row, col = item.row(), item.column()
            if col not in editable or row >= len(s["rows"]):
                return
            val = parse_decimal(item.text(), None)
            s["rows"][row][col_keys_all[col]] = val
            table.blockSignals(True)
            item.setText("" if val is None else f"{val:g}")
            refresh_computed(row)
            table.blockSignals(False)
            recompute_status()

        # -- unit headers (one combo per column; one shared by both pressures)
        strip = ui.UnitHeaderStrip(table)
        headers: Dict[str, ui.UnitColumnHeader] = {}

        def on_col_unit(keys):
            def handler(old: str, new: str):
                for k in keys:
                    for r in s["rows"]:
                        if r.get(k) is not None:
                            r[k] = units.convert_display(r[k], dims[k], old, new)
                    cols[k] = new
                update_headers()
                fill()
                recompute_status()

            return handler

        for i, key in enumerate(col_keys_all):
            if key == "p_dis":
                continue
            keys = _PRESSURE_KEYS if key == "p_suc" else (key,)
            headers[key] = ui.UnitColumnHeader(
                table,
                i,
                dims[key],
                cols[key],
                on_col_unit(keys),
                span=len(keys),
                strip=strip,
            )
        strip.headers = list(headers.values())

        def on_ref_changed(_=None):
            new = ref_combo.currentData()
            old = s["pressure_ref"]
            if new == old:
                return
            atm = units.atm_in(cols["p_suc"])
            delta = atm if new == "a" else -atm
            for r in s["rows"]:
                for k in _PRESSURE_KEYS:
                    if r.get(k) is not None:
                        r[k] = r[k] + delta
            s["pressure_ref"] = new
            update_headers()
            fill()
            recompute_status()

        table.itemChanged.connect(on_cell_changed)
        tag.textChanged.connect(
            lambda v: (s.__setitem__("pump_tag", v), recompute_status())
        )
        ref_combo.currentIndexChanged.connect(on_ref_changed)

        def on_pick():
            s["fluid_choice"] = fluid_pick.currentData()
            chosen = resolve_fluid(getattr(self, "_fluids", []), s["fluid_choice"])
            self._test_density = chosen.density if chosen is not None else None
            fill()  # re-derive Head/η with the new density
            recompute_status()

        fluid_pick.currentIndexChanged.connect(lambda _=None: on_pick())

        # -- optional bench geometry: one checkbox gates four length fields
        geo_labels = {
            "suction_id": "Suction pipe ID",
            "discharge_id": "Discharge pipe ID",
            "suction_z": "Suction gauge elevation z_s",
            "discharge_z": "Discharge gauge elevation z_d",
        }
        geo_fields: Dict[str, ui.UnitField] = {}
        geo_rows: Dict[str, QWidget] = {}

        def on_geo_change():
            applied = geo_chk.isChecked()
            for k, f in geo_fields.items():
                s[f"{k}_unit"] = f.unit_label()
                s[k] = f.magnitude() if applied else None
                f.spin.setEnabled(applied)
                f.combo.setEnabled(applied)
                if k in geo_rows:  # the label greys out with its field
                    geo_rows[k].setEnabled(applied)
            fill()  # Head column (and tooltips) re-derive with the geometry
            recompute_status()

        geo_chk = ui.checkbox(
            "Apply bench geometry",
            any(s.get(k) is not None for k in _GEO_KEYS),
            lambda: on_geo_change(),
        )
        geo_chk.setObjectName("ApplyGeometry")
        for k in _GEO_KEYS:
            is_id = k in _GEO_ID_KEYS
            f = ui.UnitField(
                "length",
                s[k] if s.get(k) is not None else 0.0,
                s.get(f"{k}_unit"),
                on_change=lambda: on_geo_change(),
                lo=0.0 if is_id else -1.0e4,
                hi=1.0e5,
                step=1.0 if is_id else 0.1,
                decimals=3,
            )
            f.spin.setObjectName(f"Geo_{k}")
            f.spin.setEnabled(geo_chk.isChecked())
            f.combo.setEnabled(geo_chk.isChecked())
            geo_fields[k] = f

        # -- optional vibration columns (RMS), hidden unless wanted / present
        def has_vibration() -> bool:
            return any(r.get(k) is not None for r in s["rows"] for k in _VIB_KEYS)

        from pump.vibration import locations_for

        where = ", ".join(loc.label for loc in locations_for(pump_type))
        vib_chk = ui.checkbox(
            f"Vibration columns (RMS, overall / filtered) · {pump_type or 'pump type not set'}"
            f": {where}",
            has_vibration(),
        )
        vib_chk.setObjectName("ShowVibration")
        vib_chk.setToolTip(
            "Record vibration at each test point for the test data summary "
            "(API 610 Annex M / 8th App. T): rated flow, preferred and allowable "
            "operating regions. Values must be RMS."
        )

        def show_vibration(on: bool) -> None:
            for c in vib_cols:
                table.setColumnHidden(c, not on)
            strip.sync()

        vib_chk.toggled.connect(show_vibration)

        # toolbar
        def blank_row() -> dict:
            # hydraulic keys only: vibration keys appear when a value is typed
            return {k: None for k in _ALL_KEYS[:8]}

        def add_row():
            s["rows"].append(blank_row())
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

        def sync_header_widgets():
            for key, h in headers.items():
                h.set_unit(cols[key], notify=False)
            ref_combo.blockSignals(True)
            idx = ref_combo.findData(s["pressure_ref"])
            if idx >= 0:
                ref_combo.setCurrentIndex(idx)
            ref_combo.blockSignals(False)

        def paste():
            text = QGuiApplication.clipboard().text()
            if not text.strip():
                return
            lines = [ln for ln in text.splitlines() if ln.strip()]

            def split(line: str) -> List[str]:
                return line.replace(";", "\t").split("\t")

            hdr = parse_paste_header(split(lines[0]))
            hdr_labels: Dict[str, str] = {}
            if hdr:
                col_keys = [h[0] for h in hdr]
                data_lines = lines[1:]
                for key, label, ref in hdr:
                    if label is not None:
                        hdr_labels[key] = label
                    if ref is not None:
                        s["pressure_ref"] = ref
                # Pressures share one unit: the first labelled pressure header wins.
                p_target = next(
                    (hdr_labels[k] for k in col_keys if k in _PRESSURE_KEYS and k in hdr_labels),
                    cols["p_suc"],
                )
                for key, label in hdr_labels.items():
                    cols[key] = p_target if key in _PRESSURE_KEYS else label
                if any(k in _PRESSURE_KEYS for k in col_keys):
                    cols["p_suc"] = cols["p_dis"] = p_target
            else:
                col_keys = list(_KEYS)
                data_lines = lines
                p_target = cols["p_suc"]

            new_rows = []
            for line in data_lines:
                cells = split(line)
                rd = blank_row()
                for c, key in enumerate(col_keys):
                    if c < len(cells):
                        v = parse_decimal(cells[c], None)
                        if (
                            v is not None
                            and key in _PRESSURE_KEYS
                            and key in hdr_labels
                            and hdr_labels[key] != p_target
                        ):
                            v = units.convert_display(
                                v, "pressure", hdr_labels[key], p_target
                            )
                        rd[key] = v
                new_rows.append(rd)
            if new_rows:
                s["rows"] = new_rows
                if any(k in _VIB_KEYS for k in col_keys):
                    vib_chk.setChecked(True)
                hidden = [
                    k for k in col_keys if k in _VIB_KEYS and k not in col_keys_all
                ]
                if hidden:
                    banner.show_message(
                        "Pasted vibration for locations of another pump type "
                        f"({', '.join(hidden)}): kept in the data; reopen the "
                        "table to see their columns.",
                        "warn",
                    )
                sync_header_widgets()
                update_headers()
                fill()
                recompute_status()

        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)
        for label, fn in [
            ("＋ Add row", add_row),
            ("－ Remove", del_rows),
            ("↑ Up", lambda: move(-1)),
            ("↓ Down", lambda: move(1)),
            ("⎘ Paste", paste),
        ]:
            b = QPushButton(label)
            b.setObjectName("ToolButton")
            b.clicked.connect(fn)
            bl.addWidget(b)
        bl.addStretch(1)

        grid = QWidget()
        gl = QVBoxLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(2)
        gl.addWidget(strip)
        gl.addWidget(table)

        dlg.add(ui.section("Pump identity"))
        dlg.add(ui.row("Pump TAG", tag))
        dlg.add(ui.row("Pressure reference", ref_combo))
        if fluids:
            dlg.add(ui.row("Fluid source", fluid_pick))
        dlg.add(ui.hline())
        dlg.add(ui.section("Test bench geometry (optional)"))
        dlg.add(geo_chk)
        for k in _GEO_KEYS:
            geo_rows[k] = geo_fields[k].row(geo_labels[k])
            geo_rows[k].setEnabled(geo_chk.isChecked())
            dlg.add(geo_rows[k])
        dlg.add(ui.hline())
        dlg.add(ui.section("Measured points"))
        dlg.add(vib_chk)
        dlg.add(bar)
        dlg.add(grid)
        dlg.add(banner)
        fill()
        recompute_status()
        show_vibration(vib_chk.isChecked())
        dlg.resize(980 if vib_chk.isChecked() else 760, 700)
        QTimer.singleShot(0, strip.sync)
        return dlg


def _set_ro(
    table, row: int, col: int, text: str, tooltip: str = ""
) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTableWidgetItem

    from ..style import qcolor

    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemIsEnabled)
    item.setForeground(qcolor("table-computed-text"))
    item.setBackground(qcolor("table-computed-bg"))
    if tooltip:
        item.setToolTip(tooltip)
    table.setItem(row, col, item)
