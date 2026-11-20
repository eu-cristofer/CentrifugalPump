"""
Browser JSON API (``pumpflow.webapi``): plain JSON in, plain JSON out.

``evaluate`` must agree with the engine and ``expected.json``, the views must
carry the desktop numbers, the exports must be real files, and the module must
import (and evaluate B-34004A) with every Qt binding blocked.
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
B34004A = ROOT / "examples" / "user" / "B-34004A_MRT_reference.pumpflow"
B34004B = ROOT / "examples" / "user" / "B-34004B_witness_2026-11-19.pumpflow"
FILES = sorted(FIXTURES.glob("*.pumpflow")) + [B34004A, B34004B]

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
    return read_json(str(B34004A))


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
    assert node["badge"] == ["APPROVED", "ok"]
    assert result_a["nodes"]["mrt_a_check"]["state"] == "reject"
    assert result_a["nodes"]["mrt_a_check"]["notes"] == ["PROVISIONAL"]
    assert result_a["nodes"]["rated"]["badge"] is None


def test_compliance_view_matches_desktop_result(doc_a, result_a):
    graph = Graph.from_dict(doc_a)
    graph.evaluate()
    desktop = graph.node_by_id("check_a").outputs_cache["ComplianceResult"]
    view = result_a["nodes"]["check_a"]["view"]
    assert view["verdict_text"] == "APPROVED ✓" == desktop.verdict_text
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

    assert nodes["rated"]["view"] == {}
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
        [sys.executable, "-c", _NO_QT, str(B34004A)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().endswith("APPROVED ✓")
