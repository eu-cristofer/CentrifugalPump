"""Qt (offscreen) test: Test Points node with bench geometry (sprint 4)."""

import os

import pytest

from pumpflow.sample_data import sample_project_doc


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _logic():
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    scene = GraphScene(make_node)
    scene.load_dict(sample_project_doc())
    return scene, next(n.logic for n in scene.nodes if n.logic.kind == "test_points")


def _heads(tps):
    from pumpflow.binding import row_head

    return [
        row_head(r, tps.test_density, tps.geometry).to("m").magnitude for r in tps.rows
    ]


def test_geometry_shifts_head_by_velocity_plus_elevation(qapp):
    from pumpflow.binding import row_head_components

    _scene, logic = _logic()
    base = logic.to_signal()
    assert base.geometry is None
    h0 = _heads(base)

    logic.settings.update(
        suction_id=150.0,
        suction_id_unit="mm",
        discharge_id=100.0,
        discharge_id_unit="mm",
        suction_z=0.3,
        suction_z_unit="m",
        discharge_z=0.8,
        discharge_z_unit="m",
    )
    tps = logic.to_signal()
    assert tps.geometry is not None and not tps.geometry.is_empty
    assert tps.geometry.components_available() == (True, True)
    h1 = _heads(tps)

    for r, a, b in zip(tps.rows, h0, h1):
        c = row_head_components(r, tps.test_density, tps.geometry)
        extra = c["velocity"].to("m").magnitude + c["elevation"].to("m").magnitude
        assert b - a == pytest.approx(extra, abs=1e-9)
        if r.head is None:  # a measured head override wins: no geometry terms
            assert c["elevation"].to("m").magnitude == pytest.approx(0.5, rel=1e-9)
        else:
            assert c["velocity"].magnitude == 0 and c["elevation"].magnitude == 0

    # the node still evaluates and emits the set carrying the geometry
    out = logic.compute({})
    assert out["TestPointSet"].geometry == tps.geometry


def test_dialog_head_column_tooltip_lists_components(qapp):
    from PySide6.QtWidgets import QTableWidget

    _scene, logic = _logic()
    logic.settings.update(
        suction_id=150.0,
        discharge_id=100.0,
        suction_z=0.3,
        discharge_z=0.8,
    )
    dlg = logic.create_dialog(None, on_change=lambda: None)
    table = dlg.findChild(QTableWidget, "TestGrid")
    tip = table.item(0, 6).toolTip()
    assert "pressure" in tip and "velocity" in tip and "elevation" in tip


def test_unset_geometry_emits_none(qapp):
    _scene, logic = _logic()
    logic.settings.update(suction_id=0.0, discharge_id=0.0)  # non-positive IDs ignored
    assert logic.to_signal().geometry is None
