import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { plots, resetPlots } from "../charts/uplotMock";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import NpshForm from "./NpshForm";

vi.mock("uplot", async () => ({ default: (await import("../charts/uplotMock")).FakePlot }));

beforeEach(resetPlots);
afterEach(cleanup);

const baseSettings = (extra: Record<string, unknown> = {}) => ({
  pump_tag: "P-9001A",
  mode: "points",
  degree: 2,
  columns: { q: "m³/h", npshr: "m" },
  rows: [
    { q: 3.45, npshr: 0.82 },
    { q: 9.88, npshr: 1.25 },
  ],
  calc_p: 1.2,
  calc_p_unit: "bar",
  calc_p_ref: "a",
  calc_temp: 20,
  calc_temp_unit: "°C",
  calc_z: 0,
  calc_z_unit: "m",
  overrides: { min_ratio: null, min_margin: null },
  npshr_quoted: 1.237,
  npshr_quoted_unit: "m",
  ...extra,
});

const result = (view: Record<string, unknown> | null = {}): NodeResult => ({
  kind: "npsh",
  state: "ok",
  status: "P-9001A · NPSHr 1.08 m @ rated · NPSHa 2.40 m · ratio 2.22 · PASSED",
  badge: ["PASSED", "ok"],
  notes: [],
  view:
    view === null
      ? {}
      : {
          pump_tag: "P-9001A",
          mode: "points",
          status: "pass",
          verdict: "PASSED",
          verified: true,
          criteria_label: "API 610 8th edition + Petrobras N-553 rev E (client overlay)",
          npsha: 2.4,
          npshr: 1.0802,
          margin: 1.3198,
          ratio: 2.2218,
          npshr_quoted: 1.237,
          quoted_ok: true,
          min_ratio: 1.15,
          min_margin: 0.8,
          npshr_tol_plus: 0,
          rated_q: 9.8,
          points: { q: [3.45, 9.88], npshr: [0.82, 1.25] },
          curve: { q: [3.45, 6.6, 9.88], npshr: [0.82, 1.0, 1.25] },
          ...view,
        },
});

function mount(s = baseSettings(), r: NodeResult = result(), dispatch = vi.fn()) {
  const doc: PumpflowDoc = {
    nodes: [{ id: "npsh-1", kind: "npsh", x: 0, y: 0, settings: s }],
    edges: [],
  };
  const engine = fakeEngine();
  render(
    <EngineContext.Provider value={engine}>
      <NpshForm nodeId="npsh-1" doc={doc} result={r} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return { dispatch, engine };
}

const lastSettings = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings as Record<string, unknown> & {
    rows: Array<Record<string, number | null>>;
    overrides: Record<string, unknown>;
  };

describe("NpshForm", () => {
  it("renders the points grid, the verdict banner and the NPSHr chart", async () => {
    mount();
    expect(((await screen.findByLabelText("Pump TAG")) as HTMLInputElement).value).toBe("P-9001A");
    expect((screen.getByLabelText("Q row 2") as HTMLInputElement).value).toBe("9.88");
    expect((screen.getByLabelText("NPSHr row 1") as HTMLInputElement).value).toBe("0.82");
    expect(screen.getByText(/PASSED\s+·\s+P-9001A/)).toBeTruthy();
    expect(screen.getByText(/ratio 2\.22/)).toBeTruthy();
    expect(screen.getByText(/Quoted NPSHr 1\.24 m: OK/)).toBeTruthy();
    expect(plots).toHaveLength(1);
    expect(plots[0]!.opts.series.slice(1).map((s) => s.label)).toEqual([
      "NPSH3 data",
      "NPSHr fit",
      "NPSHa 2.40 m",
    ]);
  });

  it("is red for a failed verdict and flags unverified criteria", async () => {
    mount(baseSettings(), result({ status: "fail", verdict: "FAILED (unverified criteria)", verified: false }));
    const banner = await screen.findByText(/FAILED \(unverified criteria\)/);
    expect(banner.className).toContain("verdict-error");
    expect(screen.getByText(/provisional/)).toBeTruthy();
  });

  it("shows the node status and no chart while the points are incomplete", async () => {
    mount(baseSettings(), { ...result(null), state: "invalid", status: "Enter ≥ 2 NPSHr points (Q, NPSHr)" });
    expect(await screen.findByText(/Enter ≥ 2 NPSHr points/)).toBeTruthy();
    expect(screen.getByText(/awaiting inputs/)).toBeTruthy();
    expect(plots).toHaveLength(0);
  });

  it("edits cells, adds and removes rows", async () => {
    const { dispatch } = mount();
    fireEvent.change(await screen.findByLabelText("NPSHr row 2"), { target: { value: "1,3" } });
    fireEvent.click(screen.getByRole("button", { name: /Add row/ }));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch).rows).toEqual([
      { q: 3.45, npshr: 0.82 },
      { q: 9.88, npshr: 1.3 },
      { q: null, npshr: null },
    ]);
  });

  it("converts a column when its unit changes", async () => {
    const { dispatch, engine } = mount();
    const unit = (await screen.findByLabelText("Capacity unit")) as HTMLSelectElement;
    await waitFor(() => expect(unit.options.length).toBeGreaterThan(1));
    fireEvent.change(unit, { target: { value: "US GPM" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(engine.convert).toHaveBeenCalledWith(3.45, "m³/h", "US GPM", "capacity");
    expect(lastSettings(dispatch).columns).toEqual({ q: "US GPM", npshr: "m" });
    expect(lastSettings(dispatch).rows[0]!.q).toBeCloseTo(3.45 * 4.40287);
  });

  it("switches to the calculator and shows its inputs and the calculated NPSHa", async () => {
    const { dispatch } = mount(baseSettings({ mode: "calculator" }), result({ mode: "calculator" }));
    expect(await screen.findByLabelText("Suction pressure")).toBeTruthy();
    expect(screen.getByLabelText("Water temperature")).toBeTruthy();
    expect((screen.getByLabelText("Suction ID") as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByText(/Calculated NPSHa: 2\.400 m/)).toBeTruthy();
    fireEvent.click(screen.getByLabelText(/Suction pipe ID/));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({ calc_id: 100, calc_id_unit: "mm" });
  });

  it("stores NPSHa and the quoted NPSHr as unset (null) when switched off", async () => {
    const { dispatch } = mount(baseSettings({ npsha: 2.4, npsha_unit: "m" }));
    fireEvent.click(await screen.findByLabelText(/Judge against the quoted NPSHr/));
    fireEvent.click(screen.getByLabelText(/Enter NPSHa here/));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({ npshr_quoted: null, npsha: null });
  });

  it("writes the criteria overrides", async () => {
    const { dispatch } = mount();
    expect((await screen.findByLabelText("Min ratio") as HTMLInputElement).disabled).toBe(true);
    fireEvent.click(screen.getByLabelText(/Min NPSHa \/ NPSHr ratio/));
    fireEvent.click(screen.getByLabelText(/Min margin NPSHa/));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch).overrides).toEqual({
      min_ratio: 1.15,
      min_margin: { value: 0.8, unit: "m" },
    });
  });
});
