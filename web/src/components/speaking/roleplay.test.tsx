import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Roleplay } from "./Roleplay";
import { api } from "../../lib/api/client";

beforeEach(() => vi.restoreAllMocks());

describe("Roleplay", () => {
  it("starts a scenario and shows the opener; AI replies to a turn", async () => {
    vi.spyOn(api, "health").mockResolvedValue({ ok: true, llmMode: "stub", providerConfigured: false, asrReady: false });
    vi.spyOn(api, "speakingRoleplay").mockResolvedValue({ reply: "Nice! What do you like about it?" });
    render(<Roleplay />);
    fireEvent.click(screen.getByText("Hometown chat"));
    expect(screen.getByText(/where is your hometown/i)).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Your reply"), { target: { value: "It's a small coastal town." } });
    fireEvent.click(screen.getByLabelText("Send"));
    await waitFor(() => expect(screen.getByText(/what do you like about it/i)).toBeTruthy());
  });
});
