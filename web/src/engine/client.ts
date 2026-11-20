import type {
  ApiFns,
  CatalogEntry,
  EvaluateResult,
  ExportFormat,
  ExportResult,
  FnName,
  Progress,
  PumpflowDoc,
  WorkerOut,
} from "./types";

/** The part of `Worker` the client needs (so tests can pass a fake). */
export interface WorkerLike {
  postMessage(message: unknown): void;
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
  terminate(): void;
}

interface Pending {
  resolve: (value: never) => void;
  reject: (reason: Error) => void;
}

/** Typed promise wrapper around the engine worker. */
export class Engine {
  /** Resolves with the Pyodide version once the engine is booted. */
  readonly ready: Promise<string>;
  private nextId = 1;
  private pending = new Map<number, Pending>();
  private resolveReady!: (version: string) => void;
  private rejectReady!: (reason: Error) => void;

  constructor(
    private readonly worker: WorkerLike,
    private readonly onProgress?: (progress: Progress) => void,
  ) {
    this.ready = new Promise<string>((resolve, reject) => {
      this.resolveReady = resolve;
      this.rejectReady = reject;
    });
    this.ready.catch(() => undefined);
    worker.onmessage = (event) => this.handle(event.data as WorkerOut);
    worker.onerror = (event) => this.fail(new Error(event.message || "worker error"));
  }

  private handle(msg: WorkerOut): void {
    if ("type" in msg) {
      if (msg.type === "progress") this.onProgress?.(msg);
      else if (msg.type === "ready") this.resolveReady(msg.version);
      else this.fail(new Error(msg.error));
      return;
    }
    const entry = this.pending.get(msg.id);
    if (!entry) return;
    this.pending.delete(msg.id);
    if (msg.ok) entry.resolve(msg.result as never);
    else entry.reject(new Error(msg.error));
  }

  private fail(error: Error): void {
    this.rejectReady(error);
    for (const entry of this.pending.values()) entry.reject(error);
    this.pending.clear();
  }

  call<F extends FnName>(fn: F, ...args: ApiFns[F]["args"]): Promise<ApiFns[F]["result"]> {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve: resolve as Pending["resolve"], reject });
      this.worker.postMessage({ id, fn, args });
    });
  }

  catalog(): Promise<CatalogEntry[]> {
    return this.call("catalog");
  }

  evaluate(doc: PumpflowDoc): Promise<EvaluateResult> {
    return this.call("evaluate", doc);
  }

  defaultSettings(kind: string): Promise<Record<string, unknown>> {
    return this.call("default_settings", kind);
  }

  exportReport(
    doc: PumpflowDoc,
    fmt: ExportFormat,
    lang: string | null = null,
  ): Promise<ExportResult> {
    return this.call("export_report", doc, fmt, lang);
  }

  dispose(): void {
    this.fail(new Error("engine disposed"));
    this.worker.terminate();
  }
}
