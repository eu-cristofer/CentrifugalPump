"""
pump.vibration
==============

API 610 pump types and where their bearing-housing vibration is measured.

API 610 measures vibration "on the bearing housing(s) or equivalent
location(s)" at positions that depend on the pump type (8th ed. Figures 2-8A
and 2-8B; 11th ed. Figures 31-33; 12th ed. Figures 32-34), and judges it against
the limits of its family (8th ed. Tables 2-5 and 2-6; 11th/12th ed. Tables 8
and 9).  This module holds that mapping; the limits themselves are data in
``pump/standards/api610.toml`` (``[editions."N".vibration]``).

Each measurement location gives two readings, both bearing-housing velocity in
RMS: **overall** (unfiltered) and **filtered** (the largest discrete frequency
in the FFT spectrum).  Column keys are ``vib_<location>`` and
``vib_<location>_f``.

Examples
--------
>>> pump_family("OH6"), pump_family("BB2"), pump_family("VS4")
('OH6', 'BB', 'VS')
>>> [loc.label for loc in locations_for("OH6")]
['Gearbox housing']
>>> vibration_keys("BB1")
['vib_de', 'vib_de_f', 'vib_nde', 'vib_nde_f']
>>> limit_group("VS1"), limit_group("OH6")
('vs', 'oh_bb')
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "PUMP_TYPES",
    "Location",
    "LOCATIONS",
    "pump_family",
    "limit_group",
    "locations_for",
    "vibration_keys",
    "location_of_key",
    "HighSpeedRule",
    "plot_high_speed_chart",
]

#: API 610 pump type code -> description (8th ed. Table 1-1; 11th/12th Table 1).
PUMP_TYPES: Dict[str, str] = {
    "OH1": "Overhung, flexibly coupled, horizontal, foot-mounted",
    "OH2": "Overhung, flexibly coupled, horizontal, centreline-mounted",
    "OH3": "Overhung, flexibly coupled, vertical in-line with bearing bracket",
    "OH4": "Overhung, rigidly coupled, vertical in-line",
    "OH5": "Overhung, close-coupled, vertical in-line",
    "OH6": "Overhung, high-speed integrally geared",
    "BB1": "Between bearings, 1-2 stage, axially split",
    "BB2": "Between bearings, 1-2 stage, radially split",
    "BB3": "Between bearings, multistage, axially split",
    "BB4": "Between bearings, multistage, single casing, radially split",
    "BB5": "Between bearings, multistage, double casing, radially split",
    "VS1": "Vertically suspended, single casing, diffuser, discharge through column",
    "VS2": "Vertically suspended, single casing, volute, discharge through column",
    "VS3": "Vertically suspended, single casing, axial flow, discharge through column",
    "VS4": "Vertically suspended, single casing, volute, line shaft, separate discharge",
    "VS5": "Vertically suspended, single casing, cantilever, separate discharge",
    "VS6": "Vertically suspended, double casing, diffuser",
    "VS7": "Vertically suspended, double casing, volute",
}


@dataclass(frozen=True)
class Location:
    """A bearing-housing measurement location of a pump type."""

    key: str  # short id used in column keys: vib_<key>, vib_<key>_f
    label: str  # display label
    where: str  # what the standard figure shows
    short: str = ""  # compact column title


LOCATIONS: Dict[str, Location] = {
    "de": Location(
        "de",
        "Drive-end bearing housing",
        "pump bearing housing at the coupling end; horizontal, vertical and axial "
        "(8th Fig. 2-8A; 11th Fig. 31; 12th Fig. 32)",
        short="DE",
    ),
    "nde": Location(
        "nde",
        "Non-drive-end bearing housing",
        "pump bearing housing away from the coupling; horizontal, vertical and "
        "axial (8th Fig. 2-8A; 11th Fig. 31; 12th Fig. 32)",
        short="NDE",
    ),
    "drv": Location(
        "drv",
        "Driver mounting surface",
        "vertical in-line pumps: driver mounting surface (11th Fig. 33a / 12th "
        "Fig. 34a, drawn for OH3; applied here to OH4 and OH5 as well)",
        short="Driver",
    ),
    "pbh": Location(
        "pbh",
        "Pump bearing housing",
        "vertical in-line pumps: pump bearing housing (11th Fig. 33a / 12th "
        "Fig. 34a, drawn for OH3; applied here to OH4 and OH5 as well)",
        short="Pump BH",
    ),
    "gb": Location(
        "gb",
        "Gearbox housing",
        "integrally geared (OH6) pumps: gearbox housing, stud-mounted sensor "
        "(11th Fig. 33b; 12th Fig. 34b)",
        short="Gearbox",
    ),
    "tbh": Location(
        "tbh",
        "Thrust bearing housing / motor mounting flange",
        "vertically suspended pumps: pump thrust bearing housing or motor mounting "
        "flange (8th Fig. 2-8B; 11th Fig. 32; 12th Fig. 33)",
        short="Thrust BH",
    ),
}

#: Pump family -> measurement locations, in display order.
_FAMILY_LOCATIONS: Dict[str, Tuple[str, ...]] = {
    "OH": ("de", "nde"),  # horizontal overhung (OH1, OH2)
    "OH_VIL": ("drv", "pbh"),  # vertical in-line (OH3, OH4, OH5)
    "OH6": ("gb",),
    "BB": ("de", "nde"),
    "VS": ("tbh",),
}

#: Locations offered when no pump type is set (the historical default).
DEFAULT_LOCATIONS: Tuple[str, ...] = ("de", "nde")


def pump_family(pump_type: Optional[str]) -> Optional[str]:
    """``"OH"``, ``"OH_VIL"``, ``"OH6"``, ``"BB"`` or ``"VS"`` (``None`` if unknown)."""
    code = (pump_type or "").strip().upper()
    if code not in PUMP_TYPES:
        return None
    if code in ("OH3", "OH4", "OH5"):
        return "OH_VIL"
    if code == "OH6":
        return "OH6"
    return code[:2]


def limit_group(pump_type: Optional[str]) -> str:
    """Which limit table applies: ``"vs"`` (Table 9 / 2-6) or ``"oh_bb"`` (Table 8 / 2-5)."""
    return "vs" if pump_family(pump_type) == "VS" else "oh_bb"


def locations_for(pump_type: Optional[str]) -> List[Location]:
    """Measurement locations of a pump type (drive end / non-drive end if unset)."""
    family = pump_family(pump_type)
    keys = (
        _FAMILY_LOCATIONS.get(family, DEFAULT_LOCATIONS)
        if family
        else DEFAULT_LOCATIONS
    )
    return [LOCATIONS[k] for k in keys]


def vibration_keys(pump_type: Optional[str]) -> List[str]:
    """Column keys (overall, filtered) for every location of a pump type."""
    keys: List[str] = []
    for loc in locations_for(pump_type):
        keys += [f"vib_{loc.key}", f"vib_{loc.key}_f"]
    return keys


def location_of_key(key: str) -> Tuple[Location, bool]:
    """``(Location, filtered)`` of a column key such as ``vib_gb_f``.

    Raises
    ------
    KeyError
        Not a vibration column key.
    """
    body = key[len("vib_") :] if key.startswith("vib_") else ""
    filtered = body.endswith("_f")
    loc = body[:-2] if filtered else body
    if loc not in LOCATIONS:
        raise KeyError(key)
    return LOCATIONS[loc], filtered


#: Every vibration column key, for any pump type.
ALL_VIBRATION_KEYS: Tuple[str, ...] = tuple(
    f"vib_{k}{suffix}" for k in LOCATIONS for suffix in ("", "_f")
)


# --------------------------------------------------------------------------- #
# High-speed / high-power allowance (11th ed. Figure 34, 12th ed. Figure 35)
# --------------------------------------------------------------------------- #
def _two_significant(value: float) -> float:
    """API 610: limits calculated from the basic limits are rounded to two
    significant figures (Table 8 / Table 9 notes)."""
    from math import floor, log10

    if value == 0:
        return 0.0
    digits = 1 - int(floor(log10(abs(value))))
    return round(value, digits)


@dataclass(frozen=True)
class HighSpeedRule:
    """
    The curve family of the high-speed vibration figure.

    ``v_u = base * (n / n_ref) ** speed_exponent * (P / p_ref) ** power_exponent``,
    kept between ``base`` and ``cap`` (the figure's "transition from 3.0 mm/s to
    4.5 mm/s"); ``P`` below ``p_ref`` uses ``p_ref`` (its "P <= 300 kW" curve).
    Limits are rounded to two significant figures, as the standard's tables
    require.  Discrete frequencies: ``v_f = discrete_ratio * v_u``.

    Examples
    --------
    >>> from pump.utilities.unit_conversion import Q_
    >>> rule = HighSpeedRule()
    >>> round(rule.overall(Q_(10212, "rpm"), Q_(25, "kW")).magnitude, 2)
    4.1
    >>> round(rule.overall(Q_(3600, "rpm"), Q_(3000, "kW")).magnitude, 2)  # capped
    4.5
    >>> rule.overall(Q_(2000, "rpm"), Q_(1000, "kW")).magnitude  # big, slow pump
    3.2
    >>> rule.overall(Q_(1000, "rpm"), Q_(300, "kW")).magnitude  # never below 3.0
    3.0
    >>> rule.applies(Q_(3000, "rpm"), Q_(200, "kW"))
    False
    """

    base: Any = None  # Q_ mm/s
    cap: Any = None
    n_ref: Any = None  # Q_ rpm
    p_ref: Any = None  # Q_ kW
    speed_exponent: float = 0.30
    power_exponent: float = 0.21
    discrete_ratio: float = 0.67
    source: str = ""
    verified: bool = False

    def __post_init__(self):
        from .utilities.unit_conversion import Q_

        defaults = {
            "base": Q_(3.0, "mm/s"),
            "cap": Q_(4.5, "mm/s"),
            "n_ref": Q_(3600, "rpm"),
            "p_ref": Q_(300, "kW"),
        }
        for name, value in defaults.items():
            if getattr(self, name) is None:
                object.__setattr__(self, name, value)

    def applies(self, speed, power_per_stage=None) -> bool:
        """True above the reference speed or the reference power per stage."""
        fast = speed is not None and speed > self.n_ref
        big = power_per_stage is not None and power_per_stage > self.p_ref
        return bool(fast or big)

    def curve_value(self, speed_rpm: float, power_kw: Optional[float] = None) -> float:
        """Unrounded overall limit in mm/s (the chart's continuous curve)."""
        p_ref = float(self.p_ref.to("kW").magnitude)
        p = p_ref if power_kw is None else max(float(power_kw), p_ref)
        base = float(self.base.to("mm/s").magnitude)
        v = (
            base
            * (float(speed_rpm) / float(self.n_ref.to("rpm").magnitude))
            ** self.speed_exponent
            * (p / p_ref) ** self.power_exponent
        )
        return min(max(v, base), float(self.cap.to("mm/s").magnitude))

    def overall(self, speed, power_per_stage=None):
        """Overall limit (mm/s RMS, two significant figures)."""
        p = None if power_per_stage is None else power_per_stage.to("kW").magnitude
        v = self.curve_value(speed.to("rpm").magnitude, p)
        return type(self.base)(_two_significant(v), "mm/s")

    def filtered(self, speed, power_per_stage=None):
        """Discrete-frequency limit: ``discrete_ratio`` x the overall limit."""
        o = self.overall(speed, power_per_stage)
        return type(o)(
            _two_significant(float(o.magnitude) * self.discrete_ratio), "mm/s"
        )

    @classmethod
    def from_table(cls, table) -> Optional["HighSpeedRule"]:
        if not table:
            return None
        from .utilities.unit_conversion import Q_

        def q(key):
            if table.get(key) is None:
                return None
            number, unit = str(table[key]).split(None, 1)
            return Q_(float(number), unit.strip())

        return cls(
            base=q("base"),
            cap=q("cap"),
            n_ref=q("n_ref"),
            p_ref=q("p_ref"),
            speed_exponent=float(table.get("speed_exponent", 0.30)),
            power_exponent=float(table.get("power_exponent", 0.21)),
            discrete_ratio=float(table.get("discrete_ratio", 0.67)),
            source=str(table.get("source", "")),
            verified=bool(table.get("verified", False)),
        )


def plot_high_speed_chart(
    rule: HighSpeedRule,
    speed=None,
    power_per_stage=None,
    title: str = "",
    labels: Optional[Dict[str, str]] = None,
) -> bytes:
    """
    The high-speed vibration chart (overall limit vs speed, one curve per power
    per stage) as PNG bytes, with the pump's operating point marked.

    Curves for 300 (and below), 500, 700, 1000, 1500, 2000 and 3000 (and above)
    kW per stage, log speed axis 500-30 000 r/min, as in the standard's figure.
    """
    import io

    import matplotlib

    matplotlib.use("Agg")
    import numpy as np
    from matplotlib.figure import Figure

    from .utilities.unit_conversion import Q_

    lab = {
        "x": "Rotational speed (r/min)",
        "y": "Overall vibration limit (mm/s RMS)",
        "pump": "This pump",
        "curve": "{p} kW per stage",
    }
    lab.update(labels or {})
    speeds = np.geomspace(500, 30000, 300)
    fig = Figure(figsize=(7.0, 4.2), dpi=150)
    ax = fig.subplots()
    powers = (300, 500, 700, 1000, 1500, 2000, 3000)
    for p in powers:
        ys = [rule.curve_value(n, p) for n in speeds]
        name = lab["curve"].format(
            p=f"≤{p}" if p == 300 else (f"≥{p}" if p == 3000 else p)
        )
        ax.plot(speeds, ys, lw=1.2, label=name)
    if speed is not None:
        n = float(speed.to("rpm").magnitude)
        v = rule.overall(speed, power_per_stage).magnitude
        ax.plot([n], [v], "k*", ms=13, label=f"{lab['pump']}: {v:.2f} mm/s")
        ax.axvline(n, color="k", ls=":", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlim(500, 30000)
    ax.set_ylim(2.0, 5.0)
    ax.set_xlabel(lab["x"])
    ax.set_ylabel(lab["y"])
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=7, loc="upper left")
    if title:
        ax.set_title(title, fontsize=10)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    return buf.getvalue()
