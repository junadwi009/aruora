import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthForm } from "./AuthForm";
import * as learningApi from "../../experience/learning/api";
import { api, ApiError } from "../../lib/api/client";

const USER = { id: 1, email: "learner@example.invalid", name: "", goal: "other", targetBand: 6 };
const PASS = "correct horse battery staple";
function fill() {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: USER.email } });
  fireEvent.change(screen.getByLabelText(/^Password/, { selector: "input" }), { target: { value: PASS } });
}
beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api, "health").mockResolvedValue({ ok: true, llmMode: "stub", providerConfigured: false, asrReady: false, googleClientId: "" });
});

describe("AuthForm: production account wiring", () => {
  it("logs in and calls onSuccess with the actual API account", async () => {
    vi.spyOn(learningApi, "request").mockResolvedValue(USER);
    const success = vi.fn();
    render(<AuthForm mode="login" onSuccess={success} />);
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Log in to my workspace" }));
    await waitFor(() => expect(success).toHaveBeenCalledWith(USER));
    expect(learningApi.request).toHaveBeenCalledWith(
  "/api/account/login",
  expect.objectContaining({
		email: USER.email,
		password: PASS,
		remember: false,
		totp: "",
	  }),
	);
  });
  it("registers via accountRegister and forwards its returned identity", async () => {
    vi.spyOn(api, "accountRegister").mockResolvedValue(USER);
    const success = vi.fn();
    render(<AuthForm mode="register" onSuccess={success} />);
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Create my account" }));
    await waitFor(() => expect(success).toHaveBeenCalledWith(USER));
    expect(api.accountRegister).toHaveBeenCalledWith({ email: USER.email, password: PASS });
  });
  it("does not authenticate when login fails", async () => {
    vi.spyOn(learningApi, "request").mockRejectedValue(
	  new ApiError(
		"UNAUTHORIZED",
		"Incorrect email or password",
	  ),
	);
    const success = vi.fn();
    render(<AuthForm mode="login" onSuccess={success} />);
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Log in to my workspace" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Sign-in was not completed/);
    expect(success).not.toHaveBeenCalled();
  });
  it("rejects a short registration password before the API call", () => {
    vi.spyOn(api, "accountRegister");
    const { container } = render(<AuthForm mode="register" onSuccess={vi.fn()} />);
    fill();
    fireEvent.change(screen.getByLabelText(/^Password/, { selector: "input" }), { target: { value: "short" } });
    fireEvent.submit(container.querySelector("form")!);
    expect(screen.getByRole("alert")).toHaveTextContent(/at least 15 characters/);
    expect(api.accountRegister).not.toHaveBeenCalled();
  });
  it("does not expose arbitrary exception details", async () => {
    vi.spyOn(api, "accountLogin").mockRejectedValue(new Error("PRIVATE_SERVER_DETAIL"));
    render(<AuthForm mode="login" onSuccess={vi.fn()} />);
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Log in to my workspace" }));
    expect(await screen.findByRole("alert")).not.toHaveTextContent("PRIVATE_SERVER_DETAIL");
  });
});
