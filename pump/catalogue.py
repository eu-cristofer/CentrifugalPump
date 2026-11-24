"""
catalogue
=========

Pump selection from a catalogue of known curves (UC-01).

A catalogue is a folder of ``*.pumpcurve.json`` files, one pump curve each.  Given
a duty ``(Q, H)`` (and optionally a fluid) :meth:`Catalogue.select` adapts every
entry to pass through the duty -- by **speed** (VFD, affinity ``N ∝ Q``) and/or by
**impeller trim** (diameter affinity ``D ∝ Q``) -- and ranks the results.

Both adaptations solve the same affinity parabola through the duty
(:func:`pump.trim.affinity_intersection`); the curves are then produced by
:meth:`pump.PerformanceCurve.to_speed` / :meth:`pump.PerformanceCurve.to_diameter`.
Viscosity correction is **not** applied (only a density change, via ``to_fluid``,
when ``fluid`` is given).

``.pumpcurve.json`` format (version 1)
--------------------------------------
Quantities are ``{"value", "unit"}`` pairs (:mod:`pump.quantity_io`)::

    {
      "format": "pumpcurve", "version": 1,
      "name": "P-9002A",
      "speed": {"value": 1780, "unit": "rpm"},
      "diameter": {"value": 128, "unit": "mm"} | null,
      "d_min": {...} | null, "d_max": {...} | null,
      "speed_range": {"min": {...}, "max": {...}} | null,      (optional)
      "polynomial_degree": 3,                                   (optional)
      "fluid": {"name": "Water", "density": {"value": 997, "unit": "kg/m**3"}},
      "points": [
        {"q": {...}, "head": {...}, "power": {...} | null,
         "efficiency": {"value": 71.2, "unit": "percent"}]      (efficiency optional)
      ]
    }

``efficiency`` (optional) pins the measured efficiency; without it the efficiency
is derived from ``power``, head and the fluid density.  An entry whose points
lack both cannot be ranked and is reported as a rejection.

Ranking (deterministic)
-----------------------
1. candidates inside the preferred operating region (POR) first;
2. then higher efficiency at the duty;
3. then smaller ``|1 - Q / Q_BEP|``;
4. then entry name, then adaptation (``as-is``, ``trim``, ``speed``).

The POR bounds (fractions of the best-efficiency flow) come from
``AcceptanceCriteria.selection`` (``pump/standards/api610.toml``, unverified).
When no bounds are configured every candidate counts as in-POR.

Candidates that do not fit are *not* silently dropped: :meth:`Catalogue.select`
returns a :class:`SelectionResult` (a ``list`` of :class:`Candidate`) whose
``rejected`` / ``reasons`` explain every entry or adaptation that was refused.
"""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .acceptance import AcceptanceCriteria
from .performance_curve import PerformanceCurve
from .point import TestPoint
from .quantity_io import from_json, to_json
from .trim import affinity_intersection, diameter_for_duty
from .utilities.fluid import Fluid
from .utilities.unit_conversion import Q_

__all__ = [
    "CURVE_SUFFIX",
    "Candidate",
    "Catalogue",
    "CatalogueEntry",
    "Rejection",
    "SelectionResult",
    "entry_from_dict",
    "entry_to_dict",
    "load_entry",
    "save_entry",
]

CURVE_SUFFIX = ".pumpcurve.json"
FORMAT_VERSION = 1

# Order used as the last ranking tie-break.
_ADAPT_ORDER = {"as-is": 0, "trim": 1, "speed": 2}


def _has_eff(point) -> bool:
    try:
        _ = point.efficiency
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CatalogueEntry:
    """One pump curve of the catalogue.

    Attributes
    ----------
    name : str
        Unique pump name.
    curve : PerformanceCurve
        Measured / published curve at ``speed`` and ``diameter`` (its points
        carry ``speed_of_rotation`` and, for ranking, efficiency).
    speed : Q_
        Speed the curve corresponds to.
    diameter : Q_ or None
        Impeller diameter the curve corresponds to (``None``: no trimming).
    d_min : Q_ or None
        Allowed impeller diameter range.  ``d_max=None`` means "not larger than
        ``diameter``".
    d_max : Q_ or None
        Allowed impeller diameter range.  ``d_max=None`` means "not larger than
        ``diameter``".
    speed_range : tuple of (Q_, Q_) or None
        Allowed ``(min, max)`` speed; ``None`` = unrestricted.
    """

    name: str
    curve: PerformanceCurve
    speed: Q_
    diameter: Optional[Q_] = None
    d_min: Optional[Q_] = None
    d_max: Optional[Q_] = None
    speed_range: Optional[Tuple[Q_, Q_]] = None

    @property
    def has_efficiency(self) -> bool:
        """True when every point of the curve carries an efficiency."""
        return bool(self.curve.points) and all(_has_eff(p) for p in self.curve.points)


@dataclass(frozen=True)
class Candidate:
    """One adapted catalogue entry, scored for a duty.

    Attributes
    ----------
    entry : CatalogueEntry
    adaptation : str
        ``"as-is"``, ``"speed"`` or ``"trim"``.
    curve : PerformanceCurve
        The adapted curve (a new instance; the entry's curve is untouched).
    value : Q_ or None
        New speed (``"speed"``) or new diameter (``"trim"``); ``None`` as-is.
    eta_at_duty : Q_
        Efficiency (percent) of the adapted curve at the duty capacity.
    power_at_duty : Q_ or None
        Breaking power (kW) at the duty, when the curve has power data.
    q_over_qbep : float
        ``Q_duty / Q_BEP`` of the adapted curve.
    in_por : bool
        ``Q / Q_BEP`` inside the preferred operating region.
    trim_margin : float or None
        Trim candidates only: ``D_max / D - 1``, the room left to enlarge the
        impeller (``D_max`` = ``entry.d_max``, else the reference diameter).
    reasons : tuple of str
        Notes (e.g. "outside the preferred operating region", large-trim warning).
    """

    entry: CatalogueEntry
    adaptation: str
    curve: PerformanceCurve
    value: Optional[Q_]
    eta_at_duty: Q_
    power_at_duty: Optional[Q_]
    q_over_qbep: float
    in_por: bool
    trim_margin: Optional[float] = None
    reasons: Tuple[str, ...] = ()

    @property
    def name(self) -> str:
        return self.entry.name

    @property
    def label(self) -> str:
        """Short display label, e.g. ``"P1 @ 1450 rpm"``."""
        if self.adaptation == "speed" and self.value is not None:
            return f"{self.entry.name} @ {self.value.to('rpm').magnitude:.0f} rpm"
        if self.adaptation == "trim" and self.value is not None:
            return f"{self.entry.name} @ D {self.value.to('mm').magnitude:.1f} mm"
        return self.entry.name


@dataclass(frozen=True)
class Rejection:
    """Why an entry (or one adaptation of it) was not offered."""

    name: str
    adaptation: str  # "as-is" | "speed" | "trim" | "-" (the whole entry)
    reason: str


class SelectionResult(list):
    """Ranked ``list`` of :class:`Candidate` that also explains the rejections.

    Attributes
    ----------
    rejected : list of Rejection
    reasons : list of str
        ``"<name> (<adaptation>): <reason>"`` for every rejection.
    """

    def __init__(self, candidates=(), rejected=()):
        super().__init__(candidates)
        self.rejected: List[Rejection] = list(rejected)

    @property
    def reasons(self) -> List[str]:
        return [f"{r.name} ({r.adaptation}): {r.reason}" for r in self.rejected]


# --------------------------------------------------------------------------- #
# JSON (de)serialisation
# --------------------------------------------------------------------------- #
def _opt_q(data: dict, key: str) -> Optional[Q_]:
    value = data.get(key)
    return None if value is None else from_json(value)


def entry_from_dict(data: dict, source: str = "") -> CatalogueEntry:
    """Build a :class:`CatalogueEntry` from a ``.pumpcurve.json`` document.

    Raises
    ------
    ValueError
        On a malformed document (the message names ``source``).
    """
    where = f"{source}: " if source else ""
    try:
        name = str(data["name"]).strip()
        if not name:
            raise ValueError("empty name")
        speed = from_json(data["speed"])
        fluid_doc = data["fluid"]
        fluid = Fluid(str(fluid_doc["name"]), density=from_json(fluid_doc["density"]))
        rows = data["points"]
        if not isinstance(rows, list) or len(rows) < 2:
            raise ValueError("'points' needs at least 2 entries")
        diameter = _opt_q(data, "diameter")
        d_min = _opt_q(data, "d_min")
        d_max = _opt_q(data, "d_max")
        sr = data.get("speed_range")
        speed_range = (from_json(sr["min"]), from_json(sr["max"])) if sr else None

        points = []
        for row in rows:
            kwargs = {"_head": from_json(row["head"])}
            if row.get("power") is not None:
                kwargs["breaking_power"] = from_json(row["power"])
            if row.get("efficiency") is not None:
                kwargs["_efficiency"] = from_json(row["efficiency"])
            point = TestPoint(
                fluid=fluid,
                capacity=from_json(row["q"]),
                speed_of_rotation=speed,
                **kwargs,
            )
            if "_efficiency" not in kwargs and "breaking_power" in kwargs:
                _ = point.efficiency  # derive and cache from power
            points.append(point)
        degree = int(data.get("polynomial_degree", 3))
        degree = max(1, min(degree, len(points) - 1))
        curve = PerformanceCurve(fluid, points, polynomial_degree=degree)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"{where}malformed pump curve ({type(exc).__name__}: {exc})")
    except ValueError as exc:
        raise ValueError(f"{where}{exc}")
    return CatalogueEntry(
        name=name,
        curve=curve,
        speed=speed,
        diameter=diameter,
        d_min=d_min,
        d_max=d_max,
        speed_range=speed_range,
    )


def entry_to_dict(entry: CatalogueEntry) -> dict:
    """The ``.pumpcurve.json`` document of an entry (JSON-ready)."""
    rows = []
    for p in entry.curve.points:
        row = {
            "q": to_json(p.capacity),
            "head": to_json(p.head),
            "power": (
                to_json(p.breaking_power) if hasattr(p, "breaking_power") else None
            ),
        }
        if _has_eff(p):
            row["efficiency"] = {
                "value": float(p.efficiency.to("percent").magnitude),
                "unit": "percent",
            }
        rows.append(row)
    fluid = entry.curve.fluid
    doc = {
        "format": "pumpcurve",
        "version": FORMAT_VERSION,
        "name": entry.name,
        "speed": to_json(entry.speed),
        "diameter": to_json(entry.diameter) if entry.diameter is not None else None,
        "d_min": to_json(entry.d_min) if entry.d_min is not None else None,
        "d_max": to_json(entry.d_max) if entry.d_max is not None else None,
        "polynomial_degree": int(entry.curve.polynomial_degree),
        "fluid": {"name": fluid.name, "density": to_json(fluid.density)},
        "points": rows,
    }
    if entry.speed_range is not None:
        doc["speed_range"] = {
            "min": to_json(entry.speed_range[0]),
            "max": to_json(entry.speed_range[1]),
        }
    return doc


def load_entry(path) -> CatalogueEntry:
    """Read one ``*.pumpcurve.json`` file."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected a JSON object")
    return entry_from_dict(data, source=path.name)


def save_entry(entry: CatalogueEntry, path) -> Path:
    """Write ``entry`` as a ``.pumpcurve.json`` file and return its path.

    If ``path`` is an existing directory the file is named
    ``<entry name>.pumpcurve.json`` inside it.
    """
    path = Path(path)
    if path.is_dir():
        safe = re.sub(r"[^\w.\-]+", "_", entry.name).strip("_") or "pump"
        path = path / f"{safe}{CURVE_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entry_to_dict(entry), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #
def _same_density(a: Fluid, b: Fluid) -> bool:
    ra = float(a.density.to("kg/m**3").magnitude)
    rb = float(b.density.to("kg/m**3").magnitude)
    return abs(ra - rb) <= 1e-9 * max(abs(rb), 1.0)


def _score(entry, adapted, adaptation, value, trim_margin, notes, duty_q, por):
    q_bep, _h, _eta = adapted.bep()
    q_bep_val = float(q_bep.to("m**3/h").magnitude)
    q_val = float(duty_q.to("m**3/h").magnitude)
    ratio = q_val / q_bep_val if q_bep_val > 0.0 else float("inf")
    por_min, por_max = por
    in_por = True if por_min is None or por_max is None else por_min <= ratio <= por_max
    notes = list(notes)
    if not in_por:
        notes.append(
            f"Q/Q_BEP = {ratio:.2f} is outside the preferred operating region "
            f"[{por_min:g}, {por_max:g}]"
        )
    try:
        power = adapted.predict_breaking_power(duty_q).to("kW")
    except (AttributeError, ValueError):
        power = None
    return Candidate(
        entry=entry,
        adaptation=adaptation,
        curve=adapted,
        value=value,
        eta_at_duty=adapted.predict_efficiency(duty_q).to("percent"),
        power_at_duty=power,
        q_over_qbep=ratio,
        in_por=in_por,
        trim_margin=trim_margin,
        reasons=tuple(notes),
    )


def _evaluate(entry, duty_q, duty_h, fluid, allow_speed, allow_trim, por, as_is_tol):
    cands: List[Candidate] = []
    rej: List[Rejection] = []
    name = entry.name
    if not entry.has_efficiency:
        return cands, [
            Rejection(
                name,
                "-",
                "no efficiency / power data on the curve: it cannot be ranked",
            )
        ]
    q_val = float(duty_q.to("m**3/h").magnitude)
    h_val = float(duty_h.to("m").magnitude)

    curve = entry.curve
    if fluid is not None and not _same_density(curve.fluid, fluid):
        try:
            curve = curve.to_fluid(fluid)
        except Exception as exc:
            return cands, [Rejection(name, "-", f"fluid change failed: {exc}")]

    caps = curve.fitter.capacities
    q_lo, q_hi = float(min(caps)), float(max(caps))
    as_is_note = None
    if q_lo <= q_val <= q_hi:
        h_pred = float(curve.predict_head(duty_q).to("m").magnitude)
        err = (h_pred - h_val) / h_val
        if abs(err) <= as_is_tol:
            cands.append(_score(entry, curve, "as-is", None, None, (), duty_q, por))
        else:
            as_is_note = (
                f"the curve gives {h_pred:.2f} m at {q_val:g} m3/h "
                f"({err:+.1%} vs the {h_val:g} m duty)"
            )
    else:
        as_is_note = (
            f"duty capacity {q_val:g} m3/h is outside the tested range "
            f"[{q_lo:g}, {q_hi:g}] m3/h"
        )
    if cands:  # the curve already serves the duty: adaptations would be no-ops
        return cands, rej

    # --- speed (VFD) ------------------------------------------------------- #
    if allow_speed:
        try:
            q1 = affinity_intersection(curve, duty_q, duty_h)
        except ValueError as exc:
            rej.append(Rejection(name, "speed", str(exc)))
        else:
            n_new = entry.speed * (q_val / float(q1.to("m**3/h").magnitude))
            n_rpm = float(n_new.to("rpm").magnitude)
            bad = None
            if entry.speed_range is not None:
                lo = float(entry.speed_range[0].to("rpm").magnitude)
                hi = float(entry.speed_range[1].to("rpm").magnitude)
                if n_rpm < lo * (1 - 1e-9) or n_rpm > hi * (1 + 1e-9):
                    bad = (
                        f"requires {n_rpm:.0f} rpm, outside the allowed speed "
                        f"range [{lo:g}, {hi:g}] rpm"
                    )
            if bad:
                rej.append(Rejection(name, "speed", bad))
            else:
                adapted = curve.to_speed(n_new)
                cands.append(
                    _score(entry, adapted, "speed", n_new, None, (), duty_q, por)
                )

    # --- impeller trim ----------------------------------------------------- #
    if allow_trim:
        if entry.diameter is None:
            rej.append(Rejection(name, "trim", "the entry has no impeller diameter"))
        else:
            try:
                d_new = diameter_for_duty(curve, duty_q, duty_h, entry.diameter)
            except ValueError as exc:
                rej.append(Rejection(name, "trim", str(exc)))
            else:
                d_mm = float(d_new.to("mm").magnitude)
                ref_mm = float(entry.diameter.to("mm").magnitude)
                max_mm = (
                    float(entry.d_max.to("mm").magnitude)
                    if entry.d_max is not None
                    else ref_mm
                )
                min_mm = (
                    float(entry.d_min.to("mm").magnitude)
                    if entry.d_min is not None
                    else None
                )
                if d_mm > max_mm * (1 + 1e-9):
                    rej.append(
                        Rejection(
                            name,
                            "trim",
                            f"requires D = {d_mm:.1f} mm, above the maximum "
                            f"{max_mm:g} mm",
                        )
                    )
                elif min_mm is not None and d_mm < min_mm * (1 - 1e-9):
                    rej.append(
                        Rejection(
                            name,
                            "trim",
                            f"requires D = {d_mm:.1f} mm, below the minimum "
                            f"{min_mm:g} mm",
                        )
                    )
                else:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        adapted = curve.to_diameter(d_new, entry.diameter)
                    notes = [
                        str(w.message)
                        for w in caught
                        if issubclass(w.category, UserWarning)
                    ]
                    cands.append(
                        _score(
                            entry,
                            adapted,
                            "trim",
                            Q_(d_mm, "mm"),
                            max_mm / d_mm - 1.0,
                            notes,
                            duty_q,
                            por,
                        )
                    )

    if not cands and as_is_note:
        rej.append(Rejection(name, "as-is", as_is_note))
    return cands, rej


def _rank_key(c: Candidate):
    eta = float(c.eta_at_duty.to("percent").magnitude)
    return (
        not c.in_por,
        -round(eta, 4),
        round(abs(1.0 - c.q_over_qbep), 4),
        c.entry.name,
        _ADAPT_ORDER.get(c.adaptation, 9),
    )


class Catalogue:
    """A set of :class:`CatalogueEntry` (sorted by name).

    ``load_errors`` lists the files :meth:`from_folder` could not read
    (``"<file>: <message>"``); they never abort the load.
    """

    def __init__(self, entries=(), load_errors=()):
        self.entries: Tuple[CatalogueEntry, ...] = tuple(
            sorted(entries, key=lambda e: e.name)
        )
        self.load_errors: List[str] = list(load_errors)

    # ------------------------------------------------------------ loaders
    @staticmethod
    def load_file(path) -> CatalogueEntry:
        """Load one ``*.pumpcurve.json`` file (see :func:`load_entry`)."""
        return load_entry(path)

    @classmethod
    def from_folder(cls, path) -> "Catalogue":
        """Load every ``*.pumpcurve.json`` file of a folder.

        Raises
        ------
        FileNotFoundError
            If ``path`` is not a directory.
        """
        folder = Path(path)
        if not folder.is_dir():
            raise FileNotFoundError(f"Catalogue folder not found: {folder}")
        entries, errors = [], []
        for file in sorted(folder.glob(f"*{CURVE_SUFFIX}")):
            try:
                entries.append(load_entry(file))
            except ValueError as exc:
                errors.append(str(exc))
        return cls(entries, errors)

    # --------------------------------------------------------------- misc
    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    @property
    def names(self) -> List[str]:
        return [e.name for e in self.entries]

    # ---------------------------------------------------------- selection
    def select(
        self,
        duty_q: Q_,
        duty_h: Q_,
        fluid: Optional[Fluid] = None,
        allow_speed: bool = True,
        allow_trim: bool = True,
        criteria: Optional[AcceptanceCriteria] = None,
        as_is_tol: float = 0.01,
    ) -> SelectionResult:
        """Rank the catalogue pumps that can serve the duty.

        Parameters
        ----------
        duty_q, duty_h : Q_
            Duty capacity and differential head (any compatible units).
        fluid : Fluid, optional
            Duty fluid.  When its density differs from an entry's fluid the curve
            is converted with ``to_fluid`` (same head, power rescaled).  The
            viscosity correction is not applied.
        allow_speed, allow_trim : bool
            Which adaptations may be used (VFD speed, impeller trim).
        criteria : AcceptanceCriteria, optional
            Source of the preferred-operating-region bounds
            (``criteria.selection``); default ``AcceptanceCriteria.default()``.
        as_is_tol : float
            An entry counts as serving the duty "as-is" when its head at the duty
            capacity is within this fraction of the duty head (selection
            heuristic, not a standard tolerance).

        Returns
        -------
        SelectionResult
            Ranked candidates (best first); possibly empty, in which case
            ``.reasons`` says why each entry was refused.

        Raises
        ------
        ValueError
            If the duty capacity or head is not positive.
        """
        q_val = float(duty_q.to("m**3/h").magnitude)
        h_val = float(duty_h.to("m").magnitude)
        if not q_val > 0.0 or not h_val > 0.0:
            raise ValueError("The duty capacity and head must both be > 0.")
        crit = criteria if criteria is not None else AcceptanceCriteria.default()
        por = (crit.selection.por_min, crit.selection.por_max)

        found: List[Candidate] = []
        rejected: List[Rejection] = []
        for entry in self.entries:
            cands, rej = _evaluate(
                entry, duty_q, duty_h, fluid, allow_speed, allow_trim, por, as_is_tol
            )
            found.extend(cands)
            rejected.extend(rej)
        if not self.entries:
            rejected.append(Rejection("-", "-", "the catalogue has no entries"))
        found.sort(key=_rank_key)
        return SelectionResult(found, rejected)
