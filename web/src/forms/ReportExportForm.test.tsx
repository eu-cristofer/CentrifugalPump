import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NodeResult, PumpflowDoc, ReportExportView } from "../engine/types";
import { withPrintScript } from "./download";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import ReportExportForm from "./ReportExportForm";

const NODE = "report_export-1";

const VIEW: ReportExportView = {
  has_rated: true,
  overall_verdict_text: "APPROVED ✓",
  pumps: [
    {
      tag: "B-34004A",
      verdict_text: "APPROVED ✓",
      sections: ["Corrected", "Fitted", "Verdict"],
      reportable: true,
    },
  ],
};

const result = (view: unknown = VIEW): NodeResult => ({
  kind: "report_export",
  state: "ok",
  status: "1 pump · APPROVED ✓",
  badge: null,
  notes: [],
  view: view as NodeResult["view"],
});

const SETTINGS = {
  language: "en",
  template_path: "",
  out_dir: "",
  filename: "",
  equipment: { Manufacturer: "Sundyne", Model: "LMV311" },
  project: "B-34004",
  client: "",
  location: "Arvada",
  test_date: "2011-12-13",
  revision: "0",
  signatories: [
    { role: "Vendor", name: "" },
    { role: "Inspector", name: "" },
  ],
};

let engine: ReturnType<typeof fakeEngine>;
let click: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  engine = fakeEngine();
  URL.createObjectURL = vi.fn(() => "blob:report");
  URL.revokeObjectURL = vi.fn();
  click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mount(settings: Record<string, unknown> = SETTINGS, res: NodeResult = result()) {
  const dispatch = vi.fn();
  const doc: PumpflowDoc = {
    meta: { schema_version: 2 },
    nodes: [
      { id: "other-1", kind: "fluid", x: 0, y: 0, settings: { name: "kept" } },
      { id: NODE, kind: "report_export", x: 0, y: 0, settings },
    ],
    edges: [],
  };
  render(
    <EngineContext.Provider value={engine}>
      <ReportExportForm nodeId={NODE} doc={doc} result={res} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return dispatch;
}

const lastSettings = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings as Record<string, unknown>;

const button = (name: string) => screen.getByRole("button", { name }) as HTMLButtonElement;

describe("withPrintScript", () => {
  it("adds a print-on-load script before </body>", () => {
    const out = withPrintScript("<html><body><p>x</p></body></html>");
    expect(out).toMatch(/<p>x<\/p><script>[^<]*print\(\)[^<]*<\/script><\/body>/);
  });

  it("appends it when there is no body end tag", () => {
    expect(withPrintScript("<p>x</p>")).toMatch(/^<p>x<\/p><script>/);
  });
});

describe("ReportExportForm", () => {
  it("shows the cover fields, the pumps, the exports and the desktop-only line", async () => {
    mount();
    expect(((await screen.findByLabelText("Project")) as HTMLInputElement).value).toBe("B-34004");
    expect((screen.getByLabelText("Location") as HTMLInputElement).value).toBe("Arvada");
    expect((screen.getByLabelText("Test date") as HTMLInputElement).value).toBe("2011-12-13");
    expect((screen.getByLabelText("Equipment field 1") as HTMLInputElement).value).toBe(
      "Manufacturer",
    );
    expect((screen.getByLabelText("Equipment value 2") as HTMLInputElement).value).toBe("LMV311");
    expect((screen.getByLabelText("Signatory role 2") as HTMLInputElement).value).toBe("Inspector");
    expect(screen.getByText(/B-34004A — APPROVED ✓/)).toBeTruthy();
    expect(screen.getByText(/Overall verdict: APPROVED ✓/)).toBeTruthy();
    for (const name of ["Word (.docx)", "HTML", "Test data summary (.xlsx)", "Print to PDF"]) {
      expect(button(name).disabled).toBe(false);
    }
    expect(screen.getByText(/LaTeX \/ PDF report: desktop app only/)).toBeTruthy();
    // desktop file paths are not offered
    expect(screen.queryByLabelText(/template/i)).toBeNull();
    expect(screen.queryByLabelText(/folder/i)).toBeNull();
  });

  it("downloads the docx the engine returns", async () => {
    mount();
    await screen.findByLabelText("Project");
    fireEvent.click(button("Word (.docx)"));
    await waitFor(() => expect(click).toHaveBeenCalled());
    expect(engine.exportReport).toHaveBeenCalledTimes(1);
    const [doc, fmt, lang] = engine.exportReport.mock.calls[0]!;
    expect(fmt).toBe("docx");
    expect(lang).toBe("en");
    const nodes = (doc as PumpflowDoc).nodes as Array<{ id: string; settings: { project?: string } }>;
    expect(nodes.find((n) => n.id === NODE)!.settings.project).toBe("B-34004");
    expect(nodes.find((n) => n.id === "other-1")).toBeTruthy();
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    const blob = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls[0]![0] as Blob;
    expect(blob.size).toBe("PK-bytes".length);
    expect(await screen.findByText("Saved Report.docx")).toBeTruthy();
  });

  it("exports with the language and edits made a moment ago (not yet in the document)", async () => {
    mount();
    fireEvent.change(await screen.findByLabelText("Language"), { target: { value: "pt" } });
    fireEvent.change(screen.getByLabelText("Project"), { target: { value: "Changed" } });
    fireEvent.click(button("Test data summary (.xlsx)"));
    await waitFor(() => expect(engine.exportReport).toHaveBeenCalled());
    const [doc, fmt, lang] = engine.exportReport.mock.calls[0]!;
    expect(fmt).toBe("summary_xlsx");
    expect(lang).toBe("pt");
    const node = ((doc as PumpflowDoc).nodes as Array<{ id: string; settings: Record<string, unknown> }>).find(
      (n) => n.id === NODE,
    )!;
    expect(node.settings.project).toBe("Changed");
    expect(node.settings.language).toBe("pt");
  });

  it("prints the HTML report from a Blob URL in a new window", async () => {
    const win = { location: { replace: vi.fn() }, close: vi.fn() };
    const open = vi.spyOn(window, "open").mockReturnValue(win as unknown as Window);
    mount();
    await screen.findByLabelText("Project");
    fireEvent.click(button("Print to PDF"));
    // the window is opened inside the click, before the export finishes
    expect(open).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(win.location.replace).toHaveBeenCalledWith("blob:report"));
    expect(engine.exportReport.mock.calls[0]![1]).toBe("html");
    const blob = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls[0]![0] as Blob;
    expect(blob.type).toBe("text/html");
    expect(click).not.toHaveBeenCalled();
  });

  it("says so when the browser blocks the print window", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    mount();
    await screen.findByLabelText("Project");
    fireEvent.click(button("Print to PDF"));
    expect((await screen.findByRole("alert")).textContent).toMatch(/blocked/);
    expect(engine.exportReport).not.toHaveBeenCalled();
  });

  it("shows an error from Python in a banner and closes the print window", async () => {
    engine.exportReport.mockRejectedValueOnce(new Error("No branch has a fitted curve to report."));
    const win = { location: { replace: vi.fn() }, close: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(win as unknown as Window);
    mount();
    await screen.findByLabelText("Project");
    fireEvent.click(button("Print to PDF"));
    expect((await screen.findByRole("alert")).textContent).toContain("No branch has a fitted curve");
    expect(win.close).toHaveBeenCalled();
    expect(button("Print to PDF").disabled).toBe(false);
  });

  it("disables the exports with nothing to report", async () => {
    mount(SETTINGS, result({ has_rated: true, overall_verdict_text: "pending", pumps: [] }));
    await screen.findByLabelText("Project");
    expect(screen.getByText("No branches connected.")).toBeTruthy();
    for (const name of ["Word (.docx)", "HTML", "Test data summary (.xlsx)", "Print to PDF"]) {
      expect(button(name).disabled).toBe(true);
    }
  });

  it("saves cover, signatory and equipment edits", async () => {
    const dispatch = mount();
    fireEvent.change(await screen.findByLabelText("Client"), { target: { value: "Petrobras" } });
    fireEvent.change(screen.getByLabelText("Signatory name 1"), { target: { value: "A. Smith" } });
    fireEvent.change(screen.getByLabelText("Equipment value 1"), { target: { value: "Acme" } });
    fireEvent.click(screen.getByRole("button", { name: "Add field" }));
    fireEvent.change(screen.getByLabelText("Equipment field 3"), { target: { value: "Driver" } });
    fireEvent.change(screen.getByLabelText("Equipment value 3"), { target: { value: "37 kW" } });
    fireEvent.click(screen.getByRole("button", { name: "Remove equipment row 2" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    const s = lastSettings(dispatch);
    expect(s.client).toBe("Petrobras");
    expect(s.signatories).toEqual([
      { role: "Vendor", name: "A. Smith" },
      { role: "Inspector", name: "" },
    ]);
    expect(s.equipment).toEqual({ Manufacturer: "Acme", Driver: "37 kW" });
    expect(s.template_path).toBe("");
  });

  it("keeps an unnamed equipment row out of the settings", async () => {
    const dispatch = mount();
    fireEvent.click(await screen.findByRole("button", { name: "Add field" }));
    fireEvent.change(screen.getByLabelText("Equipment value 3"), { target: { value: "orphan" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch).equipment).toEqual({ Manufacturer: "Sundyne", Model: "LMV311" });
  });

  it("stores include_signatures only when off, and summary fields only when filled", async () => {
    const dispatch = mount({ ...SETTINGS, po_number: "PO-1" });
    expect(((await screen.findByLabelText("Purchase order no.")) as HTMLInputElement).value).toBe("PO-1");
    fireEvent.click(screen.getByLabelText(/Include signature block/));
    fireEvent.change(screen.getByLabelText("Purchase order no."), { target: { value: "  " } });
    fireEvent.change(screen.getByLabelText("Purchaser"), { target: { value: "Petrobras" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    const s = lastSettings(dispatch);
    expect(s.include_signatures).toBe(false);
    expect("po_number" in s).toBe(false);
    expect(s.purchaser).toBe("Petrobras");
    expect((screen.getByLabelText("Signatory role 1") as HTMLInputElement).disabled).toBe(true);
    fireEvent.click(screen.getByLabelText(/Include signature block/));
    await waitFor(() => expect("include_signatures" in lastSettings(dispatch)).toBe(false), {
      timeout: 2000,
    });
  });

  it("records the ambient temperature only when ticked", async () => {
    const dispatch = mount();
    await screen.findByLabelText("Project");
    expect((screen.getByLabelText("Ambient temperature unit") as HTMLSelectElement).disabled).toBe(true);
    fireEvent.click(screen.getByLabelText(/Ambient temperature recorded/));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch).ambient_temp).toBe(25);
    expect(lastSettings(dispatch).ambient_temp_unit).toBe("°C");
  });
});
