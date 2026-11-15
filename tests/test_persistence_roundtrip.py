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

from pumpflow.persistence import read_json, read_project
from pumpflow.sample_data import sample_project_doc

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample_project.pumpflow"


# --------------------------------------------------------------------------- #
# Qt-free: the shipped file tracks the builder
# --------------------------------------------------------------------------- #
def test_shipped_file_exists():
    assert SAMPLE.is_file(), f"missing sample project: {SAMPLE}"


def test_shipped_file_matches_builder():
    # Regenerate with the scene (schema v2):
    #   scene.load_dict(sample_project_doc()); write_json(path, scene.to_dict())
    assert read_json(SAMPLE) == sample_project_doc()


def test_builder_shape():
    doc = sample_project_doc()
    assert doc["meta"] == {"unit_preset": "SI", "schema_version": 2}
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
    assert rated["settings"]["npsha"] == {"value": 0.0, "unit": "m"}


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
    from pump import Q_, Pressure
    from pumpflow.signals import TestPointSet, TestRow

    def row(p_suc, p_dis, n, power, **kw):
        return TestRow(
            q=Q_(5, "m**3/h"),
            p_suction=Pressure(Q_(p_suc, "bar"), "g"),
            p_discharge=Pressure(Q_(p_dis, "bar"), "g"),
            temperature=Q_(50, "degC"),
            speed=Q_(n, "rpm"),
            power=Q_(power, "kW"),
            **kw,
        )

    good = row(0, 30, 10301, 20)
    blank = row(0, 0, 0, 0)
    assert TestPointSet("A", (good,) * 3).is_valid() == (True, "")
    ok, msg = TestPointSet("B", (good, good, blank)).is_valid()
    assert not ok and "Row 3" in msg
    no_dp = row(1, 1, 10301, 20)
    assert not TestPointSet("B", (good, good, no_dp)).is_valid()[0]
    # an explicit head override makes equal pressures acceptable
    pinned = row(1, 1, 10301, 20, head=Q_(300.0, "m"))
    assert TestPointSet("B", (good, good, pinned)).is_valid()[0]


@pytest.fixture(scope="module")
def b34004_scene(qapp):
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node

    scene = GraphScene(make_node)
    scene.load_dict(read_project(B34004))
    return scene


def test_b34004_roundtrip_and_wiring(b34004_scene):
    doc = read_project(B34004)  # migrated to v2 if the shipped file is still v1
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


def test_every_node_dialog_opens(qapp, b34004_scene):
    """Open every node's property dialog: on the B-34004 project (branch B has
    no fitted model, so its Compliance node has no rated input) and on a fresh
    default instance of every registered node kind. A dialog that touches a
    renamed signal field fails here instead of in front of the user."""
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QMessageBox

    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import NODE_KINDS, make_node

    def _silence(*_a, **_k):
        return None

    for name in ("information", "warning", "critical"):
        setattr(QMessageBox, name, staticmethod(_silence))

    fresh = GraphScene(make_node)
    for kind in NODE_KINDS:
        fresh.add_node(kind[0] if isinstance(kind, tuple) else kind, QPointF(0, 0))
    fresh.evaluate()
    for scene in (b34004_scene, fresh):
        for item in scene.nodes:
            assert item.logic.state != "error", (item.logic.kind, item.logic.status)
            dlg = item.logic.create_dialog(None, scene.evaluate)
            if dlg is not None:
                dlg.close()


def test_b34004_diameter_for_rated_duty_within_datasheet_range(qapp, b34004_scene):
    """Sprint 10: diameter that puts B-34004A on its rated point lies inside the
    datasheet impeller range (I-FD-...-SWM-001 rev B: 125 / 128 / 131 mm)."""
    from pumpflow.binding import diameter_for_rated

    logic = {n.logic.node_id: n.logic for n in b34004_scene.nodes}
    fitted = logic["fit_a"].outputs_cache["FittedModel"]
    rated = logic["rated"].outputs_cache["RatedPoint"]
    d = diameter_for_rated(fitted, rated).to("mm").magnitude
    assert 125.0 <= d <= 131.0
    assert d == pytest.approx(127.1, abs=0.2)
