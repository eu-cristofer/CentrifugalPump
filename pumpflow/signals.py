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

# ---------------------------------------------------------------------------
# 1. RatedPoint  — produced by Rated Point Input  (UI_SPEC §5.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RatedPoint:
    """The rated (design) point + rated fluid, shared by every pump branch."""

    tag: str                       # service / datasheet TAG (shared)
    standard: str                  # e.g. "API610 (12a ed.) / ISO 13709 + N-553"

    q_m3h: float                   # rated capacity            [m³/h]
    head_m: float                  # rated differential head   [m]
    speed_rpm: float               # rated speed               [rpm]
    power_kw: float                # rated breaking power      [kW]

    efficiency_pct: Optional[float] = None   # rated efficiency        [%]
    head_shutoff_m: Optional[float] = None   # rated shut-off head     [m]

    # Rated fluid: relative density is the user-facing field; absolute density is
    # kept in sync (rel * 1000 kg/m³).  Nominal viscosity is informational until
    # the viscosity correction lands in the library.
    density_rel: float = 1.0       # relative density (SG)     [-]
    viscosity_cst: float = 1.0     # nominal viscosity         [cSt]

    pressure_unit: str = "bar"     # "kgf/cm**2" | "bar"  (drives pressure_to_head)
    parallel_operation: bool = False

    fluid_name: str = "Rated fluid"

    @property
    def density_kgm3(self) -> float:
        """Absolute rated density, kept in sync with the relative density."""
        return self.density_rel * 1000.0

    def is_valid(self) -> tuple[bool, str]:
        """UI_SPEC §5.1 validation: Q ≥ 0, H > 0, N > 0, P > 0."""
        if self.q_m3h < 0:
            return False, "Capacity Q must be ≥ 0 m³/h."
        if not self.head_m > 0:
            return False, "Differential head H must be > 0 m."
        if not self.speed_rpm > 0:
            return False, "Rated speed N must be > 0 rpm."
        if not self.power_kw > 0:
            return False, "Rated power P must be > 0 kW."
        if not self.density_rel > 0:
            return False, "Relative density must be > 0."
        if not self.tag.strip():
            return False, "A service TAG is required."
        return True, ""


# ---------------------------------------------------------------------------
# 2. TestPointSet  — produced by Test Points Table  (UI_SPEC §5.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestRow:
    """One raw measured row of a FAT performance test."""

    q_m3h: float           # measured capacity            [m³/h]
    p_suction: float       # suction pressure             [pressure_unit]
    p_discharge: float     # discharge pressure           [pressure_unit]
    temp_c: float          # test-water temperature       [°C]
    speed_rpm: float       # measured speed               [rpm]
    power_kw: float        # measured breaking power      [kW]
    head_m: Optional[float] = None        # optional measured/overridden head [m]
    efficiency_pct: Optional[float] = None  # optional measured efficiency    [%]


@dataclass(frozen=True)
class TestPointSet:
    """A physical pump's raw measured rows (the source for one branch)."""

    pump_tag: str                  # physical unit TAG (unique per branch)
    rows: tuple[TestRow, ...] = ()
    pressure_unit: str = "bar"     # "kgf/cm**2" | "bar"

    def is_valid(self) -> tuple[bool, str]:
        """UI_SPEC §5.2: at least 3 points for a degree-3 fit."""
        if not self.pump_tag.strip():
            return False, "A pump TAG is required."
        if len(self.rows) < 3:
            return False, f"At least 3 points required for a fit (have {len(self.rows)})."
        return True, ""

    def has_shutoff(self) -> bool:
        """Warn if a shut-off point (Q≈0) is missing (UI_SPEC §5.2)."""
        return any(r.q_m3h < 0.1 for r in self.rows)


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

    label: str                              # marker label
    q_m3h: float                            # capacity                  [m³/h]
    head_m: Optional[float] = None          # head                      [m]
    power_kw: Optional[float] = None        # breaking power            [kW]
    efficiency_pct: Optional[float] = None  # efficiency                [%]
    pump_tag: str = ""                      # optional grouping / colour key


# ---------------------------------------------------------------------------
# 3. CorrectedCurve — produced by Speed/Affinity Correction (UI_SPEC §5.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrectedCurve:
    """A ``pump.PerformanceCurve`` corrected to rated speed + rated fluid."""

    pump_tag: str
    curve: Any                     # pump.PerformanceCurve
    fluid: Any                     # pump.Fluid actually used (rated fluid)
    target_speed_rpm: float
    # before/after rows for the correction table (mirrors the notebook print-out)
    before_after: tuple[dict, ...] = ()


# ---------------------------------------------------------------------------
# 4. FittedModel — produced by Curve Fit (UI_SPEC §5.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FittedModel:
    """Polynomial coeffs (+ optional natural cubic splines) for H, P, η."""

    pump_tag: str
    curve: Any                     # pump.PerformanceCurve (corrected)
    degree: int
    head_coeffs: np.ndarray
    power_coeffs: np.ndarray
    efficiency_coeffs: np.ndarray
    head_spline: Any = None        # mathx.NaturalCubicSpline | None
    power_spline: Any = None
    efficiency_spline: Any = None
    r2: dict = field(default_factory=dict)   # {"head": .., "power": .., "eff": ..}


# ---------------------------------------------------------------------------
# 5. ComplianceResult — produced by API 610 Compliance Check (UI_SPEC §5.6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParameterCheck:
    """One row of the compliance table."""

    name: str                      # Head | Power | Efficiency | Shutoff Head
    actual: float                  # rated / nominal value
    predicted: float               # value predicted from the fitted curve
    minimum: Optional[float]       # acceptable min (or None)
    maximum: Optional[float]       # acceptable max (or None)
    deviation: float               # δ = 1 − nominal/predicted
    tolerance: float               # fractional tolerance
    passed: bool


@dataclass(frozen=True)
class ComplianceResult:
    """Per-parameter verdicts + the per-pump overall verdict."""

    pump_tag: str
    parameters: tuple[ParameterCheck, ...]
    overall_pass: bool
    tolerances: dict = field(default_factory=dict)   # editable tolerances used
    overridden: bool = False        # True if user changed library defaults

    @property
    def verdict_label(self) -> str:
        return "APPROVED" if self.overall_pass else "REJECTED"


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
    plot_png: Any = None           # io.BytesIO PNG | None
    equipment: dict = field(default_factory=dict)   # per-pump key/value sub-table


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
