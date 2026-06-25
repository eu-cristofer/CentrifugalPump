"""
units — the multi-unit handling spine of the workbench
======================================================

A single source of truth for *which display units the GUI offers* and *which
one a field defaults to*, layered cleanly on top of the ``pump`` library's
unit model.  The division of responsibility (the design philosophy) is:

1. **The library owns the canonical unit.** ``pump``'s ``STANDARD_UNITS`` is the
   only authority on the magnitude a stored signal carries (capacity m³/h, head
   m, power kW, …).  We never duplicate that table — we route every conversion
   back through :func:`pump.utilities.unit_conversion.quantity_factory`.
2. **The GUI owns the menu of display units.** :data:`UNIT_OPTIONS` maps each
   *dimension* the UI cares about to the display units it offers (label → Pint
   string), seeded so the library's canonical unit is always present.
3. **Display unit ≠ stored unit.** A dialog lets the user pick a display unit,
   but ``to_signal()`` always normalises back to the standard unit via
   :func:`to_standard`, so every downstream node sees canonical magnitudes.
4. **One conversion path.** Everything goes through ``quantity_factory``.  The
   viscosity kinematic↔dynamic case is the single documented exception (cSt is
   not in ``STANDARD_UNITS``), and it lives here in :func:`to_cst` only.
5. **Preset, then override.** A field's default display unit comes from the
   active project preset (:data:`PREFS`); an explicit per-field choice wins.

This module is Qt-agnostic so it can be imported by node logic, the reusable
``ui.UnitField`` widget, and tests alike.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pump.utilities.unit_conversion import Q_, quantity_factory

# ---------------------------------------------------------------------------
# The display-unit registry: dimension -> [(display label, Pint unit string)]
# The first entry of each list is the library's canonical/standard unit, so a
# field always has a safe default even outside any preset.
# ---------------------------------------------------------------------------

UNIT_OPTIONS: Dict[str, List[Tuple[str, str]]] = {
    "capacity": [
        ("m³/h", "m**3/h"),
        ("l/s", "L/s"),
        ("l/min", "L/min"),
        ("US GPM", "gallon/min"),
    ],
    "head": [
        ("m", "m"),
        ("ft", "ft"),
    ],
    "power": [
        ("kW", "kW"),
        ("hp", "hp"),
        ("CV", "metric_horsepower"),
    ],
    # Viscosity is special: cSt (kinematic) is not in STANDARD_UNITS, and the
    # cSt<->cP conversion needs the fluid density.  The Pint strings are still
    # listed for discoverability, but conversions route through to_cst().
    "viscosity": [
        ("cSt", "cSt"),
        ("cP", "cP"),
    ],
}

# Dimensions whose conversion needs the density-based special case rather than
# plain quantity_factory normalisation.
_DENSITY_COUPLED = {"viscosity"}


# ---------------------------------------------------------------------------
# Presets: a named unit system maps each dimension to a display label.
# "SI" is the canonical default; "US" is US-customary; "custom" forces no
# defaults (a field falls back to its canonical unit / last explicit choice).
# ---------------------------------------------------------------------------

PRESETS: Dict[str, Dict[str, str]] = {
    "SI": {
        "capacity": "m³/h",
        "head": "m",
        "power": "kW",
        "viscosity": "cSt",
    },
    "US": {
        "capacity": "US GPM",
        "head": "ft",
        "power": "hp",
        "viscosity": "cSt",  # cSt is the industry norm for viscosity in both
    },
    "custom": {},
}

DEFAULT_PRESET = "SI"


def canonical_unit(dimension: str) -> str:
    """The library's standard display label for a dimension (first option)."""
    return UNIT_OPTIONS[dimension][0][0]


def options_for(dimension: str) -> List[Tuple[str, str]]:
    """``[(label, label)]`` pairs suitable for :func:`pumpflow.nodes.ui.combo`."""
    return [(label, label) for label, _pint in UNIT_OPTIONS[dimension]]


def _pint_str(dimension: str, unit: str) -> str:
    for label, pint in UNIT_OPTIONS[dimension]:
        if label == unit:
            return pint
    raise KeyError(f"unknown {dimension} unit: {unit!r}")


class UnitPrefs:
    """Holds the active project-level unit preset (SI / US / custom).

    ``default_unit(dimension)`` resolves the display label a fresh field should
    open with: the preset's choice, falling back to the canonical unit.  The
    instance round-trips through ``.pumpflow`` via :meth:`to_dict` / :meth:`load`.
    """

    def __init__(self, preset: str = DEFAULT_PRESET):
        self.preset = preset if preset in PRESETS else DEFAULT_PRESET

    def set_preset(self, preset: str) -> None:
        self.preset = preset if preset in PRESETS else DEFAULT_PRESET

    def default_unit(self, dimension: str) -> str:
        return PRESETS.get(self.preset, {}).get(dimension) or canonical_unit(dimension)

    def to_dict(self) -> Dict[str, str]:
        return {"unit_preset": self.preset}

    def load(self, meta: Optional[Dict]) -> None:
        meta = meta or {}
        self.set_preset(str(meta.get("unit_preset", DEFAULT_PRESET)))


# Module singleton — the project's active unit preset.  Reset on new/open project.
PREFS = UnitPrefs()


# ---------------------------------------------------------------------------
# Conversion helpers — the single path every node uses.
# ---------------------------------------------------------------------------


def to_standard(
    value: float, dimension: str, unit: str, dens_rel: Optional[float] = None
) -> float:
    """Normalise a display value to the library's standard magnitude.

    For density-coupled dimensions (viscosity) ``dens_rel`` is required.
    """
    if dimension in _DENSITY_COUPLED:
        return to_cst(value, unit, dens_rel if dens_rel is not None else 1.0)
    return quantity_factory(Q_(value, _pint_str(dimension, unit))).magnitude


def convert_display(
    value: float,
    dimension: str,
    old_unit: str,
    new_unit: str,
    dens_rel: Optional[float] = None,
) -> float:
    """Re-express a value from one display unit to another (live combo switch)."""
    if old_unit == new_unit:
        return value
    if dimension in _DENSITY_COUPLED:
        return _convert_viscosity(value, old_unit, new_unit, dens_rel)
    std = quantity_factory(Q_(value, _pint_str(dimension, old_unit)))
    return std.to(_pint_str(dimension, new_unit)).magnitude


def to_cst(value: float, unit: str, dens_rel: float) -> float:
    """Kinematic viscosity in cSt from a cSt/cP display value.

    cSt is *kinematic* and not in ``STANDARD_UNITS``; cP is *dynamic*.  The
    bridge needs density (ν = μ / ρ), so this is the one place that does not
    route through ``quantity_factory``.
    """
    if unit == "cP":
        rho = Q_(dens_rel, "g/cm**3")
        return (Q_(value, "cP") / rho).to("cSt").magnitude
    return value


def _convert_viscosity(
    value: float, old_unit: str, new_unit: str, dens_rel: Optional[float]
) -> float:
    rho = Q_(dens_rel if dens_rel is not None else 1.0, "g/cm**3")
    if old_unit == "cSt" and new_unit == "cP":
        return (Q_(value, "cSt") * rho).to("cP").magnitude
    if old_unit == "cP" and new_unit == "cSt":
        return (Q_(value, "cP") / rho).to("cSt").magnitude
    return value
