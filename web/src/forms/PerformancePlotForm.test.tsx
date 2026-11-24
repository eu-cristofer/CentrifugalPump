import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { plots, resetPlots } from "../charts/uplotMock";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import PerformancePlotForm from "./PerformancePlotForm";

vi.mock("uplot", async () => ({ default: (await import("../charts/uplotMock")).FakePlot }));

beforeEach(resetPlots);
afterEach(cleanup);

const block = { q: [1, 2, 3], head: [30, 20, 10], power: [1, 2, 3], eff: [10, 20, 15] };

const settings = (extra: Record<string, unknown> = {}) => ({
  show_poly: true,
  show_spline: true,
  show_points: true,
  head_ylim: null,
  head_ylim_unit: "m",
  power_ylim: null,
  power_ylim_unit: "kW",
  eff_ylim: null,
  eff_ylim_unit: "%",
  ...extra,
});

const res = (withFit = true): NodeResult => ({
  kind: "performance_plot",
  state: withFit ? "ok" : "idle",
  status: withFit ? "P-9001A · plotted" : "Waiting for fitted model",
  badge: null,
  notes: [],
  view: withFit
    ? {
        pump_tag: "P-9001A",
        fit: { degree: 3, points: block, poly: block, spline: block },
        rated: { q: 2, head: 20, power: 2, head_fit: 20, power_fit: 2, eff_fit: 20, in_range: true },
        npsh: {
          npsha: 2.4,
          npshr_quoted: 1.2,
          points: { q: [1, 3], npshr: [1, 2] },
          curve: { q: [1, 2, 3], npshr: [1, 1.5, 2] },
        },
        show: { poly: true, spline: true, points: true },
      }
    : {},
});

function mount(s: Record<string, unknown>, r: NodeResult = res(), dispatch = vi.fn()) {
  const doc: PumpflowDoc = {
    nodes: [{ id: "performance_plot-1", kind: "performance_plot", x: 0, y: 0, settings: s }],
    edges: [],
  };
  const engine = fakeEngine();
  render(
    <EngineContext.Provider value={engine}>
      <PerformancePlotForm nodeId="performance_plot-1" doc={doc} result={r} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return { dispatch, engine };
}

const lastSettings = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings as Record<string, unknown>;

describe("PerformancePlotForm", () => {
  it("draws the stacked charts and shows the curve toggles", async () => {
    mount(settings());
    expect(await screen.findByLabelText(/Polynomial curve/)).toBeTruthy();
    expect(screen.getByLabelText(/Spline \(dashed\)/)).toBeTruthy();
    expect(screen.getByLabelText(/Data points/)).toBeTruthy();
    await waitFor(() => expect(plots.length).toBeGreaterThanOrEqual(4));
    const last = plots.slice(-4);
    expect(last.map((p) => p.opts.series.length)).toEqual([4, 4, 4, 4]);
  });

  it("follows the settings at once: unticking the spline drops its series and is saved", async () => {
    const { dispatch } = mount(settings());
    fireEvent.click(await screen.findByLabelText(/Spline \(dashed\)/));
    await waitFor(() => expect(plots.slice(-3).map((p) => p.opts.series.length)).toEqual([3, 3, 3]));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({ show_spline: false, show_poly: true });
  });

  it("fixes an axis range: unticking auto starts from a default range", async () => {
    const { dispatch } = mount(settings());
    const auto = await screen.findByLabelText(/Head auto/);
    expect((screen.getByLabelText("Head min") as HTMLInputElement).disabled).toBe(true);
    fireEvent.click(auto);
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({ head_ylim: [0, 100], head_ylim_unit: "m" });
  });

  it("applies a stored range to its chart (converted by Python) and edits it", async () => {
    const { dispatch } = mount(settings({ head_ylim: [10, 50] }));
    const min = (await screen.findByLabelText("Head min")) as HTMLInputElement;
    expect(min.value).toBe("10");
    await waitFor(() => {
      const head = plots.at(-4)!;
      expect(head.opts.scales?.y).toEqual({ auto: false, range: [10, 50] });
    });
    fireEvent.change(screen.getByLabelText("Head max"), { target: { value: "60" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch).head_ylim).toEqual([10, 60]);
  });

  it("shows the node status instead of a chart while there is no model", async () => {
    mount(settings(), res(false));
    expect(await screen.findByText("Waiting for fitted model")).toBeTruthy();
    expect(plots).toHaveLength(0);
  });
});
