import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Chart, { type ChartSeries, cssVar } from "./Chart";
import { failure, plots, resetPlots } from "./uplotMock";

vi.mock("uplot", async () => ({ default: (await import("./uplotMock")).FakePlot }));

beforeEach(resetPlots);
afterEach(cleanup);

const series: ChartSeries[] = [
  { label: "Data", token: "--chart-head", style: "markers" },
  { label: "Poly-3", token: "--chart-head", style: "line" },
  { label: "Spline", token: "--chart-head", style: "dashed" },
];
const x = [1, 2, 3, 4];
const data = [x, [1, null, 3, null], [1, 2, 3, 4], [1, 2, 2, 4]];

describe("Chart", () => {
  it("passes the data and one series per column (plus x) to uPlot", () => {
    render(<Chart data={data} series={series} yLabel="Head (m)" />);
    expect(plots).toHaveLength(1);
    const p = plots[0]!;
    expect(p.data).toBe(data);
    expect(p.opts.series).toHaveLength(4);
    expect(p.opts.series.slice(1).map((s) => s.label)).toEqual(["Data", "Poly-3", "Spline"]);
    expect(p.opts.series[3]!.dash).toEqual([6, 4]);
    expect(p.opts.series[1]!.paths).toBeTypeOf("function"); // markers: no connecting line
    expect(p.opts.width).toBeGreaterThanOrEqual(200);
    expect(p.target.parentElement?.getAttribute("aria-label")).toBe("Head (m)");
  });

  it("reads the series colours from the CSS custom properties", () => {
    document.documentElement.style.setProperty("--chart-head", "rgb(1, 2, 3)");
    expect(cssVar("--chart-head")).toBe("rgb(1, 2, 3)");
    render(<Chart data={data} series={series} yLabel="Head (m)" />);
    expect(plots[0]!.opts.series[2]!.stroke).toBe("rgb(1, 2, 3)");
    document.documentElement.style.removeProperty("--chart-head");
  });

  it("only calls setData when the data changes and keeps the same plot", () => {
    const { rerender } = render(<Chart data={data} series={series} yLabel="Head (m)" />);
    rerender(<Chart data={data} series={series} yLabel="Head (m)" />);
    expect(plots[0]!.setData).not.toHaveBeenCalled();
    const next = [x, [1, 2, 3, 4], [4, 3, 2, 1], [1, 1, 1, 1]];
    rerender(<Chart data={next} series={series} yLabel="Head (m)" />);
    expect(plots).toHaveLength(1);
    expect(plots[0]!.setData).toHaveBeenCalledWith(next);
  });

  it("rebuilds when the series set or the y range changes, destroying the old plot", () => {
    const { rerender } = render(<Chart data={data} series={series} yLabel="Head (m)" />);
    rerender(<Chart data={data} series={series.slice(0, 2)} yLabel="Head (m)" />);
    expect(plots).toHaveLength(2);
    expect(plots[0]!.destroy).toHaveBeenCalledTimes(1);
    expect(plots[1]!.opts.series).toHaveLength(3);
    rerender(<Chart data={data} series={series.slice(0, 2)} yLabel="Head (m)" yRange={[10, 50]} />);
    expect(plots).toHaveLength(3);
    expect(plots[2]!.opts.scales?.y).toEqual({ auto: false, range: [10, 50] });
  });

  it("destroys the plot on unmount", () => {
    const { unmount } = render(<Chart data={data} series={series} yLabel="Head (m)" />);
    unmount();
    expect(plots[0]!.destroy).toHaveBeenCalledTimes(1);
  });

  it("redraws when only the marks change, and syncs the cursor by key", () => {
    const { rerender } = render(
      <Chart data={data} series={series} yLabel="Head (m)" syncKey="k" marks={[{ x: 2, y: 1, shape: "cross" }]} />,
    );
    expect(plots[0]!.opts.cursor?.sync?.key).toBe("k");
    rerender(
      <Chart data={data} series={series} yLabel="Head (m)" syncKey="k" marks={[{ x: 3, y: 1, shape: "cross" }]} />,
    );
    expect(plots).toHaveLength(1);
    expect(plots[0]!.redraw).toHaveBeenCalled();
  });

  it("hides the x axis unless asked, and says so when the chart cannot be created", () => {
    render(<Chart data={data} series={series} yLabel="Head (m)" showXAxis={false} />);
    expect(plots[0]!.opts.axes?.[0]?.show).toBe(false);
    cleanup();
    failure.next = true;
    render(<Chart data={data} series={series} yLabel="Head (m)" />);
    expect(screen.getByText(/could not be drawn/)).toBeTruthy();
  });
});
