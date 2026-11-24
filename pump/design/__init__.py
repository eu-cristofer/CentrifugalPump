"""
pump.design
===========

The PumpFlow design system in code: :file:`tokens.json` is the single source
of truth for colours, type, spacing, radii and canvas sizes.  Its shape is
that of the PumpFlow design-system artifact.  ``tokens.json`` can be copied
into it, and back, as is.

Everything that draws uses these names, never literal values:

- the Qt stylesheet (``pumpflow.style``), through :func:`render`;
- the node canvas (``pumpflow.canvas.theme``);
- the screen charts (``pumpflow.nodes.plotting``, ``explore_plot``);
- the report and Annex M charts (:mod:`pump.utilities.annex_m_charts`).

``tests/test_design_tokens.py`` keeps it that way.  It checks that there are
no colour literals outside this file, that every token is used, that every
alias resolves, and that every documented text and control pair meets its
contrast floor.

Examples
--------
>>> color("accent")
'#2f6fb0'
>>> color("port-rated-point") == color("accent")   # an alias
True
>>> length("radius-control")
6.0
>>> font_px("body")
13.0
>>> render("QWidget { color: @body-text; border-radius: @radius-control; font-size: @fs-body; }")
'QWidget { color: #28323d; border-radius: 6px; font-size: 13px; }'
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

__all__ = [
    "TOKENS_PATH",
    "tokens",
    "color",
    "rgba",
    "length",
    "font_px",
    "text_style",
    "family",
    "render",
    "contrast",
    "PLACEHOLDER",
]

TOKENS_PATH = Path(__file__).with_name("tokens.json")

#: ``@name`` (a colour, spacing, radius or canvas token) or ``@fs-<style>``
#: (a text style's font size) in a template.
PLACEHOLDER = re.compile(r"@(fs-)?([a-z][a-z0-9-]*)")

#: CSS at-rules left alone by :func:`render`.
_AT_RULES = frozenset(
    {"media", "page", "import", "font-face", "keyframes", "supports", "charset"}
)

_ALIAS = re.compile(r"^\{([A-Za-z0-9_.-]+)\}$")


@lru_cache(maxsize=1)
def tokens() -> dict:
    """The parsed ``tokens.json`` (cached; treat as read-only)."""
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _colors() -> Dict[str, str]:
    return {t["name"]: t["value"] for t in tokens()["color"]["tokens"]}


@lru_cache(maxsize=1)
def _lengths() -> Dict[str, float]:
    out: Dict[str, float] = {}
    for family in ("spacing", "radius", "canvas"):
        for t in tokens().get(family, {}).get("tokens", []):
            out[t["name"]] = float(str(t["value"]).removesuffix("px"))
    return out


@lru_cache(maxsize=1)
def _styles() -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for group in tokens()["type"]["groups"]:
        for st in group["styles"]:
            out[st["name"]] = {**st, "family": group["family"]}
    return out


def color(name: str) -> str:
    """A colour token's value, aliases (``"{other}"``) resolved."""
    seen: List[str] = []
    value = _colors()[name]
    while True:
        m = _ALIAS.match(value)
        if not m:
            return value
        if m.group(1) in seen or len(seen) > 16:
            raise ValueError(f"alias loop at colour token {name!r}")
        seen.append(m.group(1))
        value = _colors()[m.group(1)]


def rgba(name: str) -> tuple:
    """``(r, g, b, a)`` with ``r, g, b`` in 0..255 and ``a`` in 0..1.

    >>> rgba("node-shadow")
    (40, 55, 75, 0.176)
    >>> rgba("accent")
    (47, 111, 176, 1.0)
    """
    v = color(name).strip()
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)
    m = re.match(r"rgba?\(([^)]*)\)", v)
    if not m:
        raise ValueError(f"colour token {name!r}: unsupported value {v!r}")
    parts = [p.strip() for p in m.group(1).split(",")]
    r, g, b = (int(float(p)) for p in parts[:3])
    return (r, g, b, float(parts[3]) if len(parts) > 3 else 1.0)


def length(name: str) -> float:
    """A spacing, radius or canvas token in pixels."""
    return _lengths()[name]


def text_style(name: str) -> dict:
    """A text style: ``fontSize``, ``fontWeight``, ``family``, ...."""
    return dict(_styles()[name])


def font_px(name: str) -> float:
    """A text style's font size in pixels."""
    return float(str(_styles()[name]["fontSize"]).removesuffix("px"))


def family(key: str = "sans") -> str:
    """A CSS font stack (``sans`` or ``mono``)."""
    return tokens()["type"]["families"][key]


def render(template: str) -> str:
    """Replace ``@token`` and ``@fs-<style>`` placeholders in ``template``.

    Colours become their value, lengths and font sizes ``<n>px``.  An unknown
    name raises ``KeyError``, so a typo never reaches the screen.
    """

    def sub(m: re.Match) -> str:
        if not m.group(1) and m.group(2) in _AT_RULES:
            return m.group(0)  # a CSS at-rule (@media, @page ...), not a token
        if m.group(1):
            return f"{font_px(m.group(2)):g}px"
        name = m.group(2)
        if name in _colors():
            return color(name)
        if name in _lengths():
            return f"{length(name):g}px"
        raise KeyError(f"unknown design token @{name}")

    return PLACEHOLDER.sub(sub, template)


def _luminance(name_or_hex: str) -> float:
    r, g, b, _a = (
        rgba(name_or_hex) if not name_or_hex.startswith("#") else rgba_hex(name_or_hex)
    )

    def chan(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def rgba_hex(value: str) -> tuple:
    h = value.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)


def contrast(fg: str, bg: str) -> float:
    """WCAG contrast ratio of two colour tokens (or ``#rrggbb`` values).

    >>> round(contrast("body-text", "surface"), 1)
    13.0
    """
    a, b = _luminance(fg), _luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)
