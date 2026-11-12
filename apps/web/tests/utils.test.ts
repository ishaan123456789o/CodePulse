import { describe, expect, it } from "vitest";
import { number, signed, freshness } from "../lib/utils";
describe("honest missing data display", () => {
  it("never turns missing observations into zero growth", () => {
    expect(number(null)).toBe("—");
    expect(signed(undefined)).toBe("—");
    expect(signed(-12)).toBe("-12");
    expect(signed(0)).toBe("0");
    expect(signed(12)).toBe("+12");
  });
  it("does not claim an update before an observation exists", () => {
    expect(freshness(null)).toBe("Awaiting first observation");
  });
});
