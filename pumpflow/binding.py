"""
binding
=======

The single place where the UI calls **into** the ``pump`` library (UI_SPEC §4).
Nothing here re-implements physics the library already provides; it only adapts
the signal payloads (:mod:`pumpflow.signals`, which carry Pint quantities) to the
library's constructors and reads results back out.

Binding table (UI_SPEC §4)
--------------------------
======================================  ====================================================
UI concept                              Library entry point
======================================  ====================================================
Rated fluid / test water                ``pump.Fluid(name, density=, viscosity=)``
Rated / design point                    ``pump.DesignPoint(fluid, capacity=, differential_head=, ...)``
Measured / corrected point              ``pump.TestPoint(fluid, capacity=, speed_of_rotation=, _head=, ...)``
Collection of points                    ``pump.PerformanceCurve(fluid, points, polynomial_degree=3)``
Affinity-law speed correction           ``PerformanceCurve.to_speed(Q_(N, "rpm"))``
Density correction                      ``PerformanceCurve.to_fluid(rated_fluid)``
Viscosity correction (HI 9.6.7)         ``PerformanceCurve.to_viscous(rated_fluid)``
Polynomial fit + predictions            ``PerformanceCurve.fitter.*_coeffs`` / ``predict_*``
Built-in matplotlib curve               ``PerformanceCurve.plot_performance_curve(...)``
Tolerances & verdict tables             ``pump.PerformanceChecker(design_point, curve, criteria=)``
Acceptance criteria (edition / client)  ``pump.acceptance.AcceptanceCriteria.load(key, client)``
Mechanical run verdict + trend plot     ``pump.mechanical_run.MechanicalRunChecker`` / ``plot_mechanical_run``
NPSHa / NPSHr curve / margin verdict    ``pump.npsh.npsh_available`` / ``NPSHrCurve`` / ``check_npsh`` / ``plot_npsh``
Units everywhere                        ``pump.Q_`` + ``quantity_factory`` (STANDARD_UNITS)
======================================  ====================================================
"""

from __future__ import annotations

from statistics import fmean
from typing import Optional

import numpy as np

# --- pump library imports (the library is the source of truth) --------------
from pump import (
    Q_,
    Pressure,
    Fluid,
    Water,
    DesignPoint,
    TestPoint,
    PerformanceCurve,
    PerformanceChecker,
    compare_curves,
    plot_comparison,
)
from pump.acceptance import AcceptanceCriteria
from pump.acceptance import deviation as acceptance_deviation
from pump.constants import G

from .mathx import NaturalCubicSpline, r_squared
from .numfmt import parse_decimal
from .settings_codec import parse_standard_text
from .signals import (
    RatedPoint,
    FluidSpec,
    FluidSpec,
    BenchGeometry,
    TestPointSet,
    CorrectedCurve,
    FittedModel,
    ComplianceResult,
    ParameterCheck,
    MechanicalRunSet,
    MechanicalRunResultSignal,
    NPSHSet,
    NPSHResultSignal,
)


class BindingError(Exception):
    """Human-readable wrapper around library/validation failures (UI_SPEC §7)."""


# ---------------------------------------------------------------------------
# Fluids & design point
# ---------------------------------------------------------------------------


def make_rated_fluid(rated: RatedPoint) -> Fluid:
    """Construct the rated ``Fluid`` from the rated point."""
    return Fluid(
        name=rated.fluid_name or "Rated fluid",
        density=rated.density,
        viscosity=rated.viscosity,
    )


def water_density_kgm3(temp_c: float) -> float:
    """Density of water at ``temp_c`` (°C) via ``pump.Water`` — kg/m³ (UC-00)."""
    return float(Water(Q_(temp_c, "degC")).density.magnitude)


def water_dynamic_viscosity_cP(temp_c: float) -> float:
    """Dynamic viscosity of liquid water at ``temp_c`` (°C) — cP.

    Delegates to ``pump.Water.dynamic_viscosity`` (Andrade-style exponential
    fit published by Kestin et al.).
    """
    return float(Water(Q_(temp_c, "degC")).dynamic_viscosity.to("cP").magnitude)


def water_kinematic_viscosity_cst(temp_c: float) -> float:
    """Kinematic viscosity of liquid water at ``temp_c`` (°C) — cSt.

    Delegates to ``pump.Water.kinematic_viscosity``.
    """
    return float(Water(Q_(temp_c, "degC")).kinematic_viscosity.to("cSt").magnitude)


def make_fluid(spec: FluidSpec) -> Fluid:
    """Construct a ``pump.Fluid`` (or ``Water``) from a Fluid-node spec (UC-00)."""
    if spec.source == "water" and spec.temperature is not None:
        return Water(spec.temperature)
    return Fluid(
        name=spec.name or "Service fluid",
        density=spec.density,
        viscosity=spec.viscosity,
    )


def make_design_point(rated: RatedPoint, fluid: Optional[Fluid] = None) -> DesignPoint:
    """Construct the shared ``DesignPoint`` (UI_SPEC §4)."""
    fluid = fluid or make_rated_fluid(rated)
    kwargs = {}
    if rated.head_shutoff is not None:
        kwargs["head_shutoff"] = rated.head_shutoff
    if rated.npsha is not None:
        kwargs["npsha"] = rated.npsha
    if rated.power is not None:
        kwargs["breaking_power"] = rated.power
    return DesignPoint(
        fluid=fluid,
        capacity=rated.q,
        differential_head=rated.head,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Test rows → head/efficiency at the measured condition
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Speed / affinity + density correction  (UI_SPEC §5.3)
# ---------------------------------------------------------------------------


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


def _has_eff(point) -> bool:
    try:
        _ = point.efficiency
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Curve fit  (UI_SPEC §5.4)
# ---------------------------------------------------------------------------


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
    )


# ---------------------------------------------------------------------------
# Acceptance criteria  (sprint 5)
# ---------------------------------------------------------------------------


def criteria_for(rated: RatedPoint) -> AcceptanceCriteria:
    """The ``AcceptanceCriteria`` selected by the rated point.

    Falls back to the library default when the stored key / client is unknown
    (e.g. a project saved by a newer version).
    """
    key = getattr(rated, "standard_key", None) or "api610:12"
    client = getattr(rated, "client", None) or None
    try:
        return AcceptanceCriteria.load(key, client)
    except KeyError:
        return AcceptanceCriteria.default()


def criteria_label(criteria: AcceptanceCriteria) -> str:
    """Display label: edition label, plus `` + <client label>`` for an overlay."""
    label = criteria.label
    if criteria.client_label:
        label += " + " + criteria.client_label
    return label


def standard_label(key: str, client: Optional[str] = None) -> str:
    """Display label for an edition key (+ optional client overlay)."""
    try:
        return criteria_label(AcceptanceCriteria.load(key, client or None))
    except KeyError:
        return key


def available_standards() -> list:
    """``[(key, label)]`` of the editions the library offers."""
    return list(AcceptanceCriteria.available())


def available_clients() -> list:
    """``[(client, label)]`` of the client overlays the library offers."""
    return list(AcceptanceCriteria.clients())


# ---------------------------------------------------------------------------
# API 610 compliance  (UI_SPEC §5.6)
# ---------------------------------------------------------------------------


def default_tolerances(rated: RatedPoint) -> dict:
    """Criteria-default tolerances exposed as editable fields (UI_SPEC §5.6).

    Both the head and the shut-off band are keyed by the **rated** differential
    head (the same rule as the library checker).
    """
    criteria = criteria_for(rated)
    _, head_plus = criteria.head_tolerance(rated.head)
    _, shutoff_plus = criteria.shutoff_tolerance(rated.head)
    return {
        "head": head_plus,
        "shutoff": shutoff_plus,
        "power": criteria.power_tol_plus,
        "efficiency": criteria.efficiency_tol_minus,
    }


def _band(tol: float, default_plus: float, band: tuple) -> tuple:
    """``(minus, plus)``: the criteria band, unless the user overrode the value."""
    if abs(tol - default_plus) <= 1e-9:
        return band
    return (tol, tol)


def _limit(value: float) -> float:
    """Acceptance limits are rounded to 2 decimals, exactly as
    ``PerformanceChecker._compute_limits`` does, so the GUI table and the
    library/report limits are the same numbers."""
    return round(value, 2)


def check_compliance(
    fitted: FittedModel,
    rated: RatedPoint,
    tolerances: Optional[dict] = None,
) -> ComplianceResult:
    """
    Evaluate API 610 deviations & verdict.

    Numbers come straight from ``PerformanceChecker(design_point, curve,
    criteria=)`` and the curve's ``predict_*`` polynomials so they match
    ``report_summary`` / ``test_summary_with_limits`` for the same inputs
    (UI_SPEC §9.4).  Every deviation is ``acceptance.deviation(rated,
    predicted) = (predicted − rated) / rated``.
    """
    criteria = criteria_for(rated)
    design_point = make_design_point(rated, fitted.curve.fluid)
    checker = PerformanceChecker(design_point, fitted.curve, criteria=criteria)

    lib_defaults = default_tolerances(rated)
    tol = dict(lib_defaults)
    if tolerances:
        tol.update(tolerances)
    overridden = any(
        abs(tol[k] - lib_defaults[k]) > 1e-9 for k in lib_defaults if k in tol
    )
    verified = bool(criteria.verified)

    rated_q = rated.q
    rated_head = float(rated.head.to("m").magnitude)
    rated_power = float(rated.power.to("kW").magnitude)
    head_band = _band(
        tol["head"], lib_defaults["head"], criteria.head_tolerance(rated.head)
    )
    shutoff_band = _band(
        tol["shutoff"], lib_defaults["shutoff"], criteria.shutoff_tolerance(rated.head)
    )
    params = []

    # --- Head:  min ≤ predicted ≤ max ------------------------------------------
    pred_head = float(fitted.curve.predict_head(rated_q).to("m").magnitude)
    dev_head = acceptance_deviation(rated_head, pred_head)
    params.append(
        ParameterCheck(
            name="Head",
            actual=rated_head,
            predicted=pred_head,
            minimum=_limit(rated_head * (1.0 - head_band[0])),
            maximum=_limit(rated_head * (1.0 + head_band[1])),
            deviation=dev_head,
            tolerance=tol["head"],
            passed=-head_band[0] - 1e-9 <= dev_head <= head_band[1] + 1e-9,
            verified=verified,
        )
    )

    # --- Power:  δ ≤ tol ------------------------------------------------------
    pred_power = float(fitted.curve.predict_breaking_power(rated_q).to("kW").magnitude)
    dev_power = acceptance_deviation(rated_power, pred_power)
    params.append(
        ParameterCheck(
            name="Power",
            actual=rated_power,
            predicted=pred_power,
            minimum=None,
            maximum=_limit(rated_power * (1.0 + tol["power"])),
            deviation=dev_power,
            tolerance=tol["power"],
            passed=dev_power <= tol["power"] + 1e-9,
            verified=verified,
        )
    )

    # --- Efficiency:  δ ≥ −tol -----------------------------------------------
    if rated.efficiency is not None:
        rated_eff = float(rated.efficiency.to("percent").magnitude)
        pred_eff = float(
            fitted.curve.predict_efficiency(rated_q).to("percent").magnitude
        )
        dev_eff = acceptance_deviation(rated_eff, pred_eff)
        params.append(
            ParameterCheck(
                name="Efficiency",
                actual=rated_eff,
                predicted=pred_eff,
                minimum=None,
                maximum=None,
                deviation=dev_eff,
                tolerance=tol["efficiency"],
                passed=dev_eff >= -tol["efficiency"] - 1e-9,
                verified=verified,
            )
        )

    # --- Shutoff Head:  |δ| ≤ tol --------------------------------------------
    if rated.head_shutoff is not None:
        rated_so = float(rated.head_shutoff.to("m").magnitude)
        pred_so = float(fitted.curve.predict_head(Q_(0, "m**3/h")).to("m").magnitude)
        dev_so = acceptance_deviation(rated_so, pred_so)
        params.append(
            ParameterCheck(
                name="Shutoff Head",
                actual=rated_so,
                predicted=pred_so,
                minimum=_limit(rated_so * (1.0 - shutoff_band[0])),
                maximum=_limit(rated_so * (1.0 + shutoff_band[1])),
                deviation=dev_so,
                tolerance=tol["shutoff"],
                passed=-shutoff_band[0] - 1e-9 <= dev_so <= shutoff_band[1] + 1e-9,
                extrapolated=bool(checker.shutoff_extrapolated),
                verified=verified,
            )
        )

    # --- Parallel operation (only when the rated point asks for it) ----------
    parallel_ok = checker.parallel_operation_ok() if rated.parallel_operation else None

    overall = all(p.passed for p in params) and parallel_ok is not False
    return ComplianceResult(
        pump_tag=fitted.pump_tag,
        parameters=tuple(params),
        overall_pass=overall,
        tolerances=tol,
        overridden=overridden,
        criteria_label=criteria_label(criteria),
        unverified=tuple(criteria.unverified),
        parallel_ok=parallel_ok,
    )


def _mag(q) -> Optional[float]:
    if q is None:
        return None
    try:
        return float(q.magnitude)
    except AttributeError:
        return float(q)


# ---------------------------------------------------------------------------
# Mechanical run  (sprint 6 / UC-11)
# ---------------------------------------------------------------------------


def check_mechanical_run(
    run_set: MechanicalRunSet,
    rated: Optional[RatedPoint] = None,
    overrides: Optional[dict] = None,
) -> MechanicalRunResultSignal:
    """Check a mechanical-run log against the acceptance criteria.

    The criteria come from ``criteria_for(rated).mechanical_run`` when a rated
    point is wired, else from the library default.  ``overrides`` (user-entered
    limits, all Quantities) are merged on top::

        {"min_duration": Q_, "role_max": {role: Q_},
         "stabilisation": {role: (delta Q_, window Q_)}}

    (a ``{"delta": Q_, "window": Q_}`` dict is accepted instead of the tuple).
    Any override marks the criteria as unverified.
    """
    from pump.mechanical_run import (
        MechanicalRunChecker,
        MechanicalRunCriteria,
        plot_mechanical_run,
    )

    full = criteria_for(rated) if rated is not None else AcceptanceCriteria.default()
    base = full.mechanical_run
    label = criteria_label(full)
    ov = overrides or {}

    min_duration = ov.get("min_duration")
    if min_duration is None:
        min_duration = base.min_duration
    role_max = dict(base.role_max or {})
    role_max.update(ov.get("role_max") or {})
    stabilisation = dict(base.stabilisation or {})
    for role, spec in (ov.get("stabilisation") or {}).items():
        if isinstance(spec, dict):
            spec = (spec["delta"], spec["window"])
        stabilisation[role] = (spec[0], spec[1])

    overridden = bool(
        ov.get("min_duration") is not None
        or ov.get("role_max")
        or ov.get("stabilisation")
    )
    source = getattr(base, "source", "") or ""
    if overridden:
        source = (source + " | " if source else "") + "user overrides in the node"
    criteria = MechanicalRunCriteria(
        min_duration=min_duration,
        role_max=role_max,
        stabilisation=stabilisation,
        source=source,
        verified=False if overridden else bool(getattr(base, "verified", False)),
    )
    result = MechanicalRunChecker(run_set.log, criteria).check()
    return MechanicalRunResultSignal(
        pump_tag=run_set.pump_tag,
        result=result,
        criteria_label=label,
        plot_png=plot_mechanical_run(run_set.log, criteria),
    )


# ---------------------------------------------------------------------------
# NPSH margin  (sprint 8 / UC-05)
# ---------------------------------------------------------------------------


def npsha_from_suction(
    p_suction: Pressure,
    temperature: Q_,
    q: Q_,
    suction_id: Optional[Q_] = None,
    z_suction: Optional[Q_] = None,
) -> Q_:
    """NPSHa (metres) of water at ``temperature`` from the suction conditions.

    Thin adapter over ``pump.npsh.npsh_available`` (water density and vapour
    pressure come from ``pump.Water``).  ``suction_id`` adds the velocity head
    (omit for none); ``z_suction`` is the suction gauge elevation (default 0 m).
    """
    from pump.npsh import npsh_available

    return npsh_available(
        p_suction,
        Water(temperature),
        q,
        suction_id=suction_id,
        z_suction=z_suction if z_suction is not None else Q_(0.0, "m"),
    )


def check_npsh_set(
    npsh_set: NPSHSet,
    rated: Optional[RatedPoint] = None,
    overrides: Optional[dict] = None,
) -> NPSHResultSignal:
    """Judge a pump's NPSH margin: NPSHa against the NPSHr curve at rated Q.

    The criteria come from ``criteria_for(rated).npsh`` when a rated point is
    wired, else from the library default (seeded as *not configured*, so the
    verdict is ``info``).  ``overrides`` (user-entered) are merged on top::

        {"min_ratio": float | None, "min_margin": Q_ | None}

    Any override marks the criteria as unverified.  NPSHa is the set's own
    value, else ``rated.npsha`` (when positive); NPSHr is the fitted curve at
    ``rated.q`` (or the largest data capacity without a rated point).
    """
    from pump.npsh import NPSHCriteria, NPSHrCurve, check_npsh, plot_npsh

    pts = [(q, n) for q, n in npsh_set.points if q is not None and n is not None]
    if len(pts) < 2:
        raise BindingError("At least 2 NPSHr points (Q, NPSHr) are required.")
    pts.sort(key=lambda p: float(p[0].to("m**3/h").magnitude))
    curve = NPSHrCurve(
        q=tuple(p[0] for p in pts),
        npshr=tuple(p[1] for p in pts),
        degree=int(npsh_set.degree),
    )
    q_eval = rated.q if rated is not None else curve.q[-1]
    npshr = curve.at_rated(q_eval)

    npsha = npsh_set.npsha
    if npsha is None or not float(npsha.to("m").magnitude) > 0:
        rated_npsha = getattr(rated, "npsha", None) if rated is not None else None
        if rated_npsha is not None and float(rated_npsha.to("m").magnitude) > 0:
            npsha = rated_npsha
        else:
            raise BindingError(
                "NPSHa is not set (enter it, use the calculator, or set it on "
                "the rated point)."
            )

    full = criteria_for(rated) if rated is not None else AcceptanceCriteria.default()
    base = getattr(full, "npsh", None) or NPSHCriteria()
    label = criteria_label(full)
    ov = overrides or {}

    min_ratio = ov.get("min_ratio")
    if min_ratio is None:
        min_ratio = base.min_ratio
    min_margin = ov.get("min_margin")
    if min_margin is None:
        min_margin = base.min_margin
    overridden = ov.get("min_ratio") is not None or ov.get("min_margin") is not None
    source = getattr(base, "source", "") or ""
    if overridden:
        source = (source + " | " if source else "") + "user overrides in the node"
    criteria = NPSHCriteria(
        min_ratio=min_ratio,
        min_margin=min_margin,
        source=source,
        verified=False if overridden else bool(getattr(base, "verified", False)),
    )
    result = check_npsh(npsha, npshr, criteria)
    try:
        plot = plot_npsh(curve, npsha, rated.q if rated is not None else None)
    except Exception:
        plot = None
    return NPSHResultSignal(
        pump_tag=npsh_set.pump_tag,
        result=result,
        curve=curve,
        plot_png=plot,
        criteria_label=label,
    )


# ---------------------------------------------------------------------------
# Report image  (UI_SPEC §5.5 / §5.7)
# ---------------------------------------------------------------------------


def build_report_png(
    corrected: CorrectedCurve, rated: RatedPoint, ylims: Optional[dict] = None
):
    """Reuse the library's matplotlib plot for the report image (BytesIO PNG)."""
    ylims = ylims or {}
    return corrected.curve.plot_performance_curve(
        capacity=rated.q,
        return_io=True,
        head_ylim=ylims.get("head"),
        power_ylim=ylims.get("power"),
        efficiency_ylim=ylims.get("efficiency"),
    )


# ---------------------------------------------------------------------------
# Report assembly  (UI_SPEC §5.7)
# ---------------------------------------------------------------------------


def report_summary_for(fitted: FittedModel, rated: RatedPoint) -> dict:
    """``PerformanceChecker.report_summary`` for one branch (Check's numbers)."""
    design_point = make_design_point(rated, fitted.curve.fluid)
    return PerformanceChecker(
        design_point, fitted.curve, criteria=criteria_for(rated)
    ).report_summary


def comparison_for(bundles, rated: RatedPoint) -> Optional[dict]:
    """
    Twin-pump comparison (UC-08) of the branches that carry a fitted curve.

    Returns ``None`` when fewer than two bundles have a ``fitted`` model (or the
    curves cannot be compared, e.g. no efficiency data); otherwise
    ``{"table": ComparisonTable, "plot": BytesIO, "at": [rated.q]}``.  The first
    fitted bundle is the reference.  Deterministic: evaluated at the rated
    capacity only.
    """
    fitted = [b for b in bundles if getattr(b, "fitted", None) is not None]
    if len(fitted) < 2:
        return None
    curves = {b.pump_tag: b.fitted.curve for b in fitted}
    if len(curves) < 2:
        return None
    at = [rated.q]
    try:
        table = compare_curves(curves, at)
        plot = plot_comparison(curves, rated_q=rated.q)
    except Exception:
        return None
    return {"table": table, "plot": plot, "at": at}


def assemble_report_data(
    rated: RatedPoint, bundles, equipment: Optional[dict] = None
) -> dict:
    """
    Build the ``report_data`` dict exactly as ``ReportGenerator.generate_report``
    expects (UI_SPEC §5.7): one shared design point + one keyed ``test_data``
    entry per pump TAG, plus a top-level ``"acceptance"`` entry
    (``{"label", "verified", "unverified"}``) describing the criteria used.

    A branch whose test set carried bench geometry adds a
    ``"Test bench geometry (<pump_tag>)"`` line to the equipment description.

    A branch whose corrected curve carries an HI 9.6.7 viscosity correction with
    ``B > 1`` adds a ``"viscous"`` entry (``{"B", "C_Q", "C_H", "C_eta"}``) to its
    fitted data.

    A branch with a mechanical-run result adds a ``"Mechanical Run"`` entry
    (``{"result", "plot"}``) under its tag.  A tag with *only* a mechanical run
    (no fitted curve) still gets an entry, which then lacks ``test_summary`` /
    ``test_data``.

    A branch with an NPSH result adds an ``"NPSH"`` entry
    (``{"result", "plot", "table"}``, ``table`` = ``[(Q, NPSHr), ...]`` of
    Quantities) under its tag; a tag with *only* NPSH is handled the same way.

    With two or more fitted branches a top-level ``"comparison"`` entry
    (``{"table", "plot", "at"}``, see :func:`comparison_for`) is added.
    """
    equipment = equipment or {}
    design_point = make_design_point(rated)
    criteria = criteria_for(rated)

    equipment_description = {"TAG": rated.tag}
    equipment_description.update({k: str(v) for k, v in equipment.items() if v})

    test_data = {}
    for b in bundles:
        geometry = getattr(b.corrected, "geometry", None) if b.corrected else None
        if geometry is not None and not geometry.is_empty:
            equipment_description[f"Test bench geometry ({b.pump_tag})"] = (
                format_geometry(geometry)
            )
        entry = {}
        if b.fitted is not None:
            entry["test_summary"] = report_summary_for(b.fitted, rated)
            entry["test_data"] = b.fitted.curve.test_data
            if b.compliance is not None:
                entry["verdict"] = bool(b.compliance.overall_pass)
            png = b.plot_png
            if png is None and b.corrected is not None:
                png = build_report_png(b.corrected, rated)
            if png is not None:
                entry["Performance Curve"] = png
            viscous = getattr(b.corrected, "viscous", None) if b.corrected else None
            if viscous and viscous.get("B", 0.0) > 1.0:
                entry["viscous"] = dict(viscous)
        mech = getattr(b, "mechanical", None)
        if mech is not None:
            entry["Mechanical Run"] = {"result": mech.result, "plot": mech.plot_png}
        npsh = getattr(b, "npsh", None)
        if npsh is not None:
            curve = npsh.curve
            table = list(zip(curve.q, curve.npshr)) if curve is not None else []
            entry["NPSH"] = {
                "result": npsh.result,
                "plot": npsh.plot_png,
                "table": table,
            }
        if entry:
            test_data[b.pump_tag] = entry

    report_data = {
        "equipment_description": equipment_description,
        "design_point": design_point,
        "test_data": test_data,
        "acceptance": {
            "label": criteria_label(criteria),
            "verified": bool(criteria.verified),
            "unverified": list(criteria.unverified),
        },
    }
    comparison = comparison_for(bundles, rated)
    if comparison is not None:
        report_data["comparison"] = comparison
    return report_data


def generate_docx(
    report_data: dict,
    language: str = "en",
    template_path: Optional[str] = None,
    output_file: Optional[str] = None,
) -> str:
    """Call the library's ``ReportGenerator`` to write the ``.docx`` (UI_SPEC §4)."""
    try:
        from pump import ReportGenerator  # exported at top level if available
    except Exception:
        from pump.utilities.report import ReportGenerator
    gen = ReportGenerator(language=language, template_path=template_path)
    return gen.generate_report(report_data, output_file=output_file)


def generate_tex(
    report_data: dict, language: str = "en", output_file: Optional[str] = None
) -> str:
    """Write the LaTeX source of the report (``.tex`` + ``<stem>_figs/``)."""
    from pump.utilities.report_latex import LatexReportGenerator

    return LatexReportGenerator(language=language).generate_tex(
        report_data, output_file
    )


def generate_pdf(
    report_data: dict, language: str = "en", output_file: Optional[str] = None
) -> str:
    """Compile the LaTeX report to PDF (needs latexmk or pdflatex on PATH)."""
    from pump.utilities.report_latex import LatexReportGenerator

    return LatexReportGenerator(language=language).generate_pdf(
        report_data, output_file
    )


REPORT_FORMATS = ("docx", "tex", "pdf")


def export_reports(
    report_data: dict,
    formats=REPORT_FORMATS,
    language: str = "en",
    template_path: Optional[str] = None,
    out_dir: Optional[str] = None,
    stem: Optional[str] = None,
):
    """Write the report in every requested format.

    Returns ``(paths, errors)``: ``{fmt: path}`` for the formats that succeeded
    and ``{fmt: message}`` for the ones that failed. One failing format (e.g. no
    TeX installed) never prevents the others from being written.
    """
    import io
    from datetime import datetime
    from pathlib import Path

    if stem is None:
        tag = report_data["equipment_description"]["TAG"].replace("/", "")
        from pump.utilities.report import LocalizationHelper

        report_word = LocalizationHelper(language)._("Report")
        stem = f"{report_word}_{tag}_{datetime.now().strftime('%d-%m-%Y')}"
    folder = Path(out_dir or ".")
    folder.mkdir(parents=True, exist_ok=True)

    writers = {
        "docx": lambda out: generate_docx(
            report_data, language=language, template_path=template_path, output_file=out
        ),
        "tex": lambda out: generate_tex(
            report_data, language=language, output_file=out
        ),
        "pdf": lambda out: generate_pdf(
            report_data, language=language, output_file=out
        ),
    }
    paths, errors = {}, {}
    for fmt in formats:
        if fmt not in writers:
            errors[fmt] = f"Unknown report format: {fmt!r}"
            continue
        # Each writer reads the in-memory PNG charts; rewind them so a previous
        # format having consumed the buffer cannot leave the next one empty.
        for entry in report_data.get("test_data", {}).values():
            for value in entry.values():
                if isinstance(value, io.BytesIO):
                    value.seek(0)
                elif isinstance(value, dict):  # e.g. "Mechanical Run": {"plot": ...}
                    for inner in value.values():
                        if isinstance(inner, io.BytesIO):
                            inner.seek(0)
        comparison_plot = (report_data.get("comparison") or {}).get("plot")
        if isinstance(comparison_plot, io.BytesIO):
            comparison_plot.seek(0)
        try:
            paths[fmt] = str(writers[fmt](str(folder / f"{stem}.{fmt}")))
        except Exception as exc:  # collected, reported by the caller
            errors[fmt] = f"{type(exc).__name__}: {exc}"
    return paths, errors
