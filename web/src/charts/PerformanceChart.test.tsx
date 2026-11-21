import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FitSeries } from "../engine/types";
import PerformanceChart, { NpshChart } from "./PerformanceChart";
import { plots, resetPlots } from "./uplotMock";

vi.mock("uplot", async () => ({ default: (await import("./uplotMock")).FakePlot }));

beforeEach(resetPlots);
afterEach(cleanup);

const block = { q: [1, 2, 3], head: [30, 20, 10], power: [1, 2, 3], eff: [10, 20, 15] };
const fit: FitSeries = { degree: 3, points: block, poly: block, spline: block };
const npsh = {
  npsha: 2.4,
  npshr_quoted: null,
  points: { q: [1, 3], npshr: [1, 2] },
  curve: { q: [1, 2, 3], npshr: [1, 1.5, 2] },
};

describe("PerformanceChart", () => {
  it("draws one chart per panel, sharing the cursor, x label on the last", () => {
    render(<PerformanceChart fit={fit} show={{ poly: true, spline: true, points: true }} npsh={npsh} />);
    expect(plots).toHaveLength(4);
    expect(plots.map((p) => p.opts.series.length)).toEqual([4, 4, 4, 4]); // x + 3 / x + 3
    expect(new Set(plots.map((p) => p.opts.cursor?.sync?.key)).size).toBe(1);
    expect(plots.map((p) => p.opts.axes?.[0]?.show)).toEqual([false, false, false, true]);
    expect(plots[3]!.opts.axes?.[0]?.label).toMatch(/Capacity/);
  });

  it("has the right series count for the show flags", () => {
    render(<PerformanceChart fit={fit} show={{ poly: true, spline: false, points: true }} />);
    expect(plots).toHaveLength(3);
    expect(plots.map((p) => p.opts.series.length)).toEqual([3, 3, 3]);
    cleanup();
    resetPlots();
    render(<PerformanceChart fit={fit} show={{ poly: true, spline: false, points: false }} />);
    expect(plots.map((p) => p.opts.series.length)).toEqual([2, 2, 2]);
  });

  it("passes the Python series lengths through unchanged", () => {
    render(<PerformanceChart fit={fit} show={{ poly: true, spline: true, points: true }} />);
    const data = plots[0]!.data as Array<Array<number | null>>;
    expect(data[0]).toEqual([1, 2, 3]);
    expect(data[1]).toEqual([30, 20, 10]);
  });
});

describe("NpshChart", () => {
  it("plots NPSHr data, fit and the NPSHa line", () => {
    render(<NpshChart npsh={npsh} ratedQ={2} />);
    expect(plots).toHaveLength(1);
    expect(plots[0]!.opts.series.slice(1).map((s) => s.label)).toEqual([
      "NPSH3 data",
      "NPSHr fit",
      "NPSHa 2.40 m",
    ]);
    expect(screen.getByRole("group", { name: "NPSHr (m)" })).toBeTruthy();
  });

  it("renders nothing without a fitted curve", () => {
    render(<NpshChart npsh={{ points: null, curve: null }} ratedQ={null} />);
    expect(plots).toHaveLength(0);
  });
});
