"""Build the neutral Word templates used by the report generator.

The templates ``template_en.docx`` and ``template_pt.docx`` next to this script
are neutral: they carry only the styles the report code relies on, an A4 page
setup and a "Page X of Y" footer.  Their body is empty and they hold no
author, company or image.

Regenerate them with::

    python pump/templates/build_templates.py

Never hand-edit the ``.docx`` files; change this script and rebuild.  The build
is reproducible (fixed timestamps, fixed zip metadata), so the committed files
must equal the script output byte for byte.

A site-specific template (for example a company document form) can be used
instead of the bundled one, either with the ``template_path`` argument of the
report generator or by pointing the ``PUMP_TEMPLATE_DIR`` environment variable
to a directory that holds ``template_en.docx`` / ``template_pt.docx``.
"""

from __future__ import annotations

import datetime as _dt
import io
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FIXED_TIME = _dt.datetime(2026, 1, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)

_LANGUAGES = {
    "en": {"lang": "en-US", "page": "Page ", "of": " of "},
    "pt": {"lang": "pt-BR", "page": "Página ", "of": " de "},
}


def _add_field(paragraph, instruction: str) -> None:
    """Append a complex field (begin, instruction, separate, result, end)."""

    def run_with(child):
        run = paragraph.add_run()
        run._r.append(child)
        return run

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    run_with(begin)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    run_with(instr)

    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    run_with(separate)

    paragraph.add_run("1")

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run_with(end)


def _heading_style(styles, name, size, bold, before, after):
    style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(size)
    style.font.bold = bold
    fmt = style.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.keep_with_next = True
    return style


def build_template(language: str, path: Path) -> Path:
    """Build one neutral template and write it to ``path``.

    Parameters
    ----------
    language : str
        ``"en"`` or ``"pt"``.
    path : pathlib.Path
        Destination ``.docx`` file.

    Returns
    -------
    pathlib.Path
        ``path``.

    Raises
    ------
    ValueError
        If ``language`` is not supported.
    """
    if language not in _LANGUAGES:
        raise ValueError(f"Unsupported language: {language!r}")
    cfg = _LANGUAGES[language]
    path = Path(path)

    doc = Document()

    # Empty body: keep only the section properties.
    body = doc.element.body
    for child in list(body):
        if child.tag in (qn("w:p"), qn("w:tbl")):
            body.remove(child)

    styles = doc.styles

    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    rpr = normal.element.get_or_add_rPr()
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    lang.set(qn("w:val"), cfg["lang"])

    _heading_style(styles, "Title_1", 14, True, 24, 24)
    _heading_style(styles, "Title_2", 12, True, 24, 12)
    _heading_style(styles, "Title_3", 11, False, 18, 0)

    text_body = styles.add_style("Text_body", WD_STYLE_TYPE.PARAGRAPH)
    text_body.base_style = normal
    text_body.paragraph_format.space_after = Pt(12)

    quote = styles["Intense Quote"]
    quote.font.size = Pt(10)
    quote.font.color.rgb = RGBColor(0, 0, 0)
    quote.paragraph_format.space_before = Pt(18)
    quote.paragraph_format.space_after = Pt(18)

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(1.0)
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.5)

    footer = section.footer
    footer.is_linked_to_previous = False
    par = footer.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.add_run(cfg["page"])
    _add_field(par, "PAGE")
    par.add_run(cfg["of"])
    _add_field(par, "NUMPAGES")

    props = doc.core_properties
    props.title = "PumpFlow report"
    props.author = ""
    props.last_modified_by = ""
    props.comments = ""
    props.keywords = ""
    props.subject = ""
    props.category = ""
    props.created = FIXED_TIME
    props.modified = FIXED_TIME
    props.revision = 1

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        zipfile.ZipFile(buffer) as src,
        zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as dst,
    ):
        for info in src.infolist():
            new = zipfile.ZipInfo(info.filename, date_time=ZIP_DATE_TIME)
            new.compress_type = zipfile.ZIP_DEFLATED
            new.external_attr = 0o600 << 16
            new.create_system = 3
            dst.writestr(new, src.read(info.filename))
    return path


def main() -> None:
    """Write ``template_en.docx`` and ``template_pt.docx`` next to this script."""
    here = Path(__file__).resolve().parent
    for language in _LANGUAGES:
        out = build_template(language, here / f"template_{language}.docx")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
