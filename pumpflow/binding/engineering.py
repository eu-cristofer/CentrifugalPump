"""
pumpflow.binding.engineering

System curve, operating point, catalogue export and pump selection.
"""

from __future__ import annotations

from typing import Optional

from pump import Q_, Fluid, Water
from pump.constants import G

from ..signals import (
    RatedPoint,
    FluidSpec,
    FluidSpec,
    FittedModel,
)

from pump import SystemCurve
from pump.operating_point import operating_point

from ..signals import OperatingPointResult, SystemCurveSpec

from pump.catalogue import (
    Candidate,
    Catalogue,
    CatalogueEntry,
    save_entry,
)

from ._common import BindingError, make_fluid
from .acceptance import criteria_for

SYSTEM_CURVE_MODES = ("static_k", "two_points", "pipe")


def make_system_curve(
    mode: str,
    *,
    name: str = "System",
    static_head: Optional[Q_] = None,
    k: Optional[Q_] = None,
    exponent: float = 2.0,
    points=None,
    length: Optional[Q_] = None,
    diameter: Optional[Q_] = None,
    roughness: Optional[Q_] = None,
    minor_k_sum: float = 0.0,
    fluid_spec: Optional[FluidSpec] = None,
    q_ref: Optional[Q_] = None,
) -> SystemCurveSpec:
    """Build a :class:`SystemCurveSpec` from node-level quantities.

    ``mode`` is ``"static_k"`` (needs ``static_head``, ``k``), ``"two_points"``
    (needs ``points = ((q1, h1), (q2, h2))``) or ``"pipe"`` (needs
    ``static_head``, ``length``, ``diameter``, ``roughness``; the fluid is
    ``fluid_spec`` or water at 20 °C).
    """
    try:
        if mode == "static_k":
            curve = SystemCurve(static_head, k, exponent)
        elif mode == "two_points":
            p1, p2 = points
            curve = SystemCurve.from_points(p1, p2, exponent)
        elif mode == "pipe":
            fluid = (
                make_fluid(fluid_spec)
                if fluid_spec is not None
                else Water(Q_(20.0, "degC"))
            )
            curve = SystemCurve.from_pipe(
                static_head,
                length,
                diameter,
                roughness,
                fluid,
                minor_k_sum=minor_k_sum,
                q_ref=q_ref,
            )
        else:
            raise BindingError(f"Unknown system-curve mode: {mode!r}")
    except BindingError:
        raise
    except (ValueError, TypeError) as exc:
        raise BindingError(str(exc)) from exc
    return SystemCurveSpec(name=(name or "System").strip() or "System", curve=curve)


def solve_operating_point(
    fitted: FittedModel,
    spec: SystemCurveSpec,
    method: str = "poly",
    q_max_factor: float = 1.5,
) -> OperatingPointResult:
    """Operating point of a fitted pump curve on a system curve."""
    try:
        point = operating_point(
            fitted.curve, spec.curve, method=method, q_max_factor=q_max_factor
        )
    except ValueError as exc:
        raise BindingError(str(exc)) from exc
    return OperatingPointResult(
        pump_tag=fitted.pump_tag, point=point, system_name=spec.name
    )


def export_pumpcurve(fitted: FittedModel, rated: RatedPoint, path) -> str:
    """Write a fitted curve as a catalogue file (``*.pumpcurve.json``).

    The entry carries the fitted model's :class:`PerformanceCurve`, the speed of
    its points (else the rated speed) and the rated point's datasheet impeller
    diameters (nominal / minimum / maximum, when set).  ``path`` is a file path or
    an existing folder (the file is then named after the pump tag).  Returns the
    written path.
    """
    curve = fitted.curve
    speed = (
        getattr(curve.points[0], "speed_of_rotation", None) if curve.points else None
    )
    if speed is None:
        speed = rated.speed
    entry = CatalogueEntry(
        name=str(fitted.pump_tag),
        curve=curve,
        speed=speed,
        diameter=rated.impeller_diameter,
        d_min=rated.impeller_diameter_min,
        d_max=rated.impeller_diameter_max,
    )
    try:
        return str(save_entry(entry, path))
    except (OSError, ValueError) as exc:
        raise BindingError(str(exc)) from exc


def select_pumps(
    folder,
    duty_q: Q_,
    duty_h: Q_,
    fluid: Optional[Fluid] = None,
    allow_speed: bool = True,
    allow_trim: bool = True,
    rated: Optional[RatedPoint] = None,
):
    """Rank the pumps of a catalogue folder for a duty.

    Returns ``(catalogue, result)``: the loaded :class:`pump.catalogue.Catalogue`
    (``load_errors`` lists unreadable files) and the ranked
    :class:`pump.catalogue.SelectionResult` (a list of candidates; ``.reasons``
    explains the refused ones).  The preferred-operating-region bounds come from
    the criteria of ``rated`` when given, else the library default.
    """
    try:
        catalogue = Catalogue.from_folder(folder)
    except FileNotFoundError as exc:
        raise BindingError(str(exc)) from exc
    criteria = criteria_for(rated) if rated is not None else None
    try:
        result = catalogue.select(
            duty_q,
            duty_h,
            fluid=fluid,
            allow_speed=allow_speed,
            allow_trim=allow_trim,
            criteria=criteria,
        )
    except ValueError as exc:
        raise BindingError(str(exc)) from exc
    return catalogue, result


def rated_from_candidate(
    cand: Candidate,
    duty_q: Q_,
    duty_h: Q_,
    template: Optional[RatedPoint] = None,
) -> RatedPoint:
    """A :class:`RatedPoint` for the duty served by ``cand`` ("send to canvas").

    Speed is the adapted speed (speed candidates) else the entry's; the impeller
    diameter is the trimmed one (trim candidates) else the entry's.  Power is the
    curve's prediction at the duty, or ``ρ·g·Q·H / η`` when the curve has no
    power data.  ``template`` supplies the service tag / standard / client.
    """
    fluid = cand.curve.fluid
    eta = cand.eta_at_duty
    power = cand.power_at_duty
    if power is None:
        frac = float(eta.to("percent").magnitude) / 100.0
        if not frac > 0:
            raise BindingError("Cannot derive the power: efficiency at duty <= 0.")
        power = ((fluid.density * duty_q * G * duty_h).to("kW")) / frac
    speed = cand.value if cand.adaptation == "speed" else cand.entry.speed
    d_imp = cand.value if cand.adaptation == "trim" else cand.entry.diameter
    try:
        shutoff = cand.curve.predict_head(Q_(0.0, "m**3/h"))
    except Exception:
        shutoff = None
    kwargs = {}
    if template is not None:
        kwargs = {
            "standard": template.standard,
            "standard_key": template.standard_key,
            "client": template.client,
        }
    return RatedPoint(
        tag=template.tag if template is not None else cand.entry.name,
        standard=kwargs.pop("standard", "API610 / ISO 13709"),
        q=duty_q,
        head=duty_h,
        speed=speed,
        power=power,
        efficiency=eta,
        head_shutoff=shutoff,
        density=fluid.density,
        fluid_name=fluid.name,
        service=f"Selected: {cand.label}",
        impeller_diameter=d_imp,
        impeller_diameter_max=cand.entry.d_max,
        impeller_diameter_min=cand.entry.d_min,
        **kwargs,
    )
