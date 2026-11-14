"""Qt (offscreen) tests: per-column units on the Test Points table."""

import copy
import os

import pytest

from pumpflow.sample_data import sample_project_doc


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _setup():
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    scene = GraphScene(make_node)
    scene.load_dict(sample_project_doc())
    logic = next(n.logic for n in scene.nodes if n.logic.kind == "test_points")
    dlg = logic.create_dialog(None, on_change=lambda: None)
    return scene, logic, dlg


def _header(dlg, key):
    from pumpflow.nodes import ui

    strip = dlg.findChildren(ui.UnitHeaderStrip)[0]
    for h in strip.headers:
        if h.col == [
            "q",
            "p_suc",
            "p_dis",
            "temp_c",
            "n",
            "power",
            "head",
            "eff",
        ].index(key):
            return h
    raise AssertionError(key)


def _select(header, label):
    header.combo.setCurrentIndex(header.combo.findData(label))


def _head(logic):
    from pumpflow.binding import row_head
    from pumpflow.nodes.test_points import _row_from_dict

    s = logic.settings
    return [
        row_head(_row_from_dict(r, s["columns"], s["pressure_ref"])).to("m").magnitude
        for r in s["rows"]
    ]


def _col(logic, key):
    return [r[key] for r in logic.settings["rows"]]


def test_capacity_roundtrip_restores_values_and_head(qapp):
    _scene, logic, dlg = _setup()
    q0, h0 = _col(logic, "q"), _head(logic)
    h = _header(dlg, "q")
    _select(h, "US GPM")
    assert logic.settings["columns"]["q"] == "US GPM"
    assert _col(logic, "q")[0] != pytest.approx(q0[0])
    _select(h, "m³/h")
    assert logic.settings["columns"]["q"] == "m³/h"
    assert _col(logic, "q") == pytest.approx(q0, rel=1e-12)
    assert _head(logic) == pytest.approx(h0, rel=1e-12)


def test_pressure_unit_roundtrip(qapp):
    _scene, logic, dlg = _setup()
    cols = logic.settings["columns"]
    unit0 = cols["p_suc"]
    ps0, pd0, h0 = _col(logic, "p_suc"), _col(logic, "p_dis"), _head(logic)
    h = _header(dlg, "p_suc")
    other = "psi" if unit0 != "psi" else "bar"
    _select(h, other)
    assert cols["p_suc"] == other and cols["p_dis"] == other
    assert _head(logic) == pytest.approx(h0, rel=1e-9)
    _select(h, unit0)
    assert _col(logic, "p_suc") == pytest.approx(ps0, rel=1e-12, abs=1e-12)
    assert _col(logic, "p_dis") == pytest.approx(pd0, rel=1e-12, abs=1e-12)
    assert _head(logic) == pytest.approx(h0, rel=1e-9)


def test_pressure_reference_roundtrip(qapp):
    from PySide6.QtWidgets import QComboBox

    _scene, logic, dlg = _setup()
    ps0, pd0, h0 = _col(logic, "p_suc"), _col(logic, "p_dis"), _head(logic)
    ref = dlg.findChild(QComboBox, "PressureRef")
    ref.setCurrentIndex(ref.findData("a"))
    assert logic.settings["pressure_ref"] == "a"
    assert _col(logic, "p_suc")[0] > ps0[0]
    assert _head(logic) == pytest.approx(h0, rel=1e-9)
    ref.setCurrentIndex(ref.findData("g"))
    assert logic.settings["pressure_ref"] == "g"
    assert _col(logic, "p_suc") == pytest.approx(ps0, rel=1e-12, abs=1e-12)
    assert _col(logic, "p_dis") == pytest.approx(pd0, rel=1e-12, abs=1e-12)
    assert _head(logic) == pytest.approx(h0, rel=1e-9)


def test_pressure_field_converts_between_g_and_a(qapp):
    from pumpflow.nodes import ui

    f = ui.PressureField(2.0, "bar", "g")
    f.set_ref("a")
    assert f.magnitude() == pytest.approx(3.01325, rel=1e-9)
    assert f.pressure().reference == "a"
    f.set_ref("g")
    assert f.magnitude() == pytest.approx(2.0, rel=1e-12)
    f.set_unit("kPa")
    assert f.magnitude() == pytest.approx(200.0, rel=1e-9)


def test_linked_pressure_fields_share_unit_and_ref(qapp):
    from pumpflow.nodes import ui

    a = ui.PressureField(1.0, "bar", "g")
    b = ui.PressureField(2.0, "bar", "g")
    ui.link_pressure_fields(a, b)
    a.set_unit("psi")
    assert b.unit_label() == "psi"
    b.set_ref("a")
    assert a.ref() == "a"


def test_paste_with_headers_sets_units(qapp):
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QPushButton

    _scene, logic, dlg = _setup()
    QGuiApplication.clipboard().setText(
        "Q [gpm]\tP_suc [psi g]\tP_dis [psi g]\tT [°F]\tN [rpm]\tP [hp]\n"
        "1000\t10\t100\t77\t1800\t200\n"
    )
    next(b for b in dlg.findChildren(QPushButton) if "Paste" in b.text()).click()
    cols = logic.settings["columns"]
    assert cols["q"] == "US GPM" and cols["p_suc"] == "psi" and cols["temp_c"] == "°F"
    assert cols["power"] == "hp"
    assert logic.settings["rows"] == [
        {
            "q": 1000.0,
            "p_suc": 10.0,
            "p_dis": 100.0,
            "temp_c": 77.0,
            "n": 1800.0,
            "power": 200.0,
            "head": None,
            "eff": None,
        }
    ]


def test_default_settings_follow_preset_and_exchange_import(qapp):
    from pumpflow import units
    from pumpflow.nodes.test_points import testset_settings
    from pumpflow.persistence import testset_from_json
    from pumpflow.sample_data import SINGLE_PUMP_JSON

    tps = testset_from_json(SINGLE_PUMP_JSON)
    shape = testset_settings(tps)
    assert shape["columns"]["q"] == "m³/h" and shape["columns"]["p_suc"] == "bar"
    assert shape["rows"][0]["q"] == tps.rows[0].q.to("m**3/h").magnitude
    prev = units.PREFS.preset
    try:
        units.PREFS.set_preset("US")
        from pumpflow.nodes.test_points import TestPointsTableNode

        cols = TestPointsTableNode().default_settings()["columns"]
        assert (
            cols["q"] == "US GPM" and cols["p_suc"] == "psi" and cols["temp_c"] == "°F"
        )
    finally:
        units.PREFS.set_preset(prev)


def test_every_node_dialog_still_opens(qapp):
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    scene = GraphScene(make_node)
    scene.load_dict(copy.deepcopy(sample_project_doc()))
    for item in scene.nodes:
        dlg = item.logic.create_dialog(None, on_change=lambda: None)
        assert dlg is not None
        dlg.close()
