import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PasscodeGate } from "./PasscodeGate";
import { api } from "../../lib/api/client";

beforeEach(() => vi.restoreAllMocks());

describe("PasscodeGate", () => {
  it("calls onUnlock after a successful login", async () => {
    vi.spyOn(api, "authLogin").mockResolvedValue({ ok: true });
    const onUnlock = vi.fn();
    render(<PasscodeGate onUnlock={onUnlock} />);
    fireEvent.change(screen.getByLabelText("Passcode"), { target: { value: "1234" } });
    fireEvent.click(screen.getByRole("button", { name: /unlock/i }));
    await waitFor(() => expect(onUnlock).toHaveBeenCalled());
  });

  it("shows an error on a failed login", async () => {
    vi.spyOn(api, "authLogin").mockRejectedValue(new Error("nope"));
    render(<PasscodeGate onUnlock={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Passcode"), { target: { value: "bad" } });
    fireEvent.click(screen.getByRole("button", { name: /unlock/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
  });
});
