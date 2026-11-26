import { useEffect, useRef, useState } from "react";
import { localizeNumber } from "../decimal";
import uPlot from "uplot";
import "./chart.css";

/** How a series is drawn. */
export type SeriesStyle = "line" | "dashed" | "dashdot" | "markers";

export interface ChartSeries {
  label: string;
  /** CSS custom property holding the colour, e.g. `--chart-head` (read at runtime) */
  token: string;
  style: SeriesStyle;
}

/** A rated-point decoration: a dotted vertical line, a cross with crosshair, or a hollow diamond. */
export interface ChartMark {
  x: number;
  y?: number | null;
  shape: "line" | "cross" | "diamond";
}

export type ChartData = Array<Array<number | null>>;

export interface ChartProps {
  /** `[x, y1, y2, ...]` columns of equal length; `series[i]` describes `data[i + 1]` */
  data: ChartData;
  series: ChartSeries[];
  yLabel: string;
  xLabel?: string;
  /** fixed y range; auto when null/undefined */
  yRange?: [number, number] | null;
  height?: number;
  /** charts with the same key share the cursor and the x range */
  syncKey?: string;
  marks?: ChartMark[];
  /** draw the x axis (the bottom chart of a stack only) */
  showXAxis?: boolean;
  ariaLabel?: string;
}

const Y_AXIS_SIZE = 62;
const MIN_WIDTH = 200;

/** The value of a CSS custom property of the page (design tokens only; no colour literals). */
export function cssVar(name: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || "currentColor";
}

const fmt = (v: number | null | undefined): string => {
  if (v === null || v === undefined) return "—";
  const a = Math.abs(v);
  return localizeNumber(a >= 1000 ? v.toFixed(0) : a >= 100 ? v.toFixed(1) : v.toFixed(2));
};

function seriesOptions(s: ChartSeries): uPlot.Series {
  const stroke = cssVar(s.token);
  const base: uPlot.Series = {
    label: s.label,
    stroke,
    value: (_u, v) => fmt(v),
  };
  switch (s.style) {
    case "markers":
      return {
        ...base,
        paths: () => null,
        points: { show: true, size: 7, stroke, fill: stroke, width: 1 },
      };
    case "dashed":
      return { ...base, width: 1.5, dash: [6, 4], points: { show: false } };
    case "dashdot":
      return { ...base, width: 1.5, dash: [8, 3, 2, 3], points: { show: false } };
    default:
      return { ...base, width: 2, points: { show: false } };
  }
}

function drawMarks(u: uPlot, marks: ChartMark[], color: string): void {
  if (marks.length === 0) return;
  const { ctx } = u;
  const { left, top, width, height } = u.bbox;
  const px = window.devicePixelRatio || 1;
  ctx.save();
  ctx.beginPath();
  ctx.rect(left, top, width, height);
  ctx.clip();
  ctx.strokeStyle = color;
  for (const m of marks) {
    const cx = u.valToPos(m.x, "x", true);
    const cy = m.y === null || m.y === undefined ? null : u.valToPos(m.y, "y", true);
    if (m.shape === "diamond") {
      if (cy === null) continue;
      const r = 5 * px;
      ctx.setLineDash([]);
      ctx.lineWidth = 1.4 * px;
      ctx.beginPath();
      ctx.moveTo(cx, cy - r);
      ctx.lineTo(cx + r, cy);
      ctx.lineTo(cx, cy + r);
      ctx.lineTo(cx - r, cy);
      ctx.closePath();
      ctx.stroke();
      continue;
    }
    ctx.globalAlpha = 0.7;
    ctx.setLineDash([2 * px, 3 * px]);
    ctx.lineWidth = px;
    ctx.beginPath();
    ctx.moveTo(cx, top);
    ctx.lineTo(cx, top + height);
    if (m.shape === "cross" && cy !== null) {
      ctx.moveTo(left, cy);
      ctx.lineTo(left + width, cy);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
    if (m.shape === "cross" && cy !== null) {
      const r = 5 * px;
      ctx.setLineDash([]);
      ctx.lineWidth = 1.6 * px;
      ctx.beginPath();
      ctx.moveTo(cx - r, cy - r);
      ctx.lineTo(cx + r, cy + r);
      ctx.moveTo(cx - r, cy + r);
      ctx.lineTo(cx + r, cy - r);
      ctx.stroke();
    }
  }
  ctx.restore();
}

/**
 * One uPlot chart: created on mount, `setData` when only the data changes,
 * `setSize` on resize, destroyed on unmount.  Colours come from the `--chart-*`
 * CSS variables at creation time; the series values are plotted as given (the
 * browser evaluates no curves).
 */
export default function Chart({
  data,
  series,
  yLabel,
  xLabel,
  yRange = null,
  height = 180,
  syncKey,
  marks = [],
  showXAxis = true,
  ariaLabel,
}: ChartProps) {
  const host = useRef<HTMLDivElement>(null);
  const plot = useRef<uPlot | null>(null);
  const applied = useRef<ChartData | null>(null);
  const latest = useRef({ data, marks });
  latest.current = { data, marks };
  const [failed, setFailed] = useState(false);

  // everything but the data and the marks: a change rebuilds the chart
  const structure = JSON.stringify([series, yLabel, xLabel, yRange, height, syncKey, showXAxis]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const ink = cssVar("--chart-ink");
    const tick = cssVar("--chart-tick");
    const grid = cssVar("--chart-grid");
    const frame = cssVar("--chart-frame");
    // uPlot measures and draws on a canvas: it needs a concrete CSS font string
    // ("inherit" leaves the tick labels unmeasured and invisible).
    const family = cssVar("--font-sans").replace(/^currentColor$/, "sans-serif");
    const tickFont = `${cssVar("--fs-caption").replace(/^currentColor$/, "11px")} ${family}`;
    const labelFont = `${cssVar("--fs-body").replace(/^currentColor$/, "13px")} ${family}`;
    const axis = (label: string | undefined, size?: number): uPlot.Axis => ({
      stroke: tick,
      grid: { stroke: grid, width: 1 },
      ticks: { stroke: frame, width: 1 },
      ...(label ? { label, labelSize: 18, labelFont } : {}),
      ...(size ? { size } : {}),
      font: tickFont,
    });
    const xAxis = axis(xLabel);
    xAxis.show = showXAxis;
    const opts: uPlot.Options = {
      width: Math.max(MIN_WIDTH, Math.floor(el.clientWidth) || 360),
      height,
      padding: [8, 12, 0, 0],
      legend: { live: true },
      cursor: syncKey
        ? { sync: { key: syncKey }, drag: { x: true, y: false } }
        : { drag: { x: true, y: false } },
      scales: {
        x: { time: false },
        y: yRange ? { auto: false, range: yRange } : { auto: true },
      },
      axes: [xAxis, axis(yLabel, Y_AXIS_SIZE)],
      series: [
        { label: xLabel ?? "Q", value: (_u, v) => fmt(v) },
        ...series.map(seriesOptions),
      ],
      hooks: { draw: [(u) => drawMarks(u, latest.current.marks, ink)] },
    };
    let u: uPlot;
    try {
      u = new uPlot(opts, latest.current.data as uPlot.AlignedData, el);
    } catch {
      setFailed(true);
      return;
    }
    setFailed(false);
    plot.current = u;
    applied.current = latest.current.data;
    const ro = new ResizeObserver((entries) => {
      const w = Math.floor(entries[0]?.contentRect.width ?? 0);
      if (w >= MIN_WIDTH && w !== u.width) u.setSize({ width: w, height });
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      u.destroy();
      plot.current = null;
      applied.current = null;
    };
    // `structure` stands for every input of the options except data and marks
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [structure]);

  useEffect(() => {
    const u = plot.current;
    if (u && applied.current !== data) {
      applied.current = data;
      u.setData(data as uPlot.AlignedData);
    }
  }, [data]);

  const marksKey = JSON.stringify(marks);
  useEffect(() => {
    plot.current?.redraw(false);
  }, [marksKey]);

  return (
    <div className="chart" role="group" aria-label={ariaLabel ?? yLabel}>
      <div ref={host} className="chart-host" />
      {failed && <p className="field-hint">The chart could not be drawn in this browser.</p>}
    </div>
  );
}
