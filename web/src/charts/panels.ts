import type { ChartData, ChartMark, ChartSeries } from "./Chart";
import { fixed } from "../decimal";
import type { FitSeries, NpshSeries, PlotRated, PlotShow } from "../engine/types";

export type PanelKey = "head" | "power" | "efficiency" | "npsh";

export interface PanelSpec {
  key: PanelKey;
  yLabel: string;
  data: ChartData;
  series: ChartSeries[];
  marks: ChartMark[];
  yRange: [number, number] | null;
  height: number;
}

export interface NpshExtras {
  npsha?: number | null;
  npshr_quoted?: number | null;
}

export interface PanelInput {
  fit: FitSeries;
  rated?: PlotRated | null;
  npsh?: (NpshSeries & NpshExtras) | null;
  show: PlotShow;
  /** y limits in canonical units (m, kW, %, m); null/absent = auto */
  ylims?: Partial<Record<PanelKey, [number, number] | null>>;
}

export const X_LABEL = "Capacity Q (m³/h)";

const HEIGHT: Record<PanelKey, number> = { head: 210, power: 140, efficiency: 150, npsh: 150 };

/** Sorted unique values of the given lists. */
export function unionX(...lists: Array<number[] | null | undefined>): number[] {
  const set = new Set<number>();
  for (const l of lists) for (const v of l ?? []) set.add(v);
  return [...set].sort((a, b) => a - b);
}

/** `y` at exactly the `x` positions of the layer; null elsewhere (markers). */
export function alignExact(xs: number[], x: number[], y: Array<number | null>): Array<number | null> {
  const at = new Map<number, number | null>();
  x.forEach((v, i) => at.set(v, y[i] ?? null));
  return xs.map((v) => at.get(v) ?? null);
}

/**
 * A line layer on the shared x grid: exact where the layer has a sample, linearly
 * joined between its neighbours (so the hover readout has a value at every grid
 * point inside its range), null outside its range.
 */
export function alignLine(xs: number[], x: number[], y: Array<number | null>): Array<number | null> {
  const pts = x
    .map((v, i): [number, number | null] => [v, y[i] ?? null])
    .filter((p): p is [number, number] => p[1] !== null)
    .sort((a, b) => a[0] - b[0]);
  if (pts.length === 0) return xs.map(() => null);
  const first = pts[0]![0];
  const last = pts[pts.length - 1]![0];
  let k = 0;
  return xs.map((v) => {
    if (v < first || v > last) return null;
    while (k < pts.length - 2 && pts[k + 1]![0] < v) k += 1;
    const [x0, y0] = pts[k]!;
    const [x1, y1] = pts[Math.min(k + 1, pts.length - 1)]!;
    if (v === x0) return y0;
    if (v === x1 || x1 === x0) return y1;
    return y0 + ((y1 - y0) * (v - x0)) / (x1 - x0);
  });
}

type Field = "head" | "power" | "eff";
const FIELD: Record<Exclude<PanelKey, "npsh">, { f: Field; token: string; label: string }> = {
  head: { f: "head", token: "--chart-head", label: "Head (m)" },
  power: { f: "power", token: "--chart-power", label: "Power (kW)" },
  efficiency: { f: "eff", token: "--chart-efficiency", label: "Efficiency (%)" },
};

function npshPanel(
  xs: number[],
  npsh: NpshSeries & NpshExtras,
  ratedQ: number | null,
  show: PlotShow,
  yRange: [number, number] | null,
): PanelSpec | null {
  if (!npsh.curve) return null;
  const data: ChartData = [xs];
  const series: ChartSeries[] = [];
  if (show.points && npsh.points) {
    data.push(alignExact(xs, npsh.points.q, npsh.points.npshr));
    series.push({ label: "NPSH3 data", token: "--chart-npsh", style: "markers" });
  }
  data.push(alignLine(xs, npsh.curve.q, npsh.curve.npshr));
  series.push({ label: "NPSHr fit", token: "--chart-npsh", style: "line" });
  if (npsh.npsha !== null && npsh.npsha !== undefined) {
    data.push(xs.map(() => npsh.npsha ?? null));
    series.push({
      label: `NPSHa ${fixed(npsh.npsha, 2)} m`,
      token: "--chart-npsha",
      style: "dashdot",
    });
  }
  const marks: ChartMark[] = [];
  if (ratedQ !== null) {
    marks.push({ x: ratedQ, shape: "line" });
    if (npsh.npshr_quoted !== null && npsh.npshr_quoted !== undefined) {
      marks.push({ x: ratedQ, y: npsh.npshr_quoted, shape: "diamond" });
    }
  }
  return { key: "npsh", yLabel: "NPSHr (m)", data, series, marks, yRange, height: HEIGHT.npsh };
}

/**
 * The stacked panels of the Performance Plot (UI_SPEC §5.5): Q×H, Q×P, Q×η and, when
 * an NPSH result is wired, Q×NPSHr, all on one x grid.  Everything plotted is
 * Python data; the only arithmetic is aligning the layers onto the shared grid.
 */
export function buildPanels({ fit, rated = null, npsh = null, show, ylims = {} }: PanelInput): PanelSpec[] {
  const xs = unionX(fit.points.q, fit.poly.q, fit.spline?.q, npsh?.points?.q, npsh?.curve?.q);
  const panels: PanelSpec[] = [];
  const keys: Array<Exclude<PanelKey, "npsh">> = ["head", "power", "efficiency"];
  for (const key of keys) {
    const { f, token, label } = FIELD[key];
    const pts = fit.points[f];
    if (key !== "head" && !pts) continue; // no power / efficiency data in this fit
    const data: ChartData = [xs];
    const series: ChartSeries[] = [];
    if (show.points && pts) {
      data.push(alignExact(xs, fit.points.q, pts));
      series.push({ label: "Data", token, style: "markers" });
    }
    const poly = fit.poly[f];
    if (show.poly && poly) {
      data.push(alignLine(xs, fit.poly.q, poly));
      series.push({ label: fit.degree ? `Poly-${fit.degree}` : "Polynomial", token, style: "line" });
    }
    const spl = fit.spline?.[f];
    if (show.spline && fit.spline && spl) {
      data.push(alignLine(xs, fit.spline.q, spl));
      series.push({ label: "Spline", token, style: "dashed" });
    }
    const fitted =
      key === "head" ? rated?.head_fit : key === "power" ? rated?.power_fit : rated?.eff_fit;
    const marks: ChartMark[] =
      rated && fitted !== null && fitted !== undefined
        ? [{ x: rated.q, y: fitted, shape: "cross" }]
        : [];
    panels.push({
      key,
      yLabel: label,
      data,
      series,
      marks,
      yRange: ylims[key] ?? null,
      height: HEIGHT[key],
    });
  }
  if (npsh) {
    const p = npshPanel(xs, npsh, rated?.q ?? null, show, ylims.npsh ?? null);
    if (p) panels.push(p);
  }
  return panels;
}

/** The single NPSHr chart of the NPSH form (NPSHr points + fit + NPSHa + quoted NPSHr). */
export function buildNpshPanel(
  npsh: NpshSeries & NpshExtras,
  ratedQ: number | null,
): PanelSpec | null {
  const xs = unionX(npsh.points?.q, npsh.curve?.q);
  return npshPanel(xs, npsh, ratedQ, { poly: true, spline: false, points: true }, null);
}
