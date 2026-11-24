import { describe, expect, it } from "vitest";
import { parseProject, projectFileName } from "./files";

describe("files", () => {
  it("parses a project and rejects non-projects", () => {
    expect(parseProject('{"nodes": [], "edges": []}')).toEqual({ nodes: [], edges: [] });
    expect(() => parseProject("not json")).toThrow(/not valid JSON/);
    expect(() => parseProject("[]")).toThrow(/not a PumpFlow project/);
    expect(() => parseProject('{"edges": []}')).toThrow(/not a PumpFlow project/);
  });

  it("names the saved file name.pumpflow", () => {
    expect(projectFileName("B-1")).toBe("B-1.pumpflow");
    expect(projectFileName("B-1.pumpflow")).toBe("B-1.pumpflow");
    expect(projectFileName("  ")).toBe("project.pumpflow");
  });
});
