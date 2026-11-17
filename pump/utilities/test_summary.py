"""
pump.utilities.test_summary
===========================

The API 610 **test data summary**: Annex M of the 11th/12th editions, Appendix T
of the 8th.  One summary per pump, written as Word, LaTeX, PDF or Excel.

The summary is a fill-in form: values the project knows are printed, the rest
are left blank for the witness to complete by hand.  Nothing is invented.

Blocks
------
- header (customer, purchaser, order, item, serial, size/type, stages, curve
  number, test date, certifying vendor and witnessing purchaser);
- overall hydraulic performance at rated flow (flow, head, power, NPSH3,
  shut-off head, speed): rated, tested, deviation, acceptance tolerance;
- pump construction data (impeller diameter, patterns, vanes, tip clearance);
- mechanical performance: maximum bearing-housing vibration (RMS) at rated
  flow and in the preferred and allowable operating regions, tested vs
  specified (:func:`vibration_by_region`);
- bearing temperatures;
- the test curve (:func:`plot_test_curve`).

Examples
--------
>>> from pump import Q_
>>> pts = [(Q_(q, "m**3/h"), {"vib_de": Q_(v, "mm/s")})
...        for q, v in [(3.4, 2.9), (6.6, 2.1), (9.8, 2.4), (11.7, 3.6)]]
>>> rows = vibration_by_region(pts, Q_(9.8, "m**3/h"), Q_(9.6, "m**3/h"),
...                            limits={"overall": Q_(3.0, "mm/s"),
...                                    "filtered": Q_(2.0, "mm/s")})
>>> de = rows[0]  # preferred region 70-120 % of 9.6 = 6.72-11.52 m3/h
>>> (de.location, de.measure, de.rated, de.por, de.aor)
('Drive-end bearing housing', 'Overall', (2.4, 3.0), (2.4, 3.0), (3.6, 3.9))
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from .unit_conversion import Q_

__all__ = [
    "PerformanceLine",
    "VibrationLine",
    "TestDataSummary",
    "VIBRATION_KEYS",
    "vibration_by_region",
    "plot_test_curve",
    "write_docx",
    "render_tex",
    "write_tex",
    "write_pdf",
    "write_xlsx",
]


def _vibration_keys() -> dict:
    """Every vibration column key -> (location label, measure) msgids."""
    from ..vibration import ALL_VIBRATION_KEYS, location_of_key

    out = {}
    for key in ALL_VIBRATION_KEYS:
        loc, filtered = location_of_key(key)
        out[key] = (loc.label, "Filtered" if filtered else "Overall")
    return out


#: Test-point vibration keys -> (location, measure) msgids (``pump.vibration``).
VIBRATION_KEYS = _vibration_keys()

Translate = Callable[[str], str]


def _identity(text: str) -> str:
    return text


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PerformanceLine:
    """One row of the hydraulic block (values in ``unit``; deviation a fraction)."""

    __test__ = False  # not a pytest class

    name: str
    unit: str
    rated: Optional[float] = None
    tested: Optional[float] = None
    deviation: Optional[float] = None
    tolerance: str = ""
    note: str = ""


@dataclass(frozen=True)
class VibrationLine:
    """One vibration row: ``(tested, specified)`` in mm/s RMS for each region."""

    location: str
    measure: str
    rated: tuple = (None, None)
    por: tuple = (None, None)
    aor: tuple = (None, None)


@dataclass(frozen=True)
class TestDataSummary:
    """Everything printed on one pump's test data summary."""

    __test__ = False  # not a pytest class

    pump_tag: str
    form_title: str
    standard_label: str = ""
    header: tuple = ()  # ((label msgid, value), ...)
    performance: tuple = ()  # PerformanceLine, ...
    construction: tuple = ()  # ((label msgid, stage 1, series stages), ...)
    vibration: tuple = ()  # VibrationLine, ...
    vibration_notes: tuple = ()  # already-translated sentences
    shaft_displacement: bool = False  # proximity probes fitted (rows printed blank)
    bearings: tuple = ()  # ((label msgid, value text), ...)
    curve_png: Optional[bytes] = None
    notes: tuple = ()  # already-translated sentences
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Vibration by flow region
# --------------------------------------------------------------------------- #
def _mm_s(q) -> Optional[float]:
    return None if q is None else float(q.to("mm/s").magnitude)


def vibration_by_region(
    points: Iterable,
    rated_q: Q_,
    q_bep: Optional[Q_],
    limits: Mapping,
    por: tuple = (0.70, 1.20),
    aor_factor: float = 1.30,
    rated_band: float = 0.05,
    shutoff_fraction: float = 0.05,
) -> tuple:
    """
    Maximum vibration per probe and flow region, tested vs specified.

    Parameters
    ----------
    points : iterable of (Q_, dict)
        ``(flow at rated speed, {vibration key: Q_})`` per test point; keys
        are those of :data:`VIBRATION_KEYS`.
    rated_q, q_bep : Q_
        Rated flow and best-efficiency flow (``q_bep=None``: no regions).
    limits : mapping
        ``{"overall": Q_, "filtered": Q_}`` preferred-region limits (RMS).
    por : (float, float)
        Preferred operating region as fractions of the BEP flow.
    aor_factor : float
        Allowed increase outside the preferred region (API 610: +30 %).
    rated_band : float
        A point counts as "rated flow" within this fraction of rated flow
        (N-553 rev E: vibration measured at each test flow +/-5 %).
    shutoff_fraction : float
        Points below this fraction of rated flow are shut-off (no vibration).

    Returns
    -------
    tuple of VibrationLine
        One line per probe key that has data, in :data:`VIBRATION_KEYS` order.
        The allowable region is every tested point except shut-off, because
        the vendor's allowable-region limits are not part of the project.
    """
    pts = [(q, v) for q, v in points if v]
    rq = float(rated_q.to("m**3/h").magnitude)
    bep = float(q_bep.to("m**3/h").magnitude) if q_bep is not None else None
    lines = []
    for key, (location, measure) in VIBRATION_KEYS.items():
        values = [(float(q.to("m**3/h").magnitude), v[key]) for q, v in pts if key in v]
        if not values:
            continue
        limit = limits.get("filtered" if key.endswith("_f") else "overall")
        spec = _mm_s(limit)
        spec_aor = None if spec is None else round(spec * aor_factor, 2)

        def peak(sel):
            chosen = [_mm_s(v) for q, v in values if sel(q)]
            return round(max(chosen), 2) if chosen else None

        rated = peak(lambda q: abs(q / rq - 1.0) <= rated_band + 1e-9)
        in_por = (
            peak(lambda q: por[0] * bep - 1e-9 <= q <= por[1] * bep + 1e-9)
            if bep
            else None
        )
        in_aor = peak(lambda q: q >= shutoff_fraction * rq)
        lines.append(
            VibrationLine(
                location=location,
                measure=measure,
                rated=(rated, spec),
                por=(in_por, spec),
                aor=(in_aor, spec_aor),
            )
        )
    return tuple(lines)


# --------------------------------------------------------------------------- #
# Test curve figure
# --------------------------------------------------------------------------- #
def plot_test_curve(
    curve,
    rated_q: Q_,
    rated_head: Q_,
    por: Optional[tuple] = None,
    npsh_curve=None,
    title: str = "",
    labels: Optional[Mapping[str, str]] = None,
) -> bytes:
    """
    The test-curve figure of the summary as PNG bytes.

    Head and efficiency (twin axis), power and, when given, NPSH3 against flow
    at rated speed; measured points, fitted curves, the rated point and the
    preferred operating region ``por = (q_min, q_max)`` (``Q_`` values) shaded.
    """
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    lab = {
        "flow": "Flow (m³/h)",
        "head": "Head (m)",
        "eff": "Efficiency (%)",
        "power": "Power (kW)",
        "npsh": "NPSH3 (m)",
        "por": "Preferred operating region",
        "rated": "Rated point",
    }
    lab.update(labels or {})
    fitter = curve.fitter
    caps = np.asarray(fitter.capacities, dtype=float)
    q_max = max(float(caps.max()), float(rated_q.to("m**3/h").magnitude)) * 1.05
    qs = np.linspace(0.0, q_max, 200)

    rows = 3 if npsh_curve is not None else 2
    fig = Figure(figsize=(7.2, 2.6 * rows), dpi=150)
    axes = fig.subplots(rows, 1, sharex=True)
    ax_h = axes[0]
    ax_e = ax_h.twinx()
    ax_h.plot(qs, np.polyval(fitter.head_coeffs, qs), color="#1f5fa8", lw=1.6)
    ax_h.plot(caps, fitter.heads, "o", color="#1f5fa8", ms=4)
    ax_h.set_ylabel(lab["head"], color="#1f5fa8")
    try:
        effs = np.asarray(fitter.efficiencies, dtype=float)
        ax_e.plot(qs, np.polyval(fitter.efficiency_coeffs, qs), color="#2e7d32", lw=1.2)
        ax_e.plot(caps, effs, "s", color="#2e7d32", ms=3)
        ax_e.set_ylabel(lab["eff"], color="#2e7d32")
    except Exception:  # no efficiency data: head only
        ax_e.set_visible(False)
    rq = float(rated_q.to("m**3/h").magnitude)
    ax_h.plot(
        [rq],
        [float(rated_head.to("m").magnitude)],
        "kx",
        ms=9,
        mew=2,
        label=lab["rated"],
    )

    ax_p = axes[1]
    try:
        ax_p.plot(qs, np.polyval(fitter.power_coeffs, qs), color="#b4413c", lw=1.4)
        ax_p.plot(caps, fitter.powers, "o", color="#b4413c", ms=4)
    except Exception:
        pass
    ax_p.set_ylabel(lab["power"], color="#b4413c")

    if npsh_curve is not None:
        ax_n = axes[2]
        nq = np.asarray([float(q.to("m**3/h").magnitude) for q in npsh_curve.q])
        nv = np.asarray([float(n.to("m").magnitude) for n in npsh_curve.npshr])
        grid = np.linspace(float(nq.min()), float(nq.max()), 100)
        ax_n.plot(
            grid,
            [float(npsh_curve(Q_(x, "m**3/h")).to("m").magnitude) for x in grid],
            color="#6a1b9a",
            lw=1.4,
        )
        ax_n.plot(nq, nv, "o", color="#6a1b9a", ms=4)
        ax_n.set_ylabel(lab["npsh"], color="#6a1b9a")

    for ax in axes:
        ax.axvline(rq, color="k", ls=":", lw=0.8)
        if por is not None:
            lo, hi = (float(p.to("m**3/h").magnitude) for p in por)
            ax.axvspan(
                lo,
                hi,
                color="#9ec5e8",
                alpha=0.25,
                lw=0,
                label=lab["por"] if ax is ax_h else None,
            )
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel(lab["flow"])
    axes[-1].set_xlim(0, q_max)
    ax_h.legend(loc="lower left", fontsize=7)
    if title:
        fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Formatting helpers (shared by every writer)
# --------------------------------------------------------------------------- #
def _num(value, digits: int = 2) -> str:
    if value is None:
        return ""
    return f"{value:,.{digits}f}"


def _dev(value) -> str:
    return "" if value is None else f"{value * 100:+.2f} %"


def _perf_rows(s: TestDataSummary, _: Translate) -> list:
    rows = []
    for p in s.performance:
        name = f"{_(p.name)} ({p.unit})"
        if p.note:
            name += f" [{_(p.note)}]"
        digits = 0 if p.unit == "rpm" else 2
        rows.append(
            [
                name,
                _num(p.rated, digits),
                _num(p.tested, digits),
                _dev(p.deviation),
                p.tolerance,
            ]
        )
    return rows


def _perf_header(_: Translate) -> list:
    return [
        "",
        _("Rated"),
        _("Tested (at rated flow)"),
        _("Deviation"),
        _("Acceptance tolerance"),
    ]


def _vib_header(_: Translate) -> tuple:
    regions = [
        _("Rated flow"),
        _("Preferred operating region"),
        _("Allowable operating region"),
    ]
    sub = [_("Tested"), _("Specified")] * 3
    return regions, sub


def _vib_rows(s: TestDataSummary, _: Translate) -> list:
    rows = []
    for v in s.vibration:
        rows.append(
            [f"{_(v.location)}: {_(v.measure)}"]
            + [_num(x) for pair in (v.rated, v.por, v.aor) for x in pair]
        )
    if s.shaft_displacement:
        for loc in ("Drive end", "Non-drive end"):
            for m in ("Overall", "Filtered"):
                rows.append([f"{_('Shaft displacement')}, {_(loc)}: {_(m)}"] + [""] * 6)
    return rows


def _header_rows(s: TestDataSummary, _: Translate) -> list:
    return [[_(label), value or ""] for label, value in s.header]


def _construction_rows(s: TestDataSummary, _: Translate) -> list:
    return [[_(label), a or "", b or ""] for label, a, b in s.construction]


# --------------------------------------------------------------------------- #
# Word
# --------------------------------------------------------------------------- #
def write_docx(
    summaries: Sequence[TestDataSummary], path, translate: Translate = _identity
) -> str:
    """Write every summary to one ``.docx`` (one pump per page)."""
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.shared import Cm, Pt

    _ = translate
    doc = Document()
    for section in doc.sections:
        section.left_margin = section.right_margin = Cm(1.6)
        section.top_margin = section.bottom_margin = Cm(1.4)
    style = doc.styles["Normal"]
    style.font.size = Pt(9)

    def table(rows, header=None, widths=None):
        n = len((header or rows[0]) if (header or rows) else [])
        t = doc.add_table(rows=0, cols=n)
        t.style = "Table Grid"
        if header:
            cells = t.add_row().cells
            for c, text in zip(cells, header):
                c.text = str(text)
                for r in c.paragraphs[0].runs:
                    r.bold = True
        for row in rows:
            cells = t.add_row().cells
            for c, text in zip(cells, row):
                c.text = str(text)
        if widths:
            for row in t.rows:
                for c, w in zip(row.cells, widths):
                    c.width = Cm(w)
        return t

    for i, s in enumerate(summaries):
        if i:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        doc.add_heading(f"{_(s.form_title)}: {s.pump_tag}", level=1)
        if s.standard_label:
            doc.add_paragraph(f"{_('Acceptance criteria')}: {s.standard_label}")
        table(_header_rows(s, _), widths=[6.5, 11.0])

        doc.add_heading(_("Overall hydraulic performance"), level=2)
        table(_perf_rows(s, _), header=_perf_header(_))

        doc.add_heading(_("Pump construction data"), level=2)
        table(_construction_rows(s, _), header=["", _("Stage 1"), _("Series stages")])

        doc.add_heading(_("Mechanical performance"), level=2)
        doc.add_paragraph(
            _("Maximum vibration levels recorded within specified flow region")
        )
        regions, sub = _vib_header(_)
        top = [""] + [x for reg in regions for x in (reg, "")]
        t = table([[""] + sub] + _vib_rows(s, _), header=top)
        for c in (1, 3, 5):  # each region spans its Tested / Specified pair
            merged = t.cell(0, c).merge(t.cell(0, c + 1))
            merged.text = regions[(c - 1) // 2]
            for run in merged.paragraphs[0].runs:
                run.bold = True
        for cell in t.rows[1].cells:
            for run in cell.paragraphs[0].runs:
                run.bold = True
        for note in s.vibration_notes:
            doc.add_paragraph(note)
        if s.extra.get("vibration_chart_png"):
            doc.add_paragraph(_("High-speed vibration limit (API 610 chart)"))
            doc.add_picture(io.BytesIO(s.extra["vibration_chart_png"]), width=Cm(14.0))

        doc.add_heading(_("Bearing temperatures"), level=2)
        table([[_(label), value or ""] for label, value in s.bearings])

        if s.curve_png:
            doc.add_heading(_("Test curve"), level=2)
            doc.add_picture(io.BytesIO(s.curve_png), width=Cm(16.5))
        for note in s.notes:
            doc.add_paragraph(note)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return str(out)


# --------------------------------------------------------------------------- #
# LaTeX / PDF
# --------------------------------------------------------------------------- #
def _tex_table(rows, header=None, spec=None) -> list:
    from .report_latex import latex_escape as e

    n = len(header or rows[0]) if (header or rows) else 1
    spec = spec or ("|p{5.2cm}|" + "|".join(["X"] * (n - 1)) + "|")
    out = [r"\begin{tabularx}{\linewidth}{%s}" % spec, r"\hline"]
    if header:
        out.append(" & ".join(r"\textbf{%s}" % e(h) for h in header) + r" \\ \hline")
    for row in rows:
        out.append(" & ".join(e(c) for c in row) + r" \\ \hline")
    out.append(r"\end{tabularx}")
    return out


def render_tex(
    summaries: Sequence[TestDataSummary],
    translate: Translate = _identity,
    language: str = "en",
    fig_dir: Optional[Path] = None,
    fig_rel: str = "",
) -> str:
    """LaTeX source of the summaries; curve PNGs are written to ``fig_dir``."""
    from .report_latex import latex_escape as e

    _ = translate
    babel = "brazilian" if language == "pt" else "english"
    out = [
        r"\documentclass[10pt,a4paper]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{lmodern}",
        r"\usepackage[%s]{babel}" % babel,
        r"\usepackage[margin=1.5cm]{geometry}",
        r"\usepackage{tabularx,array,graphicx}",
        r"\renewcommand{\arraystretch}{1.25}",
        r"\setlength{\parindent}{0pt}",
        r"\begin{document}",
    ]
    for i, s in enumerate(summaries):
        if i:
            out.append(r"\clearpage")
        out.append(r"\section*{%s: %s}" % (e(_(s.form_title)), e(s.pump_tag)))
        if s.standard_label:
            out.append(
                e(f"{_('Acceptance criteria')}: {s.standard_label}") + r"\par\medskip"
            )
        out += _tex_table(_header_rows(s, _), spec="|p{6.5cm}|X|")
        out.append(r"\subsection*{%s}" % e(_("Overall hydraulic performance")))
        out += _tex_table(_perf_rows(s, _), header=_perf_header(_))
        out.append(r"\subsection*{%s}" % e(_("Pump construction data")))
        out += _tex_table(
            _construction_rows(s, _), header=["", _("Stage 1"), _("Series stages")]
        )
        out.append(r"\subsection*{%s}" % e(_("Mechanical performance")))
        out.append(
            e(_("Maximum vibration levels recorded within specified flow region"))
            + r"\par\smallskip"
        )
        regions, sub = _vib_header(_)
        cell = r">{\centering\arraybackslash}p{1.55cm}"
        spec = "|p{3.8cm}|" + "|".join([cell] * 6) + "|"
        span = r">{\centering\arraybackslash}p{\dimexpr 3.1cm+2\tabcolsep\relax}|"
        out += [r"{\footnotesize", r"\begin{tabular}{%s}" % spec, r"\hline"]
        out.append(
            " & "
            + " & ".join(
                r"\multicolumn{2}{%s}{\textbf{%s}}" % (span, e(r)) for r in regions
            )
            + r" \\ \hline"
        )
        out.append(" & " + " & ".join(e(x) for x in sub) + r" \\ \hline")
        for row in _vib_rows(s, _):
            out.append(" & ".join(e(c) for c in row) + r" \\ \hline")
        out.append(r"\end{tabular}}\par\smallskip")
        for note in s.vibration_notes:
            out.append(r"{\small %s}\par" % e(note))
        chart = s.extra.get("vibration_chart_png")
        if chart and fig_dir is not None:
            fig_dir.mkdir(parents=True, exist_ok=True)
            cname = f"vibration_{i + 1}.png"
            (fig_dir / cname).write_bytes(chart)
            crel = f"{fig_rel}/{cname}" if fig_rel else cname
            out += [
                r"\par\smallskip{\small %s}\par"
                % e(_("High-speed vibration limit (API 610 chart)")),
                r"\begin{center}\includegraphics[width=0.75\linewidth]{%s}\end{center}"
                % crel,
            ]
        out.append(r"\subsection*{%s}" % e(_("Bearing temperatures")))
        out += _tex_table(
            [[_(label), value or ""] for label, value in s.bearings],
            spec="|p{6.5cm}|X|",
        )
        if s.curve_png and fig_dir is not None:
            fig_dir.mkdir(parents=True, exist_ok=True)
            name = f"curve_{i + 1}.png"
            (fig_dir / name).write_bytes(s.curve_png)
            rel = f"{fig_rel}/{name}" if fig_rel else name
            out += [
                r"\subsection*{%s}" % e(_("Test curve")),
                r"\begin{center}\includegraphics[width=0.92\linewidth]{%s}"
                r"\end{center}" % rel,
            ]
        for note in s.notes:
            out.append(r"{\small %s}\par" % e(note))
    out.append(r"\end{document}")
    return "\n".join(out) + "\n"


def write_tex(
    summaries: Sequence[TestDataSummary],
    path,
    translate: Translate = _identity,
    language: str = "en",
) -> str:
    """Write ``path`` (``.tex``) plus a ``<stem>_figs/`` folder for the curves."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig_dir = out.parent / f"{out.stem}_figs"
    out.write_text(
        render_tex(summaries, translate, language, fig_dir, fig_dir.name),
        encoding="utf-8",
    )
    return str(out)


def write_pdf(
    summaries: Sequence[TestDataSummary],
    path,
    translate: Translate = _identity,
    language: str = "en",
    engine: Optional[list] = None,
) -> str:
    """Compile the summaries to ``path`` (``.pdf``) with a local TeX engine."""
    from .report_latex import find_latex_engine

    engine = engine or find_latex_engine()
    if not engine:
        raise RuntimeError(
            "No LaTeX engine found (latexmk/pdflatex). Install a TeX distribution, "
            "or export the .tex and compile it elsewhere."
        )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pump_summary_") as build:
        tex = Path(build) / "summary.tex"
        tex.write_text(
            render_tex(summaries, translate, language, Path(build), ""),
            encoding="utf-8",
        )
        passes = 1 if Path(engine[0]).name == "latexmk" else 2
        proc = None
        for _ in range(passes):
            proc = subprocess.run(
                engine + [tex.name],
                cwd=build,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )
        pdf = Path(build) / "summary.pdf"
        if proc is None or proc.returncode != 0 or not pdf.is_file():
            log = Path(build) / "summary.log"
            tail = (
                log.read_text(errors="replace")
                if log.is_file()
                else (proc.stdout if proc else "")
            )
            raise RuntimeError("LaTeX compilation failed:\n" + tail[-3000:])
        shutil.copyfile(pdf, out)
    return str(out)


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #
def write_xlsx(
    summaries: Sequence[TestDataSummary], path, translate: Translate = _identity
) -> str:
    """Write one worksheet per pump (requires the optional ``openpyxl``)."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError as exc:  # optional dependency
        raise RuntimeError(
            'Excel export needs openpyxl: pip install "centrifugal-pump[xlsx]"'
        ) from exc

    _ = translate
    wb = Workbook()
    wb.remove(wb.active)
    thin = Side(style="thin", color="999999")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    bold = Font(bold=True)
    head_fill = PatternFill("solid", fgColor="DCE6F1")

    for s in summaries:
        title = "".join(ch for ch in s.pump_tag if ch not in "[]:*?/\\")[:31] or "Pump"
        ws = wb.create_sheet(title)
        ws.column_dimensions["A"].width = 46
        for col in "BCDEFG":
            ws.column_dimensions[col].width = 16
        r = 1
        ws.cell(r, 1, f"{_(s.form_title)}: {s.pump_tag}").font = Font(
            bold=True, size=13
        )
        r += 1
        if s.standard_label:
            ws.cell(r, 1, f"{_('Acceptance criteria')}: {s.standard_label}")
            r += 1

        def block(title, header, rows, start):
            row = start + 1
            ws.cell(row, 1, title).font = bold
            row += 1
            if header:
                for c, text in enumerate(header, 1):
                    cell = ws.cell(row, c, text)
                    cell.font, cell.fill, cell.border = bold, head_fill, box
                row += 1
            for values in rows:
                for c, text in enumerate(values, 1):
                    cell = ws.cell(row, c, text)
                    cell.border = box
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                row += 1
            return row

        r = block("", None, _header_rows(s, _), r)
        r = block(
            _("Overall hydraulic performance"), _perf_header(_), _perf_rows(s, _), r
        )
        r = block(
            _("Pump construction data"),
            ["", _("Stage 1"), _("Series stages")],
            _construction_rows(s, _),
            r,
        )
        regions, sub = _vib_header(_)
        top = [""] + [x for reg in regions for x in (reg, "")]
        r = block(
            _("Mechanical performance")
            + ": "
            + _("Maximum vibration levels recorded within specified flow region"),
            top,
            [[""] + sub] + _vib_rows(s, _),
            r,
        )
        for note in s.vibration_notes:
            ws.cell(r, 1, note)
            r += 1
        if s.extra.get("vibration_chart_png"):
            try:
                from openpyxl.drawing.image import Image as XLImage

                chart = XLImage(io.BytesIO(s.extra["vibration_chart_png"]))
                chart.width, chart.height = chart.width * 0.45, chart.height * 0.45
                ws.add_image(chart, f"H{max(r - 12, 2)}")
            except Exception:  # Pillow missing: the table is the deliverable
                pass
        r = block(
            _("Bearing temperatures"),
            None,
            [[_(label), value or ""] for label, value in s.bearings],
            r,
        )
        for note in s.notes:
            ws.cell(r, 1, note)
            r += 1
        if s.curve_png:
            try:
                from openpyxl.drawing.image import Image as XLImage

                img = XLImage(io.BytesIO(s.curve_png))
                img.width, img.height = img.width * 0.55, img.height * 0.55
                ws.add_image(img, f"A{r + 2}")
            except Exception:  # Pillow missing: the table is the deliverable
                pass
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out))
    return str(out)
