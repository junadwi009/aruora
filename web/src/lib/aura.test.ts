/**
 * WS23 — Aura voice guardrails: approved copy stays claim-safe, and the
 * forbidden-fragment list actually rejects the classic violations.
 */
import { describe, expect, it } from "vitest";
import { AURA_COPY, AURA_FORBIDDEN_PATTERNS } from "./aura";

describe("Aura approved copy", () => {
  it("covers every defined moment in both locales", () => {
    for (const moment of Object.keys(AURA_COPY)) {
      const copy = AURA_COPY[moment as keyof typeof AURA_COPY];
      expect(copy.en.length).toBeGreaterThan(0);
      expect(copy.id.length).toBeGreaterThan(0);
    }
  });

  it("contains no official-score / guarantee / examiner claims", () => {
    const texts = Object.values(AURA_COPY).flatMap((c) => [c.en, c.id]);
    for (const text of texts) {
      for (const rx of AURA_FORBIDDEN_PATTERNS) {
        expect(rx.test(text), `violated ${rx} in: ${text}`).toBe(false);
      }
    }
  });

  it("forbidden patterns reject the classic violations", () => {
    expect(AURA_FORBIDDEN_PATTERNS.some((rx) => rx.test("You are guaranteed band 7"))).toBe(true);
    expect(AURA_FORBIDDEN_PATTERNS.some((rx) => rx.test("Official score: 7.0"))).toBe(true);
    expect(AURA_FORBIDDEN_PATTERNS.some((rx) => rx.test("An examiner would say 6"))).toBe(true);
  });

  it("keeps estimate framing honest", () => {
    // The placement-result moment must acknowledge that scores are estimates.
    const c = AURA_COPY.placementResult;
    expect(/estimate|estimasi/i.test(c.en + c.id)).toBe(true);
  });
});
