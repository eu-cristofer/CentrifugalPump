import { describe, expect, it } from "vitest";
import { kebab, portColor, statusBeside, toneColors } from "./card";

describe("statusBeside", () => {
  it("drops the segment the verdict pill already shows", () => {
    expect(statusBeside("B-1A · APPROVED ✓ (provisional)", ["APPROVED", "ok"])).toBe("B-1A");
    expect(statusBeside("a · b · APPROVED", ["APPROVED", "ok"])).toBe("a · b");
  });

  it("returns an empty string when only the badge segment is left", () => {
    expect(statusBeside("REJECTED ✗", ["REJECTED", "fail"])).toBe("");
  });

  it("is the plain status (newlines flattened) without a badge", () => {
    expect(statusBeside("one\ntwo", null)).toBe("one two");
    expect(statusBeside("", undefined)).toBe("");
  });
});

describe("port colours", () => {
  it("kebab-cases the signal type", () => {
    expect(kebab("RatedPoint")).toBe("rated-point");
    expect(portColor("RatedPoint")).toBe("var(--port-rated-point)");
    expect(portColor("FluidSpec")).toBe("var(--port-fluid-spec)");
    expect(portColor("TestPointSet")).toBe("var(--port-test-point-set)");
    expect(portColor("CorrectedCurve")).toBe("var(--port-corrected-curve)");
    expect(portColor("FittedModel")).toBe("var(--port-fitted-model)");
    expect(portColor("ComplianceResult")).toBe("var(--port-compliance-result)");
  });

  it("uses the bundle colour for any other type", () => {
    expect(portColor("*")).toBe("var(--port-branch-bundle)");
    expect(portColor("Whatever")).toBe("var(--port-branch-bundle)");
  });

  it("gives the warn pill dark text and the others light text", () => {
    expect(toneColors("warn").text).toBe("var(--body-text)");
    expect(toneColors("ok")).toEqual({ fill: "var(--ok-green)", text: "var(--title-text)" });
    expect(toneColors("fail").fill).toBe("var(--reject-red)");
  });
});
