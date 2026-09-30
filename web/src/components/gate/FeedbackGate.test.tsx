import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FeedbackGate } from "./FeedbackGate";

vi.mock("../../lib/api/client", () => ({
  api: { gateUnlock: vi.fn(async () => ({ unlocked: true })) },
}));
vi.mock("../../lib/i18n", () => ({
  useT: () => ({ t: (k: string) => k }),
}));

describe("FeedbackGate", () => {
  it("disables submit until rating + 20-char insight, then unlocks", async () => {
    const onUnlocked = vi.fn();
    render(<FeedbackGate onUnlocked={onUnlocked} />);
    const submit = screen.getByRole("button", {
	  name: "Submit & continue",
	});
    expect(submit).toBeDisabled();
    fireEvent.click(
	  screen.getByRole("radio", { name: "4 ★" })
	);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "This is a sufficiently long insight." },
    });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    await waitFor(() => expect(onUnlocked).toHaveBeenCalled());
  });
});
