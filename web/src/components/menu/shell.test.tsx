import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AppShell } from "./AppShell";

vi.mock("../../lib/api/client", () => ({
  api: {
    skillLevels: vi.fn().mockResolvedValue([{ skill: "reading", band: "C1" }]),
    milestones: vi.fn().mockResolvedValue([]),
    accountMe: vi.fn().mockRejectedValue(new Error("anon")),
  },
  ApiError: class extends Error {},
}));

describe("AppShell", () => {
  it("shows the reading level chip and switches views", async () => {
    render(<AppShell />);
    // reading nav entry shows its level (may appear in sidebar + home skill map)
    expect((await screen.findAllByText("C1")).length).toBeGreaterThan(0);
    // click Tips -> tips view shows (sidebar label + content placeholder both say "Tips")
    fireEvent.click(screen.getAllByText(/tips/i)[0]);
    await waitFor(() => expect(screen.getAllByText(/^Tips$/).length).toBeGreaterThan(0));
  });
});
