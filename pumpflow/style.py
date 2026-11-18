"""
style
=====

Global Qt stylesheet — a clean, calm, professional desktop look in an industrial
blue/steel key on a light background.

:data:`APP_QSS` is a template: ``@token`` and ``@fs-<text style>`` name entries
of the design system (:mod:`pump.design`, ``pump/design/tokens.json``) and are
filled in by :func:`app_qss`.  Never write a colour, radius or font size here.
"""

APP_QSS = """
QMainWindow, QWidget { background: @window-bg; color: @body-text;
    font-family: "__UI_FONT__"; font-size: @fs-body; }

/* ---- toolbar / menu ---- */
QToolBar { background: @surface; border-bottom: 1px solid @grid-dot; spacing: 6px; padding: 5px 8px; }
QToolBar QToolButton { padding: 6px 10px; border-radius: @radius-control; color: @body-text; }
QToolBar QToolButton:hover { background: @hover-bg; }
QMenuBar { background: @surface; border-bottom: 1px solid @grid-dot; }
QMenuBar::item:selected { background: @hover-bg; }
QMenu { background: @surface; border: 1px solid @border; }
QMenu::item:selected { background: @menu-selected-bg; color: @selected-text; }
QStatusBar { background: @surface; border-top: 1px solid @grid-dot; color: @subtle-text; }

/* ---- toolbox dock ---- */
QDockWidget { titlebar-close-icon: none; color: @subtle-text; font-size: @fs-caption; }
QDockWidget::title { background: @dock-title-bg; padding: 6px 10px; }
#Toolbox { background: @surface-sunken; }
#ToolboxItem { text-align: left; padding: 9px 12px; border: 1px solid @grid-dot;
    border-radius: @radius-card; background: @surface; margin: 3px 8px; color: @body-text; }
#ToolboxItem:hover { border-color: @accent; background: @toolbox-hover-bg; }
#ToolboxGroup { color: @steel; font-size: @fs-section-label; font-weight: bold;
    letter-spacing: 1px; padding: 10px 14px 2px 14px; background: transparent; }
#ToolboxScroll { background: @surface-sunken; }

/* ---- dialogs ---- */
#PropertyDialog { background: @surface; }
#DialogHeader { background: @title-bg; }
#DialogTitle { color: @title-text; background: transparent; }
#HeaderMaximize { color: @title-text; background: transparent; border: 1px solid @header-button-border;
    border-radius: @radius-control; padding: 3px 9px; font-size: @fs-subtitle; }
#HeaderMaximize:hover { background: @header-button-hover-bg; border-color: @header-button-hover-border; }
#DialogSubtitle { color: @header-subtitle; font-size: @fs-subtitle; background: transparent; }
#SectionLabel { color: @steel; font-size: @fs-section-label; font-weight: 700; letter-spacing: 1px; }
#FieldLabel { color: @field-label; }
#UnitLabel { color: @unit-label; font-size: @fs-unit; }
#HLine { color: @divider; background: @divider; max-height: 1px; border: none; }

QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background: @surface; border: 1px solid @control-border; border-radius: @radius-control;
    padding: @space-control-y @space-control-x; selection-background-color: @selection-bg; }
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus { border-color: @accent; }
QComboBox::drop-down { border: none; width: 18px; }
QCheckBox { color: @field-label; spacing: 7px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid @control-border;
    border-radius: @radius-check; background: @surface; }
QCheckBox::indicator:checked { background: @accent; border-color: @accent; image: url("__CHECK_MARK__"); }
QCheckBox:disabled { color: @disabled-text; }
QCheckBox::indicator:disabled { background: @disabled-bg; border-color: @disabled-border; }
QCheckBox::indicator:checked:disabled { background: @disabled-text; border-color: @disabled-text; }
QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled {
    background: @disabled-bg; color: @disabled-text; border-color: @disabled-border; }
#FieldLabel:disabled, #UnitLabel:disabled { color: @disabled-text; }

/* ---- buttons ---- */
#ToolButton { background: @surface-muted; border: 1px solid @border-tool-button; border-radius: @radius-control;
    padding: 6px 12px; color: @tool-button-text; }
#ToolButton:hover { background: @tool-button-hover-bg; border-color: @accent; }
#PrimaryButton { background: @accent; border: 1px solid @accent-hover; border-radius: @radius-control;
    padding: 7px 16px; color: @title-text; font-weight: 600; }
#PrimaryButton:hover { background: @accent-hover; }

/* ---- tables ---- */
QTableWidget { background: @surface; border: 1px solid @grid-dot; border-radius: @radius-card;
    gridline-color: @gridline; selection-background-color: @table-selection-bg; selection-color: @selected-text; }
QHeaderView::section { background: @surface-muted; color: @steel; border: none;
    border-right: 1px solid @header-divider; border-bottom: 1px solid @grid-dot; padding: 6px 8px; font-weight: 600; }
QTableWidget::item { padding: 4px 6px; }

/* ---- banners ---- */
#Banner { border-radius: @radius-banner; padding: @space-control-x @space-banner-x; font-size: @fs-banner; }
#Banner[kind="info"] { background: @banner-info-bg; color: @banner-info-text; }
#Banner[kind="ok"]   { background: @banner-ok-bg; color: @banner-ok-text; }
#Banner[kind="warn"] { background: @banner-warn-bg; color: @banner-warn-text; }
#Banner[kind="error"]{ background: @banner-error-bg; color: @banner-error-text; }

/* ---- compliance verdict ---- */
#VerdictBanner { border-radius: @radius-node; padding: 14px @space-dialog-x; font-size: @fs-verdict; }
#VerdictBanner[verdict="pass"] { background: @banner-ok-bg; color: @banner-ok-text; border: 1px solid @banner-ok-border; }
#VerdictBanner[verdict="fail"] { background: @banner-error-bg; color: @banner-error-text; border: 1px solid @banner-error-border; }
#VerdictBanner[verdict="idle"] { background: @banner-info-bg; color: @verdict-idle-text; border: 1px solid @verdict-idle-border; }

/* ---- mono blocks (coeffs / pump list) ---- */
#MonoBlock { font-family: "__MONO_FONT__"; font-size: @fs-mono-block;
    background: @mono-bg; border: 1px solid @divider; border-radius: @radius-banner; padding: 10px 12px; color: @mono-text; }

QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar::handle:vertical { background: @scrollbar; border-radius: @radius-scrollbar; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: @scrollbar-hover; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: @scrollbar; border-radius: @radius-scrollbar; min-width: 28px; }

/* ---- welcome / splash dialog ---- */
#WelcomeDialog { background: @surface; border: 1px solid @border; border-radius: @radius-welcome; }
#WelcomeHeader { background: @title-bg; }
#WelcomeTitle { color: @title-text; font-size: @fs-welcome-title; font-weight: 700; letter-spacing: 0.3px; background: transparent; }
#WelcomeSubtitle { color: @header-subtitle; font-size: @fs-subtitle; background: transparent; }
#WelcomeContent { background: @surface-sunken; }
#WelcomePanel { background: @surface-sunken; }
#WelcomeSectionLabel { color: @steel; font-size: @fs-welcome-section-label; font-weight: 700; letter-spacing: 1.2px; }
#WelcomePlaceholder { color: @placeholder; font-size: @fs-unit; font-style: italic; padding: 4px 0; }
#WelcomeDivider { color: @grid-dot; background: @grid-dot; max-width: 1px; border: none; }
#WelcomeFooter { background: @surface; border-top: 1px solid @grid-dot; }
#ExampleDesc { color: @unit-label; font-size: @fs-caption; padding: 0 4px 2px 4px; }

/* Recent-file and example row buttons */
#RecentItem { text-align: left; padding: 7px 10px; border: 1px solid @grid-dot;
    border-radius: @radius-banner; background: @surface; color: @body-text; }
#RecentItem:hover { border-color: @accent; background: @row-hover-bg; color: @selected-text; }
#ExampleItem { text-align: left; padding: 7px 10px; border: 1px solid @grid-dot;
    border-radius: @radius-banner; background: @surface; color: @body-text; font-weight: 600; }
#ExampleItem:hover { border-color: @accent; background: @row-hover-bg; color: @selected-text; }
"""


# ---------------------------------------------------------------------------
# Fonts
#
# "Segoe UI" only exists on Windows; requesting a missing family forces Qt to
# build its font-alias table (the slow "Populating font family aliases" warning
# on macOS/Linux). We resolve a family that actually exists *once* at startup so
# no missing family is ever requested.
# ---------------------------------------------------------------------------

# Preference order: the Windows default, then good cross-platform faces.
_UI_FONT_PREFS = ("Segoe UI", "Inter", "Helvetica Neue", "Arial", "Sans Serif")
_MONO_FONT_PREFS = ("Consolas", "Menlo", "DejaVu Sans Mono", "Courier New", "Monospace")

# Resolved at startup by init_fonts(); fall back to the first preference until then.
_UI_FAMILY = _UI_FONT_PREFS[0]
_MONO_FAMILY = _MONO_FONT_PREFS[0]


def _first_available(prefs: tuple[str, ...]) -> str:
    """Return the first installed family from ``prefs`` (last as a fallback).

    Requires a live QApplication (QFontDatabase needs one), so call from run().
    """
    from PySide6.QtGui import QFontDatabase

    available = set(QFontDatabase.families())
    for fam in prefs:
        if fam in available:
            return fam
    return prefs[-1]


def resolve_ui_family() -> str:
    """Return the first preferred UI font that is actually installed."""
    return _first_available(_UI_FONT_PREFS)


def resolve_mono_family() -> str:
    """Return the first preferred monospace font that is actually installed."""
    return _first_available(_MONO_FONT_PREFS)


def init_fonts(app) -> None:
    """Resolve the UI/mono families and make the UI one the app default font."""
    global _UI_FAMILY, _MONO_FAMILY
    _UI_FAMILY = resolve_ui_family()
    _MONO_FAMILY = resolve_mono_family()
    f = app.font()
    f.setFamily(_UI_FAMILY)
    app.setFont(f)


def qcolor(name: str):
    """A ``QColor`` for a colour token of :mod:`pump.design` (alpha kept)."""
    from PySide6.QtGui import QColor

    from pump.design import rgba

    r, g, b, a = rgba(name)
    return QColor(r, g, b, round(a * 255))


def _px_to_pt(qss: str, dpi: float) -> str:
    """Rewrite every ``font-size: Npx`` as points at ``dpi`` logical DPI.

    A font set in pixels has ``pointSize() == -1``.  On Windows, Qt's native
    style copies that point size into new fonts and warns ``QFont::setPointSize:
    Point size <= 0 (-1)``.  Points at the screen's logical DPI keep the same
    on-screen size: 0.75 pt/px on Windows (96 DPI), 1 pt/px on macOS (72 DPI).

    >>> _px_to_pt("QWidget { font-size: 13px; }", 96)
    'QWidget { font-size: 9.75pt; }'
    >>> _px_to_pt("#T { font-size: 20px; }", 72)
    '#T { font-size: 20pt; }'
    """
    import re

    factor = 72.0 / (dpi if dpi and dpi > 0 else 96.0)
    return re.sub(
        r"font-size:\s*(\d+(?:\.\d+)?)px",
        lambda m: f"font-size: {round(float(m.group(1)) * factor, 2):g}pt",
        qss,
    )


def _logical_dpi() -> float:
    from PySide6.QtGui import QGuiApplication

    screen = QGuiApplication.primaryScreen()
    return float(screen.logicalDotsPerInchY()) if screen is not None else 96.0


_CHECK_MARK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
    '<path d="M3.5 8.4 6.6 11.3 12.5 4.8" fill="none" stroke="{ink}" '
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def check_mark_path() -> str:
    """Path of the checked-checkbox tick (an SVG in the ``check-mark`` token colour).

    A Qt stylesheet can only draw the tick from an image file, so the SVG is
    written once to the temp directory, named after its colour, and referenced
    with forward slashes (Qt's ``url()`` wants them on Windows too).
    """
    import tempfile
    from pathlib import Path

    from pump.design import color

    ink = color("check-mark")
    name = "pumpflow-check-" + "".join(c for c in ink if c.isalnum()) + ".svg"
    path = Path(tempfile.gettempdir()) / name
    try:
        if not path.exists():
            path.write_text(_CHECK_MARK_SVG.format(ink=ink), encoding="utf-8")
    except OSError:  # read-only temp: no tick, the accent fill still shows state
        return ""
    return path.as_posix()


def app_qss() -> str:
    """The global stylesheet with the resolved font families substituted in.

    Font sizes are written in px in :data:`APP_QSS` and handed to Qt in points
    (see :func:`_px_to_pt`), so no widget ends up with a pixel-sized font.
    """
    from pump.design import render

    qss = render(APP_QSS)
    qss = qss.replace("__UI_FONT__", _UI_FAMILY).replace("__MONO_FONT__", _MONO_FAMILY)
    qss = qss.replace("__CHECK_MARK__", check_mark_path())
    return _px_to_pt(qss, _logical_dpi())


def ui_font(size: int | None = None, weight=None):
    """A QFont in the resolved UI family — drop-in for QFont('Segoe UI', ...)."""
    from PySide6.QtGui import QFont

    f = QFont(_UI_FAMILY)
    f.setStyleHint(QFont.SansSerif)
    if size is not None:
        f.setPointSize(size)
    if weight is not None:
        f.setWeight(weight)
    return f


def mono_font(size: int | None = None, weight=None):
    """A QFont in the resolved monospace family — drop-in for QFont('Consolas', ...)."""
    from PySide6.QtGui import QFont

    f = QFont(_MONO_FAMILY)
    f.setStyleHint(QFont.Monospace)
    if size is not None:
        f.setPointSize(size)
    if weight is not None:
        f.setWeight(weight)
    return f
