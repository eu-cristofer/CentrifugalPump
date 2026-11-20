import { act, renderHook } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { EvaluateResult, PumpflowDoc } from "../engine/types";
import { CATALOG, edge } from "./catalog.fixture";
import { docEdges, docNodes, newNodeId } from "./model";
import {
  type Action,
  EVAL_DELAY_MS,
  INITIAL_STATE,
  MAX_HISTORY,
  type ProjectState,
  reduce,
  saveDocument,
  serializeDocument,
  useProject,
} from "./store";

const example = (name: string): PumpflowDoc =>
  JSON.parse(
    readFileSync(path.resolve(import.meta.dirname, "../../../examples/user", name), "utf8"),
  ) as PumpflowDoc;

const run = (state: ProjectState, ...actions: Action[]) => actions.reduce(reduce, state);

const small = (): PumpflowDoc => ({
  meta: { unit_preset: "SI", schema_version: 2 },
  nodes: [
    { id: "fluid-1", kind: "fluid", x: 0, y: 0, settings: {} },
    { id: "rated_point-1", kind: "rated_point", x: 300, y: 0, settings: {} },
  ],
  edges: [],
  extra: { keep: "me" },
});

describe("open and save", () => {
  it.each(["B-34004A_MRT_reference.pumpflow", "B-34004B_witness_2026-11-19.pumpflow"])(
    "returns %s unchanged except view",
    (file) => {
      const input = example(file);
      const state = run(INITIAL_STATE, { type: "open", doc: input, name: file });
      expect(state.dirty).toBe(false);
      const withoutView = (d: PumpflowDoc) => Object.fromEntries(Object.entries(d).filter(([k]) => k !== "view"));
      expect(withoutView(saveDocument(state.doc!))).toEqual(withoutView(input));
      expect(JSON.parse(serializeDocument(state.doc!))).toEqual(input);
    },
  );

  it("replaces the view on save and keeps unknown keys", () => {
    const state = run(INITIAL_STATE, { type: "open", doc: small(), name: "a" });
    const saved = saveDocument(state.doc!, { zoom: 0.5, cx: 1, cy: 2 });
    expect(saved.view).toEqual({ zoom: 0.5, cx: 1, cy: 2 });
    expect(saved.extra).toEqual({ keep: "me" });
  });

  it("serialises with indent 2 and a trailing newline", () => {
    const text = serializeDocument({ nodes: [] });
    expect(text).toBe('{\n  "nodes": []\n}\n');
  });
});

describe("reducer", () => {
  const opened = () => run(INITIAL_STATE, { type: "open", doc: small(), name: "a" });

  it("moves nodes and marks the document dirty; a no-op move changes nothing", () => {
    const s0 = opened();
    expect(reduce(s0, { type: "move", moves: [{ id: "fluid-1", x: 0, y: 0 }] })).toBe(s0);
    const s1 = reduce(s0, { type: "move", moves: [{ id: "fluid-1", x: 10, y: 5 }] });
    expect(docNodes(s1.doc!)[0]).toMatchObject({ x: 10, y: 5 });
    expect(s1.dirty).toBe(true);
    expect(docNodes(s0.doc!)[0]).toMatchObject({ x: 0, y: 0 });
  });

  it("adds a node with the smallest free id at the given position", () => {
    const s = run(
      opened(),
      { type: "add", kind: "fluid", settings: { a: 1 }, x: 5, y: 6 },
      { type: "add", kind: "fluid", settings: {}, x: 7, y: 8 },
    );
    expect(docNodes(s.doc!).map((n) => n.id)).toEqual([
      "fluid-1",
      "rated_point-1",
      "fluid-2",
      "fluid-3",
    ]);
    expect(docNodes(s.doc!)[2]).toEqual({ id: "fluid-2", kind: "fluid", x: 5, y: 6, settings: { a: 1 } });
    expect(newNodeId("fluid", ["fluid-1", "fluid-3"])).toBe("fluid-2");
  });

  it("connects, replaces a single-input edge, refuses a wrong type", () => {
    const base = run(
      opened(),
      { type: "add", kind: "fluid", settings: {}, x: 0, y: 100 },
      { type: "add", kind: "test_points", settings: {}, x: 0, y: 200 },
    );
    const a = edge("fluid-1", "FluidSpec", "rated_point-1", "FluidSpec");
    const b = edge("fluid-2", "FluidSpec", "rated_point-1", "FluidSpec");
    const s1 = reduce(base, { type: "connect", edge: a, catalog: CATALOG });
    expect(docEdges(s1.doc!)).toEqual([a]);
    const s2 = reduce(s1, { type: "connect", edge: b, catalog: CATALOG });
    expect(docEdges(s2.doc!)).toEqual([b]);
    expect(reduce(s2, { type: "connect", edge: b, catalog: CATALOG })).toBe(s2);
    const bad = edge("test_points-1", "TestPointSet", "rated_point-1", "FluidSpec");
    expect(reduce(s2, { type: "connect", edge: bad, catalog: CATALOG })).toBe(s2);
  });

  it("removes nodes with their edges, and disconnects an edge", () => {
    const a = edge("fluid-1", "FluidSpec", "rated_point-1", "FluidSpec");
    const wired = reduce(opened(), { type: "connect", edge: a, catalog: CATALOG });
    const gone = reduce(wired, { type: "remove", nodeIds: ["fluid-1"], edges: [] });
    expect(docNodes(gone.doc!).map((n) => n.id)).toEqual(["rated_point-1"]);
    expect(docEdges(gone.doc!)).toEqual([]);
    const cut = reduce(wired, { type: "disconnect", edge: a });
    expect(docEdges(cut.doc!)).toEqual([]);
    expect(docNodes(cut.doc!)).toHaveLength(2);
  });

  it("undoes and redoes, tracking dirty against the saved document", () => {
    const s0 = opened();
    const s1 = reduce(s0, { type: "move", moves: [{ id: "fluid-1", x: 1, y: 1 }] });
    const s2 = reduce(s1, { type: "move", moves: [{ id: "fluid-1", x: 2, y: 2 }] });
    const u1 = reduce(s2, { type: "undo" });
    expect(docNodes(u1.doc!)[0]).toMatchObject({ x: 1, y: 1 });
    const u2 = reduce(u1, { type: "undo" });
    expect(u2.doc).toBe(s0.doc);
    expect(u2.dirty).toBe(false);
    expect(reduce(u2, { type: "undo" })).toBe(u2);
    const r = reduce(u2, { type: "redo" });
    expect(docNodes(r.doc!)[0]).toMatchObject({ x: 1, y: 1 });
    expect(r.dirty).toBe(true);
    const edited = reduce(u1, { type: "move", moves: [{ id: "fluid-1", x: 9, y: 9 }] });
    expect(edited.future).toEqual([]);
  });

  it("markSaved clears dirty and caps history at the maximum", () => {
    let s = opened();
    for (let i = 1; i <= MAX_HISTORY + 20; i++) {
      s = reduce(s, { type: "move", moves: [{ id: "fluid-1", x: i, y: 0 }] });
    }
    expect(s.past).toHaveLength(MAX_HISTORY);
    expect(reduce(s, { type: "markSaved" }).dirty).toBe(false);
  });
});

describe("useProject evaluation", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const result = (tag: string): EvaluateResult => ({
    errors: [],
    nodes: { [tag]: { kind: "fluid", state: "ok", status: tag, badge: null, notes: [], view: {} } },
  });

  it("debounces by 150 ms and ignores out-of-order responses", async () => {
    const pending: Array<(r: EvaluateResult) => void> = [];
    const evaluate = vi.fn(
      () => new Promise<EvaluateResult>((resolve) => pending.push(resolve)),
    );
    const { result: hook } = renderHook(() => useProject({ evaluate }));

    act(() => hook.current.dispatch({ type: "open", doc: small(), name: "a" }));
    act(() => {
      hook.current.dispatch({ type: "move", moves: [{ id: "fluid-1", x: 1, y: 1 }] });
    });
    await act(async () => {
      vi.advanceTimersByTime(EVAL_DELAY_MS - 1);
    });
    expect(evaluate).not.toHaveBeenCalled();
    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    expect(evaluate).toHaveBeenCalledTimes(1);

    act(() => {
      hook.current.dispatch({ type: "move", moves: [{ id: "fluid-1", x: 2, y: 2 }] });
    });
    await act(async () => {
      vi.advanceTimersByTime(EVAL_DELAY_MS);
    });
    expect(evaluate).toHaveBeenCalledTimes(2);

    await act(async () => {
      pending[1]!(result("second"));
      pending[0]!(result("first"));
    });
    expect(Object.keys(hook.current.result!.nodes)).toEqual(["second"]);
  });
});
