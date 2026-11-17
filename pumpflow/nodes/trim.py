"""
nodes.trim — Impeller Trim  (sprint 10 / UC-07)

Inputs ``FittedModel`` (or ``CorrectedCurve``) + ``RatedPoint`` → outputs a
``CorrectedCurve`` at the trimmed diameter.  The reference diameter is the rated
point's nominal impeller diameter.  Two modes:

- ``"target"``: the user enters the target diameter;
- ``"duty"``: the diameter that makes the curve pass through the rated (Q, H),
  solved along the affinity parabola (``binding.diameter_for_rated``).

Pure diameter affinity (Q ∝ D, H ∝ D², P ∝ D³, η unchanged); HI-style trim
corrections are not applied.  All physics is in :mod:`pump` via ``binding``.
"""

from __future__ import annotations

import warnings
from typing import Dict

from PySide6.QtWidgets import QLabel

from pump import Q_

from .. import units
from ..binding import BindingError, diameter_for_rated, trim_curve
from .base import BaseNode, PortSpec
from . import ui


class TrimNode(BaseNode):
    kind = "trim"
    title = "Impeller Trim"
    glyph = "⌀"
    inputs = [
        PortSpec("FittedModel", "FittedModel"),
        PortSpec("CorrectedCurve", "CorrectedCurve"),
        PortSpec("RatedPoint", "RatedPoint"),
    ]
    outputs = [PortSpec("CorrectedCurve", "CorrectedCurve")]

    def default_settings(self) -> Dict:
        lu = units.PREFS.default_unit("length")
        return {
            "mode": "target",  # "target" | "duty"
            "d_target": units.convert_display(128.0, "length", "mm", lu),
            "d_target_unit": lu,
            "max_trim_pct": 5.0,
        }

    def _target(self) -> Q_:
        s = self.settings
        unit = s.get("d_target_unit") or "mm"
        return Q_(float(s["d_target"]), units.pint_str("length", unit))

    def compute(self, inputs) -> Dict[str, object]:
        self._info = None
        self._last = None
        rated = self.first(inputs, "RatedPoint")
        source = self.first(inputs, "FittedModel")
        if source is None:
            source = self.first(inputs, "CorrectedCurve")
        if source is None:
            return self.emit_nothing(
                "Waiting for a fitted model or corrected curve", "idle"
            )
        if rated is None:
            return self.emit_nothing("Waiting for rated point", "idle")
        d_ref = rated.impeller_diameter
        if d_ref is None:
            return self.emit_nothing(
                "Set the nominal impeller diameter on the Rated Point node", "invalid"
            )

        s = self.settings
        max_pct = float(s.get("max_trim_pct", 5.0))
        try:
            if s.get("mode") == "duty":
                d_new = diameter_for_rated(source, rated)
            else:
                d_new = self._target()
            if not float(d_new.to("mm").magnitude) > 0:
                return self.emit_nothing("Target diameter must be > 0", "invalid")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                trimmed = trim_curve(source, d_new, d_ref, max_trim=max_pct / 100.0)
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")

        d_mm = float(d_new.to("mm").magnitude)
        ref_mm = float(d_ref.to("mm").magnitude)
        trim_pct = (d_mm / ref_mm - 1.0) * 100.0
        notes = []
        if any(issubclass(w.category, UserWarning) for w in caught):
            notes.append(f"beyond max trim ({max_pct:g} %)")
        d_max = rated.impeller_diameter_max
        d_min = rated.impeller_diameter_min
        max_mm = float(d_max.to("mm").magnitude) if d_max is not None else None
        min_mm = float(d_min.to("mm").magnitude) if d_min is not None else None
        if (max_mm is not None and d_mm > max_mm + 1e-9) or (
            min_mm is not None and d_mm < min_mm - 1e-9
        ):
            lo = f"{min_mm:g}" if min_mm is not None else "-"
            hi = f"{max_mm:g}" if max_mm is not None else "-"
            notes.append(f"outside datasheet range [{lo}, {hi}] mm")

        self._info = {
            "d_mm": d_mm,
            "ref_mm": ref_mm,
            "trim_pct": trim_pct,
            "notes": notes,
        }
        self._last = trimmed
        warn = (" · ⚠ " + "; ".join(notes)) if notes else ""
        self.status = (
            f"{source.pump_tag} · D = {d_mm:.1f} mm · trim {trim_pct:+.1f} %{warn}"
        )
        self.state = "ok"
        return {"CorrectedCurve": trimmed}

    def port_label(self, name: str) -> str:
        return {
            "FittedModel": "Model",
            "CorrectedCurve": "Corrected",
            "RatedPoint": "Rated",
        }.get(name, name)

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Impeller Trim",
            "Diameter affinity:  Q ∝ D · H ∝ D² · P ∝ D³ · η unchanged. "
            "Standard approximation; HI-style trim corrections are not applied.",
            width=620,
        )
        banner = ui.Banner()

        mode = ui.combo(
            [("Target diameter", "target"), ("Solve for rated duty", "duty")],
            s.get("mode", "target"),
            None,
        )
        target = ui.UnitField(
            "length",
            s["d_target"],
            s.get("d_target_unit"),
            on_change=lambda: on_target(),
            hi=1e4,
            step=0.5,
            decimals=3,
        )
        max_trim = ui.spin(float(s.get("max_trim_pct", 5.0)), 0.0, 100.0, 0.5, 2, None)
        info = QLabel("—")
        info.setWordWrap(True)

        grid = ui.BeforeAfterTable(s)
        table = grid.table

        def refresh():
            on_change()
            manual = s.get("mode") != "duty"
            target.spin.setEnabled(manual)
            target.combo.setEnabled(manual)
            data = getattr(self, "_info", None) if self.state == "ok" else None
            trimmed = getattr(self, "_last", None) if self.state == "ok" else None
            if data:
                info.setText(
                    f"D = {data['d_mm']:.2f} mm (reference {data['ref_mm']:.2f} mm) · "
                    f"trim {data['trim_pct']:+.2f} %"
                )
                if data["notes"]:
                    banner.show_message("⚠ " + "; ".join(data["notes"]), "warn")
                else:
                    banner.show_message("", "info")
            else:
                info.setText("—")
                banner.show_message(
                    "" if self.state == "idle" else self.status,
                    "info" if self.state in ("ok", "idle") else "error",
                )
            grid.fill(trimmed.before_after if trimmed else (), ("reference", "trimmed"))

        def on_target():
            s["d_target"] = target.magnitude()
            s["d_target_unit"] = target.unit_label()
            refresh()

        mode.currentIndexChanged.connect(
            lambda _=None: (s.__setitem__("mode", mode.currentData()), refresh())
        )
        max_trim.valueChanged.connect(
            lambda v: (s.__setitem__("max_trim_pct", float(v)), refresh())
        )

        dlg.add(ui.section("Trim"))
        dlg.add(ui.row("Mode", mode))
        dlg.add(target.row("Target diameter"))
        dlg.add(ui.row("Max trim", max_trim, "%"))
        dlg.add(ui.row("Result", info))
        dlg.add(ui.hline())
        dlg.add(ui.section("Reference vs trimmed curve"))
        dlg.add(grid.strip)
        dlg.add(table)
        dlg.add(banner)
        refresh()
        dlg.resize(660, 560)
        return dlg
