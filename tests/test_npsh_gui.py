"""Qt (offscreen) tests: NPSH node, codec round-trip, report section (sprint 8 / UC-05)."""

import copy
import os
from dataclasses import replace

import pytest

# Sundyne B-34004A page 2: NPSHr [ft] at Q [gpm].
_POINTS = [(15.2, 2.7), (29.4, 2.9), (34.8, 3.3), (43.5, 4.1), (47.9, 3.3)]


def _b34004a_settings():
    return {
        "pump_tag": "B-34004A",
        "mode": "points",
        "degree": 2,
        "columns": {"q": "US GPM", "npshr": "ft"},
        "rows": [{"q": q, "npshr": n} for q, n in _POINTS],
        "npsha": None,
        "npsha_unit": "m",
        "calc_p": 1.2,
        "calc_p_unit": "bar",
        "calc_p_ref": "a",
        "calc_temp": 20.0,
        "calc_temp_unit": "°C",
        "calc_id": 100.0,
        "calc_id_unit": "mm",
        "calc_z": 0.0,
        "calc_z_unit": "m",
        "overrides": {"min_ratio": 1.1, "min_margin": {"value": 0.5, "unit": "m"}},
    }


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _rated(q=None, npsha=None):
    """Default rated point, re-pointed at the B-34004A duty (43.1 gpm, NPSHa 2.4 m)."""
    from pump import Q_
    from pumpflow.nodes.registry import make_node

    rated = make_node("rated_point").compute({})["RatedPoint"]
    return replace(
        rated,
        q=q if q is not None else Q_(43.1, "gallon/min"),
        npsha=npsha if npsha is not None else Q_(2.4, "m"),
    )


def _node(overrides=False):
    from pumpflow.nodes.registry import make_node

    node = make_node("npsh")
    s = _b34004a_settings()
    if not overrides:
        s["overrides"] = {"min_ratio": None, "min_margin": None}
    node.settings.update(s)
    return node


def test_registered_kind(qapp):
    from pumpflow.nodes.registry import NODE_KINDS

    assert any(k[0] == "npsh" and k[1] == "NPSH" for k in NODE_KINDS)


def test_b34004a_node_evaluates(qapp):
    node = _node()
    out = node.compute({"RatedPoint": [_rated()]})
    assert node.state != "invalid", node.status
    assert "B-34004A" in node.status
    assert "NPSHr" in node.status and "NPSHa 2.40 m" in node.status
    assert "ratio" in node.status
    assert "not configured" in node.status  # no margin rule is seeded
    sig = out["NPSHResult"]
    assert sig.pump_tag == "B-34004A"
    assert sig.result.status == "info"
    assert sig.result.ratio > 1.9
    # NPSHr at the rated 43.1 gpm is ~3.5-4.1 ft (1.07-1.25 m)
    npshr_ft = sig.result.npshr.to("ft").magnitude
    assert 3.4 <= npshr_ft <= 4.2


def test_override_rule_is_applied_and_unverified(qapp):
    node = _node(overrides=True)  # min ratio 1.1, min margin 0.5 m
    out = node.compute({"RatedPoint": [_rated()]})
    assert out["NPSHResult"].result.status == "pass"
    assert "(unverified criteria)" in node.status
    node.settings["overrides"]["min_ratio"] = 5.0
    out = node.compute({"RatedPoint": [_rated()]})
    assert out["NPSHResult"].result.status == "fail"
    assert node.state == "reject"


def test_calculator_mode_matches_hand_formula(qapp):
    from pump import Q_, Water
    from pump.constants import G

    node = _node()
    node.settings["mode"] = "calculator"
    rated = _rated(q=Q_(50.0, "m**3/h"))
    out = node.compute({"RatedPoint": [rated]})
    assert node.state != "invalid", node.status
    w = Water(Q_(20.0, "degC"))
    p_s = Q_(1.2, "bar").to("Pa")
    area = 3.141592653589793 * (0.1) ** 2 / 4.0
    v = Q_(50.0, "m**3/h").to("m**3/s").magnitude / area
    g = G.to("m/s**2").magnitude
    rho = w.density.to("kg/m**3").magnitude
    pv = w.vapour_pressure.to("Pa").magnitude
    hand = (p_s.magnitude - pv) / (rho * g) + v**2 / (2 * g)
    assert node._calc_npsha.to("m").magnitude == pytest.approx(hand, rel=1e-6)
    assert out["NPSHResult"].result.npsha.to("m").magnitude == pytest.approx(
        hand, rel=1e-6
    )


def test_calculator_needs_rated_point(qapp):
    node = _node()
    node.settings["mode"] = "calculator"
    assert node.compute({}) == {}
    assert node.state == "invalid"


def test_blank_sheet_is_invalid(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("npsh")
    assert node.compute({}) == {}
    assert node.state == "invalid"
    # fewer than 2 points with values
    node = _node()
    for r in node.settings["rows"][1:]:
        r["npshr"] = None
    assert node.compute({"RatedPoint": [_rated()]}) == {}
    assert node.state == "invalid"


def test_missing_npsha_is_invalid(qapp):
    from pump import Q_

    node = _node()
    rated = _rated()
    rated = replace(rated, npsha=Q_(0.0, "m"))
    assert node.compute({"RatedPoint": [rated]}) == {}
    assert node.state == "invalid"


def test_dialog_opens(qapp):
    from PySide6.QtWidgets import QTableWidget

    node = _node()
    dlg = node.create_dialog(None, lambda: node.compute({"RatedPoint": [_rated()]}))
    assert dlg is not None
    table = dlg.findChild(QTableWidget, "NPSHTable")
    assert table.rowCount() == len(_POINTS)
    assert table.columnCount() == 2
    dlg.close()


def test_default_dialog_opens(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("npsh")
    dlg = node.create_dialog(None, lambda: node.compute({}))
    assert dlg is not None
    dlg.close()


def test_codec_roundtrip():
    from pumpflow.settings_codec import decode, encode

    rt = _b34004a_settings()
    v2 = encode("npsh", rt)
    assert v2["columns"] == {"q": "gal/min", "npshr": "ft"}
    assert v2["calc_p"]["ref"] == "a"
    assert v2["calc_id"] == {"value": 100.0, "unit": "mm"}
    assert v2["overrides"]["min_margin"] == {"value": 0.5, "unit": "m"}
    assert "npsha" not in v2  # unset optional quantity is omitted
    back = decode("npsh", v2)
    expected = copy.deepcopy(rt)
    expected.pop("npsha")
    expected.pop("npsha_unit")
    assert back == expected
    assert encode("npsh", back) == v2


def test_codec_roundtrip_with_npsha():
    from pumpflow.settings_codec import decode, encode

    rt = _b34004a_settings()
    rt["npsha"] = 2.4
    v2 = encode("npsh", rt)
    assert v2["npsha"] == {"value": 2.4, "unit": "m"}
    assert decode("npsh", v2) == rt
    assert encode("npsh", decode("npsh", v2)) == v2


def test_scene_roundtrip(qapp):
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node
    from pumpflow.settings_codec import encode

    scene = GraphScene(make_node)
    doc = {
        "meta": {"unit_preset": "SI", "schema_version": 2},
        "nodes": [
            {
                "id": "n1",
                "kind": "npsh",
                "pos": [0, 0],
                "settings": encode("npsh", _b34004a_settings()),
            }
        ],
        "edges": [],
    }
    scene.load_dict(doc)
    logic = next(n.logic for n in scene.nodes if n.logic.kind == "npsh")
    assert logic.settings["pump_tag"] == "B-34004A"
    assert len(logic.settings["rows"]) == len(_POINTS)
    assert logic.settings["columns"] == {"q": "US GPM", "npshr": "ft"}


def _report_data():
    from pumpflow.binding import assemble_report_data
    from pumpflow.signals import BranchBundle

    rated = _rated()
    sig = _node().compute({"RatedPoint": [rated]})["NPSHResult"]
    bundle = BranchBundle(pump_tag="B-34004A", npsh=sig)
    return assemble_report_data(rated, [bundle], {})


def test_report_entry_for_npsh_only_tag(qapp):
    data = _report_data()
    entry = data["test_data"]["B-34004A"]
    assert "NPSH" in entry
    assert "test_summary" not in entry
    assert entry["NPSH"]["result"] is not None
    assert len(entry["NPSH"]["table"]) == len(_POINTS)


def test_report_bundle_groups_npsh_by_pump_tag(qapp):
    from pumpflow.nodes.registry import make_node

    rated = _rated()
    sig = _node().compute({"RatedPoint": [rated]})["NPSHResult"]
    exp = make_node("report_export")
    exp.compute({"RatedPoint": [rated], "branch": [sig]})
    assert len(exp._branches) == 1
    assert exp._branches[0].pump_tag == "B-34004A"
    assert exp._branches[0].npsh is sig


def test_report_tex_and_docx_contain_section(qapp, tmp_path):
    from pumpflow.binding import export_reports

    data = _report_data()
    paths, errors = export_reports(
        data, ["tex", "docx"], language="en", out_dir=str(tmp_path), stem="npsh"
    )
    assert "tex" in paths, errors
    assert "NPSH" in open(paths["tex"], encoding="utf-8").read()
    if "docx" in paths:
        import zipfile

        # Read the raw XML: the shipped template has merged-cell tables that
        # python-docx's row.cells cannot iterate.
        with zipfile.ZipFile(paths["docx"]) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        assert "NPSH" in xml
    else:  # a missing template is an environment issue, not a regression
        assert "Template" in errors["docx"]
