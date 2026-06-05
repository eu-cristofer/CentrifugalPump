"""
binding
=======

The single place where the UI calls **into** the ``pump`` library (UI_SPEC §4).
Nothing here re-implements physics the library already provides; it only adapts
the flat signal payloads (:mod:`pumpflow.signals`) to the library's constructors
and reads results back out.

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
Polynomial fit + predictions            ``PerformanceCurve.fitter.*_coeffs`` / ``predict_*``
Built-in matplotlib curve               ``PerformanceCurve.plot_performance_curve(...)``
Tolerances & verdict tables             ``pump.PerformanceChecker(design_point, curve)``
Units everywhere                        ``pump.Q_`` + ``quantity_factory`` (STANDARD_UNITS)
======================================  ====================================================
"""

from __future__ import annotations

import warnings
from statistics import fmean
from typing import Optional

import numpy as np

# --- pump library imports (the library is the source of truth) --------------
from pump import Q_, Fluid, DesignPoint, TestPoint, PerformanceCurve, PerformanceChecker

from .mathx import NaturalCubicSpline, r_squared, water_density_kgm3
from .numfmt import parse_decimal
from .signals import (
    RatedPoint,
    TestPointSet,
    CorrectedCurve,
    FittedModel,
    ComplianceResult,
    ParameterCheck,
)

G = 9.81  # m/s²

# Pressure unit → Pascal
_PA_PER = {
    "bar": 1.0e5,
    "kgf/cm**2": 98066.5,
    "kgf/cm2": 98066.5,
    "kgf/cm²": 98066.5,
}


class BindingError(Exception):
    """Human-readable wrapper around library/validation failures (UI_SPEC §7)."""


# ---------------------------------------------------------------------------
# Fluids & design point
# ---------------------------------------------------------------------------


def make_rated_fluid(rated: RatedPoint) -> Fluid:
    """Construct the rated ``Fluid`` from the rated point."""
    with warnings.catch_warnings():
        # nominal viscosity in cSt (kinematic) has no STANDARD_UNITS match — the
        # library warns and keeps it unchanged; that's expected and harmless.
        warnings.simplefilter("ignore")
        return Fluid(
            name=rated.fluid_name or "Rated fluid",
            density=Q_(rated.density_kgm3, "kg/m**3"),
            viscosity=Q_(rated.viscosity_cst, "cSt"),
        )


def make_design_point(rated: RatedPoint, fluid: Optional[Fluid] = None) -> DesignPoint:
    """Construct the shared ``DesignPoint`` (UI_SPEC §4)."""
    fluid = fluid or make_rated_fluid(rated)
    kwargs = {}
    if rated.head_shutoff_m is not None:
        kwargs["head_shutoff"] = Q_(rated.head_shutoff_m, "m")
    if rated.power_kw is not None:
        kwargs["breaking_power"] = Q_(rated.power_kw, "kW")
    return DesignPoint(
        fluid=fluid,
        capacity=Q_(rated.q_m3h, "m**3/h"),
        differential_head=Q_(rated.head_m, "m"),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Test rows → head/efficiency at the measured condition
# ---------------------------------------------------------------------------


def pressure_to_pa(value: float, unit: str) -> float:
    return float(value) * _PA_PER.get(unit, 1.0e5)


def row_head_m(row, pressure_unit: str) -> float:
    """
    Read-only ``Head`` column for the Test Points grid (UI_SPEC §5.2):
    ``Head = (P_dis − P_suc) / (ρ·g)`` using water density at ``T_water``.
    An explicit measured/overridden head on the row wins.
    """
    if row.head_m is not None:
        return float(row.head_m)
    rho = water_density_kgm3(row.temp_c)
    dp_pa = pressure_to_pa(row.p_discharge, pressure_unit) - pressure_to_pa(
        row.p_suction, pressure_unit
    )
    return dp_pa / (rho * G)


def row_efficiency_pct(row, head_m: float) -> Optional[float]:
    """η = hydraulic / breaking, using water density at the row temperature."""
    if row.efficiency_pct is not None:
        return float(row.efficiency_pct)
    if not row.power_kw:
        return None
    rho = water_density_kgm3(row.temp_c)
    q_m3s = row.q_m3h / 3600.0
    hydraulic_w = rho * q_m3s * G * head_m
    breaking_w = row.power_kw * 1000.0
    if breaking_w <= 0:
        return None
    return hydraulic_w / breaking_w * 100.0


# ---------------------------------------------------------------------------
# Speed / affinity + density correction  (UI_SPEC §5.3)
# ---------------------------------------------------------------------------


def correct_curve(
    rated: RatedPoint,
    tps: TestPointSet,
    target_speed_rpm: Optional[float] = None,
    apply_speed: bool = True,
    apply_density: bool = True,
    degree: int = 3,
) -> CorrectedCurve:
    """
    Build ``TestPoint``s from the raw rows, wrap them in a ``PerformanceCurve``,
    then correct to rated speed (affinity laws) and rated fluid (density).
    """
    ok, msg = tps.is_valid()
    if not ok:
        raise BindingError(msg)

    target = float(target_speed_rpm if target_speed_rpm is not None else rated.speed_rpm)

    # One shared test-water fluid (the library requires a single fluid per curve).
    # Per-row head/efficiency are computed with each row's own water density and
    # pinned onto the points, so the shared density is only a label here.
    mean_temp = fmean(r.temp_c for r in tps.rows)
    test_fluid = Fluid(
        name="Test water",
        density=Q_(water_density_kgm3(mean_temp), "kg/m**3"),
    )

    points = []
    before_after = []
    for r in tps.rows:
        head = row_head_m(r, tps.pressure_unit)
        eff = row_efficiency_pct(r, head)
        kwargs = {
            "_head": Q_(head, "m"),
            "breaking_power": Q_(r.power_kw, "kW"),
        }
        if eff is not None:
            kwargs["_efficiency"] = Q_(eff, "percent")
        points.append(
            TestPoint(
                fluid=test_fluid,
                capacity=Q_(r.q_m3h, "m**3/h"),
                speed_of_rotation=Q_(r.speed_rpm, "rpm"),
                **kwargs,
            )
        )
        before_after.append(
            {
                "q": r.q_m3h, "head": head, "power": r.power_kw,
                "eff": eff, "speed": r.speed_rpm,
            }
        )

    try:
        curve = PerformanceCurve(test_fluid, points, polynomial_degree=degree)
    except ValueError as exc:
        raise BindingError(str(exc)) from exc

    # 1) affinity-law speed correction
    if apply_speed:
        try:
            curve = curve.to_speed(Q_(target, "rpm"))
        except AttributeError as exc:
            raise BindingError(str(exc)) from exc

    # 2) density / fluid correction to the rated fluid
    fluid_used = test_fluid
    if apply_density:
        rated_fluid = make_rated_fluid(rated)
        curve = curve.to_fluid(rated_fluid)
        fluid_used = rated_fluid

    # after-correction values for the before/after table (capacity-sorted)
    corrected_rows = [
        {
            "q": float(p.capacity.to("m**3/h").magnitude),
            "head": float(p.head.to("m").magnitude),
            "power": float(p.breaking_power.to("kW").magnitude)
            if hasattr(p, "breaking_power")
            else None,
            "eff": float(p.efficiency.to("percent").magnitude)
            if _has_eff(p)
            else None,
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
        target_speed_rpm=target,
        before_after=merged,
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


def fit_model(corrected: CorrectedCurve, degree: int = 3, with_spline: bool = True) -> FittedModel:
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
# API 610 compliance  (UI_SPEC §5.6)
# ---------------------------------------------------------------------------


def default_tolerances(rated: RatedPoint) -> dict:
    """Library-default tolerances exposed as editable fields (UI_SPEC §5.6)."""
    h = rated.head_shutoff_m if rated.head_shutoff_m is not None else rated.head_m
    if h <= 75:
        shutoff = 0.10
    elif h <= 300:
        shutoff = 0.08
    else:
        shutoff = 0.05
    return {"head": 0.03, "shutoff": shutoff, "power": 0.04, "efficiency": 0.03}


def check_compliance(
    fitted: FittedModel,
    rated: RatedPoint,
    tolerances: Optional[dict] = None,
) -> ComplianceResult:
    """
    Evaluate API 610 deviations & verdict.

    Numbers come straight from ``PerformanceChecker(design_point, curve)`` and the
    curve's ``predict_*`` polynomials so they match ``report_summary`` /
    ``test_summary_with_limits`` for the same inputs (UI_SPEC §9.4).
    """
    design_point = make_design_point(rated, fitted.curve.fluid)
    checker = PerformanceChecker(design_point, fitted.curve)

    lib_defaults = default_tolerances(rated)
    tol = dict(lib_defaults)
    if tolerances:
        tol.update(tolerances)
    overridden = any(
        abs(tol[k] - lib_defaults[k]) > 1e-9 for k in lib_defaults if k in tol
    )

    rated_q = Q_(rated.q_m3h, "m**3/h")
    params = []

    # --- Head:  |δ| ≤ tol -----------------------------------------------------
    pred_head = float(fitted.curve.predict_head(rated_q).to("m").magnitude)
    dev_head = _deviation(rated.head_m, pred_head)
    params.append(
        ParameterCheck(
            name="Head",
            actual=rated.head_m,
            predicted=pred_head,
            minimum=_mag(checker.minimum_head),
            maximum=_mag(checker.maximum_head),
            deviation=dev_head,
            tolerance=tol["head"],
            passed=abs(dev_head) <= tol["head"] + 1e-9,
        )
    )

    # --- Power:  δ ≤ tol ------------------------------------------------------
    pred_power = float(fitted.curve.predict_breaking_power(rated_q).to("kW").magnitude)
    dev_power = _deviation(rated.power_kw, pred_power)
    params.append(
        ParameterCheck(
            name="Power",
            actual=rated.power_kw,
            predicted=pred_power,
            minimum=None,
            maximum=_mag(getattr(checker, "maximum_breaking_power", None)),
            deviation=dev_power,
            tolerance=tol["power"],
            passed=dev_power <= tol["power"] + 1e-9,
        )
    )

    # --- Efficiency:  δ ≥ −tol -----------------------------------------------
    if rated.efficiency_pct is not None:
        pred_eff = float(fitted.curve.predict_efficiency(rated_q).to("percent").magnitude)
        dev_eff = _deviation(rated.efficiency_pct, pred_eff)
        params.append(
            ParameterCheck(
                name="Efficiency",
                actual=rated.efficiency_pct,
                predicted=pred_eff,
                minimum=None,
                maximum=None,
                deviation=dev_eff,
                tolerance=tol["efficiency"],
                passed=dev_eff >= -tol["efficiency"] - 1e-9,
            )
        )

    # --- Shutoff Head:  |δ| ≤ tol --------------------------------------------
    if rated.head_shutoff_m is not None:
        pred_so = float(fitted.curve.predict_head(Q_(0, "m**3/h")).to("m").magnitude)
        dev_so = _deviation(rated.head_shutoff_m, pred_so)
        params.append(
            ParameterCheck(
                name="Shutoff Head",
                actual=rated.head_shutoff_m,
                predicted=pred_so,
                minimum=_mag(getattr(checker, "minimum_head_shutoff", None)),
                maximum=_mag(getattr(checker, "maximum_head_shutoff", None)),
                deviation=dev_so,
                tolerance=tol["shutoff"],
                passed=abs(dev_so) <= tol["shutoff"] + 1e-9,
            )
        )

    overall = all(p.passed for p in params)
    return ComplianceResult(
        pump_tag=fitted.pump_tag,
        parameters=tuple(params),
        overall_pass=overall,
        tolerances=tol,
        overridden=overridden,
    )


def _deviation(nominal: float, predicted: float) -> float:
    """δ = 1 − nominal/predicted  (UI_SPEC §5.6)."""
    if not predicted:
        return 0.0
    return 1.0 - nominal / predicted


def _mag(q) -> Optional[float]:
    if q is None:
        return None
    try:
        return float(q.magnitude)
    except AttributeError:
        return float(q)


# ---------------------------------------------------------------------------
# Report image  (UI_SPEC §5.5 / §5.7)
# ---------------------------------------------------------------------------


def build_report_png(corrected: CorrectedCurve, rated: RatedPoint, ylims: Optional[dict] = None):
    """Reuse the library's matplotlib plot for the report image (BytesIO PNG)."""
    ylims = ylims or {}
    return corrected.curve.plot_performance_curve(
        capacity=Q_(rated.q_m3h, "m**3/h"),
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
    return PerformanceChecker(design_point, fitted.curve).report_summary


def assemble_report_data(rated: RatedPoint, bundles, equipment: Optional[dict] = None) -> dict:
    """
    Build the ``report_data`` dict exactly as ``ReportGenerator.generate_report``
    expects (UI_SPEC §5.7): one shared design point + one keyed ``test_data``
    entry per pump TAG.
    """
    equipment = equipment or {}
    design_point = make_design_point(rated)

    equipment_description = {"TAG": rated.tag}
    equipment_description.update({k: str(v) for k, v in equipment.items() if v})

    test_data = {}
    for b in bundles:
        if b.fitted is None:
            continue
        entry = {
            "test_summary": report_summary_for(b.fitted, rated),
            "test_data": b.fitted.curve.test_data,
        }
        png = b.plot_png
        if png is None and b.corrected is not None:
            png = build_report_png(b.corrected, rated)
        if png is not None:
            entry["Performance Curve"] = png
        test_data[b.pump_tag] = entry

    return {
        "equipment_description": equipment_description,
        "design_point": design_point,
        "test_data": test_data,
    }


def generate_docx(report_data: dict, language: str = "en",
                  template_path: Optional[str] = None, output_file: Optional[str] = None) -> str:
    """Call the library's ``ReportGenerator`` to write the ``.docx`` (UI_SPEC §4)."""
    try:
        from pump import ReportGenerator           # exported at top level if available
    except Exception:
        from pump.utilities.report import ReportGenerator
    gen = ReportGenerator(language=language, template_path=template_path)
    return gen.generate_report(report_data, output_file=output_file)
