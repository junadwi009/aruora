import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthForm } from "./AuthForm";
import { api } from "../../lib/api/client";

const USER = { id: 1, email: "a@b.com", name: "", goal: "other", targetBand: 6 };

beforeEach(() => {
  vi.restoreAllMocks();
  // AuthForm fetches health on mount to decide whether to show the Google button.
  vi.spyOn(api, "health").mockResolvedValue({
    ok: true, llmMode: "stub", providerConfigured: false, asrReady: false, googleClientId: "",
  });
});

describe("AuthForm", () => {
  it("logs in and calls onSuccess", async () => {
    vi.spyOn(api, "accountLogin").mockResolvedValue(USER);
    const onSuccess = vi.fn();
    render(<AuthForm mode="login" onSuccess={onSuccess} />);
    fireEvent.change(screen.getByPlaceholderText(/you@example/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByPlaceholderText(/6 characters/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(USER));
  });

  it("registers via accountRegister", async () => {
    vi.spyOn(api, "accountRegister").mockResolvedValue(USER);
    const onSuccess = vi.fn();
    render(<AuthForm mode="register" onSuccess={onSuccess} />);
    fireEvent.change(screen.getByPlaceholderText(/you@example/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByPlaceholderText(/6 characters/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => expect(api.accountRegister).toHaveBeenCalled());
  });

  it("shows an error when login fails", async () => {
    vi.spyOn(api, "accountLogin").mockRejectedValue(new Error("Incorrect email or password"));
    render(<AuthForm mode="login" onSuccess={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText(/you@example/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByPlaceholderText(/6 characters/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
  });
});
