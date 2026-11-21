import { Suspense, lazy, useCallback, useEffect, useRef, useState } from "react";
import Canvas, { type CanvasHandle } from "./canvas/Canvas";
import Toolbox from "./canvas/Toolbox";
import type { Engine } from "./engine/client";
import { spawnEngine } from "./engine/spawn";
import type { CatalogEntry, Progress, PumpflowDoc } from "./engine/types";
import { readProjectFile, saveProjectText } from "./project/files";
import { serializeDocument, useProject } from "./project/store";
import {
  type OfflineHandle,
  type OfflineState,
  megabytes,
  offlineLabel,
  registerServiceWorker,
} from "./sw/register";

// The property forms (and the charts they draw) load on first use: the first screen
// needs only the canvas.
const FormPanel = lazy(() => import("./forms/FormPanel"));

const EMPTY_DOC: PumpflowDoc = {
  meta: { unit_preset: "SI", schema_version: 2 },
  nodes: [],
  edges: [],
};

export default function App() {
  const [engine, setEngine] = useState<Engine | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [catalog, setCatalog] = useState<CatalogEntry[] | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [dragging, setDragging] = useState(false);
  const [openForm, setOpenForm] = useState<string | null>(null);
  const [offline, setOffline] = useState<OfflineState>({ kind: "none" });
  const offlineRef = useRef<OfflineHandle | null>(null);
  const canvasRef = useRef<CanvasHandle>(null);
  const { state, dispatch, result, evalError } = useProject(catalog ? engine : null);
  const { doc, name, dirty, past, future, openId } = state;

  useEffect(() => {
    let live = true;
    const e = spawnEngine(setProgress);
    setEngine(e);
    e.ready
      .then(() => e.catalog())
      .then(
        (c) => live && setCatalog(c),
        (err: unknown) => live && setError(String(err)),
      );
    return () => {
      live = false;
      e.dispose();
      setEngine(null);
    };
  }, []);

  useEffect(() => {
    // production build only: a no-op in dev and in tests
    const handle = registerServiceWorker(setOffline);
    offlineRef.current = handle;
    return () => {
      handle?.dispose();
      offlineRef.current = null;
    };
  }, []);

  const openDoc = useCallback(
    async (file: File) => {
      if (dirty && !window.confirm("Discard unsaved changes?")) return;
      try {
        const next = await readProjectFile(file);
        setError("");
        setMessage("");
        setOpenForm(null);
        dispatch({ type: "open", doc: next, name: file.name });
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [dirty, dispatch],
  );

  const save = useCallback(async () => {
    if (!doc) return;
    try {
      const saved = await saveProjectText(
        serializeDocument(doc, canvasRef.current?.view()),
        name || "project",
      );
      if (saved) {
        dispatch({ type: "markSaved" });
        setMessage(`Saved ${saved}`);
      }
    } catch (err) {
      setError(String(err));
    }
  }, [doc, name, dispatch]);

  const addNode = useCallback(
    async (kind: string) => {
      if (!engine || !doc) return;
      try {
        const settings = await engine.defaultSettings(kind);
        const c = canvasRef.current?.center() ?? { x: 0, y: 0 };
        dispatch({ type: "add", kind, settings, x: Math.round(c.x), y: Math.round(c.y) });
      } catch (err) {
        setError(String(err));
      }
    },
    [engine, doc, dispatch],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      if (!mod) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      const key = e.key.toLowerCase();
      if (key === "z") {
        e.preventDefault();
        dispatch({ type: e.shiftKey ? "redo" : "undo" });
      } else if (key === "y") {
        e.preventDefault();
        dispatch({ type: "redo" });
      } else if (key === "s") {
        e.preventDefault();
        void save();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dispatch, save]);

  useEffect(() => {
    if (!dirty) return;
    const guard = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);

  const pct = progress ? Math.round((progress.loaded / progress.total) * 100) : 0;

  if (!catalog) {
    return (
      <main className="page">
        <h1>PumpFlow Web</h1>
        {!error && (
          <div className="loading">
            <div className="bar">
              <div className="bar-fill" style={{ width: `${pct}%` }} />
            </div>
            <p>Starting the Python engine{progress ? ` (${progress.stage}, ${pct}%)` : ""}</p>
            {offline.kind === "saving" && (
              <p>
                First start: saving PumpFlow for offline use
                {offline.total > 0
                  ? ` (${megabytes(offline.loaded)} of ${megabytes(offline.total)})`
                  : ""}
              </p>
            )}
          </div>
        )}
        {error && <p className="error-text">{error}</p>}
      </main>
    );
  }

  return (
    <div
      className={dragging ? "editor dragging" : "editor"}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) void openDoc(file);
      }}
    >
      <header className="topbar">
        <strong className="brand">PumpFlow</strong>
        <label className="btn">
          Open
          <input
            type="file"
            accept=".pumpflow,application/json"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void openDoc(file);
              e.target.value = "";
            }}
          />
        </label>
        <button type="button" className="btn" disabled={!doc} onClick={() => void save()}>
          Save
        </button>
        <button
          type="button"
          className="btn"
          disabled={past.length === 0}
          onClick={() => dispatch({ type: "undo" })}
        >
          Undo
        </button>
        <button
          type="button"
          className="btn"
          disabled={future.length === 0}
          onClick={() => dispatch({ type: "redo" })}
        >
          Redo
        </button>
        <span className="file-name">
          {name}
          {dirty ? " •" : ""}
        </span>
        <span className="topbar-message">{error || evalError || message}</span>
        {offline.kind !== "none" && (
          <span className={`offline-state offline-${offline.kind}`} role="status">
            {offlineLabel(offline)}
            {offline.kind === "update" && (
              <button
                type="button"
                className="btn offline-update"
                onClick={() => offlineRef.current?.applyUpdate()}
              >
                Reload
              </button>
            )}
          </span>
        )}
      </header>

      <div className="workspace">
        {doc ? (
          <>
            <Toolbox catalog={catalog} onAdd={(kind) => void addNode(kind)} />
            <Canvas
              doc={doc}
              catalog={catalog}
              result={result}
              openId={openId}
              dispatch={dispatch}
              onOpenNode={setOpenForm}
              handle={canvasRef}
            />
            {engine && openForm && (
              <Suspense fallback={null}>
                <FormPanel
                  engine={engine}
                  doc={doc}
                  catalog={catalog}
                  result={result}
                  nodeId={openForm}
                  dispatch={dispatch}
                  onClose={() => setOpenForm(null)}
                />
              </Suspense>
            )}
          </>
        ) : (
          <div className="welcome">
            <p>Open a .pumpflow project, or drop one anywhere on this page.</p>
            <button
              type="button"
              className="btn"
              onClick={() => dispatch({ type: "open", doc: EMPTY_DOC, name: "untitled.pumpflow" })}
            >
              New empty project
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
