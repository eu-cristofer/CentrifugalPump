"""
welcome
=======

Start-screen dialog shown on application launch.

Presents Recent Projects (persisted via :class:`PySide6.QtCore.QSettings`)
and bundled Example pipelines so the user can jump straight into meaningful
work without navigating the file system.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import pumpflow.examples as _ex_pkg

# Resolved once at import time; works from both source tree and installed wheel.
_EXAMPLES_DIR: Path = Path(_ex_pkg.__file__).parent

# (display title, one-line description, filename inside _EXAMPLES_DIR)
_BUNDLED: list[tuple[str, str, str]] = [
    (
        "Single Pump FAT — HC fluid",
        "Light hydrocarbon · SG 0.736 · 833 m³/h · 73 m",
        "single_pump_fat_hc.pumpflow",
    ),
    (
        "Curve & Report — Clean water",
        "Water · SG 1.0 · 400 m³/h · 100 m",
        "water_pump_curve_report.pumpflow",
    ),
    (
        "Performance Explorer — interactive",
        "Live Q×H/Q×P/Q×η · measured + fit + ad-hoc points",
        "explore_performance.pumpflow",
    ),
]

_MAX_RECENT: int = 5


# ------------------------------------------------------------------ helpers


def load_recent() -> list[str]:
    """
    Return the persisted recent-file paths, skipping any that no longer exist.

    Returns
    -------
    list of str
        Up to :data:`_MAX_RECENT` absolute path strings, most-recent first.
        Missing or unreadable paths are silently dropped.
    """
    raw = QSettings("PumpFlow", "PumpFlow").value("recentFiles", [])
    # QSettings may return a single str when only one value was stored.
    if isinstance(raw, str):
        raw = [raw]
    return [p for p in raw if Path(p).exists()]


def save_recent(path: Path) -> None:
    """
    Prepend *path* to the persisted recent-files list.

    Deduplicates and caps the list at :data:`_MAX_RECENT` entries.

    Parameters
    ----------
    path : Path
        Absolute path of the project file just opened or saved.
    """
    settings = QSettings("PumpFlow", "PumpFlow")
    raw = settings.value("recentFiles", [])
    if isinstance(raw, str):
        raw = [raw]
    s = str(path)
    recent = [r for r in raw if r != s]
    recent.insert(0, s)
    settings.setValue("recentFiles", recent[:_MAX_RECENT])


# ------------------------------------------------------------------ dialog


class WelcomeDialog(QDialog):
    """
    Splash / start-screen modal shown over the main window at launch.

    The caller reads :attr:`result_action`, :attr:`result_doc`, and
    :attr:`result_path` after ``exec()`` returns to decide how to
    initialise the canvas.

    Attributes
    ----------
    result_action : str
        One of ``"new"``, ``"open"``, or ``"skip"``.
    result_doc : dict or None
        Loaded project document when ``result_action == "open"``; ``None``
        otherwise.
    result_path : Path or None
        Source file path when the document came from a user-chosen file
        (recent or file-dialog pick).  ``None`` for bundled examples so
        the caller does not track them in the recent-files list.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WelcomeDialog")
        self.setWindowTitle("PumpFlow")
        self.setFixedSize(700, 460)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        # Initialise to "skip" so closing the window has the same effect.
        self.result_action: str = "skip"
        self.result_doc: dict | None = None
        self.result_path: Path | None = None

        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._make_header())
        root.addWidget(self._make_content(), stretch=1)
        root.addWidget(self._make_footer())

    def _make_header(self) -> QFrame:
        frame = QFrame(objectName="WelcomeHeader")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(32, 22, 32, 18)
        lay.setSpacing(4)
        lay.addWidget(QLabel("PumpFlow", objectName="WelcomeTitle"))
        lay.addWidget(
            QLabel(
                "API 610 Pump Performance Workbench — Factory Acceptance Test",
                objectName="WelcomeSubtitle",
            )
        )
        return frame

    def _make_content(self) -> QWidget:
        widget = QWidget(objectName="WelcomeContent")
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._make_recent_panel(), stretch=1)
        lay.addWidget(self._make_vdivider())
        lay.addWidget(self._make_examples_panel(), stretch=1)
        return widget

    def _make_recent_panel(self) -> QWidget:
        """
        Build the left column listing the most recently opened projects.

        Notes
        -----
        Each entry is a flat :class:`QPushButton` whose click immediately
        loads the corresponding file via :meth:`_pick_file`.  Entries for
        paths that no longer exist are silently omitted by :func:`load_recent`.
        """
        panel = QWidget(objectName="WelcomePanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(28, 20, 18, 16)
        lay.setSpacing(5)
        lay.addWidget(QLabel("RECENT PROJECTS", objectName="WelcomeSectionLabel"))
        lay.addSpacing(6)

        recent = load_recent()
        if recent:
            for path_str in recent:
                btn = QPushButton(Path(path_str).name, objectName="RecentItem")
                btn.setToolTip(path_str)
                btn.clicked.connect(
                    lambda _=False, p=path_str: self._pick_file(Path(p))
                )
                lay.addWidget(btn)
        else:
            lay.addWidget(
                QLabel("No recent projects", objectName="WelcomePlaceholder")
            )

        lay.addStretch(1)
        return panel

    def _make_examples_panel(self) -> QWidget:
        """
        Build the right column listing bundled example pipelines.

        Only examples whose ``.pumpflow`` file actually exists on disk are
        shown, so a partial install does not surface broken entries.
        """
        panel = QWidget(objectName="WelcomePanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(18, 20, 28, 16)
        lay.setSpacing(5)
        lay.addWidget(QLabel("EXAMPLES", objectName="WelcomeSectionLabel"))
        lay.addSpacing(6)

        for title, description, filename in _BUNDLED:
            ex_path = _EXAMPLES_DIR / filename
            if not ex_path.exists():
                continue
            # Button row
            btn = QPushButton(title, objectName="ExampleItem")
            btn.clicked.connect(lambda _=False, p=ex_path: self._pick_example(p))
            lay.addWidget(btn)
            # Subdued description beneath the button
            desc = QLabel(description, objectName="ExampleDesc")
            lay.addWidget(desc)
            lay.addSpacing(4)

        lay.addStretch(1)
        return panel

    @staticmethod
    def _make_vdivider() -> QFrame:
        line = QFrame(objectName="WelcomeDivider")
        line.setFrameShape(QFrame.VLine)
        return line

    def _make_footer(self) -> QFrame:
        frame = QFrame(objectName="WelcomeFooter")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(28, 14, 28, 18)
        lay.setSpacing(10)

        btn_new = QPushButton("New empty canvas", objectName="PrimaryButton")
        btn_new.clicked.connect(self._choose_new)

        btn_open = QPushButton("Open file…", objectName="ToolButton")
        btn_open.clicked.connect(self._open_file_dialog)

        btn_skip = QPushButton("Skip", objectName="ToolButton")
        btn_skip.clicked.connect(self.reject)

        lay.addWidget(btn_new)
        lay.addStretch(1)
        lay.addWidget(btn_open)
        lay.addWidget(btn_skip)
        return frame

    # ---------------------------------------------------------------- slots

    def _choose_new(self) -> None:
        self.result_action = "new"
        self.accept()

    def _pick_file(self, path: Path) -> None:
        """
        Load a project from *path* and accept the dialog.

        Parameters
        ----------
        path : Path
            Absolute path to a ``.pumpflow`` JSON file.  If reading fails the
            dialog stays open silently — the user can choose another option.
        """
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.result_action = "open"
        self.result_doc = doc
        self.result_path = path
        self.accept()

    def _pick_example(self, path: Path) -> None:
        """
        Load a bundled example from *path* and accept the dialog.

        Unlike :meth:`_pick_file`, ``result_path`` is left as ``None`` so
        the caller does not add a bundled example to the recent-files list.

        Parameters
        ----------
        path : Path
            Absolute path to a bundled ``.pumpflow`` file inside
            :data:`_EXAMPLES_DIR`.
        """
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.result_action = "open"
        self.result_doc = doc
        self.result_path = None   # intentionally None — examples are not "recent"
        self.accept()

    def _open_file_dialog(self) -> None:
        """Open a system file-picker and load the chosen project."""
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open project",
            "",
            "PumpFlow (*.pumpflow);;JSON (*.json)",
        )
        if path_str:
            self._pick_file(Path(path_str))
