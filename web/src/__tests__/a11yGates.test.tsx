/**
 * WS13-07/08 — automated accessibility gates (WCAG 2.2 AA trajectory).
 *
 * axe-core runs on the two highest-traffic surfaces (Welcome = first touch,
 * Home = authenticated landing). jsdom cannot evaluate every rule; the
 * disabled set covers rules requiring real layout/painting. This is a
 * regression gate, NOT a WCAG certificate — manual keyboard/screen-reader
 * checks per 13 §Task WS13-08 remain required before release.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { JourneyProvider } from "../lib/journey";
import { I18nProvider } from "../lib/i18n";
import { ViewProvider } from "../components/menu/viewContext";
import { Welcome } from "../components/welcome/Welcome";
import { Home } from "../components/menu/Home";
import { AppShell } from "../components/menu/AppShell";
import type { CefrBand } from "../components/ui/LevelChip";

vi.mock("../../lib/api/client", () => ({
  api: {
    skillLevels: vi.fn().mockResolvedValue([
      { skill: "reading", band: "B2" },
      { skill: "listening", band: "B1" },
    ]),
    milestones: vi.fn().mockResolvedValue([]),
    accountMe: vi.fn().mockResolvedValue({
      id: 1, name: "A", goal: "work", targetBand: 6.5, examDate: null,
    }),
    statsActivity: vi.fn().mockResolvedValue({ current: 1, longest: 1, today: 0, daysActive: 1 }),
  },
  ApiError: class extends Error {},
}));

// jsdom has no layout engine — these rules need real rendering to judge.
const JSDOM_UNJUDGEABLE = ["color-contrast"];

async function expectNoCriticalViolations(container: HTMLElement) {
  const rules = Object.fromEntries(
    JSDOM_UNJUDGEABLE.map((id) => [id, { enabled: false }])
  );
  const results = await axe.run(container, { rules });
  const serious = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious"
  );
  if (serious.length) {
    console.log(
      "axe serious findings:",
      JSON.stringify(serious.map((v) => ({ id: v.id, nodes: v.nodes.length })), null, 2)
    );
  }
  expect(
    serious.map((v) => `${v.id}: ${v.nodes.length} nodes`)
  ).toEqual([]);
}

describe("WS13 accessibility gates (axe-core)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("Welcome (first-touch surface) has no serious/critical violations", async () => {
    const { container } = render(
      <I18nProvider>
        <JourneyProvider>
          <Welcome />
        </JourneyProvider>
      </I18nProvider>
    );
    await waitFor(() => expect(container.querySelector("main, header")).toBeTruthy());
    await expectNoCriticalViolations(container);
  });

  it("Home (authenticated landing) has no serious/critical violations", async () => {
    const { container } = render(
      <I18nProvider>
        <JourneyProvider>
          <ViewProvider>
            <Home levels={{ reading: "B2", listening: "B1" } as Record<string, CefrBand>} />
          </ViewProvider>
        </JourneyProvider>
      </I18nProvider>
    );
    await waitFor(() => expect(container.textContent).toContain("Journey"));
    await expectNoCriticalViolations(container);
  });

  it("AppShell provides navigation + main landmarks", async () => {
    const { container } = render(<AppShell />);
    await waitFor(() => expect(container.querySelector("nav")).toBeTruthy());
    await waitFor(() => expect(container.querySelector("main")).toBeTruthy());
  });
});
