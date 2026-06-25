"""
nodes.fluid — Fluid (UC-00 service fluid object)

Source node.  Makes the *fluid* a first-class object on the canvas: either
**Water at a temperature** (density from ``pump.Water``'s polynomial, shown as a
live density-vs-temperature chart) or a **manual** fluid (name + density +
nominal viscosity).  Emits a ``FluidSpec`` signal.

Wired into Speed / Affinity Correction, Rated Point, Test Points or Point it
overrides the fluid those nodes use — see UC-00 in ``docs/product/use-cases.md``.
All physics goes through :mod:`pumpflow.binding` (``make_fluid`` /
``water_density_kgm3``); this node never touches ``pump`` directly.

Inputs are unit-aware (``ui.UnitField``): temperature in °C/K/°F, density in
kg/m³ or g/cm³, viscosity in cSt/cP — all normalised back to the library's
standard units in :meth:`to_signal`.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..binding import water_density_kgm3
from ..signals import FluidSpec
from .. import units
from .base import BaseNode, PortSpec
from . import ui


class FluidNode(BaseNode):
    kind = "fluid"
    title = "Fluid"
    glyph = "💧"
    is_source = True
    inputs = []
    outputs = [PortSpec("FluidSpec", "FluidSpec")]

    def default_settings(self) -> Dict:
        p = units.PREFS
        return {
            "source": "manual",  # "manual" | "water"
            "name": "Service fluid",
            "temp": 25.0,
            "temp_unit": p.default_unit("temperature"),
            "dens": 736.0,
            "dens_unit": p.default_unit("density"),
            "visc": 0.567,
            "visc_unit": p.default_unit("viscosity"),
        }

    # -- payload -----------------------------------------------------------
    def _temp_c(self) -> float:
        s = self.settings
        return units.convert_display(
            float(s["temp"]), "temperature", s.get("temp_unit") or "°C", "°C"
        )

    def to_signal(self) -> FluidSpec:
        s = self.settings
        if s.get("source") == "water":
            temp_c = self._temp_c()
            name = str(s.get("name") or "").strip() or f"Water @ {temp_c:g} °C"
            return FluidSpec(
                name=name,
                source="water",
                density_kgm3=water_density_kgm3(temp_c),
                viscosity_cst=1.0,
                temp_c=temp_c,
            )
        dens_kgm3 = units.to_standard(
            float(s["dens"]), "density", s.get("dens_unit") or "kg/m³"
        )
        dens_rel = dens_kgm3 / 1000.0
        return FluidSpec(
            name=str(s.get("name") or "").strip() or "Service fluid",
            source="manual",
            density_kgm3=dens_kgm3,
            viscosity_cst=units.to_standard(
                float(s["visc"]), "viscosity", s.get("visc_unit") or "cSt", dens_rel
            ),
            temp_c=None,
        )

    def compute(self, inputs) -> Dict[str, object]:
        spec = self.to_signal()
        ok, msg = spec.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        if spec.source == "water":
            self.status = f"{spec.name} · {spec.density_kgm3:.1f} kg/m³"
        else:
            self.status = (
                f"{spec.name} · SG {spec.density_rel:g} · {spec.viscosity_cst:g} cSt"
            )
        self.state = "ok"
        return {"FluidSpec": spec}

    def port_label(self, name: str) -> str:
        return "Fluid" if name == "FluidSpec" else name

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Fluid",
            "A reusable service fluid. Connect it to Rated Point, Test Points, "
            "Correction or Point to drive that node's fluid.",
            width=480,
        )
        banner = ui.Banner()

        source = ui.combo(
            [
                ("Manual (density + viscosity)", "manual"),
                ("Water at temperature", "water"),
            ],
            s.get("source", "manual"),
            None,
        )
        name = ui.line_edit(s.get("name", ""), None, "e.g. Light Hydrocarbon")

        # ---- Water mode: temperature (unit-aware) → live density chart ----
        temp_field = ui.UnitField(
            "temperature",
            s["temp"],
            s.get("temp_unit"),
            on_change=lambda: apply(),
            lo=-50.0,
            hi=300.0,
            step=1.0,
            decimals=2,
        )

        # pyqtgraph chart (consistent with the Performance Explorer); items are
        # created once and updated in place by update_chart().
        plot = None
        curve = None
        marker = None
        try:
            import pyqtgraph as pg

            pg.setConfigOptions(antialias=True, background="w", foreground="#33414f")
            plot = pg.PlotWidget()
            plot.setMinimumHeight(190)
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.setLabel("left", "ρ (kg/m³)")
            plot.setLabel("bottom", "Temperature (°C)")
            curve = plot.plot([], [], pen=pg.mkPen("#2f6fb0", width=2))
            marker = pg.ScatterPlotItem(
                size=10, brush=pg.mkBrush("#c0392b"), pen=pg.mkPen("#7a1f17")
            )
            plot.addItem(marker)
            chart_widget = plot
        except ImportError:
            chart_widget = QLabel(
                "pyqtgraph is not installed — run  pip install pyqtgraph  to see "
                "the density chart."
            )
            chart_widget.setWordWrap(True)

        water_box = QWidget()
        wl = QVBoxLayout(water_box)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.addWidget(temp_field.row("Temperature"))
        wl.addWidget(chart_widget)

        # ---- Manual mode: density (unit-aware) + derived SG + viscosity ----
        dens_field = ui.UnitField(
            "density",
            s["dens"],
            s.get("dens_unit"),
            on_change=lambda: apply(),
            lo=0.0,
            hi=5000.0,
            step=1.0,
            decimals=2,
        )
        sg_label = QLabel("—")
        visc_field = ui.UnitField(
            "viscosity",
            s["visc"],
            s.get("visc_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=0.01,
            decimals=3,
            dens_rel_getter=lambda: _dens_rel(),
        )

        manual_box = QWidget()
        ml = QVBoxLayout(manual_box)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.addWidget(dens_field.row("Density"))
        ml.addWidget(ui.row("Relative density", sg_label, "SG"))
        ml.addWidget(visc_field.row("Nominal viscosity"))

        def _dens_rel() -> float:
            return (
                units.to_standard(
                    float(dens_field.magnitude()),
                    "density",
                    dens_field.unit_label(),
                )
                / 1000.0
            )

        def update_chart():
            if plot is None:
                return
            temp_c = units.convert_display(
                float(temp_field.magnitude()),
                "temperature",
                temp_field.unit_label(),
                "°C",
            )
            lo, hi = min(0.0, temp_c), max(100.0, temp_c)
            ts = np.linspace(lo, hi, 60)
            ds = [water_density_kgm3(float(t)) for t in ts]
            rho = water_density_kgm3(temp_c)
            curve.setData(ts, ds)
            marker.setData([temp_c], [rho])
            plot.setTitle(f"{rho:.1f} kg/m³ @ {temp_c:g} °C")

        def refresh_mode():
            water = source.currentData() == "water"
            water_box.setVisible(water)
            manual_box.setVisible(not water)
            if water:
                update_chart()

        def apply():
            s["source"] = source.currentData()
            s["name"] = name.text()
            s["temp"], s["temp_unit"] = temp_field.magnitude(), temp_field.unit_label()
            s["dens"], s["dens_unit"] = dens_field.magnitude(), dens_field.unit_label()
            s["visc"], s["visc_unit"] = visc_field.magnitude(), visc_field.unit_label()
            sg_label.setText(f"{_dens_rel():.3f}")
            refresh_mode()
            ok, msg = self.to_signal().is_valid()
            banner.show_message("" if ok else msg, "info" if ok else "error")
            on_change()

        def on_source_change():
            # Toggling source changes which section is visible — refit the window
            # (deferred so the layout settles and the chart reports its size).
            apply()
            QTimer.singleShot(0, dlg.fit_to_contents)

        source.currentIndexChanged.connect(lambda _=None: on_source_change())
        name.textChanged.connect(lambda _=None: apply())

        dlg.add(ui.section("Fluid"))
        dlg.add(ui.row("Source", source))
        dlg.add(ui.row("Name", name))
        dlg.add(ui.hline())
        dlg.add(water_box)
        dlg.add(manual_box)
        dlg.add(banner)
        apply()
        QTimer.singleShot(0, dlg.fit_to_contents)
        return dlg
