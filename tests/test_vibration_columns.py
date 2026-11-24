"""Optional vibration columns in the Test Points table (Annex M / App. T data)."""

import copy
import os

import pytest

from pump import Q_


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _node():
    from pumpflow.nodes.registry import make_node

    return make_node("test_points")


def test_header_parsing():
    from pumpflow.units import parse_unit_header

    assert parse_unit_header("Vib DE [in/s]") == ("vib_de", "in/s", None)
    assert parse_unit_header("Vib NDE f [mm/s]") == ("vib_nde_f", "mm/s", None)
    assert parse_unit_header("DE") == ("vib_de", None, None)


def test_rows_carry_vibration_quantities(qapp):
    node = _node()
    s = node.settings
    s["columns"]["vib_de"] = "in/s"
    s["rows"][2]["vib_de"] = 0.16
    s["rows"][2]["vib_nde_f"] = 2.0  # no label stored -> exchange unit mm/s
    tps = node.to_signal()
    row = tps.rows[2]
    assert row.vibration["vib_de"].to("mm/s").magnitude == pytest.approx(4.064)
    assert row.vibration["vib_nde_f"].to("mm/s").magnitude == pytest.approx(2.0)
    assert "vib_de" not in tps.rows[0].vibration


def test_codec_writes_vibration_units_only_with_data(qapp):
    from pumpflow.settings_codec import decode, encode

    node = _node()
    plain = encode("test_points", copy.deepcopy(node.settings))
    assert not any(k.startswith("vib") for k in plain["columns"])

    s = copy.deepcopy(node.settings)
    s["columns"]["vib_de"] = "in/s"
    s["rows"][1]["vib_de"] = 0.12
    v2 = encode("test_points", copy.deepcopy(s))
    assert v2["columns"]["vib_de"] == "in/s"
    assert "vib_nde" not in v2["columns"]
    back = decode("test_points", copy.deepcopy(v2))
    assert back["columns"]["vib_de"] == "in/s"
    assert back["rows"][1]["vib_de"] == pytest.approx(0.12)
    assert encode("test_points", copy.deepcopy(back)) == v2  # fixed point


def test_dialog_toggle_and_edit(qapp):
    from PySide6.QtWidgets import QCheckBox, QTableWidget

    node = _node()
    dlg = node.create_dialog(None, lambda: None)
    table = dlg.findChild(QTableWidget, "TestGrid")
    box = dlg.findChild(QCheckBox, "ShowVibration")
    assert not box.isChecked()
    assert all(table.isColumnHidden(c) for c in range(8, 12))
    box.setChecked(True)
    assert not any(table.isColumnHidden(c) for c in range(8, 12))
    table.item(0, 8).setText("2.5")  # Vib DE on the first row
    assert node.settings["rows"][0]["vib_de"] == pytest.approx(2.5)
    dlg.close()


def test_correction_carries_vibration(qapp):
    from pumpflow.binding import correct_curve
    from pumpflow.nodes.registry import make_node

    node = _node()
    node.settings["rows"][3]["vib_de"] = 2.2
    rated = make_node("rated_point").compute({})["RatedPoint"]
    corrected = correct_curve(rated, node.to_signal(), target_speed=rated.speed)
    vibs = [pair["measured"]["vib"] for pair in corrected.before_after]
    assert {"vib_de": pytest.approx(2.2)} in vibs
    assert sum(1 for v in vibs if v) == 1
