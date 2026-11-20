import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CATALOG } from "../project/catalog.fixture";
import Toolbox, { groupCatalog } from "./Toolbox";

afterEach(cleanup);

describe("Toolbox", () => {
  it("groups the catalog keeping its order", () => {
    expect(groupCatalog(CATALOG).map(([g, es]) => [g, es.map((e) => e.kind)])).toEqual([
      ["Inputs", ["fluid", "rated_point", "test_points"]],
      ["Output", ["sink"]],
    ]);
  });

  it("shows upper-case group headers and adds a node on click", () => {
    const onAdd = vi.fn();
    render(<Toolbox catalog={CATALOG} onAdd={onAdd} />);
    expect(screen.getByText("INPUTS")).toBeTruthy();
    expect(screen.getByText("OUTPUT")).toBeTruthy();
    fireEvent.click(screen.getByText("Rated point"));
    expect(onAdd).toHaveBeenCalledWith("rated_point");
  });

  it("toggles the list from the Nodes button", () => {
    render(<Toolbox catalog={CATALOG} onAdd={() => undefined} />);
    const toggle = screen.getByRole("button", { name: "Nodes" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
  });
});
