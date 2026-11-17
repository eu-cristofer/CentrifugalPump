"""
nodes.performance_plot — Performance Plot  (UI_SPEC §5.5)

Inputs ``FittedModel`` (+ ``RatedPoint`` for the marker) → optional ``image/png``.
Three stacked shared-x charts Q×H / Q×P / Q×η with corrected points, the
polynomial, the spline (dashed) and a crosshair at the rated capacity.

Optional y-axis limits are entered per chart in a chosen display unit
(``head_ylim_unit`` / ``power_ylim_unit`` / ``eff_ylim_unit``); they are
converted to the canonical m / kW / % only when plotting.
"""

from __future__ import annotations

import io
from typing import Dict, Optional

from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from .. import units
from .base import BaseNode, PortSpec
from . import ui
from .plotting import build_figure

# (plot key, units dimension, settings key, unit settings key, default [lo, hi] in canonical units)
_YLIMS = (
    ("head", "head", "head_ylim", "head_ylim_unit", (0.0, 100.0)),
    ("power", "power", "power_ylim", "power_ylim_unit", (0.0, 500.0)),
    ("efficiency", "efficiency", "eff_ylim", "eff_ylim_unit", (0.0, 100.0)),
)


class PerformancePlotNode(BaseNode):
    kind = "performance_plot"
    title = "Performance Plot"
    glyph = "⊞"
    inputs = [PortSpec("FittedModel", "FittedModel"), PortSpec("RatedPoint", "RatedPoint")]
    outputs = [PortSpec("image", "*")]

    def default_settings(self) -> Dict:
        p = units.PREFS
        return {
            "show_poly": True, "show_spline": True, "show_points": True,
            "head_ylim": None, "power_ylim": None, "eff_ylim": None,
            "head_ylim_unit": p.default_unit("head"),
            "power_ylim_unit": p.default_unit("power"),
            "eff_ylim_unit": p.default_unit("efficiency"),
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
        """Y-limits converted from their display unit to canonical m / kW / %."""
        s = self.settings
        out = {}
        for key, dim, skey, ukey, _default in _YLIMS:
            lim = s.get(skey)
            if not lim:
                out[key] = None
                continue
            unit = s.get(ukey) or units.canonical_unit(dim)
            canon = units.canonical_unit(dim)
            lo, hi = (
                units.convert_display(float(v), dim, unit, canon) for v in lim
            )
            out[key] = (lo, hi) if lo < hi else None
        return out

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
            width=980,
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

        # Two columns: parameters on the left, the plot on the right.
        settings_panel = QW()
        settings_panel.setObjectName("PlotSettings")
        left = QVBoxLayout(settings_panel)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(10)
        settings_panel.setMinimumWidth(340)
        settings_panel.setMaximumWidth(420)

        toolbar = QW()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(0, 0, 0, 0)
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

        # ---- optional y-axis limits: "auto" checkbox + lo/hi UnitFields ----
        def ylim_editor(title, dim, skey, ukey, default_canon):
            cur = s.get(skey)
            unit = s.get(ukey) or units.PREFS.default_unit(dim)
            s[ukey] = unit
            canon = units.canonical_unit(dim)
            if cur:
                lo0, hi0 = float(cur[0]), float(cur[1])
            else:
                lo0, hi0 = (
                    units.convert_display(v, dim, canon, unit) for v in default_canon
                )
            auto = ui.checkbox("auto", cur is None, None)
            guard = {"busy": False}
            lo_f = ui.UnitField(dim, lo0, unit, on_change=lambda: changed(lo_f),
                                lo=-1e6, hi=1e6, step=1, decimals=3)
            hi_f = ui.UnitField(dim, hi0, unit, on_change=lambda: changed(hi_f),
                                lo=-1e6, hi=1e6, step=1, decimals=3)

            def changed(src):
                if guard["busy"]:
                    return
                other = hi_f if src is lo_f else lo_f
                guard["busy"] = True
                try:
                    if other.unit_label() != src.unit_label():
                        i = other.combo.findData(src.unit_label())
                        if i >= 0:
                            other.combo.setCurrentIndex(i)
                finally:
                    guard["busy"] = False
                manual = not auto.isChecked()
                for f in (lo_f, hi_f):
                    f.spin.setEnabled(manual)
                    f.combo.setEnabled(manual)
                s[ukey] = src.unit_label()
                s[skey] = [lo_f.magnitude(), hi_f.magnitude()] if manual else None
                redraw()

            auto.toggled.connect(lambda _=None: changed(lo_f))
            for f in (lo_f, hi_f):
                f.spin.setEnabled(cur is not None)
                f.combo.setEnabled(cur is not None)
            left.addWidget(ui.row(title, auto))
            left.addWidget(lo_f.row("   min"))
            left.addWidget(hi_f.row("   max"))

        tl.addStretch(1)
        left.addWidget(ui.section("Curves"))
        left.addWidget(poly)
        left.addWidget(spline)
        left.addWidget(points)
        left.addWidget(ui.hline())
        left.addWidget(ui.section("Y-axis limits"))
        for _key, dim, skey, ukey, default_canon in _YLIMS:
            ylim_editor({"head": "Head", "power": "Power", "efficiency": "Efficiency η"}[_key],
                        dim, skey, ukey, default_canon)
        left.addWidget(ui.hline())
        left.addWidget(toolbar)
        left.addWidget(banner)
        left.addStretch(1)

        columns = QW()
        cl = QHBoxLayout(columns)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(16)
        cl.addWidget(settings_panel)
        cl.addWidget(plot_area, 1)
        dlg.add(columns)
        redraw()
        dlg.resize(1180, 760)
        return dlg
