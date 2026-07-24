import { describe, expect, it } from "vitest";
import { computeShouldBeat } from "./gate";

describe("computeShouldBeat", () => {
  it("beats only when visible, focused, locked-eligible, not admin/unlocked", () => {
    expect(computeShouldBeat({ visible: true, focused: true, unlocked: false, isAdmin: false })).toBe(true);
    expect(computeShouldBeat({ visible: false, focused: true, unlocked: false, isAdmin: false })).toBe(false);
    expect(computeShouldBeat({ visible: true, focused: false, unlocked: false, isAdmin: false })).toBe(false);
    expect(computeShouldBeat({ visible: true, focused: true, unlocked: true, isAdmin: false })).toBe(false);
    expect(computeShouldBeat({ visible: true, focused: true, unlocked: false, isAdmin: true })).toBe(false);
  });
});
