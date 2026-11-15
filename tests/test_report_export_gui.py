"""Qt (offscreen) tests: Report Export cover fields + Export all (sprint 14)."""

import os
from pathlib import Path

import pytest

from pump.utilities.report_latex import find_latex_engine

PROJECT = (
    Path(__file__).resolve().parents[1]
    / "examples/user/B-34004A_MRT_reference.pumpflow"
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_report_export_defaults_evaluate(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("report_export")
    s = node.settings
    for key in ("project", "client", "location", "test_date", "revision"):
        assert s[key] == ""
    assert [r["role"] for r in s["signatories"]] == [
        "Vendor",
        "Inspector",
        "Client witness",
    ]
    assert all(r["name"] == "" for r in s["signatories"])
    assert node.compute({}) == {}
    assert node.state == "idle"


def test_report_export_dialog_opens(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("report_export")
    node.compute({})
    dlg = node.create_dialog(None, lambda: None)
    assert dlg is not None
    dlg.close()


def test_report_export_fills_defaults_for_old_projects(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("report_export")
    node.settings.pop("project")
    node.settings.pop("signatories")
    node.compute({})
    assert node.settings["project"] == ""
    assert len(node.settings["signatories"]) == 3


def test_markdown_note_report_flag_defaults_false(qapp):
    from pumpflow.nodes.registry import make_node

    note = make_node("markdown_note")
    assert note.settings["report"] is False
    note.compute({})
    dlg = note.create_dialog(None, lambda: None)
    assert dlg is not None
    dlg.close()


def test_open_points_only_from_tagged_notes():
    from pumpflow.binding import open_points_from_notes

    notes = [
        {"title": "A", "body": "# Open\n\nFix the seal.", "report": True},
        {"title": "B", "body": "Hidden", "report": False},
        {"title": "C", "body": "   ", "report": True},
        {"title": "D", "body": "No flag"},
    ]
    assert open_points_from_notes(notes) == ["# Open\n\nFix the seal."]
    assert open_points_from_notes(None) == []


def _reference_data(tmp_notes):
    from pumpflow.binding import assemble_report_data
    from pumpflow.export_cli import build_scene, report_inputs

    _app, scene = build_scene(str(PROJECT))
    rated, branches, s = report_inputs(scene)
    branches = [b for b in branches if b.fitted is not None]
    assert branches
    s = dict(s)
    s.update(
        project="Pump Station 7",
        client="ACME Oil",
        location="Sao Paulo",
        test_date="2026-11-15",
        revision="R1",
    )
    s["signatories"] = [
        {"role": "Vendor", "name": "Ada Vendor"},
        {"role": "Inspector", "name": ""},
        {"role": "Client witness", "name": ""},
    ]
    return assemble_report_data(
        rated, branches, s.get("equipment", {}), settings=s, notes=tmp_notes
    )


@pytest.mark.skipif(not PROJECT.is_file(), reason="B-34004A reference project missing")
def test_export_all_formats_write_cover_and_signatures(qapp, tmp_path):
    from pumpflow.binding import export_reports

    notes = [
        {"body": "Re-test vibration at site.", "report": True},
        {"body": "Private scratch note.", "report": False},
    ]
    data = _reference_data(notes)
    assert data["cover"]["project"] == "Pump Station 7"
    assert data["open_points"] == ["Re-test vibration at site."]

    paths, errors = export_reports(
        data, ["docx", "tex", "html"], language="en", out_dir=str(tmp_path), stem="all"
    )
    assert errors == {}
    assert set(paths) == {"docx", "tex", "html"}
    html = open(paths["html"], encoding="utf-8").read()
    tex = open(paths["tex"], encoding="utf-8").read()
    for text in (html, tex):
        assert "Pump Station 7" in text and "ACME Oil" in text
        assert "Signatures" in text and "Ada Vendor" in text
        assert "Re-test vibration at site." in text
        assert "Private scratch note." not in text
    assert "data:image/png;base64," in html


@pytest.mark.skipif(not PROJECT.is_file(), reason="B-34004A reference project missing")
@pytest.mark.skipif(find_latex_engine() is None, reason="no TeX engine installed")
def test_export_all_writes_four_files(qapp, tmp_path):
    from pumpflow.binding import REPORT_FORMATS, export_reports

    data = _reference_data([])
    paths, errors = export_reports(
        data, list(REPORT_FORMATS), language="pt", out_dir=str(tmp_path), stem="all"
    )
    assert errors == {}
    assert set(paths) == {"docx", "tex", "pdf", "html"}
    assert open(paths["pdf"], "rb").read().startswith(b"%PDF")
