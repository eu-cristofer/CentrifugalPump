"""
LaTeX (``.tex``) and PDF report generation.

Consumes the **same** ``report_data`` dictionary as
:class:`pump.utilities.report.ReportGenerator` (the ``.docx`` writer), so the
Word, LaTeX and PDF reports always carry identical content. The prose and the
gettext catalogs are shared with the docx generator, so ``language="pt"`` works
for every format.

The PDF is compiled from the generated LaTeX source with ``latexmk`` (or two
``pdflatex`` passes when ``latexmk`` is absent). No Word installation is needed.

>>> from pump.utilities.report_latex import latex_escape
>>> latex_escape("B-34004 A&B 50% #1 r_1")
'B-34004 A\\\\&B 50\\\\% \\\\#1 r\\\\_1'
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .report import (
    API_PARAGRAPH,
    COMPARISON_KEY,
    COMPARISON_TITLE,
    DEVIATIONS_TITLE,
    EQUIPMENT_TEXT,
    INTRO_PARAGRAPHS,
    MECHANICAL_RUN_KEY,
    MECHANICAL_RUN_TITLE,
    NPSH_KEY,
    NPSH_TITLE,
    SIGNATURES_TITLE,
    SUMMARY_COLUMNS,
    TEST_DATA_DESCRIPTION,
    TEST_SUMMARY_DESCRIPTION,
    TESTS_DEVELOPMENT_TEXT,
    VISCOSITY_KEY,
    LocalizationHelper,
    comparison_sentence,
    comparison_table,
    cover_rows,
    deviation_items,
    mechanical_run_duration_sentence,
    mechanical_run_notes,
    mechanical_run_table,
    mechanical_run_verdict,
    npsh_points_table,
    npsh_summary_rows,
    performance_verdict,
    signature_block,
    standard_sentence,
    unverified_sentence,
    viscosity_sentence,
)

__all__ = ["LatexReportGenerator", "latex_escape", "find_latex_engine"]

_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Unicode emitted by pint's ``~P`` format (and common in tags/notes) that
# pdflatex cannot typeset natively. Declared in the preamble via newunicodechar.
_UNICODE = {
    "³": r"\textsuperscript{3}",
    "²": r"\textsuperscript{2}",
    "¹": r"\textsuperscript{1}",
    "·": r"\ensuremath{\cdot}",
    "°": r"\ensuremath{^\circ}",
    "µ": r"\ensuremath{\mu}",
    "μ": r"\ensuremath{\mu}",
    "±": r"\ensuremath{\pm}",
    "η": r"\ensuremath{\eta}",
    "ρ": r"\ensuremath{\rho}",
    "ν": r"\ensuremath{\nu}",
    "Δ": r"\ensuremath{\Delta}",
    "≈": r"\ensuremath{\approx}",
    "≤": r"\ensuremath{\leq}",
    "≥": r"\ensuremath{\geq}",
    "×": r"\ensuremath{\times}",
    "–": "--",
    "—": "---",
    "‑": "-",
    "\u00a0": "~",  # no-break space (escape kept: a literal one is invisible)
}


# Symbols common in free text (notes, tags) that pdflatex cannot typeset.
_SYMBOLS = {
    "\u25b8": r"\ensuremath{\blacktriangleright}",  # ▸
    "\u25b6": r"\ensuremath{\blacktriangleright}",  # ▶
    "\u2192": r"\ensuremath{\rightarrow}",  # →
    "\u2190": r"\ensuremath{\leftarrow}",  # ←
    "\u2194": r"\ensuremath{\leftrightarrow}",  # ↔
    "\u21d2": r"\ensuremath{\Rightarrow}",  # ⇒
    "\u2022": r"\textbullet{}",  # •
    "\u2026": r"\ldots{}",  # …
    "\u2713": "OK",  # ✓
    "\u2714": "OK",  # ✔
    "\u2705": "OK",  # ✅
    "\u2717": "X",  # ✗
    "\u274c": "X",  # ❌
    "\u26a0": "(!)",  # ⚠
    "\u2032": "'",  # ′
    "\u2033": "''",  # ″
    "\u201c": "``",
    "\u201d": "''",
    "\u2018": "`",
    "\u2019": "'",
}


def _latex_char(ch: str) -> str:
    """One character for pdflatex: escaped, mapped, or a visible placeholder.

    Characters declared via ``newunicodechar`` (``_UNICODE``) and Latin text pass
    through; known symbols are mapped; anything else becomes ``[U+XXXX]`` so a
    stray symbol in user text can never abort the PDF build.
    """
    if ch in _ESCAPES:
        return _ESCAPES[ch]
    if ch in _SYMBOLS:
        return _SYMBOLS[ch]
    if ch in _UNICODE or ord(ch) < 0x0250:
        return ch
    return f"[U+{ord(ch):04X}]"


def latex_escape(text) -> str:
    """Escape LaTeX special characters in ``text`` (converted with ``str``).

    Also maps symbols pdflatex cannot typeset (arrows, check marks, …) and turns
    any other unsupported character into a visible ``[U+XXXX]`` placeholder.
    """
    return "".join(_latex_char(ch) for ch in str(text))


def _fmt(value) -> str:
    """Same number formatting as the docx report (``0.02f~P`` for quantities)."""
    if isinstance(value, str):
        return value
    if hasattr(value, "magnitude"):
        return f"{value:0.02f~P}"
    if isinstance(value, float):
        return f"{value:0.02f}"
    return str(value)


def find_latex_engine() -> Optional[list]:
    """Return the command used to build a PDF, or ``None`` when no TeX is found."""
    if shutil.which("latexmk"):
        return ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error"]
    if shutil.which("pdflatex"):
        return ["pdflatex", "-interaction=nonstopmode", "-halt-on-error"]
    return None


class LatexReportGenerator:
    """
    Write the FAT report as a LaTeX source and/or a compiled PDF.

    Parameters
    ----------
    language : str, optional
        ``"en"`` (default) or ``"pt"``; selects the gettext catalog and babel.
    locale_dir : str, optional
        Alternative directory holding the ``messages.po``/``.mo`` catalogs.
    """

    def __init__(self, language: str = "en", locale_dir: Optional[str] = None):
        self.language = language
        self._ = LocalizationHelper(language, locale_dir)._

    # ------------------------------------------------------------------ API
    def generate_tex(self, report_data: dict, output_file: Optional[str] = None) -> str:
        """Write ``output_file`` (``.tex``) plus a ``<stem>_figs/`` folder."""
        output_file = Path(output_file or self._default_name(report_data, ".tex"))
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig_dir = output_file.parent / f"{output_file.stem}_figs"
        source = self._render(report_data, fig_dir, fig_dir.name)
        output_file.write_text(source, encoding="utf-8")
        return str(output_file)

    def generate_pdf(
        self,
        report_data: dict,
        output_file: Optional[str] = None,
        engine: Optional[list] = None,
    ) -> str:
        """Compile the LaTeX report into ``output_file`` (``.pdf``)."""
        engine = engine or find_latex_engine()
        if not engine:
            raise RuntimeError(
                "No LaTeX engine found (latexmk/pdflatex). Install a TeX "
                "distribution, or export the .tex and compile it elsewhere."
            )
        output_file = Path(output_file or self._default_name(report_data, ".pdf"))
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pump_report_") as build:
            tex = Path(build) / "report.tex"
            self.generate_tex(report_data, str(tex))
            passes = 1 if Path(engine[0]).name == "latexmk" else 2
            for _ in range(passes):
                proc = subprocess.run(
                    engine + [tex.name],
                    cwd=build,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                )
            pdf = Path(build) / "report.pdf"
            if proc.returncode != 0 or not pdf.is_file():
                log = Path(build) / "report.log"
                tail = log.read_text(errors="replace") if log.is_file() else proc.stdout
                raise RuntimeError("LaTeX compilation failed:\n" + tail[-3000:])
            shutil.copyfile(pdf, output_file)
        return str(output_file)

    # ------------------------------------------------------------- render
    def _default_name(self, report_data: dict, ext: str) -> str:
        tag = report_data["equipment_description"]["TAG"].replace("/", "")
        return f"{self._('Report')}_{tag}_{datetime.now().strftime('%d-%m-%Y')}{ext}"

    def _render(self, report_data: dict, fig_dir: Path, fig_rel: str) -> str:
        _ = self._
        tag = report_data["equipment_description"]["TAG"]
        out = [self._preamble()]
        out.append(
            r"\title{%s\\[0.4em]\large %s}"
            % (latex_escape(_("Factory Acceptance Test Report")), latex_escape(tag))
        )
        out.append(
            r"\date{%s %s}"
            % (latex_escape(_("Generated on")), datetime.now().strftime("%d/%m/%Y"))
        )
        out.append(r"\author{}")
        out.append(r"\begin{document}")
        out.append(r"\maketitle")
        cover = cover_rows(_, report_data)
        if cover:
            out.append(self._kv_table(cover))
            out.append(r"\clearpage")
        out.append(r"\tableofcontents")
        out.append(r"\clearpage")

        out.append(r"\section{%s}" % latex_escape(_("Introduction")))
        out += [latex_escape(_(p)) + "\n" for p in INTRO_PARAGRAPHS]
        out.append(r"\section{%s}" % latex_escape(_("Tests Development")))
        out.append(latex_escape(_(TESTS_DEVELOPMENT_TEXT)) + "\n")

        equipment = report_data.get("equipment_description") or {}
        if equipment:
            out.append(r"\subsection{%s}" % latex_escape(_("Equipment Description")))
            out.append(latex_escape(_(EQUIPMENT_TEXT)) + "\n")
            out.append(self._kv_table([(_(k), v) for k, v in equipment.items()]))

        design_point = report_data.get("design_point")
        if design_point:
            data = design_point.fluid.__dict__ | design_point.__dict__
            data.pop("fluid", None)
            rows = [
                (
                    _("Service") if k == "name" else _(k.replace("_", " ").title()),
                    _fmt(v),
                )
                for k, v in data.items()
            ]
            out.append(latex_escape(_("Design Point data:")) + "\n")
            out.append(self._kv_table(rows))

        acceptance = report_data.get("acceptance", {})
        for pump_tag, entry in report_data.get("test_data", {}).items():
            out.append(r"\clearpage")
            out.append(r"\subsection{%s}" % latex_escape(_("Test Data - ") + pump_tag))
            if "verdict" in entry:
                verdict = performance_verdict(
                    _, entry["verdict"], report_data.get("acceptance")
                )
                out.append(
                    r"\textbf{%s:} %s"
                    % (latex_escape(_("Overall verdict")), latex_escape(verdict))
                    + "\n"
                )
            out.append(self._summary(entry.get("test_summary") or {}, acceptance))
            if entry.get(VISCOSITY_KEY):
                out.append(
                    latex_escape(viscosity_sentence(_, entry[VISCOSITY_KEY])) + "\n"
                )
            out.append(self._test_table(entry.get("test_data") or {}))
            for key in [k for k in entry if "Curve" in k]:
                out.append(self._figure(key, entry[key], pump_tag, fig_dir, fig_rel))
            if MECHANICAL_RUN_KEY in entry:
                out.append(
                    self._mechanical_run(entry[MECHANICAL_RUN_KEY], pump_tag, fig_dir, fig_rel)
                )
            if NPSH_KEY in entry:
                out.append(self._npsh(entry[NPSH_KEY], pump_tag, fig_dir, fig_rel))

        if report_data.get(COMPARISON_KEY):
            out.append(self._comparison(report_data[COMPARISON_KEY], fig_dir, fig_rel))

        items = deviation_items(_, report_data)
        if items:
            out.append(r"\section{%s}" % latex_escape(_(DEVIATIONS_TITLE)))
            out += [latex_escape(i).replace("\n", "\\\\\n") + "\n" for i in items]

        block = signature_block(_, report_data)
        if block is not None:
            header, rows = block
            head = " & ".join(r"\textbf{%s}" % latex_escape(h) for h in header) + r" \\"
            body = [
                " & ".join(latex_escape(c) for c in row) + r" \\[1.6em]" for row in rows
            ]
            out += [
                r"\section{%s}" % latex_escape(_(SIGNATURES_TITLE)),
                r"\begin{center}\begin{tabular}{llll}",
                r"\toprule",
                head,
                r"\midrule",
                *body,
                r"\bottomrule",
                r"\end{tabular}\end{center}",
            ]

        out.append(r"\end{document}")
        return "\n".join(out) + "\n"

    def _preamble(self) -> str:
        babel = "brazilian" if self.language == "pt" else "english"
        uni = "\n".join(
            r"\newunicodechar{%s}{%s}" % (ch, cmd) for ch, cmd in _UNICODE.items()
        )
        return "\n".join(
            [
                r"\documentclass[11pt,a4paper]{article}",
                r"\usepackage[utf8]{inputenc}",
                r"\usepackage[T1]{fontenc}",
                r"\usepackage{lmodern}",
                r"\usepackage[%s]{babel}" % babel,
                r"\usepackage[margin=2.2cm]{geometry}",
                r"\usepackage{booktabs,longtable,array,graphicx,float}",
                r"\usepackage{newunicodechar}",
                r"\usepackage{amssymb}",
                r"\usepackage[hidelinks]{hyperref}",
                r"\setlength{\parskip}{0.5em}",
                r"\setlength{\parindent}{0pt}",
                uni,
            ]
        )

    @staticmethod
    def _kv_table(rows) -> str:
        body = "\n".join(
            r"\textbf{%s} & %s \\" % (latex_escape(k), latex_escape(v)) for k, v in rows
        )
        return "\n".join(
            [
                r"\begin{longtable}{>{\raggedright\arraybackslash}p{0.38\linewidth}"
                r">{\raggedright\arraybackslash}p{0.52\linewidth}}",
                r"\toprule",
                body,
                r"\bottomrule",
                r"\end{longtable}",
            ]
        )

    def _summary(self, summary: dict, acceptance: Optional[dict] = None) -> str:
        if not summary:
            return ""
        _ = self._
        rows = []
        for parameter, value in summary.items():
            if isinstance(value, list):
                cells = value if len(value) == 3 else [value[0], "-", "-"]
            else:
                cells = [value, "-", "-"]
            rows.append(
                " & ".join(
                    [latex_escape(_(parameter))]
                    + [latex_escape(_fmt(c)) for c in cells]
                )
                + r" \\"
            )
        head = " & ".join(r"\textbf{%s}" % latex_escape(_(c)) for c in SUMMARY_COLUMNS)
        parts = [
            r"\subsubsection*{%s}" % latex_escape(_("Performance test summary.")),
            latex_escape(standard_sentence(_, acceptance)),
            r"\begin{quote}\itshape %s\end{quote}" % latex_escape(_(API_PARAGRAPH)),
            latex_escape(_("Calculated Head and Power:")),
            r"\begin{center}\begin{tabular}{lccc}",
            r"\toprule",
            head + r" \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}\end{center}",
        ]
        note = unverified_sentence(_, acceptance)
        if note:
            parts.append(latex_escape(note) + "\n")
        return "\n".join(parts)

    def _test_table(self, data: dict) -> str:
        if not data:
            return ""
        _ = self._
        cols = list(data.keys())
        nrows = len(data[cols[0]])
        head = " & ".join(r"\textbf{%s}" % latex_escape(_(c)) for c in cols) + r" \\"
        body = [
            " & ".join(latex_escape(_fmt(data[c][i])) for c in cols) + r" \\"
            for i in range(nrows)
        ]
        return "\n".join(
            [
                latex_escape(_(TEST_DATA_DESCRIPTION)) + "\n",
                r"\begin{center}\resizebox{\linewidth}{!}{%",
                r"\begin{tabular}{%s}" % ("c" * len(cols)),
                r"\toprule",
                head,
                r"\midrule",
                *body,
                r"\bottomrule",
                r"\end{tabular}}\end{center}",
            ]
        )

    def _mechanical_run(self, entry, pump_tag, fig_dir: Path, fig_rel: str) -> str:
        """Mechanical running test section (UC-11); empty without a result."""
        result = (entry or {}).get("result")
        if result is None:
            return ""
        _ = self._
        header, rows = mechanical_run_table(_, result)
        head = " & ".join(r"\textbf{%s}" % latex_escape(h) for h in header) + r" \\"
        body = [" & ".join(latex_escape(c) for c in row) + r" \\" for row in rows]
        parts = [
            r"\subsubsection*{%s}" % latex_escape(_(MECHANICAL_RUN_TITLE)),
            latex_escape(mechanical_run_duration_sentence(_, result)) + "\n",
            r"\textbf{%s:} %s"
            % (
                latex_escape(_("Overall verdict")),
                latex_escape(mechanical_run_verdict(_, result)),
            )
            + "\n",
            r"\begin{center}\begin{tabular}{lccccc}",
            r"\toprule",
            head,
            r"\midrule",
            *body,
            r"\bottomrule",
            r"\end{tabular}\end{center}",
        ]
        plot = (entry or {}).get("plot")
        if plot is not None:
            parts.append(
                self._figure(MECHANICAL_RUN_TITLE, plot, pump_tag, fig_dir, fig_rel)
            )
        for note in mechanical_run_notes(_, result):
            parts.append(latex_escape(note) + "\n")
        return "\n".join(parts)

    def _npsh(self, entry, pump_tag, fig_dir: Path, fig_rel: str) -> str:
        """NPSH section (UC-05); empty without a result."""
        result = (entry or {}).get("result")
        if result is None:
            return ""
        _ = self._
        summary = [
            r"\textbf{%s} & %s \\" % (latex_escape(label), latex_escape(value))
            for label, value in npsh_summary_rows(_, result)
        ]
        parts = [
            r"\subsubsection*{%s}" % latex_escape(_(NPSH_TITLE)),
            r"\begin{center}\begin{tabular}{ll}",
            r"\toprule",
            *summary,
            r"\bottomrule",
            r"\end{tabular}\end{center}",
        ]
        points = (entry or {}).get("table")
        if points:
            header, rows = npsh_points_table(_, points)
            head = " & ".join(r"\textbf{%s}" % latex_escape(h) for h in header) + r" \\"
            body = [" & ".join(latex_escape(c) for c in row) + r" \\" for row in rows]
            parts += [
                r"\begin{center}\begin{tabular}{cc}",
                r"\toprule",
                head,
                r"\midrule",
                *body,
                r"\bottomrule",
                r"\end{tabular}\end{center}",
            ]
        plot = (entry or {}).get("plot")
        if plot is not None:
            if isinstance(plot, io.BytesIO):
                plot.seek(0)
            parts.append(self._figure(NPSH_TITLE, plot, pump_tag, fig_dir, fig_rel))
        return "\n".join(parts)

    def _comparison(self, comparison, fig_dir: Path, fig_rel: str) -> str:
        """Pump comparison section (UC-08); empty without a table."""
        if not comparison or comparison.get("table") is None:
            return ""
        _ = self._
        table = comparison["table"]
        header, rows = comparison_table(_, comparison)
        head = " & ".join(r"\textbf{%s}" % latex_escape(h) for h in header) + r" \\"
        body = [" & ".join(latex_escape(c) for c in row) + r" \\" for row in rows]
        parts = [
            r"\clearpage",
            r"\subsection{%s}" % latex_escape(_(COMPARISON_TITLE)),
            latex_escape(comparison_sentence(_, comparison)) + "\n",
            r"\begin{center}\resizebox{\linewidth}{!}{%",
            r"\begin{tabular}{cl%s}" % ("c" * (len(header) - 2)),
            r"\toprule",
            head,
            r"\midrule",
            *body,
            r"\bottomrule",
            r"\end{tabular}}\end{center}",
        ]
        plot = comparison.get("plot")
        if plot is not None:
            parts.append(
                self._figure(
                    COMPARISON_TITLE, plot, " / ".join(table.tags), fig_dir, fig_rel
                )
            )
        return "\n".join(parts)

    def _figure(self, title, chart, pump_tag, fig_dir: Path, fig_rel: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "-." else "_" for ch in pump_tag)
        name = f"{safe}_{''.join(ch if ch.isalnum() else '_' for ch in title)}.png"
        fig_dir.mkdir(parents=True, exist_ok=True)
        target = fig_dir / name
        if isinstance(chart, (str, os.PathLike)) and os.path.exists(chart):
            shutil.copyfile(chart, target)
        elif isinstance(chart, io.BytesIO):
            target.write_bytes(chart.getvalue())
        else:
            return ""
        return "\n".join(
            [
                r"\begin{figure}[H]\centering",
                r"\includegraphics[width=0.95\linewidth]{%s/%s}" % (fig_rel, name),
                r"\caption{%s --- %s}"
                % (latex_escape(self._(title)), latex_escape(pump_tag)),
                r"\end{figure}",
            ]
        )
