"""
nodes.performance_plot — Performance Plot  (UI_SPEC §5.5)

Inputs ``FittedModel`` (+ ``RatedPoint`` for the marker) → optional ``image/png``.
Three stacked shared-x charts Q×H / Q×P / Q×η with corrected points, the
polynomial, the spline (dashed) and a crosshair at the rated capacity.
"""

from __future__ import annotations

import io
from typing import Dict, Optional

from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from .base import BaseNode, PortSpec
from . import ui
from .plotting import build_figure


class PerformancePlotNode(BaseNode):
    kind = "performance_plot"
    title = "Performance Plot"
    glyph = "⊞"
    inputs = [PortSpec("FittedModel", "FittedModel"), PortSpec("RatedPoint", "RatedPoint")]
    outputs = [PortSpec("image", "*")]

    def default_settings(self) -> Dict:
        return {
            "show_poly": True, "show_spline": True, "show_points": True,
            "head_ylim": None, "power_ylim": None, "eff_ylim": None,
        }

    def compute(self, inputs) -> Dict[str, object]:
        fitted = self.first(inputs, "FittedModel")
        rated = self.first(inputs, "RatedPoint")
        if fitted is None:
            return self.emit_nothing("Waiting for fitted model", "idle")
        self._fitted = fitted
        self._rated = rated
        self.status = f"{fitted.pump_tag} · plotted{' · rated marked' if rated else ''}"
        self.state = "ok"
        png = self._render_png()
        return {"image": png}

    def port_label(self, name: str) -> str:
        return {"FittedModel": "Model", "RatedPoint": "Rated", "image": "PNG"}.get(name, name)

    def _ylims(self) -> dict:
        s = self.settings
        return {"head": s["head_ylim"], "power": s["power_ylim"], "efficiency": s["eff_ylim"]}

    def _render_png(self) -> Optional[io.BytesIO]:
        fitted = getattr(self, "_fitted", None)
        if fitted is None:
            return None
        s = self.settings
        fig = build_figure(
            fitted, rated=getattr(self, "_rated", None),
            show_poly=s["show_poly"], show_spline=s["show_spline"],
            show_points=s["show_points"], ylims=self._ylims(),
        )
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        return buf

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "Performance Plot",
            "Q×H, Q×P, Q×η — polynomial, spline and the rated point.",
            width=680,
        )
        banner = ui.Banner()
        holder = {"canvas": None}

        plot_area = QWidget()
        pv = QVBoxLayout(plot_area)
        pv.setContentsMargins(0, 0, 0, 0)

        poly = ui.checkbox("Polynomial curve", s["show_poly"], None)
        spline = ui.checkbox("Spline (dashed)", s["show_spline"], None)
        points = ui.checkbox("Data points", s["show_points"], None)

        def redraw():
            on_change()
            fitted = getattr(self, "_fitted", None) if self.state == "ok" else None
            if not fitted:
                banner.show_message(self.status, "info")
                return
            banner.show_message("", "info")
            if holder["canvas"] is not None:
                pv.removeWidget(holder["canvas"])
                holder["canvas"].setParent(None)
            fig = build_figure(
                fitted, rated=getattr(self, "_rated", None),
                show_poly=s["show_poly"], show_spline=s["show_spline"],
                show_points=s["show_points"], ylims=self._ylims(),
            )
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(420)
            pv.addWidget(canvas)
            holder["canvas"] = canvas

        poly.toggled.connect(lambda v: (s.__setitem__("show_poly", bool(v)), redraw()))
        spline.toggled.connect(lambda v: (s.__setitem__("show_spline", bool(v)), redraw()))
        points.toggled.connect(lambda v: (s.__setitem__("show_points", bool(v)), redraw()))

        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget as QW
        toolbar = QW()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(poly)
        tl.addWidget(spline)
        tl.addWidget(points)
        tl.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.setObjectName("ToolButton")
        # Re-pull the latest upstream model and redraw — useful while this
        # modeless window stays open and upstream nodes are edited.
        refresh.clicked.connect(lambda: redraw())
        tl.addWidget(refresh)
        export = QPushButton("Export PNG…")
        export.setObjectName("ToolButton")

        def do_export():
            png = self._render_png()
            if png is None:
                return
            path, _ = QFileDialog.getSaveFileName(dlg, "Export plot PNG",
                                                  f"{self._fitted.pump_tag}_curve.png", "PNG (*.png)")
            if path:
                with open(path, "wb") as fh:
                    fh.write(png.getvalue())

        export.clicked.connect(do_export)
        tl.addWidget(export)

        dlg.add(toolbar)
        dlg.add(plot_area)
        dlg.add(banner)
        redraw()
        dlg.resize(720, 760)
        return dlg
