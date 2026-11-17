"""
nodes.performance_plot — Performance Plot  (UI_SPEC §5.5)

Inputs ``FittedModel`` (+ ``RatedPoint`` for the marker, + optional
``NPSHResult``) → optional ``image/png``.  Stacked shared-x charts Q×H / Q×P /
Q×η, plus Q×NPSHr when an NPSH node is wired in, with corrected points, the
polynomial, the spline (dashed) and a crosshair at the rated capacity.

The dialog is interactive: a zoom / pan / home toolbar, and a hover cursor
that reads the fitted H, P, η and NPSHr at the pointer's flow.

Optional y-axis limits are entered per chart in a chosen display unit
(``head_ylim_unit`` / ``power_ylim_unit`` / ``eff_ylim_unit`` /
``npsh_ylim_unit``); they are converted to the canonical m / kW / % only when
plotting.  While a chart is on "auto" its fields show the limits actually in
use (calculated, or as zoomed), so unticking "auto" starts from them.
``npsh_ylim`` is stored only when set.
"""

from __future__ import annotations

import io
from typing import Dict, Optional

from PySide6.QtWidgets import QFileDialog, QLabel, QSizePolicy, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from .. import units
from .base import BaseNode, PortSpec
from . import ui
from .plotting import build_figure

# (plot key, units dimension, settings key, unit settings key, default [lo, hi] in canonical units)
_YLIMS = (
    ("head", "head", "head_ylim", "head_ylim_unit", (0.0, 100.0)),
    ("power", "power", "power_ylim", "power_ylim_unit", (0.0, 500.0)),
    ("efficiency", "efficiency", "eff_ylim", "eff_ylim_unit", (0.0, 100.0)),
    ("npsh", "npsh", "npsh_ylim", "npsh_ylim_unit", (0.0, 10.0)),
)
_TITLES = {"head": "Head", "power": "Power", "efficiency": "Efficiency η", "npsh": "NPSHr"}
_CANON = {"head": "m", "power": "kW", "efficiency": "%", "npsh": "m"}


class PerformancePlotNode(BaseNode):
    kind = "performance_plot"
    title = "Performance Plot"
    glyph = "⊞"
    inputs = [
        PortSpec("FittedModel", "FittedModel"),
        PortSpec("RatedPoint", "RatedPoint"),
        PortSpec("NPSHResult", "NPSHResult"),
    ]
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
        self._npsh = self.first(inputs, "NPSHResult")
        extras = (" · rated marked" if rated else "") + (
            " · NPSH" if self._npsh is not None else ""
        )
        self.status = f"{fitted.pump_tag} · plotted{extras}"
        self.state = "ok"
        png = self._render_png()
        return {"image": png}

    def port_label(self, name: str) -> str:
        return {
            "FittedModel": "Model",
            "RatedPoint": "Rated",
            "NPSHResult": "NPSH",
            "image": "PNG",
        }.get(name, name)

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
            npsh=getattr(self, "_npsh", None),
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
            maximizable=True,
        )
        banner = ui.Banner()
        holder = {"canvas": None}

        plot_area = QWidget()
        pv = QVBoxLayout(plot_area)
        pv.setContentsMargins(0, 0, 0, 0)

        poly = ui.checkbox("Polynomial curve", s["show_poly"], None)
        spline = ui.checkbox("Spline (dashed)", s["show_spline"], None)
        points = ui.checkbox("Data points", s["show_points"], None)

        readout = QLabel("Hover over the plot to read the fitted values.")
        readout.setObjectName("Hint")
        readout.setWordWrap(True)
        editors: dict = {}  # key -> (auto checkbox, lo field, hi field, dimension)

        def show_axis_limits():
            """Put the limits in use into the fields of every chart on auto."""
            fig = holder.get("fig")
            axes = getattr(fig, "pump_axes", {}) if fig is not None else {}
            for key, (auto, lo_f, hi_f, dim) in editors.items():
                ax = axes.get(key)
                if ax is None or not auto.isChecked():
                    continue
                lo, hi = ax.get_ylim()
                unit = lo_f.unit_label()
                for f, v in ((lo_f, lo), (hi_f, hi)):
                    f.spin.blockSignals(True)
                    f.spin.setValue(
                        units.convert_display(v, dim, units.canonical_unit(dim), unit)
                    )
                    f.spin.blockSignals(False)

        def on_move(event):
            fig = holder.get("fig")
            if fig is None:
                return
            cursors = holder.get("cursors") or []
            if event.inaxes is None or event.xdata is None:
                for c in cursors:
                    c.set_visible(False)
                holder["canvas"].draw_idle()
                return
            q = float(event.xdata)
            for c in cursors:
                c.set_xdata([q, q])
                c.set_visible(True)
            values = fig.pump_readout(q)
            parts = [f"Q = {q:.2f} m³/h"]
            for key in ("head", "power", "efficiency", "npsh"):
                if key in values:
                    name = {"head": "H", "power": "P", "efficiency": "η",
                            "npsh": "NPSHr"}[key]
                    parts.append(f"{name} = {values[key]:.2f} {_CANON[key]}")
            if len(parts) == 1:
                parts.append("outside the tested range")
            readout.setText("   ·   ".join(parts))
            holder["canvas"].draw_idle()

        def redraw():
            on_change()
            fitted = getattr(self, "_fitted", None) if self.state == "ok" else None
            if not fitted:
                banner.show_message(self.status, "info")
                return
            banner.show_message("", "info")
            for w in ("canvas", "nav"):
                if holder.get(w) is not None:
                    pv.removeWidget(holder[w])
                    holder[w].setParent(None)
            fig = build_figure(
                fitted, rated=getattr(self, "_rated", None),
                show_poly=s["show_poly"], show_spline=s["show_spline"],
                show_points=s["show_points"], ylims=self._ylims(),
                npsh=getattr(self, "_npsh", None),
            )
            # Fit the window rather than the figure's print size; the canvas
            # then follows the dialog when it is resized.
            fig.set_size_inches(6.6, 6.4 if "npsh" in fig.pump_axes else 5.6)
            fig.tight_layout(pad=0.9)
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(420)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            canvas.mpl_connect("resize_event", lambda _e: fig.tight_layout(pad=0.9))
            nav = NavigationToolbar(canvas, plot_area)
            pv.insertWidget(0, nav)  # toolbar, readout, plot
            pv.insertWidget(2, canvas, 1)
            holder.update(canvas=canvas, nav=nav, fig=fig)
            holder["cursors"] = [
                ax.axvline(0.0, color="#33414f", lw=0.8, alpha=0.6, visible=False)
                for ax in fig.pump_axes.values()
            ]
            canvas.mpl_connect("motion_notify_event", on_move)
            # Zoom / pan from the toolbar updates the fields of charts on auto.
            for ax in fig.pump_axes.values():
                ax.callbacks.connect("ylim_changed", lambda _ax: show_axis_limits())
            show_axis_limits()

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
        def ylim_editor(key, title, dim, skey, ukey, default_canon):
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
                if manual:
                    s[skey] = [lo_f.magnitude(), hi_f.magnitude()]
                elif skey in self.default_settings():
                    s[skey] = None
                else:  # optional limit (NPSH): stored only when set
                    s.pop(skey, None)
                redraw()

            auto.toggled.connect(lambda _=None: changed(lo_f))
            editors[key] = (auto, lo_f, hi_f, dim)
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
        for key, dim, skey, ukey, default_canon in _YLIMS:
            ylim_editor(key, _TITLES[key], dim, skey, ukey, default_canon)
        limits_hint = QLabel(
            "On auto the fields show the limits in use (calculated or zoomed); "
            "untick auto to start from them."
        )
        limits_hint.setObjectName("Hint")
        limits_hint.setWordWrap(True)
        left.addWidget(limits_hint)
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
        pv.addWidget(readout)  # above the plot once the toolbar is inserted
        dlg.add(columns)
        redraw()
        dlg.resize(1180, 760)
        return dlg
