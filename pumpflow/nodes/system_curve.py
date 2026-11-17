"""
nodes.system_curve — System Curve  (sprint 11 / UC-03)

Source node emitting a ``SystemCurveSpec``.  Three modes:

- ``"static_k"``: ``H = H_static + k·Q^n`` (``k`` in m/(m³/h)^n);
- ``"two_points"``: ``H_static`` and ``k`` solved through two (Q, H) points;
- ``"pipe"``: Darcy–Weisbach with the Swamee–Jain friction factor from pipe
  length, diameter, roughness and minor losses.  The fluid comes from an
  optional Fluid node, else water at 20 °C.

All dimensional fields are ``ui.UnitField``s; physics is in :mod:`pump`.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import QLabel

from pump import Q_

from .. import units
from ..binding import BindingError
from ..binding import make_system_curve
from .base import BaseNode, PortSpec
from .fluidpick import choice_options, current_choice, resolve_fluid
from . import ui

_MODES = [
    ("Static head + k·Q^n", "static_k"),
    ("Two points", "two_points"),
    ("Pipe data (Darcy–Weisbach)", "pipe"),
]
_MODE_LABEL = {data: label for label, data in _MODES}
_DEFAULT_FLUID = "Water at 20 °C"

#: (key, dimension) of every unit-aware field.
_FIELDS = (
    ("static", "head"),
    ("q1", "capacity"),
    ("h1", "head"),
    ("q2", "capacity"),
    ("h2", "head"),
    ("length", "length"),
    ("diameter", "length"),
    ("roughness", "length"),
)


class SystemCurveNode(BaseNode):
    kind = "system_curve"
    title = "System Curve"
    glyph = "∿"
    is_source = True
    inputs = [PortSpec("FluidSpec", "FluidSpec", multi=True)]
    outputs = [PortSpec("SystemCurveSpec", "SystemCurveSpec")]

    def default_settings(self) -> Dict:
        p = units.PREFS
        qu = p.default_unit("capacity")
        hu = p.default_unit("head")
        lu = p.default_unit("length")
        return {
            "mode": "static_k",
            "name": "System",
            "static": units.convert_display(20.0, "head", "m", hu),
            "static_unit": hu,
            "k": 1.0e-4,  # m per (m³/h)^n
            "exponent": 2.0,
            "q1": units.convert_display(100.0, "capacity", "m³/h", qu),
            "q1_unit": qu,
            "h1": units.convert_display(21.0, "head", "m", hu),
            "h1_unit": hu,
            "q2": units.convert_display(300.0, "capacity", "m³/h", qu),
            "q2_unit": qu,
            "h2": units.convert_display(29.0, "head", "m", hu),
            "h2_unit": hu,
            "length": units.convert_display(100.0, "length", "m", lu),
            "length_unit": lu,
            "diameter": units.convert_display(100.0, "length", "mm", lu),
            "diameter_unit": lu,
            "roughness": units.convert_display(0.045, "length", "mm", lu),
            "roughness_unit": lu,
            "minor_k": 0.0,
            "fluid_choice": "",
        }

    def _q(self, key: str, dimension: str) -> Q_:
        s = self.settings
        unit = s.get(key + "_unit") or units.canonical_unit(dimension)
        return Q_(float(s[key]), units.pint_str(dimension, unit))

    def _build(self, fluid_spec):
        s = self.settings
        mode = s.get("mode", "static_k")
        n = float(s.get("exponent", 2.0))
        common = {"name": s.get("name", "System"), "exponent": n}
        if mode == "static_k":
            k_unit = (
                Q_(1, "m") / Q_(1, "m**3/h") ** (int(n) if n.is_integer() else n)
            ).units
            return make_system_curve(
                mode,
                static_head=self._q("static", "head"),
                k=Q_(float(s["k"]), k_unit),
                **common,
            )
        if mode == "two_points":
            return make_system_curve(
                mode,
                points=(
                    (self._q("q1", "capacity"), self._q("h1", "head")),
                    (self._q("q2", "capacity"), self._q("h2", "head")),
                ),
                **common,
            )
        return make_system_curve(
            "pipe",
            name=common["name"],
            static_head=self._q("static", "head"),
            length=self._q("length", "length"),
            diameter=self._q("diameter", "length"),
            roughness=self._q("roughness", "length"),
            minor_k_sum=float(s.get("minor_k", 0.0)),
            fluid_spec=fluid_spec,
        )

    def compute(self, inputs) -> Dict[str, object]:
        self._fluids = self.all_of(inputs, "FluidSpec")
        chosen = resolve_fluid(self._fluids, self.settings.get("fluid_choice"))
        self._last = None
        try:
            spec = self._build(chosen)
        except (BindingError, ValueError, KeyError, TypeError) as exc:
            return self.emit_nothing(str(exc), "invalid")
        static_m = float(spec.curve.static_head.to("m").magnitude)
        self._last = spec
        self.status = (
            f"{spec.name} · {_MODE_LABEL.get(self.settings.get('mode'), '')} · "
            f"static {static_m:.1f} m"
        )
        self.state = "ok"
        return {"SystemCurveSpec": spec}

    def port_label(self, name: str) -> str:
        return {"FluidSpec": "Fluid", "SystemCurveSpec": "System"}.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "System Curve",
            "System resistance:  H = H_static + k·Q^n, solved through two points, "
            "or computed from pipe data (Darcy–Weisbach, Swamee–Jain friction).",
            width=560,
            maximizable=True,
        )
        banner = ui.Banner()

        name = ui.line_edit(s.get("name", "System"), None)
        mode = ui.combo(_MODES, s.get("mode", "static_k"), None)
        info = QLabel("—")
        info.setWordWrap(True)

        fields: Dict[str, ui.UnitField] = {}

        def make_field(key: str, dimension: str, hi: float, step: float, decimals: int):
            def changed(_key=key):
                f = fields[_key]
                s[_key] = f.magnitude()
                s[_key + "_unit"] = f.unit_label()
                refresh()

            fields[key] = ui.UnitField(
                dimension,
                s[key],
                s.get(key + "_unit"),
                on_change=changed,
                hi=hi,
                step=step,
                decimals=decimals,
            )
            return fields[key]

        rows = {
            "static": make_field("static", "head", 1e5, 1.0, 3).row("Static head"),
            "q1": make_field("q1", "capacity", 1e7, 10.0, 3).row("Q₁"),
            "h1": make_field("h1", "head", 1e5, 1.0, 3).row("H₁"),
            "q2": make_field("q2", "capacity", 1e7, 10.0, 3).row("Q₂"),
            "h2": make_field("h2", "head", 1e5, 1.0, 3).row("H₂"),
            "length": make_field("length", "length", 1e7, 10.0, 3).row("Pipe length"),
            "diameter": make_field("diameter", "length", 1e5, 1.0, 3).row(
                "Inner diameter"
            ),
            "roughness": make_field("roughness", "length", 1e3, 0.01, 4).row(
                "Roughness ε"
            ),
        }
        k_spin = ui.spin(float(s.get("k", 0.0)), 0.0, 1e9, 1e-5, 10, None)
        n_spin = ui.spin(float(s.get("exponent", 2.0)), 0.1, 5.0, 0.1, 2, None)
        minor = ui.spin(float(s.get("minor_k", 0.0)), 0.0, 1e4, 0.5, 2, None)
        fluid_pick = ui.combo(
            choice_options(getattr(self, "_fluids", []), _DEFAULT_FLUID),
            current_choice(getattr(self, "_fluids", []), s.get("fluid_choice")),
            None,
        )
        rows["k"] = ui.row("k", k_spin, "m/(m³/h)^n")
        rows["exponent"] = ui.row("Exponent n", n_spin)
        rows["minor_k"] = ui.row("Σ K (minor losses)", minor)
        rows["fluid"] = ui.row("Fluid", fluid_pick)

        visible = {
            "static_k": ("static", "k", "exponent"),
            "two_points": ("q1", "h1", "q2", "h2", "exponent"),
            "pipe": ("static", "length", "diameter", "roughness", "minor_k", "fluid"),
        }

        def refresh():
            on_change()
            show = visible.get(s.get("mode", "static_k"), ())
            for key, widget in rows.items():
                widget.setVisible(key in show)
            if self.state == "ok":
                info.setText(self.status)
                banner.show_message("", "info")
            else:
                info.setText("—")
                banner.show_message(
                    "" if self.state == "idle" else self.status,
                    "info" if self.state == "idle" else "error",
                )

        name.textChanged.connect(lambda t: (s.__setitem__("name", t), refresh()))
        mode.currentIndexChanged.connect(
            lambda _=None: (s.__setitem__("mode", mode.currentData()), refresh())
        )
        k_spin.valueChanged.connect(lambda v: (s.__setitem__("k", float(v)), refresh()))
        n_spin.valueChanged.connect(
            lambda v: (s.__setitem__("exponent", float(v)), refresh())
        )
        minor.valueChanged.connect(
            lambda v: (s.__setitem__("minor_k", float(v)), refresh())
        )
        fluid_pick.currentIndexChanged.connect(
            lambda _=None: (
                s.__setitem__("fluid_choice", fluid_pick.currentData()),
                refresh(),
            )
        )

        dlg.add(ui.section("System curve"))
        dlg.add(ui.row("Name", name))
        dlg.add(ui.row("Mode", mode))
        for key in (
            "static",
            "k",
            "exponent",
            "q1",
            "h1",
            "q2",
            "h2",
            "length",
            "diameter",
            "roughness",
            "minor_k",
            "fluid",
        ):
            dlg.add(rows[key])
        dlg.add(ui.row("Result", info))
        dlg.add(banner)
        refresh()
        dlg.resize(600, 520)
        return dlg
