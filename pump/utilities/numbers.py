"""
numbers
=======

Number formatting with a chosen decimal separator.

Two places choose the separator:

- the **application** sets a per-user default with :func:`set_decimal`
  (desktop *Units ▸ Decimal separator*, web settings);
- a **report** follows its language: the exporters wrap generation in
  ``with decimal(decimal_for_language(lang)):``, which overrides the
  application default for that block only.

No thousands grouping is used, so ``1234.5`` reads ``1234.5`` or ``1234,5``.
Unit text (pint ``~P``) is never touched.

>>> num(9.8)
'9.80'
>>> with decimal(","):
...     num(9.8), nformat("{lo:g}–{hi:g} %", lo=70.5, hi=120)
('9,80', '70,5–120 %')
>>> num(None)
'—'
"""

from __future__ import annotations

import contextlib
import string
from contextvars import ContextVar
from numbers import Number
from typing import Any, Iterator, Optional

POINT = "."
COMMA = ","
SEPARATORS = (POINT, COMMA)

_default = POINT
_override: ContextVar[Optional[str]] = ContextVar("decimal_separator", default=None)


def _check(sep: str) -> str:
    if sep not in SEPARATORS:
        raise ValueError(f"decimal separator must be '.' or ',', not {sep!r}")
    return sep


def set_decimal(sep: str) -> None:
    """Set the application-wide decimal separator (the user preference).

    >>> set_decimal(","); separator()
    ','
    >>> set_decimal("."); separator()
    '.'
    """
    global _default
    _default = _check(sep)


def separator() -> str:
    """The separator in force: a report's, else the application default."""
    return _override.get() or _default


@contextlib.contextmanager
def decimal(sep: str) -> Iterator[None]:
    """Use ``sep`` inside the block (a report's language), then restore.

    >>> with decimal(","):
    ...     separator()
    ','
    >>> separator()
    '.'
    """
    token = _override.set(_check(sep))
    try:
        yield
    finally:
        _override.reset(token)


def decimal_for_language(language: Optional[str]) -> str:
    """The decimal separator of a report language: comma for Portuguese.

    >>> decimal_for_language("pt"), decimal_for_language("pt_BR"), decimal_for_language("en")
    (',', ',', '.')
    """
    return COMMA if str(language or "").lower().startswith("pt") else POINT


def localize(text: str) -> str:
    """Swap the decimal point of an already formatted number.

    Use it only on a string that holds a number and nothing else (no unit, no
    clause number).

    >>> with decimal(","):
    ...     localize("-0.25")
    '-0,25'
    """
    return text.replace(POINT, COMMA) if separator() == COMMA else text


def num(value: Any, spec: str = "0.2f", none: str = "—") -> str:
    """Format a number with ``spec`` and the separator in force.

    >>> num(1234.567, "0.1f"), num(3, "d")
    ('1234.6', '3')
    >>> with decimal(","):
    ...     num(0.0525, "0.1%")
    '5,2%'
    """
    if value is None:
        return none
    if hasattr(value, "magnitude") and hasattr(value, "units"):
        return qty(value, spec, none)
    if spec.endswith("~P"):
        spec = spec[:-2]
    return localize(format(value, spec))


def qty(q: Any, spec: str = "0.2f~P", none: str = "—") -> str:
    """Format a pint Quantity: the magnitude follows the separator, the unit not.

    >>> from pump import Q_
    >>> with decimal(","):
    ...     qty(Q_(9.8, "m**3/h")), qty(Q_(2.5, "m"), "0.1f")
    ('9,80 m³/h', '2,5 m')
    """
    if q is None:
        return none
    if not (hasattr(q, "magnitude") and hasattr(q, "units")):
        return num(q, spec.replace("~P", "").replace("~", ""), none)
    num_spec = spec
    unit_spec = "~P"
    for marker in ("~P", "~C", "~D", "~L", "~H", "P", "~"):
        if num_spec.endswith(marker):
            unit_spec = marker if marker.startswith("~") else "~" + marker
            num_spec = num_spec[: -len(marker)]
            break
    mag = localize(format(q.magnitude, num_spec))
    unit = format(q.units, unit_spec)
    return f"{mag} {unit}".strip()


class _Formatter(string.Formatter):
    def format_field(self, value: Any, format_spec: str) -> str:
        if hasattr(value, "magnitude") and hasattr(value, "units"):
            return qty(value, format_spec or "~P")
        text = super().format_field(value, format_spec)
        if (
            format_spec
            and isinstance(value, Number)
            and not isinstance(value, bool)
            and format_spec[-1:] in "eEfFgG%n"
        ):
            return localize(text)
        return text


_FORMATTER = _Formatter()


def nformat(template: str, *args: Any, **kwargs: Any) -> str:
    """``str.format`` whose numeric fields (with a spec) follow the separator.

    Fields without a format spec and strings are left as they are, so clause
    numbers passed as text ("8.3.4.2") never change.

    >>> with decimal(","):
    ...     nformat("{n:.0f} r/min · {p:.1f} kW · clause {c}", n=10211, p=26.9, c="8.3.4")
    '10211 r/min · 26,9 kW · clause 8.3.4'
    """
    return _FORMATTER.vformat(template, args, kwargs)


def localize_axes(fig: Any) -> Any:
    """Make the tick labels of every axis of a matplotlib figure follow the separator.

    Only default scalar formatters are replaced; custom tick formatters stay.
    The separator is read when the figure is drawn, so call this inside the
    same ``decimal`` block as the save.
    """
    try:
        from matplotlib.ticker import ScalarFormatter
    except ImportError:  # pragma: no cover - matplotlib is a dependency
        return fig

    class _Localized(ScalarFormatter):
        def __call__(self, x, pos=None):
            return localize(super().__call__(x, pos))

        def get_offset(self):
            return localize(super().get_offset())

    for ax in getattr(fig, "axes", ()):
        for axis in (ax.xaxis, ax.yaxis):
            fmt = axis.get_major_formatter()
            if type(fmt) is ScalarFormatter:
                new = _Localized(
                    useOffset=fmt.get_useOffset(), useMathText=fmt.get_useMathText()
                )
                axis.set_major_formatter(new)
    return fig
