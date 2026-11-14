"""
point
=====

This module defines the `BasePoint` class and its subclasses, which represent a
system point with converted physical quantities.

Classes
-------
- BasePoint: A generic system point with fluid and capacity.
- DesignPoint: A specialized point for design conditions (rated point).
- TestPoint: A specialized point for test or operational data (measured points).
"""

import warnings

import numpy as np
from .constants import G
from .utilities.unit_conversion import extract_context, Q_, quantity_factory
from .utilities.fluid import Fluid

__all__ = ["BasePoint", "DesignPoint", "TestPoint"]


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
    >>> from pump import Q_, Fluid, BasePoint
    >>> water = Fluid(name="Water", density=Q_(997, "kg/m**3"))
    >>> # capacity is canonicalized to m**3/h regardless of the input unit:
    >>> point = BasePoint(fluid=water, capacity=Q_(0.1, "m**3/s"))
    >>> point.capacity.magnitude, str(point.capacity.units)
    (360.0, 'meter ** 3 / hour')
    >>> point.fluid.name
    'Water'
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

    The legacy keyword ``NPSH_available`` is accepted as an alias of ``npsha``
    (with a ``DeprecationWarning``).

    Examples
    --------
    >>> from pump import Q_, Fluid, DesignPoint
    >>> water = Fluid("Water", density=Q_(997, "kg/m**3"))
    >>> dp = DesignPoint(fluid=water, capacity=Q_(833, "m**3/h"),
    ...                  differential_head=Q_(73, "m"))
    >>> dp.differential_head.to("m").magnitude
    73
    """
    # Gravity constant
    g = G

    def __init__(
        self, fluid: Fluid, capacity: Q_, differential_head: Q_, **kwargs: dict[str, Q_]
    ) -> None:
        if "NPSH_available" in kwargs:
            warnings.warn(
                "The 'NPSH_available' keyword is deprecated; use 'npsha'.",
                DeprecationWarning,
                stacklevel=2,
            )
            legacy = kwargs.pop("NPSH_available")
            kwargs.setdefault("npsha", legacy)
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
        """
        Calculates the outlet pressure based on inlet pressure and various heads.

        Returns
        -------
        Q_
            The calculated outlet pressure.

        Raises
        ------
        AttributeError
            If `inlet_pressure` is not available on the point.
        """
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
        """
        Calculates the head difference due to elevation.

        Returns
        -------
        Q_
            The elevation head. Returns 0 m if `inlet_elevation` or
            `outlet_elevation` are not provided.
        """
        if hasattr(self, "inlet_elevation") and hasattr(self, "outlet_elevation"):
            return quantity_factory(self.outlet_elevation - self.inlet_elevation)
        return Q_(0, "m")

    @property
    def inlet_velocity(self) -> Q_:
        """
        Calculates the fluid velocity at the pump inlet.

        Returns
        -------
        Q_
            The inlet velocity. Returns 0 m/s if `inlet_diameter` is not
            provided.
        """
        if hasattr(self, "inlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.inlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def outlet_velocity(self) -> Q_:
        """
        Calculates the fluid velocity at the pump outlet.

        Returns
        -------
        Q_
            The outlet velocity. Returns 0 m/s if `outlet_diameter` is not
            provided.
        """
        if hasattr(self, "outlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.outlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def velocity_head(self) -> Q_:
        """
        Calculates the head difference due to change in fluid velocity.

        Returns
        -------
        Q_
            The velocity head. Returns 0 m if `inlet_diameter` or
            `outlet_diameter` are not provided.
        """
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


class TestPoint(BasePoint):
    """
    Specialized version of the BasePoint class for handling test or operational data.

    This class provides additional properties for calculating hydraulic parameters
    such as pressure head, velocity head, elevation head, and hydraulic power.

    Examples
    --------
    >>> from pump import Q_, Fluid, TestPoint
    >>> water = Fluid("Water", density=Q_(997, "kg/m**3"))
    >>> tp = TestPoint(fluid=water, capacity=Q_(833, "m**3/h"),
    ...                speed_of_rotation=Q_(1750, "rpm"), _head=Q_(73, "m"),
    ...                breaking_power=Q_(252, "kW"))
    >>> tp.head.to("m").magnitude
    73
    >>> tp.speed_of_rotation.to("rpm").magnitude
    1750
    """

    # Domain class, not a pytest test class — keep collectors from grabbing it
    # when it is imported into the test suite (name starts with "Test").
    __test__ = False

    g = G

    @property
    def pressure_head(self) -> Q_:
        """
        Calculates the head generated due to pressure difference.

        Returns
        -------
        Q_
            The pressure head.

        Raises
        ------
        ValueError
            If the fluid object does not have a 'density' attribute.
        AttributeError
            If 'delta_pressure' or both 'inlet_pressure' and 'outlet_pressure'
            are missing.
        """
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
        """
        Calculates the fluid velocity at the pump inlet.

        Returns
        -------
        Q_
            The inlet velocity. Returns 0 m/s if `inlet_diameter` is not
            provided.
        """
        if hasattr(self, "inlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.inlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def outlet_velocity(self) -> Q_:
        """
        Calculates the fluid velocity at the pump outlet.

        Returns
        -------
        Q_
            The outlet velocity. Returns 0 m/s if `outlet_diameter` is not
            provided.
        """
        if hasattr(self, "outlet_diameter"):
            return quantity_factory(
                self.capacity / (np.pi * self.outlet_diameter**2 / 4)
            )
        return Q_(0, "m/s")

    @property
    def velocity_head(self) -> Q_:
        """
        Calculates the head difference due to change in fluid velocity.

        ``(v_out**2 - v_in**2) / (2 g)`` with the velocities taken from
        ``capacity`` and the inlet/outlet diameters.  **Both** ``inlet_diameter``
        and ``outlet_diameter`` are required; if either is missing the velocity
        head is 0 m (it never uses a half-specified geometry).

        Returns
        -------
        Q_
            The velocity head. Returns 0 m if `inlet_diameter` or
            `outlet_diameter` are not provided.

        Examples
        --------
        >>> from pump import Q_, Fluid, TestPoint
        >>> water = Fluid("Water", density=Q_(998, "kg/m**3"))
        >>> tp = TestPoint(fluid=water, capacity=Q_(100, "m**3/h"),
        ...                inlet_diameter=Q_(150, "mm"))
        >>> tp.velocity_head.magnitude
        0
        """
        if hasattr(self, "inlet_diameter") and hasattr(self, "outlet_diameter"):
            return quantity_factory(
                (self.outlet_velocity**2 - self.inlet_velocity**2) / (2 * self.g)
            )
        return Q_(0, "m")

    @property
    def elevation_head(self) -> Q_:
        """
        Calculates the head difference due to elevation.

        ``outlet_elevation - inlet_elevation``.  **Both** elevations are
        required; if either is missing the elevation head is 0 m.

        Returns
        -------
        Q_
            The elevation head. Returns 0 m if `inlet_elevation` or
            `outlet_elevation` are not provided.

        Examples
        --------
        >>> from pump import Q_, Fluid, TestPoint
        >>> water = Fluid("Water", density=Q_(998, "kg/m**3"))
        >>> tp = TestPoint(fluid=water, capacity=Q_(100, "m**3/h"),
        ...                inlet_elevation=Q_(0.3, "m"),
        ...                outlet_elevation=Q_(0.8, "m"))
        >>> round(tp.elevation_head.to("m").magnitude, 3)
        0.5
        """
        if hasattr(self, "inlet_elevation") and hasattr(self, "outlet_elevation"):
            return quantity_factory(self.outlet_elevation - self.inlet_elevation)
        return Q_(0, "m")

    @property
    def compute_head(self) -> Q_:
        """
        Computes the total dynamic head (TDH) from its components.

        The TDH is the sum of pressure head, velocity head, and elevation head.
        The result is cached in the `_head` attribute.

        Returns
        -------
        Q_
            The computed total dynamic head.

        Examples
        --------
        A measured pressure rise (``delta_pressure``) over a fluid whose density
        is given in kg/m³:

        >>> from pump import Q_, Fluid, TestPoint
        >>> water = Fluid("Water", density=Q_(998, "kg/m**3"))
        >>> tp = TestPoint(fluid=water, capacity=Q_(100, "m**3/h"),
        ...                delta_pressure=Q_(5, "bar"))
        >>> round(tp.compute_head.to("m").magnitude, 1)
        51.1
        """
        TDH = self.pressure_head + self.velocity_head + self.elevation_head
        self._head = quantity_factory(TDH)
        return self._head

    @property
    def head(self) -> Q_:
        """
        The total dynamic head of the point.

        Returns a cached `_head` value if it exists, otherwise computes it.

        Returns
        -------
        Q_
            The total dynamic head.
        """
        return self._head if hasattr(self, "_head") else self.compute_head

    @head.setter
    def head(self, value: Q_) -> None:
        """
        Sets the head value for the point.

        Parameters
        ----------
        value : Q_
            The head value to set, as a Pint quantity.
        """
        self._head = quantity_factory(value)

    @property
    def compute_hydraulic_power(self) -> Q_:
        """
        Computes the hydraulic power and caches it in `_hydraulic_power`.

        Returns
        -------
        Q_
            The computed hydraulic power.
        """
        self._hydraulic_power = quantity_factory(
            self.fluid.density * self.capacity * self.g * self.head
        )
        return self._hydraulic_power

    @property
    def hydraulic_power(self) -> Q_:
        """
        The hydraulic power of the point.

        Returns a cached `_hydraulic_power` value if it exists, otherwise
        computes it.

        Returns
        -------
        Q_
            The hydraulic power.
        """
        return (
            self._hydraulic_power
            if hasattr(self, "_hydraulic_power")
            else self.compute_hydraulic_power
        )

    @property
    def compute_efficiency(self) -> Q_:
        """
        Computes the pump efficiency and caches it in `_efficiency`.

        Returns
        -------
        Q_
            The computed efficiency, converted to percent.

        Raises
        ------
        AttributeError
            If `breaking_power` is not available on the point.
        """
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
        """
        The efficiency of the point.

        Returns a cached `_efficiency` value if it exists, otherwise
        computes it.

        Returns
        -------
        Q_
            The efficiency.
        """
        return (
            self._efficiency
            if hasattr(self, "_efficiency")
            else self.compute_efficiency
        )

    def __lt__(self, other: "TestPoint") -> bool:
        """
        Compares two TestPoint objects based on their capacity for sorting.
        """
        return self.capacity < other.capacity

    def __repr__(self) -> str:
        return f"TestPoint(fluid={self.fluid.name}, capacity={self.capacity:.2f~P})"

    def __str__(self) -> str:
        """Returns a detailed string representation of the fluid's properties."""
        return f"TestPoint({self._get_properties()})"
