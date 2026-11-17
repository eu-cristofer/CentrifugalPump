"""
Self-contained HTML report generation.

Consumes the **same** ``report_data`` dictionary as
:class:`pump.utilities.report.ReportGenerator` (``.docx``) and
:class:`pump.utilities.report_latex.LatexReportGenerator` (``.tex`` / ``.pdf``)
and mirrors the LaTeX section order, so every format carries the same content.

The output is ONE file: the stylesheet is inline and every PNG chart is embedded
as a ``data:image/png;base64,`` URI, so the report can be mailed or archived on
its own.  All text is escaped with :func:`html.escape`.
"""

from __future__ import annotations

import base64
import io
import os
from datetime import datetime
from html import escape
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

__all__ = ["HtmlReportGenerator"]

_CSS = """
:root { color-scheme: light; }
body { font-family: "Helvetica Neue", Arial, sans-serif; color: #1c1c1c;
  background: #fff; line-height: 1.5; margin: 0; }
main { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
h1 { font-size: 1.9rem; margin-bottom: 0.2rem; }
h2 { font-size: 1.4rem; border-bottom: 2px solid #1f3a5f; padding-bottom: 0.2rem;
  margin-top: 2.2rem; color: #1f3a5f; }
h3 { font-size: 1.15rem; margin-top: 1.6rem; color: #1f3a5f; }
h4 { font-size: 1rem; margin-top: 1.2rem; }
.subtitle { font-size: 1.2rem; color: #444; margin: 0; }
.date { color: #666; }
table { border-collapse: collapse; margin: 0.8rem 0; font-size: 0.9rem; }
th, td { border: 1px solid #b9c2cf; padding: 0.3rem 0.6rem; text-align: center; }
thead th { background: #e8edf4; }
table.kv th { text-align: left; background: #f3f5f9; width: 38%; }
table.kv td { text-align: left; }
table.sig td { height: 2.4rem; }
blockquote { font-style: italic; color: #333; border-left: 4px solid #b9c2cf;
  margin: 0.8rem 0; padding: 0.2rem 1rem; }
figure { margin: 1rem 0; text-align: center; }
figure img { max-width: 100%; height: auto; }
figcaption { font-size: 0.85rem; color: #555; }
.cover { margin: 1.5rem 0 2rem; }
@media print { main { padding: 0; } h2 { page-break-after: avoid; }
  figure { page-break-inside: avoid; } }
""".strip()


def _e(text) -> str:
    """HTML-escape ``text`` (converted with ``str``)."""
    return escape(str(text))


def _fmt(value) -> str:
    """Same number formatting as the docx report (``0.02f~P`` for quantities)."""
    if isinstance(value, str):
        return value
    if hasattr(value, "magnitude"):
        return f"{value:0.02f~P}"
    if isinstance(value, float):
        return f"{value:0.02f}"
    return str(value)


def _image_uri(chart) -> Optional[str]:
    """``data:image/png;base64,...`` for a PNG path / BytesIO, else ``None``."""
    if isinstance(chart, (str, os.PathLike)) and os.path.exists(chart):
        data = Path(chart).read_bytes()
    elif isinstance(chart, io.BytesIO):
        data = chart.getvalue()
    else:
        return None
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


class HtmlReportGenerator:
    """
    Write the FAT report as a single self-contained ``.html`` file.

    Parameters
    ----------
    language : str, optional
        ``"en"`` (default) or ``"pt"``; selects the gettext catalog.
    locale_dir : str, optional
        Alternative directory holding the ``messages.po``/``.mo`` catalogs.
    """

    def __init__(self, language: str = "en", locale_dir: Optional[str] = None):
        self.language = language
        self._ = LocalizationHelper(language, locale_dir)._

    # ------------------------------------------------------------------ API
    def generate_html(
        self, report_data: dict, output_file: Optional[str] = None
    ) -> str:
        """Write ``output_file`` (``.html``); charts are embedded, no extra files."""
        output_file = Path(output_file or self._default_name(report_data, ".html"))
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(self._render(report_data), encoding="utf-8")
        return str(output_file)

    # ------------------------------------------------------------- render
    def _default_name(self, report_data: dict, ext: str) -> str:
        tag = report_data["equipment_description"]["TAG"].replace("/", "")
        return f"{self._('Report')}_{tag}_{datetime.now().strftime('%d-%m-%Y')}{ext}"

    def _render(self, report_data: dict) -> str:
        _ = self._
        tag = report_data["equipment_description"]["TAG"]
        title = _("Factory Acceptance Test Report")
        lang = "pt-BR" if self.language == "pt" else "en"
        out = [
            "<!DOCTYPE html>",
            f'<html lang="{lang}">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_e(title)} - {_e(tag)}</title>",
            f"<style>\n{_CSS}\n</style>",
            "</head>",
            "<body>",
            "<main>",
            "<header>",
            f"<h1>{_e(title)}</h1>",
            f'<p class="subtitle">{_e(tag)}</p>',
            f'<p class="date">{_e(_("Generated on"))} {datetime.now().strftime("%d/%m/%Y")}</p>',
            "</header>",
        ]
        cover = cover_rows(_, report_data)
        if cover:
            out.append(f'<section class="cover">{self._kv_table(cover)}</section>')

        out.append(f"<h2>{_e(_('Introduction'))}</h2>")
        out += [f"<p>{_e(_(p))}</p>" for p in INTRO_PARAGRAPHS]
        out.append(f"<h2>{_e(_('Tests Development'))}</h2>")
        out.append(f"<p>{_e(_(TESTS_DEVELOPMENT_TEXT))}</p>")

        equipment = report_data.get("equipment_description") or {}
        if equipment:
            out.append(f"<h3>{_e(_('Equipment Description'))}</h3>")
            out.append(f"<p>{_e(_(EQUIPMENT_TEXT))}</p>")
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
            out.append(f"<p>{_e(_('Design Point data:'))}</p>")
            out.append(self._kv_table(rows))

        acceptance = report_data.get("acceptance", {})
        for pump_tag, entry in report_data.get("test_data", {}).items():
            out.append(f"<h3>{_e(_('Test Data - ') + pump_tag)}</h3>")
            if "verdict" in entry:
                verdict = performance_verdict(
                    _,
                    entry["verdict"],
                    report_data.get("acceptance"),
                    entry.get("not_evaluated"),
                )
                out.append(
                    f"<p><strong>{_e(_('Overall verdict'))}:</strong> {_e(verdict)}</p>"
                )
            out.append(self._summary(entry.get("test_summary") or {}, acceptance))
            if entry.get(VISCOSITY_KEY):
                out.append(f"<p>{_e(viscosity_sentence(_, entry[VISCOSITY_KEY]))}</p>")
            out.append(self._test_table(entry.get("test_data") or {}))
            for key in [k for k in entry if "Curve" in k]:
                out.append(self._figure(key, entry[key], pump_tag))
            if MECHANICAL_RUN_KEY in entry:
                out.append(self._mechanical_run(entry[MECHANICAL_RUN_KEY], pump_tag))
            if NPSH_KEY in entry:
                out.append(self._npsh(entry[NPSH_KEY], pump_tag))

        if report_data.get(COMPARISON_KEY):
            out.append(self._comparison(report_data[COMPARISON_KEY]))

        items = deviation_items(_, report_data)
        if items:
            out.append(f"<h2>{_e(_(DEVIATIONS_TITLE))}</h2>")
            out += [f"<p>{_e(i).replace(chr(10), '<br>' + chr(10))}</p>" for i in items]

        block = signature_block(_, report_data)
        if block is not None:
            header, rows = block
            out.append(f"<h2>{_e(_(SIGNATURES_TITLE))}</h2>")
            out.append(self._table(header, rows, css="sig"))

        out += ["</main>", "</body>", "</html>"]
        return "\n".join(out) + "\n"

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _table(header, rows, css: str = "") -> str:
        cls = f' class="{css}"' if css else ""
        head = "".join(f"<th>{_e(h)}</th>" for h in header)
        body = "".join(
            "<tr>" + "".join(f"<td>{_e(c)}</td>" for c in row) + "</tr>" for row in rows
        )
        return (
            f"<table{cls}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        )

    @staticmethod
    def _kv_table(rows) -> str:
        body = "".join(
            f'<tr><th scope="row">{_e(k)}</th><td>{_e(v)}</td></tr>' for k, v in rows
        )
        return f'<table class="kv"><tbody>{body}</tbody></table>'

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
            rows.append([_(parameter)] + [_fmt(c) for c in cells])
        parts = [
            f"<h4>{_e(_('Performance test summary.'))}</h4>",
            f"<p>{_e(standard_sentence(_, acceptance))}</p>",
            f"<blockquote>{_e(_(API_PARAGRAPH))}</blockquote>",
            f"<p>{_e(_('Calculated Head and Power:'))}</p>",
            self._table([_(c) for c in SUMMARY_COLUMNS], rows),
        ]
        note = unverified_sentence(_, acceptance)
        if note:
            parts.append(f"<p>{_e(note)}</p>")
        return "\n".join(parts)

    def _test_table(self, data: dict) -> str:
        if not data:
            return ""
        _ = self._
        cols = list(data.keys())
        nrows = len(data[cols[0]])
        rows = [[_fmt(data[c][i]) for c in cols] for i in range(nrows)]
        return "\n".join(
            [
                f"<p>{_e(_(TEST_DATA_DESCRIPTION))}</p>",
                self._table([_(c) for c in cols], rows),
            ]
        )

    def _mechanical_run(self, entry, pump_tag) -> str:
        """Mechanical running test section (UC-11); empty without a result."""
        result = (entry or {}).get("result")
        if result is None:
            return ""
        _ = self._
        header, rows = mechanical_run_table(_, result)
        parts = [
            f"<h4>{_e(_(MECHANICAL_RUN_TITLE))}</h4>",
            f"<p>{_e(mechanical_run_duration_sentence(_, result))}</p>",
            f"<p><strong>{_e(_('Overall verdict'))}:</strong> "
            f"{_e(mechanical_run_verdict(_, result))}</p>",
            self._table(header, rows),
        ]
        plot = (entry or {}).get("plot")
        if plot is not None:
            parts.append(self._figure(MECHANICAL_RUN_TITLE, plot, pump_tag))
        for note in mechanical_run_notes(_, result):
            parts.append(f"<p>{_e(note)}</p>")
        return "\n".join(parts)

    def _npsh(self, entry, pump_tag) -> str:
        """NPSH section (UC-05); empty without a result."""
        result = (entry or {}).get("result")
        if result is None:
            return ""
        _ = self._
        parts = [
            f"<h4>{_e(_(NPSH_TITLE))}</h4>",
            self._kv_table(npsh_summary_rows(_, result)),
        ]
        points = (entry or {}).get("table")
        if points:
            header, rows = npsh_points_table(_, points)
            parts.append(self._table(header, rows))
        plot = (entry or {}).get("plot")
        if plot is not None:
            if isinstance(plot, io.BytesIO):
                plot.seek(0)
            parts.append(self._figure(NPSH_TITLE, plot, pump_tag))
        return "\n".join(parts)

    def _comparison(self, comparison) -> str:
        """Pump comparison section (UC-08); empty without a table."""
        if not comparison or comparison.get("table") is None:
            return ""
        _ = self._
        table = comparison["table"]
        header, rows = comparison_table(_, comparison)
        parts = [
            f"<h3>{_e(_(COMPARISON_TITLE))}</h3>",
            f"<p>{_e(comparison_sentence(_, comparison))}</p>",
            self._table(header, rows),
        ]
        plot = comparison.get("plot")
        if plot is not None:
            parts.append(self._figure(COMPARISON_TITLE, plot, " / ".join(table.tags)))
        return "\n".join(parts)

    def _figure(self, title, chart, pump_tag) -> str:
        uri = _image_uri(chart)
        if uri is None:
            return ""
        caption = f"{self._(title)} \u2014 {pump_tag}"
        return (
            f'<figure><img src="{uri}" alt="{_e(caption)}">'
            f"<figcaption>{_e(caption)}</figcaption></figure>"
        )
