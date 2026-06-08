"""
persistence
===========

Two on-disk formats (UI_SPEC §6):

- **Data-exchange JSON** (§6.2) — the simple ``{unit, rated, points}`` file the
  Rated Point Input and Test Points Table widgets round-trip.  The importer
  accepts the locale-style comma-decimal strings; the exporter emits the same
  shape so existing files stay interoperable.
- **Project file** (``.pumpflow``, §6.1) — the *whole* canvas: node positions,
  links and every widget's settings.  Generic read/write lives here; the scene
  builds/consumes the document (it owns the node graph).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .numfmt import parse_decimal
from .signals import RatedPoint, TestPointSet, TestRow


# ---------------------------------------------------------------------------
# Data-exchange JSON  (UI_SPEC §6.2)
# ---------------------------------------------------------------------------


def rated_from_json(doc: dict) -> RatedPoint:
    """Build a :class:`RatedPoint` from a §6.2 document (comma-decimals ok)."""
    unit = _normalize_unit(doc.get("unit", "bar"))
    r = doc.get("rated", {})
    return RatedPoint(
        tag=str(r.get("tag", "")).strip(),
        service=str(r.get("service", "")),
        standard=str(r.get("standard", "API610 (12a ed.) / ISO 13709 + N-553")),
        q_m3h=parse_decimal(r.get("q_m3h"), 0.0),
        head_m=parse_decimal(r.get("head_m"), 0.0),
        speed_rpm=parse_decimal(r.get("n_rpm"), 0.0),
        power_kw=parse_decimal(r.get("power_kw"), 0.0),
        efficiency_pct=parse_decimal(r.get("eff_pct"), None),
        head_shutoff_m=parse_decimal(r.get("head_shutoff"), None),
        density_rel=parse_decimal(r.get("dens_rel"), 1.0),
        viscosity_cst=parse_decimal(r.get("visc_nom_cst"), 1.0),
        pressure_unit=unit,
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
                q_m3h=parse_decimal(p.get("q"), 0.0),
                p_suction=parse_decimal(p.get("p_suc"), 0.0),
                p_discharge=parse_decimal(p.get("p_dis"), 0.0),
                temp_c=parse_decimal(p.get("temp_c"), 25.0),
                speed_rpm=parse_decimal(p.get("n_rpm"), 0.0),
                power_kw=parse_decimal(p.get("power"), 0.0),
                head_m=parse_decimal(p.get("head"), None),
                efficiency_pct=parse_decimal(p.get("eff"), None),
            )
        )
    return TestPointSet(pump_tag=str(tag).strip(), rows=tuple(rows), pressure_unit=unit)


def json_from_signals(rated: RatedPoint, tps: Optional[TestPointSet] = None) -> dict:
    """Export back to the §6.2 shape (exporter mirrors importer)."""
    doc = {
        "unit": rated.pressure_unit,
        "rated": {
            "tag": rated.tag,
            "service": rated.service,
            "standard": rated.standard,
            "q_m3h": _num(rated.q_m3h),
            "head_m": _num(rated.head_m),
            "n_rpm": _num(rated.speed_rpm),
            "power_kw": _num(rated.power_kw),
            "eff_pct": _num(rated.efficiency_pct),
            "dens_rel": _num(rated.density_rel),
            "visc_nom_cst": _num(rated.viscosity_cst),
            "head_shutoff": _num(rated.head_shutoff_m),
            "parallel": rated.parallel_operation,
        },
    }
    if tps is not None:
        doc["pump_tag"] = tps.pump_tag
        doc["points"] = [
            {
                "q": _num(r.q_m3h),
                "p_suc": _num(r.p_suction),
                "p_dis": _num(r.p_discharge),
                "temp_c": _num(r.temp_c),
                "power": _num(r.power_kw),
                "n_rpm": _num(r.speed_rpm),
                **({"head": _num(r.head_m)} if r.head_m is not None else {}),
                **({"eff": _num(r.efficiency_pct)} if r.efficiency_pct is not None else {}),
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
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str | Path, doc: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
