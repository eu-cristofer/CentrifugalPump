import { useId } from "react";
import type { FitSeries, NpshSeries, PlotRated, PlotShow } from "../engine/types";
import Chart from "./Chart";
import { type NpshExtras, type PanelKey, X_LABEL, buildNpshPanel, buildPanels } from "./panels";

export interface PerformanceChartProps {
  fit: FitSeries;
  rated?: PlotRated | null;
  npsh?: (NpshSeries & NpshExtras) | null;
  show: PlotShow;
  ylims?: Partial<Record<PanelKey, [number, number] | null>>;
}

/**
 * Stacked Q×H / Q×P / Q×η (+ Q×NPSHr) panels with measured points, the polynomial,
 * the dashed spline, the rated-point crosshair and a hover readout.  The panels
 * share the cursor and the x range.
 */
export default function PerformanceChart(props: PerformanceChartProps) {
  const sync = useId();
  const panels = buildPanels(props);
  return (
    <div className="chart-stack" aria-label="Performance curves">
      {panels.map((p, i) => (
        <Chart
          key={p.key}
          data={p.data}
          series={p.series}
          yLabel={p.yLabel}
          xLabel={i === panels.length - 1 ? X_LABEL : undefined}
          showXAxis={i === panels.length - 1}
          yRange={p.yRange}
          height={p.height}
          marks={p.marks}
          syncKey={`perf${sync}`}
        />
      ))}
    </div>
  );
}

export interface NpshChartProps {
  npsh: NpshSeries & NpshExtras;
  ratedQ: number | null;
}

/** NPSHr test points, their fit, NPSHa and the quoted NPSHr at the rated flow. */
export function NpshChart({ npsh, ratedQ }: NpshChartProps) {
  const p = buildNpshPanel(npsh, ratedQ);
  if (!p) return null;
  return (
    <Chart
      data={p.data}
      series={p.series}
      yLabel={p.yLabel}
      xLabel={X_LABEL}
      marks={p.marks}
      height={200}
    />
  );
}
