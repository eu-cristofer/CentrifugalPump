"""
app
===

The PumpFlow main window: a node toolbox, the reactive canvas, the menu/toolbar
for project + data-file IO, and the default pre-wired pipeline shipped on first
launch (UI_SPEC §2).
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget, QFileDialog, QMainWindow, QMessageBox, QPushButton, QVBoxLayout,
    QWidget,
)

from .canvas.scene import GraphScene
from .canvas.view import GraphView
from .nodes import make_node
from .nodes.registry import NODE_KINDS
from .persistence import (
    json_from_signals, rated_from_json, read_json, testset_from_json, write_json,
)
from .sample_data import SECOND_PUMP_POINTS, SINGLE_PUMP_JSON
from .style import APP_QSS


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PumpFlow — API 610 Pump Performance Workbench")
        self.resize(1320, 860)

        self.scene = GraphScene(node_factory=make_node)
        self.scene.dialog_requested.connect(self._open_dialog)
        self.view = GraphView(self.scene)
        self.setCentralWidget(self.view)

        self._build_menu()
        self._build_toolbox()
        self.statusBar().showMessage("Ready")

        self.build_default_pipeline()

    # ------------------------------------------------------------------ menu
    def _build_menu(self) -> None:
        bar = self.menuBar()

        m_file = bar.addMenu("&File")
        self._act(m_file, "New pipeline", self.build_default_pipeline, "Ctrl+N")
        self._act(m_file, "Open project (.pumpflow)…", self.open_project, "Ctrl+O")
        self._act(m_file, "Save project (.pumpflow)…", self.save_project, "Ctrl+S")
        m_file.addSeparator()
        self._act(m_file, "Import data file (.json)…", self.import_data_file)
        self._act(m_file, "Export data file (.json)…", self.export_data_file)
        m_file.addSeparator()
        self._act(m_file, "Quit", self.close, "Ctrl+Q")

        m_add = bar.addMenu("&Add node")
        for kind, title, glyph in NODE_KINDS:
            self._act(m_add, f"{glyph}  {title}", lambda _=False, k=kind: self.add_node_centered(k))

        m_canvas = bar.addMenu("&Canvas")
        self._act(m_canvas, "Recompute graph", self.scene.evaluate, "F5")
        self._act(m_canvas, "Add Pump B branch (A/B demo)", self.add_second_pump_branch)
        self._act(m_canvas, "Reset view", self._reset_view)

    def _act(self, menu, text, slot, shortcut=None) -> QAction:
        act = QAction(text, self)
        act.triggered.connect(slot)
        if shortcut:
            act.setShortcut(shortcut)
        menu.addAction(act)
        return act

    # --------------------------------------------------------------- toolbox
    def _build_toolbox(self) -> None:
        dock = QDockWidget("Widgets", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        panel = QWidget(objectName="Toolbox")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(0)
        for kind, title, glyph in NODE_KINDS:
            btn = QPushButton(f"{glyph}   {title}", objectName="ToolboxItem")
            btn.clicked.connect(lambda _=False, k=kind: self.add_node_centered(k))
            lay.addWidget(btn)
        lay.addStretch(1)
        dock.setWidget(panel)
        dock.setMinimumWidth(210)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    # ----------------------------------------------------------- node dialog
    def _open_dialog(self, logic) -> None:
        dlg = logic.create_dialog(self, on_change=self._on_dialog_change)
        if dlg is not None:
            dlg.exec()
        self.scene.evaluate()

    def _on_dialog_change(self) -> None:
        self.scene.evaluate()
        self._update_status()

    # ----------------------------------------------------------- node adding
    def add_node_centered(self, kind: str):
        center = self.view.mapToScene(self.view.viewport().rect().center())
        item = self.scene.add_node(kind, center)
        self.scene.evaluate()
        return item

    def _reset_view(self) -> None:
        self.view.resetTransform()
        self.view._zoom = 1.0
        self.view.centerOn(0, 0)

    # ---------------------------------------------------- default pipeline
    def build_default_pipeline(self) -> None:
        self.scene.load_dict({"nodes": [], "edges": []})
        s = self.scene
        rated = s.add_node("rated_point", QPointF(-660, -170))
        test = s.add_node("test_points", QPointF(-660, 150))
        corr = s.add_node("correction", QPointF(-360, -20))
        fit = s.add_node("curve_fit", QPointF(-90, -20))
        plot = s.add_node("performance_plot", QPointF(200, -230))
        check = s.add_node("compliance", QPointF(200, -30))
        report = s.add_node("report_export", QPointF(200, 190))

        wire = self._wire
        wire(rated, "RatedPoint", corr, "RatedPoint")
        wire(test, "TestPointSet", corr, "TestPointSet")
        wire(corr, "CorrectedCurve", fit, "CorrectedCurve")
        wire(fit, "FittedModel", plot, "FittedModel")
        wire(rated, "RatedPoint", plot, "RatedPoint")
        wire(fit, "FittedModel", check, "FittedModel")
        wire(rated, "RatedPoint", check, "RatedPoint")
        wire(rated, "RatedPoint", report, "RatedPoint")
        wire(corr, "CorrectedCurve", report, "branch")
        wire(fit, "FittedModel", report, "branch")
        wire(check, "ComplianceResult", report, "branch")

        self.scene.evaluate()
        self._reset_view()
        self._update_status()

    def add_second_pump_branch(self) -> None:
        """Wire a Pump B branch to the same Rated Point + Report (UI_SPEC §2 A/B)."""
        s = self.scene
        rated = self._find("rated_point")
        report = self._find("report_export")
        if rated is None or report is None:
            QMessageBox.information(self, "A/B demo",
                                    "Build the default pipeline first.")
            return
        testb = s.add_node("test_points", QPointF(-660, 470),
                           settings={
                               "pump_tag": SECOND_PUMP_POINTS["pump_tag"],
                               "unit": "bar",
                               "rows": [
                                   {"q": _d(p.get("q")), "p_suc": _d(p.get("p_suc")),
                                    "p_dis": _d(p.get("p_dis")), "temp_c": _d(p.get("temp_c")),
                                    "n": _d(p.get("n_rpm")), "power": _d(p.get("power")),
                                    "head": _d(p.get("head")), "eff": _d(p.get("eff"))}
                                   for p in SECOND_PUMP_POINTS["points"]
                               ],
                           })
        corrb = s.add_node("correction", QPointF(-360, 360))
        fitb = s.add_node("curve_fit", QPointF(-90, 360))
        checkb = s.add_node("compliance", QPointF(200, 360))

        self._wire(rated, "RatedPoint", corrb, "RatedPoint")
        self._wire(testb, "TestPointSet", corrb, "TestPointSet")
        self._wire(corrb, "CorrectedCurve", fitb, "CorrectedCurve")
        self._wire(fitb, "FittedModel", checkb, "FittedModel")
        self._wire(rated, "RatedPoint", checkb, "RatedPoint")
        self._wire(corrb, "CorrectedCurve", report, "branch")
        self._wire(fitb, "FittedModel", report, "branch")
        self._wire(checkb, "ComplianceResult", report, "branch")
        self.scene.evaluate()
        self._update_status()

    def _wire(self, up_item, out_name, down_item, in_name) -> None:
        src = up_item.out_ports.get(out_name)
        dst = down_item.in_ports.get(in_name)
        if src and dst:
            self.scene.connect_ports(src, dst)

    def _find(self, kind: str):
        for n in self.scene.nodes:
            if n.logic.kind == kind:
                return n
        return None

    # ------------------------------------------------------- project IO
    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save project", "pipeline.pumpflow",
                                              "PumpFlow (*.pumpflow)")
        if not path:
            return
        write_json(path, self.scene.to_dict())
        self.statusBar().showMessage(f"Saved {path}", 4000)

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "",
                                              "PumpFlow (*.pumpflow);;JSON (*.json)")
        if not path:
            return
        self.scene.load_dict(read_json(path))
        self._reset_view()
        self.statusBar().showMessage(f"Opened {path}", 4000)
        self._update_status()

    # ------------------------------------------------------- data-file IO
    def import_data_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import data file", "", "JSON (*.json)")
        if not path:
            return
        doc = read_json(path)
        rated = rated_from_json(doc)
        tps = testset_from_json(doc)
        rated_node = self._find("rated_point")
        test_node = self._find("test_points")
        if rated_node:
            rated_node.logic.settings.update({
                "tag": rated.tag, "standard": rated.standard,
                "q": rated.q_m3h, "head": rated.head_m, "n": rated.speed_rpm,
                "power": rated.power_kw, "eff": rated.efficiency_pct or 0,
                "head_shutoff": rated.head_shutoff_m or 0,
                "dens_rel": rated.density_rel, "visc": rated.viscosity_cst,
                "unit": rated.pressure_unit, "parallel": rated.parallel_operation,
            })
        if test_node:
            test_node.logic.settings.update({
                "pump_tag": tps.pump_tag, "unit": tps.pressure_unit,
                "rows": [
                    {"q": r.q_m3h, "p_suc": r.p_suction, "p_dis": r.p_discharge,
                     "temp_c": r.temp_c, "n": r.speed_rpm, "power": r.power_kw,
                     "head": r.head_m, "eff": r.efficiency_pct}
                    for r in tps.rows
                ],
            })
        self.scene.evaluate()
        self.statusBar().showMessage(f"Imported {path}", 4000)
        self._update_status()

    def export_data_file(self) -> None:
        rated_node = self._find("rated_point")
        test_node = self._find("test_points")
        if not rated_node:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export data file", "pump_data.json",
                                              "JSON (*.json)")
        if not path:
            return
        rated = rated_node.logic.to_signal()
        tps = test_node.logic.to_signal() if test_node else None
        write_json(path, json_from_signals(rated, tps))
        self.statusBar().showMessage(f"Exported {path}", 4000)

    # ------------------------------------------------------------- status
    def _update_status(self) -> None:
        report = self._find("report_export")
        if report is not None and report.logic.status:
            self.statusBar().showMessage(f"Report Export · {report.logic.status}")


def _d(value):
    from .numfmt import parse_decimal
    return parse_decimal(value, None)


def run() -> int:
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    win = MainWindow()
    win.show()
    return app.exec()
