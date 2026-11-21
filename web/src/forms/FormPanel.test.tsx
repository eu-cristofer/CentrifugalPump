import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EvaluateResult, PumpflowDoc } from "../engine/types";
import { CATALOG } from "../project/catalog.fixture";
import { fakeEngine } from "./fakeEngine";
import FormPanel from "./FormPanel";

afterEach(cleanup);

const doc = (kind: string): PumpflowDoc => ({
  nodes: [{ id: `${kind}-1`, kind, x: 0, y: 0, settings: { tag: "T" } }],
  edges: [],
});

const result = (kind: string): EvaluateResult => ({
  nodes: {
    [`${kind}-1`]: {
      kind,
      state: "ok",
      status: "B-1 · 833 m³/h",
      badge: ["OK", "ok"],
      notes: [],
      view: {},
    },
  },
  errors: [],
});

function show(kind: string, onClose = vi.fn()) {
  render(
    <FormPanel
      engine={fakeEngine()}
      doc={doc(kind)}
      catalog={CATALOG}
      result={result(kind)}
      nodeId={`${kind}-1`}
      dispatch={vi.fn()}
      onClose={onClose}
    />,
  );
  return onClose;
}

describe("FormPanel", () => {
  it("says to use the desktop app for a kind without a web form", () => {
    show("selection");
    expect(screen.getByText("Edit this node in the desktop app.")).toBeTruthy();
  });

  it("shows the title bar, the node id and the status line", () => {
    show("selection");
    expect(screen.getByText("selection-1")).toBeTruthy();
    expect(screen.getByText("OK")).toBeTruthy();
    expect(screen.getByText("B-1 · 833 m³/h")).toBeTruthy();
  });

  it("closes with the button and with Esc", () => {
    const onClose = show("selection");
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it.each([
    ["test_points", "Pump TAG"],
    ["correction", "Fit degree"],
    ["curve_fit", "Polynomial degree"],
    ["compliance", /awaiting inputs/],
    ["performance_plot", /Polynomial curve/],
    ["npsh", "Pump TAG"],
    ["mechanical_run", "Pump TAG"],
    ["mechanical_run_check", /awaiting a log/],
    ["markdown_note", "Markdown"],
  ])("routes %s to its form", async (kind, marker) => {
    show(kind);
    expect(
      await (typeof marker === "string" ? screen.findByLabelText(marker) : screen.findByText(marker)),
    ).toBeTruthy();
  });

  it("routes rated_point to its form", async () => {
    show("rated_point");
    expect(await screen.findByLabelText("Service TAG")).toBeTruthy();
  });
});
