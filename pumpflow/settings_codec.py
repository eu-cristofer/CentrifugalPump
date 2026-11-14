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
  differs from the runtime unit.

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
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Tuple

from pump import Q_
from pump.constants import P_ATM

from . import units

__all__ = ["FIELDS", "encode", "decode", "upgrade_v1"]


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
        return units._pint_str(dimension, label)
    except KeyError:
        return label


_PRESSURE_RUNTIME = ("bar", "kgf/cm**2")


def _pressure_runtime_unit(unit: str) -> str:
    """The runtime combo unit (bar / kgf/cm**2) for a stored pressure unit."""
    for u in _PRESSURE_RUNTIME:
        if _same_unit(unit, u):
            return u
    return "bar"


def _atm(unit: str) -> float:
    return P_ATM.to(unit).magnitude


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
        d[self.key] = {"value": v, "unit": _fmt(_pint(self.dimension, label))}

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
class Fixed:
    """Value with a fixed runtime unit (no ``*_unit`` key)."""

    key: str
    unit: str

    def fill_v1(self, d: dict) -> None:
        pass

    def enc(self, d: dict) -> None:
        v = d.get(self.key)
        if v is None or isinstance(v, dict):
            return
        d[self.key] = {"value": v, "unit": self.unit}

    def dec(self, d: dict) -> None:
        q = d.get(self.key)
        if isinstance(q, dict):
            d[self.key] = _convert(q["value"], q["unit"], self.unit)


@dataclass(frozen=True)
class YLim:
    """Optional ``[lo, hi]`` axis limits (``null`` stays ``null``)."""

    key: str
    unit: str

    def fill_v1(self, d: dict) -> None:
        pass

    def enc(self, d: dict) -> None:
        v = d.get(self.key)
        if isinstance(v, (list, tuple)):
            d[self.key] = {"value": list(v), "unit": self.unit}

    def dec(self, d: dict) -> None:
        q = d.get(self.key)
        if isinstance(q, dict):
            d[self.key] = [_convert(x, q["unit"], self.unit) for x in q["value"]]


@dataclass(frozen=True)
class Pressures:
    """Gauge pressures sharing one runtime unit key -> ``{value, unit, ref}``."""

    keys: Tuple[str, ...] = ("p_suc", "p_dis")
    unit_key: str = "p_unit"

    def _present(self, d: dict):
        return [k for k in self.keys if k in d]

    def fill_v1(self, d: dict) -> None:
        if any(d.get(k) is not None for k in self.keys) and self.unit_key not in d:
            d[self.unit_key] = "bar"

    def enc(self, d: dict) -> None:
        live = [
            k
            for k in self._present(d)
            if d[k] is not None and not isinstance(d[k], dict)
        ]
        if not live:
            return
        unit = _fmt(d.pop(self.unit_key, "bar"))
        for k in live:
            d[k] = {"value": d[k], "unit": unit, "ref": "g"}

    def dec(self, d: dict) -> None:
        quantities = [k for k in self._present(d) if isinstance(d[k], dict)]
        if not quantities:
            return
        target = _pressure_runtime_unit(d[quantities[0]]["unit"])
        for k in quantities:
            q = d[k]
            value = _convert(q["value"], q["unit"], target)
            if q.get("ref", "g") == "a" and value is not None:
                value = value - _atm(target)  # absolute -> gauge; dP unchanged
            d[k] = value
        d[self.unit_key] = target


_ROW_RUNTIME_UNITS = {
    "q": "m**3/h",
    "temp_c": "degC",
    "n": "rpm",
    "power": "kW",
    "head": "m",
    "eff": "percent",
}
_ROW_PRESSURES = ("p_suc", "p_dis")


@dataclass(frozen=True)
class TestRows:
    """Test-points table: runtime ``unit`` + rows <-> ``columns`` + ``rows``."""

    __test__ = False  # not a pytest class

    def fill_v1(self, d: dict) -> None:
        pass

    def enc(self, d: dict) -> None:
        if "rows" not in d or "columns" in d:
            return
        pu = _fmt(d.pop("unit", "bar"))
        d["columns"] = {
            "q": "m**3/h",
            "p_suc": pu,
            "p_dis": pu,
            "temp_c": "degC",
            "n": "rpm",
            "power": "kW",
            "head": "m",
            "eff": "percent",
        }
        d["pressure_ref"] = "g"

    def dec(self, d: dict) -> None:
        cols = d.get("columns")
        if not isinstance(cols, dict):
            return
        d.pop("columns")
        ref = d.pop("pressure_ref", "g")
        target = _pressure_runtime_unit(cols.get("p_suc", "bar"))
        rows = []
        for row in d.get("rows", []):
            row = dict(row)
            for k, rt_unit in _ROW_RUNTIME_UNITS.items():
                if row.get(k) is not None:
                    row[k] = _convert(row[k], cols.get(k, rt_unit), rt_unit)
            for k in _ROW_PRESSURES:
                if row.get(k) is not None:
                    v = _convert(row[k], cols.get(k, target), target)
                    row[k] = v - _atm(target) if ref == "a" else v
            rows.append(row)
        d["rows"] = rows
        d["unit"] = target


FIELDS: Dict[str, tuple] = {
    "rated_point": (
        Disp("q", "capacity", "q_unit"),
        Disp("head", "head", "head_unit"),
        Disp("power", "power", "power_unit"),
        Disp("visc", "viscosity", "visc_unit"),
        Fixed("n", "rpm"),
        Fixed("eff", "percent"),
        Fixed("head_shutoff", "m"),
        Fixed("npsha", "m"),
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
        Fixed("eff", "percent"),
        Pressures(),
    ),
    "correction": (Fixed("target_speed", "rpm"),),
    "performance_plot": (
        YLim("head_ylim", "m"),
        YLim("power_ylim", "kW"),
        YLim("eff_ylim", "percent"),
    ),
    "test_points": (TestRows(),),
}

# Stale v1 keys removed by upgrade_v1 (the old exchange-style rated "unit").
_V1_DROP = {"rated_point": ("unit",)}


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
    the active preset: v1 magnitudes without a label were canonical), and the
    stale rated-point ``"unit"`` key is dropped.
    """
    d = copy.deepcopy(settings)
    for key in _V1_DROP.get(kind, ()):
        d.pop(key, None)
    for spec in FIELDS.get(kind, ()):
        spec.fill_v1(d)
    return d
