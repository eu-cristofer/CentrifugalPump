import gettext
import math
import re
from typing import Callable, Optional
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import os
from datetime import datetime
import io
from pathlib import Path

from pump.utilities.numbers import num as _nf


__all__ = ["ReportGenerator"]


# ---------------------------------------------------------------------------
# Report prose shared by every output format (docx, LaTeX/PDF).  Kept here as
# module constants so the gettext msgids stay identical across generators.
# ---------------------------------------------------------------------------
INTRO_PARAGRAPHS = (
    (
        "This report documents the Factory Acceptance Test (FAT) performed on an API 610 "
        "centrifugal pump at the manufacturer's facility. The FAT was conducted to verify "
        "compliance with the technical specifications and contractual requirements before shipment."
    ),
    (
        "The primary objective of the FAT is to ensure that the pump meets the required  "
        "mechanical, and performance criteria as defined in API 610 and the project specifications. "
        "The test procedures include mechanical run tests and performance verification, vibration "
        "analysis, and NPSH (Net Positive Suction Head) testing."
    ),
    (
        "This report provides a detailed record of the test procedures, observed results, and "
        "compliance with the acceptance criteria. Any deviations, corrective actions, and final "
        "acceptance status are also documented to ensure transparency and traceability of the "
        "qualification process."
    ),
)
TESTS_DEVELOPMENT_TEXT = "Here we present the key details regarding the development of the tests."
EQUIPMENT_TEXT = "The following section presents the main characteristics of the equipment."
TEST_SUMMARY_DESCRIPTION = (
    "The computations in this section were performed in accordance with {standard}:"
)
UNVERIFIED_NOTE = (
    "Acceptance criteria not yet verified against the standard text: {items}."
)
DEFAULT_STANDARD_LABEL = "API 610"
API_PARAGRAPH = (
    "8.3.3.4.3 The test data shall be fit to a spline or an appropriate polynomial (typically, "
    "not less than a third order) for head and for power using a least squares method. The "
    "resulting polynomial equation shall be stated on the head and power calculated. These "
    "values shall be corrected for speed, viscosity, and density (specific gravity).[..]"
)
TEST_DATA_DESCRIPTION = (
    "Here we can find the translation of the test results into data "
    "based on the specified speed of rotation (or frequency) and density."
)
SUMMARY_COLUMNS = ("Parameter", "Actual", "Minimum", "Maximum")

# Viscosity correction note (HI 9.6.7), shared by docx and LaTeX.
VISCOSITY_KEY = "viscous"
VISCOSITY_TITLE = "Viscosity correction (HI 9.6.7)"

# Mechanical running test section (UC-11), shared by docx and LaTeX.
MECHANICAL_RUN_KEY = "Mechanical Run"
MECHANICAL_RUN_TITLE = "Mechanical running test"
MECHANICAL_RUN_COLUMNS = ("Channel", "Unit", "Min", "Max", "Limit", "Status")
MECHANICAL_RUN_SOURCE = "Criteria source: {source}"
MECHANICAL_RUN_UNVERIFIED_NOTE = (
    "Mechanical running test limits not yet verified against the standard text."
)

# NPSH section (UC-05), shared by docx and LaTeX.
NPSH_KEY = "NPSH"
NPSH_TITLE = "NPSH"

# Pump comparison section (UC-08), shared by docx and LaTeX.
COMPARISON_KEY = "comparison"
COMPARISON_TITLE = "Comparison"
COMPARISON_COLUMNS = (
    "Q [m³/h]",
    "Tag",
    "H [m]",
    "P [kW]",
    "η [%]",
    "ΔH [%]",
    "ΔP [%]",
    "Δη [%]",
)

# Cover page, deviations and signature block (sprint 14), shared by docx, LaTeX
# and HTML.  ``report_data["cover"]`` and ``report_data["open_points"]`` are
# optional: without them none of these blocks is rendered.
COVER_KEY = "cover"
OPEN_POINTS_KEY = "open_points"
DEVIATIONS_TITLE = "Deviations and open points"
SIGNATURES_TITLE = "Signatures"
SIGNATURE_COLUMNS = ("Role", "Name", "Signature", "Date")
SIGNATURE_ROLES = ("Vendor", "Inspector", "Client witness")
SIGNATURE_BLANK = "_" * 16


def standard_sentence(translate: Callable[[str], str], acceptance: Optional[dict]) -> str:
    """Localized "computations performed in accordance with <standard>:" sentence."""
    label = (acceptance or {}).get("label") or DEFAULT_STANDARD_LABEL
    return translate(TEST_SUMMARY_DESCRIPTION).format(standard=label)


def unverified_sentence(
    translate: Callable[[str], str], acceptance: Optional[dict]
) -> Optional[str]:
    """Localized note listing unverified criteria, or ``None`` when all verified."""
    items = list((acceptance or {}).get("unverified") or [])
    if not items:
        return None
    return translate(UNVERIFIED_NOTE).format(items=", ".join(str(i) for i in items))


def cover_rows(translate: Callable[[str], str], report_data: dict) -> list:
    """``[(label, value), ...]`` of the cover block; ``[]`` without a ``"cover"``.

    Order: project, client, service/pump tag(s), standard + edition, test date,
    location, revision.  Empty values are skipped.  The standard falls back to
    the acceptance label when the cover does not carry one.
    """
    cover = report_data.get(COVER_KEY) or {}
    if not cover:
        return []
    rows = []

    def add(label, value):
        value = "" if value is None else str(value).strip()
        if value:
            rows.append((label, value))

    equipment = report_data.get("equipment_description") or {}
    tags = []
    for tag in [equipment.get("TAG"), *(report_data.get("test_data") or {})]:
        if tag and str(tag) not in tags:
            tags.append(str(tag))
    standard = cover.get("standard") or (report_data.get("acceptance") or {}).get("label")

    add(translate("Project"), cover.get("project"))
    add(translate("Client"), cover.get("client"))
    add(translate("TAG"), ", ".join(tags))
    add(translate("Standard"), standard)
    add(translate("Test date"), cover.get("test_date"))
    add(translate("Location"), cover.get("location"))
    add(translate("Revision"), cover.get("revision"))
    return rows


def open_point_paragraphs(text) -> list:
    """Split a note body into paragraphs (blank-line separated); ``#`` marks dropped."""
    paragraphs = []
    for block in re.split(r"\n\s*\n", str(text).strip()):
        lines = []
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                stripped = stripped.lstrip("#").strip()
            if stripped:
                lines.append(stripped)
        if lines:
            paragraphs.append("\n".join(lines))
    return paragraphs


def deviation_items(translate: Callable[[str], str], report_data: dict) -> list:
    """Paragraphs of the "Deviations and open points" section.

    The unverified-criteria sentence (when the acceptance data lists any) plus the
    open-point blocks.  Empty -- so no heading is written -- unless the report
    carries a cover or open points.
    """
    open_points = list(report_data.get(OPEN_POINTS_KEY) or [])
    if not (report_data.get(COVER_KEY) or open_points):
        return []
    items = []
    note = unverified_sentence(translate, report_data.get("acceptance"))
    if note:
        items.append(note)
    for text in open_points:
        items.extend(open_point_paragraphs(text))
    return items


def signature_block(translate: Callable[[str], str], report_data: dict):
    """``(header, rows)`` of the signature table, or ``None`` without a cover.

    One row per signatory (default Vendor / Inspector / Client witness with blank
    names); the Signature and Date cells are blank lines to sign on.  A cover
    with ``"include_signatures": False`` has no signature block either.
    """
    cover = report_data.get(COVER_KEY) or {}
    if not cover or cover.get("include_signatures") is False:
        return None
    signatories = cover.get("signatories") or [
        {"role": role, "name": ""} for role in SIGNATURE_ROLES
    ]
    header = [translate(c) for c in SIGNATURE_COLUMNS]
    rows = []
    for sig in signatories:
        role = str(sig.get("role") or "")
        rows.append(
            [
                translate(role) if role else "",
                str(sig.get("name") or ""),
                SIGNATURE_BLANK,
                SIGNATURE_BLANK,
            ]
        )
    return header, rows


def viscosity_sentence(translate: Callable[[str], str], viscous: dict) -> str:
    """``Viscosity correction (HI 9.6.7): B = ..., C_Q = ..., C_H = ..., C_η = ...``.

    ``viscous`` is ``{"B", "C_Q", "C_H", "C_eta"}`` (factors at the BEP).
    """
    return (
        f"{translate(VISCOSITY_TITLE)}: "
        f"B = {_nf(viscous['B'], '0.2f')}, "
        f"C_Q = {_nf(viscous['C_Q'], '0.3f')}, "
        f"C_H = {_nf(viscous['C_H'], '0.3f')}, "
        f"C_η = {_nf(viscous['C_eta'], '0.3f')}"
    )


def mechanical_run_verdict(translate: Callable[[str], str], result) -> str:
    """Localized overall verdict of a mechanical run result.

    A verdict computed against limits that are not verified against the
    standard text is provisional and says so ("FAILED (unverified limits)"), so
    a seed/placeholder limit is never presented as a real test failure.
    """
    if not result.passed:
        text = translate("FAILED")
    elif result.fully_assessed:
        text = translate("PASSED")
    else:
        text = translate("PASSED (not fully assessed)")
    if not getattr(result, "verified", True):
        text += f" ({translate('unverified limits')})"
    return text


def performance_verdict(
    translate: Callable[[str], str], passed: bool, acceptance=None, not_evaluated=None
) -> str:
    """Localized performance verdict; provisional when the criteria are unverified.

    ``not_evaluated`` (names of required checks that could not be computed,
    with no check failed) gives "NOT FULLY ASSESSED: ..." instead of an
    approval or a rejection.
    """
    if not passed and not_evaluated:
        names = ", ".join(translate(n) for n in not_evaluated)
        return f"{translate('NOT FULLY ASSESSED')}: {names}"
    text = translate("APPROVED") if passed else translate("NOT APPROVED")
    if acceptance and not acceptance.get("verified", True):
        text += f" ({translate('unverified criteria')})"
    return text


TOLERANCE_OVERRIDE_INTRO = (
    "Tolerances overridden by the user (acceptance-criteria default in brackets)"
)
_OVERRIDE_NAMES = (
    ("head", "head", "±"),
    ("shutoff", "shut-off head", "±"),
    ("power", "power", "+"),
    ("efficiency", "efficiency", "−"),
)


def tolerance_override_sentence(
    translate: Callable[[str], str], override, reason: str = ""
) -> str:
    """One sentence listing user-overridden tolerances, or ``""`` when none.

    ``override`` is ``{name: (used, default)}`` with fractions (``None`` = not
    set), as written by the workbench's Report Export.  The verdict and the
    summary limits of the same section were computed with the *used* values.
    ``reason`` (the user's justification) is appended; a missing reason is
    stated, so an unexplained override is visible in the report.

    Examples
    --------
    >>> tolerance_override_sentence(str, {"head": (0.05, 0.03)})
    'Tolerances overridden by the user (acceptance-criteria default in brackets): head ±5.0 % (3.0 %). Reason: not given.'
    """
    if not override:
        return ""

    def pct(v):
        return translate("not set") if v is None else f"{_nf(v * 100, '0.1f')} %"

    parts = []
    for key, label, sign in _OVERRIDE_NAMES:
        if key in override:
            used, default = override[key]
            shown = pct(used) if used is None else f"{sign}{pct(used)}"
            parts.append(f"{translate(label)} {shown} ({pct(default)})")
    if not parts:
        return ""
    why = reason.strip() if reason else translate("not given")
    return (
        f"{translate(TOLERANCE_OVERRIDE_INTRO)}: {'; '.join(parts)}. "
        f"{translate('Reason')}: {why}."
    )


def shutoff_waiver_sentence(translate: Callable[[str], str], reason: str = "") -> str:
    """The agreed reason shut-off was not tested, or ``""`` when none.

    Printed under the verdict when the Compliance node's waiver was applied
    (no test point near zero flow, so the shut-off head was not judged).

    Examples
    --------
    >>> shutoff_waiver_sentence(str, "integral-gear pump, client letter 12")
    'Shut-off head not tested (no test point near zero flow); not judged by agreement. Reason: integral-gear pump, client letter 12.'
    >>> shutoff_waiver_sentence(str, "")
    ''
    """
    why = (reason or "").strip()
    if not why:
        return ""
    return (
        f"{translate('Shut-off head not tested (no test point near zero flow); not judged by agreement')}. "
        f"{translate('Reason')}: {why.rstrip('.')}."
    )


def mechanical_run_duration_sentence(translate: Callable[[str], str], result) -> str:
    """``Duration: 4.00 h`` (plus the required minimum when configured)."""
    text = f"{translate('Duration')}: {_nf(result.duration.to('h'), '0.2f~P')}"
    if getattr(result, "min_duration", None) is not None:
        text += f" (≥ {_nf(result.min_duration.to('h'), '0.2f~P')})"
    return text


def mechanical_run_table(translate: Callable[[str], str], result) -> tuple:
    """``(header, rows)`` of strings for the per-channel table (never empty cells).

    The bearing temperature rules (``result.rules``) follow the channels as
    rows of their own: rule name, unit, the worst value in the Max column and
    the limit.
    """
    status_text = {
        "pass": translate("PASS"),
        "fail": translate("FAIL"),
        "info": translate("INFO"),
        "not evaluated": translate("NOT EVALUATED"),
    }

    def num(q):
        return "-" if q is None else f"{_nf(q.magnitude, '0.3g')}"

    header = [translate(c) for c in MECHANICAL_RUN_COLUMNS]
    rows = []
    for ch in result.channels:
        if ch.limit is not None:
            limit = f"≤ {num(ch.limit)}"
        elif ch.stabilisation:
            st = ch.stabilisation
            limit = f"Δ ≤ {_nf(st['allowed'], '0.3g~P')} / {_nf(st['window'], '0.3g~P')}"
        else:
            limit = translate("not configured")
        rows.append(
            [
                ch.name or "-",
                ch.unit or "-",
                num(ch.min),
                num(ch.max),
                limit,
                status_text.get(ch.status, ch.status),
            ]
        )
    for rule in getattr(result, "rules", ()) or ():
        rows.append(
            [
                translate(rule.name),
                rule.unit or "-",
                "-",
                num(rule.value),
                f"≤ {num(rule.limit)}" if rule.limit is not None else "-",
                status_text.get(rule.status, rule.status),
            ]
        )
    return header, rows


def mechanical_run_notes(translate: Callable[[str], str], result) -> list:
    """Criteria-source line and unverified note (empty list if nothing to say)."""
    notes = []
    lube = getattr(result, "lubrication", None)
    if getattr(result, "rules", ()):
        from ..mechanical_run import LUBRICATION_LABELS

        label = LUBRICATION_LABELS.get(lube or "", "not stated")
        notes.append(f"{translate('Bearing lubrication')}: {translate(label)}.")
    for rule in getattr(result, "rules", ()) or ():
        if rule.note:
            notes.append(f"{translate(rule.name)}: {translate(rule.note)}.")
    if getattr(result, "source", ""):
        notes.append(translate(MECHANICAL_RUN_SOURCE).format(source=result.source))
    if not getattr(result, "verified", False):
        notes.append(translate(MECHANICAL_RUN_UNVERIFIED_NOTE))
    return notes


def npsh_verdict(translate: Callable[[str], str], result) -> str:
    """Localized NPSH margin verdict.

    ``"not configured"`` when no margin rule is set (status ``info``); otherwise
    PASSED / FAILED, marked "(unverified criteria)" when the rule is not verified.
    """
    if result.status == "info":
        return translate("not configured")
    text = translate("PASSED") if result.status == "pass" else translate("FAILED")
    if not getattr(result, "verified", False):
        text += f" ({translate('unverified criteria')})"
    return text


def npsh_summary_rows(translate: Callable[[str], str], result) -> list:
    """``[(label, value), ...]`` strings: NPSHa, NPSHr, ratio, margin, the
    quoted-NPSHr check (when judged) and the verdict."""
    rows = [
        (translate("NPSH available"), f"{_nf(result.npsha.to('m'), '0.2f~P')}"),
        (translate("NPSH required"), f"{_nf(result.npshr.to('m'), '0.2f~P')}"),
        (translate("Ratio"), f"{_nf(result.ratio, '0.2f')}"),
        (translate("Margin"), f"{_nf(result.margin.to('m'), '0.2f~P')}"),
    ]
    quoted = getattr(result, "npshr_quoted", None)
    quoted_ok = getattr(result, "quoted_ok", None)
    if quoted is not None and quoted_ok is not None:
        mark = translate("PASSED") if quoted_ok else translate("FAILED")
        rows.append(
            (translate("Quoted NPSH required"), f"{_nf(quoted.to('m'), '0.2f~P')} ({mark})")
        )
    rows.append((translate("Overall verdict"), npsh_verdict(translate, result)))
    return rows


def npsh_points_table(translate: Callable[[str], str], table) -> tuple:
    """``(header, rows)`` of strings for the ``[(q, npshr), ...]`` points table."""
    header = [translate("Capacity"), translate("NPSH required")]
    rows = [[f"{_nf(q, '0.2f~P')}", f"{_nf(r, '0.2f~P')}"] for q, r in (table or ())]
    return header, rows


def comparison_sentence(translate: Callable[[str], str], comparison: dict) -> str:
    """``Reference: <tag>. Δ vs reference: (x - ref) / ref, in %.``"""
    ref = comparison["table"].tags[0]
    return (
        f"{translate('Reference')}: {ref}. "
        f"{translate('Δ vs reference')}: (x - ref) / ref, in %."
    )


def comparison_table(translate: Callable[[str], str], comparison: dict) -> tuple:
    """``(header, rows)`` of strings: one line per (capacity, tag), deltas vs reference."""
    table = comparison["table"]

    def pct(value) -> str:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "-"
        return f"{_nf(value * 100.0, '+0.2f')}"

    header = list(COMPARISON_COLUMNS)
    rows = []
    for row in table.rows:
        q = f"{_nf(float(row.q.to('m**3/h').magnitude), '0.1f')}"
        for tag in table.tags:
            vals = row.values[tag]
            d = row.deltas.get(tag)
            rows.append(
                [
                    q,
                    tag,
                    f"{_nf(vals['head'].magnitude, '0.2f')}",
                    f"{_nf(vals['power'].magnitude, '0.2f')}",
                    f"{_nf(vals['efficiency'].magnitude, '0.2f')}",
                    pct(d["head"]) if d else "-",
                    pct(d["power"]) if d else "-",
                    pct(d["efficiency"]) if d else "-",
                ]
            )
    return header, rows


def _parse_po(path) -> dict:
    """Minimal ``.po`` reader: ``{msgid: msgstr}`` for non-empty translations.

    Handles multi-line (concatenated) strings and the standard C escapes; plural
    forms and contexts are not used by the report catalogs.
    """
    import ast

    catalog: dict = {}
    msgid = msgstr = None
    target = None

    def flush():
        if msgid and msgstr:
            catalog[msgid] = msgstr

    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid "):
            flush()
            msgid, msgstr, target = ast.literal_eval(line[6:]), None, "id"
        elif line.startswith("msgstr "):
            msgstr, target = ast.literal_eval(line[7:]), "str"
        elif line.startswith('"'):
            if target == "id":
                msgid += ast.literal_eval(line)
            elif target == "str":
                msgstr += ast.literal_eval(line)
    flush()
    return catalog


class LocalizationHelper:
    """
    Handles translation and localization using gettext.

    Parameters
    ----------
    language : str, optional
        The language code to use for localization (default is 'en').
    locale_dir : str, optional
        The directory where localization files are stored (default is
        "pump/utilites/locales"). If changed, insert full path.
    """
    def __init__(self, language: str = 'en', locale_dir: Optional[str] = None) -> None:
        self.language = language
        self.locale_dir = locale_dir
        self._ = self._setup_translation()

    def _setup_translation(self) -> Callable[[str], str]:
        """
        Sets up gettext for localization.

        Returns
        -------
        Callable[[str], str]
            A function that translates a given string based on the selected language.
        """

        locale_dir: Path = (
            Path(self.locale_dir) if self.locale_dir else Path(__file__).parent / "locales"
        )

        # Compiled catalogs (*.mo) are git-ignored, so a fresh checkout only has
        # the *.po sources. Without this fallback gettext silently returns the
        # English msgids and a "pt" report comes out in English.
        if not gettext.find("messages", localedir=locale_dir, languages=[self.language]):
            po_path = Path(locale_dir) / self.language / "LC_MESSAGES" / "messages.po"
            if po_path.is_file():
                catalog = _parse_po(po_path)
                return lambda message: catalog.get(message) or message

        try:
            lang_translation = gettext.translation(
                "messages",
                localedir=locale_dir,
                languages=[self.language],
                fallback=True
            )
            lang_translation.install()
            return lang_translation.gettext
        except FileNotFoundError:
            return gettext.gettext  # Fallback to default gettext


class ReportGenerator:
    """
    Generates a report from predefined templates using the `python-docx` library.

    This class loads a document template, populates it with data, and applies localization
    to ensure language-specific content where necessary.

    Parameters
    ----------
    language : str, optional
        The language for the report (default is 'en').
    locale_dir : str, optional
        The directory containing localization files (default is
        "pump/utilites/locales"). If changed, insert full path.
    template_dir : str, optional
        The directory containing report templates (default is "templates").

    Attributes
    ----------
    language : str
        Selected language code.
    template_dir : str
        Directory containing document templates.
    localization : LocalizationHelper
        Handles language-specific text translations.
    _ : Callable[[str], str]
        Translation function from the localization helper.
    """

    def __init__(self, language='en', locale_dir : Optional[str]=None, template_path : Optional[str]=None):
        self.language = language
        self.template_path = template_path
        self.localization = LocalizationHelper(language, locale_dir)
        self._ = self.localization._

    def _get_template_path(self) -> Path:
        """Resolve the Word template to open.

        Order: the explicit ``template_path``; else
        ``$PUMP_TEMPLATE_DIR/template_<language>.docx`` when that file exists;
        else the neutral template bundled with the package.

        Returns
        -------
        pathlib.Path
            Path of the template file.

        Raises
        ------
        FileNotFoundError
            If the explicit template path or the bundled template is missing.
        """
        if self.template_path:
            path = Path(self.template_path)
            if not path.exists():
                raise FileNotFoundError(f"Template file not found: {path}")
            return path

        env_dir = os.environ.get("PUMP_TEMPLATE_DIR")
        if env_dir:
            candidate = Path(env_dir) / f"template_{self.language}.docx"
            if candidate.exists():
                return candidate

        bundled = Path(__file__).parents[1] / "templates" / f"template_{self.language}.docx"
        if not bundled.exists():
            raise FileNotFoundError(f"Template file not found: {bundled}")
        return bundled

    def generate_report(self, report_data, output_file=None):
        """
        Generates a report from a predefined template.

        Parameters
        ----------
        report_data : dict
            Dictionary containing all necessary report information.  The optional
            ``"cover"`` and ``"open_points"`` entries add a cover block, the
            "Deviations and open points" section and a signature block.
        output_file : str, optional
            Path to save the generated report.

        Returns
        -------
        str
            Path of the saved report file.
        """
        TAGS = report_data["equipment_description"]["TAG"]
        if output_file is None:
            if "/" in TAGS:
                str_TAGS = TAGS.replace("/", "")
            else:
                str_TAGS = TAGS
            output_file = f"{self._("Report")}_{str_TAGS}_{datetime.now().strftime('%d-%m-%Y')}.docx"

        template_path = self._get_template_path()
        document = Document(template_path)

        self._add_cover(document, report_data)
        self._add_intro(document)
        self._add_equipment_description(document, report_data.get("equipment_description", {}))
        self._add_design_point(document, report_data.get("design_point", {}))
        acceptance = report_data.get("acceptance", {})
        for tag, test_data in report_data["test_data"].items():
            document.add_paragraph(self._('Test Data - ') + tag, style='Title_2')
            if "verdict" in test_data:
                verdict = performance_verdict(
                    self._, test_data["verdict"], acceptance,
                    test_data.get("not_evaluated"),
                )
                document.add_paragraph(f"{self._('Overall verdict')}: {verdict}", style='Text_body')
            override_text = tolerance_override_sentence(
                self._,
                test_data.get("tolerance_override"),
                test_data.get("tolerance_override_reason", ""),
            )
            if override_text:
                document.add_paragraph(override_text, style='Text_body')
            waiver_text = shutoff_waiver_sentence(self._, test_data.get("shutoff_waiver", ""))
            if waiver_text:
                document.add_paragraph(waiver_text, style='Text_body')
            self._add_test_summary(document, test_data.get("test_summary", {}), acceptance)
            if test_data.get(VISCOSITY_KEY):
                document.add_paragraph(
                    viscosity_sentence(self._, test_data[VISCOSITY_KEY]), style='Text_body'
                )
            self._add_test_data(document, test_data.get("test_data", {}))

            # Adding  charts, if any.
            search_key = 'Curve'
            matches = [key for key in test_data.keys() if search_key in key]

            for chart in matches:
                self._add_chart(document, chart, test_data[chart])

            if MECHANICAL_RUN_KEY in test_data:
                self._add_mechanical_run(document, test_data[MECHANICAL_RUN_KEY])

            if NPSH_KEY in test_data:
                self._add_npsh(document, test_data[NPSH_KEY])

        if report_data.get(COMPARISON_KEY):
            self._add_comparison(document, report_data[COMPARISON_KEY])

        self._add_deviations(document, report_data)
        self._add_signatures(document, report_data)

        document.save(output_file)
        print(f"{self._('New document saved at')}: {output_file}")
        return output_file

    def _add_cover(self, document, report_data):
        """
        Add the cover block (title + project / client / tags / standard / date /
        location / revision) at the very start of the document.

        Nothing is written without ``report_data["cover"]``.
        """
        rows = cover_rows(self._, report_data)
        if not rows:
            return
        table_font = "Consolas"
        width = Inches(2)
        body = document.element.body
        before = list(body)  # keeps the proxies alive so ids stay stable
        known = {id(el) for el in before}
        first = before[0]

        title = document.add_paragraph(style='Text_body')
        run = title.add_run(self._("Factory Acceptance Test Report"))
        run.bold = True
        run.font.size = Pt(20)
        table = document.add_table(rows=len(rows), cols=2)
        table.style = "Table Grid"
        table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        for r, (label, value) in enumerate(rows):
            left, right = table.cell(r, 0), table.cell(r, 1)
            left.text, right.text = label, value
            left.width = right.width = width
            run_left = left.paragraphs[0].runs[0]
            run_right = right.paragraphs[0].runs[0]
            run_left.bold = True
            run_left.font.size = Pt(9)
            run_right.font.size = Pt(8)
            run_left.font.name = table_font
            run_right.font.name = table_font
        document.add_page_break()

        # python-docx appends; move the new block in front of the template body.
        for element in [el for el in body if id(el) not in known]:
            first.addprevious(element)

    def _add_deviations(self, document, report_data):
        """Add "Deviations and open points" (unverified criteria + open points)."""
        items = deviation_items(self._, report_data)
        if not items:
            return
        document.add_paragraph(self._(DEVIATIONS_TITLE), style='Title_2')
        for item in items:
            document.add_paragraph(item, style='Text_body')

    def _add_signatures(self, document, report_data):
        """Add the signature table (Role / Name / Signature / Date)."""
        block = signature_block(self._, report_data)
        if block is None:
            return
        header, rows = block
        table_font = "Consolas"
        document.add_paragraph(self._(SIGNATURES_TITLE), style='Title_2')
        table = document.add_table(rows=len(rows) + 1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        width = Inches(1.5)
        for col, name in enumerate(header):
            cell = table.cell(0, col)
            cell.text = name
            cell.width = width
            run = cell.paragraphs[0].runs[0]
            run.bold = True
            run.font.size = Pt(9)
            run.font.name = table_font
        for r, values in enumerate(rows, start=1):
            for col, text in enumerate(values):
                cell = table.cell(r, col)
                cell.text = text
                cell.width = width
                runs = cell.paragraphs[0].runs
                if runs:  # an empty name leaves the cell without runs
                    runs[0].font.size = Pt(8)
                    runs[0].font.name = table_font

    def _add_intro(self, document):
        """
        Add introductory section to the document.

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        """
        # Adding instructions to update the TOC
        TOC_note = (
            "-X-X-X-\n"
            "Note: To update the Table of Contents, open the document in Word, "
            "right-click on the TOC, and select 'Update Field'.\n"
            "-X-X-X-"
        )
        document.add_paragraph(self._(TOC_note), style='Text_body')

        # Note that the template already has an Title 1 called Introduction
        for paragraph in INTRO_PARAGRAPHS:
            document.add_paragraph(self._(paragraph)).style = 'Text_body'

        document.add_paragraph(self._("Tests Development"), style='Title_1')
        document.add_paragraph(self._(TESTS_DEVELOPMENT_TEXT), style='Text_body')

    def _add_design_point(self, document, design_point):
        """
        Add design point section to the document.

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        equipment_description : dict
            Dictionary containing equipment details.
        """
        table_font = "Consolas"
        width = Inches(2)
        if design_point:
            data = design_point.fluid.__dict__ | design_point.__dict__
            del data["fluid"]
            document.add_paragraph(self._(" "), style='Text_body')
            document.add_paragraph(self._('Design Point data:'), style='Text_body')
            table = document.add_table(rows=len(data), cols=2)
            table.style = "Table Grid"
            table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            for row, (key, value) in enumerate(data.items()):
                cell_left = table.cell(row, 0)
                cell_rigth = table.cell(row, 1)
                cell_left.text = self._(key.replace("_", " ").title()) if key != "name" else self._("Service")
                cell_rigth.text = value if isinstance(value, str) else f"{_nf(value, '0.02f~P')}"
                cell_left.width = width
                cell_rigth.width = width
                run_left =  cell_left.paragraphs[0].runs[0]
                run_rigth =  cell_rigth.paragraphs[0].runs[0]
                run_left.bold = True  # Make title row boldface
                run_left.font.size = Pt(9)  # Set font size
                run_rigth.font.size = Pt(8)  # Set font size
                run_left.font.name = table_font  # Use fixed-spacing font
                run_rigth.font.name = table_font  # Use fixed-spacing font

    def _add_equipment_description(self, document, equipment_description):
        """
        Add equipment description section to the document.

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        equipment_description : dict
            Dictionary containing equipment details.
        """
        table_font = "Consolas"
        width = Inches(2)
        if equipment_description:
            document.add_paragraph(self._('Equipment Description'), style='Title_2')
            document.add_paragraph(self._(EQUIPMENT_TEXT), style='Text_body')
            table = document.add_table(rows=len(equipment_description), cols=2)
            table.style = "Table Grid"
            table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            for row, (key, value) in enumerate(equipment_description.items()):
                cell_left = table.cell(row, 0)
                cell_rigth = table.cell(row, 1)
                cell_left.text = self._(key)
                cell_rigth.text = value
                cell_left.width = width
                cell_rigth.width = width
                run_left =  cell_left.paragraphs[0].runs[0]
                run_rigth =  cell_rigth.paragraphs[0].runs[0]
                run_left.bold = True  # Make title row boldface
                run_left.font.size = Pt(9)  # Set font size
                run_rigth.font.size = Pt(8)  # Set font size
                run_left.font.name = table_font  # Use fixed-spacing font
                run_rigth.font.name = table_font  # Use fixed-spacing font

    def _add_test_summary(self, document, test_summary, acceptance=None):
        """
        Add test summary section to the document.

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        test_summary : dict
            Dictionary containing test results and observations.
        acceptance : dict, optional
            ``{"label": str, "verified": bool, "unverified": list}`` describing
            the acceptance criteria used; drives the standard sentence and the
            "not yet verified" note.
        """
        table_font = "Consolas"
        width = Inches(1.25)
        if test_summary:
            document.add_paragraph(self._('Performance test summary.'), style='Title_3')
            document.add_paragraph(standard_sentence(self._, acceptance), style='Text_body')
            document.add_paragraph(self._(API_PARAGRAPH), style="Intense Quote")
            document.add_paragraph(self._("Calculated Head and Power:"), style='Text_body')
            table = document.add_table(rows=len(test_summary) + 1, cols=4)
            table.style = "Table Grid"
            table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            # Fill the first column with row names
            col_names = list(SUMMARY_COLUMNS)


            for col, name in enumerate(col_names):
                cell = table.cell(0, col)
                cell.text = self._(name)
                cell.width = width
                run =  cell.paragraphs[0].runs[0]
                run.bold = True  # Make title row boldface
                run.font.size = Pt(9)  # Set font size
                run.font.name = table_font  # Use fixed-spacing font

                if col != 0:
                    table.cell(0, col).paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            for row, (parameter, value) in enumerate(test_summary.items(), start=1):
                cell_left = table.cell(row, 0)
                cell_left.text = self._(parameter)
                cell_left.width = width
                run =  cell_left.paragraphs[0].runs[0]
                # run.bold = True  # Make title row boldface
                run.font.size = Pt(8)  # Set font size
                run.font.name = table_font  # Use fixed-spacing font

                if isinstance(value, list):  # If value is a list
                    actual, min_val, max_val = value if len(value) == 3 else [value[0], "-", "-"]
                else:
                    actual, min_val, max_val = value, "-", "-"

                for col, text in enumerate([actual, min_val, max_val], start=1):
                    cell = table.cell(row, col)
                    cell.text = f"{_nf(text, '0.02f~P')}" if text != "-" else text
                    cell.width = width
                    run = cell.paragraphs[0].runs[0]
                    run.font.size = Pt(8)  # Set font size
                    run.font.name = table_font  # Use fixed-spacing font
                    cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            note = unverified_sentence(self._, acceptance)
            if note:
                document.add_paragraph(note, style='Text_body')

    def _add_test_data(self, document, test_data):
        """
        Add test data section to the document.

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        test_data : dict
            Dictionary containing test results and observations.
        """
        table_font = "Consolas"
        if test_data:
            document.add_paragraph(" ", style='Text_body')
            document.add_paragraph(self._(TEST_DATA_DESCRIPTION), style='Text_body')

            table = document.add_table(rows=len(test_data["Capacity"]) + 1, cols=len(test_data))
            table.style = "Table Grid"
            table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            # Fill the first column with row names
            col_names = list(test_data.keys())

            width = Inches(1.25)
            for col, name in enumerate(col_names):
                upper_cell = table.cell(0, col)
                upper_cell.text = self._(name)
                upper_cell.width = width
                run = upper_cell.paragraphs[0].runs[0]
                run.bold = True  # Make title row boldface
                run.font.size = Pt(9)  # Set font size
                run.font.name = table_font  # Use fixed-spacing font
                upper_cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

                for row, value in enumerate(test_data[name], start=1):
                    cell = table.cell(row, col)
                    cell.text = f"{_nf(value, '0.02f~P')}"
                    cell.width = width
                    run = cell.paragraphs[0].runs[0]
                    run.font.size = Pt(8)  # Set font size
                    run.font.name = table_font  # Use fixed-spacing font
                    cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER


    def _add_chart(self, document, chart_title, chart):
        """
        Add charts to the document.

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        charts : dict
            Dictionary containing charts in file paths or bytes format.
        """
        width = Inches(6)
        height = Inches(6)
        document.add_paragraph(self._(chart_title), style='Title_3')
        paragraph = document.add_paragraph()
        run = paragraph.add_run()
        if isinstance(chart, str) and os.path.exists(chart):  # File path
            run.add_picture(chart,
                            width=width,
                            height=height)
        elif isinstance(chart, io.BytesIO):  # In-memory buffer
            run.add_picture(chart,
                            width=width,
                            height=height)
        paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    def _add_mechanical_run(self, document, entry):
        """
        Add the mechanical running test section (UC-11).

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        entry : dict
            ``{"result": MechanicalRunResult, "plot": BytesIO}``.
        """
        result = (entry or {}).get("result")
        if result is None:
            return
        table_font = "Consolas"
        document.add_paragraph(self._(MECHANICAL_RUN_TITLE), style='Title_3')
        document.add_paragraph(mechanical_run_duration_sentence(self._, result), style='Text_body')
        document.add_paragraph(
            f"{self._('Overall verdict')}: {mechanical_run_verdict(self._, result)}",
            style='Text_body',
        )

        header, rows = mechanical_run_table(self._, result)
        table = document.add_table(rows=len(rows) + 1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        width = Inches(1.0)
        for col, name in enumerate(header):
            cell = table.cell(0, col)
            cell.text = name
            cell.width = width
            run = cell.paragraphs[0].runs[0]
            run.bold = True
            run.font.size = Pt(9)
            run.font.name = table_font
            if col != 0:
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        for r, values in enumerate(rows, start=1):
            for col, text in enumerate(values):
                cell = table.cell(r, col)
                cell.text = text
                cell.width = width
                run = cell.paragraphs[0].runs[0]
                run.font.size = Pt(8)
                run.font.name = table_font
                if col != 0:
                    cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        plot = (entry or {}).get("plot")
        if isinstance(plot, io.BytesIO) or (isinstance(plot, str) and os.path.exists(plot)):
            paragraph = document.add_paragraph()
            paragraph.add_run().add_picture(plot, width=Inches(6))
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        for note in mechanical_run_notes(self._, result):
            document.add_paragraph(note, style='Text_body')

    def _add_npsh(self, document, entry):
        """
        Add the NPSH section (UC-05).

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        entry : dict
            ``{"result": NPSHResult, "plot": BytesIO | None,
            "table": [(q, npshr), ...]}``.
        """
        result = (entry or {}).get("result")
        if result is None:
            return
        table_font = "Consolas"
        document.add_paragraph(self._(NPSH_TITLE), style='Title_3')

        rows = npsh_summary_rows(self._, result)
        table = document.add_table(rows=len(rows), cols=2)
        table.style = "Table Grid"
        table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        width = Inches(2)
        for r, (label, value) in enumerate(rows):
            left, right = table.cell(r, 0), table.cell(r, 1)
            left.text, right.text = label, value
            left.width = right.width = width
            run_left = left.paragraphs[0].runs[0]
            run_right = right.paragraphs[0].runs[0]
            run_left.bold = True
            run_left.font.size = Pt(9)
            run_right.font.size = Pt(8)
            run_left.font.name = table_font
            run_right.font.name = table_font

        points = (entry or {}).get("table")
        if points:
            header, prows = npsh_points_table(self._, points)
            document.add_paragraph(" ", style='Text_body')
            ptable = document.add_table(rows=len(prows) + 1, cols=len(header))
            ptable.style = "Table Grid"
            ptable.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            for col, name in enumerate(header):
                cell = ptable.cell(0, col)
                cell.text = name
                cell.width = width
                run = cell.paragraphs[0].runs[0]
                run.bold = True
                run.font.size = Pt(9)
                run.font.name = table_font
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            for r, values in enumerate(prows, start=1):
                for col, text in enumerate(values):
                    cell = ptable.cell(r, col)
                    cell.text = text
                    cell.width = width
                    run = cell.paragraphs[0].runs[0]
                    run.font.size = Pt(8)
                    run.font.name = table_font
                    cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        plot = (entry or {}).get("plot")
        if isinstance(plot, io.BytesIO):
            plot.seek(0)
        if isinstance(plot, io.BytesIO) or (isinstance(plot, str) and os.path.exists(plot)):
            paragraph = document.add_paragraph()
            paragraph.add_run().add_picture(plot, width=Inches(6))
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    def _add_comparison(self, document, comparison):
        """
        Add the pump comparison section (UC-08).

        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        comparison : dict
            ``{"table": ComparisonTable, "plot": BytesIO, "at": [...]}``.
        """
        if not comparison or comparison.get("table") is None:
            return
        table_font = "Consolas"
        document.add_paragraph(self._(COMPARISON_TITLE), style='Title_2')
        document.add_paragraph(comparison_sentence(self._, comparison), style='Text_body')

        header, rows = comparison_table(self._, comparison)
        table = document.add_table(rows=len(rows) + 1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        width = Inches(0.9)
        for col, name in enumerate(header):
            cell = table.cell(0, col)
            cell.text = name
            cell.width = width
            run = cell.paragraphs[0].runs[0]
            run.bold = True
            run.font.size = Pt(9)
            run.font.name = table_font
            cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        for r, values in enumerate(rows, start=1):
            for col, text in enumerate(values):
                cell = table.cell(r, col)
                cell.text = text
                cell.width = width
                run = cell.paragraphs[0].runs[0]
                run.font.size = Pt(8)
                run.font.name = table_font
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        plot = comparison.get("plot")
        if isinstance(plot, io.BytesIO):
            plot.seek(0)
        if isinstance(plot, io.BytesIO) or (isinstance(plot, str) and os.path.exists(plot)):
            paragraph = document.add_paragraph()
            paragraph.add_run().add_picture(plot, width=Inches(6))
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
