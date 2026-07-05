import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RadioCard } from "./RadioCard";

function Group() {
  return (
    <div role="radiogroup" aria-label="Choices">
      <RadioCard selected onSelect={() => {}} title="First" />
      <RadioCard selected={false} onSelect={() => {}} title="Second" />
      <RadioCard selected={false} onSelect={() => {}} title="Third" />
    </div>
  );
}

describe("RadioCard (a11y)", () => {
  it("ArrowDown moves focus to the next radio", () => {
    render(<Group />);
    const radios = screen.getAllByRole("radio");
    radios[0].focus();
    fireEvent.keyDown(radios[0], { key: "ArrowDown" });
    expect(document.activeElement).toBe(radios[1]);
  });

  it("ArrowRight also moves to the next radio", () => {
    render(<Group />);
    const radios = screen.getAllByRole("radio");
    radios[1].focus();
    fireEvent.keyDown(radios[1], { key: "ArrowRight" });
    expect(document.activeElement).toBe(radios[2]);
  });

  it("ArrowUp wraps from the first radio to the last", () => {
    render(<Group />);
    const radios = screen.getAllByRole("radio");
    radios[0].focus();
    fireEvent.keyDown(radios[0], { key: "ArrowUp" });
    expect(document.activeElement).toBe(radios[radios.length - 1]);
  });

  it("Enter still selects", () => {
    const onSelect = vi.fn();
    render(
      <div role="radiogroup">
        <RadioCard selected={false} onSelect={onSelect} title="Only" />
      </div>,
    );
    const r = screen.getByRole("radio");
    r.focus();
    fireEvent.keyDown(r, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
