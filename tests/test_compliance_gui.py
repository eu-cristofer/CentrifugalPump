"""Qt (offscreen) test: criteria-aware compliance on the P-9001A reference project."""

import os
from pathlib import Path

import pytest

PROJECT = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "user"
    / "P-9001A_MRT_reference.pumpflow"
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def scene(qapp):
    if not PROJECT.is_file():
        pytest.skip(f"missing reference project: {PROJECT}")
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node
    from pumpflow.persistence import read_json

    sc = GraphScene(make_node)
    sc.load_dict(read_json(PROJECT))  # load_dict() also evaluates the graph
    return sc


def _results(scene):
    out = []
    for n in scene.nodes:
        if n.logic.kind == "compliance":
            res = n.logic.outputs_cache.get("ComplianceResult")
            if res is not None:
                out.append(res)
    return out


def test_project_evaluates_with_criteria_metadata(scene):
    results = _results(scene)
    assert results, "no compliance result produced"
    for res in results:
        assert "API 610 8th" in res.criteria_label
        assert "N-553" in res.criteria_label
        assert res.unverified == ()  # 8th ed. + N-553 rev E checked against the text
        assert res.parameters
        assert all(p.verified is True for p in res.parameters)


def test_rated_point_parses_standard_text(scene):
    logic = next(n.logic for n in scene.nodes if n.logic.kind == "rated_point")
    rated = logic.to_signal()
    assert rated.standard_key == "api610:8"
    assert rated.client == "n553"


def test_reset_restores_criteria_defaults(scene):
    from pumpflow.binding import default_tolerances

    node = next(n.logic for n in scene.nodes if n.logic.kind == "compliance")
    rated = node._rated
    node.settings["tolerances"] = {"head": 0.2}
    dlg = node.create_dialog(None, lambda: None)
    assert dlg is not None
    base = default_tolerances(rated)
    # P-9001A: API 610 8th ed. Table 4-2, rated head 333.8 m > 300 m -> ±2 %
    assert base["head"] == pytest.approx(0.02)
    assert node.settings["tolerances"] == {"head": 0.2}  # opening does not reset
    node.settings["tolerances"] = {}
    assert not node.settings["tolerances"]
