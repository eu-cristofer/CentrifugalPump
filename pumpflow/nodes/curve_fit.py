"""
nodes.curve_fit — Curve Fit  (UI_SPEC §5.4)

Input ``CorrectedCurve`` → output ``FittedModel``.
Degree-3 polynomial is the API-610 primary; a natural cubic spline is the
optional secondary.  Shows fitted coefficients for H, P, η and an R² summary.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ..binding import fit_model
from .base import BaseNode, PortSpec
from . import ui
from .plotting import build_figure


class CurveFitNode(BaseNode):
    kind = "curve_fit"
    title = "Curve Fit"
    glyph = "∿"
    inputs = [PortSpec("CorrectedCurve", "CorrectedCurve")]
    outputs = [PortSpec("FittedModel", "FittedModel")]

    def default_settings(self) -> Dict:
        return {"degree": 3, "spline": True, "resolution": 160, "show_preview": True}

    def compute(self, inputs) -> Dict[str, object]:
        corrected = self.first(inputs, "CorrectedCurve")
        if corrected is None:
            return self.emit_nothing("Waiting for corrected curve", "idle")
        s = self.settings
        fitted = fit_model(corrected, degree=int(s["degree"]), with_spline=bool(s["spline"]))
        self._last = fitted
        r2h = fitted.r2.get("head")
        r2txt = f" · R²(H)={r2h:.4f}" if r2h is not None else ""
        self.status = f"{fitted.pump_tag} · deg-{fitted.degree}{' +spline' if s['spline'] else ''}{r2txt}"
        self.state = "ok"
        return {"FittedModel": fitted}

    def port_label(self, name: str) -> str:
        return {"CorrectedCurve": "Corrected", "FittedModel": "Model"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent, "Curve Fit",
            "Least-squares polynomial (primary) + natural cubic spline (secondary) "
            "for Head, Power and Efficiency vs. Capacity.",
            width=980,
        )
        banner = ui.Banner()
        from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout
        coeff_lbl = QLabel(objectName="MonoBlock")
        coeff_lbl.setWordWrap(True)
        canvas_holder = {"canvas": None}

        degree = ui.int_spin(int(s["degree"]), 2, 5, None)
        spline = ui.checkbox("Overlay natural cubic spline", s["spline"], None)
        resolution = ui.int_spin(int(s["resolution"]), 40, 400, None)
        show_preview = ui.checkbox("Show preview", s["show_preview"], None)

        # Right pane: the (optional) live chart.
        preview = QWidget()
        pv = QVBoxLayout(preview)
        pv.setContentsMargins(0, 0, 0, 0)
        preview.setMinimumWidth(440)

        def refresh():
            on_change()
            fitted = getattr(self, "_last", None) if self.state == "ok" else None
            if not fitted:
                banner.show_message(self.status, "info")
                coeff_lbl.setText("")
                return
            banner.show_message(
                "  ·  ".join(f"R²({k})={v:.4f}" for k, v in fitted.r2.items()), "ok"
            )
            coeff_lbl.setText(_coeff_text(fitted))
            # Only (re)build the heavy chart when the preview pane is shown.
            if not s["show_preview"]:
                return
            if canvas_holder["canvas"] is not None:
                pv.removeWidget(canvas_holder["canvas"])
                canvas_holder["canvas"].setParent(None)
                canvas_holder["canvas"] = None
            fig = build_figure(fitted, show_spline=bool(s["spline"]),
                               resolution=int(s["resolution"]), compact=True)
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(300)
            pv.addWidget(canvas)
            canvas_holder["canvas"] = canvas

        def toggle_preview(v: bool) -> None:
            s["show_preview"] = bool(v)
            preview.setVisible(bool(v))
            if v:
                refresh()

        degree.valueChanged.connect(lambda v: (s.__setitem__("degree", int(v)), refresh()))
        spline.toggled.connect(lambda v: (s.__setitem__("spline", bool(v)), refresh()))
        resolution.valueChanged.connect(lambda v: (s.__setitem__("resolution", int(v)), refresh()))
        show_preview.toggled.connect(lambda v: toggle_preview(bool(v)))

        # Left column: settings + coefficients + the preview toggle.
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        left.setMinimumWidth(420)
        lv.addWidget(ui.section("Fit settings"))
        lv.addWidget(ui.row("Polynomial degree", degree))
        lv.addWidget(ui.row("", spline))
        lv.addWidget(ui.row("Curve resolution", resolution, "pts"))
        lv.addWidget(banner)
        lv.addWidget(ui.hline())
        lv.addWidget(ui.section("Coefficients (highest order first)"))
        lv.addWidget(coeff_lbl)
        lv.addWidget(show_preview)
        lv.addStretch(1)

        split = QWidget()
        sh = QHBoxLayout(split)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.setSpacing(16)
        sh.addWidget(left, 0)
        sh.addWidget(preview, 1)

        dlg.add(split)
        preview.setVisible(bool(s["show_preview"]))
        refresh()
        dlg.resize(1000, 640)
        return dlg


def _coeff_text(fitted) -> str:
    def fmt_coeffs(name, coeffs):
        if coeffs is None or not len(coeffs):
            return f"{name:>6}:  —"
        return f"{name:>6}:  " + "  ".join(f"{c:+.4e}" for c in np.asarray(coeffs))
    lines = [
        fmt_coeffs("Head", fitted.head_coeffs),
        fmt_coeffs("Power", fitted.power_coeffs),
        fmt_coeffs("Eff", fitted.efficiency_coeffs),
    ]
    return "\n".join(lines)
