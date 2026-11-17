"""
pumpflow.binding.reports

Report data assembly and export (docx, tex, pdf, html).
"""

from __future__ import annotations

from typing import Optional

from pump import PerformanceChecker, compare_curves, plot_comparison

from ..signals import RatedPoint, CorrectedCurve, FittedModel
from ._common import make_design_point
from .acceptance import criteria_for, criteria_label
from .curves import format_geometry


def build_report_png(
    corrected: CorrectedCurve, rated: RatedPoint, ylims: Optional[dict] = None
):
    """Reuse the library's matplotlib plot for the report image (BytesIO PNG)."""
    ylims = ylims or {}
    return corrected.curve.plot_performance_curve(
        capacity=rated.q,
        return_io=True,
        head_ylim=ylims.get("head"),
        power_ylim=ylims.get("power"),
        efficiency_ylim=ylims.get("efficiency"),
    )


def report_summary_for(fitted: FittedModel, rated: RatedPoint) -> dict:
    """``PerformanceChecker.report_summary`` for one branch (Check's numbers)."""
    design_point = make_design_point(rated, fitted.curve.fluid)
    return PerformanceChecker(
        design_point, fitted.curve, criteria=criteria_for(rated)
    ).report_summary


def comparison_for(bundles, rated: RatedPoint) -> Optional[dict]:
    """
    Twin-pump comparison (UC-08) of the branches that carry a fitted curve.

    Returns ``None`` when fewer than two bundles have a ``fitted`` model (or the
    curves cannot be compared, e.g. no efficiency data); otherwise
    ``{"table": ComparisonTable, "plot": BytesIO, "at": [rated.q]}``.  The first
    fitted bundle is the reference.  Deterministic: evaluated at the rated
    capacity only.
    """
    fitted = [b for b in bundles if getattr(b, "fitted", None) is not None]
    if len(fitted) < 2:
        return None
    curves = {b.pump_tag: b.fitted.curve for b in fitted}
    if len(curves) < 2:
        return None
    at = [rated.q]
    try:
        table = compare_curves(curves, at)
        plot = plot_comparison(curves, rated_q=rated.q)
    except Exception:
        return None
    return {"table": table, "plot": plot, "at": at}


DEFAULT_SIGNATORY_ROLES = ("Vendor", "Inspector", "Client witness")


def cover_from_settings(
    settings: Optional[dict], standard: Optional[str] = None
) -> dict:
    """Report-cover dict from the Report Export node settings.

    ``{"project", "client", "location", "test_date", "revision", "standard",
    "signatories": [{"role", "name"}, ...]}`` -- all plain strings.  The standard
    falls back to ``standard`` (the acceptance label) when the settings carry
    none; without signatories the three default roles (Vendor / Inspector /
    Client witness, blank names) are used.  ``"include_signatures"`` (default
    ``True``) says whether the report prints the signature block.
    """
    s = settings or {}

    def text(key: str) -> str:
        return str(s.get(key) or "").strip()

    cover = {
        key: text(key)
        for key in ("project", "client", "location", "test_date", "revision")
    }
    cover["standard"] = text("standard") or (standard or "")
    signatories = []
    for row in s.get("signatories") or []:
        if isinstance(row, dict):
            signatories.append(
                {
                    "role": str(row.get("role") or "").strip(),
                    "name": str(row.get("name") or "").strip(),
                }
            )
    if not signatories:
        signatories = [{"role": role, "name": ""} for role in DEFAULT_SIGNATORY_ROLES]
    cover["signatories"] = signatories
    # The signature block is optional (default on); the cover page stays.
    cover["include_signatures"] = bool(s.get("include_signatures", True))
    return cover


def open_points_from_notes(notes) -> list:
    """Open-point blocks from Markdown Note settings tagged ``"report": true``.

    ``notes`` is an iterable of note-node settings dicts; each tagged note with a
    non-blank body contributes its body as ONE block (a string).
    """
    points = []
    for note in notes or ():
        if not note or not note.get("report"):
            continue
        body = str(note.get("body") or "").strip()
        if body:
            points.append(body)
    return points


def assemble_report_data(
    rated: RatedPoint,
    bundles,
    equipment: Optional[dict] = None,
    settings: Optional[dict] = None,
    notes=None,
) -> dict:
    """
    Build the ``report_data`` dict exactly as ``ReportGenerator.generate_report``
    expects (UI_SPEC §5.7): one shared design point + one keyed ``test_data``
    entry per pump TAG, plus a top-level ``"acceptance"`` entry
    (``{"label", "verified", "unverified"}``) describing the criteria used.

    A branch whose test set carried bench geometry adds a
    ``"Test bench geometry (<pump_tag>)"`` line to the equipment description.

    A branch whose corrected curve carries an HI 9.6.7 viscosity correction with
    ``B > 1`` adds a ``"viscous"`` entry (``{"B", "C_Q", "C_H", "C_eta"}``) to its
    fitted data.

    A branch with a mechanical-run result adds a ``"Mechanical Run"`` entry
    (``{"result", "plot"}``) under its tag.  A tag with *only* a mechanical run
    (no fitted curve) still gets an entry, which then lacks ``test_summary`` /
    ``test_data``.

    A branch with an NPSH result adds an ``"NPSH"`` entry
    (``{"result", "plot", "table"}``, ``table`` = ``[(Q, NPSHr), ...]`` of
    Quantities) under its tag; a tag with *only* NPSH is handled the same way.

    With two or more fitted branches a top-level ``"comparison"`` entry
    (``{"table", "plot", "at"}``, see :func:`comparison_for`) is added.

    ``settings`` (the Report Export node settings) adds the top-level ``"cover"``
    entry (:func:`cover_from_settings`: project, client, location, test date,
    revision, signatories; the standard defaults to the acceptance label).
    ``notes`` (an iterable of Markdown Note settings dicts) adds the top-level
    ``"open_points"`` list from the notes tagged ``"report": true``
    (:func:`open_points_from_notes`).  Without them neither key is present.
    """
    equipment = equipment or {}
    design_point = make_design_point(rated)
    criteria = criteria_for(rated)

    equipment_description = {"TAG": rated.tag}
    equipment_description.update({k: str(v) for k, v in equipment.items() if v})

    test_data = {}
    for b in bundles:
        geometry = getattr(b.corrected, "geometry", None) if b.corrected else None
        if geometry is not None and not geometry.is_empty:
            equipment_description[f"Test bench geometry ({b.pump_tag})"] = (
                format_geometry(geometry)
            )
        entry = {}
        if b.fitted is not None:
            entry["test_summary"] = report_summary_for(b.fitted, rated)
            entry["test_data"] = b.fitted.curve.test_data
            if b.compliance is not None:
                entry["verdict"] = bool(b.compliance.overall_pass)
                if b.compliance.verdict_label == "NOT FULLY ASSESSED":
                    entry["not_evaluated"] = list(b.compliance.not_evaluated)
            png = b.plot_png
            if png is None and b.corrected is not None:
                png = build_report_png(b.corrected, rated)
            if png is not None:
                entry["Performance Curve"] = png
            viscous = getattr(b.corrected, "viscous", None) if b.corrected else None
            if viscous and viscous.get("B", 0.0) > 1.0:
                entry["viscous"] = dict(viscous)
        mech = getattr(b, "mechanical", None)
        if mech is not None:
            entry["Mechanical Run"] = {"result": mech.result, "plot": mech.plot_png}
        npsh = getattr(b, "npsh", None)
        if npsh is not None:
            curve = npsh.curve
            table = list(zip(curve.q, curve.npshr)) if curve is not None else []
            entry["NPSH"] = {
                "result": npsh.result,
                "plot": npsh.plot_png,
                "table": table,
            }
        if entry:
            test_data[b.pump_tag] = entry

    report_data = {
        "equipment_description": equipment_description,
        "design_point": design_point,
        "test_data": test_data,
        "acceptance": {
            "label": criteria_label(criteria),
            "verified": bool(criteria.verified),
            "unverified": list(criteria.unverified),
        },
    }
    comparison = comparison_for(bundles, rated)
    if comparison is not None:
        report_data["comparison"] = comparison
    if settings is not None:
        report_data["cover"] = cover_from_settings(
            settings, report_data["acceptance"]["label"]
        )
    open_points = open_points_from_notes(notes)
    if open_points:
        report_data["open_points"] = open_points
    return report_data


def generate_docx(
    report_data: dict,
    language: str = "en",
    template_path: Optional[str] = None,
    output_file: Optional[str] = None,
) -> str:
    """Call the library's ``ReportGenerator`` to write the ``.docx`` (UI_SPEC §4)."""
    try:
        from pump import ReportGenerator  # exported at top level if available
    except Exception:
        from pump.utilities.report import ReportGenerator
    gen = ReportGenerator(language=language, template_path=template_path)
    return gen.generate_report(report_data, output_file=output_file)


def generate_tex(
    report_data: dict, language: str = "en", output_file: Optional[str] = None
) -> str:
    """Write the LaTeX source of the report (``.tex`` + ``<stem>_figs/``)."""
    from pump.utilities.report_latex import LatexReportGenerator

    return LatexReportGenerator(language=language).generate_tex(
        report_data, output_file
    )


def generate_pdf(
    report_data: dict, language: str = "en", output_file: Optional[str] = None
) -> str:
    """Compile the LaTeX report to PDF (needs latexmk or pdflatex on PATH)."""
    from pump.utilities.report_latex import LatexReportGenerator

    return LatexReportGenerator(language=language).generate_pdf(
        report_data, output_file
    )


def generate_html(
    report_data: dict, language: str = "en", output_file: Optional[str] = None
) -> str:
    """Write the report as ONE self-contained ``.html`` (charts as data URIs)."""
    from pump.utilities.report_html import HtmlReportGenerator

    return HtmlReportGenerator(language=language).generate_html(
        report_data, output_file
    )


REPORT_FORMATS = ("docx", "tex", "pdf", "html")


def export_reports(
    report_data: dict,
    formats=REPORT_FORMATS,
    language: str = "en",
    template_path: Optional[str] = None,
    out_dir: Optional[str] = None,
    stem: Optional[str] = None,
):
    """Write the report in every requested format.

    Returns ``(paths, errors)``: ``{fmt: path}`` for the formats that succeeded
    and ``{fmt: message}`` for the ones that failed. One failing format (e.g. no
    TeX installed) never prevents the others from being written.
    """
    import io
    from datetime import datetime
    from pathlib import Path

    if stem is None:
        tag = report_data["equipment_description"]["TAG"].replace("/", "")
        from pump.utilities.report import LocalizationHelper

        report_word = LocalizationHelper(language)._("Report")
        stem = f"{report_word}_{tag}_{datetime.now().strftime('%d-%m-%Y')}"
    folder = Path(out_dir or ".")
    folder.mkdir(parents=True, exist_ok=True)

    writers = {
        "docx": lambda out: generate_docx(
            report_data, language=language, template_path=template_path, output_file=out
        ),
        "tex": lambda out: generate_tex(
            report_data, language=language, output_file=out
        ),
        "pdf": lambda out: generate_pdf(
            report_data, language=language, output_file=out
        ),
        "html": lambda out: generate_html(
            report_data, language=language, output_file=out
        ),
    }
    paths, errors = {}, {}
    for fmt in formats:
        if fmt not in writers:
            errors[fmt] = f"Unknown report format: {fmt!r}"
            continue
        # Each writer reads the in-memory PNG charts; rewind them so a previous
        # format having consumed the buffer cannot leave the next one empty.
        for entry in report_data.get("test_data", {}).values():
            for value in entry.values():
                if isinstance(value, io.BytesIO):
                    value.seek(0)
                elif isinstance(value, dict):  # e.g. "Mechanical Run": {"plot": ...}
                    for inner in value.values():
                        if isinstance(inner, io.BytesIO):
                            inner.seek(0)
        comparison_plot = (report_data.get("comparison") or {}).get("plot")
        if isinstance(comparison_plot, io.BytesIO):
            comparison_plot.seek(0)
        try:
            paths[fmt] = str(writers[fmt](str(folder / f"{stem}.{fmt}")))
        except Exception as exc:  # collected, reported by the caller
            errors[fmt] = f"{type(exc).__name__}: {exc}"
    return paths, errors
