import { describe, expect, it } from "vitest";
import { Engine, type WorkerLike } from "./client";
import type { Progress } from "./types";

class FakeWorker implements WorkerLike {
  sent: Array<{ id: number; fn: string; args: unknown[] }> = [];
  terminated = false;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;

  postMessage(message: unknown): void {
    this.sent.push(message as { id: number; fn: string; args: unknown[] });
  }
  terminate(): void {
    this.terminated = true;
  }
  emit(data: unknown): void {
    this.onmessage?.({ data } as MessageEvent);
  }
}

describe("Engine", () => {
  it("matches responses to requests by id, in any order", async () => {
    const w = new FakeWorker();
    const engine = new Engine(w);
    const a = engine.call("default_settings", "fluid");
    const b = engine.call("default_settings", "rated_point");
    expect(w.sent.map((m) => m.fn)).toEqual(["default_settings", "default_settings"]);
    const [first, second] = w.sent;
    w.emit({ id: second!.id, ok: true, result: { which: "second" } });
    w.emit({ id: first!.id, ok: true, result: { which: "first" } });
    expect(await a).toEqual({ which: "first" });
    expect(await b).toEqual({ which: "second" });
  });

  it("wraps the MRT helpers (next reading time, options, paste)", async () => {
    const w = new FakeWorker();
    const engine = new Engine(w);
    const rows = [{ time: "06:15" }];
    const cols = [{ name: "Flow", dimension: "capacity", unit: "m³/h", role: "flow" }];
    const a = engine.nextTime(rows);
    const b = engine.mrtOptions();
    const c = engine.parseMrtPaste("06:00\t1", cols);
    expect(w.sent.map((m) => [m.fn, m.args])).toEqual([
      ["next_time", [rows]],
      ["mrt_options", []],
      ["parse_mrt_paste", ["06:00\t1", cols]],
    ]);
    w.emit({ id: w.sent[0]!.id, ok: true, result: "06:30" });
    w.emit({ id: w.sent[1]!.id, ok: true, result: { roles: [], dimensions: [], role_dimensions: {} } });
    w.emit({ id: w.sent[2]!.id, ok: true, result: [] });
    expect(await a).toBe("06:30");
    expect((await b).roles).toEqual([]);
    expect(await c).toEqual([]);
  });

  it("rejects a request when the worker reports an error", async () => {
    const w = new FakeWorker();
    const engine = new Engine(w);
    const p = engine.evaluate({});
    w.emit({ id: w.sent[0]!.id, ok: false, error: "boom" });
    await expect(p).rejects.toThrow("boom");
  });

  it("reports progress and resolves ready", async () => {
    const w = new FakeWorker();
    const seen: Progress[] = [];
    const engine = new Engine(w, (p) => seen.push(p));
    w.emit({ type: "progress", stage: "runtime", loaded: 1, total: 4 });
    w.emit({ type: "ready", version: "314.0.7" });
    expect(await engine.ready).toBe("314.0.7");
    expect(seen).toEqual([{ type: "progress", stage: "runtime", loaded: 1, total: 4 }]);
  });

  it("fails pending requests and ready on a fatal boot error", async () => {
    const w = new FakeWorker();
    const engine = new Engine(w);
    const p = engine.catalog();
    w.emit({ type: "fatal", error: "no wasm" });
    await expect(p).rejects.toThrow("no wasm");
    await expect(engine.ready).rejects.toThrow("no wasm");
  });

  it("terminates the worker on dispose", () => {
    const w = new FakeWorker();
    new Engine(w).dispose();
    expect(w.terminated).toBe(true);
  });
});
