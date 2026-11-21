import { describe, expect, it } from "vitest";
import type { PumpflowDoc } from "../engine/types";
import { docNodes } from "./model";
import { type Action, INITIAL_STATE, type ProjectState, reduce } from "./store";

const run = (state: ProjectState, ...actions: Action[]) => actions.reduce(reduce, state);

const doc = (): PumpflowDoc => ({
  meta: { unit_preset: "SI", schema_version: 2 },
  nodes: [
    { id: "fluid-1", kind: "fluid", x: 0, y: 0, settings: { name: "A" } },
    { id: "rated_point-1", kind: "rated_point", x: 300, y: 0, settings: { tag: "T" } },
  ],
  edges: [],
});

const opened = () => run(INITIAL_STATE, { type: "open", doc: doc(), name: "p.pumpflow" });

describe("setSettings", () => {
  it("replaces one node's settings, marks dirty and is one undo step", () => {
    const s0 = opened();
    const next = { tag: "B-1" };
    const s1 = run(s0, { type: "setSettings", id: "rated_point-1", settings: next });
    const nodes = docNodes(s1.doc!);
    expect(nodes.find((n) => n.id === "rated_point-1")!.settings).toBe(next);
    expect(nodes.find((n) => n.id === "fluid-1")!.settings).toEqual({ name: "A" });
    expect(s1.dirty).toBe(true);
    expect(s1.past).toHaveLength(1);
    const s2 = run(s1, { type: "undo" });
    expect(docNodes(s2.doc!).find((n) => n.id === "rated_point-1")!.settings).toEqual({ tag: "T" });
    expect(s2.dirty).toBe(false);
  });

  it("is a no-op for an unknown node, the same settings object or no document", () => {
    const s0 = opened();
    const same = docNodes(s0.doc!)[0]!.settings;
    expect(run(s0, { type: "setSettings", id: "nope", settings: {} })).toBe(s0);
    expect(run(s0, { type: "setSettings", id: "fluid-1", settings: same })).toBe(s0);
    expect(run(INITIAL_STATE, { type: "setSettings", id: "fluid-1", settings: {} })).toBe(
      INITIAL_STATE,
    );
  });
});
