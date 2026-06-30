import { describe, it, expect } from "vitest";
import { wordAccuracy } from "./pron";

describe("wordAccuracy", () => {
  it("is 100% for an exact match (case/space insensitive)", () => {
    const r = wordAccuracy("The cat sat", "the   CAT sat");
    expect(r.accuracy).toBe(100);
    expect(r.missed).toEqual([]);
  });

  it("flags missed words and computes partial accuracy", () => {
    const r = wordAccuracy("The big brown dog", "the dog");
    expect(r.missed).toContain("big");
    expect(r.missed).toContain("brown");
    expect(r.accuracy).toBe(50); // 2 of 4 matched
  });

  it("ignores punctuation", () => {
    const r = wordAccuracy("Hello, world!", "hello world");
    expect(r.accuracy).toBe(100);
  });

  it("handles empty transcript", () => {
    const r = wordAccuracy("one two", "");
    expect(r.accuracy).toBe(0);
    expect(r.missed).toEqual(["one", "two"]);
  });
});
