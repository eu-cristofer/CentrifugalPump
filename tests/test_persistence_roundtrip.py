"""
``.pumpflow`` persistence guard — UC-02 / UC-09 (the workbench demo case).

Two layers:

1. **Qt-free** — the shipped ``examples/sample_project.pumpflow`` must stay identical
   to ``sample_data.sample_project_doc()``, so the demo file can never silently drift
   from its builder. Runs everywhere.
2. **Qt-required** — load the document into a real :class:`GraphScene` and assert it
   is a fixed point of ``to_dict(load_dict(doc))`` and that every node/edge wires up.
   Skipped cleanly when PySide6 is not installed (headless ``offscreen`` platform).
"""

import os
from pathlib import Path

import pytest

from pumpflow.persistence import read_json
from pumpflow.sample_data import sample_project_doc

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample_project.pumpflow"


# --------------------------------------------------------------------------- #
# Qt-free: the shipped file tracks the builder
# --------------------------------------------------------------------------- #
def test_shipped_file_exists():
    assert SAMPLE.is_file(), f"missing sample project: {SAMPLE}"


def test_shipped_file_matches_builder():
    # Regenerate with: python -c "from pumpflow.sample_data import sample_project_doc;
    #   from pumpflow.persistence import write_json;
    #   write_json('examples/sample_project.pumpflow', sample_project_doc())"
    assert read_json(SAMPLE) == sample_project_doc()


def test_builder_shape():
    doc = sample_project_doc()
    kinds = [n["kind"] for n in doc["nodes"]]
    assert kinds == [
        "rated_point", "test_points", "correction", "curve_fit",
        "performance_plot", "compliance", "report_export",
    ]
    assert len(doc["edges"]) == 11
    # Every edge endpoint references a declared node id.
    ids = {n["id"] for n in doc["nodes"]}
    for e in doc["edges"]:
        assert e["src_node"] in ids and e["dst_node"] in ids


# --------------------------------------------------------------------------- #
# Qt-required: real scene round-trip (skips without PySide6)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI round-trip skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _build_scene():
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    scene = GraphScene(make_node)
    scene.load_dict(sample_project_doc())
    return scene


def test_scene_roundtrip_is_fixed_point(qapp):
    scene = _build_scene()
    assert scene.to_dict() == sample_project_doc()


def test_scene_wires_every_node_and_edge(qapp):
    doc = sample_project_doc()
    scene = _build_scene()
    assert len(scene.nodes) == len(doc["nodes"])
    assert len(scene.edges) == len(doc["edges"])  # all edges connected, none dropped
