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
    headers: { "Content-Type": "application/json", ...(opts.headers ?? {}) },
    ...opts,
  });
  const text = await res.text();
  const body = text ? (JSON.parse(text) as { error?: { code: string; message: string; details?: unknown } }) : null;
  if (!res.ok) {
    const err = body?.error ?? { code: "INTERNAL", message: res.statusText };
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
  const res = await fetch(BASE + path, { method: "POST", body: form });
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
  program: (lengthDays: number) => post<ProgramResult>("/api/program", { lengthDays }),
  milestones: () => get<Milestone[]>("/api/program/milestones"),
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
  historyAttempts: (type?: "writing" | "speaking") =>
    get<AttemptSummary[]>(`/api/history/attempts${type ? `?type=${type}` : ""}`),
  historyAttempt: (id: number) => get<AttemptDetail>(`/api/history/attempt/${id}`),
  lessonToday: () => get<LessonToday>("/api/lesson/today"),
  lessonGenerate: (b: { day?: number; focus?: string; band?: string; force?: boolean }) =>
    post<LessonToday>("/api/lesson/generate", b),
  lesson: (day: number) => get<{ day: number; focus?: string; lesson: Lesson | null }>(`/api/lesson/${day}`),
};
