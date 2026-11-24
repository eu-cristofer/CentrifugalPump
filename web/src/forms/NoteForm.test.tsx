import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import NoteForm, { renderMarkdown } from "./NoteForm";

afterEach(cleanup);

const result: NodeResult = {
  kind: "markdown_note",
  state: "ok",
  status: "Note",
  badge: null,
  notes: [],
  view: {},
};

function mount(s: Record<string, unknown>, dispatch = vi.fn()) {
  const doc: PumpflowDoc = {
    nodes: [{ id: "markdown_note-1", kind: "markdown_note", x: 0, y: 0, settings: s }],
    edges: [],
  };
  render(
    <EngineContext.Provider value={fakeEngine()}>
      <NoteForm nodeId="markdown_note-1" doc={doc} result={result} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return dispatch;
}

const lastSettings = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings as Record<string, unknown>;

describe("renderMarkdown", () => {
  it("renders Markdown", () => {
    const html = renderMarkdown("# Title\n\n**bold** and a list\n\n- a\n- b");
    expect(html).toContain("<h1");
    expect(html).toContain("<strong>bold</strong>");
    expect(html).toContain("<li>a</li>");
  });

  it("strips images, scripts, iframes, styles and event handlers", () => {
    const html = renderMarkdown(
      '![logo](picture.png)\n\n<img src="x" onerror="boom()">\n\n<script>boom()</script>\n\n<iframe src="x"></iframe>\n\n<style>p{}</style>\n\n<p onclick="boom()">text</p>',
    );
    expect(html).not.toMatch(/<img|<script|<iframe|<style|onerror|onclick/i);
    expect(html).toContain("text");
  });

  it("opens links in a new tab without opener and drops javascript links", () => {
    const html = renderMarkdown("[doc](page.html) and [bad](javascript:boom())");
    expect(html).toContain('href="page.html"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).not.toContain("javascript:");
  });
});

describe("NoteForm", () => {
  const base = { title: "Witness note", body: "# Heading\n\ntext", report: false };

  it("renders the title, the body, the toggle and the live preview", async () => {
    mount(base);
    expect(((await screen.findByLabelText("Title", { selector: "input" })) as HTMLInputElement).value).toBe("Witness note");
    expect((screen.getByLabelText("Markdown") as HTMLTextAreaElement).value).toContain("# Heading");
    expect(screen.getByLabelText(/Include in report/)).toBeTruthy();
    expect(screen.getByLabelText("Preview").querySelector("h1")?.textContent).toBe("Heading");
  });

  it("previews without images or scripts", async () => {
    mount({ ...base, body: 'a ![x](y.png)<script>boom()</script> b' });
    const preview = (await screen.findByLabelText("Preview")) as HTMLElement;
    expect(preview.querySelector("img")).toBeNull();
    expect(preview.querySelector("script")).toBeNull();
    expect(preview.textContent).toContain("a");
  });

  it("updates the preview and saves the edits, including the report toggle", async () => {
    const dispatch = mount(base);
    fireEvent.change(await screen.findByLabelText("Markdown"), { target: { value: "## Two\n\nnew" } });
    expect(screen.getByLabelText("Preview").querySelector("h2")?.textContent).toBe("Two");
    fireEvent.click(screen.getByLabelText(/Include in report/));
    fireEvent.change(screen.getByLabelText("Title", { selector: "input" }), { target: { value: "Renamed" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toEqual({ title: "Renamed", body: "## Two\n\nnew", report: true });
  });
});
