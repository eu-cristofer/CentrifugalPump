import { describe, expect, it } from "vitest";
import { CATALOG, edge } from "./catalog.fixture";
import type { DocNode } from "./model";
import { canConnect, connectEdge, typesMatch } from "./ports";

const node = (id: string, kind: string): DocNode => ({ id, kind, x: 0, y: 0, settings: {} });
const nodes = [
  node("fl1", "fluid"),
  node("fl2", "fluid"),
  node("rp", "rated_point"),
  node("rp2", "rated_point"),
  node("tp", "test_points"),
  node("sk", "sink"),
];

describe("typesMatch", () => {
  it("accepts equal types and the wildcard on either side", () => {
    expect(typesMatch("A", "A")).toBe(true);
    expect(typesMatch("A", "*")).toBe(true);
    expect(typesMatch("*", "B")).toBe(true);
    expect(typesMatch("A", "B")).toBe(false);
  });
});

describe("canConnect", () => {
  it("accepts a matching output into an input", () => {
    expect(canConnect(nodes, CATALOG, edge("fl1", "FluidSpec", "rp", "FluidSpec"))).toBe(true);
  });

  it("refuses a TestPointSet output into a RatedPoint-side input", () => {
    expect(canConnect(nodes, CATALOG, edge("tp", "TestPointSet", "rp", "FluidSpec"))).toBe(false);
    expect(canConnect(nodes, CATALOG, edge("tp", "TestPointSet", "sk", "Many"))).toBe(false);
  });

  it("accepts the wildcard input", () => {
    expect(canConnect(nodes, CATALOG, edge("tp", "TestPointSet", "sk", "Any"))).toBe(true);
  });

  it("refuses self-loops, inputs as sources and unknown ports or nodes", () => {
    expect(canConnect(nodes, CATALOG, edge("rp", "RatedPoint", "rp", "FluidSpec"))).toBe(false);
    expect(canConnect(nodes, CATALOG, edge("rp", "FluidSpec", "tp", "FluidSpec"))).toBe(false);
    expect(canConnect(nodes, CATALOG, edge("fl1", "FluidSpec", "rp", "Nope"))).toBe(false);
    expect(canConnect(nodes, CATALOG, edge("fl1", "FluidSpec", "ghost", "FluidSpec"))).toBe(false);
  });
});

describe("connectEdge", () => {
  const a = edge("fl1", "FluidSpec", "rp", "FluidSpec");
  const b = edge("fl2", "FluidSpec", "rp", "FluidSpec");

  it("replaces the edge of a single-input port", () => {
    expect(connectEdge(nodes, [a], CATALOG, b)).toEqual([b]);
  });

  it("keeps the existing edges of a multi-input port", () => {
    const c = edge("rp", "RatedPoint", "sk", "Many");
    const d = edge("rp2", "RatedPoint", "sk", "Many");
    expect(connectEdge(nodes, [c], CATALOG, d)).toEqual([c, d]);
  });

  it("ignores a duplicate and refuses an invalid edge", () => {
    const edges = [a];
    expect(connectEdge(nodes, edges, CATALOG, { ...a })).toBe(edges);
    expect(connectEdge(nodes, edges, CATALOG, edge("tp", "TestPointSet", "rp", "FluidSpec"))).toBeNull();
  });
});
