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
