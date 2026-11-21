import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import MrtCheckForm from "./MrtCheckForm";

afterEach(cleanup);

const q = (value: number, unit: string) => ({ value, unit });
const view = {
  pump_tag: "B-34004B",
  verdict: "FAILED",
  verdict_label: "FAILED (unverified limits)",
  inputs_text: "Log: B-34004B, 17 readings.  Criteria: api610:8 + n553.",
  passed: false,
  fully_assessed: true,
  verified: false,
  source: "Vibration: API 610 8th ed. Table 2-5.",
  criteria_label: "API 610 8th edition + Petrobras N-553 rev E (client overlay)",
  duration: q(240, "min"),
  min_duration: q(4, "h"),
  duration_status: "pass",
  rows: [
    {
      name: "Vib unfiltered",
      role: "vibration_unfiltered",
      unit: "in/s",
      min: q(0.14, "in/s"),
      max: q(0.16, "in/s"),
      last: q(0.14, "in/s"),
      limit: q(0.11811023622047245, "in/s"),
      stabilisation: null,
      status: "fail",
    },
    {
      name: "Sump",
      role: "oil_temperature",
      unit: "°F",
      min: q(116, "°F"),
      max: q(124, "°F"),
      last: q(124, "°F"),
      limit: null,
      stabilisation: {
        change: q(1.11, "Δ°C"),
        allowed: q(2, "Δ°C"),
        window: q(30, "min"),
        ok: true,
      },
      status: "pass",
    },
  ],
};

const result = (v: Record<string, unknown> = view): NodeResult => ({
  kind: "mechanical_run_check",
  state: "reject",
  status: "B-34004B · 17 readings · 4.0 h · FAILED (unverified limits)",
  badge: ["FAILED", "fail"],
  notes: [],
  view: v,
});

function mount(overrides: Record<string, unknown> = {}, r: NodeResult = result(), dispatch = vi.fn()) {
  const doc: PumpflowDoc = {
    nodes: [
      {
        id: "mechanical_run_check-1",
        kind: "mechanical_run_check",
        x: 0,
        y: 0,
        settings: { overrides: { min_duration: null, role_max: {}, stabilisation: {}, ...overrides } },
      },
    ],
    edges: [],
  };
  const engine = fakeEngine();
  render(
    <EngineContext.Provider value={engine}>
      <MrtCheckForm nodeId="mechanical_run_check-1" doc={doc} result={r} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return { dispatch, engine };
}

const lastOverrides = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings.overrides as Record<string, unknown>;

describe("MrtCheckForm", () => {
  it("shows the verdict, the duration and the per-channel rows", async () => {
    mount();
    const banner = await screen.findByText(/FAILED \(unverified limits\)\s+·\s+B-34004B/);
    expect(banner.className).toContain("verdict-error");
    expect(screen.getByText(/Log: B-34004B, 17 readings/)).toBeTruthy();
    expect(screen.getByText(/Duration 240 min \(minimum 4 h\)/)).toBeTruthy();
    expect(screen.getByText(/provisional/)).toBeTruthy();
    const table = screen.getByRole("table", { name: "Channel results" });
    const vib = within(table).getByText("Vib unfiltered").closest("tr")!;
    expect(vib.textContent).toContain("0.1181"); // limit, 4 significant digits
    expect(within(vib).getByText("FAIL").className).toContain("v-fail");
    const sump = within(table).getByText("Sump").closest("tr")!;
    expect(sump.textContent).toContain("1.11 ≤ 2 Δ°C / 30 min ✓");
    expect(within(sump).getByText("PASS").className).toContain("v-pass");
  });

  it("is amber when passed but not fully assessed, green when fully assessed", async () => {
    mount({}, result({ ...view, verdict: "PASSED", passed: true, fully_assessed: false, verdict_label: "PASSED (not fully assessed)" }));
    expect((await screen.findByText(/PASSED \(not fully assessed\)/)).className).toContain("verdict-warn");
    cleanup();
    mount({}, result({ ...view, verdict: "PASSED", passed: true, verified: true, verdict_label: "PASSED" }));
    expect((await screen.findByText(/^PASSED\s+·/)).className).toContain("verdict-ok");
  });

  it("shows the node status while no log is wired", async () => {
    mount({}, { ...result({}), state: "idle", status: "Connect an MRT Log", badge: null });
    expect(await screen.findByText("Connect an MRT Log")).toBeTruthy();
    expect(screen.getByText(/awaiting a log/)).toBeTruthy();
  });

  it("keeps the overrides collapsed until opened, and open when one is set", async () => {
    mount();
    expect(await screen.findByText(/Criteria overrides/)).toBeTruthy();
    expect(screen.queryByLabelText(/Min duration$/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Criteria overrides/ }));
    expect(screen.getByLabelText(/Min duration$/)).toBeTruthy();
    cleanup();
    mount({ min_duration: { value: 5, unit: "h" } });
    expect(((await screen.findByLabelText("Min duration value")) as HTMLInputElement).value).toBe("5");
  });

  it("writes the min duration override", async () => {
    const { dispatch } = mount();
    fireEvent.click(await screen.findByRole("button", { name: /Criteria overrides/ }));
    fireEvent.click(screen.getByLabelText(/Min duration$/));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastOverrides(dispatch).min_duration).toEqual({ value: 4, unit: "h" });
    fireEvent.change(screen.getByLabelText("Min duration unit"), { target: { value: "min" } });
    fireEvent.change(screen.getByLabelText("Min duration value"), { target: { value: "240" } });
    await waitFor(() =>
      expect(lastOverrides(dispatch).min_duration).toEqual({ value: 240, unit: "min" }),
    { timeout: 2000 });
  });

  it("writes a role maximum and a stabilisation override, and clears them", async () => {
    const { dispatch } = mount({
      role_max: { vibration_filtered: { value: 2.5, unit: "m" } },
    });
    expect(((await screen.findByLabelText("vibration_filtered max value")) as HTMLInputElement).value).toBe("2.5");
    fireEvent.click(screen.getByLabelText(/oil_temperature stabilisation/));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastOverrides(dispatch)).toMatchObject({
      role_max: { vibration_filtered: { value: 2.5, unit: "m" } },
      stabilisation: {
        oil_temperature: { delta: { value: 2, unit: "m" }, window: { value: 60, unit: "min" } },
      },
    });
    fireEvent.click(screen.getByLabelText(/vibration_filtered max$/));
    await waitFor(() => expect(lastOverrides(dispatch).role_max).toEqual({}), { timeout: 2000 });
  });
});
