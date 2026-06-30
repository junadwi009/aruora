import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Settings } from "./Settings";
import { api } from "../../lib/api/client";

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  document.documentElement.className = "";
  document.documentElement.removeAttribute("style");
});

describe("Settings", () => {
  it("toggles dark mode and the dyslexia font", async () => {
    vi.spyOn(api, "authStatus").mockResolvedValue({ authRequired: false, authenticated: true });
    render(<Settings />);

    fireEvent.click(screen.getByRole("button", { name: /dark/i }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /dyslexia-friendly/i }));
    await waitFor(() =>
      expect(document.documentElement.style.getPropertyValue("--font-ui")).toMatch(/OpenDyslexic/i)
    );
  });
});
