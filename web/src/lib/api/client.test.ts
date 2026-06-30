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

  it("lesson endpoints hit the right URLs", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK",
      text: async () => JSON.stringify({ day: 1, focus: "writing", skill: "writing", band: "B1", lesson: null }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.lessonToday();
    expect(fetchMock.mock.calls[0][0]).toContain("/api/lesson/today");
    await api.lessonGenerate({ day: 2, focus: "listening", band: "B1" });
    expect(fetchMock.mock.calls[1][0]).toContain("/api/lesson/generate");
    await api.lesson(2);
    expect(fetchMock.mock.calls[2][0]).toContain("/api/lesson/2");
  });

  it("mock endpoints hit the right URLs", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify([]),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.mocksList();
    expect(fetchMock.mock.calls[0][0]).toContain("/api/mocks");
    await api.mockSave({ listening: 6, reading: 7, overall: 6.5 });
    expect(fetchMock.mock.calls[1][0]).toContain("/api/mocks");
    expect(fetchMock.mock.calls[1][1].method).toBe("POST");
  });

  it("pronounce endpoints hit the right URLs", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify({}),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.pronounceSentence({ level: "B1" });
    expect(fetchMock.mock.calls[0][0]).toContain("/api/pronounce/sentence");
    await api.pronounceFeedback({ target: "a", transcript: "a", accuracy: 100, missed: [] });
    expect(fetchMock.mock.calls[1][0]).toContain("/api/pronounce/feedback");
  });

  it("vocab + card endpoints hit the right URLs", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify({}),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.vocab({ topic: "x" });
    expect(fetchMock.mock.calls[0][0]).toContain("/api/vocab");
    await api.cardsDue();
    expect(fetchMock.mock.calls[1][0]).toContain("/api/cards/due");
    await api.cardReview(3, 4);
    expect(fetchMock.mock.calls[2][0]).toContain("/api/cards/3/review");
    await api.cardDelete(3);
    expect(fetchMock.mock.calls[3][1].method).toBe("DELETE");
  });

  it("practiceAttempt posts to the right URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify({ savedId: 1 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api.practiceAttempt({ skill: "reading", band: 7, correct: 9, total: 10 });
    expect(fetchMock.mock.calls[0][0]).toContain("/api/practice/attempt");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
  });

  it("throws ApiError with code on non-2xx", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 422, statusText: "Unprocessable",
      text: async () => JSON.stringify({ error: { code: "VALIDATION", message: "bad" } }),
    }));
    await expect(api.onboarding({ name: "", goal: "work", targetBand: 6.5 } as never)).rejects.toMatchObject({ code: "VALIDATION" });
  });
});
