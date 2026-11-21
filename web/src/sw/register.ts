/** What the app shows about the offline copy of itself. */
export type OfflineState =
  | { kind: "none" }
  | { kind: "saving"; loaded: number; total: number; files: number; count: number }
  | { kind: "ready" }
  | { kind: "update" }
  | { kind: "error"; message: string };

export interface OfflineHandle {
  /** ask the waiting worker to take over; the page reloads when it has */
  applyUpdate(): void;
  dispose(): void;
}

export interface RegisterOptions {
  /** register only in the production build (default); tests pass true with a fake container */
  enabled?: boolean;
  container?: ServiceWorkerContainer | null;
  reload?: () => void;
  /** worker URL, relative to the page */
  url?: string;
}

interface ProgressMessage {
  type: "precache-progress";
  done: number;
  count: number;
  bytes: number;
  total: number;
}

/** Messages the worker posts to the page (sw-template.js). */
function isWorkerMessage(data: unknown): data is ProgressMessage | { type: "precache-done" } {
  const type = (data as { type?: unknown } | null)?.type;
  return type === "precache-progress" || type === "precache-done";
}

/**
 * Register the service worker and report its state: "saving" while the files are
 * cached, "ready" once the app works offline, "update" when a new version waits
 * (applyUpdate activates it and reloads).  A no-op (returns null) outside the
 * production build or without service-worker support.
 */
export function registerServiceWorker(
  onState: (state: OfflineState) => void,
  options: RegisterOptions = {},
): OfflineHandle | null {
  const enabled = options.enabled ?? import.meta.env.PROD;
  const container =
    options.container === undefined
      ? typeof navigator !== "undefined" && "serviceWorker" in navigator
        ? navigator.serviceWorker
        : null
      : options.container;
  if (!enabled || !container) return null;
  const reload = options.reload ?? (() => window.location.reload());

  let disposed = false;
  let updating = false;
  let registration: ServiceWorkerRegistration | null = null;
  const emit = (state: OfflineState) => {
    if (!disposed) onState(state);
  };

  const watch = (worker: ServiceWorker | null) => {
    if (!worker) return;
    // a first install is shown as "saving"; a new version caches quietly behind the old one
    if (!container.controller) emit({ kind: "saving", loaded: 0, total: 0, files: 0, count: 0 });
    worker.addEventListener("statechange", () => {
      if (worker.state === "installed") {
        // with a controller this is a new version: it waits for applyUpdate
        if (container.controller) emit({ kind: "update" });
      } else if (worker.state === "activated") {
        if (!updating) emit({ kind: "ready" });
      } else if (worker.state === "redundant") {
        emit({ kind: "error", message: "The offline copy could not be saved." });
      }
    });
  };

  const onMessage = (event: MessageEvent) => {
    const data: unknown = event.data;
    if (!isWorkerMessage(data)) return;
    if (data.type === "precache-progress") {
      // while an update is cached the old version keeps serving: stay "ready"
      if (container.controller && registration?.active) return;
      emit({ kind: "saving", loaded: data.bytes, total: data.total, files: data.done, count: data.count });
    }
  };
  const onControllerChange = () => {
    if (updating) reload();
  };
  container.addEventListener("message", onMessage);
  container.addEventListener("controllerchange", onControllerChange);

  container.register(options.url ?? "sw.js").then(
    (reg) => {
      registration = reg;
      if (disposed) return;
      reg.addEventListener("updatefound", () => watch(reg.installing));
      if (reg.waiting && container.controller) emit({ kind: "update" });
      else if (reg.installing) watch(reg.installing);
      else if (reg.active) emit({ kind: "ready" });
    },
    (err: unknown) => emit({ kind: "error", message: err instanceof Error ? err.message : String(err) }),
  );

  return {
    applyUpdate() {
      const waiting = registration?.waiting;
      if (!waiting) return;
      updating = true;
      waiting.postMessage({ type: "SKIP_WAITING" });
    },
    dispose() {
      disposed = true;
      container.removeEventListener("message", onMessage);
      container.removeEventListener("controllerchange", onControllerChange);
    },
  };
}

/** "12.3 MB" */
export function megabytes(bytes: number): string {
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

/** The top-bar text of a state ("" when there is nothing to say). */
export function offlineLabel(state: OfflineState): string {
  switch (state.kind) {
    case "saving":
      return state.count > 0
        ? `Saving for offline… ${state.files}/${state.count}`
        : "Saving for offline…";
    case "ready":
      return "Ready offline";
    case "update":
      return "Update available";
    case "error":
      return "Offline copy unavailable";
    default:
      return "";
  }
}
