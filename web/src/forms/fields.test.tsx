import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EngineContext } from "./engineContext";
import { fakeEngine } from "./fakeEngine";
import {
  Banner,
  Checkbox,
  InfoButton,
  NumberField,
  Row,
  UnitField,
  formatNumber,
  parseNumber,
} from "./fields";

afterEach(cleanup);

describe("parseNumber", () => {
  it.each([
    ["1,5", 1.5],
    ["1.5", 1.5],
    [" -2,25 ", -2.25],
    ["", null],
  ])("%j -> %j", (text, value) => {
    expect(parseNumber(text)).toEqual({ ok: true, value });
  });

  it("rejects text that is not a number", () => {
    expect(parseNumber("abc").ok).toBe(false);
    expect(parseNumber("-").ok).toBe(false);
  });

  it("formats with a dot and no float noise", () => {
    expect(formatNumber(null)).toBe("");
    expect(formatNumber(440.28700000000003)).toBe("440.287");
  });
});

describe("NumberField", () => {
  it("accepts a decimal comma and reports empty as null", () => {
    const onChange = vi.fn();
    render(<NumberField value={null} onChange={onChange} ariaLabel="n" />);
    const input = screen.getByLabelText("n");
    fireEvent.change(input, { target: { value: "12,5" } });
    expect(onChange).toHaveBeenLastCalledWith(12.5);
    fireEvent.change(input, { target: { value: "abc" } });
    expect(onChange).toHaveBeenCalledTimes(1);
    fireEvent.change(input, { target: { value: "" } });
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("shows an outside change with a dot", () => {
    const { rerender } = render(<NumberField value={1} onChange={() => undefined} ariaLabel="n" />);
    rerender(<NumberField value={2.5} onChange={() => undefined} ariaLabel="n" />);
    expect((screen.getByLabelText("n") as HTMLInputElement).value).toBe("2.5");
  });
});

describe("UnitField", () => {
  it("converts through the engine and writes both value and unit", async () => {
    const engine = fakeEngine();
    const onChange = vi.fn();
    render(
      <EngineContext.Provider value={engine}>
        <Row label="Capacity Q">
          <UnitField dimension="capacity" value={100} unit="m³/h" onChange={onChange} />
        </Row>
      </EngineContext.Provider>,
    );
    await screen.findByRole("option", { name: "US GPM" });
    fireEvent.change(screen.getByLabelText("Capacity Q unit"), { target: { value: "US GPM" } });
    await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
    expect(engine.convert).toHaveBeenCalledWith(100, "m³/h", "US GPM", "capacity", null);
    const [v, u] = onChange.mock.calls[0] as [number, string];
    expect(v).toBeCloseTo(440.287, 6);
    expect(u).toBe("US GPM");
  });

  it("writes the typed value with the current unit", async () => {
    const engine = fakeEngine();
    const onChange = vi.fn();
    render(
      <EngineContext.Provider value={engine}>
        <Row label="Capacity Q">
          <UnitField dimension="capacity" value={100} unit="m³/h" onChange={onChange} />
        </Row>
      </EngineContext.Provider>,
    );
    fireEvent.change(screen.getByLabelText("Capacity Q"), { target: { value: "250,5" } });
    expect(onChange).toHaveBeenCalledWith(250.5, "m³/h");
  });
});

describe("other fields", () => {
  it("InfoButton shows the explain text, title first", async () => {
    render(
      <EngineContext.Provider value={fakeEngine()}>
        <InfoButton infoKey="head" />
      </EngineContext.Provider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Info: head" }));
    expect(await screen.findByText("Title of head")).toBeTruthy();
    expect(screen.getByText("Body of head")).toBeTruthy();
  });

  it("Checkbox shows a tick when checked and toggles", () => {
    const onChange = vi.fn();
    render(<Checkbox checked label="Parallel" onChange={onChange} />);
    expect(screen.getByText("✓")).toBeTruthy();
    fireEvent.click(screen.getByRole("checkbox", { name: "Parallel" }));
    expect(onChange).toHaveBeenCalledWith(false);
  });

  it("Banner uses an alert role only for errors", () => {
    render(
      <>
        <Banner kind="error">bad</Banner>
        <Banner kind="info">fine</Banner>
      </>,
    );
    expect(screen.getByRole("alert").textContent).toBe("bad");
    expect(screen.getByRole("status").textContent).toBe("fine");
  });
});
