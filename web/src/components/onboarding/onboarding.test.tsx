import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { JourneyProvider } from "../../lib/journey";
import { Onboarding } from "./Onboarding";
import { api } from "../../lib/api/client";

vi.mock("../../lib/api/client", () => ({
  api: { onboarding: vi.fn().mockResolvedValue({ id: 1 }) },
  ApiError: class extends Error {},
}));

function setup() {
  return render(
    <JourneyProvider>
      <Onboarding />
    </JourneyProvider>
  );
}

describe("Onboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("walks the 4 steps and posts the profile", async () => {
    setup();
    // Step 1: name
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Arjuna" },
    });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    // Step 2: goal
    fireEvent.click(screen.getByText(/work/i));
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    // Step 3: target -> continue
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    // Step 4: optional deadline — leave empty, finish
    fireEvent.click(screen.getByRole("button", { name: /start placement/i }));
    await waitFor(() => expect(api.onboarding).toHaveBeenCalled());
    const arg = (api.onboarding as any).mock.calls.at(-1)[0];
    expect(arg).toMatchObject({ name: "Arjuna", goal: "work" });
    expect(arg.targetBand).toBeGreaterThanOrEqual(4.0);
    expect(arg.examDate).toBeUndefined();
  });

  it("sends the exam month when the optional deadline is filled", async () => {
    setup();
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "A" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByText(/work/i));
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.change(screen.getByLabelText(/exam month/i), {
      target: { value: "2027-03" },
    });
    fireEvent.click(screen.getByRole("button", { name: /start placement/i }));
    await waitFor(() => expect(api.onboarding).toHaveBeenCalled());
    expect((api.onboarding as any).mock.calls.at(-1)[0].examDate).toBe("2027-03");
  });

  it("disables Next on step 1 until a name is entered", () => {
    setup();
    const next = screen.getByRole("button", {
      name: /next/i,
    }) as HTMLButtonElement;
    expect(next.disabled).toBe(true);
  });
});
