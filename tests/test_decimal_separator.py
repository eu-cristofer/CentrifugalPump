"""Decimal separator: the app preference for what the workbench shows, the
report language for what a report prints (UI_SPEC §5.2)."""

from __future__ import annotations

import base64
import io
import json
import os
import re
import zipfile
from pathlib import Path

import pytest

from pump import Q_
from pump.utilities.numbers import (
    decimal,
    decimal_for_language,
    localize_axes,
    nformat,
    num,
    qty,
    separator,
    set_decimal,
)

ROOT = Path(__file__).resolve().parents[1]
P9001 = ROOT / "examples" / "user" / "P-9001A_MRT_reference.pumpflow"


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _point_default():
    set_decimal(".")
    yield
    set_decimal(".")


def test_app_default_and_report_override_nest():
    set_decimal(",")
    assert num(9.8) == "9,80"
    with decimal(decimal_for_language("en")):
        assert separator() == "."
        assert num(9.8) == "9.80"
        with decimal(decimal_for_language("pt")):
            assert qty(Q_(333.8, "m"), "0.1f~P") == "333,8 m"
        assert num(9.8) == "9.80"
    assert num(9.8) == "9,80"


def test_nformat_leaves_text_and_unformatted_fields():
    with decimal(","):
        text = nformat("{c} · {n} pts · {v:.2f} mm/s", c="8.3.4.2", n=6, v=2.7)
    assert text == "8.3.4.2 · 6 pts · 2,70 mm/s"


def test_no_thousands_grouping():
    with decimal(","):
        assert num(1234567.891, "0.2f") == "1234567,89"
    assert num(1234567.891, "0.2f") == "1234567.89"


def test_localize_axes_ticks_follow_the_separator():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([0.5, 1.5, 2.5], [0.25, 0.75, 1.25])
    with decimal(","):
        localize_axes(fig)
        fig.canvas.draw()
        labels = [t.get_text() for t in ax.get_yticklabels() if t.get_text()]
    plt.close(fig)
    assert any("," in lab for lab in labels), labels
    assert not any("." in lab for lab in labels), labels


def _docx_text(raw: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return re.sub(r"<[^>]+>", " ", xml)


@pytest.mark.parametrize("app_sep", [".", ","])
def test_reports_follow_their_language_not_the_app(app_sep):
    from pumpflow import webapi

    set_decimal(app_sep)
    doc = json.loads(P9001.read_text(encoding="utf-8"))
    pt = webapi.export_report(doc, "html", "pt")
    en = webapi.export_report(doc, "html", "en")
    pt_html = base64.b64decode(pt["base64"]).decode("utf-8")
    en_html = base64.b64decode(en["base64"]).decode("utf-8")
    # the rated capacity cell of the design-point table (the project's own
    # note quotes "9.80 m³/h" as typed, so only the computed cells are checked)
    assert "<td>9,80 m³/h</td>" in pt_html and "<td>9.80 m³/h</td>" not in pt_html
    assert "<td>9.80 m³/h</td>" in en_html and "9,80 m³/h" not in en_html
    pt_docx = _docx_text(
        base64.b64decode(webapi.export_report(doc, "docx", "pt")["base64"])
    )
    assert "9,80 m³/h" in pt_docx
    assert separator() == app_sep  # the export restored the app default


def test_webapi_evaluate_uses_the_viewer_separator():
    from pumpflow import webapi

    doc = json.loads(P9001.read_text(encoding="utf-8"))
    point = webapi.evaluate(doc)["nodes"]
    comma = webapi.evaluate(doc, ",")["nodes"]
    rated = next(k for k, n in point.items() if n["kind"] == "rated_point")
    assert "9.8 m³/h" in point[rated]["status"]
    assert "9,8 m³/h" in comma[rated]["status"]
    assert separator() == "."


def test_desktop_number_box_shows_the_preference_and_accepts_both(qapp):
    from pumpflow.nodes import ui

    try:
        ui.apply_decimal_preference(",")
        sb = ui.spin(9.8, 0, 100, decimals=2)
        assert sb.text() == "9,80"
        assert sb.valueFromText("9.5") == pytest.approx(9.5)
        assert sb.valueFromText("9,25") == pytest.approx(9.25)
        ui.apply_decimal_preference(".")
        sb = ui.spin(1234.5, 0, 1e6, decimals=1)
        assert sb.text() == "1234.5"
        assert sb.valueFromText("7,5") == pytest.approx(7.5)
    finally:
        ui.apply_decimal_preference(".")
