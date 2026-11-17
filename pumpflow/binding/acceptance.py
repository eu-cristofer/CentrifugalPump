"""
pumpflow.binding.acceptance

Acceptance criteria and the Compliance, NPSH and mechanical-run verdicts (thin views of pump.acceptance / pump.npsh / pump.mechanical_run).
"""

from __future__ import annotations

from typing import Optional

from pump import Q_, Pressure, Water
from pump.acceptance import AcceptanceCriteria, evaluate_performance

from ..signals import (
    RatedPoint,
    FittedModel,
    ComplianceResult,
    ParameterCheck,
    MechanicalRunSet,
    MechanicalRunResultSignal,
    NPSHSet,
    NPSHResultSignal,
)
from ._common import BindingError


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


def check_compliance(
    fitted: FittedModel,
    rated: RatedPoint,
    tolerances: Optional[dict] = None,
) -> ComplianceResult:
    """
    Evaluate API 610 deviations & verdict.

    A thin adapter: the verdict is :func:`pump.acceptance.evaluate_performance`
    (the same engine as ``PerformanceChecker``), and this function only turns
    its rows into display floats (m, kW, %, rpm).  Every deviation is
    ``(predicted - rated) / rated``.
    """
    criteria = criteria_for(rated)
    lib_defaults = default_tolerances(rated)
    tol = dict(lib_defaults)
    if tolerances:
        tol.update(tolerances)

    def _differs(a, b) -> bool:
        if a is None or b is None:
            return (a is None) != (b is None)
        return abs(a - b) > 1e-9

    overridden = any(
        _differs(tol[k], lib_defaults[k]) for k in lib_defaults if k in tol
    )
    verdict = evaluate_performance(
        fitted.curve,
        rated.q,
        rated.head,
        criteria,
        rated_power=rated.power,
        rated_efficiency=rated.efficiency,
        rated_shutoff=rated.head_shutoff,
        parallel_operation=bool(rated.parallel_operation),
        rated_speed=rated.speed,
        test_speeds=tuple(getattr(fitted, "test_speeds", ()) or ()),
        tolerances=tol,
    )
    verified = bool(criteria.verified)
    display_unit = {
        "Head": "m",
        "Power": "kW",
        "Efficiency": "percent",
        "Shutoff Head": "m",
        "Test speed": "rpm",
    }

    def mag(q, unit):
        return None if q is None else float(q.to(unit).magnitude)

    params = []
    for row in verdict.rows:
        unit = display_unit.get(row.name)
        if unit is None:  # parallel operation: reported through parallel_ok
            continue
        params.append(
            ParameterCheck(
                name=row.name,
                actual=mag(row.rated, unit),
                predicted=mag(row.predicted, unit),
                minimum=mag(row.minimum, unit),
                maximum=mag(row.maximum, unit),
                deviation=row.deviation,
                tolerance=row.tolerance,
                passed=row.status in ("pass", "info"),
                extrapolated=row.extrapolated,
                verified=verified or row.status == "info",
                informational=row.status == "info",
                note=row.note,
                evaluated=row.status != "not evaluated",
            )
        )
    return ComplianceResult(
        pump_tag=fitted.pump_tag,
        parameters=tuple(params),
        overall_pass=verdict.approved,
        tolerances=tol,
        overridden=overridden,
        criteria_label=criteria_label(criteria),
        unverified=criteria.performance_unverified,
        parallel_ok=verdict.parallel_ok,
        not_evaluated=verdict.not_evaluated,
    )


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
        npshr_tol_plus=getattr(base, "npshr_tol_plus", None),
        source=source,
        verified=False if overridden else bool(getattr(base, "verified", False)),
    )
    result = check_npsh(npsha, npshr, criteria, npshr_quoted=npsh_set.npshr_quoted)
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
