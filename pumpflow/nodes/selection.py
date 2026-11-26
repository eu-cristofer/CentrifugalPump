"""
nodes.selection — Pump Selection  (sprint 12 / UC-01)

Source node: given a duty (Q, H) and a catalogue folder of ``*.pumpcurve.json``
curves it ranks the pumps that can serve the duty, adapting each by speed (VFD)
and/or impeller trim (``pump.catalogue``).  An optional ``FluidSpec`` input sets
the duty fluid (density change only).

The node emits a ``RatedPoint`` built from the chosen candidate (the top-ranked
row, or the row picked in the dialog) so it can be wired into the rest of the
canvas ("send to canvas").  All physics is in :mod:`pump` via ``binding``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from pump import Q_

from ..numfmt import num as _nf
from .. import units
from ..binding import BindingError, make_fluid, rated_from_candidate, select_pumps
from .base import BaseNode, PortSpec

_COLUMNS = [
    "#",
    "Pump",
    "Adaptation",
    "Speed / diameter",
    "η [%]",
    "Power [kW]",
    "Q/Q_BEP",
    "POR",
    "Trim margin",
]


def _value_text(cand) -> str:
    if cand.adaptation == "speed" and cand.value is not None:
        return f"{_nf(cand.value.to('rpm').magnitude, '.0f')} rpm"
    if cand.adaptation == "trim" and cand.value is not None:
        return f"{_nf(cand.value.to('mm').magnitude, '.1f')} mm"
    return "—"


class SelectionNode(BaseNode):
    kind = "selection"
    title = "Pump Selection"
    glyph = "⊕"
    is_source = True
    inputs = [PortSpec("FluidSpec", "FluidSpec")]
    outputs = [PortSpec("RatedPoint", "RatedPoint")]

    _result = None  # last SelectionResult (None when nothing was evaluated)
    _catalogue = None

    def default_settings(self) -> Dict:
        p = units.PREFS
        qu, hu = p.default_unit("capacity"), p.default_unit("head")
        return {
            "folder": "",
            "duty_q": units.convert_display(100.0, "capacity", "m³/h", qu),
            "duty_q_unit": qu,
            "duty_h": units.convert_display(50.0, "head", "m", hu),
            "duty_h_unit": hu,
            "allow_speed": True,
            "allow_trim": True,
            "choice": 0,
        }

    def _duty(self):
        s = self.settings
        q_unit = s.get("duty_q_unit") or units.canonical_unit("capacity")
        h_unit = s.get("duty_h_unit") or units.canonical_unit("head")
        q = Q_(float(s["duty_q"]), units.pint_str("capacity", q_unit))
        h = Q_(float(s["duty_h"]), units.pint_str("head", h_unit))
        return q, h

    def compute(self, inputs) -> Dict[str, object]:
        self._result = None
        self._catalogue = None
        s = self.settings
        folder = str(s.get("folder") or "").strip()
        if not folder or not Path(folder).is_dir():
            return self.emit_nothing("no catalogue", "idle")
        q, h = self._duty()
        if not (float(q.magnitude) > 0 and float(h.magnitude) > 0):
            return self.emit_nothing("Duty Q and H must be > 0", "invalid")
        spec = self.first(inputs, "FluidSpec")
        try:
            fluid = make_fluid(spec) if spec is not None else None
            catalogue, result = select_pumps(
                folder,
                q,
                h,
                fluid=fluid,
                allow_speed=bool(s.get("allow_speed", True)),
                allow_trim=bool(s.get("allow_trim", True)),
            )
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")
        self._catalogue = catalogue
        self._result = result
        if len(catalogue) == 0:
            msg = "no catalogue (no *.pumpcurve.json curves in the folder)"
            if catalogue.load_errors:
                msg += f" · {len(catalogue.load_errors)} unreadable"
            return self.emit_nothing(msg, "idle")
        if not result:
            return self.emit_nothing(
                f"no pump fits the duty ({len(result.rejected)} rejections)",
                "invalid",
            )
        idx = min(max(int(s.get("choice", 0) or 0), 0), len(result) - 1)
        chosen = result[idx]
        try:
            rated = rated_from_candidate(chosen, q, h)
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")
        eta = float(chosen.eta_at_duty.to("percent").magnitude)
        warn = "" if chosen.in_por else " · ⚠ outside POR"
        self.status = (
            f"{len(result)} candidate(s) · #{idx + 1} {chosen.label} · "
            f"η {_nf(eta, '.1f')} %{warn}"
        )
        self.state = "ok"
        return {"RatedPoint": rated}

    def port_label(self, name: str) -> str:
        return {"FluidSpec": "Fluid", "RatedPoint": "Rated"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QFileDialog,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QWidget,
        )

        from . import ui

        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Pump Selection",
            "Ranks the catalogue pumps for the duty, adapting each by speed (VFD) "
            "and/or impeller trim (affinity laws).  Preferred operating region: "
            "unverified seed from the standards data.",
            width=760,
            maximizable=True,
        )
        banner = ui.Banner()
        info = QLabel("—")
        info.setWordWrap(True)
        rejections = QLabel("")
        rejections.setWordWrap(True)

        folder = ui.line_edit(
            s.get("folder", ""), None, "folder with *.pumpcurve.json files"
        )
        browse = QPushButton("Browse…")
        folder_row = QWidget()
        fl = QHBoxLayout(folder_row)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(8)
        lab = QLabel("Catalogue folder", objectName="FieldLabel")
        lab.setMinimumWidth(150)
        fl.addWidget(lab)
        fl.addWidget(folder, 1)
        fl.addWidget(browse)

        duty_q = ui.UnitField(
            "capacity",
            s["duty_q"],
            s.get("duty_q_unit"),
            on_change=lambda: on_duty(),
            hi=1e7,
            step=10.0,
            decimals=3,
        )
        duty_h = ui.UnitField(
            "head",
            s["duty_h"],
            s.get("duty_h_unit"),
            on_change=lambda: on_duty(),
            hi=1e5,
            step=1.0,
            decimals=3,
        )
        speed_cb = ui.checkbox(
            "Allow speed change (VFD)",
            s.get("allow_speed", True),
            lambda: on_flags(),
        )
        trim_cb = ui.checkbox(
            "Allow impeller trim", s.get("allow_trim", True), lambda: on_flags()
        )

        table = QTableWidget(0, len(_COLUMNS))
        table.setHorizontalHeaderLabels(_COLUMNS)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setObjectName("ReadGrid")

        busy = [False]

        def refresh():
            on_change()
            result = self._result
            busy[0] = True
            table.setRowCount(0)
            if result:
                for i, c in enumerate(result):
                    r = table.rowCount()
                    table.insertRow(r)
                    power = c.power_at_duty
                    values = [
                        str(i + 1),
                        c.entry.name,
                        c.adaptation,
                        _value_text(c),
                        f"{_nf(c.eta_at_duty.to('percent').magnitude, '.1f')}",
                        f"{_nf(power.to('kW').magnitude, '.1f')}" if power is not None else "—",
                        f"{_nf(c.q_over_qbep, '.2f')}",
                        "yes" if c.in_por else "no",
                        (
                            f"{_nf(c.trim_margin * 100, '.1f')} %"
                            if c.trim_margin is not None
                            else "—"
                        ),
                    ]
                    for col, v in enumerate(values):
                        table.setItem(r, col, QTableWidgetItem(v))
                idx = min(max(int(s.get("choice", 0) or 0), 0), len(result) - 1)
                table.selectRow(idx)
            busy[0] = False
            if self.state == "ok":
                info.setText(self.status)
            else:
                info.setText("—")
            banner.show_message(
                (
                    ""
                    if self.state in ("ok", "idle") and not self._load_errors()
                    else (self.status if self.state != "ok" else "")
                ),
                "error" if self.state in ("invalid", "error") else "warn",
            )
            lines = list(result.reasons[:8]) if result is not None else []
            lines += self._catalogue.load_errors[:4] if self._catalogue else []
            rejections.setText(("Not offered:\n" + "\n".join(lines)) if lines else "")

        def on_duty():
            s["duty_q"] = duty_q.magnitude()
            s["duty_q_unit"] = duty_q.unit_label()
            s["duty_h"] = duty_h.magnitude()
            s["duty_h_unit"] = duty_h.unit_label()
            s["choice"] = 0
            refresh()

        def on_flags():
            s["allow_speed"] = bool(speed_cb.isChecked())
            s["allow_trim"] = bool(trim_cb.isChecked())
            s["choice"] = 0
            refresh()

        def on_folder():
            s["folder"] = folder.text().strip()
            s["choice"] = 0
            refresh()

        def on_browse():
            path = QFileDialog.getExistingDirectory(
                dlg, "Catalogue folder", folder.text().strip()
            )
            if path:
                folder.setText(path)
                on_folder()

        def on_row():
            if busy[0]:
                return
            rows = table.selectionModel().selectedRows()
            if rows:
                s["choice"] = rows[0].row()
                on_change()
                info.setText(self.status if self.state == "ok" else "—")

        folder.editingFinished.connect(on_folder)
        browse.clicked.connect(lambda _=False: on_browse())
        table.itemSelectionChanged.connect(on_row)

        dlg.add(ui.section("Duty"))
        dlg.add(duty_q.row("Capacity Q"))
        dlg.add(duty_h.row("Differential head H"))
        dlg.add(speed_cb)
        dlg.add(trim_cb)
        dlg.add(folder_row)
        dlg.add(ui.hline())
        dlg.add(
            ui.section("Ranked candidates (the selected row is sent to the canvas)")
        )
        dlg.add(table)
        dlg.add(ui.row("Chosen", info))
        dlg.add(rejections)
        dlg.add(banner)
        refresh()
        dlg.resize(820, 620)
        return dlg

    def _load_errors(self):
        return self._catalogue.load_errors if self._catalogue else []
