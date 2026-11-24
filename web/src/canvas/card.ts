import type { Badge, NodeState, Tone } from "../engine/types";

/** Below this zoom only the title and a large verdict (or glyph) are drawn. */
export const LOW_DETAIL_ZOOM = 0.75;

/** State glyph drawn in the dot, so state never relies on colour alone. */
export const STATE_GLYPH: Partial<Record<NodeState, string>> = {
  ok: "✓",
  invalid: "!",
  error: "✗",
  reject: "✗",
};

const STATE_COLOR: Record<NodeState, string> = {
  idle: "var(--subtle-text)",
  ok: "var(--ok-green)",
  invalid: "var(--amber)",
  error: "var(--reject-red)",
  reject: "var(--reject-red)",
};

const TONE_COLORS: Record<Tone, { fill: string; text: string }> = {
  ok: { fill: "var(--ok-green)", text: "var(--title-text)" },
  fail: { fill: "var(--reject-red)", text: "var(--title-text)" },
  warn: { fill: "var(--amber)", text: "var(--body-text)" },
};

const PORT_TYPES = new Set([
  "RatedPoint",
  "FluidSpec",
  "TestPointSet",
  "CorrectedCurve",
  "FittedModel",
  "ComplianceResult",
]);

/** "RatedPoint" -> "rated-point". */
export function kebab(name: string): string {
  return name.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
}

/** CSS colour of a port by signal type; unknown types use the bundle colour. */
export function portColor(type: string): string {
  return PORT_TYPES.has(type) ? `var(--port-${kebab(type)})` : "var(--port-branch-bundle)";
}

export function toneColors(tone: Tone): { fill: string; text: string } {
  return TONE_COLORS[tone];
}

export function stateColor(state: NodeState): string {
  return STATE_COLOR[state] ?? STATE_COLOR.idle;
}

/**
 * The status line without the segment the verdict pill already shows
 * (port of `_status_beside` in pumpflow/canvas/node_item.py).
 */
export function statusBeside(status: string, badge: Badge | null | undefined): string {
  const text = (status || "").replace(/\n/g, " ");
  if (!badge) return text;
  const word = badge[0];
  const kept = text.split(" · ").filter((seg) => !seg.trim().startsWith(word));
  return kept.join(" · ");
}
