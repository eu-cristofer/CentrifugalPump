"""
Browser JSON API (``pumpflow.webapi``): plain JSON in, plain JSON out.

``evaluate`` must agree with the engine and ``expected.json``, the views must
carry the desktop numbers, the exports must be real files, and the module must
import (and evaluate P-9001A) with every Qt binding blocked.
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pumpflow import settings_codec, webapi
from pumpflow.engine import Graph
from pumpflow.persistence import read_json

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "v1"
P9001A = ROOT / "examples" / "user" / "P-9001A_MRT_reference.pumpflow"
P9001B = ROOT / "examples" / "user" / "P-9001B_witness_2026-11-19.pumpflow"
FILES = sorted(FIXTURES.glob("*.pumpflow")) + [P9001A, P9001B]

WITNESS = {
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


@pytest.fixture(scope="module")
def expected():
    return json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def doc_a():
    return read_json(str(P9001A))


@pytest.fixture(scope="module")
def result_a(doc_a):
    return webapi.evaluate(doc_a)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_evaluate_is_strict_json(path):
    out = webapi.evaluate(read_json(str(path)))
    text = json.dumps(out, allow_nan=False)
    assert json.loads(text) == out
    for entry in out["nodes"].values():
        assert "error" not in entry["view"]


@pytest.mark.parametrize(
    "path", sorted(FIXTURES.glob("*.pumpflow")), ids=lambda p: p.name
)
def test_evaluate_matches_expected(path, expected):
    out = webapi.evaluate(read_json(str(path)))
    want = expected[path.name]
    assert set(out["nodes"]) == set(want)
    for node_id, entry in want.items():
        got = out["nodes"][node_id]
        assert [got["kind"], got["state"], got["status"]] == entry[:3], node_id
    assert out["errors"] == [
        i for i, n in out["nodes"].items() if n["state"] == "error"
    ]


def test_evaluate_shape_and_badges(result_a):
    node = result_a["nodes"]["check_a"]
    assert set(node) == {"kind", "state", "status", "badge", "notes", "view"}
    # no test point near zero flow: shut-off not tested (TR-01 4.1)
    assert node["badge"] == ["NOT FULLY ASSESSED", "warn"]
    assert result_a["nodes"]["mrt_a_check"]["state"] == "reject"
    assert result_a["nodes"]["mrt_a_check"]["notes"] == ["PROVISIONAL"]
    assert result_a["nodes"]["rated"]["badge"] is None


def test_compliance_view_matches_desktop_result(doc_a, result_a):
    graph = Graph.from_dict(doc_a)
    graph.evaluate()
    desktop = graph.node_by_id("check_a").outputs_cache["ComplianceResult"]
    view = result_a["nodes"]["check_a"]["view"]
    assert view["verdict_text"] == "NOT FULLY ASSESSED ⚠" == desktop.verdict_text
    shut = next(r for r in view["rows"] if r["name"] == "Shutoff Head")
    assert shut["verdict"] == "n/e" and shut["extrapolated"] is True
    assert "shut-off not tested" in shut["note"]
    assert view["shutoff_waiver"] == ""
    head = next(r for r in view["rows"] if r["name"] == "Head")
    want = next(p for p in desktop.parameters if p.name == "Head")
    assert abs(head["predicted"] - want.predicted) < 0.01
    assert head["verdict"] == "pass"
    assert set(head) == {
        "name",
        "actual",
        "predicted",
        "min",
        "max",
        "deviation",
        "tol",
        "verdict",
        "note",
        "extrapolated",
        "verified",
        "cells",
    }


def test_other_views(result_a):
    nodes = result_a["nodes"]
    npsh = nodes["npsh_a"]["view"]
    assert npsh["status"] == "pass" and npsh["verdict"] == "PASSED"
    assert npsh["ratio"] == pytest.approx(2.22, abs=0.01)
    assert len(npsh["curve"]["q"]) == len(npsh["curve"]["npshr"]) > 10

    mrt = nodes["mrt_a_check"]["view"]
    assert mrt["verdict"] == "FAILED" and mrt["rows"]
    assert mrt["duration"]["unit"]

    fit = nodes["fit_a"]["view"]
    assert fit["degree"] == 3 and fit["r2"]["head"] > 0.9
    assert len(fit["poly"]["q"]) == len(fit["poly"]["head"])
    assert len(fit["points"]["q"]) == 6

    plot = nodes["plot_a"]["view"]
    assert plot["fit"]["points"]["q"] == fit["points"]["q"]
    assert plot["rated"]["q"] == pytest.approx(9.8)
    assert plot["npsh"]["npsha"] == pytest.approx(2.4)  # NPSH wired into plot_a

    tp = nodes["test_a"]["view"]
    assert tp["n_rows"] == len(tp["rows"]) == 6
    assert tp["head_unit"] == "m" and tp["rows"][0]["head"] > 0

    corr = nodes["corr_a"]["view"]
    assert corr["before_after"] and corr["target_speed"]["unit"]

    rated = nodes["rated"]["view"]  # a Fluid node is wired in the reference file
    assert rated["fluids"] == [rated["choice"]] == [rated["override"]["name"]]
    assert nodes["note"]["view"] == {}
    assert nodes["mrt_b_check"]["view"] == {}  # idle node: no result, no view


def test_catalog_covers_every_kind():
    cat = webapi.catalog()
    assert len(cat) == 18 and len({c["kind"] for c in cat}) == 18
    assert {c["kind"] for c in cat if c["has_web_form"]} == WITNESS
    assert json.loads(json.dumps(cat, allow_nan=False)) == cat
    comp = next(c for c in cat if c["kind"] == "compliance")
    assert comp["group"] == "Checks"
    assert comp["inputs"] == [
        {"name": "FittedModel", "type": "FittedModel", "multi": False},
        {"name": "RatedPoint", "type": "RatedPoint", "multi": False},
    ]
    assert comp["outputs"] == [{"name": "ComplianceResult", "type": "ComplianceResult"}]


@pytest.mark.parametrize("kind", [c["kind"] for c in webapi.catalog()])
def test_default_settings_round_trip(kind):
    ds = webapi.default_settings(kind)
    assert json.loads(json.dumps(ds, allow_nan=False)) == ds
    assert settings_codec.encode(kind, settings_codec.decode(kind, ds)) == ds
    with pytest.raises(KeyError):
        webapi.default_settings("no_such_kind")


def test_jsonable_handles_quantities_numpy_and_nan():
    import numpy as np
    from pump import Q_

    out = webapi._jsonable(
        {
            "q": Q_(5, "m"),
            "nan": float("nan"),
            "inf": float("inf"),
            "arr": np.array([1.0, np.nan]),
            "np": np.float64(2.5),
            "t": (1, 2),
        }
    )
    assert out == {
        "q": {"value": 5.0, "unit": "m"},
        "nan": None,
        "inf": None,
        "arr": [1.0, None],
        "np": 2.5,
        "t": [1, 2],
    }
    json.dumps(out, allow_nan=False)


def test_export_docx_html_and_summary(doc_a):
    docx = webapi.export_report(doc_a, "docx")
    assert docx["filename"].endswith(".docx") and docx["mime"].endswith("document")
    assert base64.b64decode(docx["base64"])[:2] == b"PK"

    html = webapi.export_report(doc_a, "html", lang="pt")
    assert html["mime"] == "text/html"
    assert b"<html" in base64.b64decode(html["base64"]).lower()

    pytest.importorskip("openpyxl")
    xlsx = webapi.export_report(doc_a, "summary_xlsx")
    assert xlsx["filename"].endswith("_test_summary.xlsx")
    assert base64.b64decode(xlsx["base64"])[:2] == b"PK"


def test_export_errors(doc_a):
    for fmt in ("pdf", "tex"):
        with pytest.raises(ValueError, match="desktop only"):
            webapi.export_report(doc_a, fmt)
    with pytest.raises(ValueError):
        webapi.export_report(doc_a, "rtf")
    no_report = {
        **doc_a,
        "nodes": [n for n in doc_a["nodes"] if n["kind"] != "report_export"],
    }
    with pytest.raises(ValueError):
        webapi.export_report(no_report, "docx")


_NO_QT = """
import sys

class _Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("PySide6", "shiboken6", "pyqtgraph"):
            raise ImportError("blocked: " + name)
        return None

sys.meta_path.insert(0, _Block())
import json
from pumpflow import webapi
from pumpflow.persistence import read_json

out = webapi.evaluate(read_json(sys.argv[1]))
assert not [m for m in sys.modules if m.split(".")[0] in ("PySide6", "pyqtgraph")]
print(out["nodes"]["check_a"]["view"]["verdict_text"])
"""


def test_imports_and_evaluates_without_qt():
    proc = subprocess.run(
        [sys.executable, "-c", _NO_QT, str(P9001A)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().endswith("NOT FULLY ASSESSED ⚠")


# ------------------------------------------------------------ form helpers
def test_settings_round_trip_every_node(doc_a):
    for node in doc_a["nodes"]:
        stored = node["settings"]
        runtime = webapi.decode_settings(node["kind"], stored)
        json.dumps(runtime, allow_nan=False)
        assert webapi.encode_settings(node["kind"], runtime) == stored, node["id"]


def test_decode_settings_is_the_runtime_shape(doc_a):
    rated = next(n for n in doc_a["nodes"] if n["kind"] == "rated_point")
    rt = webapi.decode_settings("rated_point", rated["settings"])
    assert isinstance(rt["q"], float) and rt["q_unit"]
    assert not isinstance(rated["settings"]["q"], float)  # the input is untouched


def test_unit_options_and_convert_agree_with_units():
    from pumpflow import units

    opts = webapi.unit_options("capacity")
    assert ["m\u00b3/h", "m**3/h"] in opts
    assert [o[0] for o in opts] == [lbl for lbl, _ in units.UNIT_OPTIONS["capacity"]]
    assert webapi.convert(100, "m\u00b3/h", "US GPM", "capacity") == pytest.approx(
        440.287, rel=1e-4
    )
    assert webapi.convert(100, "m\u00b3/h", "m\u00b3/h", "capacity") == 100
    assert webapi.convert(5.0, "cSt", "cP", "viscosity", 0.8) == pytest.approx(
        units.convert_display(5.0, "viscosity", "cSt", "cP", 0.8)
    )
    assert webapi.convert(1, "nope", "bar", "pressure") is None
    with pytest.raises(KeyError):
        webapi.unit_options("no_such_dimension")


def test_explain_standards_clients_labels():
    assert "Total head" in webapi.explain("head")
    assert webapi.explain("no_such_key") == ""
    pt = webapi.explain("pump_type")
    assert pt.startswith("API 610 pump type\n") and "<" not in pt and "OH1" in pt
    assert webapi.explain("impeller_diameter").startswith("Impeller diameter\n")
    stds, cls = webapi.standards(), webapi.clients()
    assert stds and all(len(x) == 2 for x in stds)
    assert ["api610:12", webapi.standard_label("api610:12")] in stds
    assert cls and webapi.standard_label(
        stds[0][0], cls[0][0]
    ) != webapi.standard_label(stds[0][0])
    assert webapi.standard_label("api610:12", "") == webapi.standard_label("api610:12")
    json.dumps([stds, cls], allow_nan=False)


def test_water_and_pump_type_helpers():
    assert webapi.water_density(20) == pytest.approx(998.2, abs=0.1)
    w = webapi.water_properties(20)
    assert w["density"] == webapi.water_density(20)
    assert w["kinematic_cst"] == pytest.approx(1.0, abs=0.05)
    assert w["dynamic_cp"] == pytest.approx(1.0, abs=0.05)
    codes = [c for c, _ in webapi.pump_types()]
    assert "OH1" in codes and "VS7" in codes
    assert "Table 9" in webapi.pump_type_hint("VS1")
    assert "Table 8" in webapi.pump_type_hint("BB2")
    assert webapi.pump_type_hint("").startswith("Not set")


def test_rated_point_and_fluid_views(doc_a):
    # a wired water fluid overrides the rated fluid and is listed by name
    doc = json.loads(json.dumps(doc_a))
    fl = webapi.default_settings("fluid")
    fl.update({"source": "water", "name": "Test water"})
    doc["nodes"].append(
        {"id": "fluid-9", "kind": "fluid", "x": 0, "y": 0, "settings": fl}
    )
    rated = next(n for n in doc["nodes"] if n["kind"] == "rated_point")
    rated["settings"]["fluid_choice"] = "Test water"
    doc["edges"].append(
        {
            "src_node": "fluid-9",
            "src_port": "FluidSpec",
            "dst_node": rated["id"],
            "dst_port": "FluidSpec",
        }
    )
    nodes = webapi.evaluate(doc)["nodes"]
    fv = nodes["fluid-9"]["view"]
    assert fv["source"] == "water" and fv["viscosity_cp"] == pytest.approx(
        0.89, abs=0.01
    )
    rv = nodes[rated["id"]]["view"]
    assert rv["fluids"][-1] == "Test water" and rv["choice"] == "Test water"
    assert rv["override"]["name"] == "Test water"
    assert rv["standard_key"].startswith("api610:") and isinstance(rv["client"], str)
    assert rv["override"]["density_kgm3"] == pytest.approx(fv["density_kgm3"])


@pytest.mark.parametrize("kind", ["rated_point", "fluid"])
def test_web_edited_settings_decode_and_evaluate(kind):
    # edit "the web way": decode defaults, patch runtime keys, encode, evaluate
    rt = webapi.decode_settings(kind, webapi.default_settings(kind))
    if kind == "rated_point":
        rt.update({"q": 440.287, "q_unit": "US GPM", "pump_type": "BB2"})
        rt["standard_key"], rt["client"] = "api610:12", ""
        rt["standard"] = webapi.standard_label("api610:12")
    else:
        rt.update({"source": "water", "temp": 77.0, "temp_unit": "\u00b0F"})
    enc = webapi.encode_settings(kind, rt)
    assert webapi.decode_settings(kind, enc) == rt
    doc = {"meta": {"schema_version": 2}, "nodes": [], "edges": []}
    doc["nodes"].append(
        {"id": kind + "-1", "kind": kind, "x": 0, "y": 0, "settings": enc}
    )
    out = webapi.evaluate(doc)["nodes"][kind + "-1"]
    assert out["state"] == "ok", out["status"]


# ------------------------------------------- witness forms II (sprint 6 part B)
def _web_edit(doc, node_id, patch):
    """Edit one node "the web way": decode, patch runtime keys, encode, evaluate."""
    doc = json.loads(json.dumps(doc))
    node = next(n for n in doc["nodes"] if n["id"] == node_id)
    rt = webapi.decode_settings(node["kind"], node["settings"])
    patch(rt)
    node["settings"] = webapi.encode_settings(node["kind"], rt)
    return doc, webapi.evaluate(doc)["nodes"]


def test_atmosphere_agrees_with_units():
    from pumpflow import units

    assert webapi.atmosphere("bar") == pytest.approx(1.01325)
    assert webapi.atmosphere("psi") == pytest.approx(units.atm_in("psi"))


def test_parse_paste_header_and_rows():
    cols = {"p_suc": "bar", "p_dis": "bar", "q": "m³/h"}
    text = (
        "Q [US GPM]\tP_suc [psi g]\tP_dis [psi g]\tN\n"
        "440,287\t14,5\t145\t1750\n"
        "0\t14.5\t160\t1750\n"
    )
    out = webapi.parse_paste(text, cols, "a")
    assert out["columns"]["q"] == "US GPM"
    assert out["columns"]["p_suc"] == out["columns"]["p_dis"] == "psi"
    assert out["pressure_ref"] == "g" and out["vibration"] is False
    assert len(out["rows"]) == 2
    assert out["rows"][0]["q"] == pytest.approx(440.287)  # decimal comma
    assert out["rows"][0]["p_dis"] == 145 and out["rows"][0]["head"] is None
    assert out["rows"][0]["n"] == 1750
    json.dumps(out, allow_nan=False)

    # header-less lines are data in the hydraulic column order; units unchanged
    plain = webapi.parse_paste("100;1,0;5,0;25;1750;30\n", cols, "g")
    assert plain["columns"]["q"] == "m³/h" and plain["pressure_ref"] == "g"
    assert plain["rows"][0] == {
        "q": 100,
        "p_suc": 1.0,
        "p_dis": 5.0,
        "temp_c": 25,
        "n": 1750,
        "power": 30,
        "head": None,
        "eff": None,
    }
    assert webapi.parse_paste("  \n", cols, "g")["rows"] == []

    # pressure cells under a header with a different unit follow the first one
    mixed = webapi.parse_paste("P_suc [bar]\tP_dis [kPa]\n1\t500\n", {}, "g")
    assert mixed["columns"]["p_suc"] == mixed["columns"]["p_dis"] == "bar"
    assert mixed["rows"][0]["p_dis"] == pytest.approx(5.0)


def test_test_points_view_form_fields(result_a):
    v = result_a["nodes"]["test_a"]["view"]
    assert v["fluids"] == [v["choice"]] or v["choice"] == "__default__"
    assert isinstance(v["has_shutoff"], bool)
    assert v["vib_label"].startswith("Vibration columns (RMS")
    assert all({"key", "title", "tooltip"} <= set(c) for c in v["vib_columns"])
    c = result_a["nodes"]["corr_a"]["view"]
    assert c["has_rated"] is True and c["viscous_text"] == "—"
    assert c["banner"]["level"] in ("info", "warn", "error")


def test_compliance_view_cells_and_default_tolerances(doc_a, result_a):
    from pumpflow.nodes.compliance import param_cells

    view = result_a["nodes"]["check_a"]["view"]
    graph = Graph.from_dict(doc_a)
    graph.evaluate()
    desktop = graph.node_by_id("check_a").outputs_cache["ComplianceResult"]
    assert [r["cells"] for r in view["rows"]] == [
        param_cells(p) for p in desktop.parameters
    ]
    head = next(r for r in view["rows"] if r["name"] == "Head")
    assert head["cells"][0] == "Head" and head["cells"][7] == "✅"
    assert set(view["default_tolerances"]) == {
        "head",
        "shutoff",
        "power",
        "efficiency",
    }
    assert view["default_tolerances"]["head"] == desktop.default_tolerances["head"]


def test_web_edited_compliance_override_and_reset(doc_a):
    # a head tolerance and a reason, exactly as the form writes them
    def override(rt):
        base = webapi.evaluate(doc_a)["nodes"]["check_a"]["view"]["default_tolerances"]
        rt["tolerances"] = {
            "head": 0.10,
            "shutoff": base["shutoff"],
            "power": base["power"],
            "efficiency": base["efficiency"],
        }
        rt["override_reason"] = "purchaser agreement"

    doc, nodes = _web_edit(doc_a, "check_a", override)
    view = nodes["check_a"]["view"]
    assert view["overridden"] is True
    assert view["override_reason"] == "purchaser agreement"
    assert view["tolerances"]["head"] == 0.10
    assert nodes["check_a"]["badge"][0] in (
        "APPROVED",
        "REJECTED",
        "NOT FULLY ASSESSED",
    )

    # "Reset to the acceptance criteria": tolerances {} and no reason
    def reset(rt):
        rt["tolerances"] = {}
        rt.pop("override_reason", None)

    doc2, nodes2 = _web_edit(doc, "check_a", reset)
    v2 = nodes2["check_a"]["view"]
    assert v2["overridden"] is False and v2["override_reason"] == ""
    assert (
        nodes2["check_a"]["state"]
        == webapi.evaluate(doc_a)["nodes"]["check_a"]["state"]
    )
    node = next(n for n in doc2["nodes"] if n["id"] == "check_a")
    assert "override_reason" not in node["settings"]


def test_web_edited_correction_and_curve_fit(doc_a, result_a):
    base = result_a["nodes"]
    doc, nodes = _web_edit(
        doc_a,
        "corr_a",
        lambda rt: rt.update(
            {"lock_to_rated": False, "target_speed": 1800.0, "target_speed_unit": "rpm"}
        ),
    )
    assert nodes["corr_a"]["state"] == "ok", nodes["corr_a"]["status"]
    assert nodes["corr_a"]["view"]["target_speed"]["value"] == pytest.approx(1800.0)
    assert nodes["fit_a"]["state"] in ("ok", "reject", "idle")

    doc, nodes = _web_edit(
        doc_a, "fit_a", lambda rt: rt.update({"degree": 2, "spline": False})
    )
    assert nodes["fit_a"]["state"] == base["fit_a"]["state"]
    fv = nodes["fit_a"]["view"]
    assert fv["degree"] == 2 and fv["spline"] is None
    assert fv["r2_text"].startswith("R²(") and "Head" in fv["coeff_text"]


def test_web_edited_test_points_unit_change_keeps_the_physics(doc_a, result_a):
    # change the Q column to US GPM (values converted in Python, as the form does)
    def to_gpm(rt):
        for r in rt["rows"]:
            if r.get("q") is not None:
                r["q"] = webapi.convert(
                    r["q"], rt["columns"]["q"], "US GPM", "capacity"
                )
        rt["columns"]["q"] = "US GPM"

    doc, nodes = _web_edit(doc_a, "test_a", to_gpm)
    before = result_a["nodes"]["test_a"]["view"]
    after = nodes["test_a"]["view"]
    assert [r["head"] for r in after["rows"]] == pytest.approx(
        [r["head"] for r in before["rows"]]
    )
    assert nodes["check_a"]["status"] == result_a["nodes"]["check_a"]["status"]

    # pressure reference g -> a: values shifted by the atmosphere, heads unchanged
    def to_abs(rt):
        atm = webapi.atmosphere(rt["columns"]["p_suc"])
        for r in rt["rows"]:
            for k in ("p_suc", "p_dis"):
                if r.get(k) is not None:
                    r[k] = r[k] + atm
        rt["pressure_ref"] = "a"

    _, nodes_a = _web_edit(doc_a, "test_a", to_abs)
    assert [r["head"] for r in nodes_a["test_a"]["view"]["rows"]] == pytest.approx(
        [r["head"] for r in before["rows"]], rel=1e-6
    )


def test_web_edited_bench_geometry_stored_as_unset_when_off(doc_a):
    def geo_on(rt):
        rt.update({"suction_id": 200.0, "suction_id_unit": "mm", "suction_z": 0.0})
        rt.update(
            {"discharge_id": 150.0, "discharge_id_unit": "mm", "discharge_z": 1.5}
        )

    doc, nodes = _web_edit(doc_a, "test_a", geo_on)
    assert nodes["test_a"]["state"] == "ok"
    assert nodes["test_a"]["view"]["rows"][0]["components"] is not None

    def geo_off(rt):
        for k in ("suction_id", "discharge_id", "suction_z", "discharge_z"):
            rt[k] = None

    doc2, nodes2 = _web_edit(doc, "test_a", geo_off)
    node = next(n for n in doc2["nodes"] if n["id"] == "test_a")
    assert not any(k in node["settings"] for k in ("suction_id", "suction_z"))
    assert nodes2["test_a"]["view"]["rows"][0]["components"] is None


def test_p9001b_rows_typed_through_the_form_equal_the_committed_file():
    # Witness scenario: B's performance rows typed cell by cell (decimal comma, as
    # the browser grid accepts them) into a blank table give the committed verdicts.
    from pumpflow.numfmt import parse_decimal

    committed = read_json(str(P9001B))
    want = webapi.evaluate(committed)["nodes"]
    doc = json.loads(json.dumps(committed))
    node = next(n for n in doc["nodes"] if n["id"] == "test_b")
    rt = webapi.decode_settings("test_points", node["settings"])
    typed = []
    for row in rt["rows"]:
        blank = {k: None for k in ("q", "p_suc", "p_dis", "temp_c", "n", "power")}
        for key in blank:
            text = f"{row[key]!r}".replace(".", ",")  # what a user types
            blank[key] = parse_decimal(text, None)
        blank.update({"head": None, "eff": None})
        typed.append(blank)
    for t_row, r_row in zip(typed, rt["rows"]):
        for key, val in t_row.items():
            if r_row.get(key) is not None:
                assert val == pytest.approx(r_row[key])
    rt["rows"] = typed
    node["settings"] = webapi.encode_settings("test_points", rt)
    got = webapi.evaluate(doc)["nodes"]
    for node_id in ("test_b", "corr_b", "fit_b", "check_b", "report"):
        assert got[node_id]["state"] == want[node_id]["state"], node_id
        assert got[node_id]["status"] == want[node_id]["status"], node_id
        assert got[node_id]["badge"] == want[node_id]["badge"], node_id
    assert got["check_b"]["view"] == want["check_b"]["view"]
    for g, w in zip(got["test_b"]["view"]["rows"], want["test_b"]["view"]["rows"]):
        for key in ("head", "eff"):
            assert g[key] == pytest.approx(w[key]), key


# ------------------------------------------- witness forms II (sprint 7)
def test_npsh_view_matches_desktop_numbers(result_a):
    v = result_a["nodes"]["npsh_a"]["view"]
    assert json.loads(json.dumps(v, allow_nan=False)) == v
    assert v["npshr"] == pytest.approx(1.08, abs=0.005)  # NPSHr @ rated, m
    assert v["ratio"] == pytest.approx(2.22, abs=0.005)
    assert v["rated_q"] == pytest.approx(9.8)
    assert v["mode"] == "points" and v["status"] == "pass"
    assert len(v["points"]["q"]) == len(v["points"]["npshr"]) == 5
    assert len(v["curve"]["q"]) == len(v["curve"]["npshr"]) > 10


def test_mrt_check_view_verdict_and_labels(result_a):
    node = result_a["nodes"]["mrt_a_check"]
    v = node["view"]
    assert json.loads(json.dumps(v, allow_nan=False)) == v
    assert v["verdict"] == "FAILED" and v["verified"] is False
    assert v["verdict_label"] == "FAILED (unverified limits)"
    assert v["verdict_label"] in node["status"]  # the node status uses the same label
    assert v["inputs_text"].startswith("Log: P-9001A, 17 readings.")
    assert "Criteria: api610:8" in v["inputs_text"]
    assert {r["status"] for r in v["rows"]} >= {"pass", "fail", "info"}
    assert v["min_duration"] == {"value": 4.0, "unit": "h"}


def test_performance_plot_view_is_json_safe_with_series(result_a):
    v = result_a["nodes"]["plot_a"]["view"]
    assert json.loads(json.dumps(v, allow_nan=False)) == v
    fit = v["fit"]
    n = len(fit["poly"]["q"])
    assert n == 160 and len(fit["poly"]["head"]) == n
    assert len(fit["spline"]["q"]) == len(fit["spline"]["head"])
    assert len(fit["points"]["q"]) == len(fit["points"]["head"]) == 6
    assert v["show"] == {"poly": True, "spline": True, "points": True}
    assert v["rated"]["in_range"] is True
    assert len(v["npsh"]["points"]["q"]) == len(v["npsh"]["points"]["npshr"])


def test_next_time_is_the_desktop_rule():
    assert webapi.next_time([]) == "00:00"
    assert webapi.next_time([{"time": "06:00"}, {"time": "06:15"}]) == "06:30"
    assert webapi.next_time([{"time": "23:50"}]) == "00:05"  # wraps at midnight
    assert webapi.next_time([{"time": "6:45"}, {"time": ""}]) == "07:00"  # last valid
    assert webapi.next_time([{"time": "x"}]) == "00:00"


def test_mrt_options_roles_and_dimensions():
    from pump.mechanical_run import ROLES

    o = webapi.mrt_options()
    assert o["roles"] == list(ROLES) and o["roles"][-1] == "other"
    assert "vibration_velocity" in o["dimensions"]
    assert o["role_dimensions"]["oil_temperature"] == "temperature"
    assert "other" not in o["role_dimensions"]
    assert json.loads(json.dumps(o)) == o
    for dim in o["dimensions"]:
        assert webapi.unit_options(dim)


def test_web_edited_mrt_check_override_and_npsh_quoted_off(doc_a):
    def override(rt):
        rt["overrides"]["min_duration"] = {"value": 5.0, "unit": "h"}

    _, nodes = _web_edit(doc_a, "mrt_a_check", override)
    v = nodes["mrt_a_check"]["view"]
    assert v["duration_status"] == "fail"  # a 4 h run against a 5 h minimum
    assert v["min_duration"] == {"value": 5.0, "unit": "h"}

    def quoted_off(rt):
        rt.pop("npshr_quoted")
        rt.pop("npshr_quoted_unit")

    doc2, nodes2 = _web_edit(doc_a, "npsh_a", quoted_off)
    node = next(n for n in doc2["nodes"] if n["id"] == "npsh_a")
    assert "npshr_quoted" not in node["settings"]
    assert nodes2["npsh_a"]["view"]["npshr_quoted"] is None


def test_parse_mrt_paste_headers_units_and_blank():
    cols = [
        {"name": "Flow", "dimension": "capacity", "unit": "US GPM", "role": "flow"},
        {
            "name": "Sump",
            "dimension": "temperature",
            "unit": "\u00b0F",
            "role": "other",
        },
    ]
    text = "Time\tFlow [m\u00b3/h]\tSump [\u00b0C]\n06:00\t10,0\t50\n6:15\t10\t\nbad\t1\t2\n"
    rows = webapi.parse_mrt_paste(text, cols)
    assert [r["time"] for r in rows] == ["06:00", "06:15"]
    assert rows[0]["values"]["Flow"] == pytest.approx(44.0287, abs=1e-3)
    assert rows[0]["values"]["Sump"] == pytest.approx(122.0)
    assert rows[1]["values"]["Sump"] is None
    assert json.loads(json.dumps(rows, allow_nan=False)) == rows
    plain = webapi.parse_mrt_paste("06:00;1,5;70\n", cols)  # no header: channel order
    assert plain == [{"time": "06:00", "values": {"Flow": 1.5, "Sump": 70.0}}]
    assert webapi.parse_mrt_paste("   \n", cols) == []


# --------------------------------------------------------------- sprint 8: reports


def _docx_text(path_or_bytes):
    """Paragraph and table-cell texts of a .docx (what a reader sees)."""
    import io

    docx = pytest.importorskip("docx")
    from docx.oxml.ns import qn

    src = (
        io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes
    )
    d = docx.Document(src)
    paragraphs = [p.text for p in d.paragraphs]
    # raw <w:tc> text: python-docx's Table.rows fails on merged cells
    cells = ["".join(tc.itertext()) for tc in d.element.body.iter(qn("w:tc"))]
    return paragraphs, cells


def test_export_docx_has_the_texts_of_the_cli_docx(doc_a, tmp_path):
    from pumpflow import export_cli

    code = export_cli.main(
        [str(P9001A), "--formats", "docx", "--out", str(tmp_path), "--stem", "cli"]
    )
    assert code == 0
    cli_paragraphs, cli_cells = _docx_text(str(tmp_path / "cli.docx"))
    out = webapi.export_report(doc_a, "docx")
    web_paragraphs, web_cells = _docx_text(base64.b64decode(out["base64"]))
    assert cli_paragraphs and any("NOT FULLY ASSESSED" in p for p in cli_paragraphs)
    assert web_paragraphs == cli_paragraphs
    assert web_cells == cli_cells


def _with_override(doc):
    """A copy of ``doc`` whose Compliance node overrides the head tolerance."""
    import copy

    doc = copy.deepcopy(doc)
    comp = next(n for n in doc["nodes"] if n["kind"] == "compliance")
    runtime = webapi.decode_settings("compliance", comp["settings"])
    runtime["tolerances"] = {**(runtime.get("tolerances") or {}), "head": 7.0}
    comp["settings"] = webapi.encode_settings("compliance", runtime)
    return doc


def test_export_html_states_the_tolerance_override(doc_a):
    changed = _with_override(doc_a)
    res = webapi.evaluate(changed)
    comp_id = next(n["id"] for n in changed["nodes"] if n["kind"] == "compliance")
    assert res["nodes"][comp_id]["view"]["overridden"] is True

    html = base64.b64decode(webapi.export_report(changed, "html")["base64"]).decode(
        "utf-8"
    )
    plain = base64.b64decode(webapi.export_report(doc_a, "html")["base64"]).decode(
        "utf-8"
    )
    from pump.utilities.report import TOLERANCE_OVERRIDE_INTRO

    assert TOLERANCE_OVERRIDE_INTRO in html
    assert TOLERANCE_OVERRIDE_INTRO not in plain


def _with_waiver(doc, reason="integral-gear pump, API 610 12th 8.3.3.4; letter 12"):
    """A copy of ``doc`` whose Compliance node waives the shut-off test."""
    import copy

    doc = copy.deepcopy(doc)
    comp = next(n for n in doc["nodes"] if n["kind"] == "compliance")
    runtime = webapi.decode_settings("compliance", comp["settings"])
    runtime["shutoff_waiver"] = reason
    comp["settings"] = webapi.encode_settings("compliance", runtime)
    return doc


def test_shutoff_waiver_approves_and_is_printed(doc_a):
    from pump.utilities.report import shutoff_waiver_sentence

    waived = _with_waiver(doc_a)
    res = webapi.evaluate(waived)
    comp_id = next(n["id"] for n in waived["nodes"] if n["kind"] == "compliance")
    view = res["nodes"][comp_id]["view"]
    assert view["verdict_text"] == "APPROVED ✓ (shut-off not tested)"
    assert view["shutoff_waiver"].startswith("integral-gear pump")
    shut = next(r for r in view["rows"] if r["name"] == "Shutoff Head")
    assert shut["verdict"] == "info" and "waived: integral-gear" in shut["note"]

    sentence = shutoff_waiver_sentence(str, view["shutoff_waiver"])
    html = base64.b64decode(webapi.export_report(waived, "html")["base64"]).decode(
        "utf-8"
    )
    plain = base64.b64decode(webapi.export_report(doc_a, "html")["base64"]).decode(
        "utf-8"
    )
    from html import escape

    assert escape(sentence) in html
    assert "Shut-off head not tested" not in plain
    paragraphs, _ = _docx_text(
        base64.b64decode(webapi.export_report(waived, "docx")["base64"])
    )
    assert sentence in paragraphs


def test_report_export_view_lists_the_branches_and_the_overall_verdict(doc_a, result_a):
    node_id = next(n["id"] for n in doc_a["nodes"] if n["kind"] == "report_export")
    node = result_a["nodes"][node_id]
    view = node["view"]
    assert view["has_rated"] is True
    assert [p["tag"] for p in view["pumps"]] == ["P-9001A"]
    pump = view["pumps"][0]
    assert pump["reportable"] is True
    assert pump["verdict_text"].startswith("NOT FULLY ASSESSED")
    assert {"Fitted", "Verdict"} <= set(pump["sections"])
    # the overall verdict is the text after the pump count in the node status
    assert node["status"].endswith(view["overall_verdict_text"])
    json.dumps(view, allow_nan=False)


def test_report_export_view_without_branches():
    doc = {
        "meta": {"unit_preset": "SI", "schema_version": 2},
        "nodes": [
            {
                "id": "report_export-1",
                "kind": "report_export",
                "x": 0,
                "y": 0,
                "settings": webapi.default_settings("report_export"),
            }
        ],
        "edges": [],
    }
    view = webapi.evaluate(doc)["nodes"]["report_export-1"]["view"]
    assert view == {"has_rated": False, "overall_verdict_text": "pending", "pumps": []}
