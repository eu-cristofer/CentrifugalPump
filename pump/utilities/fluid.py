"""
This module provides a representation of fluids and their physical properties, enabling
engineering calculations and dynamic property management.

The `Fluid` class is the central component of this module. It allows users to define
fluids with essential physical properties, such as density, and dynamically add other
properties with unit validation. The module leverages utility functions for handling
unit conversions and context extraction.

Functions
---------
- extract_context: Extracts context from a property key, aiding in unit validation.
- Q_: A utility for creating quantities with units, typically used with the `pint` library.
- quantity_factory: A factory function for converting and validating quantities with units.

Classes
-------
- Fluid: Represents a fluid and its properties.

Notes
-----
This module assumes the use of a unit-handling library (`pint`) to manage and
validate physical quantities and their units. The `quantity_factory` function encapsulates
unit validation logic, making it easier to enforce consistency across fluid properties.

Examples
--------
# Example of creating a Fluid object:
water = Fluid(name="Water", density=Q_(1000, "kg/m**3"), viscosity=Q_(1, "cP"))

# Accessing properties:
print(water.name)           # Output: Water
print(water.density)        # Output: 1000 kg/m**3
print(water.viscosity)      # Output: 1 cP

# Adding additional properties dynamically:
water.thermal_conductivity = Q_(0.6, "W/(m*K)")
print(water.thermal_conductivity)  # Output: 0.6 W/(m*K)
"""
from typing import Dict
from .unit_conversion import extract_context, Q_, quantity_factory

__all__ = ["Fluid", "Water"]

class Fluid:
    """
    A class to represent a fluid and its properties, enabling engineering calculations.

    Attributes
    ----------
    name : str
        The name of the fluid.
    density : Q_
        The density of the fluid in standard units (e.g., `Q_(1000, "kg/m**3")`).

    Notes
    -----
    Unit validation is encapsulated within the `quantity_factory` function.
    """


    def __init__(self, name: str, density: Q_, **kwargs: Dict[str, Q_]) -> None:
        """
        Initializes a Fluid object with converted physical properties.

        Parameters
        ----------
        name : str
            The name of the fluid.
        density : Q_
            The density of the fluid with units (e.g., `Q_(1000, "kg/m**3")`).
        kwargs : Dict[str, Q_]
            Additional physical properties with units. These properties will be dynamically
            added as attributes to the Fluid object.

        Raises
        ------
        ValueError
            If the provided units are not compatible.
        """
        if not name or not isinstance(name, str):
            raise ValueError("A valid name for the fluid is required.")
        self.name = name

        if not density:
            raise ValueError("Density is a mandatory property.")
        self.density = quantity_factory(density, context="default")
        
        # Dynamically set additional properties as attributes
        for key, quantity in kwargs.items():
            context = extract_context(key)
            setattr(self, key, quantity_factory(quantity, context))

    def _get_properties(self):
        """Returns a detailed string with fluid's properties."""
        properties = ", ".join(f"{key}={value}" for key, value in self.__dict__.items())
        return properties

    def __repr__(self) -> str:
        """Returns a detailed string representation of the fluid."""
        return f"Fluid(name={self.name}, density={self.density})"
    
    def __str__(self) -> str:
        """Returns a detailed string representation of the fluid's properties."""
        return f"Fluid({self._get_properties()})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Fluid):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash((self.name, self.density.magnitude, str(self.density.units)))


class Water(Fluid):
    """
    Liquid water at a given temperature.

    Density is computed from a 4th-order polynomial fit (Kell-style coefficients,
    valid approximately 0–100 °C at 1 atm). At 4 °C the result peaks near
    999.97 kg/m³; at 34 °C it is approximately 994.4 kg/m³.

    Parameters
    ----------
    temperature : Q_
        Water temperature as a Pint quantity in any compatible unit
        (e.g. ``Q_(20, "degC")``, ``Q_(293.15, "K")``).

    Attributes
    ----------
    temperature : Q_
        Water temperature normalised to kelvin (standard unit for temperature).

    Examples
    --------
    >>> w = Water(Q_(20.0, "degC"))
    >>> w.name
    'Water'
    >>> round(w.density.magnitude, 2)
    998.2
    >>> w2 = Water(Q_(293.15, "K"))
    >>> round(w2.density.magnitude, 2)
    998.2
    """

    _RHO_COEFFS = (
        999.85308,    # T^0
        6.32693e-2,   # T^1
        -8.523829e-3, # T^2
        6.943248e-5,  # T^3
        -3.821216e-7, # T^4
    )

    def __init__(self, temperature: Q_) -> None:
        if not isinstance(temperature, Q_):
            raise ValueError("A valid pint.Quantity is required for temperature.")
        t_c = float(temperature.to("degC").magnitude)
        rho = sum(c * t_c ** i for i, c in enumerate(self._RHO_COEFFS))
        super().__init__(name="Water", density=Q_(rho, "kg/m**3"))
        self.temperature = quantity_factory(temperature, context="default")
