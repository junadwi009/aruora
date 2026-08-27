/**
 * WS05-04 — output-handling guard: model output must render as text.
 *
 * The web client renders every LLM-derived string through React's default
 * text pipeline. This suite fails the build if anyone reintroduces raw
 * HTML/JS evaluation surfaces that model output could reach.
 */
import { describe, expect, it } from "vitest";

// Load every source file (including this one) as raw text via Vite.
const modules = import.meta.glob("../**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const FORBIDDEN: RegExp[] = [
  /dangerouslySetInnerHTML/,
  /\binnerHTML\s*=/,
  /(?<![.\w])eval\s*\(/,
  /new\s+Function\s*\(/,
];

describe("WS05-04 output rendering guardrails", () => {
  it("never renders model/LLM output as HTML or executes dynamic code", () => {
    const offenders: string[] = [];
    for (const [path, text] of Object.entries(modules)) {
      if (path.endsWith("outputHandlingGuard.test.ts")) continue; // own literals
      for (const rx of FORBIDDEN) {
        if (rx.test(text)) offenders.push(`${path}: ${rx}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});
