"""
nodes.explore_plot — Performance Explorer

An *interactive* exploratory chart (pyqtgraph) — three vertically stacked,
X-linked plots Q×H / Q×P / Q×η with live pan/zoom, a mouse crosshair readout and
a legend.  Unlike the static :mod:`~pumpflow.nodes.performance_plot` (a matplotlib
PNG for the report), this node is for *exploration*: drop points, wire a couple of
branches, and poke at the curves.

It re-implements **no** physics — measured rows are reduced to Q/H/η via the
existing :mod:`pumpflow.binding` helpers, and fitted curves are merely *sampled*
(``np.polyval`` / spline ``sample``) for drawing.

Inputs (all optional, all fan-in):
  - ``Points``         — :class:`PointSample` overlays (Point nodes)
  - ``TestPointSet``   — measured scatter
  - ``CorrectedCurve`` — speed/affinity-corrected points (triangle scatter)
  - ``FittedModel``    — fitted polynomial (+ spline) curve overlays
  - ``RatedPoint``     — rated-capacity crosshair marker
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
from PySide6.QtCore import Qt

from ..binding import row_efficiency_pct, row_head_m
from .base import BaseNode, PortSpec
from . import ui

# A small, colour-blind-friendly cycle keyed per dataset/branch.
_PALETTE = ["#2f6fb0", "#b4413c", "#2e7d5b", "#8a5a9e", "#c98a1b", "#3b8a8a"]


class ExploreChartNode(BaseNode):
    kind = "explore_plot"
    title = "Performance Explorer"
    glyph = "◉"
    inputs = [
        PortSpec("Points", "PointSample", multi=True),
        PortSpec("TestPointSet", "TestPointSet", multi=True),
        PortSpec("CorrectedCurve", "CorrectedCurve", multi=True),
        PortSpec("FittedModel", "FittedModel", multi=True),
        PortSpec("RatedPoint", "RatedPoint"),
    ]
    outputs = []

    def compute(self, inputs) -> Dict[str, object]:
        self._points = self.all_of(inputs, "Points")
        self._testsets = self.all_of(inputs, "TestPointSet")
        self._corrected = self.all_of(inputs, "CorrectedCurve")
        self._models = self.all_of(inputs, "FittedModel")
        self._rated = self.first(inputs, "RatedPoint")
        n_pts = len(self._points)
        n_scatter = sum(len(t.rows) for t in self._testsets)
        n_corr = sum(len(c.before_after) for c in self._corrected)
        n_curves = len(self._models)
        if not (n_pts or n_scatter or n_corr or n_curves):
            return self.emit_nothing(
                "Wire points, a test set, a corrected curve, or a fitted model", "idle"
            )
        self.status = f"{n_pts} pts · {n_scatter} measured · {n_corr} corrected · {n_curves} curves"
        self.state = "ok"
        return {}

    def port_label(self, name: str) -> str:
        return {
            "Points": "Points",
            "TestPointSet": "Tests",
            "CorrectedCurve": "Corrected",
            "FittedModel": "Models",
            "RatedPoint": "Rated",
        }.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        dlg = ui.PropertyDialog(
            parent,
            "Performance Explorer",
            "Interactive Q×H / Q×P / Q×η — pan, zoom and hover. "
            "Measured points, fitted curves and ad-hoc Point markers.",
            width=720,
        )
        banner = ui.Banner()

        try:
            import pyqtgraph as pg
        except ImportError:
            banner.show_message(
                "pyqtgraph is not installed — run  pip install pyqtgraph  to use "
                "the Performance Explorer.",
                "error",
            )
            dlg.add(banner)
            dlg.resize(560, 200)
            return dlg

        on_change()  # ensure caches reflect the latest upstream state

        pg.setConfigOptions(antialias=True, background="w", foreground="#33414f")
        glw = pg.GraphicsLayoutWidget()
        glw.setMinimumHeight(560)

        p_h = glw.addPlot(row=0, col=0)
        p_p = glw.addPlot(row=1, col=0)
        p_e = glw.addPlot(row=2, col=0)
        for ax, ylabel in (
            (p_h, "Head (m)"),
            (p_p, "Power (kW)"),
            (p_e, "Efficiency (%)"),
        ):
            ax.showGrid(x=True, y=True, alpha=0.25)
            ax.setLabel("left", ylabel)
            ax.addLegend(offset=(-10, 10), labelTextSize="7pt")
        p_e.setLabel("bottom", "Capacity  Q (m³/h)")
        p_p.setXLink(p_h)
        p_e.setXLink(p_h)

        self._plot_all(pg, p_h, p_p, p_e)
        self._add_crosshair(pg, glw, (p_h, p_p, p_e))
        self._align_y_axes(p_h, p_p, p_e)

        # -- export -------------------------------------------------------
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget, QFileDialog

        toolbar = QWidget()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addStretch(1)
        export = QPushButton("Export PNG…")
        export.setObjectName("ToolButton")

        def do_export():
            from pyqtgraph.exporters import ImageExporter

            path, _ = QFileDialog.getSaveFileName(
                dlg, "Export chart PNG", "performance_explorer.png", "PNG (*.png)"
            )
            if path:
                exporter = ImageExporter(glw.scene())
                exporter.export(path)

        export.clicked.connect(do_export)
        tl.addWidget(export)

        dlg.add(toolbar)
        dlg.add(glw)
        dlg.add(self._build_readout(pg, dlg, (p_h, p_p, p_e)))
        dlg.add(banner)
        dlg.resize(760, 820)
        return dlg

    # -- y-axis alignment --------------------------------------------------
    def _align_y_axes(self, *plots) -> None:
        """Pin every left axis to the widest one so the plot frames (and the
        shared capacity axis) line up in a single vertical column."""
        axes = [p.getAxis("left") for p in plots]
        w = max((a.width() for a in axes), default=0)
        for a in axes:
            a.setWidth(w)

    # -- flow readout (regression values at a chosen Q) --------------------
    def _build_readout(self, pg, dlg, panes):
        """A capacity spin-box + a table of the values each fitted polynomial
        regression predicts at that Q (one row per wired Curve Fit), with a
        dashed Q-marker on all three panes."""
        from PySide6.QtWidgets import (
            QDoubleSpinBox,
            QHeaderView,
            QLabel,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
            QHBoxLayout,
        )
        from PySide6.QtGui import QColor
        from ..numfmt import fmt

        models = list(getattr(self, "_models", []))

        # capacity span across all fitted curves → spin default + range
        spans = []
        for m in models:
            c = np.asarray(m.curve.fitter.capacities, dtype=float)
            if c.size:
                spans.append((float(c.min()), float(c.max())))
        cmin = min((s[0] for s in spans), default=0.0)
        cmax = max((s[1] for s in spans), default=100.0)
        rated = getattr(self, "_rated", None)
        default_q = rated.q_m3h if rated is not None else (cmin + cmax) / 2.0

        # dashed Q-marker on every pane (moves with the spin)
        qlines = []
        for p in panes:
            ln = pg.InfiniteLine(
                pos=default_q,
                angle=90,
                pen=pg.mkPen("#b4413c", style=Qt.DashLine, width=1),
            )
            p.addItem(ln, ignoreBounds=True)
            qlines.append(ln)

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 6, 0, 0)

        ctrl = QWidget()
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(QLabel("Readout flow Q"))
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 1.0e5)
        spin.setDecimals(1)
        spin.setSingleStep(1.0)
        spin.setValue(float(default_q))
        spin.setSuffix("  m³/h")
        cl.addWidget(spin)
        cl.addStretch(1)
        lay.addWidget(ctrl)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            ["Curve", "Q [m³/h]", "Head [m]", "Power [kW]", "η [%]"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setObjectName("ReadGrid")
        table.setMaximumHeight(180)
        lay.addWidget(table)

        def model_label(m) -> str:
            try:
                rpm = float(m.curve.points[0].speed_of_rotation.to("rpm").magnitude)
                return f"{m.pump_tag} @ {rpm:g} rpm"
            except Exception:
                return m.pump_tag

        def recompute(q: float) -> None:
            for ln in qlines:
                ln.setPos(q)
            table.setRowCount(0)
            if not models:
                table.insertRow(0)
                item = QTableWidgetItem("Wire a Curve Fit to read regression values")
                item.setForeground(QColor("#8a96a3"))
                table.setItem(0, 0, item)
                table.setSpan(0, 0, 1, 5)
                return
            for i, m in enumerate(models):
                color = _PALETTE[i % len(_PALETTE)]
                head = (
                    float(np.polyval(m.head_coeffs, q))
                    if m.head_coeffs is not None and len(m.head_coeffs)
                    else None
                )
                power = (
                    float(np.polyval(m.power_coeffs, q))
                    if m.power_coeffs is not None and len(m.power_coeffs)
                    else None
                )
                eff = (
                    float(np.polyval(m.efficiency_coeffs, q))
                    if m.efficiency_coeffs is not None and len(m.efficiency_coeffs)
                    else None
                )
                r = table.rowCount()
                table.insertRow(r)
                cells = [
                    model_label(m),
                    fmt(q),
                    fmt(head) if head is not None else "—",
                    fmt(power) if power is not None else "—",
                    fmt(eff, 1) if eff is not None else "—",
                ]
                for c, v in enumerate(cells):
                    cell = QTableWidgetItem(str(v))
                    if c == 0:
                        cell.setForeground(QColor(color))
                    table.setItem(r, c, cell)

        spin.valueChanged.connect(recompute)
        recompute(float(default_q))
        return container

    # -- drawing helpers ---------------------------------------------------
    def _plot_all(self, pg, p_h, p_p, p_e) -> None:
        # fitted-curve overlays (polynomial + optional spline)
        for i, m in enumerate(getattr(self, "_models", [])):
            color = _PALETTE[i % len(_PALETTE)]
            caps = np.asarray(m.curve.fitter.capacities, dtype=float)
            if caps.size == 0:
                continue
            xs = np.linspace(float(caps.min()), float(caps.max()), 160)
            pen = pg.mkPen(color, width=2)
            self._curve(
                pg,
                p_h,
                xs,
                m.head_coeffs,
                m.head_spline,
                pen,
                color,
                f"{m.pump_tag} fit",
            )
            self._curve(pg, p_p, xs, m.power_coeffs, m.power_spline, pen, color, None)
            self._curve(
                pg, p_e, xs, m.efficiency_coeffs, m.efficiency_spline, pen, color, None
            )

        # measured scatter (head/η derived via binding — no physics here)
        for i, tps in enumerate(getattr(self, "_testsets", [])):
            color = _PALETTE[i % len(_PALETTE)]
            q, h, p, e = [], [], [], []
            test_rho = getattr(tps, "test_density_kgm3", None)
            for r in tps.rows:
                head = row_head_m(r, tps.pressure_unit, test_rho)
                q.append(r.q_m3h)
                h.append(head)
                p.append(r.power_kw)
                eff = row_efficiency_pct(r, head, test_rho)
                e.append(eff if eff is not None else np.nan)
            self._scatter(pg, p_h, q, h, color, "o", f"{tps.pump_tag} data")
            self._scatter(pg, p_p, q, p, color, "o", None)
            self._scatter(pg, p_e, q, e, color, "o", None)

        # corrected points (triangles) — read straight off the before/after rows
        # so the Explorer touches no pump objects (physics stays in binding).
        # Drawn as discrete markers ONLY (``_scatter`` uses ``pen=None``): the
        # corrected input is never joined by a line — any line you see through
        # them is the coincident fitted curve from a wired Curve Fit.
        base = len(getattr(self, "_testsets", []))
        for i, cc in enumerate(getattr(self, "_corrected", [])):
            color = _PALETTE[(base + i) % len(_PALETTE)]
            rows = [d["corrected"] for d in cc.before_after]
            q = [r["q"] for r in rows]
            h = [r["head"] for r in rows]
            p = [r["power"] if r["power"] is not None else np.nan for r in rows]
            e = [r["eff"] if r["eff"] is not None else np.nan for r in rows]
            name = f"{cc.pump_tag} @ {cc.target_speed_rpm:g} rpm"
            self._scatter(pg, p_h, q, h, color, "t", name)
            self._scatter(pg, p_p, q, p, color, "t", None)
            self._scatter(pg, p_e, q, e, color, "t", None)

        # ad-hoc Point markers (drawn large + labelled)
        for pt in getattr(self, "_points", []):
            self._marker(pg, p_h, pt.q_m3h, pt.head_m, pt.label)
            self._marker(pg, p_p, pt.q_m3h, pt.power_kw, None)
            self._marker(pg, p_e, pt.q_m3h, pt.efficiency_pct, None)

        # rated-capacity crosshair on every pane
        rated = getattr(self, "_rated", None)
        if rated is not None:
            for ax in (p_h, p_p, p_e):
                ax.addItem(
                    pg.InfiniteLine(
                        pos=rated.q_m3h,
                        angle=90,
                        pen=pg.mkPen("#33414f", style=Qt.DashLine, width=1),
                    )
                )

    def _curve(self, pg, ax, xs, coeffs, spline, pen, color, name) -> None:
        if coeffs is not None and len(coeffs):
            ax.plot(xs, np.polyval(coeffs, xs), pen=pen, name=name)
        if spline is not None:
            sx, sy = spline.sample(160)
            ax.plot(sx, sy, pen=pg.mkPen(color, width=1, style=Qt.DashLine))

    def _scatter(self, pg, ax, x, y, color, symbol, name) -> None:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        mask = ~np.isnan(y)
        ax.plot(
            x[mask],
            y[mask],
            pen=None,
            symbol=symbol,
            symbolSize=8,
            symbolBrush=color,
            symbolPen=color,
            name=name,
        )

    def _marker(self, pg, ax, x, y, label) -> None:
        if y is None:
            return
        ax.plot(
            [x],
            [y],
            pen=None,
            symbol="star",
            symbolSize=16,
            symbolBrush="#c98a1b",
            symbolPen="#7a5510",
        )
        if label:
            text = pg.TextItem(label, color="#7a5510", anchor=(0, 1))
            text.setPos(x, y)
            ax.addItem(text)

    def _add_crosshair(self, pg, glw, axes) -> None:
        """A vertical guide + value label that follows the cursor across panes."""
        vlines = []
        for ax in axes:
            vl = pg.InfiniteLine(
                angle=90, movable=False, pen=pg.mkPen("#9aa6b2", width=1)
            )
            ax.addItem(vl, ignoreBounds=True)
            vlines.append(vl)
        label = pg.TextItem("", color="#33414f", anchor=(0, 1))
        axes[0].addItem(label, ignoreBounds=True)

        def on_move(evt):
            pos = evt[0]
            p_h = axes[0]
            if not p_h.sceneBoundingRect().contains(pos):
                for ax in axes:
                    if not ax.sceneBoundingRect().contains(pos):
                        continue
            for ax in axes:
                if ax.sceneBoundingRect().contains(pos):
                    mp = ax.vb.mapSceneToView(pos)
                    for vl in vlines:
                        vl.setPos(mp.x())
                    label.setText(f"Q = {mp.x():.1f}")
                    yr = axes[0].vb.viewRange()[1]
                    label.setPos(mp.x(), yr[1])
                    break

        # keep a reference so the proxy is not garbage-collected
        self._mouse_proxy = pg.SignalProxy(
            glw.scene().sigMouseMoved, rateLimit=60, slot=on_move
        )
