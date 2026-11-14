"""
Report export in every format — UC-09 (Word / LaTeX / PDF).

Qt-free: builds the same ``report_data`` dict the workbench assembles, from the
shared ``curve`` / ``design_point`` fixtures, and drives the library generators
plus ``pumpflow.binding.export_reports``. The PDF test is skipped when no TeX
engine (latexmk / pdflatex) is installed.
"""

import zipfile

import pytest

from pump import Q_, PerformanceChecker
from pump.utilities.report import LocalizationHelper, _parse_po
from pump.utilities.report_latex import (
    LatexReportGenerator,
    find_latex_engine,
    latex_escape,
)
from pumpflow.binding import export_reports

TAG = "B-34004A"


@pytest.fixture
def report_data(curve, design_point):
    png = curve.plot_performance_curve(capacity=Q_(833, "m**3/h"), return_io=True)
    return {
        "equipment_description": {"TAG": "B-34004", "Manufacturer": "Sundyne & Co_1"},
        "design_point": design_point,
        "test_data": {
            TAG: {
                "test_summary": PerformanceChecker(design_point, curve).report_summary,
                "test_data": curve.test_data,
                "Performance Curve": png,
                "verdict": True,
            }
        },
    }


# --------------------------------------------------------------------------- #
# LaTeX helpers
# --------------------------------------------------------------------------- #
def test_latex_escape_specials():
    assert latex_escape("a&b%c$d#e_f{g}h") == r"a\&b\%c\$d\#e\_f\{g\}h"
    assert latex_escape("x~y^z") == r"x\textasciitilde{}y\textasciicircum{}z"
    assert latex_escape("C:\\dir") == r"C:\textbackslash{}dir"
    assert latex_escape(3.5) == "3.5"


# --------------------------------------------------------------------------- #
# Localization: works from the .po source even without a compiled .mo
# --------------------------------------------------------------------------- #
def test_portuguese_catalog_is_used():
    _ = LocalizationHelper("pt")._
    assert _("Equipment Description") == "Descrição do Equipamento"
    assert _("Performance Curve") == "Curva de Performance"
    assert _("not in catalog") == "not in catalog"


def test_parse_po_multiline(tmp_path):
    po = tmp_path / "messages.po"
    po.write_text(
        'msgid ""\nmsgstr ""\n"Language: pt\\n"\n\n'
        'msgid "a"\n"b"\nmsgstr "x"\n"y\\n"\n\nmsgid "empty"\nmsgstr ""\n',
        encoding="utf-8",
    )
    assert _parse_po(po) == {"ab": "xy\n"}


# --------------------------------------------------------------------------- #
# .tex
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "lang, heading, verdict",
    [
        ("en", "Equipment Description", "APPROVED"),
        ("pt", "Descrição do Equipamento", "APROVADO"),
    ],
)
def test_generate_tex(tmp_path, report_data, lang, heading, verdict):
    out = LatexReportGenerator(language=lang).generate_tex(
        report_data, str(tmp_path / "rep.tex")
    )
    tex = open(out, encoding="utf-8").read()
    assert r"\begin{document}" in tex and tex.rstrip().endswith(r"\end{document}")
    assert heading in tex and verdict in tex
    assert TAG in tex
    assert r"Sundyne \& Co\_1" in tex  # user text is escaped
    assert tex.count(r"\begin{tabular}") == 2  # summary + test data
    figs = list((tmp_path / "rep_figs").glob("*.png"))
    assert len(figs) == 1 and figs[0].stat().st_size > 1000
    assert f"rep_figs/{figs[0].name}" in tex
    babel = "brazilian" if lang == "pt" else "english"
    assert rf"\usepackage[{babel}]{{babel}}" in tex


@pytest.mark.skipif(find_latex_engine() is None, reason="no TeX engine installed")
def test_generate_pdf(tmp_path, report_data):
    out = LatexReportGenerator("pt").generate_pdf(
        report_data, str(tmp_path / "rep.pdf")
    )
    data = open(out, "rb").read()
    assert data.startswith(b"%PDF") and len(data) > 20_000


def test_generate_pdf_without_engine_raises(tmp_path, report_data, monkeypatch):
    import pump.utilities.report_latex as rl

    monkeypatch.setattr(rl, "find_latex_engine", lambda: None)
    with pytest.raises(RuntimeError, match="No LaTeX engine"):
        rl.LatexReportGenerator().generate_pdf(report_data, str(tmp_path / "x.pdf"))


# --------------------------------------------------------------------------- #
# export_reports: one entry point for GUI + CLI
# --------------------------------------------------------------------------- #
def test_export_reports_docx_and_tex(tmp_path, report_data):
    paths, errors = export_reports(
        report_data, ["docx", "tex"], language="en", out_dir=str(tmp_path), stem="R"
    )
    assert errors == {}
    assert set(paths) == {"docx", "tex"}
    with zipfile.ZipFile(paths["docx"]) as z:  # valid docx with the plot embedded
        assert any(n.startswith("word/media/") for n in z.namelist())
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Overall verdict: APPROVED" in xml and TAG in xml


def test_export_reports_collects_failures(tmp_path, report_data, monkeypatch):
    import pump.utilities.report_latex as rl

    monkeypatch.setattr(rl, "find_latex_engine", lambda: None)
    paths, errors = export_reports(
        report_data, ["pdf", "tex", "bogus"], out_dir=str(tmp_path), stem="R"
    )
    assert set(paths) == {"tex"}  # the failing formats did not stop .tex
    assert "No LaTeX engine" in errors["pdf"] and "bogus" in errors


def test_export_reports_default_stem_is_localized(tmp_path, report_data):
    paths, _ = export_reports(
        report_data, ["tex"], language="pt", out_dir=str(tmp_path)
    )
    assert "Relatório_B-34004_" in paths["tex"]


# --------------------------------------------------------------------------- #
# Mechanical running test section (UC-11)
# --------------------------------------------------------------------------- #
def _mechanical_run_entry():
    from pump import (
        Channel,
        MechanicalRunChecker,
        MechanicalRunCriteria,
        MechanicalRunLog,
        RunReading,
        plot_mechanical_run,
    )

    times = ["00:00", "01:00", "02:00", "03:00", "04:00"]
    log = MechanicalRunLog(
        (Channel("Vib filtered", "vibration_filtered"),),
        tuple(RunReading(t, {"Vib filtered": Q_(1.0, "mm/s")}) for t in times),
    )
    crit = MechanicalRunCriteria(
        min_duration=Q_(4, "h"),
        role_max={"vibration_filtered": Q_(2.0, "mm/s")},
        source="unit test source",
    )
    return {
        "result": MechanicalRunChecker(log, crit).check(),
        "plot": plot_mechanical_run(log, crit),
    }


def _mr_only_data(report_data):
    return {
        "equipment_description": report_data["equipment_description"],
        "design_point": report_data["design_point"],
        "test_data": {TAG: {"Mechanical Run": _mechanical_run_entry()}},
    }


def test_tex_mechanical_run_section(tmp_path, report_data):
    report_data["test_data"][TAG]["Mechanical Run"] = _mechanical_run_entry()
    out = LatexReportGenerator().generate_tex(report_data, str(tmp_path / "mr.tex"))
    tex = open(out, encoding="utf-8").read()
    assert "Mechanical running test" in tex
    assert "PASSED" in tex and "unit test source" in tex
    assert tex.count(r"\begin{tabular}") == 3  # summary + data + mechanical run
    assert len(list((tmp_path / "mr_figs").glob("*.png"))) == 2


def test_tex_mechanical_run_only_entry_and_pt(tmp_path, report_data):
    out = LatexReportGenerator("pt").generate_tex(
        _mr_only_data(report_data), str(tmp_path / "mr.tex")
    )
    tex = open(out, encoding="utf-8").read()
    assert "Teste de funcionamento mecânico" in tex and "APROVADO" in tex
    assert len(list((tmp_path / "mr_figs").glob("*.png"))) == 1


def test_docx_mechanical_run_section(tmp_path, report_data):
    report_data["test_data"][TAG]["Mechanical Run"] = _mechanical_run_entry()
    paths, errors = export_reports(
        report_data, ["docx"], language="en", out_dir=str(tmp_path), stem="R"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Mechanical running test" in xml and "PASSED" in xml


def test_docx_mechanical_run_only_entry(tmp_path, report_data):
    paths, errors = export_reports(
        _mr_only_data(report_data), ["docx"], language="en", out_dir=str(tmp_path), stem="R"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Mechanical running test" in xml and TAG in xml
