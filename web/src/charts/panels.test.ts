import { describe, expect, it } from "vitest";
import type { FitSeries, PlotRated } from "../engine/types";
import {
  alignExact,
  alignLine,
  buildNpshPanel,
  buildPanels,
  unionX,
} from "./panels";

const poly = {
  q: [0, 5, 10],
  head: [100, 90, 60],
  power: [10, 15, 20],
  eff: [0, 50, 40],
};
const fit: FitSeries = {
  degree: 3,
  points: { q: [0, 4, 10], head: [100, 92, 60], power: [10, 14, 20], eff: [0, 45, 40] },
  poly,
  spline: { ...poly },
};
const rated: PlotRated = {
  q: 5,
  head: 90,
  power: 15,
  head_fit: 89,
  power_fit: 15.5,
  eff_fit: 50,
  in_range: true,
};
const npsh = {
  npsha: 2.4,
  npshr_quoted: 1.2,
  points: { q: [3, 7], npshr: [1, 2] },
  curve: { q: [3, 5, 7], npshr: [1, 1.5, 2] },
};
const all = { poly: true, spline: true, points: true };

describe("alignment", () => {
  it("unions and sorts the x values", () => {
    expect(unionX([3, 1], [2, 1], null, undefined)).toEqual([1, 2, 3]);
  });
  it("markers sit only at their own x", () => {
    expect(alignExact([0, 4, 5, 10], [0, 4, 10], [1, 2, 3])).toEqual([1, 2, null, 3]);
  });
  it("lines are exact on their samples, joined between them, null outside", () => {
    const xs = [0, 2, 5, 8, 10];
    expect(alignLine(xs, [2, 5, 10], [20, 50, 100])).toEqual([null, 20, 50, 80, 100]);
    expect(alignLine(xs, [], [])).toEqual([null, null, null, null, null]);
  });
});

describe("buildPanels", () => {
  it("builds H, P, η with points + poly + spline each and one shared x grid", () => {
    const panels = buildPanels({ fit, rated, show: all });
    expect(panels.map((p) => p.key)).toEqual(["head", "power", "efficiency"]);
    for (const p of panels) {
      expect(p.series.map((s) => s.style)).toEqual(["markers", "line", "dashed"]);
      expect(p.data).toHaveLength(1 + p.series.length);
      expect(p.data.every((col) => col.length === p.data[0]!.length)).toBe(true);
    }
    expect(panels[0]!.data[0]).toEqual([0, 4, 5, 10]); // union of points and curve x
    expect(panels[0]!.series[1]!.label).toBe("Poly-3");
  });

  it("follows the show flags", () => {
    const only = (show: { poly: boolean; spline: boolean; points: boolean }) =>
      buildPanels({ fit, show })[0]!.series.length;
    expect(only({ poly: true, spline: false, points: true })).toBe(2);
    expect(only({ poly: true, spline: false, points: false })).toBe(1);
    expect(only({ poly: false, spline: false, points: false })).toBe(0);
  });

  it("skips the spline when the view has none and the panels the fit has no data for", () => {
    const bare: FitSeries = {
      points: { q: [0, 10], head: [1, 2], power: null, eff: null },
      poly: { q: [0, 10], head: [1, 2], power: null, eff: null },
      spline: null,
    };
    const panels = buildPanels({ fit: bare, show: all });
    expect(panels.map((p) => p.key)).toEqual(["head"]);
    expect(panels[0]!.series.map((s) => s.label)).toEqual(["Data", "Polynomial"]);
  });

  it("marks the rated point with the fitted value on each panel", () => {
    const panels = buildPanels({ fit, rated, show: all });
    expect(panels.map((p) => p.marks)).toEqual([
      [{ x: 5, y: 89, shape: "cross" }],
      [{ x: 5, y: 15.5, shape: "cross" }],
      [{ x: 5, y: 50, shape: "cross" }],
    ]);
    expect(buildPanels({ fit, show: all })[0]!.marks).toEqual([]);
  });

  it("adds a Q×NPSHr panel with data, fit, NPSHa and the quoted NPSHr", () => {
    const panels = buildPanels({ fit, rated, npsh, show: all, ylims: { head: [0, 400], npsh: [0, 5] } });
    expect(panels.map((p) => p.key)).toEqual(["head", "power", "efficiency", "npsh"]);
    const n = panels[3]!;
    expect(n.series.map((s) => s.label)).toEqual(["NPSH3 data", "NPSHr fit", "NPSHa 2.40 m"]);
    expect(n.marks).toEqual([
      { x: 5, shape: "line" },
      { x: 5, y: 1.2, shape: "diamond" },
    ]);
    expect(n.yRange).toEqual([0, 5]);
    expect(panels[0]!.yRange).toEqual([0, 400]);
    expect(panels[1]!.yRange).toBeNull();
    // the NPSH x values joined the shared grid
    expect(panels[0]!.data[0]).toContain(3);
    expect(n.data[3]!.every((v) => v === 2.4)).toBe(true);
  });

  it("the NPSH form panel stands alone", () => {
    const p = buildNpshPanel(npsh, 5)!;
    expect(p.key).toBe("npsh");
    expect(p.data[0]).toEqual([3, 5, 7]);
    expect(buildNpshPanel({ points: null, curve: null }, null)).toBeNull();
  });
});
