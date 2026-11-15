"""
signals
=======

Typed inter-widget payloads — the "signals" that flow along the links of the
node canvas (UI_SPEC §3).

Following Orange's model, widgets communicate by emitting and consuming typed
signals.  Each payload is an immutable ``@dataclass`` (a widget recomputes and
re-emits a *fresh* instance whenever its inputs or settings change — matching the
library's "always return a new instance" convention in
``PerformanceCurve.to_speed`` / ``to_fluid``).

The dataclasses hold live ``pump`` library objects and ``pint`` quantities at
runtime; JSON (de)serialization lives in :mod:`pumpflow.persistence`, which only
ever stores plain magnitudes + units so the on-disk format stays stable.

Identity convention (UI_SPEC §3)
--------------------------------
- ``RatedPoint.tag`` is the **service / datasheet** tag and is *shared* across
  every pump branch.
- ``TestPointSet.pump_tag`` is the **physical unit** tag and is *unique per
  branch* (e.g. ``B-2351105A``).
- Every downstream signal carries its branch's ``pump_tag`` so Report Export can
  key datasets without ambiguity, and so plots/verdicts can be told apart on the
  canvas.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Optional

import numpy as np

from pump import Q_, Pressure

# ---------------------------------------------------------------------------
# 1. RatedPoint  — produced by Rated Point Input  (UI_SPEC §5.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RatedPoint:
    """The rated (design) point + rated fluid, shared by every pump branch."""

    tag: str  # service / datasheet TAG (shared)
    standard: str  # display label, e.g. "API610 (12a ed.) / ISO 13709 + N-553"

    q: Q_  # rated capacity            (m³/h, any compatible unit)
    head: Q_  # rated differential head   (m)
    speed: Q_  # rated speed               (rpm)
    power: Q_  # rated breaking power      (kW)

    efficiency: Optional[Q_] = None  # rated efficiency        (percent)
    head_shutoff: Optional[Q_] = None  # rated shut-off head     (m)
    npsha: Optional[Q_] = None  # rated NPSHa                (m)

    # Rated fluid: absolute density is the stored quantity; ``density_rel`` (SG)
    # is the user-facing derived form.  Nominal viscosity is informational until
    # the viscosity correction lands in the library.
    density: Q_ = Q_(1000.0, "kg/m**3")  # rated density
    viscosity: Q_ = Q_(1.0, "cSt")  # nominal kinematic viscosity

    parallel_operation: bool = False

    fluid_name: str = "Rated fluid"
    service: str = ""  # human-readable service description

    # Acceptance criteria selection (sprint 5): ``standard`` above stays the
    # free-text display label; these two keys drive ``pump.acceptance``.
    standard_key: str = "api610:12"  # AcceptanceCriteria key, e.g. "api610:8"
    client: Optional[str] = None  # client overlay key, e.g. "n553"

    @property
    def density_rel(self) -> float:
        """Relative density (SG) — the user-facing density form."""
        return float(self.density.to("kg/m**3").magnitude) / 1000.0

    def is_valid(self) -> tuple[bool, str]:
        """UI_SPEC §5.1 validation: Q ≥ 0, H > 0, N > 0, P > 0."""
        if self.q.to("m**3/h").magnitude < 0:
            return False, "Capacity Q must be ≥ 0 m³/h."
        if not self.head.to("m").magnitude > 0:
            return False, "Differential head H must be > 0 m."
        if not self.speed.to("rpm").magnitude > 0:
            return False, "Rated speed N must be > 0 rpm."
        if not self.power.to("kW").magnitude > 0:
            return False, "Rated power P must be > 0 kW."
        if not self.density_rel > 0:
            return False, "Relative density must be > 0."
        if not self.tag.strip():
            return False, "A service TAG is required."
        return True, ""


# ---------------------------------------------------------------------------
# 1b. FluidSpec  — produced by the Fluid node  (UC-00 — service fluid object)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FluidSpec:
    """A service fluid defined on its own canvas node (UC-00).

    When wired into Speed / Affinity Correction it overrides the fluid the curve
    is corrected *to* (``PerformanceCurve.to_fluid``).  ``source`` is ``"water"``
    (density derived from ``temperature`` via ``pump.Water``) or ``"manual"``
    (``density`` entered directly, as relative density × 1000).
    """

    name: str
    source: str = "manual"  # "manual" | "water"
    density: Q_ = Q_(1000.0, "kg/m**3")  # resolved absolute density
    viscosity: Q_ = Q_(1.0, "cSt")  # nominal kinematic viscosity
    temperature: Optional[Q_] = None  # water temperature, when source == "water"

    @property
    def density_rel(self) -> float:
        """Relative density (SG) — the user-facing density form."""
        return float(self.density.to("kg/m**3").magnitude) / 1000.0

    def is_valid(self) -> tuple[bool, str]:
        if not self.name.strip():
            return False, "Fluid name is required."
        if not self.density.to("kg/m**3").magnitude > 0:
            return False, "Density must be > 0 kg/m³."
        return True, ""


# ---------------------------------------------------------------------------
# 2. TestPointSet  — produced by Test Points Table  (UI_SPEC §5.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestRow:
    """One raw measured row of a FAT performance test."""

    # Domain class, not a pytest test class (name starts with "Test").
    __test__ = False

    q: Q_  # measured capacity            (m³/h)
    p_suction: Pressure  # suction pressure (carries its own unit)
    p_discharge: Pressure  # discharge pressure (carries its own unit)
    temperature: Q_  # test-water temperature       (°C)
    speed: Q_  # measured speed               (rpm)
    power: Q_  # measured breaking power      (kW)
    head: Optional[Q_] = None  # optional measured/overridden head (m)
    efficiency: Optional[Q_] = None  # optional measured efficiency    (percent)


@dataclass(frozen=True)
class BenchGeometry:
    """Optional test-bench geometry completing the head (sprint 4).

    ``H = ΔP/(ρ·g) + (v_d² − v_s²)/(2g) + (z_d − z_s)``.  Every field is an
    optional length Quantity in whatever unit the user entered.  The velocity
    term needs **both** pipe inner diameters, the elevation term **both** gauge
    elevations; a missing partner makes that term 0 (library behaviour).

    Examples
    --------
    >>> from pump import Q_
    >>> BenchGeometry().is_empty
    True
    >>> g = BenchGeometry(suction_id=Q_(150, "mm"), discharge_id=Q_(100, "mm"))
    >>> g.is_empty, g.components_available()
    (False, (True, False))
    """

    suction_id: Optional[Q_] = None  # suction pipe inner diameter
    discharge_id: Optional[Q_] = None  # discharge pipe inner diameter
    suction_elevation: Optional[Q_] = None  # suction gauge elevation z_s
    discharge_elevation: Optional[Q_] = None  # discharge gauge elevation z_d

    @property
    def is_empty(self) -> bool:
        """True when no field is set (the head is then ΔP/(ρ·g) only)."""
        return (
            self.suction_id is None
            and self.discharge_id is None
            and self.suction_elevation is None
            and self.discharge_elevation is None
        )

    def components_available(self) -> tuple[bool, bool]:
        """``(velocity, elevation)`` — which head terms can be evaluated."""
        return (
            self.suction_id is not None and self.discharge_id is not None,
            self.suction_elevation is not None and self.discharge_elevation is not None,
        )


@dataclass(frozen=True)
class TestPointSet:
    """A physical pump's raw measured rows (the source for one branch)."""

    # Domain class, not a pytest test class (name starts with "Test").
    __test__ = False

    pump_tag: str  # physical unit TAG (unique per branch)
    rows: tuple[TestRow, ...] = ()
    # Test-fluid density override from a connected Fluid node.  When set,
    # Head/η are derived with this constant density instead of per-row water at
    # the row temperature.  Runtime-only — set by the node from its FluidSpec
    # input, never persisted (the table stores only its own rows).
    test_density: Optional[Q_] = None
    # Optional bench geometry (pipe IDs + gauge elevations) for the velocity and
    # elevation head terms.  ``None`` keeps the pressure-only head.
    geometry: Optional[BenchGeometry] = None

    def is_valid(self) -> tuple[bool, str]:
        """UI_SPEC §5.2: at least 3 points for a degree-3 fit."""
        if not self.pump_tag.strip():
            return False, "A pump TAG is required."
        if len(self.rows) < 3:
            return (
                False,
                f"At least 3 points required for a fit (have {len(self.rows)}).",
            )
        # A row that is still blank (e.g. a template being filled in on test
        # day) must be rejected here, not crash downstream: N=0 divides by zero
        # in the affinity ratio and an empty ΔP yields a zero head.
        for i, r in enumerate(self.rows, start=1):
            if r.speed.magnitude <= 0:
                return False, f"Row {i}: speed N is missing."
            if r.power.magnitude <= 0:
                return False, f"Row {i}: power P is missing."
            if r.head is None and (r.p_discharge - r.p_suction).magnitude == 0:
                return False, f"Row {i}: P_dis equals P_suc (no head)."
        return True, ""

    def has_shutoff(self) -> bool:
        """Warn if a shut-off point (Q≈0) is missing (UI_SPEC §5.2)."""
        return any(r.q < Q_(0.1, "m**3/h") for r in self.rows)


# ---------------------------------------------------------------------------
# 2b. PointSample — produced by the Point node (ad-hoc exploratory overlay)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PointSample:
    """A single ad-hoc Q/H/P/η point to overlay on the Performance Explorer.

    Unlike :class:`TestRow` (a raw measured row whose head/η are *derived* from
    suction/discharge pressures), a ``PointSample`` already carries the plotted
    quantities — it is a marker the user drops on the chart (a guarantee point,
    a re-test point, a datasheet value) rather than a measurement to correct.
    """

    label: str  # marker label
    q: Q_  # capacity                  (m³/h)
    head: Optional[Q_] = None  # head                      (m)
    power: Optional[Q_] = None  # breaking power            (kW)
    efficiency: Optional[Q_] = None  # efficiency                (percent)
    pump_tag: str = ""  # optional grouping / colour key


# ---------------------------------------------------------------------------
# 3. CorrectedCurve — produced by Speed/Affinity Correction (UI_SPEC §5.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrectedCurve:
    """A ``pump.PerformanceCurve`` corrected to rated speed + rated fluid."""

    pump_tag: str
    curve: Any  # pump.PerformanceCurve
    fluid: Any  # pump.Fluid actually used (rated fluid)
    target_speed: Q_
    # before/after rows for the correction table (mirrors the notebook print-out).
    # A display table: plain floats in m³/h, m, kW, % and rpm (the one documented
    # exception to "signals carry Quantities").
    before_after: tuple[dict, ...] = ()
    # Bench geometry the measured heads were derived with (for the report).
    geometry: Optional[BenchGeometry] = None
    # HI 9.6.7 viscosity correction: {"B", "C_Q", "C_H", "C_eta"} (factors at the
    # BEP), or ``None`` when the viscosity correction was not applied.
    viscous: Optional[dict] = None


# ---------------------------------------------------------------------------
# 4. FittedModel — produced by Curve Fit (UI_SPEC §5.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FittedModel:
    """Polynomial coeffs (+ optional natural cubic splines) for H, P, η."""

    pump_tag: str
    curve: Any  # pump.PerformanceCurve (corrected)
    degree: int
    head_coeffs: np.ndarray
    power_coeffs: np.ndarray
    efficiency_coeffs: np.ndarray
    head_spline: Any = None  # mathx.NaturalCubicSpline | None
    power_spline: Any = None
    efficiency_spline: Any = None
    r2: dict = field(default_factory=dict)  # {"head": .., "power": .., "eff": ..}


# ---------------------------------------------------------------------------
# 5. ComplianceResult — produced by API 610 Compliance Check (UI_SPEC §5.6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParameterCheck:
    """One row of the compliance table."""

    name: str  # Head | Power | Efficiency | Shutoff Head
    actual: float  # rated / nominal value
    predicted: float  # value predicted from the fitted curve
    minimum: Optional[float]  # acceptable min (or None)
    maximum: Optional[float]  # acceptable max (or None)
    deviation: float  # δ = (predicted − rated) / rated
    tolerance: float  # fractional tolerance
    passed: bool
    extrapolated: bool = False  # predicted value extrapolated (shut-off, no Q≈0 point)
    verified: bool = True  # criteria verified against the standard text


@dataclass(frozen=True)
class ComplianceResult:
    """Per-parameter verdicts + the per-pump overall verdict."""

    pump_tag: str
    parameters: tuple[ParameterCheck, ...]
    overall_pass: bool
    tolerances: dict = field(default_factory=dict)  # editable tolerances used
    overridden: bool = False  # True if user changed library defaults
    criteria_label: str = ""  # e.g. "API 610 12th edition + Petrobras N-553 (...)"
    unverified: tuple = ()  # names of criteria parts not yet verified
    parallel_ok: Optional[bool] = None  # parallel-operation rule (None = n/a)

    @property
    def verdict_label(self) -> str:
        return "APPROVED" if self.overall_pass else "REJECTED"


# ---------------------------------------------------------------------------
# 5b. Mechanical run — produced by the Mechanical Run node  (sprint 6 / UC-11)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MechanicalRunSet:
    """A pump's mechanical-run log (time-stamped multi-channel readings)."""

    pump_tag: str  # physical unit TAG (unique per branch)
    log: Any  # pump.mechanical_run.MechanicalRunLog


@dataclass(frozen=True)
class MechanicalRunResultSignal:
    """Verdict of a mechanical run against its criteria."""

    pump_tag: str
    result: Any  # pump.mechanical_run.MechanicalRunResult
    criteria_label: str = ""
    plot_png: Any = None  # io.BytesIO PNG | None


# ---------------------------------------------------------------------------
# 5c. NPSH margin — produced by the NPSH node  (sprint 8 / UC-05)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NPSHSet:
    """A pump's NPSHr test points plus the NPSHa they are judged against.

    ``points`` is a tuple of ``(Q_capacity, Q_npshr)`` pairs; ``npsha`` is the
    available NPSH (``None`` when the node has none of its own, then the rated
    point's value is used); ``mode`` records where NPSHa came from
    (``"points"`` = entered / rated, ``"calculator"`` = computed from suction
    conditions); ``degree`` is the NPSHr polynomial degree.
    """

    pump_tag: str  # physical unit TAG (unique per branch)
    points: tuple = ()  # ((Q_ capacity, Q_ npshr), ...)
    npsha: Optional[Q_] = None
    mode: str = "points"
    degree: int = 2


@dataclass(frozen=True)
class NPSHResultSignal:
    """Verdict of the NPSH margin check (``pump.npsh.NPSHResult``)."""

    pump_tag: str
    result: Any  # pump.npsh.NPSHResult
    curve: Any = None  # pump.npsh.NPSHrCurve
    plot_png: Any = None  # io.BytesIO PNG | None
    criteria_label: str = ""


# ---------------------------------------------------------------------------
# 6. ReportBundle — assembled inside Report Export (UI_SPEC §5.7 / §3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchBundle:
    """Everything Report Export needs from one connected pump branch."""

    pump_tag: str
    corrected: Optional[CorrectedCurve] = None
    fitted: Optional[FittedModel] = None
    compliance: Optional[ComplianceResult] = None
    plot_png: Any = None  # io.BytesIO PNG | None
    equipment: dict = field(default_factory=dict)  # per-pump key/value sub-table
    mechanical: Optional[MechanicalRunResultSignal] = None  # sprint 6
    npsh: Optional[NPSHResultSignal] = None  # sprint 8


@dataclass(frozen=True)
class ReportBundle:
    """Shared rated point/fluid + one entry per pump TAG, ready to serialize."""

    rated: RatedPoint
    branches: tuple[BranchBundle, ...] = ()

    @property
    def overall_pass(self) -> bool:
        """Acceptance reflects ALL pumps (UI_SPEC §2 / §9)."""
        checks = [b.compliance for b in self.branches if b.compliance is not None]
        return bool(checks) and all(c.overall_pass for c in checks)


def with_changes(obj, **changes):
    """Convenience for immutable re-emission (``dataclasses.replace``)."""
    return replace(obj, **changes)
