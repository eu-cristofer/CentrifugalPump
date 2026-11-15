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


# --------------------------------------------------------------------------- #
# Pump comparison section (UC-08)
# --------------------------------------------------------------------------- #
TAG_B = "B-34004B"


def _scaled_curve(water, head_scale):
    from pump import PerformanceCurve, TestPoint

    rows = [(0, 117, 180), (300, 110, 210), (600, 95, 240), (833, 73, 252), (1000, 55, 260)]
    points = [
        TestPoint(
            fluid=water,
            capacity=Q_(q, "m**3/h"),
            speed_of_rotation=Q_(1750, "rpm"),
            _head=Q_(h * head_scale, "m"),
            breaking_power=Q_(p, "kW"),
        )
        for q, h, p in rows
    ]
    return PerformanceCurve(water, points, polynomial_degree=3)


@pytest.fixture
def two_pump_data(report_data, curve, water, design_point):
    from pump import compare_curves, plot_comparison

    curve_b = _scaled_curve(water, 1.05)
    at = [Q_(833, "m**3/h")]
    report_data["test_data"][TAG_B] = {
        "test_summary": PerformanceChecker(design_point, curve_b).report_summary,
        "test_data": curve_b.test_data,
        "Performance Curve": curve_b.plot_performance_curve(
            capacity=at[0], return_io=True
        ),
        "verdict": True,
    }
    curves = {TAG: curve, TAG_B: curve_b}
    report_data["comparison"] = {
        "table": compare_curves(curves, at),
        "plot": plot_comparison(curves, rated_q=at[0]),
        "at": at,
    }
    return report_data


def test_tex_comparison_section(tmp_path, two_pump_data):
    out = LatexReportGenerator().generate_tex(two_pump_data, str(tmp_path / "cmp.tex"))
    tex = open(out, encoding="utf-8").read()
    assert "Comparison" in tex and "Reference" in tex
    assert TAG in tex and TAG_B in tex
    assert tex.index("Comparison") > tex.index(TAG_B)  # after the per-tag sections


def test_tex_comparison_section_pt(tmp_path, two_pump_data):
    out = LatexReportGenerator("pt").generate_tex(
        two_pump_data, str(tmp_path / "cmp.tex")
    )
    tex = open(out, encoding="utf-8").read()
    assert "Comparação" in tex and "Referência" in tex


def test_docx_comparison_section(tmp_path, two_pump_data):
    paths, errors = export_reports(
        two_pump_data, ["docx"], language="en", out_dir=str(tmp_path), stem="R"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Comparison" in xml and TAG in xml and TAG_B in xml


def test_no_comparison_heading_without_comparison(tmp_path, report_data):
    out = LatexReportGenerator().generate_tex(report_data, str(tmp_path / "n.tex"))
    assert "Comparison" not in open(out, encoding="utf-8").read()
    paths, errors = export_reports(
        report_data, ["docx"], language="en", out_dir=str(tmp_path), stem="N"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "Comparison" not in xml


# --------------------------------------------------------------------------- #
# NPSH section (UC-05)
# --------------------------------------------------------------------------- #
def _npsh_entry(criteria=None):
    from pump.npsh import NPSHCriteria, NPSHrCurve, check_npsh, plot_npsh

    points = [(15.2, 2.7), (29.4, 2.9), (34.8, 3.3), (43.5, 4.1), (47.9, 3.3)]
    q = tuple(Q_(a, "gallon/minute") for a, _ in points)
    r = tuple(Q_(b, "ft") for _, b in points)
    curve = NPSHrCurve(q, r)
    rated = Q_(43.1, "gallon/minute")
    npsha = Q_(2.4, "m")
    result = check_npsh(npsha, curve.at_rated(rated), criteria or NPSHCriteria())
    return {
        "result": result,
        "plot": plot_npsh(curve, npsha, rated),
        "table": list(zip(q, r)),
    }


def _npsh_only_data(report_data):
    return {
        "equipment_description": report_data["equipment_description"],
        "design_point": report_data["design_point"],
        "test_data": {TAG: {"NPSH": _npsh_entry()}},
    }


def test_tex_npsh_section_not_configured(tmp_path, report_data):
    report_data["test_data"][TAG]["NPSH"] = _npsh_entry()
    out = LatexReportGenerator().generate_tex(report_data, str(tmp_path / "np.tex"))
    tex = open(out, encoding="utf-8").read()
    assert "NPSH available" in tex and "NPSH required" in tex
    assert "Ratio" in tex and "Margin" in tex
    assert "not configured" in tex
    assert "PASSED (unverified" not in tex and "FAILED (unverified" not in tex
    assert tex.count(r"\begin{tabular}") == 4  # summary + data + NPSH + NPSH points
    assert len(list((tmp_path / "np_figs").glob("*.png"))) == 2


def test_tex_npsh_section_unverified_verdict(tmp_path, report_data):
    from pump.npsh import NPSHCriteria

    report_data["test_data"][TAG]["NPSH"] = _npsh_entry(NPSHCriteria(min_ratio=3.0))
    out = LatexReportGenerator().generate_tex(report_data, str(tmp_path / "np.tex"))
    tex = open(out, encoding="utf-8").read()
    assert "FAILED (unverified criteria)" in tex
    assert "not configured" not in tex


def test_tex_npsh_only_entry_and_pt(tmp_path, report_data):
    out = LatexReportGenerator("pt").generate_tex(
        _npsh_only_data(report_data), str(tmp_path / "np.tex")
    )
    tex = open(out, encoding="utf-8").read()
    assert "NPSH disponível" in tex and "NPSH requerido" in tex
    assert "Margem" in tex and "não configurado" in tex
    assert len(list((tmp_path / "np_figs").glob("*.png"))) == 1


def test_docx_npsh_section(tmp_path, report_data):
    report_data["test_data"][TAG]["NPSH"] = _npsh_entry()
    paths, errors = export_reports(
        report_data, ["docx"], language="en", out_dir=str(tmp_path), stem="R"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "NPSH" in xml and "NPSH required" in xml and "not configured" in xml


def test_docx_npsh_only_entry(tmp_path, report_data):
    paths, errors = export_reports(
        _npsh_only_data(report_data), ["docx"], language="en", out_dir=str(tmp_path), stem="R"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "NPSH available" in xml and TAG in xml


def test_no_npsh_heading_without_npsh(tmp_path, report_data):
    out = LatexReportGenerator().generate_tex(report_data, str(tmp_path / "n.tex"))
    assert "NPSH required" not in open(out, encoding="utf-8").read()


# --------------------------------------------------------------------------- #
# Sprint 14: HTML export, cover page, deviations, signature block
# --------------------------------------------------------------------------- #
COVER = {
    "project": "Pump Station 7",
    "client": "ACME Oil",
    "location": "Sao Paulo",
    "test_date": "2026-11-15",
    "revision": "R2",
    "standard": "API 610 12th ed.",
    "signatories": [
        {"role": "Vendor", "name": "Ada Vendor"},
        {"role": "Inspector", "name": "Ian Inspector"},
        {"role": "Client witness", "name": "Cleo Client"},
    ],
}
OPEN_POINT = "Re-test vibration at site.\n\nCheck seal flush plan."


def _with_cover(data):
    data = dict(data)
    data["cover"] = dict(COVER)
    data["open_points"] = [OPEN_POINT]
    return data


def _render_all(tmp_path, data, language="en"):
    """``{"docx": xml, "tex": source, "html": source}`` of one export run."""
    paths, errors = export_reports(
        data, ["docx", "tex", "html"], language=language, out_dir=str(tmp_path), stem="S"
    )
    assert errors == {}
    with zipfile.ZipFile(paths["docx"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return {
        "docx": xml,
        "tex": open(paths["tex"], encoding="utf-8").read(),
        "html": open(paths["html"], encoding="utf-8").read(),
    }


def test_report_formats_include_html():
    from pumpflow.binding import REPORT_FORMATS

    assert REPORT_FORMATS == ("docx", "tex", "pdf", "html")


def test_html_export_is_one_self_contained_file(tmp_path, report_data):
    paths, errors = export_reports(
        report_data, ["html"], language="en", out_dir=str(tmp_path), stem="R"
    )
    assert errors == {}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["R.html"]  # no _figs folder
    html = open(paths["html"], encoding="utf-8").read()
    assert html.startswith("<!DOCTYPE html>") and html.rstrip().endswith("</html>")
    assert "data:image/png;base64," in html
    assert html.count("<img ") == 1 and 'src="data:image/png;base64,' in html
    assert "<style>" in html and 'rel="stylesheet"' not in html
    for text in ("Equipment Description", f"Test Data - {TAG}", "Performance test summary."):
        assert text in html
    assert "Overall verdict" in html and "APPROVED" in html


def test_html_escapes_user_strings(tmp_path, report_data):
    report_data["equipment_description"]["Manufacturer"] = "Sundyne <b>&</b> Co"
    paths, _ = export_reports(
        report_data, ["html"], out_dir=str(tmp_path), stem="E"
    )
    html = open(paths["html"], encoding="utf-8").read()
    assert "Sundyne &lt;b&gt;&amp;&lt;/b&gt; Co" in html
    assert "<b>&</b>" not in html


def test_html_pt_translation(tmp_path, report_data):
    paths, _ = export_reports(
        report_data, ["html"], language="pt", out_dir=str(tmp_path), stem="P"
    )
    html = open(paths["html"], encoding="utf-8").read()
    assert '<html lang="pt-BR">' in html
    assert "Descrição do Equipamento" in html and "APROVADO" in html


def test_every_section_heading_in_all_formats(tmp_path, two_pump_data):
    two_pump_data["test_data"][TAG]["Mechanical Run"] = _mechanical_run_entry()
    two_pump_data["test_data"][TAG]["NPSH"] = _npsh_entry()
    rendered = _render_all(tmp_path, _with_cover(two_pump_data))
    headings = [
        "Equipment Description",
        "Design Point data:",
        f"Test Data - {TAG}",
        f"Test Data - {TAG_B}",
        "Performance test summary.",
        "Mechanical running test",
        "NPSH",
        "Comparison",
        "Deviations and open points",
        "Signatures",
    ]
    for fmt, text in rendered.items():
        for heading in headings:
            assert heading in text, f"{heading!r} missing from {fmt}"


@pytest.mark.parametrize("language", ["en", "pt"])
def test_cover_fields_rendered(tmp_path, report_data, language):
    rendered = _render_all(tmp_path, _with_cover(report_data), language)
    for fmt, text in rendered.items():
        for value in ("Pump Station 7", "ACME Oil", "Sao Paulo", "2026-11-15", "R2"):
            assert value in text, f"{value!r} missing from {fmt}"
        assert "API 610 12th ed." in text and "B-34004" in text
    labels = LocalizationHelper(language)._
    for fmt, text in rendered.items():
        for msgid in ("Project", "Client", "Location", "Test date", "Revision"):
            assert labels(msgid) in text, f"{msgid!r} label missing from {fmt}"


def test_cover_standard_falls_back_to_acceptance_label(tmp_path, report_data):
    data = _with_cover(report_data)
    data["cover"]["standard"] = ""
    data["acceptance"] = {"label": "API 610 11th ed.", "verified": True, "unverified": []}
    rendered = _render_all(tmp_path, data)
    for fmt, text in rendered.items():
        assert "API 610 11th ed." in text, fmt


def test_signature_block_present_with_cover(tmp_path, report_data):
    rendered = _render_all(tmp_path, _with_cover(report_data))
    for fmt, text in rendered.items():
        for value in ("Signatures", "Role", "Name", "Signature", "Date",
                      "Vendor", "Ada Vendor", "Inspector", "Ian Inspector",
                      "Client witness", "Cleo Client"):
            assert value in text, f"{value!r} missing from {fmt}"


def test_signature_block_default_roles_without_signatories(tmp_path, report_data):
    data = _with_cover(report_data)
    del data["cover"]["signatories"]
    rendered = _render_all(tmp_path, data)
    for fmt, text in rendered.items():
        assert "Signatures" in text and "Client witness" in text, fmt


def test_no_cover_means_no_signatures_or_deviations(tmp_path, report_data):
    rendered = _render_all(tmp_path, report_data)
    for fmt, text in rendered.items():
        assert "Signatures" not in text, fmt
        assert "Deviations and open points" not in text, fmt
        assert "Pump Station 7" not in text, fmt


def test_open_points_rendered(tmp_path, report_data):
    rendered = _render_all(tmp_path, _with_cover(report_data))
    for fmt, text in rendered.items():
        assert "Re-test vibration at site." in text, fmt
        assert "Check seal flush plan." in text, fmt


def test_deviations_carry_unverified_sentence(tmp_path, report_data):
    data = _with_cover(report_data)
    data["acceptance"] = {
        "label": "API 610 12th ed.",
        "verified": False,
        "unverified": ["head tolerance"],
    }
    rendered = _render_all(tmp_path, data)
    for fmt, text in rendered.items():
        assert text.count("not yet verified against the standard text: head tolerance") >= 2, fmt


def test_open_points_without_cover_add_deviations_only(tmp_path, report_data):
    report_data["open_points"] = ["Seal leak to be re-checked."]
    rendered = _render_all(tmp_path, report_data)
    for fmt, text in rendered.items():
        assert "Deviations and open points" in text, fmt
        assert "Seal leak to be re-checked." in text, fmt
        assert "Signatures" not in text, fmt


def test_new_headings_translated_to_portuguese():
    _ = LocalizationHelper("pt")._
    assert _("Signatures") == "Assinaturas"
    assert _("Deviations and open points") == "Desvios e pendências"
    assert _("Project") == "Projeto"
    assert _("Client") == "Cliente"
    assert _("Location") == "Local"
    assert _("Test date") == "Data do teste"
    assert _("Revision") == "Revisão"
    assert _("Role") == "Função"
    assert _("Name") == "Nome"
    assert _("Signature") == "Assinatura"
    assert _("Date") == "Data"
    assert _("Vendor") == "Fornecedor"
    assert _("Inspector") == "Inspetor"
    assert _("Client witness") == "Testemunha do cliente"


def test_signatures_heading_pt_in_every_format(tmp_path, report_data):
    rendered = _render_all(tmp_path, _with_cover(report_data), "pt")
    for fmt, text in rendered.items():
        assert "Assinaturas" in text, fmt
        assert "Desvios e pendências" in text, fmt


def test_latex_nbsp_key_is_the_escape_sequence():
    from pump.utilities.report_latex import _UNICODE

    assert "\u00a0" in _UNICODE and _UNICODE["\u00a0"] == "~"


def test_latex_escape_never_emits_untypesettable_unicode():
    """Free text (e.g. a canvas note included in the report) must not abort the
    PDF build: common symbols are mapped, anything else becomes [U+XXXX]."""
    out = latex_escape("Export ▸ all → OK ✓ ação 汉")
    assert "▸" not in out and "→" not in out and "✓" not in out
    assert "ação" in out  # Latin text passes through (utf8 inputenc + T1)
    assert "[U+6C49]" in out


@pytest.mark.skipif(find_latex_engine() is None, reason="no TeX engine installed")
def test_pdf_survives_symbols_in_free_text(tmp_path, report_data):
    data = dict(report_data)
    data["equipment_description"] = dict(
        report_data["equipment_description"], Note="Report Export ▸ Export all → ✓ ⚠"
    )
    out = LatexReportGenerator("en").generate_pdf(data, str(tmp_path / "sym.pdf"))
    assert open(out, "rb").read().startswith(b"%PDF")
