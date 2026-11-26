"""
webapi
======

The plain-JSON boundary between Python and the browser front end (002_web).
Everything the browser shows comes from here; the browser never computes.
Every function takes and returns JSON-serialisable values only (``str``,
``float``, ``int``, ``bool``, ``None``, ``list``, ``dict``).  Quantities are
``{"value": float, "unit": str}`` (``pump.quantity_io.to_json``); NaN and
infinity become ``None``; numpy values become floats and lists.  The module
imports without Qt (it uses :class:`pumpflow.engine.Graph` and the Qt-free node
logic only).

Public functions
----------------
``catalog() -> list``
    One entry per node kind, in toolbox order::

        {"kind": str, "title": str, "glyph": str, "group": str,
         "inputs":  [{"name": str, "type": str, "multi": bool}],
         "outputs": [{"name": str, "type": str}],
         "has_web_form": bool}

    ``has_web_form`` is true for the 12 witness kinds: rated_point, fluid,
    test_points, correction, curve_fit, performance_plot, compliance, npsh,
    mechanical_run, mechanical_run_check, report_export, markdown_note.

``evaluate(doc: dict, sep: str | None = None) -> dict``
    Build a graph from a ``.pumpflow`` document (v1 or v2), evaluate it and
    return (numbers in texts use the decimal separator ``sep``, "." or ","; the
    point by default)::

        {"nodes": {node_id: {"kind": str, "state": str, "status": str,
                             "badge": [text, tone] | None,
                             "notes": [str, ...],
                             "view": dict}},
         "errors": [node_id, ...]}

    ``state`` is idle / ok / invalid / error / reject; ``tone`` is ok / fail /
    warn; ``errors`` lists the nodes in state ``error``.  A view that raises is
    reported as ``{"error": str}`` and never breaks the response.

``node_view(graph, node) -> dict``
    Per-kind display data, built from the node's output cache and settings
    (``{}`` for kinds without a view, or while the node has no result).  Units:
    capacity m3/h, head m, power kW, efficiency %, NPSH m unless a ``*_unit``
    key says otherwise.  Shapes by kind:

    test_points::

        {"pump_tag": str, "n_rows": int, "head_unit": str, "eff_unit": str,
         "rows": [{"head": float | None, "eff": float | None,
                   "components": {"pressure","velocity","elevation","total"} | None}],
         "fluids": [name], "choice": str, "has_shutoff": bool,
         "test_fluid": {"name", "density_kgm3"} | None,
         "pump_type": str, "vib_label": str,
         "vib_columns": [{"key", "title", "tooltip"}]}

    correction::

        {"fluids": [name], "choice": str, "has_rated": bool, "has_fluid": bool,
         # and, once the node has a result:
         "pump_tag": str, "target_speed": {"value","unit"},
         "viscous": {"B","C_Q","C_H","C_eta"} | None, "viscous_text": str,
         "banner": {"text": str, "level": "info" | "warn" | "error"},
         "before_after": [{"measured": {...}, "corrected": {...}}]}

    curve_fit (and the series part of performance_plot, as ``fit``)::

        {"pump_tag": str, "degree": int, "r2": {"head","power","efficiency"},
         "points": {"q": [], "head": [], "power": [] | None, "eff": [] | None},
         "poly":   {"q": [], "head": [], "power": [] | None, "eff": [] | None},
         "spline": {same keys} | None,
         "coefficients": {"head": [], "power": [], "eff": []}}

    The ``curve_fit`` view also has ``r2_text`` (``"R²(head)=0.9988  ·  ..."``) and
    ``coeff_text`` (the desktop coefficient block).

    compliance::

        {"pump_tag": str, "verdict_text": str, "verdict_label": str,
         "overall_pass": bool, "criteria_label": str, "overridden": bool,
         "override_reason": str, "shutoff_waiver": str,
         "unverified": [str], "not_evaluated": [str],
         "parallel_ok": bool | None, "tolerances": dict,
         "default_tolerances": {"head","shutoff","power","efficiency"},
         "rows": [{"name", "actual", "predicted", "min", "max", "deviation",
                   "tol", "verdict": "pass" | "fail" | "info" | "n/e",
                   "note", "extrapolated", "verified",
                   "cells": [9 strings, the desktop table cells]}]}

    npsh::

        {"pump_tag": str, "mode": str, "status": "pass" | "fail" | "info",
         "verdict": str, "verified": bool, "criteria_label": str,
         "npsha": float, "npshr": float, "margin": float, "ratio": float | None,
         "npshr_quoted": float | None, "quoted_ok": bool | None,
         "min_ratio": float | None, "min_margin": float | None,
         "npshr_tol_plus": float | None, "rated_q": float | None,
         "points": {"q": [], "npshr": []}, "curve": {"q": [], "npshr": []}}

    mechanical_run_check::

        {"pump_tag": str, "verdict": str, "passed": bool,
         "fully_assessed": bool, "verified": bool, "source": str,
         "criteria_label": str, "duration": {"value","unit"},
         "min_duration": {"value","unit"} | None, "duration_status": str,
         "verdict_label": str,   # "FAILED (unverified limits)" etc., as the node status
         "inputs_text": str,     # log / criteria / high-speed-rule power sentence
         "rows": [{"name", "role", "unit", "min", "max", "last", "limit",
                   "stabilisation", "status"}]}   # quantities as {"value","unit"}

    performance_plot::

        {"pump_tag": str, "fit": <curve_fit series>,
         "rated": {"q","head","power","head_fit","power_fit","eff_fit",
                   "in_range"} | None,
         "npsh": {"npsha","npshr_quoted","points": {...}, "curve": {...}} | None,
         "show": {"poly": bool, "spline": bool, "points": bool}}

``default_settings(kind: str) -> dict``
    The encoded (schema v2) settings of a fresh node of ``kind``.

``decode_settings(kind: str, encoded: dict) -> dict``
    Encoded (schema v2) node settings -> the runtime shape the desktop dialogs
    edit (``settings_codec.decode``), JSON-safe.  E.g. a rated point's
    ``{"q": {"value","unit"}}`` becomes ``"q": 833.0, "q_unit": "m³/h"``.

``encode_settings(kind: str, runtime: dict) -> dict``
    The inverse (``settings_codec.encode``), JSON-safe.  The web writes node
    settings only through this, so documents stay byte-compatible with the desktop.

``unit_options(dimension: str) -> [[label, pint_str], ...]``
    The display units of a dimension (``pumpflow.units.UNIT_OPTIONS``).

``convert(value, from_label, to_label, dimension, dens_rel=None) -> float | None``
    ``pumpflow.units.convert_display``; ``dens_rel`` (relative density) is needed
    for viscosity.  ``None`` when the value cannot be converted.

``explain(key: str) -> str``
    The info text ``"<title>\\n<text>"`` of a ``pumpflow.explain`` key, or of
    ``pump_type`` / ``impeller_diameter`` (the Rated Point help); ``""`` if unknown.

``standards() -> [[key, label]]`` / ``clients() -> [[key, label]]``
    The acceptance editions and client overlays; ``standard_label(key, client=None)``
    is the report-cover label of an edition plus overlay.

``atmosphere(unit: str) -> float``
    Standard atmosphere expressed in the pressure display unit ``unit``
    (``pumpflow.units.atm_in``): the g <-> a shift of a Test Points column.

``parse_paste(text, columns=None, pressure_ref="g") -> dict``
    The Test Points paste (``nodes.test_points.paste_rows``): spreadsheet text with
    an optional unit-header line becomes ``{"rows": [...], "columns": {key: label},
    "pressure_ref": "g" | "a", "vibration": bool, "warnings": [str]}``; ``rows``
    is empty for blank text.

``next_time(rows: list) -> str``
    The MRT Log "Add reading" rule (``nodes.mechanical_run._next_time``): the time of
    the last row with a valid ``HH:MM`` plus 15 minutes (wrapping at midnight);
    ``"00:00"`` when no row has one.  ``rows`` are ``{"time": str, ...}`` dicts.

``mrt_options() -> dict``
    ``{"roles": [str], "dimensions": [str], "role_dimensions": {role: dimension}}``:
    the channel roles (``pump.mechanical_run.ROLES``), the dimensions an MRT Log
    channel may use, and the dimension of each role's limits (the MRT Check
    overrides; roles without an entry have no editable limits).

``parse_mrt_paste(text: str, columns: list) -> list``
    The MRT Log paste (``nodes.mechanical_run.paste_rows``): spreadsheet text, with an
    optional header line naming channels and units, becomes
    ``[{"time": "HH:MM", "values": {channel: float | None}}]`` in each channel's own
    unit (``columns`` are the log's ``{"name","dimension","unit","role"}`` dicts);
    ``[]`` when nothing is usable.

``water_density(temp_c: float) -> float``
    kg/m3 of water at ``temp_c`` degC.  ``water_properties(temp_c) -> dict`` adds
    ``{"density", "kinematic_cst", "dynamic_cp"}``.

``pump_types() -> [[code, description]]`` and ``pump_type_hint(code) -> str``
    The API 610 pump types and the vibration-location sentence of the Rated Point form.

report_export::

        {"has_rated": bool, "overall_verdict_text": str,
         "pumps": [{"tag": str, "verdict_text": str | None,
                    "sections": ["Corrected", "Fitted", "Verdict", "MRT", "NPSH"],
                    "reportable": bool}]}

    ``pumps`` is one entry per connected branch (the desktop "Connected pumps" list);
    ``verdict_text`` is ``None`` without a performance verdict; ``reportable`` is true
    when the branch has a fitted curve (what ``export_report`` needs).
    ``overall_verdict_text`` is ``nodes.report_export.overall_verdict_text`` (the text
    after the pump count in the node status; ``"pending"`` before any verdict).

Extra views (read after ``evaluate``): ``rated_point`` ->
``{"standard_key": str, "client": str, "fluids": [name], "choice": str, "override": {"name","density_rel",
"density_kgm3","viscosity_cst"} | None}`` and ``fluid`` -> ``{"name","source",
"density_kgm3","density_rel","viscosity_cst","viscosity_cp" | None}``.

``export_report(doc: dict, fmt: str, lang: str | None = None) -> dict``
    ``{"filename": str, "mime": str, "base64": str}`` for ``fmt`` in ``docx``,
    ``html`` and ``summary_xlsx`` (the API 610 test data summary).  ``tex`` and
    ``pdf`` raise ``ValueError("desktop only")``; an unknown format, a project
    without a Report Export node or without a reportable branch raises
    ``ValueError``.  Files are written into a temporary directory.
"""

from __future__ import annotations

import base64
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from pump import Q_
from pump.quantity_io import to_json

from .numfmt import num as _nf
from . import settings_codec
from .engine import Graph
from .nodes.registry import grouped_node_kinds, make_node

__all__ = [
    "catalog",
    "evaluate",
    "node_view",
    "default_settings",
    "export_report",
    "decode_settings",
    "encode_settings",
    "unit_options",
    "convert",
    "explain",
    "standards",
    "clients",
    "standard_label",
    "water_density",
    "water_properties",
    "pump_types",
    "pump_type_hint",
    "atmosphere",
    "parse_paste",
    "next_time",
    "mrt_options",
    "parse_mrt_paste",
]

#: Kinds with a web form (the witness kinds).
WEB_FORM_KINDS = frozenset(
    {
        "rated_point",
        "fluid",
        "test_points",
        "correction",
        "curve_fit",
        "performance_plot",
        "compliance",
        "npsh",
        "mechanical_run",
        "mechanical_run_check",
        "report_export",
        "markdown_note",
    }
)

_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "html": "text/html",
    "summary_xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


# --------------------------------------------------------------------- helpers
def _jsonable(x: Any) -> Any:
    """Convert ``x`` to plain JSON values (NaN/inf -> None, Pint -> to_json)."""
    if x is None or isinstance(x, (bool, str)):
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, Q_):
        try:
            return _jsonable(to_json(x))
        except (TypeError, ValueError):
            return _jsonable(x.magnitude)
    if isinstance(x, np.ndarray):
        return [_jsonable(v) for v in x.tolist()]
    if isinstance(x, np.generic):
        return _jsonable(x.item())
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in x]
    return str(x)


def _f(q: Any, unit: str) -> Optional[float]:
    """Magnitude of quantity ``q`` in ``unit`` (``None`` when ``q`` is None)."""
    return None if q is None else float(q.to(unit).magnitude)


def _arr(a: Any) -> List[float]:
    return [float(v) for v in np.asarray(a, dtype=float)]


def _first_output(node, port: str):
    return (node.outputs_cache or {}).get(port)


# ----------------------------------------------------------------------- views
def _view_test_points(graph: Graph, node) -> dict:
    from .binding import row_efficiency, row_head, row_head_components
    from .nodes.test_points import _pint_of, geometry_from_settings

    s = node.settings
    cols = s.get("columns") or {}
    density = getattr(node, "_test_density", None)
    geom = geometry_from_settings(s)
    head_pint, eff_pint = _pint_of(cols, "head"), _pint_of(cols, "eff")
    rows = []
    for tr in node.to_signal(density).rows:
        try:
            head_q = row_head(tr, density, geom)
            eff_q = row_efficiency(tr, head_q, density)
            comps = None
            if geom is not None and not geom.is_empty:
                comps = {
                    k: _f(v, head_pint)
                    for k, v in row_head_components(tr, density, geom).items()
                }
            rows.append(
                {
                    "head": _f(head_q, head_pint),
                    "eff": _f(eff_q, eff_pint),
                    "components": comps,
                }
            )
        except Exception:
            rows.append({"head": None, "eff": None, "components": None})
    from pump.vibration import location_of_key, locations_for

    from .nodes.fluidpick import current_choice, resolve_fluid
    from .nodes.test_points import vibration_column_title, vibration_columns

    fluids = list(getattr(node, "_fluids", []) or [])
    chosen = resolve_fluid(fluids, s.get("fluid_choice"))
    pump_type = getattr(node, "_pump_type", None)
    where = ", ".join(loc.label for loc in locations_for(pump_type))
    vib_columns = []
    for k in vibration_columns(pump_type, s.get("rows") or []):
        loc, filtered = location_of_key(k)
        vib_columns.append(
            {
                "key": k,
                "title": vibration_column_title(k),
                "tooltip": (
                    f"{loc.label}: "
                    f"{'filtered (largest discrete frequency)' if filtered else 'overall'}"
                    f" bearing-housing velocity, RMS. {loc.where}"
                ),
            }
        )
    try:
        has_shutoff = bool(node.to_signal(density).has_shutoff())
    except Exception:
        has_shutoff = True
    return {
        "pump_tag": str(s.get("pump_tag", "")).strip(),
        "n_rows": len(rows),
        "head_unit": cols.get("head", "m"),
        "eff_unit": cols.get("eff", "%"),
        "rows": rows,
        "fluids": [f.name for f in fluids],
        "choice": current_choice(fluids, s.get("fluid_choice")),
        "has_shutoff": has_shutoff,
        "test_fluid": (
            None
            if chosen is None
            else {"name": chosen.name, "density_kgm3": _f(chosen.density, "kg/m**3")}
        ),
        "pump_type": pump_type or "",
        "vib_label": (
            f"Vibration columns (RMS, overall / filtered) · "
            f"{pump_type or 'pump type not set'}: {where}"
        ),
        "vib_columns": vib_columns,
    }


def _view_correction(graph: Graph, node) -> dict:
    from .nodes.correction import banner_message, viscous_summary
    from .nodes.fluidpick import current_choice

    fluids = list(getattr(node, "_fluids", []) or [])
    has_rated = bool(getattr(node, "_has_rated", True))
    has_fluid = bool(getattr(node, "_has_fluid", False))
    base = {
        "fluids": [f.name for f in fluids],
        "choice": current_choice(fluids, node.settings.get("fluid_choice")),
        "has_rated": has_rated,
        "has_fluid": has_fluid,
    }
    cc = _first_output(node, "CorrectedCurve")
    if cc is None:
        return base
    text, level = banner_message(
        node.state, node.status, has_rated, has_fluid, cc.viscous
    )
    return {
        **base,
        "pump_tag": cc.pump_tag,
        "target_speed": cc.target_speed,
        "viscous": cc.viscous,
        "viscous_text": viscous_summary(cc.viscous),
        "banner": {"text": text, "level": level},
        "before_after": list(cc.before_after or ()),
    }


def _fit_series(fitted, resolution: int = 160, spline: bool = True) -> dict:
    """Points, polynomial and spline series of a fitted model (canonical units)."""
    fitter = fitted.curve.fitter
    caps = np.asarray(fitter.capacities, dtype=float)
    heads = np.asarray(fitter.heads, dtype=float)
    try:
        powers = np.asarray(fitter.powers, dtype=float)
    except Exception:
        powers = np.array([])
    try:
        effs = np.asarray(fitter.efficiencies, dtype=float)
    except Exception:
        effs = np.array([])
    has_p = caps.size > 0 and powers.size == caps.size
    has_e = caps.size > 0 and effs.size == caps.size
    xs = (
        np.linspace(float(caps.min()), float(caps.max()), int(resolution))
        if caps.size
        else np.array([])
    )

    def poly(coeffs, ok):
        return _arr(np.polyval(coeffs, xs)) if ok and len(coeffs) else None

    out = {
        "pump_tag": fitted.pump_tag,
        "degree": int(fitted.degree),
        "r2": dict(fitted.r2 or {}),
        "points": {
            "q": _arr(caps),
            "head": _arr(heads),
            "power": _arr(powers) if has_p else None,
            "eff": _arr(effs) if has_e else None,
        },
        "poly": {
            "q": _arr(xs),
            "head": poly(fitted.head_coeffs, xs.size > 0),
            "power": poly(fitted.power_coeffs, has_p),
            "eff": poly(fitted.efficiency_coeffs, has_e),
        },
        "spline": None,
        "coefficients": {
            "head": _arr(fitted.head_coeffs),
            "power": _arr(fitted.power_coeffs),
            "eff": _arr(fitted.efficiency_coeffs),
        },
    }
    if spline and fitted.head_spline is not None:
        sx, sh = fitted.head_spline.sample(int(resolution))
        sp = {"q": _arr(sx), "head": _arr(sh), "power": None, "eff": None}
        if fitted.power_spline is not None:
            sp["power"] = _arr(fitted.power_spline.sample(int(resolution))[1])
        if fitted.efficiency_spline is not None:
            sp["eff"] = _arr(fitted.efficiency_spline.sample(int(resolution))[1])
        out["spline"] = sp
    return out


def _view_curve_fit(graph: Graph, node) -> dict:
    fitted = _first_output(node, "FittedModel")
    if fitted is None:
        return {}
    from .nodes.curve_fit import _coeff_text

    s = node.settings
    out = _fit_series(fitted, int(s.get("resolution", 160)), bool(s.get("spline")))
    out["r2_text"] = "  ·  ".join(
        f"R²({k})={_nf(v, '.4f')}" for k, v in fitted.r2.items()
    )
    out["coeff_text"] = _coeff_text(fitted)
    return out


def _view_compliance(graph: Graph, node) -> dict:
    res = _first_output(node, "ComplianceResult")
    if res is None:
        return {}
    from .nodes.compliance import param_cells

    rows = []
    for p in res.parameters:
        if p.informational:
            verdict = "info"
        elif not p.evaluated:
            verdict = "n/e"
        else:
            verdict = "pass" if p.passed else "fail"
        rows.append(
            {
                "name": p.name,
                "actual": p.actual,
                "predicted": p.predicted,
                "min": p.minimum,
                "max": p.maximum,
                "deviation": p.deviation,
                "tol": p.tolerance,
                "verdict": verdict,
                "note": p.note,
                "extrapolated": p.extrapolated,
                "verified": p.verified,
                "cells": param_cells(p),
            }
        )
    return {
        "pump_tag": res.pump_tag,
        "verdict_text": res.verdict_text,
        "verdict_label": res.verdict_label,
        "overall_pass": res.overall_pass,
        "criteria_label": res.criteria_label,
        "overridden": res.overridden,
        "override_reason": res.override_reason,
        "shutoff_waiver": res.shutoff_waiver,
        "unverified": list(res.unverified),
        "not_evaluated": list(res.not_evaluated),
        "parallel_ok": res.parallel_ok,
        "tolerances": dict(res.tolerances or {}),
        "default_tolerances": dict(res.default_tolerances or {}),
        "rows": rows,
    }


def _npsh_series(sig, n: int = 60) -> Optional[dict]:
    """Test points and fitted curve of an NPSH signal (m3/h, m)."""
    curve = getattr(sig, "curve", None)
    if curve is None:
        return None
    q = [_f(v, "m**3/h") for v in curve.q]
    r = [_f(v, "m") for v in curve.npshr]
    grid = np.linspace(min(q), max(q), n)
    fit = [_f(curve(Q_(float(g), "m**3/h")), "m") for g in grid]
    return {
        "points": {"q": q, "npshr": r},
        "curve": {"q": _arr(grid), "npshr": fit},
    }


def _view_npsh(graph: Graph, node) -> dict:
    from .nodes.npsh import verdict_label

    sig = _first_output(node, "NPSHResult")
    if sig is None:
        return {}
    res = sig.result
    crit = res.criteria
    rated = getattr(node, "_rated", None)
    series = _npsh_series(sig) or {"points": None, "curve": None}
    return {
        "pump_tag": sig.pump_tag,
        "mode": node.settings.get("mode", "points"),
        "status": res.status,
        "verdict": verdict_label(res),
        "verified": bool(res.verified),
        "criteria_label": sig.criteria_label,
        "npsha": _f(res.npsha, "m"),
        "npshr": _f(res.npshr, "m"),
        "margin": _f(res.margin, "m"),
        "ratio": res.ratio,
        "npshr_quoted": _f(res.npshr_quoted, "m"),
        "quoted_ok": res.quoted_ok,
        "min_ratio": crit.min_ratio,
        "min_margin": _f(crit.min_margin, "m"),
        "npshr_tol_plus": crit.npshr_tol_plus,
        "rated_q": _f(getattr(rated, "q", None), "m**3/h"),
        **series,
    }


def _mrt_inputs_text(node) -> str:
    """The "Log / Criteria / High-speed rule power" sentence of the MRT Check dialog."""
    run_set = getattr(node, "_run_set", None)
    if run_set is None:
        return "No log connected: wire an MRT Log into this node."
    rated = getattr(node, "_rated", None)
    fitted = getattr(node, "_fitted", None)
    if rated is not None:
        criteria = f"Criteria: {rated.standard_key}"
        if rated.client:
            criteria += f" + {rated.client}"
        if rated.pump_type:
            criteria += f", pump type {rated.pump_type}"
        criteria += "."
    else:
        criteria = "Criteria: library default (no rated point wired)."
    power = (
        "High-speed rule power: BEP of the fitted curve."
        if fitted is not None
        else "High-speed rule power: rated power (no fitted curve wired)."
    )
    return "  ".join(
        [
            f"Log: {run_set.pump_tag}, {len(run_set.log.readings)} readings.",
            criteria,
            power,
        ]
    )


def _view_mrt_check(graph: Graph, node) -> dict:
    from .nodes.mechanical_run import verdict_label

    sig = _first_output(node, "MechanicalRunResult")
    if sig is None:
        return {}
    res = sig.result
    rows = [
        {
            "name": c.name,
            "role": c.role,
            "unit": c.unit,
            "min": c.min,
            "max": c.max,
            "last": c.last,
            "limit": c.limit,
            "stabilisation": c.stabilisation,
            "status": c.status,
        }
        for c in res.channels
    ]
    rules = [
        {
            "key": r.key,
            "name": r.name,
            "value": r.value,
            "limit": r.limit,
            "unit": r.unit,
            "status": r.status,
            "note": r.note,
        }
        for r in getattr(res, "rules", ()) or ()
    ]
    return {
        "pump_tag": sig.pump_tag,
        "verdict_label": verdict_label(res),
        "inputs_text": _mrt_inputs_text(node),
        "verdict": res.verdict,
        "passed": res.passed,
        "fully_assessed": res.fully_assessed,
        "verified": res.verified,
        "source": res.source,
        "criteria_label": sig.criteria_label,
        "duration": res.duration,
        "min_duration": res.min_duration,
        "duration_status": res.duration_status,
        "lubrication": getattr(res, "lubrication", None),
        "rows": rows,
        "rules": rules,
    }


def _view_performance_plot(graph: Graph, node) -> dict:
    inputs = graph.gather_inputs(node)
    fitted = node.first(inputs, "FittedModel")
    if fitted is None:
        return {}
    rated = node.first(inputs, "RatedPoint")
    npsh = node.first(inputs, "NPSHResult")
    s = node.settings
    fit = _fit_series(fitted, 160, bool(s.get("show_spline", True)))
    rated_view = None
    if rated is not None:
        q = _f(rated.q, "m**3/h")
        pts = fit["points"]["q"]
        eff_c, pow_c = fitted.efficiency_coeffs, fitted.power_coeffs
        rated_view = {
            "q": q,
            "head": _f(rated.head, "m"),
            "power": _f(rated.power, "kW"),
            "head_fit": float(np.polyval(fitted.head_coeffs, q)),
            "power_fit": float(np.polyval(pow_c, q)) if len(pow_c) else None,
            "eff_fit": float(np.polyval(eff_c, q)) if len(eff_c) else None,
            "in_range": bool(pts and min(pts) <= q <= max(pts)),
        }
    npsh_view = None
    if npsh is not None and getattr(npsh, "curve", None) is not None:
        npsh_view = {
            "npsha": _f(getattr(npsh.result, "npsha", None), "m"),
            "npshr_quoted": _f(getattr(npsh.result, "npshr_quoted", None), "m"),
            **(_npsh_series(npsh) or {}),
        }
    return {
        "pump_tag": fitted.pump_tag,
        "fit": fit,
        "rated": rated_view,
        "npsh": npsh_view,
        "show": {
            "poly": bool(s.get("show_poly", True)),
            "spline": bool(s.get("show_spline", True)),
            "points": bool(s.get("show_points", True)),
        },
    }


def _view_rated_point(graph: Graph, node) -> dict:
    from .nodes.fluidpick import current_choice

    from .nodes.rated_point import _standard_keys

    fluids = list(getattr(node, "_fluids", []) or [])
    ov = getattr(node, "_fluid_override", None)
    standard_key, client = _standard_keys(node.settings)
    return {
        "standard_key": standard_key,
        "client": client,
        "fluids": [f.name for f in fluids],
        "choice": current_choice(fluids, node.settings.get("fluid_choice")),
        "override": (
            None
            if ov is None
            else {
                "name": ov.name,
                "density_rel": ov.density_rel,
                "density_kgm3": _f(ov.density, "kg/m**3"),
                "viscosity_cst": _f(ov.viscosity, "cSt"),
            }
        ),
    }


def _view_fluid(graph: Graph, node) -> dict:
    spec = _first_output(node, "FluidSpec")
    if spec is None:
        return {}
    cp = None
    if spec.source == "water" and spec.temperature is not None:
        cp = water_properties(_f(spec.temperature, "degC"))["dynamic_cp"]
    return {
        "name": spec.name,
        "source": spec.source,
        "density_kgm3": _f(spec.density, "kg/m**3"),
        "density_rel": spec.density_rel,
        "viscosity_cst": _f(spec.viscosity, "cSt"),
        "viscosity_cp": cp,
    }


def _view_report_export(graph: Graph, node) -> dict:
    from .nodes.report_export import overall_verdict_text

    rated, branches = node._bundle(graph.gather_inputs(node))
    pumps = []
    for b in branches:
        sections = [
            label
            for label, present in (
                ("Corrected", b.corrected),
                ("Fitted", b.fitted),
                ("Verdict", b.compliance),
                ("MRT", b.mechanical),
                ("NPSH", b.npsh),
            )
            if present is not None
        ]
        pumps.append(
            {
                "tag": b.pump_tag,
                "verdict_text": (
                    b.compliance.verdict_text if b.compliance is not None else None
                ),
                "sections": sections,
                "reportable": b.fitted is not None,
            }
        )
    checks = [b.compliance for b in branches if b.compliance is not None]
    return {
        "has_rated": rated is not None,
        "overall_verdict_text": overall_verdict_text(checks),
        "pumps": pumps,
    }


def _view_mrt_log(graph: Graph, node) -> dict:
    """The pump type of the wired rated point (selects the vibration channels)."""
    return {"pump_type": getattr(node, "_pump_type", None)}


_VIEWS = {
    "rated_point": _view_rated_point,
    "mechanical_run": _view_mrt_log,
    "fluid": _view_fluid,
    "test_points": _view_test_points,
    "correction": _view_correction,
    "curve_fit": _view_curve_fit,
    "compliance": _view_compliance,
    "npsh": _view_npsh,
    "mechanical_run_check": _view_mrt_check,
    "performance_plot": _view_performance_plot,
    "report_export": _view_report_export,
}


def node_view(graph: Graph, node) -> dict:
    """Per-kind display data of an evaluated ``node`` (``{}`` when none)."""
    builder = _VIEWS.get(node.kind)
    if builder is None:
        return {}
    return _jsonable(builder(graph, node))


# ------------------------------------------------------------------ public API
def catalog() -> list:
    """Node kinds in toolbox order, with ports and the ``has_web_form`` flag."""
    out = []
    for group, kinds in grouped_node_kinds():
        for kind, title, glyph in kinds:
            node = make_node(kind)
            out.append(
                {
                    "kind": kind,
                    "title": title,
                    "glyph": glyph,
                    "group": group,
                    "inputs": [
                        {"name": p.name, "type": p.signal_type, "multi": bool(p.multi)}
                        for p in node.inputs
                    ],
                    "outputs": [
                        {"name": p.name, "type": p.signal_type} for p in node.outputs
                    ],
                    "has_web_form": kind in WEB_FORM_KINDS,
                }
            )
    return out


def evaluate(doc: dict, sep: Optional[str] = None) -> dict:
    """Evaluate a project document and return the JSON view of every node.

    ``sep`` is the viewer's decimal separator ("." or ","): the statuses and
    the formatted view texts use it.  ``None`` keeps the point.
    """
    from pump.utilities.numbers import POINT, decimal

    with decimal(sep if sep in (".", ",") else POINT):
        return _evaluate(doc)


def _evaluate(doc: dict) -> dict:
    graph = Graph.from_dict(doc)
    graph.evaluate()
    nodes: Dict[str, dict] = {}
    errors: List[str] = []
    for node in graph.nodes:
        try:
            view = node_view(graph, node)
        except Exception as exc:  # one bad view never breaks the response
            view = {"error": f"{type(exc).__name__}: {exc}"}
        nodes[node.node_id] = {
            "kind": node.kind,
            "state": node.state,
            "status": node.status,
            "badge": list(node.badge) if node.badge else None,
            "notes": list(node.badge_notes),
            "view": view,
        }
        if node.state == "error":
            errors.append(node.node_id)
    return {"nodes": nodes, "errors": errors}


def default_settings(kind: str) -> dict:
    """Encoded (schema v2) settings of a fresh node of ``kind``."""
    node = make_node(kind)
    return _jsonable(settings_codec.encode(kind, node.serialize_settings()))


# ------------------------------------------------------- form helpers (sprint 6)
def decode_settings(kind: str, encoded: dict) -> dict:
    """Encoded (v2) settings -> runtime settings (the shape the dialogs edit)."""
    return _jsonable(settings_codec.decode(kind, encoded))


def encode_settings(kind: str, runtime: dict) -> dict:
    """Runtime settings -> encoded (v2) settings, as the desktop would save them."""
    return _jsonable(settings_codec.encode(kind, runtime))


def unit_options(dimension: str) -> list:
    """``[[label, pint_str], ...]`` display units of ``dimension``."""
    from .units import UNIT_OPTIONS

    return [[label, pint] for label, pint in UNIT_OPTIONS[dimension]]


def convert(
    value: Any,
    from_label: str,
    to_label: str,
    dimension: str,
    dens_rel: Optional[float] = None,
) -> Optional[float]:
    """``value`` re-expressed from one display unit to another (``None`` on failure)."""
    from .units import convert_display

    try:
        out = convert_display(float(value), dimension, from_label, to_label, dens_rel)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    return _jsonable(float(out))


def _plain(html_text: str) -> str:
    """Help text written as simple HTML -> plain text (paragraphs kept)."""
    import html
    import re

    t = re.sub(r"</p>\s*", "\n\n", html_text)
    t = re.sub(r"<br\s*/?>\s*", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"[ \t]*\n[ \t]*", "\n", html.unescape(t)).strip()


def explain(key: str) -> str:
    """The info text of ``key``: ``"<title>\\n<text>"`` (``""`` when there is none).

    Keys are those of ``pumpflow.explain.FORMULAS`` plus the two help texts of the
    Rated Point dialog, ``pump_type`` and ``impeller_diameter``.
    """
    from .explain import tooltip

    try:
        return tooltip(key)
    except KeyError:
        pass
    from .nodes.rated_point import IMPELLER_DIAMETER_HELP, PUMP_TYPE_HELP

    helps = {
        "pump_type": ("API 610 pump type", PUMP_TYPE_HELP),
        "impeller_diameter": ("Impeller diameter", IMPELLER_DIAMETER_HELP),
    }
    if key in helps:
        title, body = helps[key]
        return f"{title}\n{_plain(body)}"
    return ""


def standards() -> list:
    """``[[key, label]]`` of the acceptance editions."""
    from .binding import available_standards

    return [[k, label] for k, label in available_standards()]


def clients() -> list:
    """``[[key, label]]`` of the client overlays."""
    from .binding import available_clients

    return [[k, label] for k, label in available_clients()]


def standard_label(key: str, client: Optional[str] = None) -> str:
    """Report-cover label of an edition (+ optional client overlay)."""
    from .binding import standard_label as _label

    return _label(key, client or None)


def atmosphere(unit: str) -> float:
    """Standard atmosphere in the pressure display unit ``unit``."""
    from .units import atm_in

    return float(atm_in(unit))


def parse_paste(
    text: str, columns: Optional[dict] = None, pressure_ref: str = "g"
) -> dict:
    """Test Points paste: spreadsheet text -> rows, column units and pressure ref."""
    from .nodes.test_points import paste_rows

    res = paste_rows(text, columns or {}, pressure_ref or "g")
    if res is None:
        return {
            "rows": [],
            "columns": dict(columns or {}),
            "pressure_ref": pressure_ref or "g",
            "vibration": False,
            "warnings": [],
        }
    return _jsonable(res)


def water_density(temp_c: float) -> float:
    """Density of water at ``temp_c`` degC in kg/m3."""
    from .binding import water_density_kgm3

    return float(water_density_kgm3(float(temp_c)))


def water_properties(temp_c: float) -> dict:
    """Density (kg/m3), kinematic (cSt) and dynamic (cP) viscosity of water."""
    from .binding import (
        water_density_kgm3,
        water_dynamic_viscosity_cP,
        water_kinematic_viscosity_cst,
    )

    t = float(temp_c)
    return {
        "density": float(water_density_kgm3(t)),
        "kinematic_cst": float(water_kinematic_viscosity_cst(t)),
        "dynamic_cp": float(water_dynamic_viscosity_cP(t)),
    }


def pump_types() -> list:
    """``[[code, description]]`` of the API 610 pump types."""
    from pump.vibration import PUMP_TYPES

    return [[code, desc] for code, desc in PUMP_TYPES.items()]


def pump_type_hint(code: Optional[str]) -> str:
    """Vibration locations and limit table of a pump type (the Rated Point hint)."""
    from pump.vibration import PUMP_TYPES

    from .nodes.rated_point import pump_type_hint as _hint

    code = (code or "").strip().upper()
    return _hint(code if code in PUMP_TYPES else None)


def export_report(doc: dict, fmt: str, lang: Optional[str] = None) -> dict:
    """Write one report file and return it as ``{"filename", "mime", "base64"}``."""
    if fmt in ("tex", "pdf"):
        raise ValueError("desktop only")
    if fmt not in _MIME:
        raise ValueError(f"Unknown report format: {fmt!r}")

    from pump.utilities.numbers import decimal, decimal_for_language

    graph = Graph.from_dict(doc)
    report = [n for n in graph.nodes if n.kind == "report_export"]
    language = lang or (report[0].settings.get("language") if report else None) or "en"
    # the whole export (charts included) uses the report language's separator
    with decimal(decimal_for_language(language)):
        return _export_report(graph, fmt, language)


def _export_report(graph, fmt: str, language: str) -> dict:
    from .binding import (
        assemble_report_data,
        export_reports,
        export_test_summary,
        test_data_summaries,
    )
    from .export_cli import report_inputs, report_notes

    graph.evaluate()
    try:
        rated, branches, s = report_inputs(graph)
    except SystemExit as exc:
        raise ValueError(str(exc) or "No Report Export node in this project.")
    if rated is None:
        raise ValueError("Report Export has no Rated Point.")
    reportable = [b for b in branches if b.fitted is not None]
    if not reportable:
        raise ValueError("No branch has a fitted curve to report.")

    stem = Path(s.get("filename") or "Report").stem or "Report"
    with tempfile.TemporaryDirectory() as tmp:
        if fmt == "summary_xlsx":
            from pump.utilities.report import LocalizationHelper

            summaries = test_data_summaries(
                rated, reportable, s, LocalizationHelper(language)._
            )
            paths, errors = export_test_summary(
                summaries,
                ["xlsx"],
                language=language,
                out_dir=tmp,
                stem=f"{stem}_test_summary",
            )
            key = "xlsx"
        else:
            data = assemble_report_data(
                rated,
                branches,
                s.get("equipment", {}),
                settings=s,
                notes=report_notes(graph),
            )
            paths, errors = export_reports(
                data, [fmt], language=language, out_dir=tmp, stem=stem
            )
            key = fmt
        if key in errors or key not in paths:
            raise ValueError(errors.get(key, f"Could not write the {fmt} report."))
        path = Path(paths[key])
        content = path.read_bytes()
    return {
        "filename": path.name,
        "mime": _MIME[fmt],
        "base64": base64.b64encode(content).decode("ascii"),
    }


def next_time(rows: list) -> str:
    """Time of the next MRT Log reading: last valid ``HH:MM`` + 15 min (the desktop rule)."""
    from .nodes.mechanical_run import _next_time

    return _next_time([r for r in (rows or []) if isinstance(r, dict)])


def mrt_options() -> dict:
    """Channel roles, channel dimensions, the dimension of each role's limits,
    the lubrication systems and the optional standard-channel groups."""
    from pump.mechanical_run import LUBRICATION, LUBRICATION_LABELS, ROLES

    from .nodes.mechanical_run import _DIMENSIONS, CHANNEL_GROUPS

    return {
        "roles": list(ROLES),
        "dimensions": list(_DIMENSIONS),
        "role_dimensions": dict(settings_codec.ROLE_DIMENSIONS),
        "lubrication": [[k, LUBRICATION_LABELS[k]] for k in LUBRICATION],
        "channel_groups": [list(g) for g in CHANNEL_GROUPS],
    }


def mrt_standard_channels(settings: dict, pump_type: Optional[str] = None) -> list:
    """MRT Log columns after a change of lubrication system or channel groups
    (the desktop rule, ``nodes.mechanical_run.apply_standard_channels``)."""
    from .nodes.mechanical_run import apply_standard_channels

    return _jsonable(apply_standard_channels(dict(settings or {}), pump_type or None))


def parse_mrt_paste(text: str, columns: list) -> list:
    """MRT Log paste: spreadsheet text -> readings in the channels' own units."""
    from .nodes.mechanical_run import paste_rows

    cols = [c for c in (columns or []) if isinstance(c, dict)]
    return _jsonable(paste_rows(text or "", cols))
