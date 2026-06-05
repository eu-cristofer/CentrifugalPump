"""
mathx
=====

Maths ported into the UI layer from the reference notebook
(``pump_api610_performance 1.ipynb``) because they are **not** in the ``pump``
library yet (UI_SPEC §4 note):

- :class:`NaturalCubicSpline` — the notebook's cell-8 secondary fit, a natural
  cubic spline the user can toggle on the Performance Plot (polynomial deg-3 is
  the API-610 primary curve; this is the secondary).
- :func:`water_density_kgm3` — water density as a function of temperature, used
  by the Test Points Table to compute the read-only ``Head`` column from the
  measured suction/discharge pressures.

.. note::
   These are faithful, standard implementations.  If the notebook ships exact
   coefficients for ``water_density_kgm3`` or a specific spline variant, drop
   them in here (or, preferred, contribute them to ``pump``) — the rest of the
   app only depends on the public methods below.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Water density polynomial (kg/m³ vs °C)
# ---------------------------------------------------------------------------

# Standard 4th-order fit, valid ~0–100 °C at 1 atm (Kell-style).  At 4 °C this
# peaks near 999.97 kg/m³; at 34 °C ≈ 994.4 kg/m³.
_WATER_RHO_COEFFS = (
    999.85308,        # T^0
    6.32693e-2,       # T^1
    -8.523829e-3,     # T^2
    6.943248e-5,      # T^3
    -3.821216e-7,     # T^4
)


def water_density_kgm3(temp_c: float) -> float:
    """Density of liquid water [kg/m³] at temperature ``temp_c`` [°C]."""
    t = float(temp_c)
    rho = 0.0
    for i, c in enumerate(_WATER_RHO_COEFFS):
        rho += c * t**i
    return rho


# ---------------------------------------------------------------------------
# Natural cubic spline
# ---------------------------------------------------------------------------


class NaturalCubicSpline:
    """
    Natural cubic spline interpolation (second derivative = 0 at both ends).

    Parameters
    ----------
    x, y : array-like
        Sample points.  ``x`` need not be pre-sorted; duplicate ``x`` values are
        collapsed (mean ``y``) so the tridiagonal system stays well-posed for the
        small, occasionally-repeated FAT datasets.

    Examples
    --------
    >>> s = NaturalCubicSpline([0, 1, 2, 3], [0, 1, 4, 9])
    >>> round(float(s(1.5)), 3)
    2.225
    """

    def __init__(self, x, y) -> None:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        order = np.argsort(x)
        x, y = x[order], y[order]

        # Collapse duplicate abscissae (mean of the ordinates).
        ux, idx = np.unique(x, return_inverse=True)
        if len(ux) != len(x):
            uy = np.zeros_like(ux)
            counts = np.zeros_like(ux)
            np.add.at(uy, idx, y)
            np.add.at(counts, idx, 1.0)
            y = uy / counts
            x = ux

        if len(x) < 2:
            raise ValueError("NaturalCubicSpline needs at least 2 distinct points.")

        self.x = x
        self.y = y
        self.m = self._second_derivatives(x, y)

    @staticmethod
    def _second_derivatives(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        n = len(x)
        h = np.diff(x)

        if n == 2:                      # straight line — curvature is zero
            return np.zeros(2)

        # Tridiagonal system  A · m = d   with natural BCs m[0] = m[-1] = 0.
        a = np.zeros(n)   # sub-diagonal
        b = np.zeros(n)   # main diagonal
        c = np.zeros(n)   # super-diagonal
        d = np.zeros(n)   # rhs

        b[0] = b[-1] = 1.0             # natural boundary conditions

        for i in range(1, n - 1):
            a[i] = h[i - 1]
            b[i] = 2.0 * (h[i - 1] + h[i])
            c[i] = h[i]
            d[i] = 6.0 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])

        # Thomas algorithm.
        for i in range(1, n):
            w = a[i] / b[i - 1]
            b[i] -= w * c[i - 1]
            d[i] -= w * d[i - 1]

        m = np.zeros(n)
        m[-1] = d[-1] / b[-1]
        for i in range(n - 2, -1, -1):
            m[i] = (d[i] - c[i] * m[i + 1]) / b[i]
        return m

    def __call__(self, xq):
        xq = np.asarray(xq, dtype=float)
        scalar = xq.ndim == 0
        xq = np.atleast_1d(xq)

        # Locate the interval for each query point (clamped to the data range).
        idx = np.clip(np.searchsorted(self.x, xq) - 1, 0, len(self.x) - 2)

        x_i = self.x[idx]
        x_i1 = self.x[idx + 1]
        y_i = self.y[idx]
        y_i1 = self.y[idx + 1]
        m_i = self.m[idx]
        m_i1 = self.m[idx + 1]
        h = x_i1 - x_i

        a = (x_i1 - xq) / h
        b = (xq - x_i) / h
        out = (
            a * y_i
            + b * y_i1
            + ((a**3 - a) * m_i + (b**3 - b) * m_i1) * (h**2) / 6.0
        )
        return float(out[0]) if scalar else out

    def sample(self, n: int = 100):
        """Return ``(xs, ys)`` of ``n`` evenly spaced samples across the data."""
        xs = np.linspace(self.x[0], self.x[-1], n)
        return xs, self(xs)


def r_squared(y_actual, y_pred) -> float:
    """Coefficient of determination, R²."""
    y_actual = np.asarray(y_actual, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = float(np.sum((y_actual - y_pred) ** 2))
    ss_tot = float(np.sum((y_actual - np.mean(y_actual)) ** 2))
    if ss_tot == 0:
        return 1.0
    return 1.0 - ss_res / ss_tot
