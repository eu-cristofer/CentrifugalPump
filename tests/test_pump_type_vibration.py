"""API 610 pump types: vibration locations, limits by family, high-speed rule."""

import json
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pump import Q_
from pump.acceptance import AcceptanceCriteria
from pump.vibration import (
    HighSpeedRule,
    locations_for,
    plot_high_speed_chart,
    pump_family,
    vibration_keys,
)

PROJECT = (
    Path(__file__).resolve().parents[1]
    / "examples/user/B-34004A_MRT_reference.pumpflow"
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


# --------------------------------------------------------------------------- #
# Library
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "code, family, where",
    [
        ("OH1", "OH", ["Drive-end bearing housing", "Non-drive-end bearing housing"]),
        ("OH3", "OH_VIL", ["Driver mounting surface", "Pump bearing housing"]),
        ("OH6", "OH6", ["Gearbox housing"]),
        ("BB5", "BB", ["Drive-end bearing housing", "Non-drive-end bearing housing"]),
        ("VS6", "VS", ["Thrust bearing housing / motor mounting flange"]),
        (None, None, ["Drive-end bearing housing", "Non-drive-end bearing housing"]),
    ],
)
def test_locations_by_type(code, family, where):
    assert pump_family(code) == family
    assert [loc.label for loc in locations_for(code)] == where


def test_limits_by_family_and_edition():
    for key in ("api610:8", "api610:11", "api610:12"):
        vib = AcceptanceCriteria.load(key).vibration
        assert vib.limits("BB2")["overall"] == Q_(3.0, "mm/s")
        assert vib.limits("BB2")["filtered"] == Q_(2.0, "mm/s")
        assert vib.limits("VS1")["overall"] == Q_(5.0, "mm/s")  # Table 9 / 2-6
        assert vib.limits("VS1")["filtered"] == Q_(3.4, "mm/s")
    assert AcceptanceCriteria.load("api610:8").vibration.verified is True


def test_high_speed_rule_only_from_the_11th_edition():
    n, p = Q_(10212, "rpm"), Q_(25, "kW")
    old = AcceptanceCriteria.load("api610:8").vibration.limits("OH6", n, p)
    assert old["overall"] == Q_(3.0, "mm/s")  # no allowance in the 8th edition
    new = AcceptanceCriteria.load("api610:12").vibration.limits("OH6", n, p)
    assert new["overall"].magnitude == pytest.approx(4.1)
    assert new["filtered"].magnitude == pytest.approx(2.7)  # 0.67 x, 2 sig. figures
    assert "high-speed" in new["basis"]
    vs = AcceptanceCriteria.load("api610:12").vibration.limits("VS1", n, p)
    assert vs["overall"] == Q_(5.0, "mm/s")  # the figure is for horizontal pumps


def _crossings(rule, power_kw):
    ns = np.geomspace(500, 30000, 6000)
    v = [rule.curve_value(n, power_kw) for n in ns]
    start = next(n for n, x in zip(ns, v) if x > 3.0 + 1e-9)
    top = next(n for n, x in zip(ns, v) if x >= 4.5 - 1e-9)
    return start, top


def test_chart_curves_match_the_figure_labels():
    rule = HighSpeedRule()
    # curve 1 (>= 3000 kW) reaches the 4.5 cap near 2 000-3 000 r/min,
    # curve 7 (<= 300 kW) leaves 3.0 at 3 600 and reaches 4.5 near 14 000.
    assert 2600 < _crossings(rule, 3000)[1] < 2900
    start7, top7 = _crossings(rule, 300)
    assert 3550 < start7 < 3700 and 13500 < top7 < 14300
    assert rule.overall(Q_(1000, "rpm"), Q_(300, "kW")).magnitude == 3.0
    png = plot_high_speed_chart(rule, Q_(10212, "rpm"), Q_(25, "kW"))
    assert png.startswith(b"\x89PNG")


# --------------------------------------------------------------------------- #
# Workbench
# --------------------------------------------------------------------------- #
def test_rated_point_pump_type_stored_only_when_set(qapp):
    from PySide6.QtWidgets import QComboBox

    from pumpflow.nodes.registry import make_node

    node = make_node("rated_point")
    assert node.compute({})["RatedPoint"].pump_type is None
    dlg = node.create_dialog(None, lambda: None)
    combo = dlg.findChild(QComboBox, "PumpType")
    combo.setCurrentIndex(combo.findData("VS4"))
    assert node.settings["pump_type"] == "VS4"
    assert node.compute({})["RatedPoint"].pump_type == "VS4"
    combo.setCurrentIndex(combo.findData(""))
    assert "pump_type" not in node.settings
    dlg.close()


def test_test_points_columns_follow_the_wired_pump_type(qapp):
    from PySide6.QtWidgets import QTableWidget

    from pumpflow.nodes.registry import make_node

    rated = make_node("rated_point")
    rated.settings["pump_type"] = "OH6"
    tp = make_node("test_points")
    tp.settings["rows"][0]["vib_de"] = 1.5  # data at another type's location
    tp.compute({"RatedPoint": [rated.compute({})["RatedPoint"]]})
    dlg = tp.create_dialog(None, lambda: None)
    table = dlg.findChild(QTableWidget, "TestGrid")
    titles = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    assert any(t.startswith("Gearbox overall") for t in titles)
    assert any(t.startswith("Gearbox filt.") for t in titles)
    assert any(t.startswith("DE overall") for t in titles)  # data never hidden
    assert vibration_keys("OH6") == ["vib_gb", "vib_gb_f"]
    dlg.close()


def test_b34004a_sundyne_vibration_in_the_summary(qapp):
    from pumpflow.binding import test_data_summaries
    from pumpflow.export_cli import build_scene, report_inputs

    _app, scene = build_scene(str(PROJECT))
    rated, branches, s = report_inputs(scene)
    assert rated.pump_type == "OH6"
    (summary,) = test_data_summaries(rated, branches, s)
    overall, filtered = summary.vibration
    assert overall.location == "Gearbox housing"
    # Sundyne spectra pp. 6-11 (RMS per the vendor): 0.148 in/s at design flow,
    # 0.151 in/s maximum in the preferred region; 8th edition limits 3.0 / 2.0.
    assert overall.rated == (pytest.approx(3.76, abs=0.01), 3.0)
    assert overall.por == (pytest.approx(3.84, abs=0.01), 3.0)
    assert filtered.por == (pytest.approx(2.24, abs=0.01), 2.0)
    assert not summary.extra.get("vibration_chart_png")  # no rule in the 8th


def test_12th_edition_gives_the_high_speed_limit_and_chart(qapp, tmp_path):
    from pumpflow.binding import test_data_summaries
    from pumpflow.export_cli import build_scene, report_inputs

    doc = json.loads(PROJECT.read_text(encoding="utf-8"))
    next(n for n in doc["nodes"] if n["id"] == "rated")["settings"][
        "standard_key"
    ] = "api610:12"
    project = tmp_path / "ed12.pumpflow"
    project.write_text(json.dumps(doc), encoding="utf-8")
    _app, scene = build_scene(str(project))
    rated, branches, s = report_inputs(scene)
    (summary,) = test_data_summaries(rated, branches, s)
    assert summary.vibration[0].por[1] == pytest.approx(4.1)
    assert summary.extra["vibration_chart_png"].startswith(b"\x89PNG")


def test_mechanical_run_uses_the_type_limits(qapp):
    from pumpflow.binding import check_mechanical_run
    from pumpflow.export_cli import build_scene
    from pumpflow.nodes.mechanical_run import build_log
    from pumpflow.signals import MechanicalRunSet

    _app, scene = build_scene(str(PROJECT))
    node = next(n.logic for n in scene.nodes if n.logic.node_id == "mrt_a")
    rated = next(n.logic for n in scene.nodes if n.logic.node_id == "rated").to_signal()
    run_set = MechanicalRunSet(pump_tag="B-34004A", log=build_log(node.settings))

    def limit(r):
        sig = check_mechanical_run(run_set, r)
        return {
            c.role: round(c.limit.to("mm/s").magnitude, 6)
            for c in sig.result.channels
            if c.limit is not None
        }

    assert limit(rated)["vibration_unfiltered"] == 3.0  # OH6, 8th edition
    vs = limit(replace(rated, pump_type="VS1"))
    assert vs["vibration_unfiltered"] == 5.0 and vs["vibration_filtered"] == 3.4
