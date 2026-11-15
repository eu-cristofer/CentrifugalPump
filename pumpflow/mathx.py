"""
mathx
=====

Compatibility shim.  The maths originally ported into the UI layer from the
reference notebook (``pump_api610_performance 1.ipynb``) now lives in the
``pump`` library (ADR-0009):

- :class:`NaturalCubicSpline` and :func:`r_squared` -- see :mod:`pump.fitting`.
  They are re-exported here so existing ``from pumpflow.mathx import ...``
  imports keep working.

.. note::
   Water density is provided by :class:`pump.utilities.fluid.Water`, which
   was graduated from this module into the ``pump`` library.  Import it from
   there rather than duplicating the polynomial coefficients here.
"""

from __future__ import annotations

from pump.fitting import NaturalCubicSpline, r_squared

__all__ = ["NaturalCubicSpline", "r_squared"]
