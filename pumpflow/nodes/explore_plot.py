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
  - ``Points``       — :class:`PointSample` overlays (Point nodes)
  - ``TestPointSet`` — measured scatter
  - ``FittedModel``  — fitted polynomial (+ spline) curve overlays
  - ``RatedPoint``   — rated-capacity crosshair marker
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
        PortSpec("FittedModel", "FittedModel", multi=True),
        PortSpec("RatedPoint", "RatedPoint"),
    ]
    outputs = []

    def compute(self, inputs) -> Dict[str, object]:
        self._points = self.all_of(inputs, "Points")
        self._testsets = self.all_of(inputs, "TestPointSet")
        self._models = self.all_of(inputs, "FittedModel")
        self._rated = self.first(inputs, "RatedPoint")
        n_pts = len(self._points)
        n_scatter = sum(len(t.rows) for t in self._testsets)
        n_curves = len(self._models)
        if not (n_pts or n_scatter or n_curves):
            return self.emit_nothing(
                "Wire points, a test set, or a fitted model", "idle"
            )
        self.status = f"{n_pts} pts · {n_scatter} measured · {n_curves} curves"
        self.state = "ok"
        return {}

    def port_label(self, name: str) -> str:
        return {
            "Points": "Points",
            "TestPointSet": "Tests",
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
        dlg.add(banner)
        dlg.resize(760, 720)
        return dlg

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
            for r in tps.rows:
                head = row_head_m(r, tps.pressure_unit)
                q.append(r.q_m3h)
                h.append(head)
                p.append(r.power_kw)
                eff = row_efficiency_pct(r, head)
                e.append(eff if eff is not None else np.nan)
            self._scatter(pg, p_h, q, h, color, "o", f"{tps.pump_tag} data")
            self._scatter(pg, p_p, q, p, color, "o", None)
            self._scatter(pg, p_e, q, e, color, "o", None)

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
