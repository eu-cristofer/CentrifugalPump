"""
nodes.report_export — Report Export  (UI_SPEC §5.7)

Inputs: the shared ``RatedPoint`` + a **multi-connection** ``branch`` input that
accepts ``CorrectedCurve`` / ``FittedModel`` / ``ComplianceResult`` from each
pump.  Payloads are grouped by pump TAG into a :class:`ReportBundle`.
One branch → single-pump report; N branches → one consolidated report.

Exports: ``.docx`` (via the library's ``ReportGenerator``), ``.json``
(reusable data file), and the per-pump plot ``.png``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem,
)

from ..binding import assemble_report_data, generate_docx
from ..persistence import write_json
from ..signals import BranchBundle, ComplianceResult, CorrectedCurve, FittedModel, RatedPoint
from .base import BaseNode, PortSpec
from . import ui

_DEFAULT_EQUIP = ["Manufacturer", "Model", "Serial No.", "Type", "Driver", "Test bench"]


class ReportExportNode(BaseNode):
    kind = "report_export"
    title = "Report Export"
    glyph = "▤"
    inputs = [PortSpec("RatedPoint", "RatedPoint"), PortSpec("branch", "*", multi=True)]
    outputs = []

    def default_settings(self) -> Dict:
        return {
            "language": "en",
            "template_path": "",
            "out_dir": "",
            "filename": "",
            "equipment": {k: "" for k in _DEFAULT_EQUIP},
        }

    # -- grouping ----------------------------------------------------------
    def _bundle(self, inputs):
        rated = self.first(inputs, "RatedPoint")
        groups: Dict[str, dict] = {}
        for payload in self.all_of(inputs, "branch"):
            tag = getattr(payload, "pump_tag", None)
            if tag is None:
                continue
            g = groups.setdefault(tag, {})
            if isinstance(payload, CorrectedCurve):
                g["corrected"] = payload
            elif isinstance(payload, FittedModel):
                g["fitted"] = payload
            elif isinstance(payload, ComplianceResult):
                g["compliance"] = payload
        branches = tuple(
            BranchBundle(
                pump_tag=tag,
                corrected=g.get("corrected"),
                fitted=g.get("fitted"),
                compliance=g.get("compliance"),
                equipment=self.settings.get("equipment", {}),
            )
            for tag, g in groups.items()
        )
        return rated, branches

    def compute(self, inputs) -> Dict[str, object]:
        rated, branches = self._bundle(inputs)
        self._rated = rated
        self._branches = branches
        if rated is None or not branches:
            return self.emit_nothing("Connect rated point + ≥1 branch", "idle")
        checks = [b.compliance for b in branches if b.compliance is not None]
        overall = bool(checks) and all(c.overall_pass for c in checks)
        n = len(branches)
        verdict = "APPROVED" if overall else ("REJECTED" if checks else "pending")
        self.status = f"{n} pump{'s' if n > 1 else ''} · {verdict}"
        self.state = "ok" if overall else ("reject" if checks else "idle")
        return {}

    def port_label(self, name: str) -> str:
        return {"RatedPoint": "Rated", "branch": "Branches"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "Report Export",
            "Assemble one consolidated FAT report. The rated point is shared; each "
            "connected branch adds a Test Data — <TAG> section.",
            width=560,
        )
        banner = ui.Banner()
        pumps_lbl = QLabel(objectName="MonoBlock")

        language = ui.combo([("English (EN)", "en"), ("Português (PT-BR)", "pt")], s["language"], None)
        language.currentIndexChanged.connect(
            lambda _: s.__setitem__("language", language.currentData())
        )

        template = ui.line_edit(s["template_path"], None, "optional template_*.docx path")
        template.textChanged.connect(lambda v: s.__setitem__("template_path", v))
        tmpl_btn = QPushButton("Browse…")
        tmpl_btn.setObjectName("ToolButton")
        tmpl_btn.clicked.connect(lambda: _pick_file(dlg, template, s, "template_path"))

        out_dir = ui.line_edit(s["out_dir"], None, "output folder")
        out_dir.textChanged.connect(lambda v: s.__setitem__("out_dir", v))
        dir_btn = QPushButton("Browse…")
        dir_btn.setObjectName("ToolButton")
        dir_btn.clicked.connect(lambda: _pick_dir(dlg, out_dir, s))

        filename = ui.line_edit(s["filename"], None, self._default_filename())
        filename.textChanged.connect(lambda v: s.__setitem__("filename", v))

        equip = QTableWidget(len(_DEFAULT_EQUIP), 2)
        equip.setHorizontalHeaderLabels(["Field", "Value"])
        equip.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        equip.setObjectName("ReadGrid")
        for i, key in enumerate(_DEFAULT_EQUIP):
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            equip.setItem(i, 0, key_item)
            equip.setItem(i, 1, QTableWidgetItem(s["equipment"].get(key, "")))

        def on_equip(item):
            if item.column() == 1:
                key = equip.item(item.row(), 0).text()
                s["equipment"][key] = item.text()

        equip.itemChanged.connect(on_equip)

        def refresh_pumps():
            on_change()
            branches = getattr(self, "_branches", ())
            if not branches:
                pumps_lbl.setText("No branches connected.")
                banner.setVisible(False)
                return
            lines = []
            for b in branches:
                verdict = "—"
                if b.compliance is not None:
                    verdict = "APPROVED ✓" if b.compliance.overall_pass else "REJECTED ✗"
                has = "".join(
                    m for m, ok in [("C", b.corrected), ("F", b.fitted), ("V", b.compliance)] if ok
                )
                lines.append(f"{b.pump_tag:<14} [{has:<3}]  {verdict}")
            pumps_lbl.setText("\n".join(lines))
            banner.show_message(self.status, "ok" if self.state == "ok" else "info")

        # export buttons
        def export_docx():
            rated = getattr(self, "_rated", None)
            branches = getattr(self, "_branches", ())
            if not rated or not branches:
                QMessageBox.warning(dlg, "Report Export", "Connect the rated point and at least one branch.")
                return
            data = assemble_report_data(rated, branches, s["equipment"])
            out = self._resolve_output(s, ".docx", rated)
            try:
                path = generate_docx(
                    data, language=s["language"],
                    template_path=s["template_path"] or None, output_file=out,
                )
                QMessageBox.information(dlg, "Report Export", f"Saved:\n{path}")
            except FileNotFoundError as exc:
                QMessageBox.warning(
                    dlg, "Template not found",
                    f"{exc}\n\nProvide a template_{s['language']}.docx via the Template field.",
                )
            except Exception as exc:
                QMessageBox.critical(dlg, "Report Export failed", str(exc))

        def export_json():
            rated = getattr(self, "_rated", None)
            branches = getattr(self, "_branches", ())
            if not rated:
                return
            out = self._resolve_output(s, ".json", rated)
            write_json(out, _bundle_json(rated, branches, s["equipment"]))
            QMessageBox.information(dlg, "Report Export", f"Saved:\n{out}")

        def export_png():
            branches = getattr(self, "_branches", ())
            rated = getattr(self, "_rated", None)
            if not branches or not rated:
                return
            folder = s["out_dir"] or QFileDialog.getExistingDirectory(dlg, "Choose folder")
            if not folder:
                return
            from ..binding import build_report_png
            n = 0
            for b in branches:
                if b.corrected is None:
                    continue
                png = build_report_png(b.corrected, rated)
                with open(f"{folder}/{b.pump_tag}_curve.png", "wb") as fh:
                    fh.write(png.getvalue())
                n += 1
            QMessageBox.information(dlg, "Report Export", f"Exported {n} plot(s) to:\n{folder}")

        btn_docx = _btn("Export .docx", export_docx, primary=True)
        btn_json = _btn("Export .json", export_json)
        btn_png = _btn("Export .png", export_png)

        from PySide6.QtWidgets import QHBoxLayout, QWidget
        btnrow = QWidget()
        bl = QHBoxLayout(btnrow)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(btn_docx)
        bl.addWidget(btn_json)
        bl.addWidget(btn_png)
        bl.addStretch(1)

        tmplrow = QWidget()
        tr = QHBoxLayout(tmplrow)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.addWidget(template, 1)
        tr.addWidget(tmpl_btn)

        dirrow = QWidget()
        dr = QHBoxLayout(dirrow)
        dr.setContentsMargins(0, 0, 0, 0)
        dr.addWidget(out_dir, 1)
        dr.addWidget(dir_btn)

        dlg.add(ui.section("Connected pumps"))
        dlg.add(pumps_lbl)
        dlg.add(ui.hline())
        dlg.add(ui.section("Output"))
        dlg.add(ui.row("Language", language))
        dlg.add(ui.row("Template", tmplrow))
        dlg.add(ui.row("Folder", dirrow))
        dlg.add(ui.row("Filename", filename))
        dlg.add(ui.hline())
        dlg.add(ui.section("Equipment description (service-level)"))
        dlg.add(equip)
        dlg.add(btnrow)
        dlg.add(banner)
        refresh_pumps()
        dlg.resize(600, 720)
        return dlg

    # -- helpers -----------------------------------------------------------
    def _default_filename(self) -> str:
        rated = getattr(self, "_rated", None)
        branches = getattr(self, "_branches", ())
        date = datetime.now().strftime("%d-%m-%Y")
        if rated is None:
            return f"Report_{date}"
        tag = rated.tag if len(branches) != 1 else branches[0].pump_tag
        return f"Report_{tag}_{date}".replace("/", "")

    def _resolve_output(self, s, ext, rated) -> str:
        name = (s.get("filename") or self._default_filename()).strip()
        if not name.endswith(ext):
            name += ext
        folder = s.get("out_dir") or "."
        return f"{folder.rstrip('/')}/{name}"


def _bundle_json(rated: RatedPoint, branches, equipment: dict) -> dict:
    """Richer §7 bundle: shared rated + per-pump corrected data + verdict."""
    doc = {
        "service_tag": rated.tag,
        "standard": rated.standard,
        "unit": rated.pressure_unit,
        "rated": {
            "q_m3h": rated.q_m3h, "head_m": rated.head_m, "n_rpm": rated.speed_rpm,
            "power_kw": rated.power_kw, "eff_pct": rated.efficiency_pct,
            "dens_rel": rated.density_rel, "visc_nom_cst": rated.viscosity_cst,
            "head_shutoff": rated.head_shutoff_m,
        },
        "equipment": {k: v for k, v in (equipment or {}).items() if v},
        "pumps": [],
    }
    for b in branches:
        entry = {"tag": b.pump_tag}
        if b.compliance is not None:
            entry["overall"] = b.compliance.verdict_label
            entry["parameters"] = [
                {
                    "name": p.name, "actual": p.actual, "predicted": p.predicted,
                    "deviation": p.deviation, "tolerance": p.tolerance, "passed": p.passed,
                }
                for p in b.compliance.parameters
            ]
        if b.corrected is not None:
            td = b.corrected.curve.test_data
            entry["corrected"] = {
                key: [float(getattr(v, "magnitude", v)) for v in vals]
                for key, vals in td.items()
            }
        doc["pumps"].append(entry)
    return doc


def _btn(text, fn, primary: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("PrimaryButton" if primary else "ToolButton")
    b.clicked.connect(fn)
    return b


def _pick_file(dlg, line_edit, s, key):
    path, _ = QFileDialog.getOpenFileName(dlg, "Choose template", "", "Word (*.docx)")
    if path:
        line_edit.setText(path)
        s[key] = path


def _pick_dir(dlg, line_edit, s):
    folder = QFileDialog.getExistingDirectory(dlg, "Choose output folder")
    if folder:
        line_edit.setText(folder)
        s["out_dir"] = folder
