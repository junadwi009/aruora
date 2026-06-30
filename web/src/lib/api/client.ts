import type {
  Health,
  OnboardingBody,
  PlacementStart,
  PlacementResult,
  QuizSet,
  ProgramResult,
  Milestone,
  SkillLevel,
  Tips,
  WritingEval,
  SpeakingEval,
  Transcript,
  AttemptSummary,
  AttemptDetail,
  Trends,
  Lesson,
  LessonToday,
  MockScore,
  PronounceTarget,
  PronounceFeedback,
  VocabSet,
  Flashcard,
  CardStats,
  AccountUser,
} from "../types";

const BASE = (import.meta as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ?? "http://localhost:5050";

export class ApiError extends Error {
  code: string;
  details: unknown;
  constructor(code: string, message: string, details?: unknown) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    credentials: "include", // send the passcode session cookie when set
    headers: { "Content-Type": "application/json", ...(opts.headers ?? {}) },
    ...opts,
  });
  const text = await res.text();
  const body = text ? (JSON.parse(text) as { error?: { code: string; message: string; details?: unknown } }) : null;
  if (!res.ok) {
    const err = body?.error ?? { code: "INTERNAL", message: res.statusText };
    // Idle-timeout: tell the app to return to the sign-in screen.
    if (err.code === "SESSION_EXPIRED" && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("ielts:session-expired"));
    }
    throw new ApiError(err.code, err.message, (err as { details?: unknown }).details);
  }
  return body as T;
}

const post = <T>(p: string, b: unknown) =>
  request<T>(p, { method: "POST", body: JSON.stringify(b ?? {}) });
const get = <T>(p: string) => request<T>(p);

// Multipart upload — let the browser set the multipart boundary; do NOT force
// a JSON Content-Type (that would corrupt the form encoding).
async function upload<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(BASE + path, { method: "POST", body: form, credentials: "include" });
  const text = await res.text();
  const body = text ? (JSON.parse(text) as { error?: { code: string; message: string; details?: unknown } }) : null;
  if (!res.ok) {
    const err = body?.error ?? { code: "INTERNAL", message: res.statusText };
    throw new ApiError(err.code, err.message, (err as { details?: unknown }).details);
  }
  return body as T;
}

export const api = {
  health: () => get<Health>("/api/health"),
  authStatus: () => get<{ authRequired: boolean; authenticated: boolean }>("/api/auth/status"),
  authLogin: (passcode: string) => post<{ ok: boolean }>("/api/auth/login", { passcode }),
  authLogout: () => post<{ ok: boolean }>("/api/auth/logout", {}),
  accountRegister: (b: { email: string; password: string }) => post<AccountUser>("/api/account/register", b),
  accountLogin: (b: { email: string; password: string }) => post<AccountUser>("/api/account/login", b),
  accountLogout: () => post<{ ok: boolean }>("/api/account/logout", {}),
  accountMe: () => get<AccountUser>("/api/account/me"),
  accountProfile: (b: { name?: string; country?: string; examDate?: string; bio?: string; targetBand?: number; skillTargets?: Record<string, string>; reminderTime?: string | null }) =>
    request<AccountUser>("/api/account/profile", { method: "PATCH", body: JSON.stringify(b) }),
  accountAvatar: (dataUrl: string) => post<{ ok: boolean }>("/api/account/avatar", { dataUrl }),
  accountPassword: (b: { currentPassword: string; newPassword: string }) =>
    post<{ ok: boolean }>("/api/account/password", b),
  accountExport: () => get<Record<string, unknown>>("/api/account/export"),
  accountDelete: () => request<{ ok: boolean }>("/api/account", { method: "DELETE" }),
  accountForgot: (email: string) => post<{ ok: boolean }>("/api/account/forgot", { email }),
  accountReset: (b: { token: string; newPassword: string }) =>
    post<{ ok: boolean }>("/api/account/reset", b),
  onboarding: (b: OnboardingBody) => post("/api/onboarding", b),
  placementStart: () => post<PlacementStart>("/api/placement/start", {}),
  placementSubmit: (b: unknown) => post<PlacementResult>("/api/placement/submit", b),
  practiceGenerate: () => post<{ jobId: string }>("/api/practice/generate", {}),
  practiceStatus: (jobId: string) =>
    get<{ done: boolean; progress: number }>(
      `/api/practice/status?jobId=${encodeURIComponent(jobId)}`
    ),
  practiceSet: (skill: string, band?: string) =>
    get<QuizSet>(`/api/practice/set?skill=${skill}${band ? `&band=${band}` : ""}`),
  practiceAttempt: (b: { skill: string; band: number; correct: number; total: number }) =>
    post<{ savedId: number }>("/api/practice/attempt", b),
  program: (lengthDays: number) => post<ProgramResult>("/api/program", { lengthDays }),
  milestones: () => get<Milestone[]>("/api/program/milestones"),
  milestoneAdd: (b: { title: string; dayTarget: number; targets: Record<string, string> }) =>
    post<{ id: number }>("/api/program/milestones", b),
  milestoneUpdate: (id: number, b: { title?: string; dayTarget?: number; targets?: Record<string, string> }) =>
    request<Milestone>(`/api/program/milestones/${id}`, { method: "PUT", body: JSON.stringify(b) }),
  milestoneDelete: (id: number) =>
    request<{ deleted: number }>(`/api/program/milestones/${id}`, { method: "DELETE" }),
  skillLevels: () => get<SkillLevel[]>("/api/skill-levels"),
  tips: (skill: string) => get<Tips>(`/api/tips/${skill}`),
  writingEvaluate: (b: unknown) => post<WritingEval>("/api/writing/evaluate", b),
  speakingEvaluate: (b: unknown) => post<SpeakingEval>("/api/speaking/evaluate", b),
  speakingTranscribe: (audio: Blob) => {
    const form = new FormData();
    form.append("audio", audio, "speech.webm");
    return upload<Transcript>("/api/speaking/transcribe", form);
  },
  readingGenerate: (band: string) => post<QuizSet>("/api/reading/generate", { band }),
  listeningGenerate: (band: string) => post<QuizSet>("/api/listening/generate", { band }),
  statsTrends: () => get<Trends>("/api/stats/trends"),
  statsActivity: () => get<{ current: number; longest: number; today: number; daysActive: number }>("/api/stats/activity"),
  historyAttempts: (type?: "writing" | "speaking") =>
    get<AttemptSummary[]>(`/api/history/attempts${type ? `?type=${type}` : ""}`),
  historyAttempt: (id: number) => get<AttemptDetail>(`/api/history/attempt/${id}`),
  lessonToday: () => get<LessonToday>("/api/lesson/today"),
  lessonGenerate: (b: { day?: number; focus?: string; band?: string; force?: boolean }) =>
    post<LessonToday>("/api/lesson/generate", b),
  lesson: (day: number) => get<{ day: number; focus?: string; lesson: Lesson | null }>(`/api/lesson/${day}`),
  mocksList: () => get<MockScore[]>("/api/mocks"),
  mockSave: (b: { listening: number; reading: number; overall: number }) =>
    post<{ id: number }>("/api/mocks", b),
  pronounceSentence: (b: { level?: string; topic?: string }) =>
    post<PronounceTarget>("/api/pronounce/sentence", b),
  pronounceFeedback: (b: { target: string; transcript: string; accuracy: number; missed: string[] }) =>
    post<PronounceFeedback>("/api/pronounce/feedback", b),
  vocab: (b: { topic: string; level?: string }) => post<VocabSet>("/api/vocab", b),
  cardsList: () => get<{ cards: Flashcard[]; stats: CardStats }>("/api/cards"),
  cardsDue: () => get<Flashcard[]>("/api/cards/due"),
  cardAdd: (b: { front: string; back: string } | { cards: { front: string; back: string }[] }) =>
    post<{ id?: number; added?: number }>("/api/cards", b),
  cardReview: (id: number, quality: number) =>
    post<Flashcard>(`/api/cards/${id}/review`, { quality }),
  cardDelete: (id: number) => request<{ deleted: number }>(`/api/cards/${id}`, { method: "DELETE" }),
};
