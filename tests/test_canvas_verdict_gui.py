"""
Qt (offscreen): the canvas verdict pill and first-open dialog sizing
(UI/UX review, 2026-11-17).

- Judging nodes set ``badge`` (APPROVED / REJECTED / NOT FULLY ASSESSED,
  PASSED / FAILED) and ``badge_notes`` (OVERRIDDEN, PROVISIONAL); the canvas
  paints them, and a zoomed-out canvas paints the verdict instead of text.
- The Compliance node's tolerance editors sit in a collapsed "Override
  acceptance criteria" section, opened automatically when an override exists.
- A node window opened for the first time is wide enough for its content and
  its table headers.
"""

import os
from pathlib import Path

import pytest

PROJECT = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "user"
    / "B-34004A_MRT_reference.pumpflow"
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture
def scene(qapp):
    if not PROJECT.is_file():
        pytest.skip(f"missing reference project: {PROJECT}")
    from pumpflow.canvas.scene import GraphScene
    from pumpflow.nodes.registry import make_node
    from pumpflow.persistence import read_json

    sc = GraphScene(make_node)
    sc.load_dict(read_json(PROJECT))
    yield sc
    sc.dispose()


@pytest.fixture
def no_saved_geometry(monkeypatch, tmp_path):
    from PySide6.QtCore import QSettings

    from pumpflow.nodes import ui

    path = str(tmp_path / "settings.ini")
    monkeypatch.setattr(
        ui, "window_settings", lambda: QSettings(path, QSettings.IniFormat)
    )


def _logic(scene, kind, state="ok"):
    return next(
        n.logic for n in scene.nodes if n.logic.kind == kind and n.logic.state == state
    )


def test_judging_nodes_carry_a_badge(scene):
    assert _logic(scene, "compliance").badge == ("APPROVED", "ok")
    assert _logic(scene, "report_export").badge == ("APPROVED", "ok")
    mrt = _logic(scene, "mechanical_run_check", "reject")
    assert mrt.badge == ("FAILED", "fail")
    assert "PROVISIONAL" in mrt.badge_notes  # MRT limits are not verified
    # nodes that judge nothing carry none
    assert _logic(scene, "curve_fit").badge is None


def test_override_adds_badge_note_and_clears_on_reset(scene):
    node = _logic(scene, "compliance")
    node.settings["tolerances"] = {"head": 0.10}
    scene.evaluate()
    assert "OVERRIDDEN" in node.badge_notes
    node.settings["tolerances"] = {}
    scene.evaluate()
    assert node.badge_notes == ()


def test_badge_cleared_when_node_loses_input(scene):
    node = _logic(scene, "compliance")
    node.badge = ("APPROVED", "ok")
    node.run({})  # no inputs: waiting
    assert node.badge is None and node.badge_notes == ()


@pytest.mark.parametrize("scale", [1.0, 0.4])
def test_canvas_paints_at_detail_and_overview_zoom(scene, scale):
    from PySide6.QtGui import QImage, QPainter

    from pumpflow.canvas.view import GraphView

    view = GraphView(scene)
    view.resize(800, 600)
    view.scale(scale, scale)
    img = QImage(800, 600, QImage.Format_ARGB32)
    painter = QPainter(img)
    view.render(painter)  # exercises NodeItem.paint at this level of detail
    painter.end()
    view.deleteLater()


def test_status_beside_pill_drops_the_repeated_verdict():
    from pumpflow.canvas.node_item import _status_beside

    badge = ("APPROVED", "ok")
    assert _status_beside("B-1A · APPROVED ✓ (provisional)", badge) == "B-1A"
    assert _status_beside("1 pump · APPROVED ✓", badge) == "1 pump"
    assert _status_beside("B-1A · x", None) == "B-1A · x"


def test_override_section_is_collapsed_unless_overridden(scene, no_saved_geometry):
    from PySide6.QtWidgets import QToolButton

    node = _logic(scene, "compliance")
    node.settings["tolerances"] = {}
    scene.evaluate()
    dlg = node.create_dialog(None, lambda: None)
    toggle = dlg.findChild(QToolButton, "SectionToggle")
    assert toggle is not None and not toggle.isChecked()
    dlg.deleteLater()

    node.settings["tolerances"] = {"head": 0.10}
    scene.evaluate()
    dlg = node.create_dialog(None, lambda: None)
    assert dlg.findChild(QToolButton, "SectionToggle").isChecked()
    dlg.deleteLater()
    node.settings["tolerances"] = {}
    scene.evaluate()


def test_first_open_fits_table_headers(scene, no_saved_geometry):
    from PySide6.QtWidgets import QTableWidget

    node = _logic(scene, "compliance")
    dlg = node.create_dialog(None, lambda: None)
    dlg.remember_as("compliance-test")
    dlg.show()
    table = dlg.body.findChild(QTableWidget)
    fm = table.horizontalHeader().fontMetrics()
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    assert table.minimumWidth() >= sum(fm.horizontalAdvance(h) for h in headers)
    # as wide as the content, but never wider than 90 % of the screen
    cap = int(dlg.screen().availableGeometry().width() * 0.9)
    assert dlg.width() >= min(table.minimumWidth(), cap)
    dlg.close()
    dlg.deleteLater()
