"""Node windows: maximise from the title bar, a header Maximize / Restore
button on chart and table windows, and size remembered per node type."""

import os

import pytest

CHART_KINDS = (
    "performance_plot",
    "test_points",
    "mechanical_run",
    "npsh",
    "curve_fit",
    "explore_plot",
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """Point the window memory at a throw-away INI file."""
    from PySide6.QtCore import QSettings

    from pumpflow.nodes import ui

    path = str(tmp_path / "windows.ini")
    monkeypatch.setattr(
        ui, "window_settings", lambda: QSettings(path, QSettings.IniFormat)
    )
    return path


def test_every_node_window_has_min_max_buttons(qapp):
    from PySide6.QtCore import Qt

    from pumpflow.nodes.registry import NODE_KINDS, make_node

    for kind, _title, _glyph in NODE_KINDS:
        dlg = make_node(kind).create_dialog(None, lambda: None)
        if dlg is None:
            continue
        flags = dlg.windowFlags()
        assert flags & Qt.WindowMaximizeButtonHint, kind
        assert flags & Qt.WindowMinimizeButtonHint, kind
        dlg.close()


@pytest.mark.parametrize("kind", CHART_KINDS)
def test_chart_windows_have_header_button(qapp, kind):
    from pumpflow.nodes.registry import make_node

    dlg = make_node(kind).create_dialog(None, lambda: None)
    assert dlg.max_button is not None
    assert "Maximize" in dlg.max_button.text()
    dlg.close()


def test_short_forms_have_no_header_button(qapp):
    from pumpflow.nodes.registry import make_node

    for kind in ("fluid", "rated_point"):
        dlg = make_node(kind).create_dialog(None, lambda: None)
        assert dlg.max_button is None
        dlg.close()


def test_button_and_double_click_toggle(qapp):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    from pumpflow.nodes.registry import make_node

    dlg = make_node("performance_plot").create_dialog(None, lambda: None)
    dlg.show()
    dlg.max_button.click()
    assert dlg.windowState() & Qt.WindowMaximized
    assert "Restore" in dlg.max_button.text()
    ev = QMouseEvent(
        QEvent.MouseButtonDblClick,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    dlg.eventFilter(dlg._header, ev)
    assert not dlg.windowState() & Qt.WindowMaximized
    assert "Maximize" in dlg.max_button.text()
    dlg.close()


def test_size_and_maximised_state_remembered(qapp, isolated_settings):
    from PySide6.QtCore import Qt

    from pumpflow.nodes.registry import make_node

    dlg = make_node("npsh").create_dialog(None, lambda: None)
    dlg.remember_as("npsh")
    dlg.show()
    dlg.resize(701, 503)  # inside the offscreen screen (restore clamps to it)
    dlg.close()  # hidden -> saved

    again = make_node("npsh").create_dialog(None, lambda: None)
    again.remember_as("npsh")
    assert (again.width(), again.height()) == (701, 503)
    again.show()
    again.toggle_maximized()
    again.close()

    third = make_node("npsh").create_dialog(None, lambda: None)
    third.remember_as("npsh")
    third.show()
    assert third.windowState() & Qt.WindowMaximized
    assert "Restore" in third.max_button.text()
    third.close()
    # nothing is written to the project: the node settings are untouched
    assert "geometry" not in str(make_node("npsh").settings)
