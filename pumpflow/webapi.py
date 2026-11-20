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

``evaluate(doc: dict) -> dict``
    Build a graph from a ``.pumpflow`` document (v1 or v2), evaluate it and
    return::

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
                   "components": {"pressure","velocity","elevation","total"} | None}]}

    correction::

        {"pump_tag": str, "target_speed": {"value","unit"},
         "viscous": {"B","C_Q","C_H","C_eta"} | None,
         "before_after": [{"measured": {...}, "corrected": {...}}]}

    curve_fit (and the series part of performance_plot, as ``fit``)::

        {"pump_tag": str, "degree": int, "r2": {"head","power","efficiency"},
         "points": {"q": [], "head": [], "power": [] | None, "eff": [] | None},
         "poly":   {"q": [], "head": [], "power": [] | None, "eff": [] | None},
         "spline": {same keys} | None,
         "coefficients": {"head": [], "power": [], "eff": []}}

    compliance::

        {"pump_tag": str, "verdict_text": str, "verdict_label": str,
         "overall_pass": bool, "criteria_label": str, "overridden": bool,
         "override_reason": str, "unverified": [str], "not_evaluated": [str],
         "parallel_ok": bool | None, "tolerances": dict,
         "rows": [{"name", "actual", "predicted", "min", "max", "deviation",
                   "tol", "verdict": "pass" | "fail" | "info" | "n/e",
                   "note", "extrapolated", "verified"}]}

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

from . import settings_codec
from .engine import Graph
from .nodes.registry import grouped_node_kinds, make_node

__all__ = ["catalog", "evaluate", "node_view", "default_settings", "export_report"]

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
    return {
        "pump_tag": str(s.get("pump_tag", "")).strip(),
        "n_rows": len(rows),
        "head_unit": cols.get("head", "m"),
        "eff_unit": cols.get("eff", "%"),
        "rows": rows,
    }


def _view_correction(graph: Graph, node) -> dict:
    cc = _first_output(node, "CorrectedCurve")
    if cc is None:
        return {}
    return {
        "pump_tag": cc.pump_tag,
        "target_speed": cc.target_speed,
        "viscous": cc.viscous,
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
    s = node.settings
    return _fit_series(fitted, int(s.get("resolution", 160)), bool(s.get("spline")))


def _view_compliance(graph: Graph, node) -> dict:
    res = _first_output(node, "ComplianceResult")
    if res is None:
        return {}
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
        "unverified": list(res.unverified),
        "not_evaluated": list(res.not_evaluated),
        "parallel_ok": res.parallel_ok,
        "tolerances": dict(res.tolerances or {}),
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


def _view_mrt_check(graph: Graph, node) -> dict:
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
    return {
        "pump_tag": sig.pump_tag,
        "verdict": res.verdict,
        "passed": res.passed,
        "fully_assessed": res.fully_assessed,
        "verified": res.verified,
        "source": res.source,
        "criteria_label": sig.criteria_label,
        "duration": res.duration,
        "min_duration": res.min_duration,
        "duration_status": res.duration_status,
        "rows": rows,
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


_VIEWS = {
    "test_points": _view_test_points,
    "correction": _view_correction,
    "curve_fit": _view_curve_fit,
    "compliance": _view_compliance,
    "npsh": _view_npsh,
    "mechanical_run_check": _view_mrt_check,
    "performance_plot": _view_performance_plot,
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


def evaluate(doc: dict) -> dict:
    """Evaluate a project document and return the JSON view of every node."""
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


def export_report(doc: dict, fmt: str, lang: Optional[str] = None) -> dict:
    """Write one report file and return it as ``{"filename", "mime", "base64"}``."""
    if fmt in ("tex", "pdf"):
        raise ValueError("desktop only")
    if fmt not in _MIME:
        raise ValueError(f"Unknown report format: {fmt!r}")

    from .binding import (
        assemble_report_data,
        export_reports,
        export_test_summary,
        test_data_summaries,
    )
    from .export_cli import report_inputs, report_notes

    graph = Graph.from_dict(doc)
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

    language = lang or s.get("language") or "en"
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
