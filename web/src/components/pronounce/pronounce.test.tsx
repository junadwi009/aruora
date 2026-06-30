import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Pronounce } from "./Pronounce";
import { ViewProvider } from "../menu/viewContext";
import { api } from "../../lib/api/client";

beforeEach(() => vi.restoreAllMocks());

describe("Pronounce", () => {
  it("renders the seed target sentence and a New sentence control", async () => {
    // Recorder probes health on mount — keep it offline-safe.
    vi.spyOn(api, "health").mockResolvedValue({
      ok: true, llmMode: "stub", providerConfigured: false, asrReady: false,
    });
    render(
      <ViewProvider>
        <Pronounce />
      </ViewProvider>
    );
    // sentence is rendered word-by-word in separate spans; match one word
    expect(screen.getByText(/early/)).toBeTruthy();
    expect(screen.getByText("New sentence")).toBeTruthy();
  });
});
