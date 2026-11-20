import { useCallback, useEffect, useRef, useState } from "react";
import type { Engine } from "./engine/client";
import { spawnEngine } from "./engine/spawn";
import type { EvaluateResult, Progress, PumpflowDoc } from "./engine/types";

export default function App() {
  const engineRef = useRef<Engine | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [ready, setReady] = useState(false);
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState<EvaluateResult | null>(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const engine = spawnEngine(setProgress);
    engineRef.current = engine;
    engine.ready.then(
      () => setReady(true),
      (err: unknown) => setError(String(err)),
    );
    return () => {
      engine.dispose();
      engineRef.current = null;
    };
  }, []);

  const openFile = useCallback(async (file: File) => {
    const engine = engineRef.current;
    if (!engine) return;
    setError("");
    try {
      const doc = JSON.parse(await file.text()) as PumpflowDoc;
      setFileName(file.name);
      setResult(await engine.evaluate(doc));
    } catch (err) {
      setResult(null);
      setError(String(err));
    }
  }, []);

  const rows = result
    ? Object.entries(result.nodes).sort(([a], [b]) => a.localeCompare(b))
    : [];
  const pct = progress ? Math.round((progress.loaded / progress.total) * 100) : 0;

  return (
    <main
      className={dragging ? "page dragging" : "page"}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files[0];
        if (file && ready) void openFile(file);
      }}
    >
      <h1>PumpFlow Web</h1>

      {!ready && !error && (
        <div className="loading">
          <div className="bar">
            <div className="bar-fill" style={{ width: `${pct}%` }} />
          </div>
          <p>Starting the Python engine{progress ? ` (${progress.stage}, ${pct}%)` : ""}</p>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {ready && (
        <label className="open">
          Open .pumpflow
          <input
            type="file"
            accept=".pumpflow,application/json"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void openFile(file);
              e.target.value = "";
            }}
          />
        </label>
      )}

      {result && (
        <>
          <p className="summary">
            {fileName} · {rows.length} nodes · {result.errors.length} errors
          </p>
          <table>
            <thead>
              <tr>
                <th>Node</th>
                <th>Kind</th>
                <th>State</th>
                <th>Status</th>
                <th>Badge</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([id, node]) => (
                <tr key={id}>
                  <td>{id}</td>
                  <td>{node.kind}</td>
                  <td className={`state-${node.state}`}>{node.state}</td>
                  <td>{node.status}</td>
                  <td className={node.badge ? `tone-${node.badge[1]}` : undefined}>
                    {node.badge ? node.badge[0] : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  );
}
