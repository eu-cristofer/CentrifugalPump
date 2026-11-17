"""
acceptance
==========

Edition-aware acceptance criteria (tolerance tables) for pump performance
verification.

The numbers live in TOML files under ``pump/standards/`` (one file per standard,
one table per edition) so they can be reviewed and corrected without touching
code.  A *client overlay* (``pump/standards/clients/*.toml``) may replace any
subset of the keys of an edition.

Each edition table carries ``verified`` and a ``source`` naming the clauses it
was checked against.  A verified table may still list ``unverified_parts`` (keys
the standard text does not settle); :attr:`AcceptanceCriteria.unverified` lists
every part that still needs confirmation.  Tool settings such as the shut-off
extrapolation threshold are not standard values and are never listed.

Efficiency is **not a rated value** in API 610 (8th ed. Table 4-2 note; 11th and
12th ed. Table 16 note c): an edition without ``efficiency_tol_minus`` reports
efficiency for information only.  A purchaser-specified efficiency tolerance is
entered as an override (or by a client overlay).

Tolerance bands are keyed on the **rated differential head** (including the
shut-off band, which is selected by the rated head, not by the shut-off head).

Examples
--------
>>> from pump import Q_
>>> from pump.acceptance import AcceptanceCriteria
>>> crit = AcceptanceCriteria.default()
>>> crit.key
'api610:12'
>>> crit.head_tolerance(Q_(73, "m"))
(0.03, 0.03)
>>> crit.shutoff_tolerance(Q_(73, "m"))
(0.1, 0.1)
>>> crit.shutoff_tolerance(Q_(400, "m"))
(0.05, 0.05)
>>> crit.npsh.configured
False
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional

from .mechanical_run import MechanicalRunCriteria
from .npsh import NPSHCriteria
from .utilities.unit_conversion import Q_

__all__ = [
    "AcceptanceCriteria",
    "CheckRow",
    "PerformanceVerdict",
    "SelectionCriteria",
    "deviation",
    "evaluate_performance",
    "head_rises_to_shutoff",
]

_STD_DIR = Path(__file__).parent / "standards"
_CLIENT_DIR = _STD_DIR / "clients"

# Overridable keys -> human-readable part names (used for ``unverified``).
_PARTS = {
    "head_bands": "head tolerance bands",
    "shutoff_bands": "shut-off tolerance bands",
    "power_tol_plus": "power tolerance",
    "efficiency_tol_minus": "efficiency tolerance",
    "parallel_shutoff_min_ratio": "parallel-operation shut-off ratio",
    "shutoff_extrapolation_q_fraction": "shut-off extrapolation threshold",
    "test_speed_tol": "test speed tolerance",
}

# Tool settings: kept in the tables (and overridable) but they are not standard
# values, so they are never reported as "unverified".
_TOOL_SETTINGS = {"shutoff_extrapolation_q_fraction"}

# The ``mechanical_run`` sub-table is merged key by key (not replaced wholesale).
_MR_PART = "mechanical running test limits"

# The ``npsh`` sub-table is merged key by key as well.
_NPSH_PART_UNCONFIGURED = "NPSH margin rule (not configured)"
_NPSH_PART = "NPSH margin rule"

# The ``selection`` sub-table (preferred operating region) is merged key by key too.
_SELECTION_PART = "preferred operating region (pump selection)"

_DEFAULT_KEY = "api610:12"


@lru_cache(maxsize=None)
def _read_toml(path: str) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _merge_sub(base: Optional[dict], overlay: Mapping, overlay_label: str) -> dict:
    """Overlay a sub-table key by key, keeping *both* sources (base | overlay)."""
    merged = {**(base or {}), **overlay}
    base_src = (base or {}).get("source", "")
    over_src = overlay.get("source", "")
    if base_src and over_src:
        merged["source"] = f"{base_src} | {overlay_label}: {over_src}"
    return merged


def _edition_sort_key(edition: str):
    return (0, int(edition)) if edition.isdigit() else (1, edition)


def _standards() -> dict:
    """``{key: (edition_table, standard_title)}`` for every shipped edition."""
    found = {}
    for path in sorted(Path(_STD_DIR).glob("*.toml")):
        data = _read_toml(str(path))
        standard = data["standard"]
        title = data.get("title", standard)
        for edition, table in data.get("editions", {}).items():
            found[f"{standard}:{edition}"] = (table, title)
    return found


def _client_overlays() -> dict:
    """``{client: overlay_table}`` for every shipped client overlay."""
    found = {}
    for path in sorted(Path(_CLIENT_DIR).glob("*.toml")):
        data = _read_toml(str(path))
        found[data.get("client", path.stem)] = data
    return found


def _parse_quantity(text) -> Q_:
    """Parse ``"75 m"`` / ``"inf m"`` into a Pint quantity."""
    number, unit = str(text).split(None, 1)
    return Q_(float(number), unit.strip())


def _parse_bands(raw) -> tuple:
    bands = [
        (
            _parse_quantity(b["max_rated_head"]),
            float(b["tol_minus"]),
            float(b["tol_plus"]),
        )
        for b in raw
    ]
    bands.sort(key=lambda band: band[0].to("m").magnitude)
    return tuple(bands)


def _band_for(bands: tuple, rated_head) -> tuple:
    """Tolerances of the first band whose limit is >= ``rated_head``."""
    for max_head, minus, plus in bands:
        if rated_head <= max_head:
            return (minus, plus)
    return (bands[-1][1], bands[-1][2])


@dataclass(frozen=True)
class SelectionCriteria:
    """
    Preferred operating region (POR) used by pump selection (UC-01).

    Attributes
    ----------
    por_min, por_max : float or None
        POR bounds as fractions of the best-efficiency flow (``Q / Q_BEP``).
        ``None`` = not configured (no POR constraint).
    source : str
        Provenance of the bounds.
    verified : bool
        True only when checked against the standard text.

    Examples
    --------
    >>> SelectionCriteria().configured
    False
    >>> SelectionCriteria.from_table({"por_min": 0.7, "por_max": 1.2}).configured
    True
    """

    por_min: Optional[float] = None
    por_max: Optional[float] = None
    source: str = "not configured"
    verified: bool = False

    @property
    def configured(self) -> bool:
        """True when both bounds are set."""
        return self.por_min is not None and self.por_max is not None

    @classmethod
    def from_table(cls, table: Optional[Mapping]) -> "SelectionCriteria":
        """Build from a TOML ``selection`` table (missing bounds stay ``None``)."""
        table = table or {}
        por_min = table.get("por_min")
        por_max = table.get("por_max")
        por_min = float(por_min) if por_min is not None else None
        por_max = float(por_max) if por_max is not None else None
        if por_min is not None and por_max is not None and not por_min < por_max:
            raise ValueError("selection: por_min must be smaller than por_max.")
        return cls(
            por_min=por_min,
            por_max=por_max,
            source=str(table.get("source", "not configured")),
            verified=bool(table.get("verified", False)),
        )


@dataclass(frozen=True)
class AcceptanceCriteria:
    """
    Tolerance tables for one standard edition, optionally overlaid by a client.

    Attributes
    ----------
    key : str
        ``"<standard>:<edition>"``, e.g. ``"api610:12"``.
    label, source : str
        Display label and provenance of the numbers.
    verified : bool
        True only if the base edition *and* the overlay (if any) are verified.
    client, client_label : str or None
        Overlay id and display label.
    head_bands, shutoff_bands : tuple of (max_rated_head, tol_minus, tol_plus)
        Sorted by ``max_rated_head`` (a Pint quantity; may be infinite).
    power_tol_plus : float
        Maximum allowed positive power deviation.
    efficiency_tol_minus : float or None
        Maximum allowed negative (relative) efficiency deviation, or ``None``
        when efficiency is not a rated value (information only).
    parallel_shutoff_min_ratio : float
        Minimum shut-off head / rated head for parallel operation.
    shutoff_extrapolation_q_fraction : float
        If no test point lies below this fraction of rated capacity, the
        shut-off head is considered extrapolated.
    test_speed_tol : float or None
        Allowed relative difference between test and rated speed (API 610:
        within 3 % unless otherwise agreed); ``None`` = not checked.
    unverified : tuple of str
        Human-readable names of the parts not verified against the standard.
    mechanical_run : MechanicalRunCriteria
        Mechanical running test limits (minimum duration, vibration limits).
    npsh : NPSHCriteria
        NPSH margin rule (shipped *not configured*: no limits).
    selection : SelectionCriteria
        Preferred operating region used by pump selection (unverified seed).
    """

    key: str
    label: str
    source: str
    verified: bool
    client: Optional[str]
    client_label: Optional[str]
    head_bands: tuple
    shutoff_bands: tuple
    power_tol_plus: float
    efficiency_tol_minus: Optional[float]
    parallel_shutoff_min_ratio: float
    shutoff_extrapolation_q_fraction: float
    unverified: tuple
    test_speed_tol: Optional[float] = None
    mechanical_run: MechanicalRunCriteria = field(default_factory=MechanicalRunCriteria)
    npsh: NPSHCriteria = field(default_factory=NPSHCriteria)
    selection: SelectionCriteria = field(default_factory=SelectionCriteria)

    # ------------------------------------------------------------ discovery
    @staticmethod
    def available() -> list:
        """``[(key, label), ...]`` for every shipped edition, sorted."""
        items = []
        for key, (table, _title) in _standards().items():
            standard, edition = key.split(":", 1)
            items.append(((standard, _edition_sort_key(edition)), key, table["label"]))
        items.sort(key=lambda item: item[0])
        return [(key, label) for _sort, key, label in items]

    @staticmethod
    def clients() -> list:
        """``[(client, label), ...]`` for every shipped client overlay."""
        return [
            (client, data.get("label", client))
            for client, data in sorted(_client_overlays().items())
        ]

    # ---------------------------------------------------------------- loaders
    @classmethod
    def load(
        cls, key: str = _DEFAULT_KEY, client: Optional[str] = None
    ) -> "AcceptanceCriteria":
        """
        Load an edition, optionally merged with a client overlay.

        The overlay replaces only the keys it defines.  ``verified`` is True
        only if both the base and the overlay are verified.

        Raises
        ------
        KeyError
            Unknown edition key or client (the message lists the available ones).
        """
        standards = _standards()
        norm = str(key).strip().lower()
        if norm not in standards:
            raise KeyError(
                f"Unknown acceptance criteria {key!r}; available: {sorted(standards)}"
            )
        base, _title = standards[norm]
        merged = {k: base[k] for k in _PARTS if k in base}
        mr_table = dict(base["mechanical_run"]) if "mechanical_run" in base else None
        npsh_table = dict(base["npsh"]) if "npsh" in base else None
        sel_table = dict(base["selection"]) if "selection" in base else None
        verified = bool(base.get("verified", False))
        source = base.get("source", "")
        client_label = None
        overlay_unverified = None
        mr_overridden = False
        npsh_overridden = False
        sel_overridden = False

        if client:
            overlays = _client_overlays()
            cname = str(client).strip().lower()
            if cname not in overlays:
                raise KeyError(
                    f"Unknown client overlay {client!r}; available: {sorted(overlays)}"
                )
            overlay = overlays[cname]
            client_label = overlay.get("label", cname)
            overlay_verified = bool(overlay.get("verified", False))
            for k in _PARTS:
                if k in overlay:
                    merged[k] = overlay[k]
            # A merged sub-table is verified only when every layer that
            # contributes to it is: a verified overlay that adds one rule must
            # not hide the base edition's own unverified values.
            if "mechanical_run" in overlay:
                base_ok = mr_table is None or bool(mr_table.get("verified", False))
                mr_table = _merge_sub(mr_table, overlay["mechanical_run"], client_label)
                mr_overridden = overlay_verified and base_ok
                mr_table["verified"] = mr_overridden
            if "npsh" in overlay:
                base_ok = npsh_table is None or bool(npsh_table.get("verified", False))
                npsh_table = _merge_sub(npsh_table, overlay["npsh"], client_label)
                npsh_overridden = overlay_verified and base_ok
                npsh_table["verified"] = npsh_overridden
            if "selection" in overlay:
                base_ok = sel_table is None or bool(sel_table.get("verified", False))
                sel_table = _merge_sub(sel_table, overlay["selection"], client_label)
                sel_overridden = overlay_verified and base_ok
                sel_table["verified"] = sel_overridden
            verified = verified and overlay_verified
            if overlay.get("source"):
                source = f"{source} | {client_label}: {overlay['source']}"
            if not overlay_verified:
                overlay_unverified = client_label
            overridden_verified = {
                k for k in _PARTS if k in overlay and overlay_verified
            }
            client = cname
        else:
            overridden_verified = set()
            client = None

        npsh_criteria = (
            NPSHCriteria.from_table(npsh_table)
            if npsh_table is not None
            else NPSHCriteria()
        )

        unverified = []
        base_open = (
            set(merged)  # every part the tables define
            if not base.get("verified", False)
            else set(base.get("unverified_parts", ()))
        )
        unverified += [
            name
            for k, name in _PARTS.items()
            if k in base_open
            and k in merged
            and k not in overridden_verified
            and k not in _TOOL_SETTINGS
        ]
        if mr_table is not None and not (
            mr_overridden or mr_table.get("verified", False)
        ):
            unverified.append(_MR_PART)
        if npsh_table is not None and not (
            npsh_overridden or npsh_table.get("verified", False)
        ):
            unverified.append(
                _NPSH_PART if npsh_criteria.configured else _NPSH_PART_UNCONFIGURED
            )
        if sel_table is not None and not (
            sel_overridden or sel_table.get("verified", False)
        ):
            unverified.append(_SELECTION_PART)
        if overlay_unverified:
            unverified.append(overlay_unverified)

        return cls(
            key=norm,
            label=base["label"],
            source=source,
            verified=verified,
            client=client,
            client_label=client_label,
            head_bands=_parse_bands(merged["head_bands"]),
            shutoff_bands=_parse_bands(merged["shutoff_bands"]),
            power_tol_plus=float(merged["power_tol_plus"]),
            efficiency_tol_minus=(
                float(merged["efficiency_tol_minus"])
                if merged.get("efficiency_tol_minus") is not None
                else None
            ),
            parallel_shutoff_min_ratio=float(merged["parallel_shutoff_min_ratio"]),
            shutoff_extrapolation_q_fraction=float(
                merged["shutoff_extrapolation_q_fraction"]
            ),
            unverified=tuple(unverified),
            test_speed_tol=(
                float(merged["test_speed_tol"])
                if merged.get("test_speed_tol") is not None
                else None
            ),
            mechanical_run=(
                MechanicalRunCriteria.from_table(mr_table)
                if mr_table is not None
                else MechanicalRunCriteria()
            ),
            npsh=npsh_criteria,
            selection=(
                SelectionCriteria.from_table(sel_table)
                if sel_table is not None
                else SelectionCriteria()
            ),
        )

    @classmethod
    def default(cls) -> "AcceptanceCriteria":
        """The default criteria (``api610:12``, no client overlay)."""
        return cls.load(_DEFAULT_KEY)

    @property
    def performance_unverified(self) -> tuple:
        """The unverified parts that bear on the performance-test verdict.

        Excludes the mechanical run, NPSH and selection parts (each has its own
        verdict) so an open mechanical-run item does not make the performance
        verdict provisional.
        """
        perf = set(_PARTS.values()) | {self.client_label}
        return tuple(item for item in self.unverified if item in perf)

    # ------------------------------------------------------------ tolerances
    def head_tolerance(self, rated_head) -> tuple:
        """``(minus, plus)`` head tolerance for a rated differential head."""
        return _band_for(self.head_bands, rated_head)

    def shutoff_tolerance(self, rated_head) -> tuple:
        """
        ``(minus, plus)`` shut-off head tolerance.

        Keyed by the **rated differential head** (not by the shut-off head).
        """
        return _band_for(self.shutoff_bands, rated_head)

    @staticmethod
    def deviation(rated, predicted) -> float:
        """Alias of the module-level :func:`deviation`."""
        return deviation(rated, predicted)


def deviation(rated, predicted) -> float:
    """Relative deviation ``(predicted - rated) / rated``.

    The single deviation formula used by the library checker and the workbench
    (review finding F-05).  Accepts Pint quantities or plain numbers.

    Examples
    --------
    >>> round(deviation(100.0, 103.0), 6)
    0.03
    """
    ratio = (predicted - rated) / rated
    if hasattr(ratio, "to"):
        return float(ratio.to("dimensionless").magnitude)
    return float(ratio)


def head_rises_to_shutoff(predict_head, rated_q, samples: int = 60) -> bool:
    """True when the head rises continuously from ``rated_q`` back to shut-off.

    API 610 (8th ed. Table 4-2 note a; 11th/12th ed. Table 16 note a): when a
    rising head-flow curve is specified, the *negative* shut-off tolerance is
    allowed only if the test curve still shows a rising characteristic.
    ``predict_head`` is a callable ``Q -> head`` (e.g. ``curve.predict_head``).

    Examples
    --------
    >>> from pump import Q_
    >>> falling = lambda q: Q_(100.0 - 0.1 * q.to("m**3/h").magnitude ** 2, "m")
    >>> head_rises_to_shutoff(falling, Q_(20, "m**3/h"))
    True
    >>> drooping = lambda q: Q_(100.0 + q.to("m**3/h").magnitude
    ...                         - 0.1 * q.to("m**3/h").magnitude ** 2, "m")
    >>> head_rises_to_shutoff(drooping, Q_(20, "m**3/h"))
    False
    """
    q_max = float(rated_q.to("m**3/h").magnitude)
    heads = [
        float(predict_head(Q_(q_max * i / samples, "m**3/h")).to("m").magnitude)
        for i in range(samples + 1)
    ]
    # Head must not increase with flow anywhere on [0, Q_rated].
    return all(b <= a + 1e-9 for a, b in zip(heads, heads[1:]))


# --------------------------------------------------------------------------- #
# The performance verdict: one engine for the library and the workbench
# --------------------------------------------------------------------------- #
PASS, FAIL, INFO, NOT_EVALUATED = "pass", "fail", "info", "not evaluated"

_TOL_EPS = 1e-9


@dataclass(frozen=True)
class CheckRow:
    """
    One acceptance check at the rated point.

    ``status`` is ``"pass"``, ``"fail"``, ``"info"`` (reported, not judged) or
    ``"not evaluated"`` (required but the data or the prediction is missing;
    the verdict is then not an approval).  Quantities keep the units of the
    rated value; ``deviation`` and ``tolerance`` are fractions.
    """

    name: str
    rated: Optional[Q_]
    predicted: Optional[Q_]
    minimum: Optional[Q_]
    maximum: Optional[Q_]
    deviation: Optional[float]
    tolerance: Optional[float]
    status: str
    extrapolated: bool = False
    note: str = ""

    @property
    def judged(self) -> bool:
        """True for rows that take part in the verdict."""
        return self.status != INFO


@dataclass(frozen=True)
class PerformanceVerdict:
    """
    Outcome of :func:`evaluate_performance`.

    ``passed`` means no judged row failed; ``complete`` means every required
    row could be evaluated.  ``approved`` is ``passed and complete``.
    """

    rows: tuple
    criteria: "AcceptanceCriteria"
    parallel_ok: Optional[bool] = None

    @property
    def passed(self) -> bool:
        return not any(r.status == FAIL for r in self.rows)

    @property
    def complete(self) -> bool:
        return not any(r.status == NOT_EVALUATED for r in self.rows)

    @property
    def approved(self) -> bool:
        return self.passed and self.complete

    @property
    def not_evaluated(self) -> tuple:
        return tuple(r.name for r in self.rows if r.status == NOT_EVALUATED)

    def row(self, name: str) -> Optional[CheckRow]:
        return next((r for r in self.rows if r.name == name), None)


def _band(override: Optional[float], default: tuple) -> tuple:
    """``(minus, plus)``: the criteria band, or a symmetric user override."""
    if override is None or abs(override - default[1]) <= _TOL_EPS:
        return default
    return (override, override)


def _limit(value: Q_) -> Q_:
    """Limits are rounded to 2 decimals in the rated value's unit."""
    return Q_(round(float(value.magnitude), 2), value.units)


def _try_predict(fn, q):
    try:
        return fn(q), ""
    except Exception as exc:  # reported as "not evaluated", never swallowed
        return None, f"cannot predict: {type(exc).__name__}: {exc}"


def evaluate_performance(
    curve,
    rated_q: Q_,
    rated_head: Q_,
    criteria: "AcceptanceCriteria",
    *,
    rated_power: Optional[Q_] = None,
    rated_efficiency: Optional[Q_] = None,
    rated_shutoff: Optional[Q_] = None,
    parallel_operation: bool = False,
    rated_speed: Optional[Q_] = None,
    test_speeds: tuple = (),
    tolerances: Optional[Mapping] = None,
) -> PerformanceVerdict:
    """
    Judge a fitted, corrected performance curve at the rated point.

    The single implementation of the API 610 performance verdict, used by
    :class:`pump.PerformanceChecker` and by the workbench's Compliance node.

    Checks (deviation ``(predicted - rated) / rated``):

    - **Head**: inside the band chosen by the rated head.
    - **Power**: ``<= +power_tol_plus`` (when a rated power is given).
    - **Efficiency**: ``>= -tol`` only when a tolerance exists (criteria or
      ``tolerances["efficiency"]``); otherwise ``info``.
    - **Shutoff Head**: inside the shut-off band (chosen by the rated head);
      with ``parallel_operation`` (rising curve specified) the negative side
      is allowed only if :func:`head_rises_to_shutoff`.
    - **Parallel operation**: shut-off / rated head ``>= parallel_shutoff_min_ratio``
      and a rising curve (only when ``parallel_operation``).
    - **Test speed**: every tested speed within ``test_speed_tol`` of the rated
      speed (when both are given and the criteria define the tolerance).

    ``tolerances`` overrides the criteria: ``{"head", "shutoff", "power",
    "efficiency"}`` fractions (a head/shut-off override replaces the band by a
    symmetric one; ``efficiency=None`` means information only).

    Examples
    --------
    >>> from pump import Q_
    >>> crit = AcceptanceCriteria.load("api610:8")
    >>> head = lambda q: Q_(357.0 - 0.18 * q.to("m**3/h").magnitude ** 2, "m")
    >>> class Curve:
    ...     predict_head = staticmethod(head)
    ...     def predict_breaking_power(self, q): return Q_(24.6, "kW")
    ...     def predict_efficiency(self, q): return Q_(36.8, "percent")
    ...     points = ()
    >>> v = evaluate_performance(Curve(), Q_(9.8, "m**3/h"), Q_(333.8, "m"), crit,
    ...     rated_power=Q_(26.9, "kW"), rated_efficiency=Q_(32.7, "percent"),
    ...     rated_speed=Q_(10212, "rpm"), test_speeds=(Q_(10301, "rpm"),))
    >>> [(r.name, r.status) for r in v.rows]
    [('Head', 'pass'), ('Power', 'pass'), ('Efficiency', 'info'), ('Test speed', 'pass')]
    >>> v.approved
    True
    """
    tol = dict(tolerances or {})
    rows = []

    # --- Head -------------------------------------------------------------
    h_minus, h_plus = _band(tol.get("head"), criteria.head_tolerance(rated_head))
    pred_h, why = _try_predict(curve.predict_head, rated_q)
    if pred_h is None:
        rows.append(
            CheckRow(
                "Head",
                rated_head,
                None,
                None,
                None,
                None,
                h_plus,
                NOT_EVALUATED,
                note=why,
            )
        )
    else:
        pred_h = pred_h.to(rated_head.units)
        d = deviation(rated_head, pred_h)
        ok = -h_minus - _TOL_EPS <= d <= h_plus + _TOL_EPS
        rows.append(
            CheckRow(
                "Head",
                rated_head,
                pred_h,
                _limit(rated_head * (1 - h_minus)),
                _limit(rated_head * (1 + h_plus)),
                d,
                h_plus,
                PASS if ok else FAIL,
            )
        )

    # --- Power ------------------------------------------------------------
    if rated_power is not None:
        p_tol = tol.get("power", criteria.power_tol_plus)
        pred_p, why = _try_predict(curve.predict_breaking_power, rated_q)
        if pred_p is None:
            rows.append(
                CheckRow(
                    "Power",
                    rated_power,
                    None,
                    None,
                    None,
                    None,
                    p_tol,
                    NOT_EVALUATED,
                    note=why,
                )
            )
        else:
            pred_p = pred_p.to(rated_power.units)
            d = deviation(rated_power, pred_p)
            rows.append(
                CheckRow(
                    "Power",
                    rated_power,
                    pred_p,
                    None,
                    _limit(rated_power * (1 + p_tol)),
                    d,
                    p_tol,
                    PASS if d <= p_tol + _TOL_EPS else FAIL,
                )
            )

    # --- Efficiency (information only unless a tolerance exists) -----------
    if rated_efficiency is not None:
        e_tol = (
            tol["efficiency"] if "efficiency" in tol else criteria.efficiency_tol_minus
        )
        pred_e, why = _try_predict(curve.predict_efficiency, rated_q)
        if pred_e is None:
            rows.append(
                CheckRow(
                    "Efficiency",
                    rated_efficiency,
                    None,
                    None,
                    None,
                    None,
                    e_tol,
                    INFO if e_tol is None else NOT_EVALUATED,
                    note=why,
                )
            )
        else:
            pred_e = pred_e.to(rated_efficiency.units)
            d = deviation(rated_efficiency, pred_e)
            if e_tol is None:
                rows.append(
                    CheckRow(
                        "Efficiency",
                        rated_efficiency,
                        pred_e,
                        None,
                        None,
                        d,
                        None,
                        INFO,
                        note="information only: efficiency is not a rated value in API 610",
                    )
                )
            else:
                rows.append(
                    CheckRow(
                        "Efficiency",
                        rated_efficiency,
                        pred_e,
                        _limit(rated_efficiency * (1 - e_tol)),
                        None,
                        d,
                        e_tol,
                        PASS if d >= -e_tol - _TOL_EPS else FAIL,
                    )
                )

    # --- Shut-off head ------------------------------------------------------
    zero = Q_(0, "m**3/h")
    q_floor = criteria.shutoff_extrapolation_q_fraction * rated_q
    points = getattr(curve, "points", ()) or ()
    extrapolated = bool(points) and not any(p.capacity < q_floor for p in points)
    rising = None
    if rated_shutoff is not None or parallel_operation:
        try:
            rising = head_rises_to_shutoff(curve.predict_head, rated_q)
        except Exception:
            rising = None
    if rated_shutoff is not None:
        s_minus, s_plus = _band(
            tol.get("shutoff"), criteria.shutoff_tolerance(rated_head)
        )
        pred_s, why = _try_predict(curve.predict_head, zero)
        if pred_s is None:
            rows.append(
                CheckRow(
                    "Shutoff Head",
                    rated_shutoff,
                    None,
                    None,
                    None,
                    None,
                    s_plus,
                    NOT_EVALUATED,
                    note=why,
                )
            )
        else:
            pred_s = pred_s.to(rated_shutoff.units)
            d = deviation(rated_shutoff, pred_s)
            ok = -s_minus - _TOL_EPS <= d <= s_plus + _TOL_EPS
            note = ""
            if ok and d < 0 and parallel_operation and rising is not True:
                ok = False
                note = (
                    "negative tolerance not allowed: the curve does not rise "
                    "to shut-off"
                )
            rows.append(
                CheckRow(
                    "Shutoff Head",
                    rated_shutoff,
                    pred_s,
                    _limit(rated_shutoff * (1 - s_minus)),
                    _limit(rated_shutoff * (1 + s_plus)),
                    d,
                    s_plus,
                    PASS if ok else FAIL,
                    extrapolated=extrapolated,
                    note=note,
                )
            )

    # --- Parallel operation -------------------------------------------------
    parallel_ok = None
    if parallel_operation:
        pred_s, why = _try_predict(curve.predict_head, zero)
        ratio_min = criteria.parallel_shutoff_min_ratio
        if pred_s is None or rising is None:
            rows.append(
                CheckRow(
                    "Parallel operation",
                    None,
                    None,
                    None,
                    None,
                    None,
                    ratio_min - 1,
                    NOT_EVALUATED,
                    note=why or "cannot evaluate the rising curve",
                )
            )
        else:
            ratio = float((pred_s / rated_head).to("dimensionless").magnitude)
            parallel_ok = bool(ratio >= ratio_min - _TOL_EPS and rising)
            note = "" if rising else "head does not rise continuously to shut-off"
            rows.append(
                CheckRow(
                    "Parallel operation",
                    rated_head,
                    pred_s.to(rated_head.units),
                    _limit(rated_head * ratio_min),
                    None,
                    ratio - 1,
                    ratio_min - 1,
                    PASS if parallel_ok else FAIL,
                    extrapolated=extrapolated,
                    note=note,
                )
            )

    # --- Test speed -----------------------------------------------------------
    n_tol = criteria.test_speed_tol
    speeds = [s for s in (test_speeds or ()) if s is not None]
    if rated_speed is not None and speeds and n_tol is not None:
        devs = [deviation(rated_speed, s) for s in speeds]
        worst = max(range(len(devs)), key=lambda i: abs(devs[i]))
        ok = abs(devs[worst]) <= n_tol + _TOL_EPS
        rows.append(
            CheckRow(
                "Test speed",
                rated_speed,
                speeds[worst].to(rated_speed.units),
                _limit(rated_speed * (1 - n_tol)),
                _limit(rated_speed * (1 + n_tol)),
                devs[worst],
                n_tol,
                PASS if ok else FAIL,
                note=(
                    ""
                    if ok
                    else "test speed outside the agreed band: correct only if agreed"
                ),
            )
        )

    return PerformanceVerdict(
        rows=tuple(rows), criteria=criteria, parallel_ok=parallel_ok
    )
