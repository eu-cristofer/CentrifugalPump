"""
npsh
====

Net Positive Suction Head (NPSH) tools for the Performance test (UC-05).

- :func:`npsh_available` computes NPSHa from the suction conditions.
- :func:`npsh3_from_sweep` finds NPSH3 (3 % head drop) from a suction sweep.
- :class:`NPSHrCurve` is a least-squares polynomial of NPSHr versus capacity.
- :func:`npsh_margin` / :func:`check_npsh` compare NPSHa with NPSHr against
  an (optional) margin rule held in :class:`NPSHCriteria`.
- :func:`plot_npsh` draws the NPSHr points, the fit, NPSHa and the rated flow.

No margin rule is shipped as a real criterion: the seeded criteria are *not
configured* (``min_ratio = None``, ``min_margin = None``), so a check without a
rule reports ``status == "info"`` and never a pass/fail.

Examples
--------
>>> from pump import Q_, Fluid
>>> from pump.utilities.pressure import Pressure
>>> fluid = Fluid("w", density=Q_(1000, "kg/m**3"))
>>> p = Pressure(Q_(98066.5, "Pa"), "a")
>>> h = npsh_available(p, fluid, Q_(0, "m**3/h"), vapour_pressure=Q_(0, "Pa"))
>>> round(h.to("m").magnitude, 6)
10.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO
from typing import Mapping, Optional, Sequence

import numpy as np

from .constants import G
from .utilities.pressure import Pressure
from .utilities.unit_conversion import Q_

__all__ = [
    "npsh_available",
    "npsh3_from_sweep",
    "NPSHrCurve",
    "npsh_margin",
    "NPSHCriteria",
    "NPSHResult",
    "check_npsh",
    "plot_npsh",
]

_NOT_CONFIGURED_SOURCE = "not configured \u2014 enter the client/API margin rule"


def _parse_quantity(text) -> Q_:
    """Parse ``"1 m"`` into a Pint quantity."""
    number, unit = str(text).split(None, 1)
    return Q_(float(number), unit.strip())


# --------------------------------------------------------------------------- #
# NPSH available
# --------------------------------------------------------------------------- #
def npsh_available(
    p_suction: Pressure,
    fluid,
    q: Q_,
    suction_id: Optional[Q_] = None,
    z_suction: Q_ = Q_(0, "m"),
    vapour_pressure: Optional[Q_] = None,
) -> Q_:
    """
    NPSH available at the pump suction, in metres.

    ``NPSHa = (p_s,abs - p_v) / (rho g) + v_s**2 / (2 g) + z_s``

    Parameters
    ----------
    p_suction : Pressure
        Suction pressure with its gauge/absolute reference.
    fluid : Fluid
        Provides ``density`` and, unless ``vapour_pressure`` is given, a
        ``vapour_pressure`` attribute (``Water`` has one).
    q : Q_
        Capacity (for the suction velocity head).
    suction_id : Q_, optional
        Suction pipe inside diameter; without it the velocity head is zero.
    z_suction : Q_, optional
        Elevation of the pressure tap above the pump reference (default 0 m).
    vapour_pressure : Q_, optional
        Absolute vapour pressure; defaults to ``fluid.vapour_pressure``.

    Raises
    ------
    ValueError
        If ``p_suction`` is not a :class:`Pressure`, or no vapour pressure is
        available.

    Examples
    --------
    >>> from pump import Q_, Fluid
    >>> from pump.utilities.pressure import Pressure
    >>> fluid = Fluid("w", density=Q_(1000, "kg/m**3"))
    >>> gauge = Pressure(Q_(0, "bar"), "g")
    >>> h = npsh_available(gauge, fluid, Q_(0, "m**3/h"), vapour_pressure=Q_(0, "Pa"))
    >>> round(h.to("m").magnitude, 3)
    10.332
    >>> npsh_available(gauge, fluid, Q_(0, "m**3/h"))
    Traceback (most recent call last):
        ...
    ValueError: No vapour pressure: pass vapour_pressure or use a fluid that has one (e.g. Water).
    """
    if not isinstance(p_suction, Pressure):
        raise ValueError("p_suction must be a Pressure (explicit gauge/absolute).")
    if vapour_pressure is None:
        vapour_pressure = getattr(fluid, "vapour_pressure", None)
    if vapour_pressure is None:
        raise ValueError(
            "No vapour pressure: pass vapour_pressure or use a fluid that has one "
            "(e.g. Water)."
        )
    rho = fluid.density
    pressure_head = ((p_suction.absolute() - vapour_pressure) / (rho * G)).to("m")
    if suction_id is not None:
        velocity: Q_ = (q / (math.pi * suction_id**2 / 4)).to("m/s")
        velocity_head: Q_ = (velocity**2 / (2 * G)).to("m")
    else:
        velocity_head = Q_(0.0, "m")
    total = pressure_head + velocity_head + z_suction.to("m")
    return Q_(float(total.to("m").magnitude), "m")


# --------------------------------------------------------------------------- #
# NPSH3 from a suction sweep
# --------------------------------------------------------------------------- #
def npsh3_from_sweep(
    npsha_values: Sequence[Q_], heads: Sequence[Q_], drop: float = 0.03
) -> Q_:
    """
    NPSH3 from a suction sweep at one flow.

    The sweep is a series of decreasing NPSHa values with the head measured at
    each.  The reference head is the mean of the first two (highest-NPSHa)
    points; NPSH3 is the NPSHa at which the head has fallen to
    ``(1 - drop) * reference``, by linear interpolation between the bracketing
    points.

    Raises
    ------
    ValueError
        If the lengths differ, fewer than 3 points are given, or the head drop
        is never reached.

    Examples
    --------
    >>> from pump import Q_
    >>> x = [Q_(v, "m") for v in (8, 7, 6, 5, 4, 3)]
    >>> h = [Q_(v, "m") for v in (100, 100, 100, 90, 80, 70)]
    >>> round(npsh3_from_sweep(x, h).to("m").magnitude, 6)
    5.7
    >>> npsh3_from_sweep(x, [Q_(100, "m")] * 6)
    Traceback (most recent call last):
        ...
    ValueError: The head never dropped by 3 % in the sweep.
    """
    x = np.array([v.to("m").magnitude for v in npsha_values], dtype=float)
    h = np.array([v.to("m").magnitude for v in heads], dtype=float)
    if x.size != h.size:
        raise ValueError("npsha_values and heads must have the same length.")
    if x.size < 3:
        raise ValueError("At least 3 sweep points are needed.")
    order = np.argsort(-x, kind="stable")
    x, h = x[order], h[order]
    target = (1.0 - drop) * float(h[:2].mean())
    for j in range(1, x.size):
        if h[j] <= target:
            x0, x1, h0, h1 = x[j - 1], x[j], h[j - 1], h[j]
            xs = x1 if h0 == h1 else x0 + (target - h0) * (x1 - x0) / (h1 - h0)
            return Q_(float(xs), "m")
    raise ValueError(f"The head never dropped by {drop * 100:g} % in the sweep.")


# --------------------------------------------------------------------------- #
# NPSH required curve
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NPSHrCurve:
    """
    Least-squares polynomial of NPSHr versus capacity.

    Parameters
    ----------
    q : tuple of Q_
        Capacities and the NPSHr measured at each.
    npshr : tuple of Q_
        Capacities and the NPSHr measured at each.
    degree : int, optional
        Polynomial degree (default 2); reduced to ``n - 1`` for few points.

    Examples
    --------
    >>> from pump import Q_
    >>> c = NPSHrCurve(
    ...     (Q_(0, "m**3/h"), Q_(100, "m**3/h")), (Q_(1, "m"), Q_(2, "m"))
    ... )
    >>> round(c(Q_(50, "m**3/h")).to("m").magnitude, 6)
    1.5
    >>> c.extrapolated(Q_(150, "m**3/h")), c.extrapolated(Q_(50, "m**3/h"))
    (True, False)
    """

    q: tuple
    npshr: tuple
    degree: int = 2

    def __post_init__(self) -> None:
        q, r = tuple(self.q), tuple(self.npshr)
        if not q or len(q) != len(r):
            raise ValueError("q and npshr must be non-empty and of equal length.")
        object.__setattr__(self, "q", q)
        object.__setattr__(self, "npshr", r)

    def _xy(self):
        x = np.array([v.to("m**3/h").magnitude for v in self.q], dtype=float)
        y = np.array([v.to("m").magnitude for v in self.npshr], dtype=float)
        return x, y

    def _coefficients(self) -> np.ndarray:
        x, y = self._xy()
        degree = max(0, min(int(self.degree), np.unique(x).size - 1))
        return np.polyfit(x, y, degree)

    def __call__(self, q: Q_) -> Q_:
        """NPSHr (metres) at capacity ``q`` from the fitted polynomial."""
        x = q.to("m**3/h").magnitude
        raw = np.polyval(self._coefficients(), x)
        value = float(raw) if np.ndim(raw) == 0 else raw
        return Q_(value, "m")

    def at_rated(self, q_rated: Q_) -> Q_:
        """NPSHr at the rated capacity."""
        return self(q_rated)

    def extrapolated(self, q: Q_) -> bool:
        """True when ``q`` lies outside the measured capacity range."""
        x, _ = self._xy()
        value = q.to("m**3/h").magnitude
        return bool(np.any(value < x.min()) or np.any(value > x.max()))


# --------------------------------------------------------------------------- #
# Margin, criteria and check
# --------------------------------------------------------------------------- #
def npsh_margin(npsha: Q_, npshr: Q_) -> dict:
    """
    Ratio ``NPSHa / NPSHr`` and margin ``NPSHa - NPSHr``.

    Examples
    --------
    >>> from pump import Q_
    >>> m = npsh_margin(Q_(2.4, "m"), Q_(1.2, "m"))
    >>> round(m["ratio"], 6), round(m["margin"].to("m").magnitude, 6)
    (2.0, 1.2)
    """
    denominator = float(npshr.to("m").magnitude)
    ratio = (
        float(npsha.to("m").magnitude) / denominator
        if denominator > 0
        else float("inf")
    )
    margin = Q_(float((npsha - npshr).to("m").magnitude), "m")
    return {"ratio": ratio, "margin": margin}


@dataclass(frozen=True)
class NPSHCriteria:
    """
    NPSH margin rule.  Seeded as *not configured*: both limits are ``None``.

    Attributes
    ----------
    min_ratio : float or None
        Minimum ``NPSHa / NPSHr``.
    min_margin : Q_ or None
        Minimum ``NPSHa - NPSHr`` (a length).
    npshr_tol_plus : float or None
        Allowed relative excess of the tested NPSHr over the *quoted* NPSHr at
        the rated point (API 610 "Rated NPSH +0 %" is ``0.0``).  Judged only
        when a quoted value is given to :func:`check_npsh`.
    source : str
        Provenance of the rule.
    verified : bool
        True only when the rule was checked against the standard / client text.

    Examples
    --------
    >>> NPSHCriteria().configured
    False
    >>> NPSHCriteria.from_table({"min_ratio": 1.3, "min_margin": "0.6 m"}).configured
    True
    """

    min_ratio: Optional[float] = None
    min_margin: Optional[Q_] = None
    npshr_tol_plus: Optional[float] = None
    source: str = _NOT_CONFIGURED_SOURCE
    verified: bool = False

    @property
    def configured(self) -> bool:
        """True when at least one margin limit (ratio or margin) is set."""
        return self.min_ratio is not None or self.min_margin is not None

    @classmethod
    def from_table(cls, table: Optional[Mapping]) -> "NPSHCriteria":
        """Build from a TOML ``npsh`` table (missing limits stay ``None``)."""
        table = table or {}
        min_ratio = table.get("min_ratio")
        min_margin = table.get("min_margin")
        tol = table.get("npshr_tol_plus")
        return cls(
            min_ratio=float(min_ratio) if min_ratio is not None else None,
            min_margin=_parse_quantity(min_margin) if min_margin is not None else None,
            npshr_tol_plus=float(tol) if tol is not None else None,
            source=str(table.get("source", _NOT_CONFIGURED_SOURCE)),
            verified=bool(table.get("verified", False)),
        )


@dataclass(frozen=True)
class NPSHResult:
    """
    Outcome of :func:`check_npsh`.

    ``status`` is ``"pass"``, ``"fail"`` or ``"info"`` (no rule configured:
    ratio and margin are reported but nothing is judged).  ``quoted_ok`` is the
    "rated NPSH" check (tested NPSHr against the quoted NPSHr), ``None`` when no
    quoted value or no tolerance was given.
    """

    npsha: Q_
    npshr: Q_
    ratio: float
    margin: Q_
    status: str
    criteria: NPSHCriteria
    verified: bool
    npshr_quoted: Optional[Q_] = None
    quoted_ok: Optional[bool] = None


def check_npsh(
    npsha: Q_,
    npshr: Q_,
    criteria: Optional[NPSHCriteria] = None,
    npshr_quoted: Optional[Q_] = None,
) -> NPSHResult:
    """
    Compare NPSHa with NPSHr under an optional margin rule.

    The status is ``"info"`` when no limit is configured; otherwise it is
    ``"fail"`` if any configured limit is not met and ``"pass"`` if all are.
    With ``npshr_quoted`` (the datasheet / proposal NPSHr at rated flow) and a
    ``criteria.npshr_tol_plus``, the tested NPSHr must also not exceed the
    quoted value by more than that fraction (API 610: +0 %).

    Examples
    --------
    >>> from pump import Q_
    >>> check_npsh(Q_(2.4, "m"), Q_(1.2, "m")).status
    'info'
    >>> rule = NPSHCriteria(min_ratio=1.3, min_margin=Q_(0.6, "m"))
    >>> check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), rule).status
    'pass'
    >>> check_npsh(Q_(1.4, "m"), Q_(1.2, "m"), rule).status
    'fail'
    >>> api = NPSHCriteria(npshr_tol_plus=0.0)
    >>> check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), api, npshr_quoted=Q_(1.1, "m")).status
    'fail'
    >>> check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), api, npshr_quoted=Q_(1.3, "m")).quoted_ok
    True
    """
    criteria = criteria if criteria is not None else NPSHCriteria()
    m = npsh_margin(npsha, npshr)
    checks = []
    if criteria.min_ratio is not None:
        checks.append(m["ratio"] >= criteria.min_ratio)
    if criteria.min_margin is not None:
        checks.append(bool(m["margin"] >= criteria.min_margin))
    quoted_ok = None
    if npshr_quoted is not None and criteria.npshr_tol_plus is not None:
        limit: Q_ = npshr_quoted * (1.0 + criteria.npshr_tol_plus)
        quoted_ok = bool(npshr <= limit * (1.0 + 1e-9))
        checks.append(quoted_ok)
    if not checks:
        status = "info"
    else:
        status = "pass" if all(checks) else "fail"
    return NPSHResult(
        npsha=npsha,
        npshr=npshr,
        ratio=m["ratio"],
        margin=m["margin"],
        status=status,
        criteria=criteria,
        verified=criteria.verified,
        npshr_quoted=npshr_quoted,
        quoted_ok=quoted_ok,
    )


# --------------------------------------------------------------------------- #
# Plot
# --------------------------------------------------------------------------- #
def plot_npsh(
    curve: NPSHrCurve,
    npsha: Optional[Q_] = None,
    rated_q: Optional[Q_] = None,
) -> BytesIO:
    """
    PNG ``BytesIO``: NPSHr points, the polynomial fit, a horizontal NPSHa line
    and a vertical rated-capacity line.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    x, y = curve._xy()
    lo, hi = float(x.min()), float(x.max())
    if rated_q is not None:
        rq = float(rated_q.to("m**3/h").magnitude)
        lo, hi = min(lo, rq), max(hi, rq)
    xs = np.linspace(lo, hi, 200)
    fit = np.asarray(curve(Q_(xs, "m**3/h")).magnitude, dtype=float)

    fig = Figure(figsize=(8, 4.5))
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.plot(x, y, "o", label="NPSHr")
    ax.plot(xs, fit, "-", label="NPSHr fit")
    if npsha is not None:
        ax.axhline(
            float(npsha.to("m").magnitude), ls="--", color="tab:green", label="NPSHa"
        )
    if rated_q is not None:
        ax.axvline(rq, ls=":", color="tab:red", label="Rated Q")
    ax.set_xlabel("Capacity [m\u00b3/h]")
    ax.set_ylabel("NPSH [m]")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    return buf
