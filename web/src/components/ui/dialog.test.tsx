import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Dialog } from "./Dialog";

describe("Dialog (a11y)", () => {
  it("marks the panel as a modal dialog with an accessible name", () => {
    render(
      <Dialog open onClose={() => {}} title="History">
        <button>Inside</button>
      </Dialog>,
    );
    const panel = screen.getByRole("dialog", { name: "History" });
    expect(panel.getAttribute("aria-modal")).toBe("true");
  });

  it("moves focus into the panel on open", () => {
    render(
      <Dialog open onClose={() => {}} title="History">
        <button>Inside</button>
      </Dialog>,
    );
    // First focusable inside the panel is the close button (before children).
    const closeBtn = screen.getByRole("button", { name: /close/i });
    expect(document.activeElement).toBe(closeBtn);
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(
      <Dialog open onClose={onClose} title="History">
        <button>Inside</button>
      </Dialog>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("wraps focus with Tab at the last element", () => {
    render(
      <Dialog open onClose={() => {}} title="History">
        <button>Last</button>
      </Dialog>,
    );
    const closeBtn = screen.getByRole("button", { name: /close/i });
    const last = screen.getByRole("button", { name: "Last" });
    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(closeBtn); // wrapped back to first
  });
});
