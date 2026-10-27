"""
nodes.markdown_note — Markdown Note

An Orange3-style annotation node: a free-standing sticky note (no input/output
ports) that lets the user write Markdown to explain the case on the canvas.  It
produces no signal — it only documents the pipeline.

Minimal by design: the canvas card shows the note's title plus a one-line
preview; the full Markdown is edited and rendered (via PySide6's built-in
``setMarkdown``) inside the property dialog.
"""

from __future__ import annotations

from typing import Dict

from .base import BaseNode
from . import ui

_DEFAULT_BODY = "# Note\n\nDescribe the case here…"


class MarkdownNoteNode(BaseNode):
    kind = "markdown_note"
    title = "Note"
    glyph = "✎"
    inputs = []
    outputs = []

    def default_settings(self) -> Dict:
        return {"title": "Note", "body": _DEFAULT_BODY}

    def compute(self, inputs) -> Dict[str, object]:
        # Reflect the note onto the canvas card: title + first non-empty line.
        self.title = str(self.settings.get("title") or "Note")
        lines = [ln.strip() for ln in str(self.settings.get("body") or "").splitlines()]
        first = next((ln for ln in lines if ln), "")
        preview = first.lstrip("#").strip()
        self.status = preview[:30] if preview else "empty note"
        self.state = "ok"
        return {}

    # -- dialog ------------------------------------------------------------
    def create_dialog(self, parent, on_change):
        from PySide6.QtWidgets import QPlainTextEdit, QTextBrowser

        s = self.settings
        dlg = ui.PropertyDialog(
            parent,
            "Markdown Note",
            "Annotate the case in Markdown — a free-standing sticky note that "
            "produces no signal.",
            width=520,
        )

        title = ui.line_edit(s.get("title", "Note"), None, "note title")
        editor = QPlainTextEdit(str(s.get("body", "")))
        editor.setPlaceholderText("# Heading\n\nWrite **Markdown** here…")
        editor.setMinimumHeight(180)
        preview = QTextBrowser()
        preview.setOpenExternalLinks(True)
        preview.setMinimumHeight(160)

        def render():
            preview.setMarkdown(str(s.get("body", "")))

        def set_title(v):
            s["title"] = v
            on_change()

        def set_body():
            s["body"] = editor.toPlainText()
            render()
            on_change()

        title.textChanged.connect(set_title)
        editor.textChanged.connect(set_body)

        dlg.add(ui.section("Title"))
        dlg.add(ui.row("Title", title))
        dlg.add(ui.hline())
        dlg.add(ui.section("Markdown"))
        dlg.add(editor)
        dlg.add(ui.section("Preview"))
        dlg.add(preview)
        render()
        dlg.resize(560, 620)
        return dlg
