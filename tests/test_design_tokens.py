"""The design system is the single source of truth (pump/design/tokens.json).

- no colour literal anywhere in the code: only token names;
- the token file has the shape the design-system artifact reads;
- every alias resolves and every colour / length token is used;
- the stylesheet template has no unknown or unresolved names;
- every documented text and control pair meets its contrast floor.
"""

import json
import re
from pathlib import Path

import pytest

from pump import design

ROOT = Path(__file__).resolve().parents[1]
CODE = [
    p
    for d in ("pump", "pumpflow")
    for p in (ROOT / d).rglob("*.py")
    if "__pycache__" not in p.parts and p.parent.name != "design"  # the loader
]
HEX = re.compile(r"(?<![\w&])#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\b")


def test_no_colour_literals_in_code():
    offenders = []
    for p in CODE:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if HEX.search(line):
                offenders.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, "use a design token instead:\n" + "\n".join(offenders)


def test_token_file_shape():
    t = json.loads(design.TOKENS_PATH.read_text(encoding="utf-8"))
    name_re = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    seen = set()
    for family in ("color", "spacing", "radius", "canvas"):
        entries = t[family]["tokens"]
        assert isinstance(entries, list)
        for e in entries:
            assert set(e) >= {"name", "value", "usage"}, e
            assert name_re.match(e["name"]), e["name"]
            assert e["name"] not in seen, f"duplicate token {e['name']}"
            assert e["usage"].strip(), f"{e['name']} has no usage note"
            seen.add(e["name"])
    styles = [s["name"] for g in t["type"]["groups"] for s in g["styles"]]
    assert len(styles) == len(set(styles))


def test_every_colour_resolves():
    for e in design.tokens()["color"]["tokens"]:
        v = design.color(e["name"])
        assert re.match(r"^(#[0-9a-fA-F]{6}|rgba?\()", v), (e["name"], v)
        design.rgba(e["name"])  # parses


def _code_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in CODE)


def test_every_token_is_used():
    text = _code_text()
    colours = {e["name"]: e["value"] for e in design.tokens()["color"]["tokens"]}
    used = {n for n in colours if re.search(rf"[\"'@]{re.escape(n)}\b", text)}
    # a token used only through an alias of a used token counts as used
    changed = True
    while changed:
        changed = False
        for n, v in colours.items():
            m = re.match(r"^\{(.+)\}$", v)
            if n in used and m and m.group(1) not in used:
                used.add(m.group(1))
                changed = True
    unused = sorted(set(colours) - used)
    assert not unused, f"colour tokens never used: {unused}"
    lengths = [
        e["name"]
        for f in ("spacing", "radius", "canvas")
        for e in design.tokens()[f]["tokens"]
    ]
    unused_len = [n for n in lengths if not re.search(rf"[\"'@]{re.escape(n)}\b", text)]
    assert not unused_len, f"length tokens never used: {unused_len}"


def test_stylesheet_template_resolves():
    from pumpflow.style import APP_QSS

    out = design.render(APP_QSS)
    assert "@" not in out
    with pytest.raises(KeyError):
        design.render("QWidget { color: @no-such-token; }")


# (foreground, background, floor): text 4.5:1, large text / controls 3:1.
PAIRS = [
    ("body-text", "window-bg", 4.5),
    ("body-text", "surface", 4.5),
    ("subtle-text", "surface", 4.5),
    ("subtle-text", "surface-sunken", 4.5),
    ("subtle-text", "dock-title-bg", 4.5),
    ("field-label", "surface", 4.5),
    ("unit-label", "surface", 4.5),
    ("unit-label", "surface-sunken", 4.5),
    ("placeholder", "surface-sunken", 4.5),
    ("steel", "surface", 4.5),
    ("steel", "surface-muted", 4.5),
    ("steel", "dock-title-bg", 4.5),
    ("mono-text", "mono-bg", 4.5),
    ("selected-text", "table-selection-bg", 4.5),
    ("selected-text", "menu-selected-bg", 4.5),
    ("selected-text", "row-hover-bg", 4.5),
    ("tool-button-text", "surface-muted", 4.5),
    ("table-computed-text", "table-computed-bg", 4.5),
    ("title-text", "title-bg", 4.5),
    ("title-text", "title-bg-source", 4.5),
    ("title-text", "accent", 4.5),
    ("title-text", "accent-hover", 4.5),
    ("header-subtitle", "title-bg", 4.5),
    ("banner-info-text", "banner-info-bg", 4.5),
    ("banner-ok-text", "banner-ok-bg", 4.5),
    ("banner-warn-text", "banner-warn-bg", 4.5),
    ("banner-error-text", "banner-error-bg", 4.5),
    ("verdict-idle-text", "banner-info-bg", 4.5),
    ("warn-text", "surface", 4.5),
    ("ok-green", "surface", 4.5),
    ("reject-red", "surface", 4.5),
    ("info-button", "surface", 4.5),
    ("control-border", "surface", 3.0),
    ("control-border", "surface-sunken", 3.0),
    ("accent", "surface", 3.0),  # focus ring
]


@pytest.mark.parametrize("fg, bg, floor", PAIRS, ids=lambda v: str(v))
def test_contrast(fg, bg, floor):
    ratio = design.contrast(fg, bg)
    assert ratio >= floor - 0.005, f"{fg} on {bg}: {ratio:.2f}:1 < {floor}:1"


def test_canvas_and_qss_follow_the_tokens(qapp_offscreen):
    from pumpflow.canvas import theme
    from pumpflow.style import app_qss

    assert theme.ACCENT.name() == design.color("accent")
    assert theme.NODE_W == design.length("node-width")
    assert design.color("control-border") in app_qss()


@pytest.fixture(scope="module")
def qapp_offscreen():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])
