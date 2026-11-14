"""
acceptance
==========

Edition-aware acceptance criteria (tolerance tables) for pump performance
verification.

The numbers live in TOML files under ``pump/standards/`` (one file per standard,
one table per edition) so they can be reviewed and corrected without touching
code.  A *client overlay* (``pump/standards/clients/*.toml``) may replace any
subset of the keys of an edition.

Every table currently shipped is a **seed** copied from the pre-Sprint-5 code
defaults and is flagged ``verified = false``; :attr:`AcceptanceCriteria.unverified`
lists the parts that still need confirmation against the standard text.  The
NPSH margin rule is shipped *not configured* (no limits at all).

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
from typing import Optional

from .mechanical_run import MechanicalRunCriteria
from .npsh import NPSHCriteria
from .utilities.unit_conversion import Q_

__all__ = ["AcceptanceCriteria", "deviation"]

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
}

# The ``mechanical_run`` sub-table is merged key by key (not replaced wholesale).
_MR_PART = "mechanical running test limits"

# The ``npsh`` sub-table is merged key by key as well.
_NPSH_PART_UNCONFIGURED = "NPSH margin rule (not configured)"
_NPSH_PART = "NPSH margin rule"

_DEFAULT_KEY = "api610:12"


@lru_cache(maxsize=None)
def _read_toml(path: str) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


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
    efficiency_tol_minus : float
        Maximum allowed negative (relative) efficiency deviation.
    parallel_shutoff_min_ratio : float
        Minimum shut-off head / rated head for parallel operation.
    shutoff_extrapolation_q_fraction : float
        If no test point lies below this fraction of rated capacity, the
        shut-off head is considered extrapolated.
    unverified : tuple of str
        Human-readable names of the parts not verified against the standard.
    mechanical_run : MechanicalRunCriteria
        Mechanical running test limits (minimum duration, vibration limits).
    npsh : NPSHCriteria
        NPSH margin rule (shipped *not configured*: no limits).
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
    efficiency_tol_minus: float
    parallel_shutoff_min_ratio: float
    shutoff_extrapolation_q_fraction: float
    unverified: tuple
    mechanical_run: MechanicalRunCriteria = field(default_factory=MechanicalRunCriteria)
    npsh: NPSHCriteria = field(default_factory=NPSHCriteria)

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
        verified = bool(base.get("verified", False))
        source = base.get("source", "")
        client_label = None
        overlay_unverified = None
        mr_overridden = False
        npsh_overridden = False

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
            if "mechanical_run" in overlay:
                mr_table = {**(mr_table or {}), **overlay["mechanical_run"]}
                mr_overridden = overlay_verified
            if "npsh" in overlay:
                npsh_table = {**(npsh_table or {}), **overlay["npsh"]}
                npsh_overridden = overlay_verified
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
        if not base.get("verified", False):
            unverified += [
                name for k, name in _PARTS.items() if k not in overridden_verified
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
            efficiency_tol_minus=float(merged["efficiency_tol_minus"]),
            parallel_shutoff_min_ratio=float(merged["parallel_shutoff_min_ratio"]),
            shutoff_extrapolation_q_fraction=float(
                merged["shutoff_extrapolation_q_fraction"]
            ),
            unverified=tuple(unverified),
            mechanical_run=(
                MechanicalRunCriteria.from_table(mr_table)
                if mr_table is not None
                else MechanicalRunCriteria()
            ),
            npsh=npsh_criteria,
        )

    @classmethod
    def default(cls) -> "AcceptanceCriteria":
        """The default criteria (``api610:12``, no client overlay)."""
        return cls.load(_DEFAULT_KEY)

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
