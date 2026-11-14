"""
nodes.rated_point — Rated Point Input  (UI_SPEC §5.1)

Source node.  Captures the shared rated (design) point + rated fluid and emits a
``RatedPoint`` signal.  Density is entered as relative density **and** kg/m³ kept
in sync.

Unit selection for Q, H, N, P, η, shut-off head, NPSHa and viscosity is handled
by the reusable ``ui.UnitField`` widget, backed by the central
:mod:`pumpflow.units` registry — the single place that knows which display units
are offered and how they map to the library's canonical units.  ``to_signal``
always normalises Q/H/N/P/η/… to m³/h/m/rpm/kW/% (and viscosity to cSt) and wraps
them as Pint Quantities so every downstream node sees standard units.
A fresh node opens in whatever display units the active project preset selects.

The acceptance criteria are chosen with the "Standard / edition" and "Client
overlay" combos (``standard_key`` / ``client``); when those settings are absent
(older projects) they are derived from the free-text ``standard`` label.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import QLabel

from pump import Q_

from .. import units
from ..binding import (
    available_clients,
    available_standards,
    standard_label,
    water_density_kgm3,
)
from ..settings_codec import parse_standard_text
from ..signals import RatedPoint
from .base import BaseNode, PortSpec
from .fluidpick import choice_options, current_choice, resolve_fluid
from . import ui

_DEFAULT_LABEL = "Custom (entered below)"


def _standard_keys(s: Dict):
    """``(standard_key, client)`` of the settings: stored keys, else parsed text."""
    if "standard_key" in s:
        return (str(s.get("standard_key") or "api610:12"), str(s.get("client") or ""))
    key, client = parse_standard_text(s.get("standard", ""))
    return key, client or ""


class RatedPointInputNode(BaseNode):
    kind = "rated_point"
    title = "Rated Point Input"
    glyph = "◆"
    is_source = True
    # Optional Fluid input (multi): wired Fluid nodes can override the rated
    # fluid (density / viscosity / name), which then propagates to the design
    # point, Compliance, Report Export and the correction target.  A "Fluid
    # source" picker chooses Custom or one of the wired fluids.
    inputs = [PortSpec("FluidSpec", "FluidSpec", multi=True)]
    outputs = [PortSpec("RatedPoint", "RatedPoint")]

    def default_settings(self) -> Dict:
        p = units.PREFS
        qu = p.default_unit("capacity")
        hu = p.default_unit("head")
        pu = p.default_unit("power")
        vu = p.default_unit("viscosity")
        nu = p.default_unit("speed")
        eu = p.default_unit("efficiency")
        hsu = p.default_unit("head")
        npu = p.default_unit("npsh")
        return {
            "tag": "B-2351105",
            "service": "",
            "standard": "API610 (12a ed.) / ISO 13709 + N-553",
            "q": units.convert_display(833.0, "capacity", "m³/h", qu),
            "q_unit": qu,
            "head": units.convert_display(73.0, "head", "m", hu),
            "head_unit": hu,
            "n": units.convert_display(1750.0, "speed", "rpm", nu),
            "n_unit": nu,
            "power": units.convert_display(252.0, "power", "kW", pu),
            "power_unit": pu,
            "eff": units.convert_display(61.0, "efficiency", "%", eu),
            "eff_unit": eu,
            "head_shutoff": units.convert_display(117.0, "head", "m", hsu),
            "head_shutoff_unit": hsu,
            "npsha": units.convert_display(0.0, "npsh", "m", npu),
            "npsha_unit": npu,
            "dens_rel": 0.736,
            "dens_unit": p.default_unit("density"),
            "visc": 0.567,
            "visc_unit": vu,
            "parallel": False,
            "fluid_name": "Rated fluid",
            "fluid_choice": "",  # ""=first wired (default), "__default__"=Custom, or a name
        }

    # -- payload -----------------------------------------------------------
    def to_signal(self, override=None) -> RatedPoint:
        s = self.settings
        dens_rel = float(s["dens_rel"])
        viscosity_cst = units.to_standard(
            float(s["visc"]), "viscosity", s.get("visc_unit") or "cSt", dens_rel
        )
        density = Q_(dens_rel * 1000.0, "kg/m**3")
        viscosity = Q_(viscosity_cst, "cSt")
        fluid_name = str(s.get("fluid_name", "Rated fluid"))
        # A connected Fluid node overrides the rated fluid (UC-00).
        if override is not None:
            density = override.density
            viscosity = override.viscosity
            fluid_name = override.name
        eff = _opt(s.get("eff"))
        head_shutoff = _opt(s.get("head_shutoff"))
        npsha = _opt(s.get("npsha"))
        eff_unit = s.get("eff_unit") or "%"
        hso_unit = s.get("head_shutoff_unit") or "m"
        npsha_unit = s.get("npsha_unit") or "m"
        n_unit = s.get("n_unit") or "rpm"
        standard_key, client = _standard_keys(s)
        # Persist the resolved edition: a file re-saved from an old project then
        # carries explicit keys, exactly like one passed through migrate().
        s.setdefault("standard_key", standard_key)
        s.setdefault("client", client)
        return RatedPoint(
            tag=str(s["tag"]).strip(),
            service=str(s.get("service", "")),
            standard=str(s["standard"]),
            q=Q_(
                units.to_standard(float(s["q"]), "capacity", s.get("q_unit") or "m³/h"),
                "m**3/h",
            ),
            head=Q_(
                units.to_standard(float(s["head"]), "head", s.get("head_unit") or "m"),
                "m",
            ),
            speed=Q_(float(s["n"]), units.pint_str("speed", n_unit)).to("rpm"),
            power=Q_(
                units.to_standard(
                    float(s["power"]), "power", s.get("power_unit") or "kW"
                ),
                "kW",
            ),
            efficiency=(
                None
                if eff is None
                else Q_(eff, units.pint_str("efficiency", eff_unit)).to("percent")
            ),
            head_shutoff=(
                None
                if head_shutoff is None
                else Q_(units.to_standard(head_shutoff, "head", hso_unit), "m")
            ),
            npsha=(
                None
                if npsha is None
                else Q_(units.to_standard(npsha, "npsh", npsha_unit), "m")
            ),
            density=density,
            viscosity=viscosity,
            parallel_operation=bool(s["parallel"]),
            fluid_name=fluid_name,
            standard_key=standard_key,
            client=client or None,
        )

    def compute(self, inputs) -> Dict[str, object]:
        self._fluids = self.all_of(inputs, "FluidSpec")
        self._fluid_override = resolve_fluid(
            self._fluids, self.settings.get("fluid_choice")
        )
        rated = self.to_signal(self._fluid_override)
        ok, msg = rated.is_valid()
        if not ok:
            return self.emit_nothing(msg, "invalid")
        s = self.settings
        par = " · ∥-op" if rated.parallel_operation else ""
        fl = " · fluid✓" if self._fluid_override is not None else ""
        self.status = (
            f"{rated.tag} · {float(s['q']):g} {s.get('q_unit', 'm³/h')}"
            f" · {float(s['head']):g} {s.get('head_unit', 'm')}"
            f" · {rated.speed.to('rpm').magnitude:g} rpm{par}{fl}"
        )
        self.state = "ok"
        return {"RatedPoint": rated}

    def port_label(self, name: str) -> str:
        return {"FluidSpec": "Fluid", "RatedPoint": "Rated"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Rated Point Input",
            "Shared rated/design point and fluid — entered once, reused by every pump branch.",
            width=500,
        )
        banner = ui.Banner()

        # Unit-aware fields (Q, H, N, P, η, H shut-off, NPSHa, density, viscosity).
        # Viscosity reads the live relative density for its kinematic↔dynamic
        # conversion.
        q_field = ui.UnitField(
            "capacity",
            s["q"],
            s.get("q_unit"),
            on_change=lambda: apply(),
            hi=1e6,
            step=1,
            decimals=3,
        )
        head_field = ui.UnitField(
            "head",
            s["head"],
            s.get("head_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=1,
            decimals=3,
        )
        n_field = ui.UnitField(
            "speed",
            s["n"],
            s.get("n_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=10,
            decimals=3,
        )
        power_field = ui.UnitField(
            "power",
            s["power"],
            s.get("power_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=1,
            decimals=3,
        )
        eff_field = ui.UnitField(
            "efficiency",
            s.get("eff") or 0,
            s.get("eff_unit"),
            on_change=lambda: apply(),
            hi=100,
            step=0.5,
            decimals=3,
        )
        hso_field = ui.UnitField(
            "head",
            s.get("head_shutoff") or 0,
            s.get("head_shutoff_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=1,
            decimals=3,
        )
        npsha_field = ui.UnitField(
            "npsh",
            s.get("npsha") or 0,
            s.get("npsha_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=0.1,
            decimals=3,
        )
        density_field = ui.UnitField(
            "density",
            units.convert_display(
                float(s["dens_rel"]) * 1000.0,
                "density",
                "kg/m³",
                s.get("dens_unit") or "kg/m³",
            ),
            s.get("dens_unit"),
            on_change=lambda: apply(),
            lo=0.0,
            hi=5000.0,
            step=1.0,
            decimals=3,
        )
        visc_field = ui.UnitField(
            "viscosity",
            s["visc"],
            s.get("visc_unit"),
            on_change=lambda: apply(),
            hi=1e5,
            step=0.01,
            decimals=3,
            dens_rel_getter=lambda: float(s["dens_rel"]),
        )

        def sync_fields():
            s["q"], s["q_unit"] = q_field.magnitude(), q_field.unit_label()
            s["head"], s["head_unit"] = head_field.magnitude(), head_field.unit_label()
            s["n"], s["n_unit"] = n_field.magnitude(), n_field.unit_label()
            s["power"], s["power_unit"] = (
                power_field.magnitude(),
                power_field.unit_label(),
            )
            s["eff"], s["eff_unit"] = eff_field.magnitude(), eff_field.unit_label()
            s["head_shutoff"], s["head_shutoff_unit"] = (
                hso_field.magnitude(),
                hso_field.unit_label(),
            )
            s["npsha"], s["npsha_unit"] = (
                npsha_field.magnitude(),
                npsha_field.unit_label(),
            )
            s["dens_unit"] = density_field.unit_label()
            s["visc"], s["visc_unit"] = visc_field.magnitude(), visc_field.unit_label()

        # ---- IDENTIFICATION ----
        service = ui.line_edit(s.get("service", ""), None, "e.g. Crude Oil Transfer")
        service.textChanged.connect(lambda v: (s.__setitem__("service", v), apply()))
        tag = ui.line_edit(s["tag"], None, "service / datasheet TAG")
        tag.textChanged.connect(lambda v: (s.__setitem__("tag", v), apply()))
        std = ui.line_edit(s["standard"], None)
        std.textChanged.connect(lambda v: (s.__setitem__("standard", v), apply()))

        # ---- ACCEPTANCE CRITERIA — edition + client overlay ----
        cur_key, cur_client = _standard_keys(s)
        edition_combo = ui.combo(
            [(label, key) for key, label in available_standards()], cur_key, None
        )
        client_combo = ui.combo(
            [("None", "")] + [(label, c) for c, label in available_clients()],
            cur_client,
            None,
        )

        def on_standard_change():
            key = edition_combo.currentData() or "api610:12"
            client = client_combo.currentData() or ""
            s["standard_key"], s["client"] = key, client
            label = standard_label(key, client or None)
            s["standard"] = label
            std.setText(label)
            apply()

        edition_combo.currentIndexChanged.connect(lambda _=None: on_standard_change())
        client_combo.currentIndexChanged.connect(lambda _=None: on_standard_change())

        # ---- RATED FLUID — relative ↔ absolute density kept in sync ----
        dens_rel = ui.spin(s["dens_rel"], 0.0, 5.0, 0.001, 6, None)
        density_rel_display = QLabel("—")
        density_kgm3_display = QLabel("—")
        water_equivalent_display = QLabel("—")

        def on_rel(v):
            s["dens_rel"] = float(v)
            density_field.spin.blockSignals(True)
            density_field.spin.setValue(
                units.convert_display(
                    float(v) * 1000.0,
                    "density",
                    "kg/m³",
                    density_field.unit_label(),
                )
            )
            density_field.spin.blockSignals(False)
            apply()

        def on_density_change():
            density_kgm3 = density_field.standard()
            s["dens_rel"] = density_kgm3 / 1000.0
            dens_rel.blockSignals(True)
            dens_rel.setValue(s["dens_rel"])
            dens_rel.blockSignals(False)
            apply()

        dens_rel.valueChanged.connect(on_rel)
        density_field.spin.valueChanged.connect(lambda _=None: on_density_change())
        density_field.combo.currentIndexChanged.connect(lambda _=None: on_density_change())

        fluid_name = ui.line_edit(
            s.get("fluid_name", "Rated fluid"), None, "e.g. Light Hydrocarbon"
        )
        fluid_name.textChanged.connect(
            lambda v: (s.__setitem__("fluid_name", v), apply())
        )

        # ---- Fluid source picker (Custom or a wired Fluid node) ----
        fluids = getattr(self, "_fluids", [])
        fluid_pick = ui.combo(
            choice_options(fluids, _DEFAULT_LABEL),
            current_choice(fluids, s.get("fluid_choice")),
            None,
        )
        fluid_pick.currentIndexChanged.connect(
            lambda _: (s.__setitem__("fluid_choice", fluid_pick.currentData()), apply())
        )

        def set_fluid_enabled(enabled: bool) -> None:
            for w in (
                fluid_name,
                dens_rel,
                density_field.spin,
                density_field.combo,
                visc_field.spin,
                visc_field.combo,
            ):
                w.setEnabled(enabled)
        parallel = ui.checkbox("Parallel-operation unit (A/B)", s["parallel"], None)
        parallel.toggled.connect(
            lambda v: (s.__setitem__("parallel", bool(v)), apply())
        )

        def refresh_density_labels(override) -> None:
            if override is not None:
                density_rel_display.setText(f"{override.density_rel:.6f}")
                density_kgm3_display.setText(
                    f"{override.density.to('kg/m**3').magnitude:.3f}"
                )
                water_equivalent_display.setText("From connected Fluid node")
                return
            density_kgm3 = float(s["dens_rel"]) * 1000.0
            density_rel_display.setText(f"{float(s['dens_rel']):.6f}")
            density_kgm3_display.setText(f"{density_kgm3:.3f}")
            water_temp_c = 20.0
            water_equivalent_display.setText(
                f"Water @ {water_temp_c:g} °C = {water_density_kgm3(water_temp_c):.3f} kg/m³"
            )

        def apply():
            sync_fields()
            override = resolve_fluid(
                getattr(self, "_fluids", []), s.get("fluid_choice")
            )
            set_fluid_enabled(override is None)
            refresh_density_labels(override)
            ok, msg = self.to_signal(override).is_valid()
            if override is not None:
                banner.show_message(
                    f"Rated fluid from wired Fluid node: {override.name}.", "info"
                )
            else:
                banner.show_message("" if ok else msg, "error" if not ok else "info")
            on_change()

        # ---- Layout ----
        dlg.add(ui.section("Identification"))
        dlg.add(ui.row("Service", service))
        dlg.add(ui.row("Service TAG", tag))
        dlg.add(ui.row("Standard / edition", edition_combo))
        dlg.add(ui.row("Client overlay", client_combo))
        dlg.add(ui.row("Standard", std))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated duty"))
        dlg.add(q_field.row("Capacity  Q"))
        dlg.add(head_field.row("Diff. head  H"))
        dlg.add(n_field.row("Speed  N"))
        dlg.add(power_field.row("Power  P"))
        dlg.add(eff_field.row("Efficiency  η"))
        dlg.add(hso_field.row("Shut-off head"))
        dlg.add(npsha_field.row("NPSHa"))
        dlg.add(ui.hline())
        dlg.add(ui.section("Rated fluid"))
        if fluids:
            dlg.add(ui.row("Fluid source", fluid_pick))
        fluid_name_row = ui.row("Fluid name", fluid_name)
        dens_rel_input_row = ui.row("Relative density input", dens_rel, "SG")
        density_input_row = density_field.row("Density input")
        density_rel_row = ui.row("Relative density", density_rel_display, "SG")
        density_row = ui.row("Density", density_kgm3_display, "kg/m³")
        viscosity_row = visc_field.row("Nominal viscosity")
        water_reference_row = ui.row("Water reference", water_equivalent_display)
        dlg.add(fluid_name_row)
        dlg.add(dens_rel_input_row)
        dlg.add(density_input_row)
        dlg.add(density_rel_row)
        dlg.add(density_row)
        dlg.add(viscosity_row)
        dlg.add(water_reference_row)
        dlg.add(ui.row("", parallel))
        dlg.add(banner)

        def sync_fluid_rows(enabled: bool) -> None:
            dens_rel_input_row.setVisible(enabled)
            density_input_row.setVisible(enabled)

        original_set_fluid_enabled = set_fluid_enabled

        def set_fluid_enabled(enabled: bool) -> None:
            original_set_fluid_enabled(enabled)
            sync_fluid_rows(enabled)

        apply()
        return dlg


def _opt(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None
