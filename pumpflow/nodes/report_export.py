"""
nodes.report_export — Report Export  (UI_SPEC §5.7)

Inputs: the shared ``RatedPoint`` + a **multi-connection** ``branch`` input that
accepts ``CorrectedCurve`` / ``FittedModel`` / ``ComplianceResult`` /
``MechanicalRunResultSignal`` / ``NPSHResultSignal`` from each pump.  Payloads
are grouped by pump TAG into a :class:`ReportBundle`.
One branch → single-pump report; N branches → one consolidated report.

Exports: ``.docx`` (via the library's ``ReportGenerator``), ``.tex`` and
``.pdf`` (LaTeX, via ``LatexReportGenerator``; the PDF is compiled with
latexmk/pdflatex), ``.html`` (one self-contained file), ``.json`` (reusable data
file), and the per-pump plot ``.png``.  "Export all" writes every format listed
in ``settings["formats"]`` (default: docx + tex + pdf + html).  The same export
runs headless with ``python -m pumpflow.export_cli``.

Cover page: ``project``, ``client``, ``location``, ``test_date``, ``revision``
and the three ``signatories`` (Vendor / Inspector / Client witness, editable
names) feed the report cover and signature block.  Markdown Note nodes tagged
"Include in report" feed the "Deviations and open points" section.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from ..binding import (
    DEFAULT_SIGNATORY_ROLES, REPORT_FORMATS, SUMMARY_FIELDS, SUMMARY_FORMATS,
    assemble_report_data, export_reports, export_test_summary, test_data_summaries,
    open_points_from_notes,
)
from ..numfmt import decimal, decimal_for_language
from ..persistence import write_json
from ..signals import (
    BranchBundle, ComplianceResult, CorrectedCurve, FittedModel,
    MechanicalRunResultSignal, MechanicalRunSet, NPSHResultSignal, NPSHSet,
    RatedPoint,
)
from .base import BaseNode, PortSpec

_DEFAULT_EQUIP = ["Manufacturer", "Model", "Serial No.", "Type", "Driver", "Test bench"]
_COVER_KEYS = ("project", "client", "location", "test_date", "revision")


def overall_verdict_text(checks) -> str:
    """Consolidated verdict of several pumps, in the Compliance node's words.

    REJECTED if any pump is rejected, else NOT FULLY ASSESSED if any is, else
    APPROVED; "provisional" / "tolerances overridden" are kept when any pump
    carries them.  ``pending`` when no pump has a performance verdict yet.
    """
    if not checks:
        return "pending"
    labels = [c.verdict_label for c in checks]
    if "REJECTED" in labels:
        text = "REJECTED ✗"
    elif "NOT FULLY ASSESSED" in labels:
        text = "NOT FULLY ASSESSED ⚠"
    else:
        text = "APPROVED ✓"
    qualifiers = []
    if any(c.unverified for c in checks):
        qualifiers.append("provisional")
    if any(c.overridden for c in checks):
        qualifiers.append("tolerances overridden")
    if qualifiers:
        text += " (" + ", ".join(qualifiers) + ")"
    return text


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
            "project": "",
            "client": "",
            "location": "",
            "test_date": "",
            "revision": "",
            "signatories": [
                {"role": role, "name": ""} for role in DEFAULT_SIGNATORY_ROLES
            ],
        }

    def _ensure_defaults(self) -> None:
        """Fill the cover keys a project saved before sprint 14 does not carry."""
        s = self.settings
        for key in _COVER_KEYS:
            s.setdefault(key, "")
        if not isinstance(s.get("signatories"), list) or not s["signatories"]:
            s["signatories"] = [
                {"role": role, "name": ""} for role in DEFAULT_SIGNATORY_ROLES
            ]

    def report_notes(self) -> List[dict]:
        """Settings of the Markdown Note nodes on the same canvas (may be empty)."""
        item = getattr(self, "item", None)
        scene = item.scene() if item is not None and hasattr(item, "scene") else None
        if scene is None:
            return []
        return [
            n.logic.settings
            for n in getattr(scene, "nodes", [])
            if n.logic.kind == "markdown_note"
        ]

    def report_inputs(self):
        """``(rated, branches, notes)`` for an export, evaluated afresh.

        The canvas is re-evaluated headless, so the charts are drawn with the
        decimal separator in force (the exporters set the report language's
        separator around this call).  Without a canvas the last computed
        inputs are used.
        """
        item = getattr(self, "item", None)
        scene = item.scene() if item is not None and hasattr(item, "scene") else None
        if scene is None or not hasattr(scene, "to_dict"):
            return (
                getattr(self, "_rated", None),
                list(getattr(self, "_branches", ())),
                self.report_notes(),
            )
        from ..engine import Graph

        graph = Graph.from_dict(scene.to_dict())
        graph.evaluate()
        logic = [getattr(n, "logic", n) for n in graph.nodes]
        me = next((lg for lg in logic if lg.node_id == self.node_id), None)
        notes = [lg.settings for lg in logic if lg.kind == "markdown_note"]
        if me is None:  # pragma: no cover - the canvas always holds this node
            return getattr(self, "_rated", None), list(getattr(self, "_branches", ())), notes
        return getattr(me, "_rated", None), list(getattr(me, "_branches", ())), notes

    # -- grouping ----------------------------------------------------------
    def _bundle(self, inputs):
        rated = self.first(inputs, "RatedPoint")
        groups: Dict[str, dict] = {}
        for payload in self.all_of(inputs, "branch"):
            tag = getattr(payload, "pump_tag", None)
            if tag is None or isinstance(payload, (MechanicalRunSet, NPSHSet)):
                continue
            g = groups.setdefault(tag, {})
            if isinstance(payload, CorrectedCurve):
                g["corrected"] = payload
            elif isinstance(payload, FittedModel):
                g["fitted"] = payload
            elif isinstance(payload, ComplianceResult):
                g["compliance"] = payload
            elif isinstance(payload, MechanicalRunResultSignal):
                g["mechanical"] = payload
            elif isinstance(payload, NPSHResultSignal):
                g["npsh"] = payload
        branches = tuple(
            BranchBundle(
                pump_tag=tag,
                corrected=g.get("corrected"),
                fitted=g.get("fitted"),
                compliance=g.get("compliance"),
                equipment=self.settings.get("equipment", {}),
                mechanical=g.get("mechanical"),
                npsh=g.get("npsh"),
            )
            for tag, g in groups.items()
        )
        return rated, branches

    def compute(self, inputs) -> Dict[str, object]:
        self._ensure_defaults()
        rated, branches = self._bundle(inputs)
        self._rated = rated
        self._branches = branches
        if rated is None or not branches:
            return self.emit_nothing("Connect rated point + ≥1 branch", "idle")
        checks = [b.compliance for b in branches if b.compliance is not None]
        overall = bool(checks) and all(c.overall_pass for c in checks)
        n = len(branches)
        self.status = f"{n} pump{'s' if n > 1 else ''} · {overall_verdict_text(checks)}"
        self.state = "ok" if overall else ("reject" if checks else "idle")
        if checks:
            labels = [c.verdict_label for c in checks]
            label = next(
                (v for v in ("REJECTED", "NOT FULLY ASSESSED") if v in labels),
                "APPROVED",
            )
            self.set_badge(
                label,
                {"APPROVED": "ok", "NOT FULLY ASSESSED": "warn"}.get(label, "fail"),
                provisional=any(c.unverified for c in checks),
                overridden=any(c.overridden for c in checks),
            )
        return {}

    def port_label(self, name: str) -> str:
        return {"RatedPoint": "Rated", "branch": "Branches"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QFileDialog, QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
            QTableWidgetItem,
        )

        from . import ui

        self._ensure_defaults()
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

        def cover_field(key, placeholder=""):
            edit = ui.line_edit(s.get(key, ""), None, placeholder)
            edit.textChanged.connect(lambda v, k=key: s.__setitem__(k, v))
            return edit

        project = cover_field("project", "project / contract")
        client = cover_field("client", "client")
        location = cover_field("location", "test location")
        test_date = cover_field("test_date", "e.g. 2026-11-15")
        revision = cover_field("revision", "e.g. R0")

        sigs = s["signatories"]
        signers = QTableWidget(len(sigs), 2)
        signers.setHorizontalHeaderLabels(["Role", "Name"])
        signers.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        signers.setObjectName("ReadGrid")
        for i, row in enumerate(sigs):
            role_item = QTableWidgetItem(str(row.get("role", "")))
            role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)
            signers.setItem(i, 0, role_item)
            signers.setItem(i, 1, QTableWidgetItem(str(row.get("name", ""))))

        def on_signer(item):
            if item.column() == 1 and 0 <= item.row() < len(sigs):
                sigs[item.row()]["name"] = item.text()

        signers.itemChanged.connect(on_signer)

        include_sigs = ui.checkbox(
            "Include signature block in the report",
            s.get("include_signatures", True),
            None,
        )
        signers.setEnabled(include_sigs.isChecked())

        def on_include_sigs(v):
            # Stored only when off, so older projects re-save byte-identical.
            if v:
                s.pop("include_signatures", None)
            else:
                s["include_signatures"] = False
            signers.setEnabled(bool(v))
            on_change()

        include_sigs.toggled.connect(on_include_sigs)

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

        # -- test data summary (API 610 Annex M / 8th App. T): optional fields,
        # stored only when filled so older projects re-save unchanged.
        summary_labels = {
            "purchaser": ("Purchaser", "defaults to the client"),
            "po_number": ("Purchase order no.", ""),
            "item_number": ("Item no.", "defaults to the service TAG"),
            "curve_number": ("Curve no.", ""),
            "stages": ("No. of stages", "e.g. 1"),
            "impeller_pattern": ("Impeller pattern no.", ""),
            "vanes": ("No. of vanes", ""),
            "volute_pattern": ("Volute/diffuser pattern no.", ""),
            "blade_tip_clearance": ("Blade tip clearance (%)", ""),
        }
        summary_edits = {}
        for key in SUMMARY_FIELDS:
            edit = ui.line_edit(s.get(key, ""), None, summary_labels[key][1])

            def store(v, k=key):
                if v.strip():
                    s[k] = v
                else:
                    s.pop(k, None)

            edit.textChanged.connect(store)
            summary_edits[key] = edit
        ambient_chk = ui.checkbox(
            "Ambient temperature recorded", s.get("ambient_temp") is not None
        )
        ambient = ui.UnitField(
            "temperature",
            float(s.get("ambient_temp") or 25.0),
            s.get("ambient_temp_unit"),
            on_change=lambda: on_ambient(),
            lo=-60.0,
            hi=200.0,
            step=0.5,
            decimals=1,
        )

        def on_ambient():
            on = ambient_chk.isChecked()
            ambient.spin.setEnabled(on)
            ambient.combo.setEnabled(on)
            if on:
                s["ambient_temp"] = ambient.magnitude()
                s["ambient_temp_unit"] = ambient.unit_label()
            else:
                s.pop("ambient_temp", None)
                s.pop("ambient_temp_unit", None)

        ambient_chk.toggled.connect(lambda _=None: on_ambient())
        ambient.spin.setEnabled(ambient_chk.isChecked())
        ambient.combo.setEnabled(ambient_chk.isChecked())

        def refresh_pumps():
            on_change()
            branches = getattr(self, "_branches", ())
            if not branches:
                pumps_lbl.setText("No branches connected.")
                banner.setVisible(False)
                return
            lines = []
            for b in branches:
                verdict = (
                    b.compliance.verdict_text if b.compliance is not None
                    else "no performance verdict"
                )
                has = " · ".join(
                    label for label, ok in [
                        ("Corrected", b.corrected), ("Fitted", b.fitted),
                        ("Verdict", b.compliance), ("MRT", b.mechanical),
                        ("NPSH", b.npsh),
                    ] if ok
                )
                lines.append(f"{b.pump_tag}  —  {verdict}\n    sections: {has or 'none'}")
            pumps_lbl.setText("\n".join(lines))
            banner.show_message(self.status, "ok" if self.state == "ok" else "info")

        # export buttons — every document format goes through
        # binding.export_reports so the GUI and the CLI behave identically.
        def run_export(formats):
            with decimal(decimal_for_language(s["language"])):
                rated, found, notes = self.report_inputs()
                branches = [
                    b for b in found
                    if b.fitted is not None or b.mechanical is not None
                    or b.npsh is not None
                ]
                if not rated or not branches:
                    QMessageBox.warning(
                        dlg, "Report Export",
                        "Connect the rated point and at least one complete branch "
                        "(test points → correction → curve fit), a mechanical run "
                        "or an NPSH result.",
                    )
                    return
                data = assemble_report_data(
                    rated, branches, s["equipment"], settings=s, notes=notes,
                )
                stem = self._resolve_output(s, "", rated)
                folder, _, name = stem.rpartition("/")
                paths, errors = export_reports(
                    data, formats, language=s["language"],
                    template_path=s["template_path"] or None,
                    out_dir=folder or ".", stem=name,
                )
            lines = [f"Saved {fmt}: {path}" for fmt, path in paths.items()]
            lines += [f"FAILED {fmt}: {msg}" for fmt, msg in errors.items()]
            if errors and "docx" in errors and "Template" in errors["docx"]:
                lines.append(f"Provide a template_{s['language']}.docx via the Template field.")
            box = QMessageBox.warning if errors else QMessageBox.information
            box(dlg, "Report Export", "\n".join(lines))

        def export_docx():
            run_export(["docx"])

        def export_tex():
            run_export(["tex"])

        def export_pdf():
            run_export(["pdf"])

        def export_html():
            run_export(["html"])

        def export_all():
            run_export(list(s.get("formats") or REPORT_FORMATS))

        def export_summary():
            from pump.utilities.report import LocalizationHelper

            with decimal(decimal_for_language(s["language"])):
                rated, found, _notes = self.report_inputs()
                branches = [b for b in found if b.fitted is not None]
                if not rated or not branches:
                    QMessageBox.warning(
                        dlg, "Report Export",
                        "The test data summary needs the rated point and at least one "
                        "fitted branch (test points → correction → curve fit).",
                    )
                    return
                summaries = test_data_summaries(
                    rated, branches, s, LocalizationHelper(s["language"])._
                )
                stem = self._resolve_output(s, "", rated)
                folder, _sep, name = stem.rpartition("/")
                paths, errors = export_test_summary(
                    summaries, SUMMARY_FORMATS, language=s["language"],
                    out_dir=folder or ".", stem=f"{name}_test_summary",
                )
            lines = [f"Saved {fmt}: {path}" for fmt, path in paths.items()]
            lines += [f"FAILED {fmt}: {msg}" for fmt, msg in errors.items()]
            box = QMessageBox.warning if errors else QMessageBox.information
            box(dlg, "Report Export", "\n".join(lines))

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

        btn_all = _btn("Export all (docx + tex + pdf + html)", export_all, primary=True)
        btn_docx = _btn("Export .docx", export_docx)
        btn_tex = _btn("Export .tex", export_tex)
        btn_pdf = _btn("Export .pdf", export_pdf)
        btn_html = _btn("Export .html", export_html)
        btn_json = _btn("Export .json", export_json)
        btn_png = _btn("Export .png", export_png)
        btn_summary = _btn(
            "Export test data summary (docx + tex + pdf + xlsx)", export_summary
        )
        btn_summary.setAccessibleName("ExportSummary")

        from PySide6.QtWidgets import QHBoxLayout, QWidget
        btnrow = QWidget()
        bl = QHBoxLayout(btnrow)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(btn_docx)
        bl.addWidget(btn_tex)
        bl.addWidget(btn_pdf)
        bl.addWidget(btn_html)
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
        dlg.add(ui.section("Cover page"))
        dlg.add(ui.row("Project", project))
        dlg.add(ui.row("Client", client))
        dlg.add(ui.row("Location", location))
        dlg.add(ui.row("Test date", test_date))
        dlg.add(ui.row("Revision", revision))
        dlg.add(ui.section("Signatories"))
        dlg.add(include_sigs)
        dlg.add(signers)
        dlg.add(ui.hline())
        dlg.add(ui.section("Equipment description (service-level)"))
        dlg.add(equip)
        dlg.add(ui.hline())
        dlg.add(ui.section("Test data summary (API 610 Annex M / 8th ed. App. T)"))
        for key in SUMMARY_FIELDS:
            dlg.add(ui.row(summary_labels[key][0], summary_edits[key]))
        dlg.add(ui.row("", ambient_chk))
        dlg.add(ambient.row("Ambient temperature"))
        dlg.add(ui.hline())
        dlg.add(btn_all)
        dlg.add(btnrow)
        dlg.add(btn_summary)
        dlg.add(banner)
        refresh_pumps()
        dlg.resize(600, 860)
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
        # A filename typed with one extension must not leak into another format
        # ("rep.docx" exported as PDF would otherwise become "rep.docx.pdf").
        for known in (".docx", ".tex", ".pdf", ".html", ".json"):
            if name.lower().endswith(known):
                name = name[: -len(known)]
                break
        name += ext
        folder = s.get("out_dir") or "."
        return f"{folder.rstrip('/')}/{name}"


def _mag(q, unit):
    """Float magnitude of an optional Quantity in ``unit`` (``None`` stays ``None``)."""
    return None if q is None else float(q.to(unit).magnitude)


def _bundle_json(rated: RatedPoint, branches, equipment: dict) -> dict:
    """Richer §7 bundle: shared rated + per-pump corrected data + verdict."""
    doc = {
        "service_tag": rated.tag,
        "standard": rated.standard,
        "unit": "bar",
        "rated": {
            "q_m3h": _mag(rated.q, "m**3/h"), "head_m": _mag(rated.head, "m"),
            "n_rpm": _mag(rated.speed, "rpm"),
            "power_kw": _mag(rated.power, "kW"), "eff_pct": _mag(rated.efficiency, "percent"),
            "dens_rel": rated.density_rel, "visc_nom_cst": _mag(rated.viscosity, "cSt"),
            "head_shutoff": _mag(rated.head_shutoff, "m"), "npsha_m": _mag(rated.npsha, "m"),
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
                    "informational": p.informational, "note": p.note,
                }
                for p in b.compliance.parameters
            ]
        if b.corrected is not None:
            td = b.corrected.curve.test_data
            entry["corrected"] = {
                key: [float(getattr(v, "magnitude", v)) for v in vals]
                for key, vals in td.items()
            }
        if b.mechanical is not None:
            res = b.mechanical.result
            entry["mechanical_run"] = {
                "passed": bool(getattr(res, "passed", False)),
                "fully_assessed": bool(getattr(res, "fully_assessed", True)),
                "criteria": b.mechanical.criteria_label,
            }
        if b.npsh is not None:
            res = b.npsh.result
            entry["npsh"] = {
                "status": getattr(res, "status", None),
                "npsha_m": _mag(getattr(res, "npsha", None), "m"),
                "npshr_m": _mag(getattr(res, "npshr", None), "m"),
                "ratio": getattr(res, "ratio", None),
                "margin_m": _mag(getattr(res, "margin", None), "m"),
                "verified": bool(getattr(res, "verified", False)),
                "criteria": b.npsh.criteria_label,
            }
        doc["pumps"].append(entry)
    return doc


def _btn(text, fn, primary: bool = False):
    from PySide6.QtWidgets import QPushButton

    b = QPushButton(text)
    b.setObjectName("PrimaryButton" if primary else "ToolButton")
    b.clicked.connect(fn)
    return b


def _pick_file(dlg, line_edit, s, key):
    from PySide6.QtWidgets import QFileDialog

    path, _ = QFileDialog.getOpenFileName(dlg, "Choose template", "", "Word (*.docx)")
    if path:
        line_edit.setText(path)
        s[key] = path


def _pick_dir(dlg, line_edit, s):
    from PySide6.QtWidgets import QFileDialog

    folder = QFileDialog.getExistingDirectory(dlg, "Choose output folder")
    if folder:
        line_edit.setText(folder)
        s["out_dir"] = folder
