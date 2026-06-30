import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { JourneyProvider, useJourney } from "../../lib/journey";
import { Results } from "./Results";

vi.mock("../../lib/api/client", () => ({ api: {}, ApiError: class extends Error {} }));

const result = {
  perSkill: {
    listening: { cefr: "B1", ieltsApprox: 5.0, raw: "6/10", confidence: "medium" },
    reading:   { cefr: "C1", ieltsApprox: 7.0, raw: "11/13", confidence: "medium" },
    writing:   { cefr: "B1", ielts: 5.0 },
    speaking:  { cefr: "B1", ielts: 5.0 },
  },
  overallBand: 5.5, cefr: "B2", gapToTarget: 1.0,
};

function Harness() {
  const { setPlacementResult, placementResult } = useJourney();
  useEffect(() => { setPlacementResult(result as any); }, []);
  return placementResult ? <Results /> : null;
}

describe("Results", () => {
  it("shows reading level and the save/continue CTA", async () => {
    render(<JourneyProvider><Harness /></JourneyProvider>);
    expect(await screen.findByText("C1")).toBeTruthy();   // reading level chip
    const cta = await screen.findByRole("button", { name: /save your results/i });
    expect(cta).toBeTruthy();
  });

  it("renders a data-table equivalent for the radar", async () => {
    render(<JourneyProvider><Harness /></JourneyProvider>);
    // a table with the 4 skills exists for a11y
    expect(await screen.findByRole("table")).toBeTruthy();
  });
});
