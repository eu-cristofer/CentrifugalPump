"""GraphScene.dispose hands every item back to Python and breaks the cycles."""

import os

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_dispose_empties_scene_and_breaks_cycles(qapp):
    from pathlib import Path

    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node
    from pumpflow.persistence import read_json

    project = Path(__file__).parent / "fixtures" / "v1" / "sample_project.pumpflow"
    scene = GraphScene(make_node)
    scene.load_dict(read_json(project))
    logics = [n.logic for n in scene.nodes]
    assert logics and scene.edges
    scene.dispose()
    assert scene.nodes == [] and scene.edges == []
    assert scene.items() == []
    assert all(getattr(lg, "item", None) is None for lg in logics)
