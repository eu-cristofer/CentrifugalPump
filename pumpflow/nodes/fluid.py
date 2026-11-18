"""
nodes.fluid — Fluid (UC-00 service fluid object)

Source node.  Makes the *fluid* a first-class object on the canvas: either
**Water at a temperature** (density from ``pump.Water``'s polynomial, shown as a
live density-vs-temperature chart) or a **manual** fluid (name + density +
nominal viscosity).  Emits a ``FluidSpec`` signal.

Wired into Speed / Affinity Correction, Rated Point, Test Points or Point it
overrides the fluid those nodes use — see UC-00 in ``docs/product/use-cases.md``.
All physics goes through :mod:`pumpflow.binding` (``make_fluid`` /
``water_density_kgm3``) and ``pump.Water``; the emitted ``FluidSpec`` carries
Pint Quantities.

Inputs are unit-aware (``ui.UnitField``): temperature in °C/K/°F, density in
kg/m³ or g/cm³, viscosity in cSt/cP — all normalised back to the library's
standard units in :meth:`to_signal`.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pump import Q_, Water

from ..binding import (
    water_density_kgm3,
    water_dynamic_viscosity_cP,
    water_kinematic_viscosity_cst,
)
from ..signals import FluidSpec
from .. import units
from pump.design import color as token_color

from .base import BaseNode, PortSpec
from . import ui


class FluidNode(BaseNode):
    kind = "fluid"
    title = "Fluid"
    glyph = "≈"
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
            temperature = Q_(temp_c, "degC")
            water = Water(temperature)
            return FluidSpec(
                name=name,
                source="water",
                density=water.density,
                viscosity=water.kinematic_viscosity,
                temperature=temperature,
            )
        dens_kgm3 = units.to_standard(
            float(s["dens"]), "density", s.get("dens_unit") or "kg/m³"
        )
        dens_rel = dens_kgm3 / 1000.0
        return FluidSpec(
            name=str(s.get("name") or "").strip() or "Service fluid",
            source="manual",
            density=Q_(dens_kgm3, "kg/m**3"),
            viscosity=Q_(
                units.to_standard(
                    float(s["visc"]), "viscosity", s.get("visc_unit") or "cSt", dens_rel
                ),
                "cSt",
            ),
            temperature=None,
        )

    def compute(self, inputs) -> Dict[str, object]:
        spec = self.to_signal()
        ok, msg = spec.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        density_kgm3 = spec.density.to("kg/m**3").magnitude
        viscosity_cst = spec.viscosity.to("cSt").magnitude
        if spec.source == "water":
            self.status = (
                f"{spec.name} · {density_kgm3:.1f} kg/m³"
                f" · {viscosity_cst:.3f} cSt"
            )
        else:
            self.status = (
                f"{spec.name} · SG {spec.density_rel:g} · {viscosity_cst:g} cSt"
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

            pg.setConfigOptions(antialias=True, background="w", foreground=token_color("chart-ink"))
            plot = pg.PlotWidget()
            # Span the full body width but keep the height modest so showing the
            # chart only grows the window by a small amount.
            plot.setFixedHeight(220)
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.setLabel("left", "ρ (kg/m³)")
            plot.setLabel("bottom", "Temperature (°C)")
            curve = plot.plot([], [], pen=pg.mkPen(token_color("chart-head"), width=2))
            marker = pg.ScatterPlotItem(
                size=10, brush=pg.mkBrush(token_color("chart-state-point")),
                pen=pg.mkPen(token_color("chart-state-point-edge")),
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
        density_label = QLabel("—")
        density_label.setWordWrap(True)
        viscosity_cst_label = QLabel("—")
        viscosity_cp_label = QLabel("—")
        viscosity_cp_label.setWordWrap(True)
        equation_label = QLabel(
            "Density: 4th-order Kell polynomial in temperature. "
            "Viscosity: Andrade-type exponential, "
            "mu = 2.414e-5 * 10^(247.8 / (T[K] - 140)) Pa·s."
        )
        equation_label.setWordWrap(True)
        reference_label = QLabel(
            "References: Kell, G. S. (1975). Journal of Chemical and Engineering Data, "
            "20(1), 97-105, doi:10.1021/je60064a005; Kestin, J., Sokolov, M., "
            "Wakeham, W. A. (1978). Journal of Physical and Chemical Reference Data, "
            "7(3), 941-948, doi:10.1063/1.555581."
        )
        reference_label.setWordWrap(True)
        wl.addWidget(temp_field.row("Temperature"))
        wl.addWidget(ui.row("Density", density_label))
        wl.addWidget(ui.row("Viscosity", viscosity_cst_label, "cSt"))
        wl.addWidget(ui.row("Dynamic viscosity", viscosity_cp_label, "cP"))
        wl.addWidget(equation_label)
        wl.addWidget(reference_label)
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
            temp_c = units.convert_display(
                float(temp_field.magnitude()),
                "temperature",
                temp_field.unit_label(),
                "°C",
            )
            rho = water_density_kgm3(temp_c)
            nu_cst = water_kinematic_viscosity_cst(temp_c)
            mu_cp = water_dynamic_viscosity_cP(temp_c)
            density_label.setText(f"{rho:.3f} kg/m³  |  SG {rho / 1000.0:.6f}")
            viscosity_cst_label.setText(f"{nu_cst:.6f}")
            viscosity_cp_label.setText(f"{mu_cp:.6f}")
            if plot is None:
                return
            lo, hi = min(0.0, temp_c), max(100.0, temp_c)
            ts = np.linspace(lo, hi, 60)
            ds = [water_density_kgm3(float(t)) for t in ts]
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
            # Height-only so showing/hiding the chart never shifts the window
            # sideways.
            apply()
            QTimer.singleShot(0, lambda: dlg.fit_to_contents(vertical_only=True))

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
