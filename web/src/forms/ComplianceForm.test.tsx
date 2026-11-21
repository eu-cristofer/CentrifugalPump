import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import ComplianceForm from "./ComplianceForm";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";

afterEach(cleanup);

const rowCells = (name: string, verdict: string) => [
  name,
  "73.00",
  "72.10",
  "70.00",
  "80.00",
  "-1.23 %",
  "5.0 %",
  verdict,
  "",
];

const view = (over: Record<string, unknown> = {}) => ({
  pump_tag: "B-34004A",
  verdict_text: "APPROVED ✓",
  verdict_label: "APPROVED",
  overall_pass: true,
  criteria_label: "API 610 12th edition",
  overridden: false,
  override_reason: "",
  unverified: [],
  not_evaluated: [],
  parallel_ok: null,
  tolerances: {},
  default_tolerances: { head: 0.05, shutoff: 0.1, power: 0.04, efficiency: null },
  rows: [
    {
      name: "Head",
      actual: 73,
      predicted: 72.1,
      min: 70,
      max: 80,
      deviation: -0.0123,
      tol: 0.05,
      verdict: "pass",
      note: "",
      extrapolated: false,
      verified: true,
      cells: rowCells("Head", "✅"),
    },
    {
      name: "Efficiency",
      actual: 61,
      predicted: 60,
      min: null,
      max: null,
      deviation: null,
      tol: null,
      verdict: "info",
      note: "",
      extrapolated: false,
      verified: true,
      cells: ["Efficiency", "61.00", "60.00", "—", "—", "—", "—", "info", "unverified"],
    },
  ],
  ...over,
});

const result = (v: Record<string, unknown>, over: Partial<NodeResult> = {}): NodeResult => ({
  kind: "compliance",
  state: "ok",
  status: "",
  badge: null,
  notes: [],
  view: v,
  ...over,
});

function show(settings: Record<string, unknown>, res: NodeResult, dispatch = vi.fn()) {
  const doc: PumpflowDoc = {
    nodes: [{ id: "compliance-1", kind: "compliance", x: 0, y: 0, settings }],
    edges: [],
  };
  render(
    <EngineContext.Provider value={fakeEngine()}>
      <ComplianceForm nodeId="compliance-1" doc={doc} result={res} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return dispatch;
}

const lastSettings = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings as Record<string, unknown>;

describe("ComplianceForm", () => {
  it("shows the verdict text, the criteria and the parameter table", async () => {
    show({ tolerances: {} }, result(view()));
    const banner = await screen.findByText(/APPROVED ✓/);
    expect(banner.className).toContain("verdict-ok");
    expect(banner.textContent).toContain("B-34004A");
    expect(screen.getByText("Criteria: API 610 12th edition")).toBeTruthy();
    const table = screen.getByRole("table", { name: "Compliance parameters" });
    expect(table.querySelectorAll("thead th")).toHaveLength(9);
    expect(screen.getByText("-1.23 %")).toBeTruthy();
    expect(screen.getByText("✅").className).toContain("v-pass");
  });

  it("uses the error tone for REJECTED and warn for NOT FULLY ASSESSED", async () => {
    show(
      { tolerances: {} },
      result(view({ verdict_text: "REJECTED ✗", verdict_label: "REJECTED", overall_pass: false })),
    );
    expect((await screen.findByText(/REJECTED/)).className).toContain("verdict-error");
    cleanup();
    show(
      { tolerances: {} },
      result(view({ verdict_text: "NOT FULLY ASSESSED", verdict_label: "NOT FULLY ASSESSED" })),
    );
    expect((await screen.findByText(/NOT FULLY ASSESSED/)).className).toContain("verdict-warn");
  });

  it("lists the unverified criteria", async () => {
    show({ tolerances: {} }, result(view({ unverified: ["shut-off band"] })));
    expect(await screen.findByText(/Unverified against the standard text: shut-off band/)).toBeTruthy();
  });

  it("keeps the override section collapsed unless the tolerances are overridden", async () => {
    show({ tolerances: {} }, result(view()));
    const toggle = await screen.findByRole("button", { name: /Override acceptance criteria/ });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Reset to the acceptance criteria")).toBeNull();
    fireEvent.click(toggle);
    expect(screen.getByText(/Changing a tolerance changes the verdict/)).toBeTruthy();
    expect(screen.getByLabelText("Head")).toBeTruthy();
    cleanup();

    show(
      { tolerances: { head: 0.1 }, override_reason: "agreed" },
      result(view({ overridden: true, override_reason: "agreed" })),
    );
    const open = await screen.findByRole("button", { name: /Override acceptance criteria/ });
    expect(open.getAttribute("aria-expanded")).toBe("true");
    expect((screen.getByLabelText("Reason") as HTMLInputElement).value).toBe("agreed");
    expect((screen.getByLabelText("Head") as HTMLInputElement).value).toBe("10");
    expect(screen.getByText(/Tolerances overridden/)).toBeTruthy();
  });

  it("shows the library default in the tolerance fields and writes all four on edit", async () => {
    const dispatch = show({ tolerances: {} }, result(view()));
    fireEvent.click(await screen.findByRole("button", { name: /Override acceptance criteria/ }));
    expect((screen.getByLabelText("Head") as HTMLInputElement).value).toBe("5");
    expect((screen.getByLabelText("Shut-off head") as HTMLInputElement).value).toBe("10");
    fireEvent.change(screen.getByLabelText("Head"), { target: { value: "10" } });
    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "  purchaser agreement " } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({
      tolerances: { head: 0.1, shutoff: 0.1, power: 0.04, efficiency: null },
      override_reason: "purchaser agreement",
    });
  });

  it("resets the tolerances and the reason", async () => {
    const dispatch = show(
      { tolerances: { head: 0.1 }, override_reason: "agreed" },
      result(view({ overridden: true, override_reason: "agreed" })),
    );
    fireEvent.click(await screen.findByText("Reset to the acceptance criteria"));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    const sent = lastSettings(dispatch);
    expect(sent.tolerances).toEqual({});
    expect("override_reason" in sent).toBe(false);
    expect((screen.getByLabelText("Reason") as HTMLInputElement).value).toBe("");
  });

  it("says it is waiting when there is no result yet", async () => {
    show({ tolerances: {} }, result({}, { state: "idle", status: "Waiting for model + rated point" }));
    expect(await screen.findByText(/awaiting inputs/)).toBeTruthy();
  });
});
