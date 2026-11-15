"""
settings_codec
==============

Qt-free translation between node **runtime settings** (flat floats plus
``*_unit`` display-label keys, what the property dialogs read and write) and
the **v2 on-disk shape** of a ``.pumpflow`` project (``{"value", "unit"}``
quantities, UI_SPEC §6.1).

The translation happens at the persistence boundary only::

    scene.to_dict()   -> encode(kind, node.serialize_settings())
    scene.load_dict() -> decode(kind, stored_settings)

Kinds that are not in :data:`FIELDS` pass through unchanged (deep-copied).

Invariants
----------
- ``encode(kind, decode(kind, v2)) == v2`` for every document written by
  :func:`encode`.
- ``decode(kind, encode(kind, rt)) == rt`` for runtime dicts with all keys
  present.
- Magnitudes are never perturbed when the unit does not change: values are
  passed through untouched and only converted with Pint when the stored unit
  has no display label (then the canonical display unit is used).
- Optional quantities (:class:`OptDisp`, e.g. the test-bench geometry or the
  rated-point impeller diameters) are
  stored as ``null`` when unset, with no stray ``*_unit`` key; an unset value
  therefore decodes without a unit label (the dialog re-seeds its default).

Examples
--------
>>> from pumpflow.settings_codec import encode, decode
>>> rt = {"q": 833.0, "q_unit": "m³/h", "head": 73.0, "head_unit": "m"}
>>> v2 = encode("rated_point", rt)
>>> v2["q"]
{'value': 833.0, 'unit': 'm**3/h'}
>>> decode("rated_point", v2) == rt
True
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

from pump import Q_
from pump.constants import P_ATM

from . import units

__all__ = [
    "FIELDS",
    "encode",
    "decode",
    "upgrade_v1",
    "parse_standard_text",
    "ROLE_DIMENSIONS",
    "DURATION_LABELS",
    "delta_pint",
]


# ---------------------------------------------------------------------------
# Unit helpers (Pint only; no new registry)
# ---------------------------------------------------------------------------


def _norm(unit: str) -> str:
    """Normalise the compact ``%`` spelling to Pint's ``percent``."""
    return "percent" if unit == "%" else unit


@lru_cache(maxsize=None)
def _same_unit(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if a == b:
        return True
    try:
        return Q_(1, a).units == Q_(1, b).units
    except Exception:
        return False


def _convert(value, src: str, dst: str):
    """Convert ``value`` from ``src`` to ``dst``; untouched when the units agree."""
    if value is None or _same_unit(src, dst):
        return value
    return Q_(value, _norm(src)).to(_norm(dst)).magnitude


@lru_cache(maxsize=None)
def _fmt(pint_str: str) -> str:
    """Compact (``~C``) Pint spelling, as produced by ``pump.quantity_io.to_json``."""
    return format(Q_(1, pint_str).units, "~C")


def _pint(dimension: str, label: str) -> str:
    """Pint string of a display label (a bare Pint string is accepted too)."""
    try:
        return units.pint_str(dimension, label)
    except KeyError:
        return label


@lru_cache(maxsize=None)
def _disk_unit(dimension: str, label: str) -> str:
    """The unit string written to disk for a display label.

    Compact Pint spelling (as ``pump.quantity_io`` writes) when it reads back as
    the same display label; otherwise the raw Pint string.  Efficiency always
    uses the raw string (``percent`` / ``dimensionless``): the compact ``%`` is
    not stable.
    """
    raw = _pint(dimension, label)
    if dimension == "efficiency":
        return raw
    try:
        compact = _fmt(raw)
    except Exception:
        return raw
    lab = units.label_for(dimension, compact)
    if lab is not None and lab == units.label_for(dimension, raw):
        return compact
    return raw


def _atm(unit: str) -> float:
    return P_ATM.to(unit).magnitude


def _label_or_canonical(dimension: str, stored: str):
    """``(label, converted?)`` for a stored unit: its label, else canonical."""
    label = units.label_for(dimension, stored)
    if label is not None:
        return label, False
    return units.canonical_unit(dimension), True


# ---------------------------------------------------------------------------
# Field specs.  Each spec edits a (deep-copied) settings dict in place.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Disp:
    """Value with a runtime display label: ``key`` + ``unit_key`` <-> quantity."""

    key: str
    dimension: str
    unit_key: str

    def fill_v1(self, d: dict) -> None:
        if d.get(self.key) is not None and self.unit_key not in d:
            d[self.unit_key] = units.canonical_unit(self.dimension)

    def enc(self, d: dict) -> None:
        v = d.get(self.key)
        if v is None or isinstance(v, dict):
            return
        label = d.pop(self.unit_key, units.canonical_unit(self.dimension))
        d[self.key] = {"value": v, "unit": _disk_unit(self.dimension, label)}

    def dec(self, d: dict) -> None:
        q = d.get(self.key)
        if not isinstance(q, dict):
            return
        value, unit = q["value"], q["unit"]
        label = units.label_for(self.dimension, unit)
        if label is None:  # no display label: fall back to the canonical unit
            label = units.canonical_unit(self.dimension)
            value = _convert(value, unit, _pint(self.dimension, label))
        d[self.key] = value
        d[self.unit_key] = label


@dataclass(frozen=True)
class OptDisp(Disp):
    """Optional :class:`Disp`: an unset (``None``) value is **omitted** on disk.

    The ``unit_key`` is always consumed on encode, so nothing stray is left
    behind.  Omitting (rather than writing ``null``) makes a file saved with the
    field unset identical to a file written before the field existed, so
    migration and re-saving agree.  Keys absent from a document stay absent on
    decode and the runtime defaults apply.
    """

    def fill_v1(self, d: dict) -> None:
        return None

    def enc(self, d: dict) -> None:
        v = d.get(self.key)
        label = d.pop(self.unit_key, units.canonical_unit(self.dimension))
        if v is None:
            d.pop(self.key, None)
            return
        if isinstance(v, dict):
            return
        d[self.key] = {"value": v, "unit": _disk_unit(self.dimension, label)}


@dataclass(frozen=True)
class YLimDisp:
    """Optional ``[lo, hi]`` axis limits with a runtime unit label."""

    key: str
    dimension: str
    unit_key: str

    def fill_v1(self, d: dict) -> None:
        if isinstance(d.get(self.key), (list, tuple)) and self.unit_key not in d:
            d[self.unit_key] = units.canonical_unit(self.dimension)

    def enc(self, d: dict) -> None:
        v = d.get(self.key)
        # The unit key is always consumed: an unset (None) limit is stored as a
        # bare null with no stray "<key>_unit" left beside it.
        label = d.pop(self.unit_key, units.canonical_unit(self.dimension))
        if isinstance(v, (list, tuple)):
            d[self.key] = {"value": list(v), "unit": _disk_unit(self.dimension, label)}

    def dec(self, d: dict) -> None:
        q = d.get(self.key)
        if not isinstance(q, dict):
            return
        unit = q["unit"]
        label, convert = _label_or_canonical(self.dimension, unit)
        values = list(q["value"])
        if convert:
            dst = _pint(self.dimension, label)
            values = [_convert(x, unit, dst) for x in values]
        d[self.key] = values
        d[self.unit_key] = label


@dataclass(frozen=True)
class Pressures:
    """Pressures sharing one runtime unit label + g/a reference -> ``{value, unit, ref}``."""

    keys: Tuple[str, ...] = ("p_suc", "p_dis")
    unit_key: str = "p_unit"
    ref_key: str = "p_ref"

    def _present(self, d: dict):
        return [k for k in self.keys if k in d]

    def fill_v1(self, d: dict) -> None:
        if any(d.get(k) is not None for k in self.keys):
            if self.unit_key not in d:
                d[self.unit_key] = "bar"
            else:  # v1 combo data was a Pint string ("kgf/cm**2"): use its label
                d[self.unit_key] = (
                    units.label_for("pressure", d[self.unit_key]) or d[self.unit_key]
                )

    def enc(self, d: dict) -> None:
        live = [
            k
            for k in self._present(d)
            if d[k] is not None and not isinstance(d[k], dict)
        ]
        if not live:
            return
        label = d.pop(self.unit_key, "bar")
        ref = d.pop(self.ref_key, "g")
        unit = _disk_unit("pressure", label)
        for k in live:
            d[k] = {"value": d[k], "unit": unit, "ref": ref}

    def dec(self, d: dict) -> None:
        quantities = [k for k in self._present(d) if isinstance(d[k], dict)]
        if not quantities:
            return
        first = d[quantities[0]]
        target, _ = _label_or_canonical("pressure", first["unit"])
        if units.label_for("pressure", first["unit"]) is None:
            target = "bar"
        target_pint = _pint("pressure", target)
        target_ref = first.get("ref", "g")
        for k in quantities:
            q = d[k]
            value = _convert(q["value"], q["unit"], target_pint)
            ref = q.get("ref", "g")
            if value is not None and ref != target_ref:
                value = (
                    value - _atm(target_pint)
                    if ref == "a"
                    else value + _atm(target_pint)
                )
            d[k] = value
        d[self.unit_key] = target
        d[self.ref_key] = target_ref


@dataclass(frozen=True)
class TestRows:
    """Test-points table: runtime ``columns`` (labels) <-> on-disk ``columns`` (Pint).

    Rows are stored in their column units on both sides; only the ``columns``
    map is translated (label <-> Pint string).
    """

    __test__ = False  # not a pytest class

    def fill_v1(self, d: dict) -> None:
        """v1 runtime shape (``unit`` + canonical rows) -> ``columns`` shape."""
        if "rows" not in d or "columns" in d:
            return
        unit = d.pop("unit", "bar")
        plabel = units.label_for("pressure", unit) or "bar"
        if plabel not in ("bar", "kgf/cm²"):
            plabel = "bar"
        cols = {
            k: units.canonical_unit(dim) for k, dim in units.COLUMN_DIMENSIONS.items()
        }
        cols["p_suc"] = cols["p_dis"] = plabel
        d["columns"] = cols
        d["pressure_ref"] = "g"

    def enc(self, d: dict) -> None:
        if "rows" not in d:
            return
        self.fill_v1(d)
        cols = d.get("columns", {})
        out = {}
        for key, dim in units.COLUMN_DIMENSIONS.items():
            label = cols.get(key, units.canonical_unit(dim))
            # One spelling on disk for every column (compact Pint, as
            # quantity_io writes quantities), so encode(decode(v2)) == v2.
            out[key] = _disk_unit(dim, label)
        d["columns"] = out
        d["pressure_ref"] = d.get("pressure_ref", "g")

    def dec(self, d: dict) -> None:
        cols = d.get("columns")
        if not isinstance(cols, dict):
            return
        d.pop("columns")
        ref = d.pop("pressure_ref", "g")

        labels: Dict[str, str] = {}
        src: Dict[str, str] = {}  # key -> stored unit (only when conversion needed)
        dst: Dict[str, str] = {}
        p_target = "bar"
        stored_p = cols.get("p_suc")
        if stored_p is not None:
            p_target = units.label_for("pressure", stored_p) or "bar"
        for key, dim in units.COLUMN_DIMENSIONS.items():
            stored = cols.get(key)
            if dim == "pressure":
                labels[key] = p_target
                if stored is not None and not _same_unit(
                    stored, _pint("pressure", p_target)
                ):
                    src[key], dst[key] = stored, _pint("pressure", p_target)
                continue
            if stored is None:
                labels[key] = units.canonical_unit(dim)
                continue
            label, convert = _label_or_canonical(dim, stored)
            labels[key] = label
            if convert:
                src[key], dst[key] = stored, _pint(dim, label)

        rows = []
        for row in d.get("rows", []):
            row = dict(row)
            for key, s_unit in src.items():
                if row.get(key) is not None:
                    row[key] = _convert(row[key], s_unit, dst[key])
            rows.append(row)
        d["rows"] = rows
        d["columns"] = labels
        d["pressure_ref"] = ref


# ---------------------------------------------------------------------------
# Mechanical run (sprint 6)
# ---------------------------------------------------------------------------

#: Dimension (``units.UNIT_OPTIONS`` key) of the limits of each channel role.
#: Roles without an entry (``other``) have no editable limits.
ROLE_DIMENSIONS: Dict[str, str] = {
    "vibration_filtered": "vibration_velocity",
    "vibration_unfiltered": "vibration_velocity",
    "bearing_temperature": "temperature",
    "oil_temperature": "temperature",
    "oil_pressure": "pressure",
    "seal_pressure": "pressure",
    "flow": "capacity",
    "differential_pressure": "pressure",
    "power": "power",
}

#: Duration display label -> Pint unit string.
DURATION_LABELS: Dict[str, str] = {"h": "hour", "min": "minute"}
_DURATION_BACK = {"hour": "h", "h": "h", "minute": "min", "min": "min"}

_DELTA_TEMP = {"°C": "delta_degC", "°F": "delta_degF", "K": "kelvin"}
_DELTA_TEMP_BACK = {v: k for k, v in _DELTA_TEMP.items()}


def delta_pint(dimension: str, label: str) -> str:
    """Pint unit of a *difference* in ``dimension`` shown in ``label``.

    Temperatures use the Pint delta units (``delta_degC`` / ``delta_degF`` /
    ``kelvin``); every other dimension uses its ordinary unit.
    """
    if dimension == "temperature":
        return _DELTA_TEMP.get(label, label)
    return units.pint_str(dimension, label)


def _q_enc(q, dim: str, kind: str):
    """Runtime ``{"value", "unit": label}`` -> on-disk ``{"value", "unit": pint}``."""
    if not isinstance(q, dict):
        return q
    label = q["unit"]
    if kind == "dur":
        unit = DURATION_LABELS.get(label, label)
    elif kind == "delta":
        unit = (
            delta_pint(dim, label) if dim == "temperature" else _disk_unit(dim, label)
        )
    else:
        unit = _disk_unit(dim, label)
    return {"value": q["value"], "unit": unit}


def _q_dec(q, dim: str, kind: str):
    """On-disk ``{"value", "unit"}`` -> runtime ``{"value", "unit": label}``."""
    if not isinstance(q, dict):
        return q
    value, unit = q["value"], q["unit"]
    if kind == "dur":
        label = _DURATION_BACK.get(unit)
        if label is None:
            label = "min"
            value = Q_(value, unit).to("minute").magnitude
    elif kind == "delta" and dim == "temperature":
        label = _DELTA_TEMP_BACK.get(unit)
        if label is None:
            label = "°C"
            value = Q_(value, unit).to("delta_degC").magnitude
    else:
        label, convert = _label_or_canonical(dim, unit)
        if convert:
            value = _convert(value, unit, _pint(dim, label))
    return {"value": value, "unit": label}


@dataclass(frozen=True)
class RunLog:
    """Mechanical-run settings: channel units and criteria overrides.

    ``columns`` entries carry a display label at runtime and a Pint string on
    disk; rows are stored in the column units on both sides (only converted
    when a stored unit has no display label).  ``overrides`` quantities are
    ``{"value", "unit"}`` on both sides, with labels <-> Pint strings.
    """

    def fill_v1(self, d: dict) -> None:
        return None

    @staticmethod
    def _overrides(ov, fn) -> None:
        if not isinstance(ov, dict):
            return
        if ov.get("min_duration") is not None:
            ov["min_duration"] = fn(ov["min_duration"], "duration", "dur")
        for role, q in list((ov.get("role_max") or {}).items()):
            dim = ROLE_DIMENSIONS.get(role)
            if dim:
                ov["role_max"][role] = fn(q, dim, "q")
        for role, st in (ov.get("stabilisation") or {}).items():
            dim = ROLE_DIMENSIONS.get(role)
            if not dim or not isinstance(st, dict):
                continue
            if "delta" in st:
                st["delta"] = fn(st["delta"], dim, "delta")
            if "window" in st:
                st["window"] = fn(st["window"], "duration", "dur")

    def enc(self, d: dict) -> None:
        for c in d.get("columns") or []:
            if isinstance(c, dict) and c.get("dimension") in units.UNIT_OPTIONS:
                c["unit"] = _disk_unit(c["dimension"], c["unit"])
        self._overrides(d.get("overrides"), _q_enc)

    def dec(self, d: dict) -> None:
        cols = d.get("columns")
        if isinstance(cols, list):
            rows = d.get("rows") or []
            for c in cols:
                dim = c.get("dimension") if isinstance(c, dict) else None
                if dim not in units.UNIT_OPTIONS:
                    continue
                stored = c["unit"]
                label, convert = _label_or_canonical(dim, stored)
                if convert:
                    for r in rows:
                        vals = r.get("values") or {}
                        if vals.get(c["name"]) is not None:
                            vals[c["name"]] = _convert(
                                vals[c["name"]], stored, _pint(dim, label)
                            )
                c["unit"] = label
        self._overrides(d.get("overrides"), _q_dec)


# ---------------------------------------------------------------------------
# NPSH (sprint 8)
# ---------------------------------------------------------------------------

#: NPSHr-table column key -> unit dimension.
_NPSH_COLUMNS: Dict[str, str] = {"q": "capacity", "npshr": "npsh"}


@dataclass(frozen=True)
class NPSHTable:
    """NPSH-node settings: per-column units of the NPSHr table + the margin override.

    ``columns`` is ``{"q", "npshr"}`` (display labels at runtime, Pint strings on
    disk); rows are stored in their column units on both sides and only converted
    when a stored unit has no display label.  ``overrides["min_margin"]`` is a
    ``{"value", "unit"}`` quantity (label <-> Pint); ``min_ratio`` is a plain
    float.  The optional/other quantities of the node (``npsha``, the calculator
    suction conditions) use the generic :class:`Disp` / :class:`OptDisp` /
    :class:`Pressures` specs listed beside this one in :data:`FIELDS`.
    """

    def fill_v1(self, d: dict) -> None:
        return None

    def enc(self, d: dict) -> None:
        cols = d.get("columns")
        if isinstance(cols, dict):
            d["columns"] = {
                key: _disk_unit(dim, cols.get(key, units.canonical_unit(dim)))
                for key, dim in _NPSH_COLUMNS.items()
            }
        ov = d.get("overrides")
        if isinstance(ov, dict) and ov.get("min_margin") is not None:
            ov["min_margin"] = _q_enc(ov["min_margin"], "npsh", "q")

    def dec(self, d: dict) -> None:
        cols = d.get("columns")
        if isinstance(cols, dict):
            rows = d.get("rows") or []
            labels: Dict[str, str] = {}
            for key, dim in _NPSH_COLUMNS.items():
                stored = cols.get(key)
                if stored is None:
                    labels[key] = units.canonical_unit(dim)
                    continue
                label, convert = _label_or_canonical(dim, stored)
                if convert:
                    dst = _pint(dim, label)
                    for r in rows:
                        if r.get(key) is not None:
                            r[key] = _convert(r[key], stored, dst)
                labels[key] = label
            d["columns"] = labels
        ov = d.get("overrides")
        if isinstance(ov, dict) and ov.get("min_margin") is not None:
            ov["min_margin"] = _q_dec(ov["min_margin"], "npsh", "q")


FIELDS: Dict[str, tuple] = {
    "rated_point": (
        Disp("q", "capacity", "q_unit"),
        Disp("head", "head", "head_unit"),
        Disp("power", "power", "power_unit"),
        Disp("visc", "viscosity", "visc_unit"),
        Disp("n", "speed", "n_unit"),
        Disp("eff", "efficiency", "eff_unit"),
        Disp("head_shutoff", "head", "head_shutoff_unit"),
        Disp("npsha", "npsh", "npsha_unit"),
        # Optional datasheet impeller diameters (sprint 10): omitted when unset.
        OptDisp("d_imp", "length", "d_imp_unit"),
        OptDisp("d_max", "length", "d_max_unit"),
        OptDisp("d_min", "length", "d_min_unit"),
    ),
    "fluid": (
        Disp("temp", "temperature", "temp_unit"),
        Disp("dens", "density", "dens_unit"),
        Disp("visc", "viscosity", "visc_unit"),
    ),
    "point": (
        Disp("q", "capacity", "q_unit"),
        Disp("head", "head", "head_unit"),
        Disp("power", "power", "power_unit"),
        Disp("eff", "efficiency", "eff_unit"),
        Pressures(),
    ),
    "correction": (Disp("target_speed", "speed", "target_speed_unit"),),
    "trim": (Disp("d_target", "length", "d_target_unit"),),
    # Pump selection (sprint 12): the duty point of the catalogue search.
    "selection": (
        Disp("duty_q", "capacity", "duty_q_unit"),
        Disp("duty_h", "head", "duty_h_unit"),
    ),
    "performance_plot": (
        YLimDisp("head_ylim", "head", "head_ylim_unit"),
        YLimDisp("power_ylim", "power", "power_ylim_unit"),
        YLimDisp("eff_ylim", "efficiency", "eff_ylim_unit"),
    ),
    "test_points": (
        TestRows(),
        # Optional test-bench geometry (sprint 4): four optional lengths.
        OptDisp("suction_id", "length", "suction_id_unit"),
        OptDisp("discharge_id", "length", "discharge_id_unit"),
        OptDisp("suction_z", "length", "suction_z_unit"),
        OptDisp("discharge_z", "length", "discharge_z_unit"),
    ),
    "mechanical_run": (RunLog(),),
    "npsh": (
        NPSHTable(),
        # Optional NPSHa typed in the node (unset = use the rated point's).
        OptDisp("npsha", "npsh", "npsha_unit"),
        # NPSHa calculator: suction conditions (suction ID is optional).
        Pressures(keys=("calc_p",), unit_key="calc_p_unit", ref_key="calc_p_ref"),
        Disp("calc_temp", "temperature", "calc_temp_unit"),
        OptDisp("calc_id", "length", "calc_id_unit"),
        Disp("calc_z", "length", "calc_z_unit"),
    ),
    "system_curve": (
        Disp("static", "head", "static_unit"),
        Disp("q1", "capacity", "q1_unit"),
        Disp("h1", "head", "h1_unit"),
        Disp("q2", "capacity", "q2_unit"),
        Disp("h2", "head", "h2_unit"),
        Disp("length", "length", "length_unit"),
        Disp("diameter", "length", "diameter_unit"),
        Disp("roughness", "length", "roughness_unit"),
    ),
}

# Stale v1 keys removed by upgrade_v1 (the old exchange-style rated "unit").
_V1_DROP = {"rated_point": ("unit",)}


# ---------------------------------------------------------------------------
# Free-text "standard" -> acceptance keys  (sprint 5)
# ---------------------------------------------------------------------------

_API610_EDITIONS = (8, 10, 11, 12)
_DEFAULT_STANDARD_KEY = "api610:12"
_API610_RE = re.compile(r"api\s*-?\s*610[^0-9]{0,6}(\d{1,2})(?!\d)", re.IGNORECASE)
_N553_RE = re.compile(r"(?<![a-z0-9])n[-\s]?553", re.IGNORECASE)


def parse_standard_text(text: Optional[str]) -> Tuple[str, Optional[str]]:
    """``(standard_key, client)`` from the free-text rated-point ``standard``.

    ``"API 610"`` / ``"API610"`` followed by an edition number (``8th``, ``12a``,
    ``(12``, ``11ª``) gives ``"api610:<n>"`` when ``<n>`` is 8/10/11/12, else
    ``"api610:12"``; ``N-553`` / ``N553`` gives client ``"n553"``, else ``None``.

    Examples
    --------
    >>> parse_standard_text("API610 (12a ed.) / ISO 13709 + N-553")
    ('api610:12', 'n553')
    >>> parse_standard_text("API 610 8th + N-553C + API 682 3rd")
    ('api610:8', 'n553')
    >>> parse_standard_text("garbage")
    ('api610:12', None)
    """
    text = str(text or "")
    key = _DEFAULT_STANDARD_KEY
    m = _API610_RE.search(text)
    if m and int(m.group(1)) in _API610_EDITIONS:
        key = f"api610:{int(m.group(1))}"
    client = "n553" if _N553_RE.search(text) else None
    return key, client


def encode(kind: str, runtime: dict) -> dict:
    """Runtime settings -> v2 on-disk settings (new dict; input untouched)."""
    d = copy.deepcopy(runtime)
    for spec in FIELDS.get(kind, ()):
        spec.enc(d)
    return d


def decode(kind: str, stored: dict) -> dict:
    """v2 on-disk settings -> runtime settings (new dict; input untouched)."""
    d = copy.deepcopy(stored)
    for spec in FIELDS.get(kind, ()):
        spec.dec(d)
    return d


def upgrade_v1(kind: str, settings: dict) -> dict:
    """Normalise a v1 runtime-shaped settings dict before :func:`encode`.

    Missing ``*_unit`` keys are filled with the **canonical** unit label (never
    the active preset: v1 magnitudes without a label were canonical), the stale
    rated-point ``"unit"`` key is dropped, and a v1 test-points ``unit`` becomes
    the ``columns`` map (pressure ``bar`` / ``kgf/cm²``, the rest canonical).
    A rated point that carries a free-text ``standard`` but no ``standard_key`` /
    ``client`` gets them parsed from that text (``client`` is ``""`` for none).
    """
    d = copy.deepcopy(settings)
    for key in _V1_DROP.get(kind, ()):
        d.pop(key, None)
    for spec in FIELDS.get(kind, ()):
        spec.fill_v1(d)
    if kind == "rated_point" and d.get("standard") is not None:
        key, client = parse_standard_text(d.get("standard"))
        d.setdefault("standard_key", key)
        d.setdefault("client", client or "")
    return d
