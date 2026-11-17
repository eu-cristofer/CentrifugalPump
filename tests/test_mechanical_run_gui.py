"""Qt (offscreen) tests: MRT Log + MRT Check nodes, codec round-trip, the
legacy one-node split, and the report section (sprint 6 / UC-11)."""

import copy
import os

import pytest

_RAW = """\
06:00 43.53 487.32 29.72 0.04 0.15 44 116 69.34
06:15 43.51 486.45 29.42 0.04 0.15 44 120 66.77
06:30 43.51 484.71 29.08 0.04 0.15 42 121 65.89
06:45 43.49 485.58 28.78 0.04 0.15 42 121 65.82
07:00 43.49 485.58 28.71 0.04 0.16 42 122 66.11
07:15 43.51 484.71 28.61 0.05 0.15 42 122 65.15
07:30 43.47 485.58 28.76 0.05 0.15 42 122 65.38
07:45 43.51 484.71 28.83 0.05 0.15 42 121 64.94
08:00 43.49 485.58 28.86 0.05 0.14 42 120 65.16
08:15 43.51 485.58 29.15 0.05 0.15 42 121 66.09
08:30 43.49 486.59 29.11 0.05 0.15 42 121 65.45
08:45 43.51 486.45 29.08 0.05 0.15 42 121 65.67
09:00 43.51 486.45 29.03 0.05 0.16 42 122 65.89
09:15 43.49 486.45 28.98 0.05 0.15 42 123 66.11
09:30 43.49 487.32 29.03 0.05 0.15 42 122 65.67
09:45 43.51 487.32 29.08 0.05 0.14 42 123 65.53
10:00 43.49 487.32 29.11 0.05 0.14 42 124 65.65
"""

_COLUMNS = [
    {"name": "Flow", "dimension": "capacity", "unit": "US GPM", "role": "flow"},
    {
        "name": "ΔP",
        "dimension": "pressure",
        "unit": "psi",
        "role": "differential_pressure",
    },
    {"name": "Power", "dimension": "power", "unit": "kW", "role": "power"},
    {
        "name": "Vib filtered",
        "dimension": "vibration_velocity",
        "unit": "in/s",
        "role": "vibration_filtered",
    },
    {
        "name": "Vib unfiltered",
        "dimension": "vibration_velocity",
        "unit": "in/s",
        "role": "vibration_unfiltered",
    },
    {
        "name": "Lube oil",
        "dimension": "pressure",
        "unit": "psi",
        "role": "oil_pressure",
    },
    {
        "name": "Sump",
        "dimension": "temperature",
        "unit": "°F",
        "role": "oil_temperature",
    },
    {
        "name": "Seal cavity",
        "dimension": "pressure",
        "unit": "psi",
        "role": "seal_pressure",
    },
]


_OVERRIDES = {
    "min_duration": None,
    "role_max": {},
    "stabilisation": {
        "oil_temperature": {
            "delta": {"value": 2.0, "unit": "°F"},
            "window": {"value": 60.0, "unit": "min"},
        }
    },
}


def _b34004a_log_settings():
    s = _b34004a_settings()
    s.pop("overrides")
    return s


def _b34004a_settings():
    """The legacy one-node settings (log + overrides) of B-34004A."""
    names = [c["name"] for c in _COLUMNS]
    rows = []
    for line in _RAW.splitlines():
        cells = line.split()
        rows.append(
            {
                "time": cells[0],
                "values": {n: float(v) for n, v in zip(names, cells[1:])},
            }
        )
    return {
        "pump_tag": "B-34004A",
        "columns": copy.deepcopy(_COLUMNS),
        "rows": rows,
        "overrides": {
            "min_duration": None,
            "role_max": {},
            "stabilisation": {
                "oil_temperature": {
                    "delta": {"value": 2.0, "unit": "°F"},
                    "window": {"value": 60.0, "unit": "min"},
                }
            },
        },
    }


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _node():
    from pumpflow.nodes.registry import make_node

    node = make_node("mechanical_run")
    node.settings.update(_b34004a_log_settings())
    return node


def _check(log_node, rated=None, fitted=None):
    """An MRT Check fed by ``log_node``: ``(check node, outputs)``."""
    import copy as _copy

    from pumpflow.nodes.registry import make_node

    check = make_node("mechanical_run_check")
    check.settings["overrides"] = _copy.deepcopy(_OVERRIDES)
    inputs = {"MechanicalRunSet": [log_node.compute({})["MechanicalRunSet"]]}
    if rated is not None:
        inputs["RatedPoint"] = [rated]
    if fitted is not None:
        inputs["FittedModel"] = [fitted]
    return check, check.compute(inputs)


def test_default_log_emits_only_the_log(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("mechanical_run")
    out = node.compute({})
    assert set(out) == {"MechanicalRunSet"}
    assert "readings" in node.status
    assert "overrides" not in node.settings
    # the witness sheet: time (row key), flow, vibration overall / filtered,
    # oil temperature
    assert [(c["name"], c["role"]) for c in node.settings["columns"]] == [
        ("Flow", "flow"),
        ("Vib overall", "vibration_unfiltered"),
        ("Vib filtered", "vibration_filtered"),
        ("Oil temperature", "oil_temperature"),
    ]
    assert [p.name for p in node.outputs] == ["MechanicalRunSet"]
    assert node.inputs == []


def test_b34004a_log_and_check(qapp):
    node = _node()
    out = node.compute({})
    assert "17 readings" in node.status and "4.0 h" in node.status
    assert "FAILED" not in node.status  # the log gives no verdict
    assert out["MechanicalRunSet"].pump_tag == "B-34004A"
    check, res = _check(node)
    # unfiltered 0.16 in/s = 4.06 mm/s > 3.0 mm/s seed (unverified): FAILED
    assert "FAILED" in check.status and "17 readings" in check.status
    assert res["MechanicalRunResult"].pump_tag == "B-34004A"
    assert res["MechanicalRunResult"].plot_png is not None


def test_check_without_log_is_idle(qapp):
    from pumpflow.nodes.registry import make_node

    check = make_node("mechanical_run_check")
    assert check.compute({}) == {}
    assert check.state == "idle"


def test_check_dialog_shows_verdict_and_trend(qapp):
    from PySide6.QtWidgets import QLabel, QTableWidget

    check, _res = _check(_node())
    dlg = check.create_dialog(None, lambda: None)
    table = dlg.findChild(QTableWidget, "RunResult")
    assert table.rowCount() >= 1
    trend = dlg.findChild(QLabel, "RunTrend")
    assert trend.pixmap() is not None and not trend.pixmap().isNull()
    assert dlg.max_button is not None
    dlg.close()


def test_too_few_readings_is_invalid(qapp):
    node = _node()
    node.settings["rows"] = node.settings["rows"][:1]
    assert node.compute({}) == {}
    assert node.state == "invalid"


def test_dialog_opens(qapp):
    node = _node()
    dlg = node.create_dialog(None, lambda: node.compute({}))
    assert dlg is not None
    from PySide6.QtWidgets import QTableWidget

    grid = dlg.findChild(QTableWidget, "RunGrid")
    assert grid.rowCount() == 17
    assert grid.columnCount() == 1 + len(_COLUMNS)
    dlg.close()


def test_log_units_sit_above_the_readings_and_convert(qapp):
    """MRT Log follows the Test Points layout: one unit combo above each
    channel column; picking another unit converts that column only."""
    import pytest as _pytest
    from PySide6.QtWidgets import QTableWidget

    node = _node()
    dlg = node.create_dialog(None, lambda: node.compute({}))
    cols = dlg.findChild(QTableWidget, "RunColumns")
    assert [cols.horizontalHeaderItem(c).text() for c in range(cols.columnCount())] == [
        "Name",
        "Dimension",
        "Role",
    ]
    strip = next(
        w for w in dlg.findChildren(object) if type(w).__name__ == "UnitHeaderStrip"
    )
    assert len(strip.headers) == len(_COLUMNS)
    sump = next(
        h
        for h in strip.headers
        if h.col == 1 + [c["name"] for c in _COLUMNS].index("Sump")
    )
    assert sump.combo.currentData() == "°F"
    before = [r["values"]["Sump"] for r in node.settings["rows"]]
    sump.combo.setCurrentIndex(sump.combo.findData("°C"))
    after = [r["values"]["Sump"] for r in node.settings["rows"]]
    assert after[0] == _pytest.approx((before[0] - 32) / 1.8)
    assert (
        next(c for c in node.settings["columns"] if c["name"] == "Sump")["unit"] == "°C"
    )
    grid = dlg.findChild(QTableWidget, "RunGrid")
    titles = [grid.horizontalHeaderItem(c).text() for c in range(grid.columnCount())]
    assert "Sump [°C]" in titles
    # other columns untouched
    assert node.settings["rows"][0]["values"]["Flow"] == 43.53
    dlg.close()


def test_codec_roundtrip():
    from pumpflow.settings_codec import decode, encode

    rt = _b34004a_settings()  # the codec still reads legacy overrides
    v2 = encode("mechanical_run", rt)
    # columns carry Pint strings on disk, overrides {"value", "unit"}
    assert v2["columns"][0]["unit"] == "gal/min"
    st = v2["overrides"]["stabilisation"]["oil_temperature"]
    assert st["delta"] == {"value": 2.0, "unit": "delta_degF"}
    assert st["window"] == {"value": 60.0, "unit": "minute"}
    assert decode("mechanical_run", v2) == rt
    assert encode("mechanical_run", decode("mechanical_run", v2)) == v2
    # the MRT Check stores the overrides in the same on-disk form
    chk = {"overrides": copy.deepcopy(_OVERRIDES)}
    assert encode("mechanical_run_check", chk)["overrides"] == v2["overrides"]
    assert decode("mechanical_run_check", encode("mechanical_run_check", chk)) == chk


def test_codec_unknown_unit_converts_to_canonical():
    from pumpflow.settings_codec import decode

    stored = {
        "pump_tag": "X",
        "columns": [
            {
                "name": "Vib",
                "dimension": "vibration_velocity",
                "unit": "km/h",
                "role": "vibration_filtered",
            }
        ],
        "rows": [{"time": "06:00", "values": {"Vib": 3.6}}],
        "overrides": {"min_duration": None, "role_max": {}, "stabilisation": {}},
    }
    out = decode("mechanical_run", stored)
    assert out["columns"][0]["unit"] == "m/s"
    assert out["rows"][0]["values"]["Vib"] == pytest.approx(1.0)


def test_scene_roundtrip(qapp):
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    scene = GraphScene(make_node)
    doc = {
        "meta": {"unit_preset": "SI", "schema_version": 2},
        "nodes": [
            {
                "id": "n1",
                "kind": "mechanical_run",
                "pos": [0, 0],
                "settings": __import__(
                    "pumpflow.settings_codec", fromlist=["encode"]
                ).encode("mechanical_run", _b34004a_settings()),
            }
        ],
        "edges": [],
    }
    doc["nodes"].append(
        {"id": "rep", "kind": "report_export", "x": 400, "y": 0, "settings": {}}
    )
    doc["edges"] = [
        {
            "src_node": "n1",
            "src_port": "MechanicalRunResult",
            "dst_node": "rep",
            "dst_port": "branch",
        }
    ]
    scene.load_dict(doc)  # a legacy one-node run is split on load
    try:
        logic = next(n.logic for n in scene.nodes if n.logic.kind == "mechanical_run")
        assert logic.settings["pump_tag"] == "B-34004A"
        assert len(logic.settings["rows"]) == 17
        assert "overrides" not in logic.settings
        check = next(
            n.logic for n in scene.nodes if n.logic.kind == "mechanical_run_check"
        )
        assert check.node_id == "n1_check"
        st = check.settings["overrides"]["stabilisation"]["oil_temperature"]
        assert st["delta"]["value"] == 2.0
        assert "FAILED" in check.status  # same verdict as the one-node run
        out = scene.to_dict()
        wires = {(e["src_node"], e["src_port"], e["dst_node"]) for e in out["edges"]}
        assert ("n1", "MechanicalRunSet", "n1_check") in wires
        assert ("n1_check", "MechanicalRunResult", "rep") in wires
        # saved in the new form, reloading changes nothing
        scene.load_dict(out)
        assert scene.to_dict() == out
    finally:
        scene.dispose()


def test_b34004a_reference_uses_log_and_check(qapp):
    """The regression fixture: MRT Log -> MRT Check (rated + fitted wired) ->
    Report Export; the verdict is unchanged (FAILED on unverified limits)."""
    import json
    from pathlib import Path

    from pumpflow.export_cli import build_scene, report_inputs

    path = (
        Path(__file__).resolve().parents[1]
        / "examples/user/B-34004A_MRT_reference.pumpflow"
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    kinds = {n["id"]: n["kind"] for n in doc["nodes"]}
    assert kinds["mrt_a"] == "mechanical_run"
    assert kinds["mrt_a_check"] == "mechanical_run_check"
    wires = {
        (e["src_node"], e["src_port"], e["dst_node"], e["dst_port"])
        for e in doc["edges"]
    }
    assert ("mrt_a", "MechanicalRunSet", "mrt_a_check", "MechanicalRunSet") in wires
    assert ("rated", "RatedPoint", "mrt_a_check", "RatedPoint") in wires
    assert ("fit_a", "FittedModel", "mrt_a_check", "FittedModel") in wires
    assert ("mrt_a_check", "MechanicalRunResult", "report", "branch") in wires

    _app, scene = build_scene(str(path))
    try:
        by_id = {n.logic.node_id: n.logic for n in scene.nodes}
        assert by_id["mrt_a"].state == "ok"
        assert by_id["mrt_a_check"].status.endswith("FAILED (unverified limits)")
        _rated, branches, _s = report_inputs(scene)
        (b,) = branches
        assert b.mechanical is not None and not b.mechanical.result.passed
    finally:
        scene.dispose()


def _report_data(tmp_path):
    from pumpflow.binding import assemble_report_data
    from pumpflow.nodes.registry import make_node
    from pumpflow.signals import BranchBundle

    rated = make_node("rated_point").compute({})["RatedPoint"]
    _chk, res = _check(_node())
    sig = res["MechanicalRunResult"]
    bundle = BranchBundle(pump_tag="B-34004A", mechanical=sig)
    return assemble_report_data(rated, [bundle], {})


def test_report_entry_for_mechanical_only_tag(qapp, tmp_path):
    data = _report_data(tmp_path)
    entry = data["test_data"]["B-34004A"]
    assert "Mechanical Run" in entry
    assert "test_summary" not in entry
    assert entry["Mechanical Run"]["result"] is not None


def test_report_tex_and_docx_contain_section(qapp, tmp_path):
    from pumpflow.binding import export_reports

    data = _report_data(tmp_path)
    paths, errors = export_reports(
        data, ["tex", "docx"], language="en", out_dir=str(tmp_path), stem="mr"
    )
    assert "tex" in paths, errors
    assert "Mechanical running test" in open(paths["tex"], encoding="utf-8").read()
    if "docx" in paths:
        import zipfile

        # Read the raw XML: the shipped template has merged-cell tables that
        # python-docx's row.cells cannot iterate.
        with zipfile.ZipFile(paths["docx"]) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        assert "Mechanical running test" in xml
    else:  # a missing template is an environment issue, not a regression
        assert "Template" in errors["docx"]


def test_blank_template_is_invalid_not_a_verdict(qapp):
    """A witness-day template with times but no values must be invalid (no
    verdict, nothing sent to Report Export)."""
    from pumpflow.nodes.registry import make_node

    node = make_node("mechanical_run")
    s = node.settings
    s["rows"] = [
        {"time": r["time"], "values": {c["name"]: None for c in s["columns"]}}
        for r in s["rows"]
    ]
    out = node.compute({})
    assert node.state == "invalid" and not out
