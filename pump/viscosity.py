"""
viscosity
=========

Viscosity correction of a water-test performance curve (HI 9.6.7 / ISO TR 17766).

Equation source
---------------
The equations are ANSI/HI 9.6.7-2010 Eq. 2-7 as reproduced by
midstreamcalculator.com (pump viscosity correction calculator, which cites the
equation numbers).  They were cross-checked independently (SI vs US constants,
continuity at B = 1, the legacy HI chart field example, hand values) but **NOT
against the standard text**; confirm against the purchased standard before
relying on a result for acceptance.

With ``nu`` in cSt, ``H`` in ft (per stage), ``Q`` in gpm and ``N`` in rpm,
all at the water best-efficiency point (BEP-W)::

    B     = 26.6 * nu**0.5 * H**0.0625 / (Q**0.375 * N**0.25)     (Eq. 3)
    C_Q   = 2.71 ** (-0.165 * log10(B)**3.15)                      (Eq. 4)
    C_H   = 1 - (1 - C_Q) * (Q / Q_BEP)**0.75   (C_H,BEP = C_Q)    (Eq. 5, 6)
    C_eta = B ** (-0.0547 * B**0.69)                               (Eq. 7)

Valid for 1 < B < 40; for B <= 1 there is no correction and for B >= 40 a
``UserWarning`` ("outside method validity") is raised while the values are
still returned.

Functions
---------
- b_parameter: the dimensionless B parameter from Pint quantities.
- correction_factors: ``(C_Q, C_H, C_eta)`` for a given B (and Q / Q_BEP).

>>> correction_factors(0.5)
(1.0, 1.0, 1.0)
"""

import math
import warnings

from .utilities.unit_conversion import Q_

__all__ = ["b_parameter", "correction_factors"]

#: Upper validity limit of the method (exclusive).
B_MAX = 40.0


def b_parameter(nu: Q_, q_bep_w: Q_, h_bep_w: Q_, n: Q_) -> float:
    """
    HI 9.6.7 viscosity parameter B (ANSI/HI 9.6.7-2010 Eq. 3, US-unit form).

    The equations are ANSI/HI 9.6.7-2010 Eq. 2-7 as reproduced by
    midstreamcalculator.com; they were cross-checked independently but NOT
    against the standard text.  The calculation is done in one unit system
    (US: gpm, ft per stage, rpm, cSt, constant 26.6); the inputs are Pint
    quantities converted with ``.to()``.

    Parameters
    ----------
    nu : Q_
        Kinematic viscosity of the pumped liquid (any kinematic-viscosity unit).
    q_bep_w : Q_
        Capacity at the best-efficiency point on water.
    h_bep_w : Q_
        Head **per stage** at the best-efficiency point on water.
    n : Q_
        Speed of rotation.

    Returns
    -------
    float
        The dimensionless parameter B.

    Raises
    ------
    ValueError
        If any input is not strictly positive.
    """
    nu_cst = float(nu.to("cSt").magnitude)
    q_gpm = float(q_bep_w.to("gallon/minute").magnitude)
    h_ft = float(h_bep_w.to("ft").magnitude)
    n_rpm = float(n.to("rpm").magnitude)
    if min(nu_cst, q_gpm, h_ft, n_rpm) <= 0.0:
        raise ValueError(
            "b_parameter needs strictly positive viscosity, capacity, head and speed."
        )
    return 26.6 * nu_cst**0.5 * h_ft**0.0625 / (q_gpm**0.375 * n_rpm**0.25)


def correction_factors(b: float, q_ratio: float = 1.0) -> tuple:
    """
    HI 9.6.7 correction factors ``(C_Q, C_H, C_eta)`` (ANSI/HI 9.6.7-2010 Eq. 4-7).

    The equations are ANSI/HI 9.6.7-2010 Eq. 2-7 as reproduced by
    midstreamcalculator.com; they were cross-checked independently but NOT
    against the standard text.

    Parameters
    ----------
    b : float
        The parameter from :func:`b_parameter`.
    q_ratio : float, optional
        Water capacity over the water BEP capacity, ``Q_W / Q_BEP-W`` (default 1,
        i.e. the factors at the BEP, where ``C_H = C_Q``).

    Returns
    -------
    tuple of float
        ``(C_Q, C_H, C_eta)``; exactly ``(1.0, 1.0, 1.0)`` for ``b <= 1``.

    Warns
    -----
    UserWarning
        For ``b >= 40`` ("outside method validity"); the values are still returned.

    Raises
    ------
    ValueError
        If ``q_ratio`` is negative.
    """
    if q_ratio < 0.0:
        raise ValueError("q_ratio (Q / Q_BEP) must be >= 0.")
    if b <= 1.0:
        return (1.0, 1.0, 1.0)
    if b >= B_MAX:
        warnings.warn(
            f"B = {b:.2f} is outside method validity (HI 9.6.7 is valid for "
            f"1 < B < {B_MAX:g}); the correction factors are extrapolated.",
            UserWarning,
            stacklevel=2,
        )
    c_q = 2.71 ** (-0.165 * math.log10(b) ** 3.15)
    c_h = 1.0 - (1.0 - c_q) * q_ratio**0.75
    c_eta = b ** (-0.0547 * b**0.69)
    return (c_q, c_h, c_eta)
