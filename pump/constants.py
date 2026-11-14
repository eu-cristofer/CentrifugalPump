"""
constants
=========

Physical constants shared by the whole library, as Pint quantities.

Constants
---------
- G: standard acceleration of gravity (ISO 80000-3 / CGPM 1901), 9.80665 m/s**2.
- P_ATM: standard atmosphere, 101325 Pa.

Examples
--------
>>> from pump.constants import G, P_ATM
>>> G.magnitude, str(G.units)
(9.80665, 'meter / second ** 2')
>>> P_ATM.to("bar").magnitude
1.01325
"""

from pump.utilities.unit_conversion import Q_

__all__ = ["G", "P_ATM"]

#: Standard acceleration of gravity.
G = Q_(9.80665, "m/s**2")

#: Standard atmospheric pressure.
P_ATM = Q_(101325, "Pa")
