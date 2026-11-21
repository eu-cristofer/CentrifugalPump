import { type Dispatch, useEffect, useReducer, useRef, useState } from "react";
import type { Engine } from "../engine/client";
import type { CatalogEntry, EvaluateResult, PumpflowDoc } from "../engine/types";
import {
  type DocEdge,
  type DocNode,
  type View,
  docEdges,
  docNodes,
  newNodeId,
  sameEdge,
} from "./model";
import { connectEdge } from "./ports";

export const MAX_HISTORY = 100;
export const EVAL_DELAY_MS = 150;

export interface ProjectState {
  doc: PumpflowDoc | null;
  name: string;
  /** document snapshots, oldest first */
  past: PumpflowDoc[];
  future: PumpflowDoc[];
  /** the document as last opened or saved */
  saved: PumpflowDoc | null;
  dirty: boolean;
  /** bumped by every open; the canvas remounts (and fits or restores the view) */
  openId: number;
}

export const INITIAL_STATE: ProjectState = {
  doc: null,
  name: "",
  past: [],
  future: [],
  saved: null,
  dirty: false,
  openId: 0,
};

export type Action =
  | { type: "open"; doc: PumpflowDoc; name: string }
  | { type: "move"; moves: Array<{ id: string; x: number; y: number }> }
  | { type: "add"; kind: string; settings: Record<string, unknown>; x: number; y: number }
  | { type: "setSettings"; id: string; settings: Record<string, unknown> }
  | { type: "remove"; nodeIds: string[]; edges: DocEdge[] }
  | { type: "connect"; edge: DocEdge; catalog: CatalogEntry[] }
  | { type: "disconnect"; edge: DocEdge }
  | { type: "undo" }
  | { type: "redo" }
  | { type: "markSaved" };

/** Record `doc` as the new current document (history + dirty); same doc = no-op. */
function commit(state: ProjectState, doc: PumpflowDoc): ProjectState {
  if (!state.doc || doc === state.doc) return state;
  const past = [...state.past, state.doc].slice(-MAX_HISTORY);
  return { ...state, doc, past, future: [], dirty: doc !== state.saved };
}

export function reduce(state: ProjectState, action: Action): ProjectState {
  switch (action.type) {
    case "open":
      return {
        doc: action.doc,
        name: action.name,
        past: [],
        future: [],
        saved: action.doc,
        dirty: false,
        openId: state.openId + 1,
      };
    case "move": {
      if (!state.doc) return state;
      const moves = new Map(action.moves.map((m) => [m.id, m]));
      let changed = false;
      const nodes = docNodes(state.doc).map((n) => {
        const m = moves.get(n.id);
        if (!m || (m.x === n.x && m.y === n.y)) return n;
        changed = true;
        return { ...n, x: m.x, y: m.y };
      });
      return changed ? commit(state, { ...state.doc, nodes }) : state;
    }
    case "add": {
      if (!state.doc) return state;
      const old = docNodes(state.doc);
      const node: DocNode = {
        id: newNodeId(action.kind, old.map((n) => n.id)),
        kind: action.kind,
        x: action.x,
        y: action.y,
        settings: action.settings,
      };
      return commit(state, { ...state.doc, nodes: [...old, node] });
    }
    case "setSettings": {
      if (!state.doc) return state;
      let changed = false;
      const nodes = docNodes(state.doc).map((n) => {
        if (n.id !== action.id || n.settings === action.settings) return n;
        changed = true;
        return { ...n, settings: action.settings };
      });
      return changed ? commit(state, { ...state.doc, nodes }) : state;
    }
    case "remove": {
      if (!state.doc) return state;
      const gone = new Set(action.nodeIds);
      const oldNodes = docNodes(state.doc);
      const oldEdges = docEdges(state.doc);
      const nodes = oldNodes.filter((n) => !gone.has(n.id));
      const edges = oldEdges.filter(
        (e) =>
          !gone.has(e.src_node) &&
          !gone.has(e.dst_node) &&
          !action.edges.some((x) => sameEdge(x, e)),
      );
      if (nodes.length === oldNodes.length && edges.length === oldEdges.length) return state;
      return commit(state, { ...state.doc, nodes, edges });
    }
    case "connect": {
      if (!state.doc) return state;
      const old = docEdges(state.doc);
      const edges = connectEdge(docNodes(state.doc), old, action.catalog, action.edge);
      if (edges === null || edges === old) return state;
      return commit(state, { ...state.doc, edges });
    }
    case "disconnect": {
      if (!state.doc) return state;
      const old = docEdges(state.doc);
      const edges = old.filter((e) => !sameEdge(e, action.edge));
      return edges.length === old.length ? state : commit(state, { ...state.doc, edges });
    }
    case "undo": {
      const prev = state.past[state.past.length - 1];
      if (!state.doc || !prev) return state;
      return {
        ...state,
        doc: prev,
        past: state.past.slice(0, -1),
        future: [state.doc, ...state.future],
        dirty: prev !== state.saved,
      };
    }
    case "redo": {
      const next = state.future[0];
      if (!state.doc || !next) return state;
      return {
        ...state,
        doc: next,
        past: [...state.past, state.doc].slice(-MAX_HISTORY),
        future: state.future.slice(1),
        dirty: next !== state.saved,
      };
    }
    case "markSaved":
      return state.doc ? { ...state, saved: state.doc, dirty: false } : state;
  }
}

/** The document as it is written to disk (view replaced when given). */
export function saveDocument(doc: PumpflowDoc, view?: View): PumpflowDoc {
  return view ? { ...doc, view } : doc;
}

/** Desktop format: indent 2, non-ASCII kept, trailing newline. */
export function serializeDocument(doc: PumpflowDoc, view?: View): string {
  return JSON.stringify(saveDocument(doc, view), null, 2) + "\n";
}

export interface UseProject {
  state: ProjectState;
  dispatch: Dispatch<Action>;
  result: EvaluateResult | null;
  evalError: string;
}

/** The project store: reducer state plus debounced, order-safe evaluation. */
export function useProject(engine: Pick<Engine, "evaluate"> | null): UseProject {
  const [state, dispatch] = useReducer(reduce, INITIAL_STATE);
  const [result, setResult] = useState<EvaluateResult | null>(null);
  const [evalError, setEvalError] = useState("");
  const counter = useRef(0);
  const { doc } = state;

  useEffect(() => {
    if (!engine || !doc) return;
    const id = ++counter.current;
    const timer = setTimeout(() => {
      engine.evaluate(doc).then(
        (r) => {
          if (id !== counter.current) return;
          setResult(r);
          setEvalError("");
        },
        (err: unknown) => {
          if (id === counter.current) setEvalError(String(err));
        },
      );
    }, EVAL_DELAY_MS);
    return () => clearTimeout(timer);
  }, [engine, doc]);

  return { state, dispatch, result, evalError };
}
