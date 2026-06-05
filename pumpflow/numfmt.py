"""
numfmt
======

Locale-tolerant number parsing/formatting (UI_SPEC §5.2 / §6.2).

The data-exchange JSON stores locale-style comma-decimal *strings*
(``"858,29"``, ``"0,736"``) but the same files also contain dot-decimal values
(``"78.552"``).  :func:`parse_decimal` accepts either, plus thousands separators,
and the spreadsheet grid uses it live as the user types.
"""

from __future__ import annotations

from typing import Optional


def parse_decimal(value, default: Optional[float] = None) -> Optional[float]:
    """
    Parse a number that may use ``,`` or ``.`` as the decimal separator.

    Heuristic:
    - both ``,`` and ``.`` present → the *last* one is the decimal separator and
      the other is a thousands separator (``"1.234,56"`` → 1234.56).
    - only ``,`` → comma is the decimal separator (``"858,29"`` → 858.29).
    - only ``.`` → dot is the decimal separator (``"78.552"`` → 78.552).
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return default
    s = s.replace(" ", "").replace("\u00a0", "")

    has_comma = "," in s
    has_dot = "." in s

    try:
        if has_comma and has_dot:
            if s.rfind(",") > s.rfind("."):          # comma is decimal
                s = s.replace(".", "").replace(",", ".")
            else:                                     # dot is decimal
                s = s.replace(",", "")
        elif has_comma:
            s = s.replace(",", ".")
        return float(s)
    except (ValueError, TypeError):
        return default


def fmt(value: Optional[float], decimals: int = 2, unit: str = "") -> str:
    """Deterministic display formatting (matches the library's ``:0.02f`` style)."""
    if value is None:
        return "—"
    try:
        text = f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)
    return f"{text} {unit}".strip()


def fmt_pct(value: Optional[float], decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{decimals}f} %"
