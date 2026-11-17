"""
nodes.npsh — NPSH margin  (sprint 8 / UC-05)

Source node.  NPSHr test points (Q / NPSHr, per-column units) for one physical
pump, judged against the available NPSH at the rated capacity.  Optional
``RatedPoint`` input (rated Q, rated NPSHa, acceptance criteria selection).
Emits an ``NPSHResult`` (:class:`~pumpflow.signals.NPSHResultSignal`) that
connects to Report Export's multi ``branch`` input.

Two NPSHa sources (the ``mode`` setting):

- ``"points"``     — "Direct NPSHr points": NPSHa is typed in the node (optional)
  or taken from the rated point.
- ``"calculator"`` — "NPSHa calculator": computed from the suction pressure
  (g/a), water temperature, suction ID and elevation at the rated Q, through
  ``binding.npsha_from_suction`` (no physics in this module).

The 3 % head-drop sweep (``pump.npsh.npsh3_from_sweep``) is library-only for
now; it has no GUI mode yet.

Runtime settings::

    {"pump_tag": str, "mode": "points" | "calculator", "degree": int,
     "columns": {"q": <capacity label>, "npshr": <npsh label>},
     "rows": [{"q": float | None, "npshr": float | None}, ...],
     "npsha": float | None, "npsha_unit": <npsh label>,
     "calc_p": float, "calc_p_unit": <pressure label>, "calc_p_ref": "g" | "a",
     "calc_temp": float, "calc_temp_unit": <temperature label>,
     "calc_id": float | None, "calc_id_unit": <length label>,
     "calc_z": float, "calc_z_unit": <length label>,
     "overrides": {"min_ratio": float | None,
                   "min_margin": None | {"value", "unit"}}}
"""

from __future__ import annotations

import copy
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pump import Pressure, Q_

from .. import explain, units
from ..binding import check_npsh_set, npsha_from_suction
from ..numfmt import parse_decimal
from ..signals import NPSHSet
from .base import BaseNode, PortSpec
from . import ui

_MODES = [("Direct NPSHr points", "points"), ("NPSHa calculator", "calculator")]


# ---------------------------------------------------------------------------
# Qt-free helpers
# ---------------------------------------------------------------------------


def _blank_rows(n: int = 5) -> list:
    return [{"q": None, "npshr": None} for _ in range(n)]


def points_from_settings(s: dict) -> tuple:
    """``((Q_capacity, Q_npshr), ...)`` of the rows that have both values."""
    cols = s.get("columns") or {}
    q_pint = units.pint_str("capacity", cols.get("q", "m³/h"))
    n_pint = units.pint_str("npsh", cols.get("npshr", "m"))
    pts = []
    for r in s.get("rows") or []:
        q, n = r.get("q"), r.get("npshr")
        if q is None or n is None:
            continue
        pts.append((Q_(float(q), q_pint), Q_(float(n), n_pint)))
    return tuple(pts)


def overrides_to_quantities(ov: Optional[dict]) -> dict:
    """Runtime override dict (display labels) -> values for the binding."""
    out: dict = {"min_ratio": None, "min_margin": None}
    if not ov:
        return out
    if ov.get("min_ratio") is not None:
        out["min_ratio"] = float(ov["min_ratio"])
    mm = ov.get("min_margin")
    if isinstance(mm, dict) and mm.get("value") is not None:
        out["min_margin"] = Q_(float(mm["value"]), units.pint_str("npsh", mm["unit"]))
    return out


def calc_npsha(s: dict, q: Q_) -> Q_:
    """NPSHa from the calculator settings at capacity ``q`` (via the binding)."""
    p_pint = units.pint_str("pressure", s.get("calc_p_unit", "bar"))
    p = Pressure(Q_(float(s.get("calc_p", 0.0)), p_pint), s.get("calc_p_ref", "g"))
    t_pint = units.pint_str("temperature", s.get("calc_temp_unit", "°C"))
    temperature = Q_(float(s.get("calc_temp", 20.0)), t_pint)
    suction_id = None
    if s.get("calc_id") is not None:
        suction_id = Q_(
            float(s["calc_id"]), units.pint_str("length", s.get("calc_id_unit", "mm"))
        )
    z = Q_(
        float(s.get("calc_z") or 0.0),
        units.pint_str("length", s.get("calc_z_unit", "m")),
    )
    return npsha_from_suction(p, temperature, q, suction_id=suction_id, z_suction=z)


def verdict_label(result) -> str:
    """Status verdict; ``not configured`` when no rule exists, provisional when
    the rule is not verified."""
    status = getattr(result, "status", "info")
    if status == "info":
        return "not configured"
    text = "PASSED" if status == "pass" else "FAILED"
    if not getattr(result, "verified", True):
        text += " (unverified criteria)"
    return text


def _m(q) -> float:
    return float(q.to("m").magnitude)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


class NPSHNode(BaseNode):
    kind = "npsh"
    title = "NPSH"
    glyph = "◔"
    is_source = True
    inputs = [PortSpec("RatedPoint", "RatedPoint")]
    outputs = [PortSpec("NPSHResult", "NPSHResult")]

    def default_settings(self) -> Dict:
        return {
            "pump_tag": "B-0001",
            "mode": "points",
            "degree": 2,
            "columns": {"q": "m³/h", "npshr": "m"},
            "rows": _blank_rows(),
            "npsha": None,
            "npsha_unit": "m",
            "calc_p": 1.2,
            "calc_p_unit": "bar",
            "calc_p_ref": "a",
            "calc_temp": 20.0,
            "calc_temp_unit": "°C",
            "calc_id": None,
            "calc_id_unit": "mm",
            "calc_z": 0.0,
            "calc_z_unit": "m",
            "overrides": {"min_ratio": None, "min_margin": None},
        }

    def port_label(self, name: str) -> str:
        return {"RatedPoint": "Rated", "NPSHResult": "Result"}.get(name, name)

    # -- payload -----------------------------------------------------------
    def compute(self, inputs) -> Dict[str, object]:
        s = self.settings
        self._signal = None
        self._result = None
        self._calc_npsha = None
        self._calc_error = ""
        self._rated = self.first(inputs, "RatedPoint")
        rated = self._rated
        tag = str(s.get("pump_tag", "")).strip()
        try:
            pts = points_from_settings(s)
        except Exception as exc:
            return self.emit_nothing(f"{type(exc).__name__}: {exc}", "invalid")
        # A blank sheet (template filled in on test day) is not a verdict.
        if len(pts) < 2:
            return self.emit_nothing("Enter ≥ 2 NPSHr points (Q, NPSHr)", "invalid")
        if not tag:
            return self.emit_nothing("A pump TAG is required", "invalid")

        mode = s.get("mode", "points")
        try:
            npsha = None
            if mode == "calculator":
                if rated is None:
                    self._calc_error = "The NPSHa calculator needs the Rated Point (Q)"
                    return self.emit_nothing(self._calc_error, "invalid")
                npsha = calc_npsha(s, rated.q)
                self._calc_npsha = npsha
            elif s.get("npsha") is not None:
                npsha = Q_(
                    float(s["npsha"]), units.pint_str("npsh", s.get("npsha_unit", "m"))
                )
            quoted = None
            if s.get("npshr_quoted") is not None:
                quoted = Q_(
                    float(s["npshr_quoted"]),
                    units.pint_str("npsh", s.get("npshr_quoted_unit", "m")),
                )
            npsh_set = NPSHSet(
                pump_tag=tag,
                points=pts,
                npsha=npsha,
                mode=mode,
                degree=int(s.get("degree", 2)),
                npshr_quoted=quoted,
            )
            sig = check_npsh_set(
                npsh_set, rated, overrides_to_quantities(s.get("overrides"))
            )
        except Exception as exc:
            self._calc_error = f"{type(exc).__name__}: {exc}"
            return self.emit_nothing(self._calc_error, "invalid")

        self._signal = sig
        self._result = sig.result
        res = sig.result
        extrap = ""
        try:
            if rated is not None and sig.curve.extrapolated(rated.q):
                extrap = " · extrapolated"
        except Exception:
            pass
        where = "rated" if rated is not None else "max Q"
        self.status = (
            f"{tag} · NPSHr {_m(res.npshr):.2f} m @ {where} · "
            f"NPSHa {_m(res.npsha):.2f} m · ratio {float(res.ratio):.2f} · "
            f"{verdict_label(res)}{extrap}"
        )
        st = getattr(res, "status", "info")
        self.state = {"pass": "ok", "fail": "reject"}.get(st, "idle")
        return {"NPSHResult": sig}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        for k, v in self.default_settings().items():
            s.setdefault(k, copy.deepcopy(v))
        cols = s["columns"]
        cols.setdefault("q", "m³/h")
        cols.setdefault("npshr", "m")
        ov = s["overrides"]
        ov.setdefault("min_ratio", None)
        ov.setdefault("min_margin", None)
        rows = s["rows"]

        dlg = ui.PropertyDialog(
            parent,
            "NPSH",
            "NPSHr test points and the NPSHa they are judged against at the "
            "rated capacity.",
            width=640,
        )
        banner = ui.Banner()
        tag = ui.line_edit(s["pump_tag"], None, "physical unit TAG, e.g. B-34004A")
        mode = ui.combo(_MODES, s.get("mode", "points"), None)
        degree = ui.int_spin(s.get("degree", 2), 1, 5, None)

        # -- NPSHr points table ---------------------------------------------
        table = QTableWidget(0, 2)
        table.setObjectName("NPSHTable")
        from PySide6.QtWidgets import QHeaderView

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        q_unit = ui.combo(units.options_for("capacity"), cols["q"], None)
        n_unit = ui.combo(units.options_for("npsh"), cols["npshr"], None)

        def headers():
            table.setHorizontalHeaderLabels(
                [f"Q [{cols['q']}]", f"NPSHr [{cols['npshr']}]"]
            )

        def fill_table():
            table.blockSignals(True)
            headers()
            table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                for j, key in enumerate(("q", "npshr")):
                    v = r.get(key)
                    table.setItem(
                        i, j, QTableWidgetItem("" if v is None else f"{float(v):g}")
                    )
            table.blockSignals(False)

        def on_cell(item):
            i, j = item.row(), item.column()
            if i >= len(rows):
                return
            val = parse_decimal(item.text(), None)
            rows[i][("q", "npshr")[j]] = val
            table.blockSignals(True)
            item.setText("" if val is None else f"{val:g}")
            table.blockSignals(False)
            recompute()

        table.itemChanged.connect(on_cell)

        def on_col_unit(key, dim, combo):
            def handler(_=None):
                new = combo.currentData()
                old = cols[key]
                if not new or new == old:
                    return
                for r in rows:
                    if r.get(key) is not None:
                        r[key] = units.convert_display(r[key], dim, old, new)
                cols[key] = new
                fill_table()
                recompute()

            combo.currentIndexChanged.connect(handler)

        on_col_unit("q", "capacity", q_unit)
        on_col_unit("npshr", "npsh", n_unit)

        def add_row():
            rows.append({"q": None, "npshr": None})
            fill_table()
            recompute()

        def del_rows():
            idx = sorted({i.row() for i in table.selectedItems()}, reverse=True)
            for i in idx:
                if 0 <= i < len(rows):
                    del rows[i]
            fill_table()
            recompute()

        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)
        for label, fn in (("＋ Add row", add_row), ("－ Remove", del_rows)):
            b = QPushButton(label)
            b.setObjectName("ToolButton")
            b.clicked.connect(lambda _=False, fn=fn: fn())
            bl.addWidget(b)
        bl.addStretch(1)

        # -- NPSHa: direct entry --------------------------------------------
        npsha_chk = ui.checkbox(
            "Enter NPSHa here (else the rated point's)", s.get("npsha") is not None
        )
        npsha_f = ui.UnitField(
            "npsh",
            s["npsha"] if s.get("npsha") is not None else 0.0,
            s.get("npsha_unit"),
            on_change=lambda: sync(),
            lo=0.0,
            hi=1e6,
            step=0.1,
            decimals=3,
        )
        npsha_f.spin.setToolTip(explain.tooltip("npsha"))  # UC-10
        direct_panel = QWidget()
        dv = QVBoxLayout(direct_panel)
        dv.setContentsMargins(0, 0, 0, 0)
        dv.addWidget(npsha_chk)
        dv.addWidget(npsha_f.row("NPSHa"))

        # -- Quoted NPSHr (API 610 "rated NPSH +0 %") --------------------------
        quoted_chk = ui.checkbox(
            "Judge against the quoted NPSHr (datasheet, at rated flow)",
            s.get("npshr_quoted") is not None,
        )
        quoted_f = ui.UnitField(
            "npsh",
            s["npshr_quoted"] if s.get("npshr_quoted") is not None else 0.0,
            s.get("npshr_quoted_unit"),
            on_change=lambda: sync(),
            lo=0.0,
            hi=1e6,
            step=0.1,
            decimals=3,
        )
        quoted_f.spin.setToolTip(
            "API 610: NPSH3 at the rated point shall not exceed the quoted value "
            "(rated NPSH tolerance +0 %)."
        )

        # -- NPSHa: calculator ----------------------------------------------
        pf = ui.PressureField(
            s["calc_p"],
            s.get("calc_p_unit"),
            s.get("calc_p_ref", "g"),
            on_change=lambda: sync(),
        )
        temp_f = ui.UnitField(
            "temperature",
            s["calc_temp"],
            s.get("calc_temp_unit"),
            on_change=lambda: sync(),
            lo=-100.0,
            hi=1000.0,
            step=1.0,
            decimals=2,
        )
        id_chk = ui.checkbox(
            "Suction pipe ID (adds velocity head)", s["calc_id"] is not None
        )
        id_f = ui.UnitField(
            "length",
            s["calc_id"] if s["calc_id"] is not None else 100.0,
            s.get("calc_id_unit"),
            on_change=lambda: sync(),
            lo=0.0,
            hi=1e6,
            step=1.0,
            decimals=3,
        )
        z_f = ui.UnitField(
            "length",
            s["calc_z"],
            s.get("calc_z_unit"),
            on_change=lambda: sync(),
            lo=-1e6,
            hi=1e6,
            step=0.1,
            decimals=3,
        )
        calc_lbl = QLabel(objectName="MonoBlock")
        calc_panel = QWidget()
        cv = QVBoxLayout(calc_panel)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.addWidget(pf.row("Suction pressure"))
        cv.addWidget(temp_f.row("Water temperature"))
        cv.addWidget(id_chk)
        cv.addWidget(id_f.row("Suction ID"))
        cv.addWidget(z_f.row("Suction elevation z"))
        cv.addWidget(calc_lbl)

        # -- criteria overrides ---------------------------------------------
        ratio_chk = ui.checkbox("Min NPSHa / NPSHr ratio", ov["min_ratio"] is not None)
        ratio_spin = ui.spin(
            ov["min_ratio"] if ov["min_ratio"] is not None else 1.0,
            0.0,
            100.0,
            0.05,
            3,
            None,
        )
        mm = ov["min_margin"] if isinstance(ov["min_margin"], dict) else {}
        margin_chk = ui.checkbox("Min margin NPSHa − NPSHr", bool(mm))
        margin_f = ui.UnitField(
            "npsh",
            mm.get("value", 0.0),
            mm.get("unit"),
            on_change=lambda: sync(),
            lo=0.0,
            hi=1e6,
            step=0.1,
            decimals=3,
        )

        def sync(*_):
            s["pump_tag"] = tag.text()
            s["mode"] = mode.currentData()
            s["degree"] = degree.value()
            s["npsha"] = npsha_f.magnitude() if npsha_chk.isChecked() else None
            s["npsha_unit"] = npsha_f.unit_label()
            if quoted_chk.isChecked():
                s["npshr_quoted"] = quoted_f.magnitude()
                s["npshr_quoted_unit"] = quoted_f.unit_label()
            else:
                s.pop("npshr_quoted", None)
                s.pop("npshr_quoted_unit", None)
            quoted_f.spin.setEnabled(quoted_chk.isChecked())
            quoted_f.combo.setEnabled(quoted_chk.isChecked())
            s["calc_p"] = pf.magnitude()
            s["calc_p_unit"] = pf.unit_label()
            s["calc_p_ref"] = pf.ref()
            s["calc_temp"] = temp_f.magnitude()
            s["calc_temp_unit"] = temp_f.unit_label()
            s["calc_id"] = id_f.magnitude() if id_chk.isChecked() else None
            s["calc_id_unit"] = id_f.unit_label()
            s["calc_z"] = z_f.magnitude()
            s["calc_z_unit"] = z_f.unit_label()
            s["overrides"] = {
                "min_ratio": ratio_spin.value() if ratio_chk.isChecked() else None,
                "min_margin": (
                    {"value": margin_f.magnitude(), "unit": margin_f.unit_label()}
                    if margin_chk.isChecked()
                    else None
                ),
            }
            recompute()

        def recompute():
            on_change()
            is_calc = s.get("mode") == "calculator"
            direct_panel.setVisible(not is_calc)
            calc_panel.setVisible(is_calc)
            kind = {"ok": "ok", "reject": "error"}.get(self.state, "warn")
            banner.show_message(self.status, kind)
            calc = getattr(self, "_calc_npsha", None)
            if calc is not None:
                calc_lbl.setText(f"Calculated NPSHa: {_m(calc):.3f} m")
            else:
                calc_lbl.setText(getattr(self, "_calc_error", "") or "")

        tag.textChanged.connect(sync)
        mode.currentIndexChanged.connect(sync)
        degree.valueChanged.connect(sync)
        npsha_chk.toggled.connect(sync)
        quoted_chk.toggled.connect(sync)
        id_chk.toggled.connect(sync)
        ratio_chk.toggled.connect(sync)
        ratio_spin.valueChanged.connect(sync)
        margin_chk.toggled.connect(sync)

        dlg.add(ui.section("Pump identity"))
        dlg.add(ui.row("Pump TAG", tag))
        dlg.add(ui.hline())
        dlg.add(ui.section("NPSHr test points"))
        dlg.add(ui.row("Capacity unit", q_unit))
        dlg.add(ui.row("NPSHr unit", n_unit))
        dlg.add(bar)
        dlg.add(table)
        dlg.add(ui.row("Fit degree", degree))
        dlg.add(quoted_chk)
        dlg.add(quoted_f.row("Quoted NPSHr"))
        dlg.add(ui.hline())
        dlg.add(ui.section("NPSHa"))
        dlg.add(ui.row("Source", mode))
        dlg.add(direct_panel)
        dlg.add(calc_panel)
        dlg.add(ui.hline())
        dlg.add(ui.section("Criteria overrides (blank = library criteria)"))
        dlg.add(ratio_chk)
        dlg.add(ui.row("Min ratio", ratio_spin))
        dlg.add(margin_chk)
        dlg.add(margin_f.row("Min margin"))
        dlg.add(ui.hline())
        dlg.add(ui.section("Verdict"))
        dlg.add(banner)

        fill_table()
        recompute()
        dlg.resize(700, 860)
        return dlg
