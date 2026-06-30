import { describe, it, expect } from "vitest";
import { bandFromPct } from "./band";

describe("bandFromPct", () => {
  it("maps high scores to high bands", () => {
    expect(bandFromPct(100)).toBe(8);
    expect(bandFromPct(90)).toBe(8);
    expect(bandFromPct(85)).toBe(7.5);
    expect(bandFromPct(72)).toBe(7);
  });
  it("maps mid scores", () => {
    expect(bandFromPct(62)).toBe(6.5);
    expect(bandFromPct(55)).toBe(6);
    expect(bandFromPct(45)).toBe(5.5);
  });
  it("floors low scores", () => {
    expect(bandFromPct(35)).toBe(5);
    expect(bandFromPct(10)).toBe(4.5);
    expect(bandFromPct(0)).toBe(4.5);
  });
});
