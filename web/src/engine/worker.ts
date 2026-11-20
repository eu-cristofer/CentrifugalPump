// Web Worker: boots Pyodide from /py/ (local files only) and serves
// {id, fn, args} requests with {id, ok, result | error}.
import { boot } from "./boot.js";
import type { WorkerIn, WorkerOut } from "./types";

const ctx = self as unknown as {
  postMessage(message: WorkerOut): void;
  onmessage: ((event: MessageEvent<WorkerIn>) => void) | null;
};

const PY_BASE = "/py/";

async function readFile(relPath: string): Promise<Uint8Array> {
  const res = await fetch(PY_BASE + relPath);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${PY_BASE + relPath}`);
  return new Uint8Array(await res.arrayBuffer());
}

async function start() {
  const url = PY_BASE + "pyodide.mjs";
  const mod = (await import(/* @vite-ignore */ url)) as {
    loadPyodide: (options: { indexURL: string }) => Promise<unknown>;
  };
  return boot({
    loadPyodide: mod.loadPyodide as never,
    indexURL: PY_BASE,
    readFile,
    onProgress: (stage, loaded, total) =>
      ctx.postMessage({ type: "progress", stage, loaded, total }),
  });
}

const engine = start().then(
  (e) => {
    ctx.postMessage({ type: "ready", version: e.version });
    return e;
  },
  (err: unknown) => {
    ctx.postMessage({ type: "fatal", error: String(err) });
    throw err;
  },
);
engine.catch(() => undefined);

ctx.onmessage = async (event: MessageEvent<WorkerIn>) => {
  const { id, fn, args } = event.data;
  try {
    const e = await engine;
    const text = e.call(fn, args);
    ctx.postMessage({ id, ok: true, result: JSON.parse(text) });
  } catch (err) {
    ctx.postMessage({ id, ok: false, error: String(err) });
  }
};
