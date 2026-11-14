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
    rated = next(n for n in doc["nodes"] if n["kind"] == "rated_point")
    assert rated["settings"]["npsha"] == 0.0


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


# --------------------------------------------------------------------------- #
# B-34004 FAT reference project (twin unit A filled in, unit B blank template)
# --------------------------------------------------------------------------- #
B34004 = SAMPLE.parent / "user" / "B-34004A_MRT_reference.pumpflow"


def test_blank_test_rows_are_invalid_not_crashing():
    """A template row with no N / P / ΔP must be rejected by validation; before
    the fix it reached the Correction node and raised ``float division by zero``."""
    from pumpflow.signals import TestPointSet, TestRow

    good = TestRow(q_m3h=5, p_suction=0, p_discharge=30, temp_c=50, speed_rpm=10301, power_kw=20)
    blank = TestRow(q_m3h=5, p_suction=0, p_discharge=0, temp_c=25, speed_rpm=0, power_kw=0)
    assert TestPointSet("A", (good,) * 3).is_valid() == (True, "")
    ok, msg = TestPointSet("B", (good, good, blank)).is_valid()
    assert not ok and "Row 3" in msg
    no_dp = TestRow(q_m3h=5, p_suction=1, p_discharge=1, temp_c=50, speed_rpm=10301, power_kw=20)
    assert not TestPointSet("B", (good, good, no_dp)).is_valid()[0]
    # an explicit head override makes equal pressures acceptable
    pinned = TestRow(5, 1, 1, 50, 10301, 20, head_m=300.0)
    assert TestPointSet("B", (good, good, pinned)).is_valid()[0]


@pytest.fixture(scope="module")
def b34004_scene(qapp):
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    scene = GraphScene(make_node)
    scene.load_dict(read_json(B34004))
    return scene


def test_b34004_roundtrip_and_wiring(b34004_scene):
    doc = read_json(B34004)
    out = b34004_scene.to_dict()
    assert out["nodes"] == doc["nodes"] and out["edges"] == doc["edges"]
    assert len(b34004_scene.edges) == len(doc["edges"])


def test_b34004_evaluates_end_to_end(b34004_scene):
    logic = {n.logic.node_id: n.logic for n in b34004_scene.nodes}
    assert not [k for k, lg in logic.items() if lg.state == "error"]
    for k in ("test_a", "corr_a", "fit_a", "plot_a", "check_a", "report"):
        assert logic[k].state == "ok", (k, logic[k].status)
    assert logic["test_b"].state == "invalid"  # blank template waits for readings

    res = logic["check_a"].outputs_cache["ComplianceResult"]
    assert res.overall_pass
    got = {p.name: p for p in res.parameters}
    # Sanity vs the Sundyne certified test converted to datasheet conditions
    assert got["Head"].predicted == pytest.approx(339.4, abs=1.0)  # rated 333.8 m
    assert got["Power"].predicted == pytest.approx(24.6, abs=0.3)  # rated 26.9 kW
    assert got["Efficiency"].predicted == pytest.approx(36.8, abs=0.5)  # rated 32.7 %


def test_b34004_cli_exports(qapp, tmp_path):
    from pumpflow.export_cli import main

    rc = main([str(B34004), "--formats", "docx,tex", "--out", str(tmp_path), "--stem", "R"])
    assert rc == 0
    assert (tmp_path / "R.docx").is_file() and (tmp_path / "R.tex").is_file()
    assert "B-34004A" in (tmp_path / "R.tex").read_text(encoding="utf-8")
