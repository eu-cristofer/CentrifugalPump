"""Qt (offscreen) tests for the 2026-11-16 UI fixes.

- Rated Point: the (i) help button on the impeller-diameter section.
- Correction / Trim: display-unit choice for the before/after table (on screen only).
- Performance Plot: the plot sits to the right of its parameters.
- Report Export: the "Include signature block" switch.
"""

import os

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


PAIR = {
    "measured": {"q": 10.0, "head": 300.0, "power": 25.0, "eff": 32.0},
    "corrected": {"q": 9.9, "head": 294.0, "power": None, "eff": None},
}


def _cells(table, row):
    return [table.item(row, c).text() for c in range(table.columnCount())]


def _headers(table):
    return [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]


def test_before_after_table_converts_display_only(qapp):
    from pumpflow.nodes import ui

    settings = {}
    grid = ui.BeforeAfterTable(settings)
    for dim in ("capacity", "head", "power"):
        grid.combos[dim].setCurrentIndex(grid.combos[dim].findData(
            {"capacity": "m³/h", "head": "m", "power": "kW"}[dim]))
    grid.fill([PAIR], ("measured", "corrected"))
    assert _cells(grid.table, 0)[:4] == ["10.00", "300.00", "25.00", "32.0"]
    assert _cells(grid.table, 1)[2:] == ["—", "—", "corrected"]

    grid.combos["capacity"].setCurrentIndex(grid.combos["capacity"].findData("US GPM"))
    grid.combos["head"].setCurrentIndex(grid.combos["head"].findData("ft"))
    grid.combos["power"].setCurrentIndex(grid.combos["power"].findData("hp"))
    q, h, p = (float(x.replace(",", "")) for x in _cells(grid.table, 0)[:3])
    assert q == pytest.approx(44.03, rel=1e-3)  # 10 m³/h in US gpm
    assert h == pytest.approx(984.25, rel=1e-3)  # 300 m in ft
    assert p == pytest.approx(33.53, rel=1e-3)  # 25 kW in hp
    assert _headers(grid.table)[:3] == ["Q [US GPM]", "Head [ft]", "Power [hp]"]
    # The source rows are untouched; the choice is remembered in the settings.
    assert PAIR["measured"]["q"] == 10.0
    assert settings["table_units"] == {"capacity": "US GPM", "head": "ft", "power": "hp"}
    reopened = ui.BeforeAfterTable(settings)
    assert reopened.units == settings["table_units"]


@pytest.mark.parametrize("kind", ["correction", "trim"])
def test_before_after_dialogs_have_unit_strip(qapp, kind):
    from pumpflow.nodes import ui
    from pumpflow.nodes.registry import make_node

    node = make_node(kind)
    dlg = node.create_dialog(None, lambda: None)
    combos = [w for w in dlg.findChildren(type(ui.combo([], None)))]
    labels = {c.itemText(i) for c in combos for i in range(c.count())}
    assert {"US GPM", "ft", "hp"} <= labels
    dlg.close()


def test_rated_point_impeller_info_button(qapp):
    from PySide6.QtWidgets import QToolButton

    from pumpflow.nodes.registry import make_node

    node = make_node("rated_point")
    dlg = node.create_dialog(None, lambda: None)
    buttons = [b for b in dlg.findChildren(QToolButton) if b.objectName() == "InfoButton"]
    assert len(buttons) == 1
    buttons[0].click()
    text = buttons[0]._box.text()
    for needle in ("Nominal D", "Maximum D", "Minimum D", "not set", "Impeller Trim"):
        assert needle in text
    buttons[0]._box.close()
    dlg.close()


def test_performance_plot_parameters_left_of_plot(qapp):
    from PySide6.QtWidgets import QHBoxLayout, QWidget

    from pumpflow.nodes.registry import make_node

    node = make_node("performance_plot")
    dlg = node.create_dialog(None, lambda: None)
    panel = dlg.findChild(QWidget, "PlotSettings")
    assert panel is not None
    row = panel.parentWidget().layout()
    assert isinstance(row, QHBoxLayout) and row.count() == 2
    # Left: the parameters (fixed width); right: the plot, taking the extra space.
    assert row.itemAt(0).widget() is panel
    assert row.stretch(0) == 0 and row.stretch(1) == 1
    assert dlg.minimumWidth() >= 900
    dlg.close()


def test_report_export_signature_switch(qapp):
    from PySide6.QtWidgets import QCheckBox, QTableWidget

    from pumpflow.nodes.registry import make_node

    node = make_node("report_export")
    # Absent means "on", so projects saved before the switch keep their signatures.
    assert "include_signatures" not in node.settings

    dlg = node.create_dialog(None, lambda: None)
    box = [c for c in dlg.findChildren(QCheckBox) if "signature" in c.text().lower()][0]
    signers = [t for t in dlg.findChildren(QTableWidget)
               if t.horizontalHeaderItem(0).text() == "Role"][0]
    box.setChecked(False)
    assert node.settings["include_signatures"] is False
    assert not signers.isEnabled()
    box.setChecked(True)
    assert "include_signatures" not in node.settings and signers.isEnabled()
    dlg.close()
