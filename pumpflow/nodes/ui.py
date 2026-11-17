"""
nodes.ui
========

Small reusable building blocks for the widget property dialogs — a styled
dialog shell, labelled form rows, and a validation banner — so each node's
dialog stays short and consistent (UI_SPEC §5: "double-click-to-open property
dialog", left settings pane + main area).
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import QByteArray, QEvent, QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from pump import Q_, Pressure

from ..style import ui_font
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import units as _units


def window_settings() -> QSettings:
    """Where node windows remember their size (app settings, not the project).

    Tests replace this to keep the user's own settings untouched.
    """
    return QSettings("PumpFlow", "PumpFlow")


class PropertyDialog(QDialog):
    """A consistent shell: header, a body you fill, and live-apply semantics.

    Every node window can be minimised and maximised from the title bar.  With
    ``maximizable=True`` (charts and tables) the header also carries a
    Maximize / Restore button; double-clicking the header or pressing F11 does
    the same.  :meth:`remember_as` makes the window reopen at its last size and
    maximised state (stored in the app settings, never in the project file).
    """

    def __init__(
        self,
        parent,
        title: str,
        subtitle: str = "",
        width: int = 460,
        maximizable: bool = False,
    ):
        super().__init__(parent)
        # An independent (modeless) tool window with its own min/max/close,
        # so the canvas and menus stay usable while it is open.  QDialog has no
        # maximise button unless asked for.
        self.setWindowFlag(Qt.Window, True)
        self.setWindowFlag(Qt.WindowMinMaxButtonsHint, True)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self._memory_key: Optional[str] = None
        self.max_button: Optional[QToolButton] = None
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.setObjectName("PropertyDialog")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget(objectName="DialogHeader")
        # A plain QWidget ignores its stylesheet `background` unless told to paint
        # a styled background — without this the dark header never renders and the
        # white title/subtitle text sits on the light window color (unreadable).
        header.setAttribute(Qt.WA_StyledBackground, True)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 14, 18, 12)
        hl.setSpacing(2)
        t = QLabel(title, objectName="DialogTitle")
        t.setFont(ui_font(12, QFont.DemiBold))
        if maximizable:
            top = QHBoxLayout()
            top.setContentsMargins(0, 0, 0, 0)
            top.addWidget(t, 1)
            btn = QToolButton(objectName="HeaderMaximize")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self.toggle_maximized)
            top.addWidget(btn, 0, Qt.AlignTop)
            hl.addLayout(top)
            self.max_button = btn
            self._sync_max_button()
            header.installEventFilter(self)
            QShortcut(QKeySequence(Qt.Key_F11), self, activated=self.toggle_maximized)
        else:
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

    # -- maximise / restore ------------------------------------------------
    def toggle_maximized(self) -> None:
        """Maximise the window, or restore it to its previous size."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_max_button()

    def _sync_max_button(self) -> None:
        if self.max_button is None:
            return
        if self.isMaximized():
            self.max_button.setText("🗗  Restore")
            self.max_button.setToolTip("Restore the window size (F11 or double-click the header)")
        else:
            self.max_button.setText("⛶  Maximize")
            self.max_button.setToolTip("Maximize the window (F11 or double-click the header)")

    def changeEvent(self, event) -> None:  # title-bar maximise keeps the button right
        if event.type() == QEvent.WindowStateChange:
            self._sync_max_button()
        super().changeEvent(event)

    def eventFilter(self, obj, event) -> bool:
        header = getattr(self, "_header", None)
        if obj is header and event.type() == QEvent.MouseButtonDblClick:
            self.toggle_maximized()
            return True
        return super().eventFilter(obj, event)

    # -- remembered size ---------------------------------------------------
    def remember_as(self, key: str) -> None:
        """Restore the last size / maximised state saved under ``key`` and save
        it again whenever the window is hidden or closed."""
        self._memory_key = key
        saved = window_settings().value(f"dialogs/{key}/geometry")
        if isinstance(saved, (QByteArray, bytes)) and len(saved):
            self.restoreGeometry(QByteArray(saved))
            self._sync_max_button()

    def save_window_state(self) -> None:
        if self._memory_key:
            window_settings().setValue(
                f"dialogs/{self._memory_key}/geometry", self.saveGeometry()
            )

    def hideEvent(self, event) -> None:
        self.save_window_state()
        super().hideEvent(event)

    def fit_to_contents(self, vertical_only: bool = False) -> None:
        """Resize the window to fit header + body preferred size (opt-in).

        Used by dialogs whose content changes height (e.g. the Fluid node showing
        a chart only in Water mode) so the window grows/shrinks to fit instead of
        scrolling or leaving dead space.  Clamped to the available screen.

        With ``vertical_only=True`` the current width is preserved and only the
        height is adjusted, so a content change never makes the window jump
        sideways.
        """
        self.body.adjustSize()
        body_hint = self.body.sizeHint()
        header_h = self._header.sizeHint().height()
        # +2 for frame, +24 vertical / +40 horizontal slack (margins + scrollbar)
        w = self.width() if vertical_only else max(self.minimumWidth(), body_hint.width() + 40)
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

    def set_unit(self, label: str) -> None:
        """Programmatically switch the display unit (converts the shown value)."""
        idx = self.combo.findData(label)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

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


class PressureField:
    """A pressure field: ``UnitField("pressure")`` plus a gauge/absolute combo.

    Constructor: ``PressureField(value, unit=None, ref="g", *, prefs=None,
    on_change=None, lo=-1e6, hi=1e6, step=0.1, decimals=3)``.

    Reads: :meth:`magnitude`, :meth:`unit_label`, :meth:`ref`,
    :meth:`pressure` (a ``pump.Pressure``).  Layout: :meth:`row`.

    Switching g<->a converts the displayed value by adding / subtracting the
    standard atmosphere expressed in the *current* unit.  Two fields that must
    share one unit and reference are tied with :func:`link_pressure_fields`
    (or ``add_listener`` / :meth:`set_unit` / :meth:`set_ref` by hand).
    """

    def __init__(
        self,
        value: float,
        unit: Optional[str] = None,
        ref: str = "g",
        *,
        prefs=None,
        on_change: Optional[Callable] = None,
        lo: float = -1e6,
        hi: float = 1e6,
        step: float = 0.1,
        decimals: int = 5,  # g<->a adds 1.01325 bar: keep it lossless
    ):
        self._on_change = on_change
        self._listeners: List[Callable] = []
        self.unit_field = UnitField(
            "pressure",
            value,
            unit,
            prefs=prefs,
            on_change=self._inner_changed,
            lo=lo,
            hi=hi,
            step=step,
            decimals=decimals,
        )
        self.spin = self.unit_field.spin
        self.combo = self.unit_field.combo
        self._last_unit = self.unit_field.unit
        self._ref = ref if ref in ("g", "a") else "g"
        self.ref_combo = combo([("g", "g"), ("a", "a")], self._ref, None)
        self.ref_combo.currentIndexChanged.connect(self._on_ref_changed)

    # -- wiring ------------------------------------------------------------
    def add_listener(self, fn: Callable) -> None:
        """``fn(kind, field)`` is called with ``kind`` in ``{"unit", "ref"}``."""
        self._listeners.append(fn)

    def _notify(self, kind: str) -> None:
        for fn in list(self._listeners):
            fn(kind, self)

    def _fire(self) -> None:
        if self._on_change:
            self._on_change()

    def _inner_changed(self) -> None:
        if self.unit_field.unit != self._last_unit:
            self._last_unit = self.unit_field.unit
            self._notify("unit")
        self._fire()

    def _on_ref_changed(self, _idx=None) -> None:
        new = self.ref_combo.currentData()
        if new and new != self._ref:
            atm = _units.atm_in(self.unit_field.unit)
            v = float(self.spin.value()) + (atm if new == "a" else -atm)
            self.spin.blockSignals(True)
            self.spin.setValue(v)
            self.spin.blockSignals(False)
            self._ref = new
            self._notify("ref")
        self._fire()

    def set_unit(self, label: str) -> None:
        if label != self.unit_field.unit:
            self.unit_field.set_unit(label)

    def set_ref(self, ref: str) -> None:
        if ref != self._ref:
            idx = self.ref_combo.findData(ref)
            if idx >= 0:
                self.ref_combo.setCurrentIndex(idx)

    # -- reads -------------------------------------------------------------
    def magnitude(self) -> float:
        return self.unit_field.magnitude()

    def unit_label(self) -> str:
        return self.unit_field.unit_label()

    def ref(self) -> str:
        return self._ref

    def pressure(self) -> Pressure:
        pint = _units.pint_str("pressure", self.unit_label())
        return Pressure(Q_(self.magnitude(), pint), self._ref)

    # -- layout ------------------------------------------------------------
    def row(self, label: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        lab = QLabel(label, objectName="FieldLabel")
        lab.setMinimumWidth(150)
        h.addWidget(lab)
        h.addWidget(self.spin, 1)
        h.addWidget(self.combo)
        h.addWidget(self.ref_combo)
        return w


def link_pressure_fields(a: PressureField, b: PressureField) -> None:
    """Keep two pressure fields on the same unit and g/a reference."""

    def mirror(src: PressureField, dst: PressureField):
        def on(kind, _field):
            if kind == "unit":
                dst.set_unit(src.unit_label())
            else:
                dst.set_ref(src.ref())

        src.add_listener(on)

    mirror(a, b)
    mirror(b, a)
    b.set_unit(a.unit_label())
    b.set_ref(a.ref())


class UnitHeaderStrip(QWidget):
    """A strip of unit combos laid out above a ``QTableWidget``'s columns."""

    def __init__(self, table):
        super().__init__()
        self.table = table
        self.headers: List["UnitColumnHeader"] = []
        self.setFixedHeight(28)
        self.setObjectName("UnitHeaderStrip")
        table.installEventFilter(self)
        table.horizontalHeader().sectionResized.connect(lambda *_: self.sync())

    def add(self, header: "UnitColumnHeader") -> None:
        header.combo.setParent(self)
        header.combo.show()
        self.headers.append(header)
        self.sync()

    def eventFilter(self, obj, event):
        if obj is self.table and event.type() in (QEvent.Resize, QEvent.Show):
            QTimer.singleShot(0, self.sync)
        return False

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.sync()

    def sync(self) -> None:
        tbl = self.table
        hh = tbl.horizontalHeader()
        vh = tbl.verticalHeader()
        base = self.mapFromGlobal(tbl.mapToGlobal(QPoint(0, 0))).x()
        vw = vh.width() if vh.isVisible() else 0
        for h in self.headers:
            if tbl.isColumnHidden(h.col):
                h.combo.hide()
                continue
            h.combo.show()
            x = base + tbl.frameWidth() + vw + hh.sectionViewportPosition(h.col)
            w = sum(hh.sectionSize(c) for c in range(h.col, h.col + h.span))
            h.combo.setGeometry(x + 1, 2, max(w - 2, 20), 24)


class UnitColumnHeader:
    """A unit combo for one table column (or ``span`` adjacent columns).

    ``on_change(old_label, new_label)`` is called when the user picks another
    unit; the caller converts its stored values.  Build a :class:`UnitHeaderStrip`
    above the table and pass it as ``strip`` (or call ``strip.add(header)``).
    """

    def __init__(
        self,
        table,
        col: int,
        dimension: str,
        unit: str,
        on_change: Callable[[str, str], None],
        *,
        span: int = 1,
        strip: Optional[UnitHeaderStrip] = None,
    ):
        self.table = table
        self.col = col
        self.span = span
        self.dimension = dimension
        self.unit = unit
        self._on_change = on_change
        self.combo = combo(_units.options_for(dimension), unit, None)
        self.unit = self.combo.currentData() or unit
        self.combo.currentIndexChanged.connect(self._changed)
        if strip is not None:
            strip.add(self)

    def _changed(self, _idx=None) -> None:
        new = self.combo.currentData()
        old = self.unit
        if new and new != old:
            self.unit = new
            self._on_change(old, new)

    def set_unit(self, label: str, notify: bool = False) -> None:
        """Select ``label``; ``on_change`` is only called when ``notify``."""
        idx = self.combo.findData(label)
        if idx < 0:
            return
        if notify:
            self.combo.setCurrentIndex(idx)
            return
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(idx)
        self.combo.blockSignals(False)
        self.unit = label


class BeforeAfterTable:
    """Read-only before/after table (Q, Head, Power, η, stage) with display-unit
    combos for Q, Head and Power.

    Rows arrive in the binding's canonical units (m³/h, m, kW, %); the combos
    only change what is *shown* — nothing upstream or in the report changes.
    The chosen labels are kept in ``settings["table_units"]`` so the window
    reopens in the same units.
    """

    DIMS = (("capacity", "Q"), ("head", "Head"), ("power", "Power"))

    def __init__(self, settings: dict, prefs=None):
        from PySide6.QtWidgets import QHeaderView, QTableWidget

        prefs = prefs if prefs is not None else _units.PREFS
        self._settings = settings
        stored = settings.get("table_units")
        self.units = dict(stored) if isinstance(stored, dict) else {}
        self.combos = {}
        self.strip = QWidget()
        h = QHBoxLayout(self.strip)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(QLabel("Show in", objectName="FieldLabel"))
        for dim, label in self.DIMS:
            unit = self.units.get(dim) or prefs.default_unit(dim)
            cb = combo(_units.options_for(dim), unit, None)
            self.units[dim] = cb.currentData() or _units.canonical_unit(dim)
            cb.currentIndexChanged.connect(lambda _=None, d=dim: self._unit_changed(d))
            h.addWidget(QLabel(label, objectName="FieldLabel"))
            h.addWidget(cb)
            self.combos[dim] = cb
        h.addStretch(1)

        self.table = QTableWidget(0, 5)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setObjectName("ReadGrid")
        self._pairs = ()
        self._labels = ("before", "after")
        self._set_headers()

    def _set_headers(self) -> None:
        u = self.units
        self.table.setHorizontalHeaderLabels(
            [
                f"Q [{u['capacity']}]",
                f"Head [{u['head']}]",
                f"Power [{u['power']}]",
                "η [%]",
                "stage",
            ]
        )

    def _unit_changed(self, dim: str) -> None:
        self.units[dim] = self.combos[dim].currentData()
        self._settings["table_units"] = dict(self.units)
        self._set_headers()
        self.fill(self._pairs, self._labels)

    def _show(self, value, dim: str) -> str:
        from ..numfmt import fmt

        if value is None:
            return "—"
        canon = _units.canonical_unit(dim)
        return fmt(_units.convert_display(float(value), dim, canon, self.units[dim]))

    def _cells(self, row: dict, stage: str) -> list:
        from ..numfmt import fmt

        eff = row.get("eff")
        return [
            self._show(row.get("q"), "capacity"),
            self._show(row.get("head"), "head"),
            self._show(row.get("power"), "power"),
            fmt(eff, 1) if eff is not None else "—",
            stage,
        ]

    def fill(self, pairs, labels=("before", "after")) -> None:
        """Show ``({"measured": row, "corrected": row}, ...)`` pairs."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QTableWidgetItem

        self._pairs = tuple(pairs or ())
        self._labels = labels
        self.table.setRowCount(0)
        for pair in self._pairs:
            for key, stage, muted in (
                ("measured", labels[0], True),
                ("corrected", labels[1], False),
            ):
                r = self.table.rowCount()
                self.table.insertRow(r)
                for c, text in enumerate(self._cells(pair[key], stage)):
                    item = QTableWidgetItem(text)
                    if muted:
                        item.setForeground(QColor("#8a96a3"))
                    self.table.setItem(r, c, item)

    def clear(self) -> None:
        self.fill((), self._labels)


def info_button(title: str, html: str, parent: Optional[QWidget] = None):
    """A small round "i" button that opens ``html`` in a modeless help box."""
    from PySide6.QtWidgets import QPushButton, QToolButton

    btn = QToolButton(parent)
    btn.setText("i")
    btn.setObjectName("InfoButton")
    btn.setToolTip(f"About: {title}")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedSize(20, 20)
    btn.setStyleSheet(
        "QToolButton#InfoButton { border: 1px solid #5b8def; border-radius: 10px;"
        " color: #5b8def; font-weight: bold; font-style: italic; }"
        "QToolButton#InfoButton:hover { background: #5b8def; color: white; }"
    )

    def show():
        box = QDialog(btn.window())
        box.setWindowTitle(title)
        box.setObjectName("InfoDialog")
        box.setMinimumWidth(480)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)
        text = QLabel(html)
        text.setTextFormat(Qt.RichText)
        text.setWordWrap(True)
        text.setStyleSheet("font-weight: normal;")
        text.setFixedWidth(460)
        text.setMinimumHeight(text.heightForWidth(460) + 8)
        lay.addWidget(text)
        ok = QPushButton("OK")
        ok.clicked.connect(box.close)
        bar = QHBoxLayout()
        bar.addStretch(1)
        bar.addWidget(ok)
        lay.addLayout(bar)
        box.text = text.text  # let tests read the help text
        btn._box = box  # keep a reference while it is open
        box.adjustSize()
        box.show()

    btn.clicked.connect(show)
    return btn


def section_with_info(title: str, info_title: str, html: str) -> QWidget:
    """A section heading followed by an :func:`info_button`."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    h.addWidget(section(title))
    btn = info_button(info_title, html, w)
    h.addWidget(btn)
    h.addStretch(1)
    w.info_button = btn
    return w


def checkbox(text: str, value: bool, on_change: Optional[Callable] = None) -> QCheckBox:
    cb = QCheckBox(text)
    cb.setChecked(bool(value))
    if on_change:
        cb.toggled.connect(lambda _=None: on_change())
    return cb
