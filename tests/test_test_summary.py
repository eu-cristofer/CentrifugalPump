"""API 610 test data summary (Annex M / 8th-edition Appendix T)."""

import json
import os
import zipfile
from pathlib import Path

import pytest

from pump import Q_
from pump.utilities.test_summary import vibration_by_region

PROJECT = (
    Path(__file__).resolve().parents[1]
    / "examples/user/B-34004A_MRT_reference.pumpflow"
)
LIMITS = {"overall": Q_(3.0, "mm/s"), "filtered": Q_(2.0, "mm/s")}


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


# --------------------------------------------------------------------------- #
# Library: vibration by flow region
# --------------------------------------------------------------------------- #
def _pts(rows):
    return [
        (Q_(q, "m**3/h"), {k: Q_(v, "mm/s") for k, v in d.items()}) for q, d in rows
    ]


def test_regions_rated_preferred_allowable():
    pts = _pts(
        [
            (0.0, {"vib_de": 9.9}),  # shut-off: excluded everywhere
            (5.0, {"vib_de": 2.8}),  # below the preferred region (0.7 x 10 = 7)
            (9.9, {"vib_de": 2.1}),  # rated (within 5 % of 10)
            (11.0, {"vib_de": 2.6}),  # preferred region, not rated
            (12.5, {"vib_de": 3.4}),  # above the preferred region (1.2 x 10 = 12)
        ]
    )
    (de,) = vibration_by_region(pts, Q_(10, "m**3/h"), Q_(10, "m**3/h"), LIMITS)
    assert de.rated == (2.1, 3.0)
    assert de.por == (2.6, 3.0)
    assert de.aor == (3.4, 3.9)  # allowable: +30 %


def test_filtered_uses_filtered_limit_and_missing_keys_are_skipped():
    pts = _pts([(10.0, {"vib_nde_f": 1.1})])
    lines = vibration_by_region(pts, Q_(10, "m**3/h"), Q_(10, "m**3/h"), LIMITS)
    assert [(v.location, v.measure) for v in lines] == [
        ("Non-drive-end bearing housing", "Filtered")
    ]
    assert lines[0].rated == (1.1, 2.0) and lines[0].aor == (1.1, 2.6)


def test_no_vibration_data_gives_no_lines():
    assert vibration_by_region([], Q_(10, "m**3/h"), Q_(10, "m**3/h"), LIMITS) == ()


def test_form_title_follows_edition_and_language():
    from pump.acceptance import AcceptanceCriteria
    from pump.utilities.report import LocalizationHelper
    from pumpflow.binding import form_title

    en, pt = LocalizationHelper("en")._, LocalizationHelper("pt")._
    assert form_title(AcceptanceCriteria.load("api610:8"), en).endswith(
        "(API 610 8th edition, Appendix T)"
    )
    assert form_title(AcceptanceCriteria.load("api610:12"), en).endswith(
        "(API 610 12th edition, Annex M)"
    )
    assert "8ª edição, Apêndice T" in form_title(
        AcceptanceCriteria.load("api610:8"), pt
    )


# --------------------------------------------------------------------------- #
# Workbench: B-34004A reference project
# --------------------------------------------------------------------------- #
def _summaries(qapp, project=PROJECT, lang="en"):
    from pump.utilities.report import LocalizationHelper
    from pumpflow.binding import test_data_summaries
    from pumpflow.export_cli import build_scene, report_inputs

    _app, scene = build_scene(str(project))
    rated, branches, s = report_inputs(scene)
    return test_data_summaries(rated, branches, s, LocalizationHelper(lang)._)


def test_b34004a_summary_values(qapp):
    (s,) = _summaries(qapp)
    assert s.pump_tag == "B-34004A"
    assert "Appendix T" in s.form_title
    perf = {p.name: p for p in s.performance}
    assert perf["Head"].tolerance == "±2 %"  # API 610 8th Table 4-2, > 300 m
    assert perf["Head"].deviation == pytest.approx(0.0172, abs=5e-4)
    assert perf["Power"].tolerance == "+4 %"
    assert perf["NPSH3"].rated == pytest.approx(4.06 * 0.3048)  # quoted 4.06 ft
    assert perf["NPSH3"].tested < perf["NPSH3"].rated
    assert perf["Shut-off head"].note == "extrapolated"  # no shut-off point
    assert perf["Speed"].tested == pytest.approx(10301)
    header = dict(s.header)
    assert header["Item no."] == "B-34004"  # defaults to the service TAG
    assert header["Purchase order no."] == ""  # not in the project: left blank
    # Sundyne per-point gearbox-housing readings (RMS per the vendor), OH6
    overall = [v for v in s.vibration if v.measure == "Overall"][0]
    assert overall.location == "Gearbox housing"
    assert overall.rated == (pytest.approx(3.76, abs=0.01), 3.0)
    assert s.curve_png and s.curve_png.startswith(b"\x89PNG")
    # Figure M.4 style: test points + gearbox vibration against flow
    assert s.extra["test_points_png"].startswith(b"\x89PNG")


def test_point_vibration_fills_every_region(qapp, tmp_path):
    doc = json.loads(PROJECT.read_text(encoding="utf-8"))
    node = next(n for n in doc["nodes"] if n["id"] == "test_a")
    # Synthetic test inputs (B-34004A has no per-point vibration).
    for row, v in zip(node["settings"]["rows"], (2.9, 2.2, 2.0, 2.4, 2.6, 3.6)):
        row["vib_de"] = v
    node["settings"]["columns"]["vib_de"] = "mm/s"
    project = tmp_path / "synthetic.pumpflow"
    project.write_text(json.dumps(doc), encoding="utf-8")
    (s,) = _summaries(qapp, project)
    (de,) = [v for v in s.vibration if v.location == "Drive-end bearing housing"]
    assert de.location == "Drive-end bearing housing" and de.rated[0] == pytest.approx(
        2.4
    )
    assert de.por[0] is not None and de.aor == (pytest.approx(3.6), pytest.approx(3.9))


def test_writers(qapp, tmp_path):
    from pump.utilities.report_latex import find_latex_engine
    from pumpflow.binding import export_test_summary

    sums = _summaries(qapp, lang="pt")
    fmts = ["docx", "tex", "xlsx"] + (["pdf"] if find_latex_engine() else [])
    paths, errors = export_test_summary(
        sums, fmts, language="pt", out_dir=str(tmp_path), stem="S"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Resumo dos dados de teste" in xml and "B-34004A" in xml
    tex = Path(paths["tex"]).read_text(encoding="utf-8")
    assert r"\usepackage[brazilian]{babel}" in tex and "Apêndice T" in tex
    assert (tmp_path / "S_figs" / "curve_1.png").is_file()
    openpyxl = pytest.importorskip("openpyxl")
    ws = openpyxl.load_workbook(paths["xlsx"])["B-34004A"]
    assert "Resumo dos dados de teste" in ws["A1"].value


def test_report_export_fields_stored_only_when_filled(qapp):
    from PySide6.QtWidgets import QLineEdit, QPushButton

    from pumpflow.nodes.registry import make_node

    node = make_node("report_export")
    before = dict(node.settings)
    dlg = node.create_dialog(None, lambda: None)
    assert dict(node.settings).keys() == before.keys()  # opening adds nothing
    edits = [
        e
        for e in dlg.findChildren(QLineEdit)
        if e.placeholderText() == "defaults to the service TAG"
    ]
    edits[0].setText("ITEM-7")
    assert node.settings["item_number"] == "ITEM-7"
    edits[0].setText("")
    assert "item_number" not in node.settings
    assert any(
        b.accessibleName() == "ExportSummary" for b in dlg.findChildren(QPushButton)
    )
    dlg.close()


def test_cli_summary_flag(qapp, tmp_path, capsys):
    from pump.utilities.report_latex import find_latex_engine
    from pumpflow.export_cli import main

    rc = main(
        [
            str(PROJECT),
            "--formats",
            "docx",
            "--out",
            str(tmp_path),
            "--stem",
            "R",
            "--summary",
        ]
    )
    for ext in ("docx", "tex", "xlsx"):
        assert (tmp_path / f"R_test_summary.{ext}").is_file()
    if find_latex_engine():
        assert rc == 0 and (tmp_path / "R_test_summary.pdf").is_file()
    else:  # no TeX: the PDF failure is reported and the exit code says so
        assert rc == 1
        assert "FAILED summary pdf" in capsys.readouterr().err
