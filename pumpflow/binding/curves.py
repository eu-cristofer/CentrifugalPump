"""
pumpflow.binding.curves

Test rows, speed/density/viscosity correction, trim and curve fitting.
"""

from __future__ import annotations

from statistics import fmean
from typing import Optional

import numpy as np
from pump import (
    Q_,
    Pressure,
    Fluid,
    Water,
    TestPoint,
    PerformanceCurve,
)
from pump.constants import G

from ..mathx import NaturalCubicSpline, r_squared
from ..signals import (
    RatedPoint,
    BenchGeometry,
    TestPointSet,
    CorrectedCurve,
    FittedModel,
)
from ._common import BindingError, _has_eff, make_rated_fluid


def _geometry_point(row, rho: Q_, geometry: BenchGeometry) -> TestPoint:
    """Temporary ``pump.TestPoint`` carrying the row's ΔP and the bench geometry.

    Only the geometry attributes that are present are passed; the library then
    evaluates ``pressure_head + velocity_head + elevation_head`` (the velocity
    term needs both diameters, the elevation term both elevations).
    ``delta_pressure`` is intentionally in the library's ``delta`` context.
    """
    kwargs = {"delta_pressure": row.p_discharge - row.p_suction}
    if geometry.suction_id is not None:
        kwargs["inlet_diameter"] = geometry.suction_id
    if geometry.discharge_id is not None:
        kwargs["outlet_diameter"] = geometry.discharge_id
    if geometry.suction_elevation is not None:
        kwargs["inlet_elevation"] = geometry.suction_elevation
    if geometry.discharge_elevation is not None:
        kwargs["outlet_elevation"] = geometry.discharge_elevation
    return TestPoint(
        fluid=Fluid(name="row", density=rho),
        capacity=row.q,
        **kwargs,
    )


def row_head(
    row, density: Optional[Q_] = None, geometry: Optional[BenchGeometry] = None
) -> Q_:
    """
    Read-only ``Head`` column for the Test Points grid (UI_SPEC §5.2):
    ``Head = (P_dis − P_suc) / (ρ·g)`` in metres.  ``ρ`` is water at ``T_water``
    by default, or ``density`` when a Fluid node overrides the test fluid
    (UC-00).  An explicit measured/overridden head on the row wins.

    With a non-empty ``geometry`` the velocity and elevation heads are added
    (``pump.TestPoint.compute_head``).  Without geometry the computation is the
    unchanged pressure-only one.
    """
    if row.head is not None:
        return row.head.to("m")
    rho = density if density is not None else Water(row.temperature).density
    if geometry is None or geometry.is_empty:
        return ((row.p_discharge - row.p_suction) / (rho * G)).to("m")
    return _geometry_point(row, rho, geometry).compute_head.to("m")


def row_head_components(
    row, density: Optional[Q_] = None, geometry: Optional[BenchGeometry] = None
) -> dict:
    """Head split into its terms, all in metres (tooltips / reports).

    Returns ``{"pressure", "velocity", "elevation", "total"}``.  An explicit row
    head is reported as the pressure term with zero velocity/elevation.
    """
    zero = Q_(0.0, "m")
    if row.head is not None:
        total = row.head.to("m")
        return {"pressure": total, "velocity": zero, "elevation": zero, "total": total}
    rho = density if density is not None else Water(row.temperature).density
    if geometry is None or geometry.is_empty:
        total = ((row.p_discharge - row.p_suction) / (rho * G)).to("m")
        return {"pressure": total, "velocity": zero, "elevation": zero, "total": total}
    tp = _geometry_point(row, rho, geometry)
    return {
        "pressure": tp.pressure_head.to("m"),
        "velocity": tp.velocity_head.to("m"),
        "elevation": tp.elevation_head.to("m"),
        "total": tp.compute_head.to("m"),
    }


def format_geometry(geometry: BenchGeometry) -> str:
    """One-line description of the set geometry parts, in the entered units."""

    def part(name: str, q: Optional[Q_]) -> Optional[str]:
        return None if q is None else f"{name} {q.magnitude:g} {q.units:~P}"

    parts = [
        part("suction ID", geometry.suction_id),
        part("discharge ID", geometry.discharge_id),
        part("z_s", geometry.suction_elevation),
        part("z_d", geometry.discharge_elevation),
    ]
    return " · ".join(p for p in parts if p)


def row_efficiency(row, head: Q_, density: Optional[Q_] = None) -> Optional[Q_]:
    """η = hydraulic / breaking, in percent.  ``ρ`` is water at ``T_water`` by
    default, or ``density`` when a Fluid node overrides the test fluid (UC-00)."""
    if row.efficiency is not None:
        return row.efficiency.to("percent")
    if row.power.magnitude <= 0:
        return None
    rho = density if density is not None else Water(row.temperature).density
    return (rho * row.q * G * head / row.power).to("percent")


def head_from_pressures(p_suction: Pressure, p_discharge: Pressure, density: Q_) -> Q_:
    """Head in metres from a pressure pair and a constant density (Point node)."""
    return ((p_discharge - p_suction) / (density * G)).to("m")


def _has_viscosity(fluid) -> bool:
    """True when ``fluid`` carries a kinematic or dynamic viscosity."""
    return any(
        getattr(fluid, attr, None) is not None
        for attr in ("kinematic_viscosity", "viscosity")
    )


def correct_curve(
    rated: RatedPoint,
    tps: TestPointSet,
    target_speed: Optional[Q_] = None,
    apply_speed: bool = True,
    apply_density: bool = True,
    degree: int = 3,
    target_fluid: Optional[Fluid] = None,
    apply_viscosity: bool = False,
) -> CorrectedCurve:
    """
    Build ``TestPoint``s from the raw rows, wrap them in a ``PerformanceCurve``,
    then correct to rated speed (affinity laws) and rated fluid (density).

    ``target_fluid`` overrides the density-correction target: when a Fluid node
    is wired in, the curve is corrected ``to_fluid`` *that* fluid instead of the
    rated fluid derived from ``rated`` (UC-00).  With it set, ``rated`` may be
    ``None`` (forced speed correction that still applies the density step).

    The order is speed -> density -> viscosity.  With ``apply_viscosity`` (and a
    target fluid carrying a viscosity) the fluid step uses
    ``PerformanceCurve.to_viscous`` (HI 9.6.7) instead of ``to_fluid``; the
    returned ``CorrectedCurve.viscous`` then holds ``{"B", "C_Q", "C_H",
    "C_eta"}`` (factors at the BEP).  For ``B <= 1`` the corrected curve is
    identical to the density-only result.
    """
    ok, msg = tps.is_valid()
    if not ok:
        raise BindingError(msg)

    target = target_speed if target_speed is not None else rated.speed

    # One shared test fluid (the library requires a single fluid per curve).
    # Per-row head/efficiency are computed with the test density and pinned onto
    # the points, so the shared fluid is only a label here.  A connected Fluid
    # node overrides the test density (constant); otherwise water at T_water.
    test_rho = tps.test_density
    if test_rho is not None:
        test_fluid = Fluid(name="Test fluid", density=test_rho)
    else:
        mean_temp = fmean(r.temperature.to("degC").magnitude for r in tps.rows)
        test_fluid = Water(Q_(mean_temp, "degC"))

    points = []
    before_after = []
    for r in tps.rows:
        head = row_head(r, test_rho, tps.geometry)
        eff = row_efficiency(r, head, test_rho)
        kwargs = {
            "_head": head,
            "breaking_power": r.power,
        }
        if eff is not None:
            kwargs["_efficiency"] = eff
        points.append(
            TestPoint(
                fluid=test_fluid,
                capacity=r.q,
                speed_of_rotation=r.speed,
                **kwargs,
            )
        )
        before_after.append(
            {
                "q": float(r.q.to("m**3/h").magnitude),
                "head": float(head.to("m").magnitude),
                "power": float(r.power.to("kW").magnitude),
                "eff": float(eff.to("percent").magnitude) if eff is not None else None,
                "speed": float(r.speed.to("rpm").magnitude),
            }
        )

    try:
        curve = PerformanceCurve(test_fluid, points, polynomial_degree=degree)
    except ValueError as exc:
        raise BindingError(str(exc)) from exc

    # 1) affinity-law speed correction
    if apply_speed:
        try:
            curve = curve.to_speed(target)
        except AttributeError as exc:
            raise BindingError(str(exc)) from exc

    # 2) density / fluid correction to the rated fluid (or an override Fluid node),
    #    3) with the HI 9.6.7 viscosity correction folded into the fluid step
    fluid_used = test_fluid
    viscous = None
    if apply_density:
        rated_fluid = (
            target_fluid if target_fluid is not None else make_rated_fluid(rated)
        )
        if apply_viscosity and _has_viscosity(rated_fluid):
            try:
                curve = curve.to_viscous(rated_fluid)
            except (ValueError, AttributeError) as exc:
                raise BindingError(str(exc)) from exc
            info = getattr(curve, "viscosity_correction", None)
            viscous = dict(info) if info is not None else None
        else:
            curve = curve.to_fluid(rated_fluid)
        fluid_used = rated_fluid

    # after-correction values for the before/after table (capacity-sorted)
    corrected_rows = [
        {
            "q": float(p.capacity.to("m**3/h").magnitude),
            "head": float(p.head.to("m").magnitude),
            "power": (
                float(p.breaking_power.to("kW").magnitude)
                if hasattr(p, "breaking_power")
                else None
            ),
            "eff": float(p.efficiency.to("percent").magnitude) if _has_eff(p) else None,
        }
        for p in curve.points
    ]
    # zip measured (capacity-sorted) with corrected (capacity-sorted)
    before_after_sorted = sorted(before_after, key=lambda d: d["q"])
    merged = tuple(
        {"measured": m, "corrected": c}
        for m, c in zip(before_after_sorted, corrected_rows)
    )

    return CorrectedCurve(
        pump_tag=tps.pump_tag,
        curve=curve,
        fluid=fluid_used,
        target_speed=target,
        before_after=merged,
        geometry=tps.geometry,
        viscous=viscous,
    )


def _trim_row(point) -> dict:
    """Display row (m³/h, m, kW, %) of one curve point."""
    return {
        "q": float(point.capacity.to("m**3/h").magnitude),
        "head": float(point.head.to("m").magnitude),
        "power": (
            float(point.breaking_power.to("kW").magnitude)
            if hasattr(point, "breaking_power")
            else None
        ),
        "eff": (
            float(point.efficiency.to("percent").magnitude) if _has_eff(point) else None
        ),
    }


def trim_curve(
    source,
    d_new: Q_,
    d_ref: Q_,
    max_trim: float = 0.05,
) -> CorrectedCurve:
    """Impeller-trim a corrected curve or fitted model (``PerformanceCurve.to_diameter``).

    ``source`` is a ``CorrectedCurve`` or a ``FittedModel`` (anything with a
    ``curve`` and ``pump_tag``).  Pure diameter affinity (Q ∝ D, H ∝ D²,
    P ∝ D³, η unchanged); the library warns beyond ``max_trim``.  The result is a
    ``CorrectedCurve`` tagged ``"<pump_tag>@D=<d> mm"``.
    """
    base = source.curve
    try:
        trimmed = base.to_diameter(d_new, d_ref, max_trim=max_trim)
    except (ValueError, AttributeError) as exc:
        raise BindingError(str(exc)) from exc

    speed = getattr(source, "target_speed", None)
    if speed is None:
        speed = getattr(base.points[0], "speed_of_rotation", None)
    if speed is None:
        speed = Q_(0.0, "rpm")
    pairs = tuple(
        {"measured": _trim_row(a), "corrected": _trim_row(b)}
        for a, b in zip(base.points, trimmed.points)
    )
    d_mm = float(d_new.to("mm").magnitude)
    return CorrectedCurve(
        pump_tag=f"{source.pump_tag}@D={d_mm:.1f} mm",
        curve=trimmed,
        fluid=getattr(source, "fluid", None) or base.fluid,
        target_speed=speed,
        before_after=pairs,
        geometry=getattr(source, "geometry", None),
        viscous=getattr(source, "viscous", None),
    )


def diameter_for_rated(source, rated: RatedPoint) -> Q_:
    """Diameter at which the curve passes through the rated duty (affinity parabola).

    Thin adapter over ``pump.trim.diameter_for_duty`` using the rated Q, H and the
    rated point's nominal impeller diameter as the reference.
    """
    from pump.trim import diameter_for_duty

    d_ref = getattr(rated, "impeller_diameter", None)
    if d_ref is None:
        raise BindingError("The rated point has no impeller diameter (reference).")
    try:
        return diameter_for_duty(source.curve, rated.q, rated.head, d_ref)
    except ValueError as exc:
        raise BindingError(str(exc)) from exc


def fit_model(
    corrected: CorrectedCurve, degree: int = 3, with_spline: bool = True
) -> FittedModel:
    """Polynomial coeffs (primary) + natural cubic splines (secondary)."""
    base = corrected.curve
    curve = PerformanceCurve(base.fluid, list(base.points), polynomial_degree=degree)
    fitter = curve.fitter

    caps = fitter.capacities
    heads = fitter.heads
    try:
        powers = fitter.powers
    except Exception:
        powers = np.array([])
    try:
        effs = fitter.efficiencies
    except Exception:
        effs = np.array([])

    head_coeffs = fitter.head_coeffs
    power_coeffs = fitter.power_coeffs if powers.size else np.array([])
    eff_coeffs = fitter.efficiency_coeffs if effs.size else np.array([])

    head_spline = power_spline = eff_spline = None
    if with_spline and len(caps) >= 2:
        head_spline = NaturalCubicSpline(caps, heads)
        if powers.size:
            power_spline = NaturalCubicSpline(caps, powers)
        if effs.size:
            eff_spline = NaturalCubicSpline(caps, effs)

    r2 = {"head": r_squared(heads, np.polyval(head_coeffs, caps))}
    if powers.size:
        r2["power"] = r_squared(powers, np.polyval(power_coeffs, caps))
    if effs.size:
        r2["efficiency"] = r_squared(effs, np.polyval(eff_coeffs, caps))

    return FittedModel(
        pump_tag=corrected.pump_tag,
        curve=curve,
        degree=degree,
        head_coeffs=head_coeffs,
        power_coeffs=power_coeffs,
        efficiency_coeffs=eff_coeffs,
        head_spline=head_spline,
        power_spline=power_spline,
        efficiency_spline=eff_spline,
        r2=r2,
        # Measured pump speeds (before correction), for the test-speed check.
        test_speeds=tuple(
            Q_(pair["measured"]["speed"], "rpm")
            for pair in (corrected.before_after or ())
            if pair.get("measured", {}).get("speed") is not None
        ),
    )
