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
   Efficiency is the other small special case: it converts directly between
   ``percent`` and ``dimensionless`` (the ``%`` spelling is not parseable by
   every Pint build, so ``quantity_factory`` is bypassed for it).
5. **Preset, then override.** A field's default display unit comes from the
   active project preset (:data:`PREFS`); an explicit per-field choice wins.

This module is Qt-agnostic so it can be imported by node logic, the reusable
``ui.UnitField`` widget, and tests alike.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from pump.constants import P_ATM
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
    # Temperature normalises to kelvin (absolute); quantity_factory handles the
    # offset units.  Used by the Fluid node's Water-at-temperature mode.
    "temperature": [
        ("°C", "degC"),
        ("K", "kelvin"),
        ("°F", "degF"),
    ],
    "density": [
        ("kg/m³", "kg/m**3"),
        ("g/cm³", "g/cm**3"),
    ],
    # Pressure standardises to kgf/cm² (quantity_factory default context).
    "pressure": [
        ("kgf/cm²", "kgf/cm**2"),
        ("bar", "bar"),
        ("psi", "psi"),
        ("kPa", "kPa"),
        ("MPa", "MPa"),
        ("mH₂O", "meter_H2O"),
    ],
    # Shaft speed.  Never use Hz (Pint's Hz is 1/s, i.e. 2*pi off from rev/s).
    "speed": [
        ("rpm", "rpm"),
        ("rev/s", "revolution/second"),
    ],
    "length": [
        ("m", "m"),
        ("mm", "mm"),
        ("in", "inch"),
    ],
    # NPSH: same Pint dimensionality as head, separate so presets can differ.
    "npsh": [
        ("m", "m"),
        ("ft", "ft"),
    ],
    # Efficiency standardises to percent.
    "efficiency": [
        ("%", "percent"),
        ("fraction", "dimensionless"),
    ],
    "vibration_velocity": [
        ("m/s", "m/s"),
        ("mm/s", "mm/s"),
        ("in/s", "inch/s"),
    ],
}

# Dimensions whose conversion needs the density-based special case rather than
# plain quantity_factory normalisation.
_DENSITY_COUPLED = {"viscosity"}

# Dimensions converted directly with Pint (standard unit given here) instead of
# through quantity_factory.
_DIRECT_STD = {"efficiency": "percent"}


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
        "temperature": "°C",
        "density": "kg/m³",
        "pressure": "bar",
        "speed": "rpm",
        "length": "mm",
        "npsh": "m",
        "efficiency": "%",
        "vibration_velocity": "mm/s",
    },
    "US": {
        "capacity": "US GPM",
        "head": "ft",
        "power": "hp",
        "viscosity": "cSt",  # cSt is the industry norm for viscosity in both
        "temperature": "°F",
        "density": "kg/m³",
        "pressure": "psi",
        "speed": "rpm",
        "length": "in",
        "npsh": "ft",
        "efficiency": "%",
        "vibration_velocity": "in/s",
    },
    "custom": {},
}

DEFAULT_PRESET = "SI"

# Test Points column key -> unit dimension.
COLUMN_DIMENSIONS: Dict[str, str] = {
    "q": "capacity",
    "p_suc": "pressure",
    "p_dis": "pressure",
    "temp_c": "temperature",
    "n": "speed",
    "power": "power",
    "head": "head",
    "eff": "efficiency",
}

# Optional Test Points vibration columns (bearing-housing velocity, RMS): drive
# end / non-drive end, overall / filtered.  Kept out of COLUMN_DIMENSIONS so a
# project without vibration data keeps its exact on-disk shape.
VIBRATION_COLUMNS: Dict[str, str] = {
    "vib_de": "vibration_velocity",
    "vib_de_f": "vibration_velocity",
    "vib_nde": "vibration_velocity",
    "vib_nde_f": "vibration_velocity",
}

#: Every Test Points column key -> unit dimension.
ALL_COLUMN_DIMENSIONS: Dict[str, str] = {**COLUMN_DIMENSIONS, **VIBRATION_COLUMNS}


def canonical_unit(dimension: str) -> str:
    """The library's standard display label for a dimension (first option)."""
    return UNIT_OPTIONS[dimension][0][0]


def options_for(dimension: str) -> List[Tuple[str, str]]:
    """``[(label, label)]`` pairs suitable for :func:`pumpflow.nodes.ui.combo`."""
    return [(label, label) for label, _pint in UNIT_OPTIONS[dimension]]


def pint_str(dimension: str, unit: str) -> str:
    """Pint unit string of a display label (``KeyError`` if the label is unknown).

    Examples
    --------
    >>> pint_str("capacity", "US GPM")
    'gallon/min'
    >>> pint_str("pressure", "bar")
    'bar'
    """
    for label, pint in UNIT_OPTIONS[dimension]:
        if label == unit:
            return pint
    raise KeyError(f"unknown {dimension} unit: {unit!r}")


_pint_str = pint_str  # backwards-compatible private alias


def atm_in(unit: str) -> float:
    """Standard atmosphere expressed in the pressure display unit ``unit``.

    Used to switch a pressure between gauge and absolute in its current unit.

    Examples
    --------
    >>> round(atm_in("bar"), 5)
    1.01325
    """
    return P_ATM.to(pint_str("pressure", unit)).magnitude


def label_for(dimension: str, pint_str: str) -> Optional[str]:
    """Display label of the ``UNIT_OPTIONS`` entry that is the same unit as ``pint_str``.

    Matches by Pint unit equality / unit conversion (not string equality), so
    ``"gal/min"`` finds ``"US GPM"`` and ``"°C"`` finds ``"°C"``.  Returns
    ``None`` when the dimension offers no such unit.

    Examples
    --------
    >>> label_for("capacity", "m**3/h")
    'm³/h'
    >>> label_for("head", "ft")
    'ft'
    >>> label_for("head", "psi") is None
    True
    """
    if pint_str == "%":
        pint_str = "percent"
    try:
        target = Q_(1, pint_str)
    except Exception:
        return None
    for label, pint in UNIT_OPTIONS.get(dimension, []):
        if Q_(1, pint).units == target.units:
            return label
        try:
            if abs(target.to(pint).magnitude - 1.0) < 1e-12:
                return label
        except Exception:
            continue
    return None


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
    if dimension in _DIRECT_STD:
        return Q_(value, pint_str(dimension, unit)).to(_DIRECT_STD[dimension]).magnitude
    return quantity_factory(Q_(value, pint_str(dimension, unit))).magnitude


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
    if dimension in _DIRECT_STD:
        return (
            Q_(value, pint_str(dimension, old_unit))
            .to(pint_str(dimension, new_unit))
            .magnitude
        )
    std = quantity_factory(Q_(value, pint_str(dimension, old_unit)))
    return std.to(pint_str(dimension, new_unit)).magnitude


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


# ---------------------------------------------------------------------------
# Column-header parsing ("Q [gpm]", "P_dis [psi g]", ...) for paste.
# ---------------------------------------------------------------------------

_HEADER_KEYS = {
    "q": "q",
    "p_suc": "p_suc",
    "p_dis": "p_dis",
    "t": "temp_c",
    "t_water": "temp_c",
    "temp": "temp_c",
    "temp_c": "temp_c",
    "n": "n",
    "p": "power",
    "power": "power",
    "head": "head",
    "h": "head",
    "η": "eff",
    "eta": "eff",
    "eff": "eff",
    "vib_de": "vib_de",
    "vib_de_f": "vib_de_f",
    "vib_nde": "vib_nde",
    "vib_nde_f": "vib_nde_f",
    "vib_de_filtered": "vib_de_f",
    "vib_nde_filtered": "vib_nde_f",
    "de": "vib_de",
    "de_f": "vib_de_f",
    "nde": "vib_nde",
    "nde_f": "vib_nde_f",
}

# Aliases are keyed by casefolded text.
_UNIT_ALIASES: Dict[str, Dict[str, str]] = {
    "capacity": {
        "gpm": "US GPM",
        "m3/h": "m³/h",
        "m**3/h": "m³/h",
        "lps": "l/s",
        "lpm": "l/min",
    },
    "temperature": {"degf": "°F", "f": "°F", "degc": "°C", "c": "°C"},
    "pressure": {
        "kgf/cm2": "kgf/cm²",
        "kgf/cm**2": "kgf/cm²",
        "kg/cm2": "kgf/cm²",
        "mh2o": "mH₂O",
        "mh₂o": "mH₂O",
        "meter_h2o": "mH₂O",
    },
    "speed": {"rev/s": "rev/s", "rps": "rev/s"},
    "efficiency": {"percent": "%", "pct": "%"},
    "power": {"cv": "CV"},
}

# "psig" -> ("psi", "g"), etc.
_REF_SUFFIX = {
    "barg": ("bar", "g"),
    "bara": ("bar", "a"),
    "psig": ("psi", "g"),
    "psia": ("psi", "a"),
}
_REF_WORDS = {"g": "g", "gauge": "g", "a": "a", "abs": "a", "absolute": "a"}


def _match_unit(dimension: str, text: str) -> str:
    t = text.strip()
    options = UNIT_OPTIONS[dimension]
    for label, _p in options:
        if label == t:
            return label
    fold = t.casefold()
    alias = _UNIT_ALIASES.get(dimension, {}).get(fold)
    if alias:
        return alias
    for label, pint in options:
        if label.casefold() == fold or pint.casefold() == fold:
            return label
    raise ValueError(f"unknown {dimension} unit: {text!r}")


def parse_unit_header(text: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Parse a column header such as ``"Q [gpm]"`` or ``"P_dis [psi g]"``.

    Returns ``(column_key, display_label, ref)`` where ``column_key`` is a Test
    Points key (``q``, ``p_suc``, ``p_dis``, ``temp_c``, ``n``, ``power``,
    ``head``, ``eff``), ``display_label`` is the matching ``UNIT_OPTIONS`` label
    (``None`` when no brackets) and ``ref`` is ``"g"``/``"a"`` for pressures
    (``None`` when absent).  Matching is case-insensitive.

    Raises
    ------
    ValueError
        Unknown column key or unknown unit.

    Examples
    --------
    >>> parse_unit_header("Q [gpm]")
    ('q', 'US GPM', None)
    >>> parse_unit_header("P_dis [psi g]")
    ('p_dis', 'psi', 'g')
    >>> parse_unit_header("T [°F]")
    ('temp_c', '°F', None)
    >>> parse_unit_header("Head")
    ('head', None, None)
    >>> parse_unit_header("Vib DE [in/s]")
    ('vib_de', 'in/s', None)
    """
    m = re.match(r"^\s*([^\[\]]+?)\s*(?:\[([^\]]*)\])?\s*$", str(text))
    if not m:
        raise ValueError(f"cannot parse column header: {text!r}")
    key = _HEADER_KEYS.get(re.sub(r"\s+", "_", m.group(1).strip().lower()))
    if key is None:
        raise ValueError(f"unknown column: {m.group(1)!r}")
    unit_text = (m.group(2) or "").strip()
    if not unit_text:
        return key, None, None
    dimension = ALL_COLUMN_DIMENSIONS[key]
    ref: Optional[str] = None
    if dimension == "pressure":
        tokens = unit_text.split()
        if len(tokens) > 1 and tokens[-1].casefold() in _REF_WORDS:
            ref = _REF_WORDS[tokens[-1].casefold()]
            unit_text = " ".join(tokens[:-1])
        elif len(tokens) == 1 and tokens[0].casefold() in _REF_SUFFIX:
            unit_text, ref = _REF_SUFFIX[tokens[0].casefold()]
    return key, _match_unit(dimension, unit_text), ref
