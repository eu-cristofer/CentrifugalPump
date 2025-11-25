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

__all__ = ["Fluid"]

class Fluid:
    """
    A class to represent a fluid and its properties, enabling engineering calculations.

    Attributes
    ----------
    name : str
        The name of the fluid.
    density : Q_
        The density of the fluid in standard units (e.g., `Q_(1000, "kg/m**3")`).
    additional_properties : dict
        Additional physical properties with units, dynamically added as attributes.

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
        kwargs : dict
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
