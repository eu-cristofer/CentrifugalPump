import { describe, expect, it, vi } from "vitest";
import { type OfflineState, megabytes, offlineLabel, registerServiceWorker } from "./register";

type Listener = (event: unknown) => void;

class FakeWorker {
  state = "installing";
  posted: unknown[] = [];
  listeners: Listener[] = [];
  addEventListener(_type: string, l: Listener) {
    this.listeners.push(l);
  }
  postMessage(m: unknown) {
    this.posted.push(m);
  }
  set(state: string) {
    this.state = state;
    this.listeners.forEach((l) => l({}));
  }
}

class FakeRegistration {
  installing: FakeWorker | null = null;
  waiting: FakeWorker | null = null;
  active: FakeWorker | null = null;
  listeners: Record<string, Listener[]> = {};
  addEventListener(type: string, l: Listener) {
    (this.listeners[type] ??= []).push(l);
  }
  fire(type: string) {
    (this.listeners[type] ?? []).forEach((l) => l({}));
  }
}

class FakeContainer {
  controller: unknown = null;
  listeners: Record<string, Listener[]> = {};
  registered: string[] = [];
  constructor(public reg: FakeRegistration) {}
  register = vi.fn(async (url: string) => {
    this.registered.push(url);
    return this.reg;
  });
  addEventListener(type: string, l: Listener) {
    (this.listeners[type] ??= []).push(l);
  }
  removeEventListener(type: string, l: Listener) {
    this.listeners[type] = (this.listeners[type] ?? []).filter((x) => x !== l);
  }
  emit(type: string, event: unknown = {}) {
    (this.listeners[type] ?? []).forEach((l) => l(event));
  }
}

const flush = () => new Promise((r) => setTimeout(r, 0));

function setup(configure: (reg: FakeRegistration, c: FakeContainer) => void = () => undefined) {
  const reg = new FakeRegistration();
  const container = new FakeContainer(reg);
  configure(reg, container);
  const states: OfflineState[] = [];
  const reload = vi.fn();
  const handle = registerServiceWorker((s) => states.push(s), {
    enabled: true,
    container: container as unknown as ServiceWorkerContainer,
    reload,
  });
  return { reg, container, states, reload, handle };
}

describe("registerServiceWorker", () => {
  it("is a no-op outside the production build (as in tests) and without support", () => {
    const onState = vi.fn();
    expect(registerServiceWorker(onState)).toBeNull();
    expect(registerServiceWorker(onState, { enabled: true, container: null })).toBeNull();
    expect(onState).not.toHaveBeenCalled();
  });

  it("registers the worker next to the page", async () => {
    const { container } = setup();
    await flush();
    expect(container.registered).toEqual(["sw.js"]);
  });

  it("first visit: saving with progress, then ready when the worker activates", async () => {
    const worker = new FakeWorker();
    const { container, states } = setup((reg) => {
      reg.installing = worker;
    });
    await flush();
    expect(states.at(-1)).toMatchObject({ kind: "saving", files: 0 });
    container.emit("message", {
      data: { type: "precache-progress", done: 8, count: 40, bytes: 1000, total: 4000 },
    });
    expect(states.at(-1)).toEqual({ kind: "saving", loaded: 1000, total: 4000, files: 8, count: 40 });
    worker.set("installed"); // no controller: not an update
    expect(states.at(-1)).toMatchObject({ kind: "saving" });
    worker.set("activated");
    expect(states.at(-1)).toEqual({ kind: "ready" });
  });

  it("later visit: ready at once", async () => {
    const { states } = setup((reg, c) => {
      reg.active = new FakeWorker();
      c.controller = {};
    });
    await flush();
    expect(states).toEqual([{ kind: "ready" }]);
  });

  it("a waiting worker is an update; applyUpdate posts SKIP_WAITING and reloads on takeover", async () => {
    const waiting = new FakeWorker();
    const { container, states, reload, handle } = setup((reg, c) => {
      reg.active = new FakeWorker();
      reg.waiting = waiting;
      c.controller = {};
    });
    await flush();
    expect(states.at(-1)).toEqual({ kind: "update" });
    container.emit("controllerchange");
    expect(reload).not.toHaveBeenCalled(); // not asked for
    handle!.applyUpdate();
    expect(waiting.posted).toEqual([{ type: "SKIP_WAITING" }]);
    container.emit("controllerchange");
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("a new version found while running caches quietly, then offers the update", async () => {
    const next = new FakeWorker();
    const { reg, container, states } = setup((r, c) => {
      r.active = new FakeWorker();
      c.controller = {};
    });
    await flush();
    reg.installing = next;
    reg.fire("updatefound");
    container.emit("message", {
      data: { type: "precache-progress", done: 1, count: 4, bytes: 1, total: 4 },
    });
    expect(states.at(-1)).toEqual({ kind: "ready" });
    next.set("installed");
    expect(states.at(-1)).toEqual({ kind: "update" });
  });

  it("reports a failed registration and a redundant worker", async () => {
    const worker = new FakeWorker();
    const { states } = setup((reg) => {
      reg.installing = worker;
    });
    await flush();
    worker.set("redundant");
    expect(states.at(-1)).toMatchObject({ kind: "error" });

    const failing = new FakeContainer(new FakeRegistration());
    failing.register.mockRejectedValueOnce(new Error("nope"));
    const seen: OfflineState[] = [];
    registerServiceWorker((s) => seen.push(s), {
      enabled: true,
      container: failing as unknown as ServiceWorkerContainer,
    });
    await flush();
    expect(seen).toEqual([{ kind: "error", message: "nope" }]);
  });

  it("stops reporting after dispose", async () => {
    const { container, states, handle } = setup((reg) => {
      reg.installing = new FakeWorker();
    });
    await flush();
    const n = states.length;
    handle!.dispose();
    container.emit("message", {
      data: { type: "precache-progress", done: 1, count: 2, bytes: 1, total: 2 },
    });
    expect(states.length).toBe(n);
  });
});

describe("labels", () => {
  it("formats the top-bar text", () => {
    expect(offlineLabel({ kind: "none" })).toBe("");
    expect(offlineLabel({ kind: "ready" })).toBe("Ready offline");
    expect(offlineLabel({ kind: "update" })).toBe("Update available");
    expect(offlineLabel({ kind: "saving", loaded: 0, total: 0, files: 0, count: 0 })).toBe(
      "Saving for offline…",
    );
    expect(offlineLabel({ kind: "saving", loaded: 5, total: 10, files: 3, count: 30 })).toBe(
      "Saving for offline… 3/30",
    );
    expect(megabytes(1.5 * 1024 ** 2)).toBe("1.5 MB");
  });
});
