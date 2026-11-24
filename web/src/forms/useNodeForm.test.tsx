import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PumpflowDoc, Settings } from "../engine/types";
import { FORM_DEBOUNCE_MS, useNodeForm } from "./useNodeForm";
import { fakeEngine } from "./fakeEngine";

const doc = (settings: Settings): PumpflowDoc => ({
  nodes: [{ id: "rated_point-1", kind: "rated_point", x: 0, y: 0, settings }],
  edges: [],
});

const flushMicro = () => act(async () => {});
const tick = (ms: number) => act(async () => void vi.advanceTimersByTime(ms));

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

function setup(settings: Settings = { tag: "A", q: 1 }) {
  const engine = fakeEngine();
  const dispatch = vi.fn();
  const d = doc(settings);
  const hook = renderHook(() => useNodeForm(engine, d, "rated_point-1", dispatch));
  return { engine, dispatch, hook, d };
}

describe("useNodeForm", () => {
  it("loads the runtime settings through decodeSettings", async () => {
    const { engine, hook } = setup();
    expect(hook.result.current.runtime).toBeNull();
    await flushMicro();
    expect(engine.decodeSettings).toHaveBeenCalledWith("rated_point", { tag: "A", q: 1 });
    expect(hook.result.current.runtime).toEqual({ tag: "A", q: 1 });
  });

  it("shows an edit at once and dispatches one debounced setSettings", async () => {
    const { engine, dispatch, hook } = setup();
    await flushMicro();
    act(() => hook.result.current.update({ tag: "B" }));
    expect(hook.result.current.runtime).toEqual({ tag: "B", q: 1 });
    act(() => hook.result.current.update({ q: 2 }));
    await tick(FORM_DEBOUNCE_MS - 1);
    expect(engine.encodeSettings).not.toHaveBeenCalled();
    await tick(1);
    await flushMicro();
    expect(engine.encodeSettings).toHaveBeenCalledTimes(1);
    expect(engine.encodeSettings).toHaveBeenCalledWith("rated_point", { tag: "B", q: 2 });
    expect(dispatch).toHaveBeenCalledTimes(1);
    expect(dispatch).toHaveBeenCalledWith({
      type: "setSettings",
      id: "rated_point-1",
      settings: { tag: "B", q: 2 },
    });
  });

  it("ignores a stale encode response", async () => {
    const { engine, dispatch, hook } = setup();
    await flushMicro();
    const resolvers: Array<(s: Settings) => void> = [];
    engine.encodeSettings.mockImplementation(
      () => new Promise<Settings>((resolve) => resolvers.push(resolve)),
    );
    act(() => hook.result.current.update({ tag: "first" }));
    await tick(FORM_DEBOUNCE_MS);
    act(() => hook.result.current.update({ tag: "second" }));
    await tick(FORM_DEBOUNCE_MS);
    expect(resolvers).toHaveLength(2);
    resolvers[0]!({ tag: "first" });
    await flushMicro();
    expect(dispatch).not.toHaveBeenCalled();
    resolvers[1]!({ tag: "second" });
    await flushMicro();
    expect(dispatch).toHaveBeenCalledTimes(1);
    expect(dispatch.mock.calls[0]![0].settings).toEqual({ tag: "second" });
  });

  it("removes a key patched to undefined", async () => {
    const { hook } = setup({ tag: "A", pump_type: "BB2" });
    await flushMicro();
    act(() => hook.result.current.update({ pump_type: undefined }));
    expect(hook.result.current.runtime).toEqual({ tag: "A" });
  });

  it("flushes a pending edit on unmount", async () => {
    const { engine, dispatch, hook } = setup();
    await flushMicro();
    act(() => hook.result.current.update({ tag: "Z" }));
    hook.unmount();
    await flushMicro();
    expect(engine.encodeSettings).toHaveBeenCalledTimes(1);
    expect(dispatch).toHaveBeenCalledTimes(1);
  });

  it("reloads when the document changes elsewhere (undo)", async () => {
    const engine = fakeEngine();
    const dispatch = vi.fn();
    let d = doc({ tag: "A" });
    const hook = renderHook(() => useNodeForm(engine, d, "rated_point-1", dispatch));
    await flushMicro();
    d = doc({ tag: "OLD" });
    hook.rerender();
    await flushMicro();
    expect(hook.result.current.runtime).toEqual({ tag: "OLD" });
  });
});
