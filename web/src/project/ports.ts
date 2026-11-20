import type { CatalogEntry } from "../engine/types";
import { type DocEdge, type DocNode, sameEdge } from "./model";

/** Signal types match when equal or when either side is the wildcard "*". */
export function typesMatch(a: string, b: string): boolean {
  return a === b || a === "*" || b === "*";
}

function entryOf(
  nodes: DocNode[],
  catalog: CatalogEntry[],
  nodeId: string,
): CatalogEntry | undefined {
  const node = nodes.find((n) => n.id === nodeId);
  return node ? catalog.find((c) => c.kind === node.kind) : undefined;
}

/**
 * Whether `edge` may be drawn: the source is an output of the source node, the
 * target an input of the target node, the types match, and it is no self-loop.
 */
export function canConnect(
  nodes: DocNode[],
  catalog: CatalogEntry[],
  edge: DocEdge,
): boolean {
  if (edge.src_node === edge.dst_node) return false;
  const src = entryOf(nodes, catalog, edge.src_node);
  const dst = entryOf(nodes, catalog, edge.dst_node);
  if (!src || !dst) return false;
  const out = src.outputs.find((p) => p.name === edge.src_port);
  const inp = dst.inputs.find((p) => p.name === edge.dst_port);
  if (!out || !inp) return false;
  return typesMatch(out.type, inp.type);
}

/**
 * The edge list after connecting `edge`, or `null` when it is refused.  A
 * duplicate returns `edges` itself; a single-input port replaces its edge.
 */
export function connectEdge(
  nodes: DocNode[],
  edges: DocEdge[],
  catalog: CatalogEntry[],
  edge: DocEdge,
): DocEdge[] | null {
  if (!canConnect(nodes, catalog, edge)) return null;
  if (edges.some((e) => sameEdge(e, edge))) return edges;
  const dst = entryOf(nodes, catalog, edge.dst_node);
  const port = dst?.inputs.find((p) => p.name === edge.dst_port);
  const kept = port?.multi
    ? edges
    : edges.filter((e) => !(e.dst_node === edge.dst_node && e.dst_port === edge.dst_port));
  return [...kept, edge];
}
