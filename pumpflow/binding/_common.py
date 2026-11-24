"""
pumpflow.binding._common

Shared adapters: errors, fluids, the rated design point.
"""

from __future__ import annotations

from typing import Optional

from pump import (
    Q_,
    Fluid,
    Water,
    DesignPoint,
)

from ..signals import RatedPoint, FluidSpec, FluidSpec


class BindingError(Exception):
    """Human-readable wrapper around library/validation failures (UI_SPEC §7)."""


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


def _has_eff(point) -> bool:
    try:
        _ = point.efficiency
        return True
    except Exception:
        return False


def _mag(q) -> Optional[float]:
    if q is None:
        return None
    try:
        return float(q.magnitude)
    except AttributeError:
        return float(q)
