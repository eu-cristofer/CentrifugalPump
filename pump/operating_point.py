"""
operating_point
===============

Intersection of a pump performance curve with a system curve (UC-04).

The root of ``H_pump(Q) - H_system(Q)`` is bracketed on a grid over
``[0, q_max_factor * Q_max_tested]`` (first sign change) and refined with
:func:`pump.fitting.bisect_root`.  The pump head is the fitted polynomial
(``method="poly"``, the API 610 primary fit) or a natural cubic spline through
the test points (``method="spline"``).  ``extrapolated`` flags a solution
outside the tested capacity range.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .fitting import NaturalCubicSpline, bisect_root
from .utilities.unit_conversion import Q_

__all__ = ["OperatingPoint", "operating_point"]

_GRID = 600


@dataclass(frozen=True)
class OperatingPoint:
    """Solution of pump curve = system curve."""

    q: Q_
    h: Q_
    power: Optional[Q_]
    efficiency: Optional[Q_]
    extrapolated: bool


def operating_point(
    pump_curve,
    system_curve,
    method: str = "poly",
    q_max_factor: float = 1.5,
) -> OperatingPoint:
    """Operating point of ``pump_curve`` on ``system_curve``.

    Parameters
    ----------
    pump_curve : PerformanceCurve
    system_curve : SystemCurve or PipeSystemCurve
        Anything with ``head(q) -> Q_`` accepting a capacity array.
    method : {"poly", "spline"}
    q_max_factor : float
        Search up to ``q_max_factor * Q_max_tested``.

    Raises
    ------
    ValueError
        Unknown ``method``, or no intersection in the search range.
    """
    if method not in ("poly", "spline"):
        raise ValueError(f"method must be 'poly' or 'spline', got {method!r}.")
    if not float(q_max_factor) > 0:
        raise ValueError("q_max_factor must be > 0.")

    fitter = pump_curve.fitter
    caps = np.asarray(fitter.capacities, dtype=float)
    q_min, q_max = float(caps.min()), float(caps.max())
    if method == "spline":
        spline = NaturalCubicSpline(caps, fitter.heads)

        def pump_head(q):
            return spline(q)

    else:
        coeffs = fitter.head_coeffs

        def pump_head(q):
            return np.polyval(coeffs, q)

    def system_head(q):
        return np.asarray(
            system_curve.head(Q_(q, "m**3/h")).to("m").magnitude, dtype=float
        )

    def diff(q):
        return float(np.asarray(pump_head(q)) - system_head(q))

    hi = float(q_max_factor) * q_max
    grid = np.linspace(0.0, hi, _GRID + 1)
    d = np.asarray(pump_head(grid), dtype=float) - system_head(grid)

    root = None
    for i in range(len(grid) - 1):
        if d[i] == 0.0:
            root = float(grid[i])
            break
        if d[i] * d[i + 1] < 0.0 or d[i + 1] == 0.0:
            root = bisect_root(diff, float(grid[i]), float(grid[i + 1]))
            break
    if root is None:
        raise ValueError(
            "The pump curve and the system curve do not intersect in "
            f"[0, {hi:g}] m3/h (tested range {q_min:g}-{q_max:g} m3/h)."
        )

    q = Q_(root, "m**3/h")
    h = system_curve.head(q).to("m")
    try:
        power = pump_curve.predict_breaking_power(q)
    except Exception:
        power = None
    try:
        eff = pump_curve.predict_efficiency(q)
    except Exception:
        eff = None
    tol = 1e-9 * max(q_max, 1.0)
    extrapolated = bool(root < q_min - tol or root > q_max + tol)
    return OperatingPoint(
        q=q, h=h, power=power, efficiency=eff, extrapolated=extrapolated
    )
