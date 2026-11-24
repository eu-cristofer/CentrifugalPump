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
parabola ``H = (h / q**2) * Q**2``).  :func:`affinity_intersection` intersects
that parabola with the fitted head polynomial (``numpy.roots``; SciPy is not a
dependency) and returns ``Q1``.  :func:`diameter_for_duty` then returns
``D = d_ref * q / Q1``; the speed analogue is ``N = N_ref * q / Q1`` (used by
:mod:`pump.catalogue`).
"""

from __future__ import annotations

import numpy as np

from .utilities.unit_conversion import Q_

__all__ = ["diameter_for_duty", "affinity_intersection"]


def _duty_values(q: Q_, h: Q_):
    """``(q_m3h, h_m)`` floats of a duty; ``ValueError`` unless both are > 0."""
    q_val = float(q.to("m**3/h").magnitude)
    h_val = float(h.to("m").magnitude)
    if not q_val > 0.0 or not h_val > 0.0:
        raise ValueError("The duty capacity and head must both be > 0.")
    return q_val, h_val


def affinity_intersection(curve, q: Q_, h: Q_) -> Q_:
    """Capacity ``Q1`` where the affinity parabola through ``(q, h)`` meets ``curve``.

    The parabola ``H = (h / q**2) * Q**2`` is intersected with the fitted head
    polynomial (``curve.fitter.head_coeffs``, Q in m**3/h, H in m).  Along this
    parabola, speed and diameter changes keep ``H / Q**2`` constant, so::

        N_new / N_ref = D_new / D_ref = q / Q1

    Parameters
    ----------
    curve : PerformanceCurve
        Curve at the reference speed / diameter.
    q, h : Q_
        Duty capacity and head (both must be > 0).

    Returns
    -------
    Q_
        ``Q1`` in m**3/h.

    Raises
    ------
    ValueError
        If the duty is not positive, or the parabola does not intersect the head
        polynomial inside the tested capacity range.  When several real roots lie
        in range, the one closest to ``q`` is used.
    """
    q_val, h_val = _duty_values(q, h)

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
    return Q_(q1, "m**3/h")


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
    ``Q1`` (:func:`affinity_intersection`); diameter affinity gives
    ``Q / Q1 = D / d_ref``.  When several real roots lie in range, the one
    closest to ``q`` is used.
    """
    q_val, _h_val = _duty_values(q, h)
    if not float(d_ref.to("mm").magnitude) > 0.0:
        raise ValueError("The reference impeller diameter must be > 0.")
    q1 = float(affinity_intersection(curve, q, h).to("m**3/h").magnitude)
    return d_ref * (q_val / q1)
