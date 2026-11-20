import type { CatalogEntry } from "../engine/types";

/** A small catalog with the real kinds, port names and types the tests need. */
export const CATALOG: CatalogEntry[] = [
  {
    kind: "fluid",
    title: "Fluid",
    glyph: "F",
    group: "Inputs",
    inputs: [],
    outputs: [{ name: "FluidSpec", type: "FluidSpec" }],
    has_web_form: true,
  },
  {
    kind: "rated_point",
    title: "Rated point",
    glyph: "R",
    group: "Inputs",
    inputs: [{ name: "FluidSpec", type: "FluidSpec", multi: false }],
    outputs: [{ name: "RatedPoint", type: "RatedPoint" }],
    has_web_form: true,
  },
  {
    kind: "test_points",
    title: "Test points",
    glyph: "T",
    group: "Inputs",
    inputs: [{ name: "FluidSpec", type: "FluidSpec", multi: false }],
    outputs: [{ name: "TestPointSet", type: "TestPointSet" }],
    has_web_form: true,
  },
  {
    kind: "sink",
    title: "Sink",
    glyph: "S",
    group: "Output",
    inputs: [
      { name: "Any", type: "*", multi: false },
      { name: "Many", type: "RatedPoint", multi: true },
    ],
    outputs: [],
    has_web_form: false,
  },
];

export const edge = (
  src_node: string,
  src_port: string,
  dst_node: string,
  dst_port: string,
) => ({ src_node, src_port, dst_node, dst_port });
