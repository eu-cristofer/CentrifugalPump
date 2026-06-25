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
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import units as _units


class PropertyDialog(QDialog):
    """A consistent shell: header, a body you fill, and live-apply semantics."""

    def __init__(self, parent, title: str, subtitle: str = "", width: int = 460):
        super().__init__(parent)
        # An independent (modeless) tool window with its own min/restore/close,
        # so the canvas and menus stay usable while it is open.
        self.setWindowFlag(Qt.Window, True)
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
        self._header = header

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

    def fit_to_contents(self) -> None:
        """Resize the window to fit header + body preferred size (opt-in).

        Used by dialogs whose content changes height (e.g. the Fluid node showing
        a chart only in Water mode) so the window grows/shrinks to fit instead of
        scrolling or leaving dead space.  Clamped to the available screen.
        """
        self.body.adjustSize()
        body_hint = self.body.sizeHint()
        header_h = self._header.sizeHint().height()
        # +2 for frame, +24 vertical / +40 horizontal slack (margins + scrollbar)
        w = max(self.minimumWidth(), body_hint.width() + 40)
        h = header_h + body_hint.height() + 24
        screen = self.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = min(w, avail.width())
            h = min(h, avail.height())
        self.resize(w, h)


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


def line_edit(
    value: str, on_change: Optional[Callable] = None, placeholder: str = ""
) -> QLineEdit:
    le = QLineEdit(str(value) if value is not None else "")
    if placeholder:
        le.setPlaceholderText(placeholder)
    if on_change:
        le.textChanged.connect(lambda _=None: on_change())
    return le


def spin(
    value: float,
    lo: float,
    hi: float,
    step: float = 1.0,
    decimals: int = 2,
    on_change: Optional[Callable] = None,
) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(lo, hi)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    sb.setValue(float(value) if value is not None else 0.0)
    sb.setKeyboardTracking(False)
    if on_change:
        sb.valueChanged.connect(lambda _=None: on_change())
    return sb


def int_spin(
    value: int, lo: int, hi: int, on_change: Optional[Callable] = None
) -> QSpinBox:
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


def unit_row(label: str, spinbox: QWidget, unit_combo: QWidget) -> QWidget:
    """Like row() but with a QComboBox as the suffix widget for unit selection."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    lab = QLabel(label, objectName="FieldLabel")
    lab.setMinimumWidth(150)
    h.addWidget(lab)
    h.addWidget(spinbox, 1)
    h.addWidget(unit_combo)
    return w


class UnitField:
    """A unit-aware numeric field: a spinbox + a display-unit combo that
    auto-converts the shown value when the unit changes.

    This is the reusable form of the boilerplate that used to be hand-written
    once per quantity in ``rated_point.py``.  A dialog builds one per quantity,
    drops it in with :meth:`row`, and reads back either the display value
    (:meth:`magnitude` / :meth:`unit_label`) or the normalised standard-unit
    magnitude (:meth:`standard`).  The display unit defaults from the active
    project preset (``units.PREFS``) when none is stored.

    ``dens_rel_getter`` supplies the live relative density for density-coupled
    dimensions (viscosity), read at conversion time so it tracks edits.
    """

    def __init__(
        self,
        dimension: str,
        value: float,
        unit: Optional[str] = None,
        *,
        prefs=None,
        on_change: Optional[Callable] = None,
        lo: float = 0.0,
        hi: float = 1e6,
        step: float = 1.0,
        decimals: int = 3,
        dens_rel_getter: Optional[Callable] = None,
    ):
        prefs = prefs if prefs is not None else _units.PREFS
        self.dimension = dimension
        self.unit = unit or prefs.default_unit(dimension)
        self._dens = dens_rel_getter
        self._on_change = on_change

        self.spin = spin(value, lo, hi, step, decimals, None)
        self.combo = combo(_units.options_for(dimension), self.unit, None)
        # Keep self.unit consistent if a stored unit wasn't in the options list.
        self.unit = self.combo.currentData() or self.unit

        self.spin.valueChanged.connect(lambda _=None: self._fire())
        self.combo.currentIndexChanged.connect(self._on_unit_changed)

    # -- wiring ------------------------------------------------------------
    def _fire(self) -> None:
        if self._on_change:
            self._on_change()

    def _on_unit_changed(self, _idx=None) -> None:
        new_unit = self.combo.currentData()
        if new_unit and new_unit != self.unit:
            dens = self._dens() if self._dens else None
            new_val = _units.convert_display(
                float(self.spin.value()), self.dimension, self.unit, new_unit, dens
            )
            self.spin.blockSignals(True)
            self.spin.setValue(new_val)
            self.spin.blockSignals(False)
            self.unit = new_unit
        self._fire()

    # -- reads -------------------------------------------------------------
    def magnitude(self) -> float:
        return float(self.spin.value())

    def unit_label(self) -> str:
        return self.unit

    def standard(self) -> float:
        dens = self._dens() if self._dens else None
        return _units.to_standard(self.magnitude(), self.dimension, self.unit, dens)

    # -- layout ------------------------------------------------------------
    def row(self, label: str) -> QWidget:
        return unit_row(label, self.spin, self.combo)


def checkbox(text: str, value: bool, on_change: Optional[Callable] = None) -> QCheckBox:
    cb = QCheckBox(text)
    cb.setChecked(bool(value))
    if on_change:
        cb.toggled.connect(lambda _=None: on_change())
    return cb
