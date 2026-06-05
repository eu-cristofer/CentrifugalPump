"""
nodes.ui
========

Small reusable building blocks for the widget property dialogs — a styled
dialog shell, labelled form rows, and a validation banner — so each node's
dialog stays short and consistent (UI_SPEC §5: "double-click-to-open property
dialog", left settings pane + main area).
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)


class PropertyDialog(QDialog):
    """A consistent shell: header, a body you fill, and live-apply semantics."""

    def __init__(self, parent, title: str, subtitle: str = "", width: int = 460):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.setObjectName("PropertyDialog")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget(objectName="DialogHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 14, 18, 12)
        hl.setSpacing(2)
        t = QLabel(title, objectName="DialogTitle")
        f = QFont("Segoe UI", 12, QFont.DemiBold)
        t.setFont(f)
        hl.addWidget(t)
        if subtitle:
            s = QLabel(subtitle, objectName="DialogSubtitle")
            s.setWordWrap(True)
            hl.addWidget(s)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(18, 14, 18, 16)
        self.body_layout.setSpacing(12)
        scroll.setWidget(self.body)
        outer.addWidget(scroll, 1)

    def add(self, widget: QWidget) -> QWidget:
        self.body_layout.addWidget(widget)
        return widget


class Banner(QLabel):
    """A status / validation chip (UI_SPEC §7)."""

    def __init__(self, text: str = "", kind: str = "info"):
        super().__init__(text)
        self.setWordWrap(True)
        self.set_kind(kind)
        self.setVisible(bool(text))

    def set_kind(self, kind: str) -> None:
        self.setProperty("kind", kind)
        self.setObjectName("Banner")
        self.style().unpolish(self)
        self.style().polish(self)

    def show_message(self, text: str, kind: str = "info") -> None:
        self.setText(text)
        self.set_kind(kind)
        self.setVisible(bool(text))


def section(title: str) -> QLabel:
    lbl = QLabel(title.upper(), objectName="SectionLabel")
    return lbl


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setObjectName("HLine")
    return line


def row(label: str, widget: QWidget, suffix: str = "") -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    lab = QLabel(label, objectName="FieldLabel")
    lab.setMinimumWidth(150)
    h.addWidget(lab)
    h.addWidget(widget, 1)
    if suffix:
        unit = QLabel(suffix, objectName="UnitLabel")
        unit.setMinimumWidth(48)
        h.addWidget(unit)
    return w


def line_edit(value: str, on_change: Optional[Callable] = None,
              placeholder: str = "") -> QLineEdit:
    le = QLineEdit(str(value) if value is not None else "")
    if placeholder:
        le.setPlaceholderText(placeholder)
    if on_change:
        le.textChanged.connect(lambda _=None: on_change())
    return le


def spin(value: float, lo: float, hi: float, step: float = 1.0,
         decimals: int = 2, on_change: Optional[Callable] = None) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(lo, hi)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    sb.setValue(float(value) if value is not None else 0.0)
    sb.setKeyboardTracking(False)
    if on_change:
        sb.valueChanged.connect(lambda _=None: on_change())
    return sb


def int_spin(value: int, lo: int, hi: int, on_change: Optional[Callable] = None) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(lo, hi)
    sb.setValue(int(value))
    sb.setKeyboardTracking(False)
    if on_change:
        sb.valueChanged.connect(lambda _=None: on_change())
    return sb


def combo(options, value, on_change: Optional[Callable] = None) -> QComboBox:
    cb = QComboBox()
    for label, data in options:
        cb.addItem(label, data)
    idx = cb.findData(value)
    if idx >= 0:
        cb.setCurrentIndex(idx)
    if on_change:
        cb.currentIndexChanged.connect(lambda _=None: on_change())
    return cb


def checkbox(text: str, value: bool, on_change: Optional[Callable] = None) -> QCheckBox:
    cb = QCheckBox(text)
    cb.setChecked(bool(value))
    if on_change:
        cb.toggled.connect(lambda _=None: on_change())
    return cb
