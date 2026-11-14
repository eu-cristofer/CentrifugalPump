"""
persistence
===========

Two on-disk formats (UI_SPEC §6):

- **Data-exchange JSON** (§6.2) — the simple ``{unit, rated, points}`` file the
  Rated Point Input and Test Points Table widgets round-trip.  The importer
  accepts the locale-style comma-decimal strings; the exporter emits the same
  shape so existing files stay interoperable.  Floats ↔ Pint quantities are
  converted here, at the JSON edge.
- **Project file** (``.pumpflow``, §6.1) — the *whole* canvas: node positions,
  links and every widget's settings.  Generic read/write lives here; the scene
  builds/consumes the document (it owns the node graph).  Schema **v2** stores
  quantities as ``{"value", "unit"}`` pairs (see :mod:`pumpflow.settings_codec`);
  :func:`migrate` upgrades v1 documents.  The exchange JSON is not a project and
  is never migrated.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

from pump import Q_, Pressure

from . import settings_codec
from .numfmt import parse_decimal
from .signals import RatedPoint, TestPointSet, TestRow

SCHEMA_VERSION = 2

# ---------------------------------------------------------------------------
# Data-exchange JSON  (UI_SPEC §6.2)
# ---------------------------------------------------------------------------


def _opt(value, unit: str):
    """``Q_(value, unit)`` or ``None`` (floats ↔ Quantities at the JSON edge)."""
    return None if value is None else Q_(value, unit)


def _mag(q, unit: str):
    """Plain magnitude of an optional Quantity in ``unit`` (``None`` stays)."""
    return None if q is None else q.to(unit).magnitude


def testset_pressure_unit(tps: Optional[TestPointSet]) -> str:
    """Exchange pressure unit of a test set: its rows' unit, else ``"bar"``."""
    if tps is not None and tps.rows:
        if tps.rows[0].p_suction.value.units == Q_(1, "kgf/cm**2").units:
            return "kgf/cm**2"
    return "bar"


def rated_from_json(doc: dict) -> RatedPoint:
    """Build a :class:`RatedPoint` from a §6.2 document (comma-decimals ok)."""
    r = doc.get("rated", {})
    return RatedPoint(
        tag=str(r.get("tag", "")).strip(),
        service=str(r.get("service", "")),
        standard=str(r.get("standard", "API610 (12a ed.) / ISO 13709 + N-553")),
        q=Q_(parse_decimal(r.get("q_m3h"), 0.0), "m**3/h"),
        head=Q_(parse_decimal(r.get("head_m"), 0.0), "m"),
        speed=Q_(parse_decimal(r.get("n_rpm"), 0.0), "rpm"),
        power=Q_(parse_decimal(r.get("power_kw"), 0.0), "kW"),
        efficiency=_opt(parse_decimal(r.get("eff_pct"), None), "percent"),
        head_shutoff=_opt(parse_decimal(r.get("head_shutoff"), None), "m"),
        npsha=_opt(parse_decimal(r.get("npsha_m"), None), "m"),
        density=Q_(parse_decimal(r.get("dens_rel"), 1.0) * 1000.0, "kg/m**3"),
        viscosity=Q_(parse_decimal(r.get("visc_nom_cst"), 1.0), "cSt"),
        parallel_operation=bool(r.get("parallel", False)),
        fluid_name=str(r.get("fluid_name", "Rated fluid")),
    )


def testset_from_json(doc: dict, pump_tag: Optional[str] = None) -> TestPointSet:
    """Build a :class:`TestPointSet` from a §6.2 document."""
    unit = _normalize_unit(doc.get("unit", "bar"))
    tag = pump_tag or doc.get("pump_tag") or (doc.get("rated", {}).get("tag", "") + "A")
    rows = []
    for p in doc.get("points", []):
        rows.append(
            TestRow(
                q=Q_(parse_decimal(p.get("q"), 0.0), "m**3/h"),
                p_suction=Pressure(Q_(parse_decimal(p.get("p_suc"), 0.0), unit), "g"),
                p_discharge=Pressure(Q_(parse_decimal(p.get("p_dis"), 0.0), unit), "g"),
                temperature=Q_(parse_decimal(p.get("temp_c"), 25.0), "degC"),
                speed=Q_(parse_decimal(p.get("n_rpm"), 0.0), "rpm"),
                power=Q_(parse_decimal(p.get("power"), 0.0), "kW"),
                head=_opt(parse_decimal(p.get("head"), None), "m"),
                efficiency=_opt(parse_decimal(p.get("eff"), None), "percent"),
            )
        )
    return TestPointSet(pump_tag=str(tag).strip(), rows=tuple(rows))


def json_from_signals(rated: RatedPoint, tps: Optional[TestPointSet] = None) -> dict:
    """Export back to the §6.2 shape (exporter mirrors importer)."""
    unit = testset_pressure_unit(tps)
    doc = {
        "unit": unit,
        "rated": {
            "tag": rated.tag,
            "service": rated.service,
            "standard": rated.standard,
            "q_m3h": _num(_mag(rated.q, "m**3/h")),
            "head_m": _num(_mag(rated.head, "m")),
            "n_rpm": _num(_mag(rated.speed, "rpm")),
            "power_kw": _num(_mag(rated.power, "kW")),
            "eff_pct": _num(_mag(rated.efficiency, "percent")),
            "dens_rel": _num(rated.density_rel),
            "visc_nom_cst": _num(_mag(rated.viscosity, "cSt")),
            "head_shutoff": _num(_mag(rated.head_shutoff, "m")),
            "npsha_m": _num(_mag(rated.npsha, "m")),
            "parallel": rated.parallel_operation,
        },
    }
    if tps is not None:
        doc["pump_tag"] = tps.pump_tag
        doc["points"] = [
            {
                "q": _num(_mag(r.q, "m**3/h")),
                "p_suc": _num(_mag(r.p_suction.value, unit)),
                "p_dis": _num(_mag(r.p_discharge.value, unit)),
                "temp_c": _num(_mag(r.temperature, "degC")),
                "power": _num(_mag(r.power, "kW")),
                "n_rpm": _num(_mag(r.speed, "rpm")),
                **({"head": _num(_mag(r.head, "m"))} if r.head is not None else {}),
                **(
                    {"eff": _num(_mag(r.efficiency, "percent"))}
                    if r.efficiency is not None
                    else {}
                ),
            }
            for r in tps.rows
        ]
    return doc


def _num(value):
    if value is None:
        return None
    f = float(value)
    return int(f) if f.is_integer() else round(f, 6)


def _normalize_unit(unit: str) -> str:
    u = str(unit).strip().lower().replace(" ", "")
    if u in ("bar",):
        return "bar"
    if u in ("kgf/cm2", "kgf/cm**2", "kgf/cm²", "kgfcm2", "kgf"):
        return "kgf/cm**2"
    return "bar"


# ---------------------------------------------------------------------------
# Generic file IO
# ---------------------------------------------------------------------------


def read_json(path: str | Path) -> dict:
    """Raw JSON read (also used for the §6.2 exchange JSON; never migrated)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str | Path, doc: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Project schema versions
# ---------------------------------------------------------------------------


def migrate(doc: dict) -> dict:
    """Upgrade a ``.pumpflow`` document to schema v2 (pure, idempotent).

    Returns a new dict; the input is never mutated.  A v1 document has every
    node's settings run through ``settings_codec.upgrade_v1`` (missing ``*_unit``
    keys get the canonical label, never the active preset) and then
    ``settings_codec.encode``; ``meta.schema_version`` becomes 2 while
    ``meta.unit_preset`` is kept.  A v2 document is returned as a deep copy.

    Examples
    --------
    >>> v1 = {"nodes": [{"id": "r", "kind": "rated_point", "settings": {"q": 833.0}}]}
    >>> migrate(v1)["nodes"][0]["settings"]["q"]
    {'value': 833.0, 'unit': 'm**3/h'}
    >>> migrate(migrate(v1)) == migrate(v1)
    True
    """
    out = copy.deepcopy(doc)
    meta = out.get("meta") or {}
    if int(meta.get("schema_version", 1)) >= 2:
        return out
    for node in out.get("nodes", []):
        settings = node.get("settings")
        if isinstance(settings, dict):
            kind = node.get("kind", "")
            node["settings"] = settings_codec.encode(
                kind, settings_codec.upgrade_v1(kind, settings)
            )
    out["meta"] = {**meta, "schema_version": SCHEMA_VERSION}
    return out


def read_project(path: str | Path) -> dict:
    """Read a ``.pumpflow`` project file and migrate it to the current schema."""
    return migrate(read_json(path))
