"""
sample_data
===========

A realistic, seeded **single-pump** FAT dataset (UI_SPEC: "Use realistic seeded
example data").  It is expressed in the exact data-exchange JSON shape of
UI_SPEC §6.2 — including locale-style comma-decimal strings — so it also serves
as a fixture proving the importer round-trips real ``.json`` files.

Engineering sketch (light-hydrocarbon service, SG ≈ 0.736):
  - rated point  Q = 833 m³/h · H = 73 m · N = 1750 rpm · P = 252 kW · Hso = 117 m
  - six measured points on test water (~34 °C, ~1799 rpm), bracketing the rated
    flow from part-load to overload, with the §6.2 example row included verbatim.
"""

from __future__ import annotations

from typing import Dict, List

from .persistence import testset_from_json

# UI_SPEC §6.2 shape — note the mixed comma/dot decimals on purpose.
SINGLE_PUMP_JSON = {
    "unit": "bar",
    "rated": {
        "tag": "B-2351105",
        "standard": "API610 (12a ed.) / ISO 13709 + N-553",
        "q_m3h": "833",
        "head_m": "73",
        "n_rpm": "1750",
        "power_kw": "252",
        "eff_pct": "61",
        "dens_rel": "0,736",
        "visc_nom_cst": "0,567",
        "head_shutoff": "117",
        "parallel": False,
    },
    "pump_tag": "B-2351105A",
    "points": [
        {"q": "300",     "p_suc": "1,80", "p_dis": "12,53", "temp_c": "34", "power": "248",    "n_rpm": "1799"},
        {"q": "500",     "p_suc": "1,80", "p_dis": "11,56", "temp_c": "34", "power": "270",    "n_rpm": "1800"},
        {"q": "700",     "p_suc": "1,80", "p_dis": "10,39", "temp_c": "33", "power": "288",    "n_rpm": "1798"},
        {"q": "858,29",  "p_suc": "1,81", "p_dis": "9,47",  "temp_c": "34", "head": "78.552", "power": "298,69", "n_rpm": "1799"},
        {"q": "1000",    "p_suc": "1,80", "p_dis": "7,85",  "temp_c": "35", "power": "308",    "n_rpm": "1801"},
        {"q": "1100",    "p_suc": "1,80", "p_dis": "6,48",  "temp_c": "34", "power": "312",    "n_rpm": "1800"},
    ],
}


# A second physical unit for the optional two-pump (A/B) demonstration — same
# service/rated point, its own measured rows (slightly different machine).
SECOND_PUMP_POINTS = {
    "pump_tag": "B-2351105B",
    "points": [
        {"q": "300",    "p_suc": "1,80", "p_dis": "12,30", "temp_c": "35", "power": "252",    "n_rpm": "1801"},
        {"q": "500",    "p_suc": "1,80", "p_dis": "11,38", "temp_c": "35", "power": "274",    "n_rpm": "1800"},
        {"q": "700",    "p_suc": "1,80", "p_dis": "10,15", "temp_c": "34", "power": "291",    "n_rpm": "1799"},
        {"q": "860",    "p_suc": "1,80", "p_dis": "9,20",  "temp_c": "34", "power": "301",    "n_rpm": "1800"},
        {"q": "1000",   "p_suc": "1,80", "p_dis": "7,60",  "temp_c": "35", "power": "310",    "n_rpm": "1802"},
        {"q": "1100",   "p_suc": "1,80", "p_dis": "6,20",  "temp_c": "34", "power": "315",    "n_rpm": "1801"},
    ],
}


# Ad-hoc points for the Performance Explorer demo — a datasheet/guarantee point
# and a what-if alternate duty, overlaid as markers on the live chart.
EXPLORE_POINTS: List[Dict] = [
    {"label": "Guarantee", "q": 833.0, "head": 73.0, "power": 252.0, "eff": 61.0},
    {"label": "Alt duty", "q": 950.0, "head": 62.0, "power": 0.0, "eff": 0.0},
]


# ---------------------------------------------------------------------------
# Sample .pumpflow project (UI_SPEC §6.1)
# ---------------------------------------------------------------------------
#
# A complete single-pump FAT pipeline expressed in the project-file shape that
# ``canvas/scene.py`` ``to_dict`` / ``load_dict`` round-trips:
#
#     {"nodes": [{id, kind, x, y, settings}], "edges": [{src_node, src_port,
#                                                        dst_node, dst_port}]}
#
# The node settings below are the *full* default settings of each node kind
# (see the corresponding ``default_settings`` in ``pumpflow/nodes/*.py``), so
# the document is a fixed point of ``to_dict(load_dict(doc))`` — loading then
# re-serializing yields the same dict.  Keep this builder Qt-free: it is the
# single source for ``examples/sample_project.pumpflow`` and for the headless
# regeneration in the round-trip test.


def _test_rows() -> List[dict]:
    """The §6.2 measured rows, normalized to the test-points node settings shape."""
    tps = testset_from_json(SINGLE_PUMP_JSON)
    return [
        {
            "q": r.q_m3h, "p_suc": r.p_suction, "p_dis": r.p_discharge,
            "temp_c": r.temp_c, "n": r.speed_rpm, "power": r.power_kw,
            "head": r.head_m, "eff": r.efficiency_pct,
        }
        for r in tps.rows
    ]


def sample_project_doc() -> Dict:
    """Return the canonical single-pump ``.pumpflow`` document (Qt-free).

    Pipeline (left → right): Rated Point + Test Points → Speed Correction →
    Curve Fit → {Performance Plot, Compliance Check} → Report Export.
    """
    tps = testset_from_json(SINGLE_PUMP_JSON)
    nodes = [
        {
            "id": "rated", "kind": "rated_point", "x": -560.0, "y": -40.0,
            "settings": {
                "tag": "B-2351105",
                "standard": "API610 (12a ed.) / ISO 13709 + N-553",
                "q": 833.0, "head": 73.0, "n": 1750.0, "power": 252.0,
                "eff": 61.0, "head_shutoff": 117.0,
                "dens_rel": 0.736, "visc": 0.567,
                "unit": "bar", "parallel": False, "fluid_name": "Rated fluid",
            },
        },
        {
            "id": "test_a", "kind": "test_points", "x": -560.0, "y": 220.0,
            "settings": {
                "pump_tag": tps.pump_tag,
                "unit": tps.pressure_unit,
                "rows": _test_rows(),
            },
        },
        {
            "id": "corr_a", "kind": "correction", "x": -240.0, "y": 90.0,
            "settings": {
                "lock_to_rated": True, "target_speed": 1750.0,
                "apply_speed": True, "apply_density": True,
                "apply_viscosity": False, "degree": 3,
            },
        },
        {
            "id": "fit_a", "kind": "curve_fit", "x": 40.0, "y": 90.0,
            "settings": {"degree": 3, "spline": True, "resolution": 160},
        },
        {
            "id": "plot_a", "kind": "performance_plot", "x": 320.0, "y": -60.0,
            "settings": {
                "show_poly": True, "show_spline": True, "show_points": True,
                "head_ylim": None, "power_ylim": None, "eff_ylim": None,
            },
        },
        {
            "id": "check_a", "kind": "compliance", "x": 320.0, "y": 200.0,
            "settings": {"tolerances": {}},
        },
        {
            "id": "report", "kind": "report_export", "x": 620.0, "y": 90.0,
            "settings": {
                "language": "en", "template_path": "", "out_dir": "", "filename": "",
                "equipment": {
                    k: "" for k in
                    ["Manufacturer", "Model", "Serial No.", "Type", "Driver", "Test bench"]
                },
            },
        },
    ]
    edges = [
        {"src_node": "rated",   "src_port": "RatedPoint",        "dst_node": "corr_a",  "dst_port": "RatedPoint"},
        {"src_node": "test_a",  "src_port": "TestPointSet",      "dst_node": "corr_a",  "dst_port": "TestPointSet"},
        {"src_node": "corr_a",  "src_port": "CorrectedCurve",    "dst_node": "fit_a",   "dst_port": "CorrectedCurve"},
        {"src_node": "fit_a",   "src_port": "FittedModel",       "dst_node": "plot_a",  "dst_port": "FittedModel"},
        {"src_node": "rated",   "src_port": "RatedPoint",        "dst_node": "plot_a",  "dst_port": "RatedPoint"},
        {"src_node": "fit_a",   "src_port": "FittedModel",       "dst_node": "check_a", "dst_port": "FittedModel"},
        {"src_node": "rated",   "src_port": "RatedPoint",        "dst_node": "check_a", "dst_port": "RatedPoint"},
        {"src_node": "rated",   "src_port": "RatedPoint",        "dst_node": "report",  "dst_port": "RatedPoint"},
        {"src_node": "corr_a",  "src_port": "CorrectedCurve",    "dst_node": "report",  "dst_port": "branch"},
        {"src_node": "fit_a",   "src_port": "FittedModel",       "dst_node": "report",  "dst_port": "branch"},
        {"src_node": "check_a", "src_port": "ComplianceResult",  "dst_node": "report",  "dst_port": "branch"},
    ]
    return {"nodes": nodes, "edges": edges}


def explore_project_doc() -> Dict:
    """Return the interactive-exploration ``.pumpflow`` document (Qt-free).

    Pipeline: Rated Point + Test Points → Speed Correction → Curve Fit, with the
    measured set, the fitted model, the rated point and two ad-hoc Point markers
    all feeding the **Performance Explorer** (the interactive pyqtgraph chart).
    """
    tps = testset_from_json(SINGLE_PUMP_JSON)
    nodes = [
        {
            "id": "rated", "kind": "rated_point", "x": -560.0, "y": -120.0,
            "settings": {
                "tag": "B-2351105",
                "standard": "API610 (12a ed.) / ISO 13709 + N-553",
                "q": 833.0, "head": 73.0, "n": 1750.0, "power": 252.0,
                "eff": 61.0, "head_shutoff": 117.0,
                "dens_rel": 0.736, "visc": 0.567,
                "unit": "bar", "parallel": False, "fluid_name": "Rated fluid",
            },
        },
        {
            "id": "test_a", "kind": "test_points", "x": -560.0, "y": 140.0,
            "settings": {
                "pump_tag": tps.pump_tag,
                "unit": tps.pressure_unit,
                "rows": _test_rows(),
            },
        },
        {
            "id": "corr_a", "kind": "correction", "x": -260.0, "y": 140.0,
            "settings": {
                "lock_to_rated": True, "target_speed": 1750.0,
                "apply_speed": True, "apply_density": True,
                "apply_viscosity": False, "degree": 3,
            },
        },
        {
            "id": "fit_a", "kind": "curve_fit", "x": 0.0, "y": 140.0,
            "settings": {"degree": 3, "spline": True, "resolution": 160},
        },
        {
            "id": "pt_guar", "kind": "point", "x": -560.0, "y": 360.0,
            "settings": EXPLORE_POINTS[0],
        },
        {
            "id": "pt_alt", "kind": "point", "x": -360.0, "y": 360.0,
            "settings": EXPLORE_POINTS[1],
        },
        {
            "id": "explore", "kind": "explore_plot", "x": 300.0, "y": 60.0,
            "settings": {},
        },
    ]
    edges = [
        {"src_node": "rated",   "src_port": "RatedPoint",     "dst_node": "corr_a",  "dst_port": "RatedPoint"},
        {"src_node": "test_a",  "src_port": "TestPointSet",   "dst_node": "corr_a",  "dst_port": "TestPointSet"},
        {"src_node": "corr_a",  "src_port": "CorrectedCurve", "dst_node": "fit_a",   "dst_port": "CorrectedCurve"},
        {"src_node": "fit_a",   "src_port": "FittedModel",    "dst_node": "explore", "dst_port": "FittedModel"},
        {"src_node": "test_a",  "src_port": "TestPointSet",   "dst_node": "explore", "dst_port": "TestPointSet"},
        {"src_node": "rated",   "src_port": "RatedPoint",     "dst_node": "explore", "dst_port": "RatedPoint"},
        {"src_node": "pt_guar", "src_port": "Point",          "dst_node": "explore", "dst_port": "Points"},
        {"src_node": "pt_alt",  "src_port": "Point",          "dst_node": "explore", "dst_port": "Points"},
    ]
    return {"nodes": nodes, "edges": edges}
