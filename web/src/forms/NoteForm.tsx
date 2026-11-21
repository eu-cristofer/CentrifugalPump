import DOMPurify from "dompurify";
import { marked } from "marked";
import { useMemo } from "react";
import { useEngine } from "./engineContext";
import { Banner, Checkbox, Divider, Row, Section, TextField } from "./fields";
import type { FormProps } from "./forms.types";
import { getBool, getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";

/** Remote content and active elements never reach the preview. */
const FORBIDDEN_TAGS = ["img", "iframe", "script", "style", "object", "embed", "form", "link"];

let hookInstalled = false;
function installLinkHook(): void {
  if (hookInstalled) return;
  hookInstalled = true;
  DOMPurify.addHook("afterSanitizeAttributes", (node) => {
    if (node.tagName === "A") {
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer");
    }
  });
}

/** Markdown -> sanitised HTML: no images or active content, links open in a new tab. */
export function renderMarkdown(body: string): string {
  installLinkHook();
  const html = marked.parse(body, { async: false, gfm: true });
  return DOMPurify.sanitize(html, {
    FORBID_TAGS: FORBIDDEN_TAGS,
    FORBID_ATTR: ["style", "srcset"],
    ADD_ATTR: ["target"],
  });
}

/** Markdown Note — mirrors pumpflow/nodes/markdown_note.py (title, body, include in report). */
export default function NoteForm({ nodeId, doc, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const body = s ? getStr(s, "body") : "";
  const html = useMemo(() => renderMarkdown(body), [body]);
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  return (
    <div className="form-body">
      <Section title="Title" />
      <Row label="Title">
        <TextField
          value={getStr(s, "title", "Note")}
          placeholder="note title"
          onChange={(v) => update({ title: v })}
        />
      </Row>
      <Divider />
      <Section title="Markdown" />
      <textarea
        className="field note-editor"
        aria-label="Markdown"
        value={body}
        placeholder={"# Heading\n\nWrite **Markdown** here…"}
        onChange={(e) => update({ body: e.target.value })}
      />
      <Checkbox
        checked={getBool(s, "report", false)}
        label="Include in report (Deviations and open points)"
        onChange={(v) => update({ report: v })}
      />
      <Section title="Preview" />
      <div
        className="note-preview"
        aria-label="Preview"
        // sanitised above: no scripts, images, iframes or styles
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {error && <Banner kind="error">{error}</Banner>}
    </div>
  );
}
