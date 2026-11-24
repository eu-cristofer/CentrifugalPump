"""Qt (offscreen) tests: System Curve + Operating Point nodes (sprint 11 / UC-03, UC-04)."""

import os

import pytest

from pump import Q_


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


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


def test_registered_kinds(qapp):
    from pumpflow.nodes.registry import NODE_KINDS

    kinds = [k[0] for k in NODE_KINDS]
    assert "system_curve" in kinds and "operating_point" in kinds


def test_default_nodes_evaluate_without_inputs(qapp):
    from pumpflow.nodes.registry import make_node

    sysnode = make_node("system_curve")
    out = sysnode.compute({})
    assert sysnode.state == "ok", sysnode.status
    assert "SystemCurveSpec" in out
    opnode = make_node("operating_point")
    assert opnode.compute({}) == {} and opnode.state == "idle"


def test_wired_system_and_operating_point(qapp, curve):
    from pumpflow.nodes.registry import make_node

    sysnode = make_node("system_curve")
    sysnode.settings.update(
        {"mode": "static_k", "static": 20.0, "static_unit": "m", "k": 2.0e-4}
    )
    spec = sysnode.compute({})["SystemCurveSpec"]
    assert spec.curve.head(Q_(0, "m**3/h")).to("m").magnitude == pytest.approx(20.0)

    opnode = make_node("operating_point")
    out = opnode.compute({"FittedModel": [_fitted(curve)], "SystemCurveSpec": [spec]})
    assert opnode.state == "ok", opnode.status
    result = out["OperatingPointResult"]
    assert result.pump_tag == "B-1"
    assert opnode.status.startswith("Q ") and "m³/h" in opnode.status
    assert "H " in opnode.status
    assert not result.point.extrapolated


def test_two_points_and_pipe_modes(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("system_curve")
    node.settings["mode"] = "two_points"
    node.compute({})
    assert node.state == "ok", node.status

    node.settings["mode"] = "pipe"
    out = node.compute({})
    assert node.state == "ok", node.status
    assert out["SystemCurveSpec"].curve.head(Q_(50, "m**3/h")).magnitude > 20.0


def test_invalid_pipe_is_reported_not_raised(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("system_curve")
    node.settings.update({"mode": "pipe", "diameter": 0.0})
    assert node.compute({}) == {}
    assert node.state == "invalid"


def test_dialogs_open(qapp, curve):
    from pumpflow.nodes.registry import make_node

    sysnode = make_node("system_curve")
    opnode = make_node("operating_point")
    for node in (sysnode, opnode):
        dlg = node.create_dialog(None, lambda: None)
        assert dlg is not None
        dlg.close()
    spec = sysnode.compute({})["SystemCurveSpec"]
    opnode.compute({"FittedModel": [_fitted(curve)], "SystemCurveSpec": [spec]})
    for node in (sysnode, opnode):
        dlg = node.create_dialog(None, lambda: None)
        dlg.close()


def test_system_curve_units_are_persisted():
    """Regression: the system-curve codec entry must live in FIELDS (it was
    misplaced in sprint 11, so units were silently dropped on save)."""
    from pumpflow import settings_codec as codec

    rt = {
        "mode": "static_k",
        "static": 10.0,
        "static_unit": "ft",
        "k": 0.001,
        "exponent": 2.0,
    }
    v2 = codec.encode("system_curve", rt)
    assert v2["static"] == {"value": 10.0, "unit": "ft"}
    assert codec.decode("system_curve", v2) == rt
