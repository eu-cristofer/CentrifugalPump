"""
point
=====

This module defines the Point class and its subclasses, which represent a system point 
with converted physical quantities.

Classes
-------
- Point: Represents a system point blueprint with capacity and inlet pressure.
- DesignPoint: A specialized version of Point for design conditions.
- TestPoint: A specialized version of Point for handling test or operational data.
"""

import numpy as np
from .utilities.unit_conversion import extract_context, Q_, quantity_factory
from .utilities.fluid import Fluid

__all__ = ["BasePoint", "Point", "DesignPoint", "TestPoint"]


class BasePoint:
    """
    Represents a system point with physical quantities.

    Parameters
    ----------
    fluid : Fluid
        A fluid object that should at least contain properties like density.
    capacity : Q_
        The capacity as a Pint quantity with units (e.g., Q_(10, "m**3/s")).
    **kwargs : dict[str, Q_]
        Additional named quantities.

    Attributes
    ----------
    capacity : Q_
        The capacity converted to its standard unit.
    fluid : Fluid
        The fluid associated with the point.
    <other attributes from kwargs> : Q_
        Any additional attributes passed via kwargs are stored as Pint
        quantities in this object.

    Raises
    ------
    ValueError
        If the provided units are not compatible or if quantity_factory
        raises an error for invalid unit conversion.

    Examples
    --------
    >>> from pump.utilities.unit_conversion import Fluid, Q_
    >>> water = Fluid(name="Water", density=Q_(1000, "kg/m**3"))
    >>> point = Point(fluid=water, capacity=Q_(0.1, "m**3/s"), inlet_pressure=Q_(1, "atm"))
    >>> print(point)
    Point(fluid=Water, capacity=0.1 meter ** 3 / second, inlet_pressure=101325.0 pascal)
    """

    def __init__(self, fluid: Fluid, capacity: Q_, **kwargs: dict[str, Q_]) -> None:
        self.fluid = fluid
        self.capacity = quantity_factory(capacity, context="default")

        # Dynamically set additional properties as attributes
        for key, quantity in kwargs.items():
            context = extract_context(key)
            setattr(self, key, quantity_factory(quantity, context))

    def _get_properties(self):
        """Returns a detailed string with fluid's properties."""
        properties = ", ".join(f"{key}={value}" for key, value in self.__dict__.items())
        return properties

    def __repr__(self) -> str:
        return f"BasePoint(fluid={self.fluid.name}, capacity={self.capacity:.2f~P})"

    def __str__(self) -> str:
        """Returns a detailed string representation of the fluid's properties."""
        return f"BasePoint({self._get_properties()})"


class DesignPoint(BasePoint):
    """
    Specialized version of the BasePoint class, representing a design condition.
    """
    # Gravity constant
    g = Q_(9.81, "m/s**2")

    def __init__(
        self, fluid: Fluid, capacity: Q_, differential_head: Q_, **kwargs: dict[str, Q_]
    ) -> None:
        kwargs = {"differential_head": differential_head} | kwargs
        super().__init__(fluid, capacity, **kwargs)

    @property
    def specific_energy(self) -> Q_:
        """
        Specific energy is the energy per unit mass of fluid.
        It is calculated as the product of the gravity constant and the differential head.
        It is used to calculate the pump power output.
        """
        return quantity_factory(self.g * self.differential_head)

    @property
    def power_output(self) -> Q_:
        """
        The mechanical power transferred to the liquid as it passes through the pump,
        also known as pump hydraulic power.
        """
        return quantity_factory(self.fluid.density * self.capacity * self.specific_energy)

    @property
    def outlet_pressure(self) -> Q_:
        if hasattr(self, "inlet_pressure"):
            heads = self.differential_head - self.elevation_head - self.velocity_head
            pressure = heads * self.fluid.density * self.g
            return quantity_factory(pressure + self.inlet_pressure, context="default")
        else:
            raise AttributeError(
                "Cannot compute outlet_pressure because 'inlet_pressure' is missing."
            )

    @property
    def elevation_head(self) -> Q_:
        if hasattr(self, "inlet_elevation") and hasattr(self, "outlet_elevation"):
            return quantity_factory(self.outlet_elevation - self.inlet_elevation)
        return Q_(0, "m")

    @property
    def inlet_velocity(self) -> Q_:
        if hasattr(self, "inlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.inlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def outlet_velocity(self) -> Q_:
        if hasattr(self, "outlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.outlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def velocity_head(self) -> Q_:
        if hasattr(self, "inlet_diameter") and hasattr(self, "outlet_diameter"):
            return quantity_factory(
                (self.outlet_velocity**2 - self.inlet_velocity**2) / (2 * self.g)
            )
        return Q_(0, "m")

    def __repr__(self) -> str:
        return f"DesignPoint(fluid={self.fluid.name}, capacity={self.capacity:.2f~P})"

    def __str__(self) -> str:
        """Returns a detailed string representation of the fluid's properties."""
        return f"DesignPoint({self._get_properties()})"

    def summary(self) -> str:
        """
        Prints and returns a comprehensive summary of the pump design point calculations.
        
        Returns
        -------
        str
            A formatted string containing all relevant pump design information.
        """
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("PUMP DESIGN POINT SUMMARY")
        summary_lines.append("=" * 60)
        
        # Fluid information
        summary_lines.append(f"\nFLUID PROPERTIES:")
        summary_lines.append(f"  Fluid Name: {self.fluid.name}")
        summary_lines.append(f"  Density: {self.fluid.density:.2f~P}")
        
        # Basic design parameters
        summary_lines.append(f"\nDESIGN PARAMETERS:")
        summary_lines.append(f"  Capacity: {self.capacity:.2f~P}")
        summary_lines.append(f"  Differential Head: {self.differential_head:.2f~P}")
        
        # Calculated properties
        summary_lines.append(f"\nCALCULATED PROPERTIES:")
        summary_lines.append(f"  Specific Energy: {self.specific_energy:.2f~P}")
        summary_lines.append(f"  Power Output: {self.power_output:.2f~P}")
        
        # Optional properties if available
        if hasattr(self, "inlet_pressure"):
            summary_lines.append(f"  Inlet Pressure: {self.inlet_pressure:.2f~P}")
            summary_lines.append(f"  Outlet Pressure: {self.outlet_pressure:.2f~P}")
        
        if hasattr(self, "inlet_elevation") and hasattr(self, "outlet_elevation"):
            summary_lines.append(f"  Inlet Elevation: {self.inlet_elevation:.2f~P}")
            summary_lines.append(f"  Outlet Elevation: {self.outlet_elevation:.2f~P}")
            summary_lines.append(f"  Elevation Head: {self.elevation_head:.2f~P}")
        
        if hasattr(self, "inlet_diameter") and hasattr(self, "outlet_diameter"):
            summary_lines.append(f"  Inlet Diameter: {self.inlet_diameter:.2f~P}")
            summary_lines.append(f"  Outlet Diameter: {self.outlet_diameter:.2f~P}")
            summary_lines.append(f"  Inlet Velocity: {self.inlet_velocity:.2f~P}")
            summary_lines.append(f"  Outlet Velocity: {self.outlet_velocity:.2f~P}")
            summary_lines.append(f"  Velocity Head: {self.velocity_head:.2f~P}")
        
        # Additional properties from kwargs
        additional_props = []
        for key, value in self.__dict__.items():
            if key not in ['fluid', 'capacity', 'differential_head', 'inlet_pressure', 
                          'inlet_elevation', 'outlet_elevation', 'inlet_diameter', 'outlet_diameter']:
                additional_props.append(f"  {key}: {value:.2f~P}")
        
        if additional_props:
            summary_lines.append(f"\nADDITIONAL PROPERTIES:")
            summary_lines.extend(additional_props)
        
        summary_lines.append("\n" + "=" * 60)
        
        summary_text = "\n".join(summary_lines)
        
        # Print to screen
        print(summary_text)
        
        # Return the summary text
        return summary_text


class Point(BasePoint):
    """
    Specialized version of BasePoint class, representig a generic performance point.
    """

    g = Q_(9.81, "m/s**2")

    @property
    def outlet_pressure(
        self,
    ):
        return quantity_factory()

    @property
    def pressure_head(self) -> Q_:
        if not hasattr(self.fluid, "density"):
            raise ValueError("Fluid object does not have a 'density' attribute.")

        if not hasattr(self, "delta_pressure"):
            if not hasattr(self, "inlet_pressure") or not hasattr(
                self, "outlet_pressure"
            ):
                raise AttributeError(
                    "Cannot compute head because 'delta_pressure' or pressures are missing."
                )
            else:
                self.delta_pressure = self.outlet_pressure - self.inlet_pressure
        return quantity_factory(self.delta_pressure / (self.fluid.density * self.g))

    @property
    def inlet_velocity(self) -> Q_:
        if hasattr(self, "inlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.inlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def outlet_velocity(self) -> Q_:
        if hasattr(self, "outlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.outlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def velocity_head(self) -> Q_:
        if hasattr(self, "inlet_diameter") and hasattr(self, "outlet_diameter"):
            return quantity_factory(
                (self.outlet_velocity**2 - self.inlet_velocity**2) / (2 * self.g)
            )
        return Q_(0, "m")

    @property
    def elevation_head(self) -> Q_:
        if hasattr(self, "inlet_elevation") and hasattr(self, "outlet_elevation"):
            return quantity_factory(self.outlet_elevation - self.inlet_elevation)
        return Q_(0, "m")

    @property
    def compute_head(self) -> Q_:
        TDH = self.pressure_head + self.velocity_head + self.elevation_head
        self._head = quantity_factory(TDH)
        return self._head

    @property
    def head(self) -> Q_:
        return self._head if hasattr(self, "_head") else self.compute_head

    @head.setter
    def head(self, value: Q_) -> None:
        self._head = quantity_factory(value)

    def __repr__(self) -> str:
        return f"Point(fluid={self.fluid.name}, capacity={self.capacity:.2f~P})"

    def __str__(self) -> str:
        """Returns a detailed string representation of the fluid's properties."""
        return f"Point({self._get_properties()})"


class TestPoint(BasePoint):
    """
    Specialized version of the BasePoint class for handling test or operational data.

    This class provides additional properties for calculating hydraulic parameters
    such as pressure head, velocity head, elevation head, and hydraulic power.
    """

    g = Q_(9.81, "m/s**2")

    @property
    def pressure_head(self) -> Q_:
        if not hasattr(self.fluid, "density"):
            raise ValueError("Fluid object does not have a 'density' attribute.")

        if not hasattr(self, "delta_pressure"):
            if not hasattr(self, "inlet_pressure") or not hasattr(
                self, "outlet_pressure"
            ):
                raise AttributeError(
                    "Cannot compute head because 'delta_pressure' or pressures are missing."
                )
            else:
                self.delta_pressure = self.outlet_pressure - self.inlet_pressure
        return quantity_factory(self.delta_pressure / (self.fluid.density * self.g))

    @property
    def inlet_velocity(self) -> Q_:
        if hasattr(self, "inlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.inlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def outlet_velocity(self) -> Q_:
        if hasattr(self, "outlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.outlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def velocity_head(self) -> Q_:
        if hasattr(self, "inlet_diameter") and hasattr(self, "outlet_diameter"):
            return quantity_factory(
                (self.outlet_velocity**2 - self.inlet_velocity**2) / (2 * self.g)
            )
        return Q_(0, "m")

    @property
    def elevation_head(self) -> Q_:
        if hasattr(self, "inlet_elevation") and hasattr(self, "outlet_elevation"):
            return quantity_factory(self.outlet_elevation - self.inlet_elevation)
        return Q_(0, "m")

    @property
    def compute_head(self) -> Q_:
        TDH = self.pressure_head + self.velocity_head + self.elevation_head
        self._head = quantity_factory(TDH)
        return self._head

    @property
    def head(self) -> Q_:
        return self._head if hasattr(self, "_head") else self.compute_head

    @property
    def compute_hydraulic_power(self) -> Q_:
        self._hydraulic_power = quantity_factory(
            self.fluid.density * self.capacity * self.g * self.head
        )
        return self._hydraulic_power

    @property
    def hydraulic_power(self) -> Q_:
        return (
            self._hydraulic_power
            if hasattr(self, "_hydraulic_power")
            else self.compute_hydraulic_power
        )

    @property
    def compute_efficiency(self) -> Q_:
        if not hasattr(self, "breaking_power"):
            raise AttributeError(
                "Cannot compute efficiency: 'breaking_power' is missing."
            )
        self._efficiency = quantity_factory(
            self.hydraulic_power / self.breaking_power
        ).to("percent")
        return self._efficiency

    @property
    def efficiency(self) -> Q_:
        return (
            self._efficiency
            if hasattr(self, "_efficiency")
            else self.compute_efficiency
        )

    def __lt__(self, other: "TestPoint") -> bool:
        return self.capacity < other.capacity
