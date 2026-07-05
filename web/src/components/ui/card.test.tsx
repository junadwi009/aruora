import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Card } from "./Card";

describe("Card (interactive a11y)", () => {
  it("interactive + onClick is a keyboard-operable button", () => {
    const onClick = vi.fn();
    render(
      <Card variant="interactive" onClick={onClick}>
        Go
      </Card>,
    );
    const el = screen.getByRole("button", { name: "Go" });
    el.focus();
    expect(document.activeElement).toBe(el);
    fireEvent.keyDown(el, { key: "Enter" });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("Space also activates the interactive card", () => {
    const onClick = vi.fn();
    render(
      <Card variant="interactive" onClick={onClick}>
        Go
      </Card>,
    );
    fireEvent.keyDown(screen.getByRole("button", { name: "Go" }), { key: " " });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("a plain card is not exposed as a button", () => {
    render(<Card>Static</Card>);
    expect(screen.queryByRole("button")).toBeNull();
  });
});
