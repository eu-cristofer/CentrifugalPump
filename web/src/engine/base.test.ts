// @vitest-environment node
import { describe, expect, it } from "vitest";
import { pyBase } from "./base";

describe("pyBase", () => {
  it("handles the root base", () => {
    expect(pyBase("/")).toBe("/py/");
  });

  it("handles a sub-path base", () => {
    expect(pyBase("/CentrifugalPump/app/")).toBe("/CentrifugalPump/app/py/");
  });

  it("handles a relative base", () => {
    expect(pyBase("./")).toBe("./py/");
  });

  it("adds a missing trailing slash", () => {
    expect(pyBase("/CentrifugalPump/app")).toBe("/CentrifugalPump/app/py/");
  });

  it("defaults to the build base", () => {
    expect(pyBase()).toBe(pyBase(import.meta.env.BASE_URL));
  });
});
