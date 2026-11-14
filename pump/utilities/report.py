import gettext
import locale
from typing import Callable, Optional
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import os
from datetime import datetime
import io
from pathlib import Path


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
    "The computations in this section were performed in accordancy with API 610 12th issue:"
)
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
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error:
            print("Warning: Unable to set locale, using default.")

        if self.locale_dir:
            locale_dir = self.locale_dir
        else:
            locale_dir = Path(__file__).parent / "locales"

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

    def _get_template_path(self):
        """
        Retrieve the appropriate template file based on the selected language.
        
        Returns
        -------
        str
            The full path to the template file.
        
        Raises
        ------
        FileNotFoundError
            If the specified template file is not found.
        """
        if self.template_path:
            if not os.path.exists(self.template_path):
                raise FileNotFoundError(f"Template file not found: {self.template_path}")
            return self.template_path
        else:
            template_file = f"template_{self.language}.docx"
            template_path = Path(__file__).parents[1] / "templates" / template_file
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template file not found: {template_path}")
            return template_path

    def generate_report(self, report_data, output_file=None):
        """
        Generates a report from a predefined template.

        Parameters
        ----------
        report_data : dict
            Dictionary containing all necessary report information.
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

        self._add_intro(document)
        self._add_equipment_description(document, report_data.get("equipment_description", {}))
        self._add_design_point(document, report_data.get("design_point", {}))
        for tag, test_data in report_data["test_data"].items():
            document.add_paragraph(self._('Test Data - ') + tag, style='Title_2')
            if "verdict" in test_data:
                verdict = self._("APPROVED") if test_data["verdict"] else self._("NOT APPROVED")
                document.add_paragraph(f"{self._('Overall verdict')}: {verdict}", style='Text_body')
            self._add_test_summary(document, test_data.get("test_summary", {}))
            self._add_test_data(document, test_data.get("test_data", {}))

            # Adding  charts, if any.
            search_key = 'Curve'
            matches = [key for key in test_data.keys() if search_key in key]

            for chart in matches:
                self._add_chart(document, chart, test_data[chart])

        document.save(output_file)
        print(f"{self._('New document saved at')}: {output_file}")
        return output_file

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
                cell_rigth.text = value if isinstance(value, str) else f"{value:0.02f~P}"
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

    def _add_test_summary(self, document, test_summary):
        """
        Add test summary section to the document.
        
        Parameters
        ----------
        document : docx.Document
            The Word document object to modify.
        test_summary : dict
            Dictionary containing test results and observations.
        """
        table_font = "Consolas"
        width = Inches(1.25)
        if test_summary:
            document.add_paragraph(self._('Performance test summary.'), style='Title_3')
            document.add_paragraph(self._(TEST_SUMMARY_DESCRIPTION), style='Text_body')
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
                    cell.text = f"{text:0.02f~P}" if text != "-" else text
                    cell.width = width
                    run = cell.paragraphs[0].runs[0]
                    run.font.size = Pt(8)  # Set font size
                    run.font.name = table_font  # Use fixed-spacing font
                    cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

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
                    cell.text = f"{value:0.02f~P}"
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

