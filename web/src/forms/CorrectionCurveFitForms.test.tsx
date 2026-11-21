import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import CorrectionForm from "./CorrectionForm";
import CurveFitForm from "./CurveFitForm";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";

afterEach(cleanup);

function mount(
  Form: typeof CorrectionForm,
  kind: string,
  settings: Record<string, unknown>,
  res: NodeResult,
  dispatch = vi.fn(),
) {
  const doc: PumpflowDoc = {
    nodes: [{ id: `${kind}-1`, kind, x: 0, y: 0, settings }],
    edges: [],
  };
  render(
    <EngineContext.Provider value={fakeEngine()}>
      <Form nodeId={`${kind}-1`} doc={doc} result={res} dispatch={dispatch} />
    </EngineContext.Provider>,
  );
  return dispatch;
}

const lastSettings = (d: ReturnType<typeof vi.fn>) =>
  d.mock.calls.at(-1)![0].settings as Record<string, unknown>;

const corrSettings = {
  lock_to_rated: true,
  target_speed: 1750,
  target_speed_unit: "rpm",
  apply_speed: true,
  apply_density: true,
  apply_viscosity: false,
  degree: 3,
  fluid_choice: "",
};

const corrResult = (view: Record<string, unknown>): NodeResult => ({
  kind: "correction",
  state: "ok",
  status: "B-34004A · 6 pts",
  badge: null,
  notes: [],
  view: {
    fluids: [],
    choice: "__default__",
    has_rated: true,
    has_fluid: false,
    viscous_text: "—",
    banner: { text: "", level: "info" },
    before_after: [
      {
        measured: { q: 100, head: 80, power: 50, eff: 55 },
        corrected: { q: 99, head: 79, power: 49.5, eff: 56 },
      },
    ],
    ...view,
  },
});

describe("CorrectionForm", () => {
  it("renders the key fields and the before/after table", async () => {
    mount(CorrectionForm, "correction", corrSettings, corrResult({}));
    expect(await screen.findByLabelText("Target speed")).toBeTruthy();
    expect((screen.getByLabelText("Target speed") as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByLabelText(/Speed \(affinity\) correction/)).toBeTruthy();
    expect(screen.getByLabelText(/Density \(ρ_rated \/ ρ_test\) correction/)).toBeTruthy();
    expect(screen.getByLabelText(/Viscosity correction \(HI 9\.6\.7\)/)).toBeTruthy();
    expect((screen.getByLabelText("Fit degree") as HTMLSelectElement).value).toBe("3");
    const table = screen.getByRole("table", { name: "Before / after correction" });
    await waitFor(() => expect(table.textContent).toContain("100.00"));
    expect(table.textContent).toContain("measured");
    expect(table.textContent).toContain("corrected");
    expect(table.textContent).toContain("55.0");
  });

  it("unlocks the target speed and writes the edits", async () => {
    const dispatch = mount(CorrectionForm, "correction", corrSettings, corrResult({}));
    fireEvent.click(await screen.findByLabelText(/Lock target speed to rated N/));
    const speed = screen.getByLabelText("Target speed") as HTMLInputElement;
    expect(speed.disabled).toBe(false);
    fireEvent.change(speed, { target: { value: "1800" } });
    fireEvent.change(screen.getByLabelText("Fit degree"), { target: { value: "4" } });
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({
      lock_to_rated: false,
      target_speed: 1800,
      degree: 4,
    });
  });

  it("is forced without a rated point: manual speed, density needs a fluid", async () => {
    mount(
      CorrectionForm,
      "correction",
      corrSettings,
      corrResult({
        has_rated: false,
        banner: { text: "No rated point connected — forced speed correction", level: "info" },
      }),
    );
    expect(((await screen.findByLabelText("Target speed")) as HTMLInputElement).disabled).toBe(false);
    expect((screen.getByLabelText(/Lock target speed to rated N/) as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByLabelText(/Density \(ρ_rated \/ ρ_test\) correction/) as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByText(/forced speed correction/)).toBeTruthy();
  });
});

describe("CurveFitForm", () => {
  const settings = { degree: 3, spline: true, resolution: 160, show_preview: true };
  const res = (state: NodeResult["state"]): NodeResult => ({
    kind: "curve_fit",
    state,
    status: "Waiting for corrected curve",
    badge: null,
    notes: [],
    view:
      state === "ok"
        ? {
            r2_text: "R²(head)=0.9988  ·  R²(power)=0.9970",
            coeff_text: "  Head:  +1.0000e-05  -2.0000e-03",
          }
        : {},
  });

  it("renders degree, spline, resolution, R² and the coefficients", async () => {
    mount(CurveFitForm as never, "curve_fit", settings, res("ok"));
    expect((await screen.findByLabelText("Polynomial degree")) as HTMLSelectElement).toBeTruthy();
    expect((screen.getByLabelText("Curve resolution") as HTMLInputElement).value).toBe("160");
    expect(screen.getByLabelText(/Overlay natural cubic spline/)).toBeTruthy();
    expect(screen.getByLabelText(/Show preview/)).toBeTruthy();
    expect(screen.getByText(/R²\(head\)=0.9988/)).toBeTruthy();
    expect(screen.getByText(/Head: \+1\.0000e-05/)).toBeTruthy();
  });

  it("writes the settings; an out-of-range resolution is not committed", async () => {
    const dispatch = mount(CurveFitForm as never, "curve_fit", settings, res("ok"));
    const resolution = (await screen.findByLabelText("Curve resolution")) as HTMLInputElement;
    fireEvent.change(resolution, { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText("Polynomial degree"), { target: { value: "2" } });
    fireEvent.click(screen.getByLabelText(/Overlay natural cubic spline/));
    await waitFor(() => expect(dispatch).toHaveBeenCalled(), { timeout: 2000 });
    expect(lastSettings(dispatch)).toMatchObject({ degree: 2, spline: false, resolution: 160 });
    fireEvent.change(resolution, { target: { value: "200" } });
    await waitFor(() => expect(lastSettings(dispatch).resolution).toBe(200), { timeout: 2000 });
  });

  it("shows the node status while there is no fit", async () => {
    mount(CurveFitForm as never, "curve_fit", settings, res("idle"));
    expect(await screen.findByText("Waiting for corrected curve")).toBeTruthy();
  });
});
