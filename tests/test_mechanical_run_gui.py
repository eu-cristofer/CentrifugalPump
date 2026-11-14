"""Qt (offscreen) tests: Mechanical Run node, codec round-trip, report section (sprint 6)."""

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


def _b34004a_settings():
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
    node.settings.update(_b34004a_settings())
    return node


def test_default_node_evaluates(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("mechanical_run")
    out = node.compute({})
    assert "MechanicalRunResult" in out
    assert "readings" in node.status


def test_b34004a_node_evaluates(qapp):
    node = _node()
    out = node.compute({})
    assert "17 readings" in node.status
    assert "4.0 h" in node.status
    # unfiltered 0.16 in/s = 4.06 mm/s > 3.0 mm/s seed (unverified): FAILED
    assert "FAILED" in node.status
    assert out["MechanicalRunResult"].pump_tag == "B-34004A"
    assert out["MechanicalRunSet"].pump_tag == "B-34004A"
    assert out["MechanicalRunResult"].plot_png is not None


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


def test_codec_roundtrip():
    from pumpflow.settings_codec import decode, encode

    rt = _b34004a_settings()
    v2 = encode("mechanical_run", rt)
    # columns carry Pint strings on disk, overrides {"value", "unit"}
    assert v2["columns"][0]["unit"] == "gal/min"
    st = v2["overrides"]["stabilisation"]["oil_temperature"]
    assert st["delta"] == {"value": 2.0, "unit": "delta_degF"}
    assert st["window"] == {"value": 60.0, "unit": "minute"}
    assert decode("mechanical_run", v2) == rt
    assert encode("mechanical_run", decode("mechanical_run", v2)) == v2


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
    scene.load_dict(doc)
    logic = next(n.logic for n in scene.nodes if n.logic.kind == "mechanical_run")
    assert logic.settings["pump_tag"] == "B-34004A"
    assert len(logic.settings["rows"]) == 17


def _report_data(tmp_path):
    from pumpflow.binding import assemble_report_data
    from pumpflow.nodes.registry import make_node
    from pumpflow.signals import BranchBundle

    rated = make_node("rated_point").compute({})["RatedPoint"]
    node = _node()
    sig = node.compute({})["MechanicalRunResult"]
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
