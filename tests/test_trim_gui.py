"""Qt (offscreen) tests: Impeller Trim node, rated-point diameters, codec (sprint 10 / UC-07)."""

import os

import pytest

from pump import Q_


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _rated(d_imp=128.0, d_max=131.0, d_min=125.0):
    from pumpflow.nodes.registry import make_node

    node = make_node("rated_point")
    node.settings.update(
        {
            "d_imp": d_imp,
            "d_imp_unit": "mm",
            "d_max": d_max,
            "d_max_unit": "mm",
            "d_min": d_min,
            "d_min_unit": "mm",
        }
    )
    return node.compute({})["RatedPoint"]


def _fitted(curve):
    from pumpflow.binding import fit_model
    from pumpflow.signals import CorrectedCurve

    corrected = CorrectedCurve(
        pump_tag="B-1",
        curve=curve,
        fluid=curve.fluid,
        target_speed=Q_(1750, "rpm"),
    )
    return fit_model(corrected, degree=3)


def test_registered_kind(qapp):
    from pumpflow.nodes.registry import NODE_KINDS

    assert any(k[0] == "trim" for k in NODE_KINDS)


def test_rated_point_carries_impeller_diameters(qapp):
    rated = _rated()
    assert rated.impeller_diameter.to("mm").magnitude == pytest.approx(128.0)
    assert rated.impeller_diameter_max.to("mm").magnitude == pytest.approx(131.0)
    assert rated.impeller_diameter_min.to("mm").magnitude == pytest.approx(125.0)
    unset = _rated(None, None, None)
    assert unset.impeller_diameter is None
    assert unset.impeller_diameter_max is None and unset.impeller_diameter_min is None


def test_rated_diameter_codec_round_trip(qapp):
    from pumpflow.settings_codec import decode, encode

    rt = {
        "q": 833.0,
        "q_unit": "m³/h",
        "d_imp": 128.0,
        "d_imp_unit": "mm",
        "d_max": None,
        "d_max_unit": "mm",
    }
    v2 = encode("rated_point", rt)
    assert v2["d_imp"]["value"] == 128.0
    assert "d_max" not in v2 and "d_max_unit" not in v2  # unset: omitted on disk
    back = decode("rated_point", v2)
    assert back["d_imp"] == 128.0 and back["d_imp_unit"] == "mm"
    assert "d_max" not in back
    assert encode("rated_point", back) == v2


def test_trim_node_default_idle_without_inputs(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("trim")
    assert node.compute({}) == {}
    assert node.state == "idle"


def test_trim_node_waits_for_reference_diameter(qapp, curve):
    from pumpflow.nodes.registry import make_node

    node = make_node("trim")
    out = node.compute({"FittedModel": [_fitted(curve)], "RatedPoint": [_rated(None)]})
    assert out == {} and node.state == "invalid"


def test_trim_node_target_mode(qapp, curve):
    from pumpflow.nodes.registry import make_node

    node = make_node("trim")
    node.settings.update({"mode": "target", "d_target": 125.0, "d_target_unit": "mm"})
    out = node.compute({"FittedModel": [_fitted(curve)], "RatedPoint": [_rated()]})
    assert node.state == "ok", node.status
    trimmed = out["CorrectedCurve"]
    assert trimmed.pump_tag == "B-1@D=125.0 mm"
    assert "125.0 mm" in node.status and "-2.3" in node.status
    assert "⚠" not in node.status
    assert len(trimmed.curve) == len(curve)
    assert len(trimmed.before_after) == len(curve)


def test_trim_node_warns_outside_range_and_max_trim(qapp, curve):
    from pumpflow.nodes.registry import make_node

    node = make_node("trim")
    node.settings.update({"mode": "target", "d_target": 140.0, "d_target_unit": "mm"})
    node.compute({"FittedModel": [_fitted(curve)], "RatedPoint": [_rated()]})
    assert node.state == "ok"
    assert "max trim" in node.status and "datasheet range" in node.status


def test_trim_node_accepts_corrected_curve_input(qapp, curve):
    from pumpflow.nodes.registry import make_node
    from pumpflow.signals import CorrectedCurve

    corrected = CorrectedCurve(
        pump_tag="B-2", curve=curve, fluid=curve.fluid, target_speed=Q_(1750, "rpm")
    )
    node = make_node("trim")
    node.settings.update({"mode": "target", "d_target": 126.0, "d_target_unit": "mm"})
    out = node.compute({"CorrectedCurve": [corrected], "RatedPoint": [_rated()]})
    assert out["CorrectedCurve"].pump_tag == "B-2@D=126.0 mm"


def test_trim_node_duty_mode_and_binding(qapp, curve):
    from pumpflow.binding import diameter_for_rated
    from pumpflow.nodes.registry import make_node

    fitted, rated = _fitted(curve), _rated()
    d = diameter_for_rated(fitted, rated)
    assert 0.9 * 128.0 < d.to("mm").magnitude < 1.1 * 128.0

    node = make_node("trim")
    node.settings["mode"] = "duty"
    out = node.compute({"FittedModel": [fitted], "RatedPoint": [rated]})
    assert node.state == "ok", node.status
    assert out["CorrectedCurve"].pump_tag == f"B-1@D={d.to('mm').magnitude:.1f} mm"


def test_trim_dialog_opens(qapp, curve):
    from pumpflow.nodes.registry import make_node

    node = make_node("trim")
    dlg = node.create_dialog(None, lambda: None)
    assert dlg is not None
    dlg.close()
    node.compute({"FittedModel": [_fitted(curve)], "RatedPoint": [_rated()]})
    dlg = node.create_dialog(None, lambda: None)
    dlg.close()
