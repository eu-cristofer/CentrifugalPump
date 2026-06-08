"""
style
=====

Global Qt stylesheet — a clean, calm, professional desktop look in an industrial
blue/steel key on a light background.
"""

APP_QSS = """
QMainWindow, QWidget { background: #eef1f4; color: #28323d;
    font-family: "Segoe UI", "Inter", system-ui, sans-serif; font-size: 13px; }

/* ---- toolbar / menu ---- */
QToolBar { background: #ffffff; border-bottom: 1px solid #d3dae2; spacing: 6px; padding: 5px 8px; }
QToolBar QToolButton { padding: 6px 10px; border-radius: 6px; color: #28323d; }
QToolBar QToolButton:hover { background: #e7ecf2; }
QMenuBar { background: #ffffff; border-bottom: 1px solid #d3dae2; }
QMenuBar::item:selected { background: #e7ecf2; }
QMenu { background: #ffffff; border: 1px solid #c3ccd6; }
QMenu::item:selected { background: #eaf1f8; color: #1f4f7a; }
QStatusBar { background: #ffffff; border-top: 1px solid #d3dae2; color: #5a6573; }

/* ---- toolbox dock ---- */
QDockWidget { titlebar-close-icon: none; color: #5a6573; font-size: 11px; }
QDockWidget::title { background: #e4e9ef; padding: 6px 10px; }
#Toolbox { background: #f4f6f9; }
#ToolboxItem { text-align: left; padding: 9px 12px; border: 1px solid #d3dae2;
    border-radius: 8px; background: #ffffff; margin: 3px 8px; color: #28323d; }
#ToolboxItem:hover { border-color: #2f6fb0; background: #f6faff; }

/* ---- dialogs ---- */
#PropertyDialog { background: #ffffff; }
#DialogHeader { background: #2b3a4a; }
#DialogTitle { color: #ffffff; }
#DialogSubtitle { color: #c4d0db; font-size: 12px; }
#SectionLabel { color: #5b7185; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
#FieldLabel { color: #3c4753; }
#UnitLabel { color: #8a96a3; font-size: 12px; }
#HLine { color: #e3e8ee; background: #e3e8ee; max-height: 1px; border: none; }

QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background: #ffffff; border: 1px solid #c3ccd6; border-radius: 6px;
    padding: 5px 8px; selection-background-color: #cfe2f5; }
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus { border-color: #2f6fb0; }
QComboBox::drop-down { border: none; width: 18px; }
QCheckBox { color: #3c4753; spacing: 7px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #b6c0cb;
    border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { background: #2f6fb0; border-color: #2f6fb0; }

/* ---- buttons ---- */
#ToolButton { background: #eef2f6; border: 1px solid #c8d1da; border-radius: 6px;
    padding: 6px 12px; color: #2b3a4a; }
#ToolButton:hover { background: #e2e9f0; border-color: #2f6fb0; }
#PrimaryButton { background: #2f6fb0; border: 1px solid #2a64a0; border-radius: 6px;
    padding: 7px 16px; color: #ffffff; font-weight: 600; }
#PrimaryButton:hover { background: #2a64a0; }

/* ---- tables ---- */
QTableWidget { background: #ffffff; border: 1px solid #d3dae2; border-radius: 8px;
    gridline-color: #e6ebf0; selection-background-color: #dcebfb; selection-color: #1f4f7a; }
QHeaderView::section { background: #eef2f6; color: #5b7185; border: none;
    border-right: 1px solid #e0e6ec; border-bottom: 1px solid #d3dae2; padding: 6px 8px; font-weight: 600; }
QTableWidget::item { padding: 4px 6px; }

/* ---- banners ---- */
#Banner { border-radius: 7px; padding: 8px 12px; font-size: 12px; }
#Banner[kind="info"] { background: #eef2f6; color: #44566a; }
#Banner[kind="ok"]   { background: #e3f1ea; color: #1f6b4c; }
#Banner[kind="warn"] { background: #fbf1de; color: #8a6116; }
#Banner[kind="error"]{ background: #f8e4e2; color: #9a3a34; }

/* ---- compliance verdict ---- */
#VerdictBanner { border-radius: 9px; padding: 14px 18px; font-size: 18px; }
#VerdictBanner[verdict="pass"] { background: #e3f1ea; color: #1f6b4c; border: 1px solid #bfe0cd; }
#VerdictBanner[verdict="fail"] { background: #f8e4e2; color: #9a3a34; border: 1px solid #ecc6c1; }
#VerdictBanner[verdict="idle"] { background: #eef2f6; color: #6b7785; border: 1px solid #d8e0e8; }

/* ---- mono blocks (coeffs / pump list) ---- */
#MonoBlock { font-family: "Consolas", "Menlo", monospace; font-size: 12px;
    background: #f6f8fa; border: 1px solid #e3e8ee; border-radius: 7px; padding: 10px 12px; color: #33414f; }

QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar::handle:vertical { background: #c4cdd7; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #aab6c2; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c4cdd7; border-radius: 5px; min-width: 28px; }

/* ---- welcome / splash dialog ---- */
#WelcomeDialog { background: #ffffff; border: 1px solid #c3ccd6; border-radius: 10px; }
#WelcomeHeader { background: #2b3a4a; border-radius: 9px 9px 0 0; }
#WelcomeTitle { color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: 0.3px; }
#WelcomeSubtitle { color: #c4d0db; font-size: 12px; }
#WelcomeContent { background: #f4f6f9; }
#WelcomePanel { background: #f4f6f9; }
#WelcomeSectionLabel { color: #5b7185; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; }
#WelcomePlaceholder { color: #a0aab4; font-size: 12px; font-style: italic; padding: 4px 0; }
#WelcomeDivider { color: #d3dae2; background: #d3dae2; max-width: 1px; border: none; }
#WelcomeFooter { background: #ffffff; border-top: 1px solid #d3dae2; border-radius: 0 0 9px 9px; }
#ExampleDesc { color: #8a96a3; font-size: 11px; padding: 0 4px 2px 4px; }

/* Recent-file and example row buttons */
#RecentItem { text-align: left; padding: 7px 10px; border: 1px solid #d3dae2;
    border-radius: 7px; background: #ffffff; color: #28323d; }
#RecentItem:hover { border-color: #2f6fb0; background: #f0f6ff; color: #1f4f7a; }
#ExampleItem { text-align: left; padding: 7px 10px; border: 1px solid #d3dae2;
    border-radius: 7px; background: #ffffff; color: #28323d; font-weight: 600; }
#ExampleItem:hover { border-color: #2f6fb0; background: #f0f6ff; color: #1f4f7a; }
"""
