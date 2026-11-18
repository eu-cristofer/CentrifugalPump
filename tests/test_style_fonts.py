"""The app stylesheet hands Qt point sizes, never pixel sizes.

A pixel-sized font has ``pointSize() == -1``; on Windows Qt's native style
copies it and warns ``QFont::setPointSize: Point size <= 0 (-1)``.
"""

import os
import re

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_qss_has_no_pixel_font_sizes(qapp):
    from pumpflow.style import app_qss

    qss = app_qss()
    assert not re.search(r"font-size:\s*[\d.]+px", qss)
    assert re.search(r"font-size:\s*[\d.]+pt", qss)


@pytest.mark.parametrize(
    "dpi, expected", [(96, "9.75pt"), (72, "13pt"), (144, "6.5pt")]
)
def test_px_to_pt_keeps_on_screen_size(dpi, expected):
    from pumpflow.style import _px_to_pt

    assert _px_to_pt("QWidget { font-size: 13px; }", dpi) == (
        f"QWidget {{ font-size: {expected}; }}"
    )


def test_styled_widgets_have_point_sized_fonts(qapp):
    from PySide6.QtCore import qInstallMessageHandler
    from PySide6.QtWidgets import QLabel

    from pumpflow.nodes import ui
    from pumpflow.style import app_qss

    warnings = []
    previous = qInstallMessageHandler(lambda _m, _c, msg: warnings.append(msg))
    old_qss = qapp.styleSheet()
    try:
        qapp.setStyleSheet(app_qss())
        dlg = ui.PropertyDialog(None, "Fonts", "subtitle", maximizable=True)
        label = QLabel("section", objectName="SectionLabel")
        dlg.add(label)
        for w in [dlg, label, *dlg.findChildren(QLabel)]:
            w.ensurePolished()
            assert w.font().pointSizeF() > 0, w.objectName()
        dlg.close()
    finally:
        qapp.setStyleSheet(old_qss)
        qInstallMessageHandler(previous)
    assert not [m for m in warnings if "setPointSize" in m]
