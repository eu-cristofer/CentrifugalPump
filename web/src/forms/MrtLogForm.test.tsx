import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { MrtColumn, MrtRow, NodeResult, PumpflowDoc } from "../engine/types";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import MrtLogForm from "./MrtLogForm";

afterEach(cleanup);

const columns: MrtColumn[] = [
  { name: "Flow", dimension: "capacity", unit: "m³/h", role: "flow" },
  { name: "Sump", dimension: "temperature", unit: "°C", role: "oil_temperature" },
];
const rows: MrtRow[] = [
  { time: "06:00", values: { Flow: 10, Sump: 50 } },
  { time: "06:15", values: { Flow: 10.5, Sump: 51 } },
];
const settings = (over: Record<string, unknown> = {}) => ({
  pump_tag: "P-9001B",
  columns,
  rows,
  ...over,
});

const result = (
  state: NodeResult["state"] = "ok",
  status = "P-9001B · 2 readings · 0.3 h",
): NodeResult => ({
  kind: "mechanical_run",
  state,
  status,
  badge: null,
  notes: [],
  view: {},
});

function mount(s = settings(), r = result(), dispatch = vi.fn()) {
  const doc: PumpflowDoc = {
    nodes: [{ id: "mechanical_run-1", kind: "mechanical_run", x: 0, y: 0, settings: s }],
    edges: [],
  };
  const engine = fakeEngine();
  render(
    <EngineContext.Provider value={engine}>
      <MrtLogForm nodeId="mechanical_run-1" doc={doc} result={r} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return { dispatch, engine };
}

const lastSettings = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings as { pump_tag: string; columns: MrtColumn[]; rows: MrtRow[] };

describe("MrtLogForm", () => {
  it("renders the channels, the readings and the status", async () => {
    mount();
    expect(((await screen.findByLabelText("Pump TAG")) as HTMLInputElement).value).toBe("P-9001B");
    expect((screen.getByLabelText("Time reading 2") as HTMLInputElement).value).toBe("06:15");
    expect((screen.getByLabelText("Flow reading 2") as HTMLInputElement).value).toBe("10.5");
    expect((screen.getByLabelText("Sump reading 1") as HTMLInputElement).value).toBe("50");
    expect((screen.getByLabelText("Channel 1 name") as HTMLInputElement).value).toBe("Flow");
    await waitFor(() =>
      expect((screen.getByLabelText("Channel 2 role") as HTMLSelectElement).value).toBe(
        "oil_temperature",
      ),
    );
    expect(screen.getByText("P-9001B · 2 readings · 0.3 h")).toBeTruthy();
  });

  it("Add reading pre-fills the next time from the engine (the desktop +15 min rule)", async () => {
    const { dispatch, engine } = mount();
    fireEvent.click(await screen.findByRole("button", { name: /Add reading/ }));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(engine.nextTime).toHaveBeenCalledWith(rows);
    const out = lastSettings(dispatch).rows;
    expect(out).toHaveLength(3);
    expect(out[2]).toEqual({ time: "06:30", values: {} });
  });

  it("edits a time and a value; a comma decimal is accepted", async () => {
    const { dispatch } = mount();
    fireEvent.change(await screen.findByLabelText("Flow reading 1"), { target: { value: "9,75" } });
    fireEvent.change(screen.getByLabelText("Time reading 2"), { target: { value: "06:20" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    const out = lastSettings(dispatch).rows;
    expect(out[0]!.values.Flow).toBe(9.75);
    expect(out[1]!.time).toBe("06:20");
  });

  it("removes and moves the selected readings", async () => {
    const { dispatch } = mount();
    fireEvent.click(await screen.findByRole("button", { name: "Select reading 2" }));
    fireEvent.click(screen.getByRole("button", { name: /Up/ }));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch).rows.map((r) => r.time)).toEqual(["06:15", "06:00"]);
    fireEvent.click(screen.getByRole("button", { name: "－ Remove" }));
    await waitFor(() => expect(lastSettings(dispatch).rows).toHaveLength(1), { timeout: 2000 });
  });

  it("pastes spreadsheet cells through Python", async () => {
    const { dispatch, engine } = mount();
    const grid = await screen.findByRole("table", { name: "Readings" });
    const text = "Time\tFlow\n07:00\t11\n07:15\t12\n";
    fireEvent.paste(grid, { clipboardData: { getData: () => text } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(engine.parseMrtPaste).toHaveBeenCalledWith(text, columns);
    expect(lastSettings(dispatch).rows.map((r) => r.time)).toEqual(["07:00", "07:15"]);
  });

  it("converts a channel's readings when its unit changes", async () => {
    const { dispatch, engine } = mount();
    const unit = (await screen.findByLabelText("Flow unit")) as HTMLSelectElement;
    await waitFor(() => expect(unit.options.length).toBeGreaterThan(1));
    fireEvent.change(unit, { target: { value: "US GPM" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(engine.convert).toHaveBeenCalledWith(10, "m³/h", "US GPM", "capacity");
    const out = lastSettings(dispatch);
    expect(out.columns[0]!.unit).toBe("US GPM");
    expect(out.rows[0]!.values.Flow).toBeCloseTo(44.0287);
    expect(out.rows[0]!.values.Sump).toBe(50); // other channels untouched
  });

  it("renames a channel (keys of the readings follow), rejecting empty and duplicate names", async () => {
    const { dispatch } = mount();
    const name = (await screen.findByLabelText("Channel 2 name")) as HTMLInputElement;
    fireEvent.change(name, { target: { value: "Flow" } });
    fireEvent.blur(name);
    expect(name.value).toBe("Sump"); // duplicate: reverted
    fireEvent.change(name, { target: { value: "Oil temp" } });
    fireEvent.blur(name);
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    const out = lastSettings(dispatch);
    expect(out.columns.map((c) => c.name)).toEqual(["Flow", "Oil temp"]);
    expect(out.rows[0]!.values).toEqual({ Flow: 10, "Oil temp": 50 });
  });

  it("adds a channel, changes its role and removes another", async () => {
    const { dispatch } = mount();
    fireEvent.click(await screen.findByRole("button", { name: /＋ Channel/ }));
    await waitFor(() => expect(screen.getByLabelText("Channel 3 name")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Channel 3 role"), { target: { value: "other" } });
    fireEvent.click(screen.getByRole("button", { name: "Remove channel 1" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    const out = lastSettings(dispatch);
    expect(out.columns.map((c) => c.name)).toEqual(["Sump", "Channel 3"]);
    expect(out.rows[0]!.values).toEqual({ Sump: 50 });
  });

  it("shows the node status when the log is not valid", async () => {
    mount(settings(), result("invalid", "Enter readings: < 2 rows have values"));
    expect(await screen.findByText("Enter readings: < 2 rows have values")).toBeTruthy();
  });
});
