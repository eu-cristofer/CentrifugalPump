import { afterEach, describe, expect, it } from "vitest";
import { decimalSep, fixed, localizeNumber, setDecimalSep } from "./decimal";
import { formatNumber, parseNumber } from "./forms/fields";

describe("decimal separator", () => {
  afterEach(() => setDecimalSep("."));

  it("defaults to the point", () => {
    expect(decimalSep()).toBe(".");
    expect(fixed(9.8, 2)).toBe("9.80");
    expect(formatNumber(1234.5)).toBe("1234.5");
  });

  it("shows a comma once chosen, remembers it, and still parses both", () => {
    setDecimalSep(",");
    expect(decimalSep()).toBe(",");
    expect(localStorage.getItem("pumpflow.decimalSeparator")).toBe(",");
    expect(fixed(9.8, 2)).toBe("9,80");
    expect(fixed(null, 2)).toBe("—");
    expect(formatNumber(1234.5)).toBe("1234,5");
    expect(localizeNumber("-0.25")).toBe("-0,25");
    expect(parseNumber("9.5").value).toBe(9.5);
    expect(parseNumber("9,5").value).toBe(9.5);
  });
});
