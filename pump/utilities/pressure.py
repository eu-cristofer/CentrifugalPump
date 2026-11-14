"""
pressure
========

Gauge / absolute pressure with an explicit atmosphere.

A bare pressure number is ambiguous: ``1 bar`` may be gauge or absolute. The
:class:`Pressure` dataclass carries the reference with the value so a gauge to
absolute conversion is explicit, and a difference between two pressures is only
allowed when it is unambiguous.

Classes
-------
- Pressure: Immutable pressure value with ``reference`` (``"g"`` or ``"a"``).

Examples
--------
>>> from pump import Q_
>>> from pump.utilities.pressure import Pressure
>>> p = Pressure(Q_(1, "bar"), "g")
>>> round(p.absolute().to("bar").magnitude, 5)
2.01325
"""

from dataclasses import dataclass
from typing import Any, Dict, Literal

from pump import quantity_io as _qio
from pump.constants import P_ATM
from pump.utilities.unit_conversion import Q_

__all__ = ["Pressure"]

_PRESSURE_DIM = P_ATM.dimensionality


@dataclass(frozen=True)
class Pressure:
    """
    A pressure value together with its reference.

    Parameters
    ----------
    value : Q_
        Pressure quantity (any pressure unit).
    reference : {"g", "a"}, optional
        ``"g"`` for gauge (relative to ``atmosphere``), ``"a"`` for absolute.
    atmosphere : Q_, optional
        Atmospheric pressure used for gauge/absolute conversion
        (default: standard atmosphere, 101325 Pa).

    Raises
    ------
    ValueError
        If ``value`` or ``atmosphere`` is not a pressure quantity, or
        ``reference`` is not ``"g"`` or ``"a"``.

    Examples
    --------
    >>> from pump import Q_
    >>> d = Pressure(Q_(50.0, "psi"), "g") - Pressure(Q_(10.0, "psi"), "g")
    >>> round(d.to("psi").magnitude, 6)
    40.0
    >>> Pressure(Q_(1, "bar"), "g") - Pressure(Q_(1, "bar"), "a")
    Traceback (most recent call last):
        ...
    ValueError: Cannot subtract pressures with mixed gauge/absolute references.
    """

    value: Q_
    reference: Literal["g", "a"] = "g"
    atmosphere: Q_ = P_ATM

    def __post_init__(self) -> None:
        if self.reference not in ("g", "a"):
            raise ValueError("reference must be 'g' (gauge) or 'a' (absolute).")
        for name in ("value", "atmosphere"):
            q = getattr(self, name)
            if not isinstance(q, Q_) or q.dimensionality != _PRESSURE_DIM:
                raise ValueError(f"{name} must be a pint Quantity of pressure.")

    def absolute(self) -> Q_:
        """
        Absolute pressure, in the units of ``value``.

        Examples
        --------
        >>> from pump import Q_
        >>> round(Pressure(Q_(0, "bar"), "g").absolute().to("kPa").magnitude, 3)
        101.325
        >>> Pressure(Q_(2.0, "bar"), "a").absolute().to("bar").magnitude
        2.0
        """
        if self.reference == "a":
            return self.value
        return self.value + self.atmosphere

    def gauge(self) -> Q_:
        """
        Gauge pressure, in the units of ``value``.

        Examples
        --------
        >>> from pump import Q_
        >>> round(Pressure(Q_(2.01325, "bar"), "a").gauge().to("bar").magnitude, 5)
        1.0
        """
        if self.reference == "g":
            return self.value
        return self.value - self.atmosphere

    def __sub__(self, other: "Pressure") -> Q_:
        """
        Difference of two pressures (reference-free), in the units of ``self``.

        Raises
        ------
        ValueError
            If the references differ (mixed gauge/absolute) or the atmospheres
            differ.
        """
        if not isinstance(other, Pressure):
            return NotImplemented
        if self.reference != other.reference:
            raise ValueError(
                "Cannot subtract pressures with mixed gauge/absolute references."
            )
        if self.atmosphere.to("Pa").magnitude != other.atmosphere.to("Pa").magnitude:
            raise ValueError("Cannot subtract pressures with different atmospheres.")
        return self.value - other.value

    def to_json(self) -> Dict[str, Any]:
        """
        Serialise to ``{"value", "unit", "ref", "atm": {"value", "unit"}}``.

        Examples
        --------
        >>> from pump import Q_
        >>> d = Pressure(Q_(1, "bar"), "g").to_json()
        >>> d["value"], d["ref"], sorted(d["atm"])
        (1.0, 'g', ['unit', 'value'])
        """
        data = _qio.to_json(self.value)
        data["ref"] = self.reference
        data["atm"] = _qio.to_json(self.atmosphere)
        return data

    @classmethod
    def from_json(cls, d: Dict[str, Any]) -> "Pressure":
        """
        Rebuild from :meth:`to_json` output (``ref`` defaults to gauge, ``atm``
        to the standard atmosphere).

        Examples
        --------
        >>> from pump import Q_
        >>> p = Pressure(Q_(3, "bar"), "a")
        >>> Pressure.from_json(p.to_json()) == p
        True
        """
        value = _qio.from_json({"value": d["value"], "unit": d["unit"]})
        atm = _qio.from_json(d["atm"]) if "atm" in d else P_ATM
        return cls(value, d.get("ref", "g"), atm)
