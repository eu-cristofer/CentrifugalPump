"""
nodes.operating_point — Operating Point  (sprint 11 / UC-04)

Inputs ``FittedModel`` + ``SystemCurveSpec`` → outputs an
``OperatingPointResult``: the intersection of the fitted pump head curve with the
system curve (polynomial fit, or natural cubic spline), flagged when it lies
outside the tested capacity range.  All physics is in :mod:`pump` via
:mod:`pumpflow.binding`.
"""

from __future__ import annotations

from typing import Dict

from ..binding import BindingError
from ..binding import solve_operating_point
from .base import BaseNode, PortSpec


class OperatingPointNode(BaseNode):
    kind = "operating_point"
    title = "Operating Point"
    glyph = "✕"
    inputs = [
        PortSpec("FittedModel", "FittedModel"),
        PortSpec("SystemCurveSpec", "SystemCurveSpec"),
    ]
    outputs = [PortSpec("OperatingPointResult", "OperatingPointResult")]

    def default_settings(self) -> Dict:
        return {"method": "poly", "q_max_factor": 1.5}

    def compute(self, inputs) -> Dict[str, object]:
        self._last = None
        fitted = self.first(inputs, "FittedModel")
        spec = self.first(inputs, "SystemCurveSpec")
        if fitted is None:
            return self.emit_nothing("Waiting for a fitted model", "idle")
        if spec is None:
            return self.emit_nothing("Waiting for a system curve", "idle")
        s = self.settings
        try:
            result = solve_operating_point(
                fitted,
                spec,
                method=s.get("method", "poly"),
                q_max_factor=float(s.get("q_max_factor", 1.5)),
            )
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")
        pt = result.point
        text = (
            f"Q {float(pt.q.to('m**3/h').magnitude):.1f} m³/h · "
            f"H {float(pt.h.to('m').magnitude):.1f} m"
        )
        if pt.efficiency is not None:
            text += f" · η {float(pt.efficiency.to('percent').magnitude):.1f} %"
        if pt.extrapolated:
            text += " · extrapolated"
        self._last = result
        self.status = text
        self.state = "ok"
        return {"OperatingPointResult": result}

    def port_label(self, name: str) -> str:
        return {
            "FittedModel": "Model",
            "SystemCurveSpec": "System",
            "OperatingPointResult": "Op. point",
        }.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        from PySide6.QtWidgets import QLabel

        from . import ui

        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Operating Point",
            "Intersection of the fitted pump head curve with the system curve. "
            "A solution outside the tested capacity range is flagged as extrapolated.",
            width=520,
            maximizable=True,
        )
        banner = ui.Banner()
        method = ui.combo(
            [("Polynomial fit", "poly"), ("Natural cubic spline", "spline")],
            s.get("method", "poly"),
            None,
        )
        factor = ui.spin(float(s.get("q_max_factor", 1.5)), 1.0, 10.0, 0.1, 2, None)
        info = QLabel("—")
        info.setWordWrap(True)

        def refresh():
            on_change()
            if self.state == "ok":
                info.setText(self.status)
                pt = self._last.point
                if pt.extrapolated:
                    banner.show_message(
                        "⚠ Operating point is outside the tested capacity range.",
                        "warn",
                    )
                else:
                    banner.show_message("", "info")
            else:
                info.setText("—")
                banner.show_message(
                    "" if self.state == "idle" else self.status,
                    "info" if self.state == "idle" else "error",
                )

        method.currentIndexChanged.connect(
            lambda _=None: (s.__setitem__("method", method.currentData()), refresh())
        )
        factor.valueChanged.connect(
            lambda v: (s.__setitem__("q_max_factor", float(v)), refresh())
        )

        dlg.add(ui.section("Solver"))
        dlg.add(ui.row("Pump head curve", method))
        dlg.add(ui.row("Search up to", factor, "× Q max tested"))
        dlg.add(ui.row("Result", info))
        dlg.add(banner)
        refresh()
        dlg.resize(560, 300)
        return dlg
