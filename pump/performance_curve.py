"""
peroformance_curve
==================

This module defines the PerformanceCurve class, which represents a system point with converted
physical quantities.

Classes
-------
- PerformanceCurve: Represents a system point with capacity and inlet pressure.
- PerformanceChecker: Check the performance of a system based on its design point and performance curve.
- PerformanceFitter: Handles polynomial regression for performance metrics.
"""

from typing import Optional, List, Dict, Any
import warnings
import numpy as np
import matplotlib.pyplot as plt
from .utilities.unit_conversion import Q_, quantity_factory
from .utilities.fluid import Fluid
from .point import DesignPoint, TestPoint
from .acceptance import AcceptanceCriteria, evaluate_performance, _band
from .viscosity import b_parameter, correction_factors
from tabulate import tabulate
import io

__all__ = ["PerformanceChecker", "PerformanceCurve"]

from .design import color as _c

class PerformanceFitter:
    """
    Handles polynomial regression for performance metrics (head, efficiency, power),
    with lazy computation of polynomial coefficients.

    Parameters
    ----------
    points : list of TestPoint
        A list of TestPoint instances used for polynomial regression.
    polynomial_degree : int, optional
        The degree of the polynomial fit (default is 4).
    """

    def __init__(self, points, polynomial_degree: int = 4) -> None:
        self.points = points
        self.polynomial_degree = polynomial_degree
        self._capacities: Optional[np.ndarray] = None
        self._heads: Optional[np.ndarray] = None
        self._efficiencies: Optional[np.ndarray] = None
        self._powers: Optional[np.ndarray] = None
        self._head_coeffs: Optional[np.ndarray] = None
        self._efficiency_coeffs: Optional[np.ndarray] = None
        self._power_coeffs: Optional[np.ndarray] = None
    
    @property
    def capacities(self) -> np.ndarray:
        """
        Lazily computes and returns the capacity values as a NumPy array.

        Returns
        -------
        np.ndarray
            Array of capacity values.
        """
        if self._capacities is None:
            self._capacities = np.array([p.capacity.magnitude for p in self.points])
        return self._capacities

    @property
    def heads(self) -> np.ndarray:
        """
        Lazily computes and returns the head values as a NumPy array.

        Returns
        -------
        np.ndarray
            Array of head values.
        """
        if self._heads is None:
            self._heads = np.array([p.head.magnitude for p in self.points])
        return self._heads

    @property
    def efficiencies(self) -> np.ndarray:
        """
        Lazily computes and returns the efficiency values as a NumPy array.

        Returns
        -------
        np.ndarray
            Array of efficiency values.
        """
        if self._efficiencies is None:
            self._efficiencies = np.array([p.efficiency.magnitude for p in self.points])
        return self._efficiencies

    @property
    def powers(self) -> np.ndarray:
        """
        Lazily computes and returns the power values as a NumPy array.

        Returns
        -------
        np.ndarray
            Array of power values.
        """
        
        if self._powers is None:
            self._powers = np.array([p.breaking_power.magnitude for p in self.points])
        return self._powers

    @property
    def head_coeffs(self) -> np.ndarray:
        """
        Lazily computes the polynomial regression coefficients for head vs. capacity.

        Returns
        -------
        np.ndarray
            Array of polynomial coefficients.
        """
        if self._head_coeffs is None:
            capacities = self.capacities
            heads = np.array([p.head.magnitude for p in self.points])
            self._head_coeffs = np.polyfit(capacities, heads, self.polynomial_degree)
        return self._head_coeffs

    @property
    def efficiency_coeffs(self) -> np.ndarray:
        """
        Lazily computes the polynomial regression coefficients for efficiency vs. capacity.

        Returns
        -------
        np.ndarray
            Array of polynomial coefficients.
        """
        if self._efficiency_coeffs is None:
            capacities = self.capacities
            efficiencies = np.array([p.efficiency.magnitude for p in self.points])
            self._efficiency_coeffs = np.polyfit(capacities, efficiencies, self.polynomial_degree)
        return self._efficiency_coeffs

    @property
    def power_coeffs(self) -> np.ndarray:
        """
        Lazily computes the polynomial regression coefficients for power vs. capacity.

        Returns
        -------
        np.ndarray
            Array of polynomial coefficients.
        """
        if self._power_coeffs is None:
            capacities = self.capacities
            powers = np.array([p.breaking_power.magnitude for p in self.points])
            self._power_coeffs = np.polyfit(capacities, powers, self.polynomial_degree)
        return self._power_coeffs
    
    

class PerformanceCurve:
    """
    A container for handling a collection of TestPoint objects that share the same fluid.

    This class allows you to:
      - Scale the pump speed to a new speed (using simplified pump affinity laws).
      - Change the fluid of the entire collection.
      - Always return a new instance when these transformations are applied,
        preserving the original data.
      - Predict performance metrics like head, efficiency, and power based on polynomial fits.
      - Plot pump performance curves.

    Parameters
    ----------
    fluid : Fluid
        The fluid object shared by all TestPoints in this collection.
    points : list of TestPoint
        A list of TestPoint instances that share the same fluid.
    polynomial_degree : int, optional
        The degree of the polynomial fit used by the internal fitter (default is 4).

    Attributes
    ----------
    fluid : Fluid
        The fluid used by all points in this collection.
    points : list of TestPoint
        The list of performance points stored in this collection.
    polynomial_degree : int
        The polynomial degree used for curve fitting.

    Examples
    --------
    >>> from pump import Q_, Fluid, TestPoint, PerformanceCurve
    >>> water = Fluid("Water", density=Q_(997, "kg/m**3"))
    >>> points = [
    ...     TestPoint(fluid=water, capacity=Q_(q, "m**3/h"),
    ...               speed_of_rotation=Q_(1750, "rpm"), _head=Q_(h, "m"),
    ...               breaking_power=Q_(p, "kW"))
    ...     for q, h, p in [(0, 117, 180), (600, 95, 240), (1000, 55, 260)]
    ... ]
    >>> curve = PerformanceCurve(water, points, polynomial_degree=2)
    >>> len(curve)
    3
    >>> # Scale to a new speed with the affinity laws (3500 rpm here):
    >>> faster = curve.to_speed(Q_(3500, "rpm"))
    >>> faster.points[-1].speed_of_rotation.to("rpm").magnitude
    3500
    """

    def __init__(self, fluid: Fluid, points: List[TestPoint], polynomial_degree: int = 4) -> None:
        self.fluid = fluid
        self.polynomial_degree = polynomial_degree
        for pt in points:
            if pt.fluid != fluid:
                raise ValueError("All TestPoints must have the same fluid.")
        self.points = sorted(points) # Sort by capacity
        self.fitter = PerformanceFitter(points, polynomial_degree=polynomial_degree)
        # Set by ``to_viscous`` on the curve it returns: {"B", "C_Q", "C_H", "C_eta"}.
        self.viscosity_correction: Optional[Dict[str, float]] = None

    def predict_metric(self, capacity, coeffs, unit) -> Q_:
        capacity_value = capacity.to("m**3/h").magnitude
        metric_value = np.polyval(coeffs, capacity_value)
        return quantity_factory(Q_(metric_value, unit))

    def predict_head(self, capacity: Q_) -> Q_:
        """
        Predicts the head for a given flow (capacity) using the stored polynomial.

        Parameters
        ----------
        capacity : Q_
            The input flow in m³/h.

        Returns
        -------
        Q_
            The predicted head in meters.
        """
        coeffs = self.fitter.head_coeffs
        return self.predict_metric(capacity, coeffs, "m")

    def predict_efficiency(self, capacity: Q_) -> Q_:
        """
        Predicts the efficiency for a given flow (capacity) using the stored polynomial.

        Parameters
        ----------
        capacity : Q_
            The input flow in m³/h.

        Returns
        -------
        Q_
            The predicted efficiency in percent.
        """
        coeffs = self.fitter.efficiency_coeffs
        return self.predict_metric(capacity, coeffs, "%")

    def predict_breaking_power(self, capacity: Q_) -> Q_:
        """
        Predicts the power for a given flow (capacity) using the stored polynomial.

        Parameters
        ----------
        capacity : Q_
            The input flow in m³/h.

        Returns
        -------
        Q_
            The predicted power in kW.
        """
        coeffs = self.fitter.power_coeffs
        return self.predict_metric(capacity, coeffs, "kW")

    def predicted_data(self, capacity:Q_) -> Dict:
        efficiency = self.predict_efficiency(capacity)
        head = self.predict_head(capacity)
        shutoff_head = self.predict_head(Q_(0, "m**3/h"))

        return {
            "Head": head,
            "Efficiency": efficiency,
            "Head Shuttoff": shutoff_head
        }

    def bep(self):
        """
        Best-efficiency point of the fitted curve.

        The fitted efficiency polynomial is sampled densely over the tested
        capacity range and the capacity of maximum efficiency is taken.

        Returns
        -------
        tuple of Q_
            ``(Q_bep, H_bep, eta_bep)`` in m³/h, m and percent.
        """
        caps = [p.capacity.to("m**3/h").magnitude for p in self.points]
        q = np.linspace(min(caps), max(caps), 2001)
        eff = np.polyval(self.fitter.efficiency_coeffs, q)
        q_bep = Q_(float(q[int(np.argmax(eff))]), "m**3/h")
        return q_bep, self.predict_head(q_bep), self.predict_efficiency(q_bep)

    def plot_performance_curve(self, chart_title=None, capacity: Optional[Q_] = None, return_io=False,
                               head_ylim=None, power_ylim=None, efficiency_ylim=None,
                               npsh_curve=None, npsha: Optional[Q_] = None,
                               npshr_quoted: Optional[Q_] = None, npsh_ylim=None):
        """
        Plots the pump performance curve with three subplots:
        - Head vs. Capacity (takes up more height)
        - Power vs. Capacity
        - Efficiency vs. Capacity

        Parameters
        ----------
        chart_title : str, optional
            Custom title for the chart.
        capacity : Q_, optional
            A capacity value to highlight on the curve with crosshairs.
        return_io : bool, optional
            If True, returns a BytesIO PNG stream instead of displaying.
        head_ylim : tuple of (float, float), optional
            Y-axis limits for the Head subplot, e.g. (80, 130).
        power_ylim : tuple of (float, float), optional
            Y-axis limits for the Power subplot, e.g. (150, 550).
        efficiency_ylim : tuple of (float, float), optional
            Y-axis limits for the Efficiency subplot, e.g. (0, 100).
        npsh_curve : pump.npsh.NPSHrCurve, optional
            NPSH3 test points.  When given (and power and efficiency are
            present) a fourth subplot NPSHr vs. Capacity is drawn: the points,
            their fit over the tested range only, ``npsha`` as a dash-dot line
            and ``npshr_quoted`` (datasheet NPSHr) as a diamond at ``capacity``.
        npsh_ylim : tuple of (float, float), optional
            Y-axis limits for the NPSHr subplot.
        """
        capacities = self.fitter.capacities
        heads = self.fitter.heads

        has_power = all(hasattr(p, "breaking_power") for p in self.points)
        has_efficiency = all(hasattr(p, "efficiency") for p in self.points)

        # Generate smooth values for polynomial curves
        smooth_capacities = np.linspace(min(capacities), max(capacities), 100)
        head_curve = np.polyval(self.fitter.head_coeffs, smooth_capacities)

        # Compute fitted values for the given flow
        if capacity is not None:
            capacity_value = capacity.to("m**3/h").magnitude
            fitted_head = np.polyval(self.fitter.head_coeffs, capacity_value)
    
            if has_power and has_efficiency:
                fitted_power = np.polyval(self.fitter.power_coeffs, capacity_value)
                fitted_efficiency = np.polyval(self.fitter.efficiency_coeffs, capacity_value)

        # Setup figure based on available data
        with_npsh = npsh_curve is not None and has_power and has_efficiency
        if with_npsh:
            fig, axes = plt.subplots(
                4, 1, sharex=True, figsize=(8, 10),
                gridspec_kw={'height_ratios': [5, 3, 4, 3]}
            )
        elif has_power and has_efficiency:
            fig, axes = plt.subplots(
                3, 1, sharex=True, figsize=(8, 8), gridspec_kw={'height_ratios': [5, 3, 4]}
            )
        else:
            fig, axes = plt.subplots(1, 1, figsize=(8, 4))  # Only one plot needed
    
        # Plot Head vs Capacity
        if has_power and has_efficiency:
            ax1 = axes[0]
        else:
            ax1 = axes

        ax1.scatter(capacities, heads, color=_c("chart-head"), label="Head Data", marker="o")  # Data points only
        ax1.plot(smooth_capacities, head_curve, "-", color=_c("chart-head"), label="Head Fit")  # Polynomial curve
        ax1.set_ylabel("Head (m)")
        if chart_title:
            ax1.set_title(f"{chart_title} - {self.fluid.name}")
        else:
            ax1.set_title(f"Pump Performance Curve - {self.fluid.name} Curve")
        ax1.grid()
        ax1.legend()

        if capacity is not None:
            ax1.plot(capacity_value, fitted_head, "x", color=_c("chart-head"), markersize=10, label=f"Capacity {capacity_value:.1f} m³/h")
            ax1.axvline(capacity_value, color=_c("chart-cursor"), linestyle="dashed")  # Vertical dashed line
            ax1.axhline(fitted_head, color=_c("chart-cursor"), linestyle="dashed")  # Horizontal dashed line

            # Add tick labels
            ax1.text(ax1.get_xlim()[0],
                     fitted_head,
                     f"{fitted_head:.1f}",
                     verticalalignment='center',
                     horizontalalignment='left',
                     fontsize=10, bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3'))
            
            if not has_power and not has_efficiency:
                ax1.text(capacity_value,
                         ax1.get_ylim()[0],
                         f"{capacity_value:.1f}",
                         verticalalignment='bottom',
                         horizontalalignment='center',
                         fontsize=10,
                         bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3'))
                

        if has_power and has_efficiency:
            # Power vs Capacity
            powers = np.array([p.breaking_power.to("kW").magnitude for p in self.points])
            power_curve = np.polyval(self.fitter.power_coeffs, smooth_capacities)
            
            ax2 = axes[1]
            ax2.scatter(capacities, powers, color=_c("chart-power"), label="Power Data", marker="o")
            ax2.plot(smooth_capacities, power_curve, "-", color=_c("chart-power"), label="Power Fit")
            ax2.set_ylabel("Power (kW)")
            ax2.grid()
            ax2.legend()
            ax2.yaxis.set_label_position("right")
            ax2.yaxis.tick_right()

            if capacity is not None:
                ax2.plot(capacity_value, fitted_power, "x", color=_c("chart-power"), markersize=10, label=f"Capacity {capacity_value:.1f} m³/h")
                ax2.axvline(capacity_value, color=_c("chart-cursor"), linestyle="dashed")
                ax2.axhline(fitted_power, color=_c("chart-cursor"), linestyle="dashed")
                
                # Add tick labels
                ax2.text(ax2.get_xlim()[0],
                         fitted_power,
                         f"{fitted_power:.1f}",
                         verticalalignment='center',
                         horizontalalignment='left',
                         fontsize=10,
                         bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3'))
               
            # Efficiency vs Capacity
            efficiencies = np.array([p.efficiency.to("percent").magnitude for p in self.points])
            efficiency_curve = np.polyval(self.fitter.efficiency_coeffs, smooth_capacities)
            
            ax3 = axes[2]
            ax3.scatter(capacities, efficiencies, color=_c("chart-efficiency"), label="Efficiency Data", marker="o")
            ax3.plot(smooth_capacities, efficiency_curve, "-", color=_c("chart-efficiency"), label="Efficiency Fit")
            ax3.set_ylabel("Efficiency (%)")
            ax3.set_xlabel("Capacity (m³/h)")
            ax3.grid()
            ax3.legend()

            if capacity is not None:
                ax3.plot(capacity_value, fitted_efficiency, "x", color=_c("chart-efficiency"), markersize=10, label=f"Capacity {capacity_value:.1f} m³/h")
                ax3.axvline(capacity_value, color=_c("chart-cursor"), linestyle="dashed")
                ax3.axhline(fitted_efficiency, color=_c("chart-cursor"), linestyle="dashed")
    
                # Add tick labels
                ax3.text(capacity_value, ax3.get_ylim()[0], f"{capacity_value:.1f}", verticalalignment='bottom', horizontalalignment='center', fontsize=10, bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3'))
                ax3.text(ax3.get_xlim()[0], fitted_efficiency, f"{fitted_efficiency:.1f}", verticalalignment='center', horizontalalignment='left', fontsize=10, bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3'))

        if with_npsh:
            ax3.set_xlabel("")
            ax4 = axes[3]
            nq = np.array([q.to("m**3/h").magnitude for q in npsh_curve.q], dtype=float)
            nv = np.array([v.to("m").magnitude for v in npsh_curve.npshr], dtype=float)
            grid = np.linspace(nq.min(), nq.max(), 100)
            fit = np.array([npsh_curve(Q_(x, "m**3/h")).to("m").magnitude for x in grid])
            ax4.scatter(nq, nv, color=_c("chart-npsh"), label="NPSH3 Data", marker="o")
            ax4.plot(grid, fit, "-", color=_c("chart-npsh"), label="NPSHr Fit")
            if npsha is not None:
                a = npsha.to("m").magnitude
                ax4.axhline(a, color=_c("chart-npsha"), linestyle="-.", label=f"NPSHa {a:.2f} m")
            if capacity is not None:
                ax4.axvline(capacity_value, color=_c("chart-cursor"), linestyle="dashed")
                if nq.min() <= capacity_value <= nq.max():
                    at = npsh_curve(capacity).to("m").magnitude
                    ax4.plot(capacity_value, at, "x", color=_c("chart-npsh"), markersize=10)
                    ax4.text(ax4.get_xlim()[0], at, f"{at:.2f}", verticalalignment='center',
                             horizontalalignment='left', fontsize=10,
                             bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3'))
                if npshr_quoted is not None:
                    ax4.plot(capacity_value, npshr_quoted.to("m").magnitude, "D",
                             markerfacecolor="white", markeredgecolor=_c("chart-npsh"),
                             markersize=7, label="Quoted NPSHr")
            ax4.set_ylabel("NPSHr (m)")
            ax4.set_xlabel("Capacity (m³/h)")
            ax4.yaxis.set_label_position("right")
            ax4.yaxis.tick_right()
            ax4.grid()
            ax4.legend(loc="center left")
            if npsh_ylim is not None:
                ax4.set_ylim(npsh_ylim)

        if head_ylim is not None:
            ax1.set_ylim(head_ylim)

        if has_power and has_efficiency:
            if power_ylim is not None:
                ax2.set_ylim(power_ylim)
            if efficiency_ylim is not None:
                ax3.set_ylim(efficiency_ylim)

        plt.tight_layout()
        
        if return_io:
            image_stream = io.BytesIO()
            fig.savefig(image_stream, format='png')
            plt.close(fig)
            image_stream.seek(0)
            return image_stream
        plt.show()

        

    def to_speed(self, new_speed: Q_) -> "PerformanceCurve":
        """
        Create a new PerformanceCurve with all TestPoints scaled to `new_speed`.

        Uses simplified pump affinity laws:
          - Capacity scales proportionally to speed ratio: Q2 = Q1 * (N2 / N1)
          - Head scales as (N2 / N1)^2 (implicitly handled if you re-compute head).
          - Power scales as (N2 / N1)^3.

        Parameters
        ----------
        new_speed : Q_
            The target speed for all points in this new curve (e.g., Q_(4000, "rpm")).

        Returns
        -------
        PerformanceCurve
            A new PerformanceCurve instance with updated speeds and derived values.

        Raises
        ------
        AttributeError
            If any TestPoint does not have a `speed_of_rotation` attribute.
        """
        new_points = []
        for p in self.points:
            if not hasattr(p, "speed_of_rotation"):
                raise AttributeError(
                    f"TestPoint {p} has no 'speed_of_rotation' attribute."
                )

            # Affinity-laws ratio
            ratio = new_speed / p.speed_of_rotation

            # Scale capacity
            new_capacity = p.capacity * ratio

            # Scales Head
            new_head = p.head * ratio**2

            # Scale power if `breaking_power` exists
            new_breaking_power = (
                p.breaking_power * ratio**3
                if hasattr(p, "breaking_power")
                else None
            )

            # Collect all other attributes except those we want to override
            new_attrs: Dict[str, Any] = {}
            new_attrs["_head"] = new_head
            new_attrs["_efficiency"] = p.efficiency

            # If we had a breaking_power before, include the scaled one
            if new_breaking_power is not None:
                new_attrs["breaking_power"] = new_breaking_power

            # Create a new TestPoint with updated capacity and speed
            new_point = TestPoint(
                fluid=p.fluid,
                capacity=new_capacity,
                speed_of_rotation=new_speed,
                **new_attrs
            )
            new_points.append(new_point)

        return PerformanceCurve(self.fluid, new_points, polynomial_degree=self.polynomial_degree)

    def to_diameter(self, d_new: Q_, d_ref: Q_, max_trim: float = 0.05) -> "PerformanceCurve":
        """
        Create a new PerformanceCurve with all TestPoints scaled from the
        impeller diameter ``d_ref`` to ``d_new`` (UC-07 impeller trim).

        Uses the standard **diameter affinity approximation** (speed unchanged):
          - Capacity scales with the diameter ratio: Q2 = Q1 * (D2 / D1)
          - Head scales as (D2 / D1)^2.
          - Power scales as (D2 / D1)^3.
          - Efficiency is unchanged.

        The approximation degrades for large trims, so a ``UserWarning`` is
        issued when ``|1 - d_new / d_ref| > max_trim``.  HI-style trim
        corrections are not applied.

        Parameters
        ----------
        d_new : Q_
            Target impeller diameter (a length, e.g. ``Q_(122, "mm")``).
        d_ref : Q_
            Impeller diameter this curve corresponds to.
        max_trim : float, optional
            Largest fractional diameter change before warning (default 0.05).

        Returns
        -------
        PerformanceCurve
            A new instance; ``self`` is not modified.

        Raises
        ------
        ValueError
            If a diameter is not a length Quantity or is not positive.

        Warns
        -----
        UserWarning
            When the diameter change exceeds ``max_trim``.
        """
        for name, d in (("d_new", d_new), ("d_ref", d_ref)):
            if not hasattr(d, "to"):
                raise ValueError(f"{name} must be a Pint length Quantity.")
        d_new_mm = float(d_new.to("mm").magnitude)
        d_ref_mm = float(d_ref.to("mm").magnitude)
        if not (d_new_mm > 0.0 and d_ref_mm > 0.0):
            raise ValueError("Impeller diameters must be > 0.")
        ratio = d_new_mm / d_ref_mm

        change = ratio - 1.0
        if abs(change) > max_trim:
            warnings.warn(
                f"Impeller diameter change of {change:+.1%} exceeds max_trim "
                f"({max_trim:.1%}); the diameter affinity approximation loses "
                f"accuracy for large trims.",
                UserWarning,
                stacklevel=2,
            )

        new_points = []
        for p in self.points:
            new_attrs: Dict[str, Any] = {}
            new_attrs["_head"] = p.head * ratio**2
            new_attrs["_efficiency"] = p.efficiency
            if hasattr(p, "breaking_power"):
                new_attrs["breaking_power"] = p.breaking_power * ratio**3
            if hasattr(p, "speed_of_rotation"):
                new_attrs["speed_of_rotation"] = p.speed_of_rotation

            new_points.append(
                TestPoint(
                    fluid=p.fluid,
                    capacity=p.capacity * ratio,
                    **new_attrs
                )
            )

        return PerformanceCurve(self.fluid, new_points, polynomial_degree=self.polynomial_degree)

    def to_fluid(self, new_fluid: Fluid) -> "PerformanceCurve":
        """
        Create a new PerformanceCurve by assigning a new fluid to all TestPoints.

        The capacity, speed, and other dimensional attributes remain the same, but the
        fluid-dependent calculations (head, hydraulic_power, etc.) will reflect the
        properties of the new fluid when accessed.

        Parameters
        ----------
        new_fluid : Fluid
            The new fluid object to assign to all TestPoints.

        Returns
        -------
        PerformanceCurve
            A new PerformanceCurve instance with all TestPoints referencing `new_fluid`.
        """

        new_points = []
        for p in self.points:
            # Collect attributes except the fluid
            new_attrs: Dict[str, Any] = {}
            new_attrs["_head"] = p.head
            # If we had a efficiency before, include the scaled one
            if hasattr(p, "_efficiency"):
                new_attrs["_efficiency"] = p.efficiency
                new_attrs["breaking_power"] = quantity_factory(new_fluid.density * p.capacity * p.g * p.head / p.efficiency)
            
            # Create a new TestPoint with the new fluid
            new_point = TestPoint(
                fluid=new_fluid,
                capacity=p.capacity,
                speed_of_rotation=p.speed_of_rotation,
                **new_attrs
            )
            new_points.append(new_point)

        return PerformanceCurve(new_fluid, new_points, polynomial_degree=self.polynomial_degree)

    def to_viscous(self, new_fluid: Fluid, stages: int = 1) -> "PerformanceCurve":
        """
        Create a new PerformanceCurve corrected from water to a viscous liquid
        (HI 9.6.7 / ISO TR 17766, see :mod:`pump.viscosity`).

        The equations are ANSI/HI 9.6.7-2010 Eq. 2-7 as reproduced by
        midstreamcalculator.com; they were cross-checked independently but NOT
        against the standard text.

        The parameter B comes from the water best-efficiency point (:meth:`bep`)
        and the speed of the curve.  Every point becomes ``Q * C_Q``,
        ``H * C_H(Q / Q_BEP)`` and ``eta * C_eta``, and the breaking power is
        recomputed from the viscous liquid density,
        ``P = rho * g * Q_vis * H_vis / eta_vis``.  For ``B <= 1`` the result is
        the same as :meth:`to_fluid` (density only).  The returned curve carries
        ``viscosity_correction = {"B", "C_Q", "C_H", "C_eta"}`` (factors at the BEP).

        Parameters
        ----------
        new_fluid : Fluid
            Target liquid; must carry its density and a kinematic viscosity
            (``kinematic_viscosity`` or ``viscosity``; a dynamic viscosity is
            converted with the density).
        stages : int, optional
            Number of stages; HI uses the head *per stage* in B (default 1).

        Returns
        -------
        PerformanceCurve
            A new instance; ``self`` is not modified.

        Raises
        ------
        ValueError
            If the fluid has no viscosity or ``stages`` is not a positive integer.
        AttributeError
            If a point has no ``speed_of_rotation``.

        Warns
        -----
        UserWarning
            When B >= 40 (outside the method validity).
        """
        if int(stages) < 1:
            raise ValueError("stages must be a positive integer.")
        nu = _kinematic_viscosity(new_fluid)
        speed = getattr(self.points[0], "speed_of_rotation", None)
        if speed is None:
            raise AttributeError(
                f"TestPoint {self.points[0]} has no 'speed_of_rotation' attribute."
            )
        q_bep, h_bep, _eta_bep = self.bep()
        b = b_parameter(nu, q_bep, h_bep / int(stages), speed)
        c_q_bep, c_h_bep, c_eta_bep = correction_factors(b)  # warns once if B >= 40
        info = {"B": b, "C_Q": c_q_bep, "C_H": c_h_bep, "C_eta": c_eta_bep}

        if b <= 1.0:
            curve = self.to_fluid(new_fluid)
            curve.viscosity_correction = info
            return curve

        new_points = []
        for p in self.points:
            ratio = float((p.capacity / q_bep).to("dimensionless").magnitude)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                c_q, c_h, c_eta = correction_factors(b, ratio)

            new_capacity = p.capacity * c_q
            new_head = p.head * c_h
            new_efficiency = p.efficiency * c_eta

            new_attrs = {"_head": new_head, "_efficiency": new_efficiency}
            if _dimensionless(new_efficiency) > 0.0:
                new_attrs["breaking_power"] = quantity_factory(
                    new_fluid.density * new_capacity * p.g * new_head / new_efficiency
                )
            elif hasattr(p, "breaking_power"):
                # Zero efficiency (shut-off): no hydraulic power, scale by density.
                new_attrs["breaking_power"] = quantity_factory(
                    p.breaking_power * (new_fluid.density / p.fluid.density)
                )

            new_points.append(
                TestPoint(
                    fluid=new_fluid,
                    capacity=new_capacity,
                    speed_of_rotation=p.speed_of_rotation,
                    **new_attrs
                )
            )

        curve = PerformanceCurve(new_fluid, new_points, polynomial_degree=self.polynomial_degree)
        curve.viscosity_correction = info
        return curve
    
    @property
    def test_summary(self) -> str:
        results = []
        for point in self.points:
            results.append([
                f"{point.capacity:0.02f~P}", 
                f"{point.head:0.02f~P}",
                f"{getattr(point, "breaking_power", 0):0.02f~P}" if hasattr(point, "breaking_power") else "N/A",
                f"{getattr(point, "hydraulic_power", 0):0.02f~P}" if hasattr(point, "hydraulic_power") else "N/A",
                f"{getattr(point, "efficiency", 0):0.02f~P}" if hasattr(point, "efficiency") else "N/A",
            ])

        headers = ["Flow", "Head", "Breaking Power", "Hydralic Power", "Efficiency"]
        return tabulate(results, headers=headers, tablefmt="grid")
    
    @property
    def test_data(self) -> Dict:
        data = {
            "Capacity" : [p.capacity for p in self.points],
            "Head" : [p.head for p in self.points],
            "Breaking Power" : [p.breaking_power for p in self.points if hasattr(self.points[0], "breaking_power") ],
            "Hydraulic Power" : [p.hydraulic_power for p in self.points if hasattr(self.points[0], "hydraulic_power") ],
            "Efficiency" : [p.efficiency for p in self.points if hasattr(self.points[0], "efficiency") ],
        }
        return data

    def __len__(self) -> int:
        """
        Returns
        -------
        int
            The number of TestPoints in this collection.
        """
        return len(self.points)

    def __getitem__(self, index: int) -> TestPoint:
        """
        Access an individual TestPoint by index.

        Parameters
        ----------
        index : int
            The index of the desired TestPoint in the `points` list.

        Returns
        -------
        TestPoint
            The corresponding TestPoint.
        """
        return self.points[index]

    def __iter__(self):
        """
        Returns
        -------
        iterator of TestPoint
            An iterator over the TestPoints in this collection.
        """
        return iter(self.points)

    def __repr__(self) -> str:
        """
        Returns
        -------
        str
            A concise string representation of the PerformanceCurve.
        """
        return f"PerformanceCurve(fluid={self.fluid}, points={len(self.points)})"
    

def _fmt_value(value) -> str:
    """Format a table cell: Pint quantities with ``0.02f~P``, others as text."""
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    try:
        return f"{value:0.02f~P}"
    except (TypeError, ValueError):
        return str(value)


def _dimensionless(value) -> float:
    """Float value of a dimensionless quantity (percent aware) or a number."""
    if hasattr(value, "to"):
        return float(value.to("dimensionless").magnitude)
    return float(value)


def _kinematic_viscosity(fluid: Fluid) -> Q_:
    """Kinematic viscosity (cSt) of ``fluid``.

    Reads ``kinematic_viscosity`` (e.g. ``Water``) or ``viscosity``; a dynamic
    viscosity is divided by the fluid density.
    """
    nu = getattr(fluid, "kinematic_viscosity", None)
    if nu is None:
        visc = getattr(fluid, "viscosity", None)
        if visc is None:
            raise ValueError(
                "to_viscous needs a fluid carrying a (kinematic) viscosity."
            )
        if visc.check("[length] ** 2 / [time]"):
            nu = visc
        else:
            nu = visc / fluid.density
    return nu.to("cSt")


class PerformanceChecker:
    """
    A class to check and validate the performance of a system based on a design point
    and performance curve.

    The tolerances come from an :class:`pump.acceptance.AcceptanceCriteria`
    (default: ``api610:12``, which reproduces the historical numbers: head
    +/-3 %, shut-off +/-10/8/5 % by rated differential head, power +4 %).

    Examples
    --------
    >>> from pump import Q_, Fluid, DesignPoint, TestPoint, PerformanceCurve, PerformanceChecker
    >>> water = Fluid("Water", density=Q_(997, "kg/m**3"))
    >>> points = [
    ...     TestPoint(fluid=water, capacity=Q_(q, "m**3/h"),
    ...               speed_of_rotation=Q_(1750, "rpm"), _head=Q_(h, "m"),
    ...               breaking_power=Q_(p, "kW"))
    ...     for q, h, p in [(0, 117, 180), (600, 95, 240), (833, 73, 252), (1000, 55, 260)]
    ... ]
    >>> curve = PerformanceCurve(water, points, polynomial_degree=3)
    >>> dp = DesignPoint(fluid=water, capacity=Q_(833, "m**3/h"),
    ...                  differential_head=Q_(73, "m"), breaking_power=Q_(252, "kW"),
    ...                  head_shutoff=Q_(117, "m"))
    >>> chk = PerformanceChecker(dp, curve)
    >>> chk.head_tolerance  # API 610: +/-3% on rated head
    0.03
    >>> chk.shutoff_tolerance  # rated head 73 m <= 75 -> 10%
    0.1
    """
    def __init__(
        self,
        design_point: DesignPoint,
        performance_curve: PerformanceCurve,
        acceptable_limits: Optional[Dict[str, float]] = None,
        criteria: Optional[AcceptanceCriteria] = None,
        tolerances: Optional[Dict[str, Optional[float]]] = None,
    ):
        """
        Initializes the PerformanceChecker with a design point and performance curve.
        
        Parameters
        ----------
        design_point : Any
            The design point containing head, shutoff head, and breaking power values.
        performance_curve : Any
            The performance curve data to be evaluated.
        acceptable_limits : dict, optional
            Deprecated and ignored; pass ``criteria`` instead.
        criteria : AcceptanceCriteria, optional
            Tolerance tables (default: ``AcceptanceCriteria.default()``).
        tolerances : dict, optional
            User overrides of the criteria (``{"head", "shutoff", "power",
            "efficiency"}``, fractions), applied exactly as
            :func:`pump.acceptance.evaluate_performance` applies them, so the
            limits in :attr:`report_summary` match the verdict.
        """
        if acceptable_limits is not None:
            warnings.warn(
                "acceptable_limits is ignored; pass criteria=AcceptanceCriteria…",
                DeprecationWarning,
                stacklevel=2,
            )
        self.design_point = design_point
        self.curve = performance_curve
        self.criteria = criteria if criteria is not None else AcceptanceCriteria.default()
        self.tolerances: Dict[str, Optional[float]] = dict(tolerances or {})

        rated_head = self.design_point.differential_head
        self.head_tolerance_minus, self.head_tolerance = self._head_band()
        self.shutoff_tolerance: float = self._get_shutoff_tolerance()
        self.breaking_power_tolerance: float = self.tolerances.get(
            "power", self.criteria.power_tol_plus
        )

        self._compute_limits()

    def _get_shutoff_tolerance(self) -> float:
        """
        Determines the shutoff head tolerance (plus side) from the rated
        differential head of the design point.

        Returns
        -------
        float
            The tolerance value for the shutoff head.
        """
        return self._shutoff_band()[1]

    def _head_band(self) -> tuple:
        """``(minus, plus)`` head tolerance: criteria band or user override."""
        rated = self.design_point.differential_head
        return _band(
            getattr(self, "tolerances", {}).get("head"),
            self.criteria.head_tolerance(rated),
        )

    def _shutoff_band(self) -> tuple:
        """``(minus, plus)`` shut-off tolerance: criteria band or user override."""
        criteria = getattr(self, "criteria", None)
        if criteria is None:
            criteria = AcceptanceCriteria.default()
        rated = self.design_point.differential_head
        return _band(
            getattr(self, "tolerances", {}).get("shutoff"),
            criteria.shutoff_tolerance(rated),
        )

    def _compute_limits(self) -> None:
        """
        Computes the acceptable limits for head, shutoff head, and breaking power.
        Limits without input data are ``None``.
        """
        rated = self.design_point.differential_head
        head_minus, head_plus = self._head_band()
        self.minimum_head = round(rated - head_minus * rated, 2)
        self.maximum_head = round(rated + head_plus * rated, 2)

        self.minimum_head_shutoff = None
        self.maximum_head_shutoff = None
        self.maximum_breaking_power = None

        head_shutoff = getattr(self.design_point, "head_shutoff", None)
        if head_shutoff is not None:
            so_minus, so_plus = self._shutoff_band()
            self.maximum_head_shutoff = round(head_shutoff + so_plus * head_shutoff, 2)
            self.minimum_head_shutoff = round(head_shutoff - so_minus * head_shutoff, 2)

        breaking_power = getattr(self.design_point, "breaking_power", None)
        if breaking_power is not None:
            self.maximum_breaking_power = round(
                breaking_power + self.breaking_power_tolerance * breaking_power, 2
            )

    @property
    def shutoff_extrapolated(self) -> bool:
        """
        True when no curve point lies below ``shutoff_extrapolation_q_fraction``
        of the rated capacity, i.e. the shut-off head is extrapolated.
        """
        threshold: Q_ = (
            self.criteria.shutoff_extrapolation_q_fraction * self.design_point.capacity
        )
        return not any(point.capacity < threshold for point in self.curve)

    def verdict(self, parallel_operation: bool = False, test_speeds: tuple = ()):
        """The :class:`pump.acceptance.PerformanceVerdict` of this design point.

        The same engine as the workbench's Compliance node
        (:func:`pump.acceptance.evaluate_performance`).
        """
        dp = self.design_point
        return evaluate_performance(
            self.curve,
            dp.capacity,
            dp.differential_head,
            self.criteria,
            rated_power=getattr(dp, "breaking_power", None),
            rated_efficiency=getattr(dp, "efficiency", None),
            rated_shutoff=getattr(dp, "head_shutoff", None),
            parallel_operation=parallel_operation,
            rated_speed=getattr(dp, "speed_of_rotation", None),
            test_speeds=test_speeds,
            tolerances=self.tolerances or None,
        )

    def parallel_operation_ok(self) -> Optional[bool]:
        """
        Parallel-operation rule: shut-off head / rated differential head
        >= ``parallel_shutoff_min_ratio`` and a continuously rising curve.
        ``None`` when it cannot be evaluated (reported as "not evaluated" by
        :meth:`verdict`, never as a pass).
        """
        return self.verdict(parallel_operation=True).parallel_ok

    @property
    def acceptable_limits(self) -> Dict[str, float]:
        limits = {
            "Head (min)": self.minimum_head,
            "Head (max)": self.maximum_head,
            "Shutoff Head (min)": self.minimum_head_shutoff,
            "Shutoff Head (max)": self.maximum_head_shutoff,
            "Breaking Power (max)": self.maximum_breaking_power
        }
        return {k: v for k, v in limits.items() if v is not None}

    @property
    def test_summary(self) -> str:
        return self.curve.test_summary
    
    @property
    def check_summary(self) -> str:
        """
        Table of the rated-point checks (not of every raw test point), from
        :meth:`verdict`: Head, Power, Efficiency (``info`` unless a tolerance
        exists) and Shutoff Head (flagged when extrapolated).  A check that
        cannot be computed shows ``not evaluated``; it is never dropped.
        """
        verdict = self.verdict()
        rows = []
        extrapolated = False
        for r in verdict.rows:
            name = {"Power": "Breaking Power"}.get(r.name, r.name)  # library label
            if r.name == "Shutoff Head" and r.extrapolated:
                name, extrapolated = "Shutoff Head (extrapolated)", True
            if r.status == "info":
                name += " (info)"
            ok = {"pass": True, "fail": False}.get(r.status, r.status)
            rows.append([
                name,
                _fmt_value(r.predicted) if r.predicted is not None else "-",
                _fmt_value(r.minimum) if r.minimum is not None else "-",
                _fmt_value(r.maximum) if r.maximum is not None else "-",
                ok,
            ])

        headers = ["Parameter", "Predicted", "Min", "Max", "OK"]
        text = tabulate(rows, headers=headers, tablefmt="grid")
        if extrapolated:
            fraction = self.criteria.shutoff_extrapolation_q_fraction
            text += (
                "\nNote: shutoff head is extrapolated (no test point below "
                f"{fraction:.0%} of rated capacity)."
            )
        if verdict.not_evaluated:
            text += "\nNot evaluated: " + ", ".join(verdict.not_evaluated) + "."
        return text

    @property
    def test_summary_with_limits(self) -> str:
        """
        Generates a summary table checking if performance values are within limits.
        
        Returns
        -------
        str
            A formatted table summarizing the check results.
        """
        # A point counts as shut-off below the extrapolation threshold
        # (a fraction of the rated flow), whatever the capacity unit.
        shutoff_q: Q_ = (
            self.criteria.shutoff_extrapolation_q_fraction * self.design_point.capacity
        )
        results = []
        for point in self.curve:                
            results.append([
                f"{point.capacity:0.02f~P}", 
                f"{point.head:0.02f~P}",
                f"{self.minimum_head:0.02f~P}", f"{self.maximum_head:0.02f~P}",
                f"{point.head:0.02f~P}" if point.capacity < shutoff_q else "N/A",
                f"{self.minimum_head_shutoff:0.02f~P}" if self.minimum_head_shutoff is not None else "N/A",
                f"{self.maximum_head_shutoff:0.02f~P}" if self.maximum_head_shutoff is not None else "N/A",
                f"{getattr(point, "breaking_power", 0):0.02f~P}" if hasattr(point, "breaking_power") else "N/A",
                f"{self.maximum_breaking_power:0.02f~P}" if self.maximum_breaking_power is not None else "N/A"
            ])

        headers = [
            "Flow", "Head", "Head Min", "Head Max", 
            "Shutoff Head", "Shutoff Min", "Shutoff Max",
            "Breaking Power", "Max B. Power"
        ]
        
        
        return tabulate(results, headers=headers, tablefmt="grid")
    

    @property
    def report_summary(self) -> Dict[str, Any]:
        """
        Generates a report summarizing predicted performance values.
        
        Returns
        -------
        dict
            Dictionary containing predicted performance parameters.
        """
        rated_capacity = self.design_point.capacity
        return {
            "Head": [self.curve.predict_head(rated_capacity),
                     self.minimum_head,
                     self.maximum_head],
            "Breaking Power": [self.curve.predict_breaking_power(rated_capacity),
                               "-",
                               self.maximum_breaking_power if self.maximum_breaking_power is not None else "-"],
            "Efficiency": self.curve.predict_efficiency(rated_capacity),
            "Rated Capacity": self.design_point.capacity
        }
