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
Polynomial fit + predictions            ``PerformanceCurve.fitter.*_coeffs`` / ``predict_*``
Built-in matplotlib curve               ``PerformanceCurve.plot_performance_curve(...)``
Tolerances & verdict tables             ``pump.PerformanceChecker(design_point, curve)``
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
)
from pump.constants import G

from .mathx import NaturalCubicSpline, r_squared
from .numfmt import parse_decimal
from .signals import (
    RatedPoint,
    FluidSpec,
    TestPointSet,
    CorrectedCurve,
    FittedModel,
    ComplianceResult,
    ParameterCheck,
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


def row_head(row, density: Optional[Q_] = None) -> Q_:
    """
    Read-only ``Head`` column for the Test Points grid (UI_SPEC §5.2):
    ``Head = (P_dis − P_suc) / (ρ·g)`` in metres.  ``ρ`` is water at ``T_water``
    by default, or ``density`` when a Fluid node overrides the test fluid
    (UC-00).  An explicit measured/overridden head on the row wins.
    """
    if row.head is not None:
        return row.head.to("m")
    rho = density if density is not None else Water(row.temperature).density
    return ((row.p_discharge - row.p_suction) / (rho * G)).to("m")


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


def correct_curve(
    rated: RatedPoint,
    tps: TestPointSet,
    target_speed: Optional[Q_] = None,
    apply_speed: bool = True,
    apply_density: bool = True,
    degree: int = 3,
    target_fluid: Optional[Fluid] = None,
) -> CorrectedCurve:
    """
    Build ``TestPoint``s from the raw rows, wrap them in a ``PerformanceCurve``,
    then correct to rated speed (affinity laws) and rated fluid (density).

    ``target_fluid`` overrides the density-correction target: when a Fluid node
    is wired in, the curve is corrected ``to_fluid`` *that* fluid instead of the
    rated fluid derived from ``rated`` (UC-00).  With it set, ``rated`` may be
    ``None`` (forced speed correction that still applies the density step).
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
        head = row_head(r, test_rho)
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

    # 2) density / fluid correction to the rated fluid (or an override Fluid node)
    fluid_used = test_fluid
    if apply_density:
        rated_fluid = (
            target_fluid if target_fluid is not None else make_rated_fluid(rated)
        )
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
# API 610 compliance  (UI_SPEC §5.6)
# ---------------------------------------------------------------------------


def default_tolerances(rated: RatedPoint) -> dict:
    """Library-default tolerances exposed as editable fields (UI_SPEC §5.6)."""
    head_m = float(rated.head.to("m").magnitude)
    h = (
        float(rated.head_shutoff.to("m").magnitude)
        if rated.head_shutoff is not None
        else head_m
    )
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

    rated_q = rated.q
    rated_head = float(rated.head.to("m").magnitude)
    rated_power = float(rated.power.to("kW").magnitude)
    params = []

    # --- Head:  |δ| ≤ tol -----------------------------------------------------
    pred_head = float(fitted.curve.predict_head(rated_q).to("m").magnitude)
    dev_head = _deviation(rated_head, pred_head)
    params.append(
        ParameterCheck(
            name="Head",
            actual=rated_head,
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
    dev_power = _deviation(rated_power, pred_power)
    params.append(
        ParameterCheck(
            name="Power",
            actual=rated_power,
            predicted=pred_power,
            minimum=None,
            maximum=_mag(getattr(checker, "maximum_breaking_power", None)),
            deviation=dev_power,
            tolerance=tol["power"],
            passed=dev_power <= tol["power"] + 1e-9,
        )
    )

    # --- Efficiency:  δ ≥ −tol -----------------------------------------------
    if rated.efficiency is not None:
        rated_eff = float(rated.efficiency.to("percent").magnitude)
        pred_eff = float(
            fitted.curve.predict_efficiency(rated_q).to("percent").magnitude
        )
        dev_eff = _deviation(rated_eff, pred_eff)
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
            )
        )

    # --- Shutoff Head:  |δ| ≤ tol --------------------------------------------
    if rated.head_shutoff is not None:
        rated_so = float(rated.head_shutoff.to("m").magnitude)
        pred_so = float(fitted.curve.predict_head(Q_(0, "m**3/h")).to("m").magnitude)
        dev_so = _deviation(rated_so, pred_so)
        params.append(
            ParameterCheck(
                name="Shutoff Head",
                actual=rated_so,
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
    return PerformanceChecker(design_point, fitted.curve).report_summary


def assemble_report_data(
    rated: RatedPoint, bundles, equipment: Optional[dict] = None
) -> dict:
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
        if b.compliance is not None:
            entry["verdict"] = bool(b.compliance.overall_pass)
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
        try:
            paths[fmt] = str(writers[fmt](str(folder / f"{stem}.{fmt}")))
        except Exception as exc:  # collected, reported by the caller
            errors[fmt] = f"{type(exc).__name__}: {exc}"
    return paths, errors
