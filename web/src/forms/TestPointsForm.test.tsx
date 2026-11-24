import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import TestPointsForm from "./TestPointsForm";

afterEach(cleanup);

const row = (q: number, p_dis: number) => ({
  q,
  p_suc: 0.5,
  p_dis,
  temp_c: 25,
  n: 1750,
  power: 100,
  head: null,
  eff: null,
});

const baseSettings = () => ({
  pump_tag: "P-9001A",
  pressure_ref: "g",
  fluid_choice: "",
  columns: {
    q: "m³/h",
    p_suc: "bar",
    p_dis: "bar",
    temp_c: "°C",
    n: "rpm",
    power: "kW",
    head: "m",
    eff: "%",
  },
  rows: [row(0, 9), row(500, 8), row(833, 7)],
  suction_id: null,
  suction_id_unit: "mm",
  discharge_id: null,
  discharge_id_unit: "mm",
  suction_z: null,
  suction_z_unit: "m",
  discharge_z: null,
  discharge_z_unit: "m",
});

const docWith = (settings: Record<string, unknown>): PumpflowDoc => ({
  nodes: [{ id: "test_points-1", kind: "test_points", x: 0, y: 0, settings }],
  edges: [],
});

const result = (over: Partial<NodeResult> = {}, view: Record<string, unknown> = {}): NodeResult => ({
  kind: "test_points",
  state: "ok",
  status: "P-9001A · 3 points",
  badge: null,
  notes: [],
  view: {
    pump_tag: "P-9001A",
    n_rows: 3,
    head_unit: "m",
    eff_unit: "%",
    rows: [
      { head: 91.23, eff: null, components: null },
      { head: 81.456, eff: 55.62, components: null },
      { head: 71.0, eff: 61.0, components: null },
    ],
    fluids: [],
    choice: "__default__",
    has_shutoff: true,
    test_fluid: null,
    pump_type: "",
    vib_label: "Vibration columns (RMS, overall / filtered) · pump type not set: Bearing housing",
    vib_columns: [{ key: "vib_de", title: "DE overall", tooltip: "DE" }],
    ...view,
  },
  ...over,
});

function show(
  settings: Record<string, unknown> = baseSettings(),
  res: NodeResult = result(),
  dispatch = vi.fn(),
) {
  const engine = fakeEngine();
  const out = render(
    <EngineContext.Provider value={engine}>
      <TestPointsForm
        nodeId="test_points-1"
        doc={docWith(settings)}
        result={res}
        dispatch={dispatch}
      />
    </EngineContext.Provider>,
  );
  return { engine, dispatch, ...out };
}

const lastSettings = (dispatch: ReturnType<typeof vi.fn>) =>
  dispatch.mock.calls.at(-1)![0].settings as Record<string, unknown> & {
    rows: Array<Record<string, number | null>>;
    columns: Record<string, string>;
  };

describe("TestPointsForm", () => {
  it("keeps the bench geometry fields disabled until the checkbox is checked", async () => {
    const { dispatch } = show();
    const id = (await screen.findByLabelText("Suction pipe ID")) as HTMLInputElement;
    const z = screen.getByLabelText("Discharge gauge elevation z_d") as HTMLInputElement;
    expect(id.disabled).toBe(true);
    expect(z.disabled).toBe(true);
    expect(screen.getByText("Suction pipe ID").className).toContain("disabled");

    fireEvent.click(screen.getByLabelText(/Apply bench geometry/));
    expect(id.disabled).toBe(false);
    expect(z.disabled).toBe(false);
    fireEvent.change(id, { target: { value: "200" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({ suction_id: 200, suction_z: 0 });

    // unchecking stores the four values as unset (null), like the desktop
    fireEvent.click(screen.getByLabelText(/Apply bench geometry/));
    expect(id.disabled).toBe(true);
    await waitFor(() => expect(lastSettings(dispatch).suction_id).toBeNull(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({
      suction_id: null,
      discharge_id: null,
      suction_z: null,
      discharge_z: null,
    });
  });

  it("writes a typed Q cell as a number (decimal comma accepted)", async () => {
    const { dispatch } = show();
    const cell = (await screen.findByLabelText("Q row 2")) as HTMLInputElement;
    expect(cell.value).toBe("500");
    fireEvent.change(cell, { target: { value: "12,5" } });
    expect(cell.value).toBe("12,5");
    await waitFor(() => expect(dispatch).toHaveBeenCalledTimes(1), { timeout: 2000 });
    const sent = lastSettings(dispatch);
    expect(sent.rows[1]!.q).toBe(12.5);
    expect(sent.rows[0]!.q).toBe(0);
    expect(sent.rows[2]!.q).toBe(833);
  });

  it("shows the computed Head and η from the view, read-only", async () => {
    show();
    const head = await screen.findByLabelText("Head row 2 (computed)");
    expect(head.textContent).toBe("81.46");
    expect(head.querySelector("input")).toBeNull();
    expect(screen.getByLabelText("η row 2 (computed)").textContent).toBe("55.6");
    expect(screen.getByLabelText("η row 1 (computed)").textContent).toBe("—");
    expect(screen.queryByLabelText("Head row 2")).toBeNull();
  });

  it("adds, removes and moves rows", async () => {
    const { dispatch } = show();
    await screen.findByLabelText("Q row 3");
    fireEvent.click(screen.getByRole("button", { name: /Add row/ }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledTimes(1), { timeout: 2000 });
    expect(lastSettings(dispatch).rows).toHaveLength(4);
    expect(lastSettings(dispatch).rows[3]).toMatchObject({ q: null, power: null });

    // select row 1 (Q = 0) and move it down
    fireEvent.click(screen.getByLabelText("Select row 1"));
    fireEvent.click(screen.getByRole("button", { name: /Down/ }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledTimes(2), { timeout: 2000 });
    expect(lastSettings(dispatch).rows.map((r) => r.q)).toEqual([500, 0, 833, null]);

    // "Up" on the (now second) row restores the order
    fireEvent.click(screen.getByRole("button", { name: /Up/ }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledTimes(3), { timeout: 2000 });
    expect(lastSettings(dispatch).rows.map((r) => r.q)).toEqual([0, 500, 833, null]);

    // remove the selected row
    fireEvent.click(screen.getByRole("button", { name: /Remove/ }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledTimes(4), { timeout: 2000 });
    expect(lastSettings(dispatch).rows.map((r) => r.q)).toEqual([500, 833, null]);
  });

  it("converts a whole column through the engine when its unit changes", async () => {
    const { engine, dispatch } = show();
    const select = (await screen.findByLabelText("Q unit")) as HTMLSelectElement;
    await screen.findByRole("option", { name: "US GPM" });
    fireEvent.change(select, { target: { value: "US GPM" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(engine.convert).toHaveBeenCalledWith(500, "m³/h", "US GPM", "capacity");
    const sent = lastSettings(dispatch);
    expect(sent.columns.q).toBe("US GPM");
    expect(sent.rows[1]!.q).toBeCloseTo(500 * 4.40287, 6);
    expect(sent.rows[0]!.q).toBe(0); // 0 stays 0 (fake factor)
  });

  it("shifts the pressures by the atmosphere when the reference changes", async () => {
    const { engine, dispatch } = show();
    fireEvent.change(await screen.findByLabelText("Pressure reference"), {
      target: { value: "a" },
    });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(engine.atmosphere).toHaveBeenCalledWith("bar");
    const sent = lastSettings(dispatch);
    expect(sent.pressure_ref).toBe("a");
    expect(sent.rows[0]!.p_suc).toBeCloseTo(0.5 + 1.01325, 9);
  });

  it("pastes spreadsheet text through parse_paste", async () => {
    const { engine, dispatch } = show();
    await screen.findByLabelText("Q row 1");
    fireEvent.click(screen.getByRole("button", { name: /Paste/ })); // jsdom: no clipboard
    fireEvent.change(await screen.findByLabelText(/Paste the spreadsheet cells/), {
      target: { value: "100,5\t1\t5\n200\t1\t4" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(engine.parsePaste).toHaveBeenCalled();
    const sent = lastSettings(dispatch);
    expect(sent.rows).toHaveLength(2);
    expect(sent.rows[0]!.q).toBe(100.5);
  });

  it("shows the node status and the shut-off warning", async () => {
    show(baseSettings(), result({}, { has_shutoff: false }));
    expect(await screen.findByText(/no shut-off point/)).toBeTruthy();
    cleanup();
    show(baseSettings(), result({ state: "invalid", status: "need at least 3 points" }));
    expect(await screen.findByText("need at least 3 points")).toBeTruthy();
  });

  it("offers the fluid source only when fluids are wired", async () => {
    const { container } = show(baseSettings(), result({}, { fluids: ["Gasoline"], choice: "Gasoline" }));
    const pick = (await screen.findByLabelText("Fluid source")) as HTMLSelectElement;
    expect(pick.value).toBe("Gasoline");
    expect(within(container).getAllByRole("option", { name: "Water at T_water" })).toHaveLength(1);
  });

  it("shows the vibration columns when the box is checked", async () => {
    show();
    await screen.findByLabelText("Q row 1");
    expect(screen.queryByLabelText("DE overall row 1")).toBeNull();
    fireEvent.click(screen.getByLabelText(/Vibration columns/));
    expect(screen.getByLabelText("DE overall row 1")).toBeTruthy();
  });
});
