"""
trim
====

Impeller trim helpers (UC-07).

Method
------
Pure **diameter affinity** (the standard affinity approximation, the same
family of laws as the speed affinity used by
:meth:`pump.PerformanceCurve.to_speed`)::

    Q2 / Q1 = D2 / D1
    H2 / H1 = (D2 / D1) ** 2
    P2 / P1 = (D2 / D1) ** 3
    eta2    = eta1                (efficiency invariant)

The approximation degrades for large trims, so
:meth:`pump.PerformanceCurve.to_diameter` warns beyond ``max_trim`` (default
5 %).  HI-style trim corrections (e.g. exponent / efficiency corrections for
large trims) are out of scope.

Solving for a diameter
----------------------
A duty point ``(q, h)`` served at diameter ``D`` corresponds, on the reference
diameter ``d_ref``, to the point with the same ``H / Q**2`` ratio (the affinity
parabola ``H = (h / q**2) * Q**2``).  :func:`diameter_for_duty` intersects that
parabola with the fitted head polynomial (``numpy.roots``; SciPy is not a
dependency) and returns ``D = d_ref * q / Q1``.
"""

from __future__ import annotations

import numpy as np

from .utilities.unit_conversion import Q_

__all__ = ["diameter_for_duty"]


def diameter_for_duty(curve, q: Q_, h: Q_, d_ref: Q_) -> Q_:
    """Impeller diameter that makes ``curve`` pass through the duty ``(q, h)``.

    Parameters
    ----------
    curve : PerformanceCurve
        Curve measured / defined at the reference diameter ``d_ref``.  Its fitted
        head polynomial (``curve.fitter.head_coeffs``, Q in m**3/h, H in m) is
        used.
    q : Q_
        Duty capacity (must be > 0).
    h : Q_
        Duty head (must be > 0).
    d_ref : Q_
        Impeller diameter the curve corresponds to.

    Returns
    -------
    Q_
        The required diameter, in the unit of ``d_ref``.

    Raises
    ------
    ValueError
        If the duty is not positive, or the affinity parabola through the duty
        does not intersect the head polynomial inside the tested capacity range.

    Notes
    -----
    The parabola ``H = (h / q**2) * Q**2`` intersects the fitted head curve at
    ``Q1``; diameter affinity gives ``Q / Q1 = D / d_ref``.  When several real
    roots lie in range, the one closest to ``q`` is used.
    """
    q_val = float(q.to("m**3/h").magnitude)
    h_val = float(h.to("m").magnitude)
    if not q_val > 0.0 or not h_val > 0.0:
        raise ValueError("The duty capacity and head must both be > 0.")
    if not float(d_ref.to("mm").magnitude) > 0.0:
        raise ValueError("The reference impeller diameter must be > 0.")

    coeffs = np.array(curve.fitter.head_coeffs, dtype=float)
    if coeffs.size < 3:  # make sure a Q**2 coefficient exists
        coeffs = np.concatenate([np.zeros(3 - coeffs.size), coeffs])
    poly = coeffs.copy()
    poly[-3] -= h_val / q_val**2  # head polynomial minus the parabola

    caps = np.asarray(curve.fitter.capacities, dtype=float)
    q_min, q_max = float(caps.min()), float(caps.max())
    tol = 1e-9 * max(1.0, abs(q_max))

    candidates = []
    for root in np.roots(poly):
        if abs(root.imag) > 1e-9 * max(1.0, abs(root.real)):
            continue
        r = float(root.real)
        if r > 0.0 and q_min - tol <= r <= q_max + tol:
            candidates.append(r)
    if not candidates:
        raise ValueError(
            f"No intersection of the affinity parabola through the duty "
            f"({q_val:g} m3/h, {h_val:g} m) with the fitted head curve inside "
            f"the tested range [{q_min:g}, {q_max:g}] m3/h: the duty cannot be "
            f"reached by impeller trimming of this curve."
        )
    q1 = min(candidates, key=lambda r: abs(r - q_val))
    return d_ref * (q_val / q1)
