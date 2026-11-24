"""UI/UX review, round 2 (2026-11-18): disabled fields read as disabled, a tick
in checked checkboxes, a named report-cover label on Rated Point, a grouped
toolbox with distinct glyphs, and welcome-screen wording."""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


# --------------------------------------------------------------------------- #
# Toolbox catalogue
# --------------------------------------------------------------------------- #
def test_every_node_is_in_exactly_one_named_group(qapp):
    from pumpflow.nodes.registry import NODE_KINDS, grouped_node_kinds

    groups = grouped_node_kinds()
    names = [g for g, _ in groups]
    assert names == ["Inputs", "Corrections", "Curves & analysis", "Checks", "Output"]
    kinds = [k for _, items in groups for k, *_ in items]
    assert sorted(kinds) == sorted(k for k, *_ in NODE_KINDS)
    assert len(kinds) == len(set(kinds))


def test_node_glyphs_are_distinct_text_symbols(qapp):
    from pumpflow.nodes.registry import NODE_KINDS

    glyphs = [g for *_, g in NODE_KINDS]
    assert len(glyphs) == len(set(glyphs)), glyphs
    # no colour emoji, and none of the canvas state glyphs (✓ ! ✗)
    assert all(ord(ch) < 0x1F000 for g in glyphs for ch in g)
    assert not {"✓", "!", "✗"} & set(glyphs)


# --------------------------------------------------------------------------- #
# Stylesheet: disabled state and checkbox tick
# --------------------------------------------------------------------------- #
def test_stylesheet_has_disabled_state_and_tick(qapp):
    from pumpflow.style import app_qss, check_mark_path

    qss = app_qss()
    assert "QLineEdit:disabled" in qss and "#FieldLabel:disabled" in qss
    path = check_mark_path()
    assert path and Path(path).exists()
    assert f'image: url("{path}")' in qss
    assert "<path" in Path(path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Test Points: bench-geometry rows follow the checkbox
# --------------------------------------------------------------------------- #
def test_geometry_rows_disabled_until_applied(qapp):
    from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox

    from pumpflow.nodes.registry import make_node

    node = make_node("test_points")
    dlg = node.create_dialog(None, lambda: None)
    box = dlg.findChild(QCheckBox, "ApplyGeometry")
    spin = dlg.findChild(QDoubleSpinBox, "Geo_suction_id")
    row = spin.parentWidget()
    assert not box.isChecked()
    assert not spin.isEnabled() and not row.isEnabled()
    box.setChecked(True)
    assert spin.isEnabled() and row.isEnabled()
    box.setChecked(False)
    assert not row.isEnabled()
    dlg.close()


# --------------------------------------------------------------------------- #
# Rated Point: the free-text label says what it is
# --------------------------------------------------------------------------- #
def test_rated_point_cover_label_is_named(qapp):
    from PySide6.QtWidgets import QLabel

    from pumpflow.nodes.registry import make_node

    dlg = make_node("rated_point").create_dialog(None, lambda: None)
    texts = [lab.text() for lab in dlg.findChildren(QLabel, "FieldLabel")]
    assert "Label on report cover" in texts
    assert "Standard" not in texts
    assert texts.index("Label on report cover") == texts.index("Client overlay") + 1
    dlg.close()


# --------------------------------------------------------------------------- #
# Welcome
# --------------------------------------------------------------------------- #
def test_welcome_wording(qapp):
    from PySide6.QtWidgets import QPushButton

    from pumpflow.welcome import WelcomeDialog

    dlg = WelcomeDialog(None)
    texts = [b.text() for b in dlg.findChildren(QPushButton)]
    assert "Skip" not in texts and "Demo pipeline" in texts
    # "&" is escaped, so "Curve & Report" does not render as "Curve _Report"
    assert "Curve && Report — Clean water" in texts
    dlg.close()


def test_recent_label_shows_folder_and_date(tmp_path):
    from pumpflow.welcome import recent_label

    f = tmp_path / "job" / "b-1.pumpflow"
    f.parent.mkdir()
    f.write_text("{}", encoding="utf-8")
    name, detail = recent_label(f).splitlines()
    assert name == "b-1.pumpflow"
    assert detail.startswith("job  ·  20")
