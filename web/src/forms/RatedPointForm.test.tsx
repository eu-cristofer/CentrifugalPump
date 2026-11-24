import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import RatedPointForm from "./RatedPointForm";

afterEach(cleanup);

const settings = {
  tag: "P-9001",
  service: "",
  standard: "API 610 12th",
  standard_key: "api610:12",
  client: "",
  q: 833,
  q_unit: "m³/h",
  head: 73,
  head_unit: "m",
  n: 1750,
  n_unit: "rpm",
  power: 252,
  power_unit: "kW",
  eff: 61,
  eff_unit: "%",
  head_shutoff: 117,
  head_shutoff_unit: "m",
  npsha: 0,
  npsha_unit: "m",
  dens_rel: 0.736,
  dens_unit: "kg/m³",
  visc: 0.567,
  visc_unit: "cSt",
  parallel: false,
  fluid_name: "Rated fluid",
};

const doc: PumpflowDoc = {
  nodes: [{ id: "rated_point-1", kind: "rated_point", x: 0, y: 0, settings }],
  edges: [],
};

const result: NodeResult = {
  kind: "rated_point",
  state: "ok",
  status: "",
  badge: null,
  notes: [],
  view: { standard_key: "api610:12", client: "", fluids: [], choice: "__default__", override: null },
};

function show(dispatch = vi.fn()) {
  const engine = fakeEngine();
  const out = render(
    <EngineContext.Provider value={engine}>
      <RatedPointForm nodeId="rated_point-1" doc={doc} result={result} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return { engine, dispatch, ...out };
}

describe("RatedPointForm", () => {
  it("lists the identification rows in the desktop order", async () => {
    const { container } = show();
    await screen.findByLabelText("Service TAG");
    const labels = Array.from(container.querySelectorAll("label.row-label")).map(
      (l) => l.textContent,
    );
    expect(labels.slice(0, 5)).toEqual([
      "Service",
      "Service TAG",
      "Standard / edition",
      "Client overlay",
      "Label on report cover",
    ]);
    expect(labels).toContain("Capacity Q");
    expect(labels.indexOf("Rated duty")).toBe(-1); // a section, not a row
    expect(screen.getByText("Rated fluid")).toBeTruthy();
  });

  it("writes the edition, client and the cover label when the combos change", async () => {
    const { engine, dispatch } = show();
    await screen.findByRole("option", { name: "Petrobras N-553" });
    fireEvent.change(screen.getByLabelText("Client overlay"), { target: { value: "n553" } });
    await waitFor(() => expect(engine.standardLabel).toHaveBeenCalledWith("api610:12", "n553"));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    const sent = dispatch.mock.calls.at(-1)![0].settings;
    expect(sent).toMatchObject({
      standard_key: "api610:12",
      client: "n553",
      standard: "api610:12+n553",
    });
  });

  it("edits the tag and dispatches the encoded settings", async () => {
    const { dispatch } = show();
    const tag = (await screen.findByLabelText("Service TAG")) as HTMLInputElement;
    fireEvent.change(tag, { target: { value: "P-1" } });
    expect(tag.value).toBe("P-1");
    await waitFor(() => expect(dispatch).toHaveBeenCalledTimes(1), { timeout: 2000 });
    expect(dispatch.mock.calls[0]![0].settings.tag).toBe("P-1");
  });
});
