"""
system_curve
============

System (pipe network) resistance curves (UC-03).

Two models, both exposing ``head(q)`` and ``curve(q_array)``:

- :class:`SystemCurve` -- ``H(Q) = H_static + k * Q**n`` (``n = 2`` by default).
  ``k`` carries the units ``m / (m**3/h)**n`` and is stored normalised to them.
- :class:`PipeSystemCurve` -- a single pipe run evaluated with the full
  Darcy-Weisbach friction law at every ``Q`` (not a fitted ``k``), built by
  :meth:`SystemCurve.from_pipe`.

Friction law (sources)
----------------------
- Darcy-Weisbach: ``h_f = (f * L / D + sum(K)) * V**2 / (2 * g)`` with
  ``V = Q / (pi * D**2 / 4)`` and ``Re = V * D / nu`` (any fluid-mechanics
  text, e.g. White, *Fluid Mechanics*, ch. 6; Crane TP-410).
- Swamee-Jain explicit approximation of Colebrook (Swamee & Jain, 1976,
  J. Hydraulics Div. ASCE 102(5), 657-664)::

      f = 0.25 / [ log10( (eps/D)/3.7 + 5.74 / Re**0.9 ) ]**2

  stated valid for ``5e3 <= Re <= 1e8`` and ``1e-6 <= eps/D <= 1e-2``.
- For ``Re < 2300`` (laminar) the Hagen-Poiseuille result ``f = 64 / Re`` is
  used.  The two branches are not blended across the transition region.

Examples
--------
>>> from pump import Q_
>>> s = SystemCurve(Q_(20, "m"), Q_(1e-4, "m/(m**3/h)**2"))
>>> round(s.head(Q_(100, "m**3/h")).to("m").magnitude, 6)
21.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .constants import G
from .utilities.unit_conversion import Q_, quantity_factory

__all__ = ["SystemCurve", "PipeSystemCurve"]

_CAPACITY_DIM = "[length] ** 3 / [time]"


def _k_unit(exponent: float):
    """Pint unit ``m / (m**3/h)**n``."""
    n = float(exponent)
    e = int(n) if n.is_integer() else n
    return (Q_(1, "m") / Q_(1, "m**3/h") ** e).units


def _capacity_m3h(q) -> np.ndarray:
    """Capacity (any compatible unit, scalar or array) as float m**3/h."""
    if not isinstance(q, Q_):
        raise ValueError("A valid pint.Quantity is required for capacity.")
    if not q.check(_CAPACITY_DIM):
        raise ValueError(
            f"Capacity must have dimensions of volume/time, got {q.units}."
        )
    return np.asarray(quantity_factory(q).magnitude, dtype=float)


def _length(q, name: str) -> Q_:
    if not isinstance(q, Q_):
        raise ValueError(f"A valid pint.Quantity is required for {name}.")
    if not q.check("[length]"):
        raise ValueError(f"{name} must be a length, got {q.units}.")
    return quantity_factory(q)


def _head_quantity(values) -> Q_:
    values = np.asarray(values, dtype=float)
    return Q_(float(values) if values.ndim == 0 else values, "m")


@dataclass(frozen=True)
class SystemCurve:
    """``H(Q) = static_head + k * Q**exponent``.

    Parameters
    ----------
    static_head : Q_
        Static head (length), normalised to metres.
    k : Q_
        Resistance coefficient with units ``m / (m**3/h)**exponent`` (any
        equivalent unit, e.g. ``ft/gpm**2`` for ``exponent = 2``); stored
        normalised to ``m / (m**3/h)**exponent``.
    exponent : float
        Flow exponent ``n`` (> 0); 2 for fully turbulent friction.
    """

    static_head: Q_
    k: Q_
    exponent: float = 2.0

    def __post_init__(self) -> None:
        n = float(self.exponent)
        if not n > 0:
            raise ValueError("exponent must be > 0.")
        object.__setattr__(self, "exponent", n)
        object.__setattr__(
            self, "static_head", _length(self.static_head, "static_head")
        )
        if not isinstance(self.k, Q_):
            raise ValueError("A valid pint.Quantity is required for k.")
        unit = _k_unit(n)
        if self.k.dimensionality != Q_(1, unit).dimensionality:
            raise ValueError(
                f"k must have units of m/(m**3/h)**{n:g} "
                f"(head per capacity**n), got {self.k.units}."
            )
        object.__setattr__(self, "k", self.k.to(unit))

    # -- evaluation --------------------------------------------------------
    def head(self, q: Q_) -> Q_:
        """System head at capacity ``q`` (scalar or array Quantity), in metres."""
        qm = _capacity_m3h(q)
        h = self.static_head.to("m").magnitude + self.k.magnitude * np.power(
            qm, self.exponent
        )
        return _head_quantity(h)

    def curve(self, q_array: Q_) -> Q_:
        """Head at every capacity of ``q_array`` (a Quantity array), in metres."""
        return self.head(q_array)

    # -- constructors ------------------------------------------------------
    @classmethod
    def from_points(cls, p1, p2, exponent: float = 2.0) -> "SystemCurve":
        """Fit ``H_static`` and ``k`` through two ``(q, h)`` points.

        Examples
        --------
        >>> s = SystemCurve.from_points(
        ...     (Q_(100, "m**3/h"), Q_(11, "m")), (Q_(200, "m**3/h"), Q_(14, "m"))
        ... )
        >>> round(s.static_head.magnitude, 6), round(s.k.magnitude, 9)
        (10.0, 0.0001)
        """
        (q1, h1), (q2, h2) = p1, p2
        n = float(exponent)
        a1 = float(np.power(_capacity_m3h(q1), n))
        a2 = float(np.power(_capacity_m3h(q2), n))
        if a1 == a2:
            raise ValueError("The two points must have different capacities.")
        h1m = _length(h1, "head").to("m").magnitude
        h2m = _length(h2, "head").to("m").magnitude
        k = (h2m - h1m) / (a2 - a1)
        static = h1m - k * a1
        return cls(Q_(static, "m"), Q_(k, _k_unit(n)), n)

    @staticmethod
    def from_pipe(
        static_head: Q_,
        length: Q_,
        diameter: Q_,
        roughness: Q_,
        fluid,
        minor_k_sum: float = 0.0,
        q_ref: Optional[Q_] = None,
    ) -> "PipeSystemCurve":
        """Pipe-run system curve from Darcy-Weisbach with Swamee-Jain friction.

        ``fluid`` supplies the kinematic viscosity (``fluid.kinematic_viscosity``
        or ``fluid.viscosity``; a dynamic viscosity is divided by the density).
        The returned object evaluates the full friction law at each ``Q``;
        ``q_ref`` (optional) lets it produce an equivalent ``k * Q**2`` curve via
        :meth:`PipeSystemCurve.equivalent`.  See the module docstring for the
        formula sources.
        """
        return PipeSystemCurve(
            static_head=static_head,
            length=length,
            diameter=diameter,
            roughness=roughness,
            kinematic_viscosity=_kinematic_viscosity(fluid),
            minor_k_sum=minor_k_sum,
            q_ref=q_ref,
        )


def _kinematic_viscosity(fluid) -> Q_:
    nu = getattr(fluid, "kinematic_viscosity", None)
    if nu is None:
        visc = getattr(fluid, "viscosity", None)
        if visc is None:
            raise ValueError(
                "The fluid needs a (kinematic) viscosity for the pipe curve."
            )
        nu = visc if visc.check("[length] ** 2 / [time]") else visc / fluid.density
    return nu.to("cSt")


@dataclass(frozen=True)
class PipeSystemCurve:
    """Static head plus Darcy-Weisbach friction + minor losses of one pipe run.

    ``H(Q) = H_static + (f * L / D + sum(K)) * V**2 / (2 g)``, with ``f`` from
    Swamee-Jain (turbulent) or ``64 / Re`` (laminar, ``Re < 2300``).
    """

    static_head: Q_
    length: Q_
    diameter: Q_
    roughness: Q_
    kinematic_viscosity: Q_
    minor_k_sum: float = 0.0
    q_ref: Optional[Q_] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "static_head", _length(self.static_head, "static_head")
        )
        object.__setattr__(self, "length", _length(self.length, "length"))
        object.__setattr__(self, "diameter", _length(self.diameter, "diameter"))
        object.__setattr__(self, "roughness", _length(self.roughness, "roughness"))
        if not self.length.magnitude > 0:
            raise ValueError("length must be > 0.")
        if not self.diameter.magnitude > 0:
            raise ValueError("diameter must be > 0.")
        if self.roughness.magnitude < 0:
            raise ValueError("roughness must be >= 0.")
        if float(self.minor_k_sum) < 0:
            raise ValueError("minor_k_sum must be >= 0.")
        nu = self.kinematic_viscosity
        if not isinstance(nu, Q_) or not nu.check("[length] ** 2 / [time]"):
            raise ValueError(
                "kinematic_viscosity must be a kinematic viscosity (e.g. cSt)."
            )
        if not nu.to("m**2/s").magnitude > 0:
            raise ValueError("kinematic_viscosity must be > 0.")

    # -- hydraulics --------------------------------------------------------
    def _velocity(self, q) -> np.ndarray:
        d = self.diameter.to("m").magnitude
        q_si = np.abs(_capacity_m3h(q)) / 3600.0
        return q_si / (math.pi * d * d / 4.0)

    def reynolds(self, q: Q_) -> np.ndarray:
        """Reynolds number ``V * D / nu`` at capacity ``q``."""
        d = self.diameter.to("m").magnitude
        nu = self.kinematic_viscosity.to("m**2/s").magnitude
        return self._velocity(q) * d / nu

    def friction_factor(self, q: Q_) -> np.ndarray:
        """Darcy friction factor (Swamee-Jain; ``64/Re`` for ``Re < 2300``)."""
        re = np.asarray(self.reynolds(q), dtype=float)
        safe = np.where(re > 0.0, re, 1.0)
        rel = self.roughness.to("m").magnitude / self.diameter.to("m").magnitude
        turbulent = 0.25 / np.log10(rel / 3.7 + 5.74 / safe**0.9) ** 2
        laminar = 64.0 / safe
        return np.where(safe < 2300.0, laminar, turbulent)

    def head(self, q: Q_) -> Q_:
        """System head at capacity ``q`` (scalar or array Quantity), in metres."""
        v = self._velocity(q)
        f = self.friction_factor(q)
        ld = self.length.to("m").magnitude / self.diameter.to("m").magnitude
        g = G.to("m/s**2").magnitude
        hf = (f * ld + float(self.minor_k_sum)) * v * v / (2.0 * g)
        return _head_quantity(self.static_head.to("m").magnitude + hf)

    def curve(self, q_array: Q_) -> Q_:
        """Head at every capacity of ``q_array`` (a Quantity array), in metres."""
        return self.head(q_array)

    def equivalent(self, q_ref: Optional[Q_] = None) -> SystemCurve:
        """Equivalent ``H_static + k * Q**2`` curve matching this one at ``q_ref``."""
        q_ref = q_ref if q_ref is not None else self.q_ref
        if q_ref is None:
            raise ValueError("A reference capacity q_ref is required.")
        qm = float(_capacity_m3h(q_ref))
        if not qm > 0:
            raise ValueError("q_ref must be > 0.")
        static = self.static_head.to("m").magnitude
        k = (float(self.head(q_ref).to("m").magnitude) - static) / qm**2
        return SystemCurve(Q_(static, "m"), Q_(k, _k_unit(2.0)), 2.0)
