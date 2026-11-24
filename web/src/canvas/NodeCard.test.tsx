import { ReactFlowProvider } from "@xyflow/react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CatalogEntry, NodeResult } from "../engine/types";
import { NodeCardView, type NodeCardData } from "./NodeCard";

afterEach(cleanup);

const entry: CatalogEntry = {
  kind: "compliance",
  title: "Compliance",
  glyph: "C",
  group: "Checks",
  inputs: [{ name: "CorrectedCurve", type: "CorrectedCurve", multi: false }],
  outputs: [{ name: "ComplianceResult", type: "ComplianceResult" }],
  has_web_form: true,
};

const result = (over: Partial<NodeResult>): NodeResult => ({
  kind: "compliance",
  state: "ok",
  status: "B-1A · APPROVED ✓",
  badge: null,
  notes: [],
  view: {},
  ...over,
});

function show(r: NodeResult | undefined, zoom = 1, e: CatalogEntry | undefined = entry) {
  const data: NodeCardData = { kind: "compliance", entry: e, result: r };
  // Handles outside a node log a React Flow warning; silence it for these tests.
  vi.spyOn(console, "warn").mockImplementation(() => undefined);
  return render(
    <ReactFlowProvider>
      <NodeCardView data={data} zoom={zoom} />
    </ReactFlowProvider>,
  );
}

describe("NodeCardView", () => {
  it("renders the verdict pill, notes as chips and the status beside them", () => {
    show(result({ badge: ["APPROVED ✓", "ok"], notes: ["PROVISIONAL", "OVERRIDDEN"] }));
    expect(screen.getByText("APPROVED ✓")).toBeTruthy();
    expect(screen.getByText("PROVISIONAL")).toBeTruthy();
    expect(screen.getByText("OVERRIDDEN")).toBeTruthy();
    expect(screen.getByText("B-1A")).toBeTruthy();
    expect(screen.queryByText("B-1A · APPROVED ✓")).toBeNull();
  });

  it("uses the warn pill with dark text", () => {
    show(result({ badge: ["PENDING", "warn"] }));
    const pill = screen.getByText("PENDING");
    expect(pill.style.color).toBe("var(--body-text)");
    expect(pill.style.background).toBe("var(--amber)");
  });

  it.each([
    ["ok", "✓"],
    ["invalid", "!"],
    ["error", "✗"],
    ["reject", "✗"],
  ] as const)("shows the %s state glyph", (state, glyph) => {
    show(result({ state, status: "text" }));
    const dot = document.querySelector(`.state-dot[data-state="${state}"]`);
    expect(dot?.textContent).toBe(glyph);
  });

  it("draws idle as a hollow ring without a glyph", () => {
    show(undefined);
    const dot = document.querySelector('.state-dot[data-state="idle"]');
    expect(dot?.textContent).toBe("");
    expect(dot?.classList.contains("state-dot-idle")).toBe(true);
  });

  it("labels the ports and colours the handles by signal type", () => {
    show(result({}));
    expect(screen.getByText("CorrectedCurve")).toBeTruthy();
    expect(screen.getByText("ComplianceResult")).toBeTruthy();
    const handle = document.querySelector('[data-handleid="ComplianceResult"]') as HTMLElement;
    expect(handle.style.background).toBe("var(--port-compliance-result)");
  });

  it("marks source nodes (no inputs) for the lighter title bar", () => {
    show(undefined, 1, { ...entry, inputs: [] });
    expect(document.querySelector(".node-title.source")).not.toBeNull();
  });

  it("shows only the title and a big verdict below 75 % zoom", () => {
    show(result({ badge: ["APPROVED ✓", "ok"], notes: ["PROVISIONAL"] }), 0.5);
    expect(screen.getByText("Compliance")).toBeTruthy();
    expect(screen.getByText("APPROVED ✓")).toBeTruthy();
    expect(screen.getByTestId("overview")).toBeTruthy();
    expect(screen.queryByText("PROVISIONAL")).toBeNull();
    expect(screen.queryByText("CorrectedCurve")).toBeNull();
  });

  it("shows a big state glyph in the overview when there is no badge", () => {
    show(result({ state: "error", status: "boom" }), 0.5);
    expect(screen.getByTestId("overview").textContent).toBe("✗");
  });
});
