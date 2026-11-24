import type { PumpflowDoc } from "../engine/types";

/** One node of a schema-v2 `.pumpflow` document. */
export interface DocNode {
  id: string;
  kind: string;
  x: number;
  y: number;
  settings: Record<string, unknown>;
}

/** One edge of a schema-v2 `.pumpflow` document. */
export interface DocEdge {
  src_node: string;
  src_port: string;
  dst_node: string;
  dst_port: string;
}

/** The viewport as the desktop saves it: scene coordinates of the view centre. */
export interface View {
  zoom: number;
  cx: number;
  cy: number;
}

export function docNodes(doc: PumpflowDoc): DocNode[] {
  return Array.isArray(doc.nodes) ? (doc.nodes as DocNode[]) : [];
}

export function docEdges(doc: PumpflowDoc): DocEdge[] {
  return Array.isArray(doc.edges) ? (doc.edges as DocEdge[]) : [];
}

export function docView(doc: PumpflowDoc): View | null {
  const v = doc.view as Partial<View> | undefined;
  if (
    v &&
    typeof v.zoom === "number" &&
    typeof v.cx === "number" &&
    typeof v.cy === "number"
  ) {
    return { zoom: v.zoom, cx: v.cx, cy: v.cy };
  }
  return null;
}

export function edgeId(e: DocEdge): string {
  return `${e.src_node}:${e.src_port}->${e.dst_node}:${e.dst_port}`;
}

export function sameEdge(a: DocEdge, b: DocEdge): boolean {
  return edgeId(a) === edgeId(b);
}

/** `${kind}-${n}` with the smallest n >= 1 that is not taken. */
export function newNodeId(kind: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  let n = 1;
  while (used.has(`${kind}-${n}`)) n += 1;
  return `${kind}-${n}`;
}
