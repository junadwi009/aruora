import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "./client";

beforeEach(() => { vi.restoreAllMocks(); });

describe("api client", () => {
  it("health calls /api/health and returns parsed json", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK",
      text: async () => JSON.stringify({ ok: true, llmMode: "stub", providerConfigured: false, asrReady: false }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const h = await api.health();
    expect(h.ok).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain("/api/health");
  });

  it("speakingTranscribe posts multipart audio and returns transcript", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK",
      text: async () => JSON.stringify({ transcript: "Hello world.", asr: true }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const blob = new Blob([new Uint8Array([1, 2, 3])], { type: "audio/webm" });
    const out = await api.speakingTranscribe(blob);
    expect(out.transcript).toBe("Hello world.");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/speaking/transcribe");
    expect(init.body).toBeInstanceOf(FormData);
    // must NOT force application/json — the browser sets the multipart boundary
    expect(init.headers?.["Content-Type"]).toBeUndefined();
  });

  it("statsTrends and historyAttempts hit the right endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK",
      text: async () => JSON.stringify({ writing: [], speaking: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.statsTrends();
    expect(fetchMock.mock.calls[0][0]).toContain("/api/stats/trends");
    await api.historyAttempts("writing");
    expect(fetchMock.mock.calls[1][0]).toContain("/api/history/attempts?type=writing");
    await api.historyAttempt(7);
    expect(fetchMock.mock.calls[2][0]).toContain("/api/history/attempt/7");
  });

  it("throws ApiError with code on non-2xx", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 422, statusText: "Unprocessable",
      text: async () => JSON.stringify({ error: { code: "VALIDATION", message: "bad" } }),
    }));
    await expect(api.onboarding({ name: "", goal: "work", targetBand: 6.5 } as never)).rejects.toMatchObject({ code: "VALIDATION" });
  });
});
