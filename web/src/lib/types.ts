export type Goal = "work" | "study_abroad" | "other";
export type Cefr = "A1A2" | "B1" | "B2" | "C1" | "C2";
export type Skill = "listening" | "reading" | "writing" | "speaking";

export interface Health {
  ok: boolean;
  llmMode: string;
  providerConfigured: boolean;
  asrReady: boolean;
  googleClientId?: string;
}

/** WS03-09: an active signed-in session (device) for this account. */
export interface AccountSession {
  current: boolean;
  device: string;
  remember: boolean;
  createdAt: string | null;
  lastSeenAt: string | null;
}

/** WS03-07: privileged-action audit row (admin view). */
export interface AdminAuditEntry {
  id: number;
  action: string;
  actorEmail: string;
  actorUserId: number | null;
  targetUserId: number | null;
  detail: Record<string, unknown>;
  createdAt: string | null;
}

export interface OnboardingBody {
  name: string;
  goal: Goal;
  targetBand: number;
  skillTargets?: Record<string, unknown>;
  examDate?: string;
}

export interface PlacementItem {
  id: number;
  skill: Skill;
  bandTag: Cefr;
  type: string;
  payload: unknown;
}

export interface PlacementStart {
  comboId: number;
  sections: Record<string, unknown>;
  targetMinutes: number;
  items: PlacementItem[];
}

export interface PerSkill {
  cefr: Cefr;
  ieltsApprox?: number;
  ielts?: number | null;
  raw?: string;
  confidence?: string;
  assessed?: boolean;
}

export interface PlacementResult {
  perSkill: Record<Skill, PerSkill>;
  overallBand: number;
  cefr: Cefr;
  gapToTarget: number;
}

export interface Milestone {
  id?: number;
  idx: number;
  dayTarget: number;
  title: string;
  targets: Record<string, Cefr>;
}

export interface ProgramResult {
  program: { id: number; lengthDays: number; status: string };
  milestones: Milestone[];
}

export interface SkillLevel {
  skill: Skill;
  band: Cefr;
}

export interface QuizQuestion {
  stem: string;
  options?: string[];
  answer: string;
  explanation?: string;
}

export interface QuizSet {
  title?: string;
  passage?: string;
  transcript?: string;
  questions: QuizQuestion[];
  stub?: boolean;
}

export interface EssayMetrics {
  wordCount: number;
  sentenceCount: number;
  readability: {
    fleschReadingEase: number;
    fleschKincaidGrade: number;
    gunningFog: number;
  };
  lexicalDiversity: {
    ttr: number;
    mtld: number | null;
  };
  syntax: {
    meanSentenceLength: number | null;
    meanDependencyDepth: number | null;
    nLongWords: number | null;
  } | null;
}

export interface WritingEval {
  bands: Record<string, number>;
  cefr: Cefr;
  corrections: unknown[];
  rewrite?: string;
  stub?: boolean;
  metrics?: EssayMetrics;
}

export interface SpeakingEval {
  // Pronunciation is "unassessed" (string) until ASR audio evidence exists (WS02-04)
  bands: Record<string, number | string>;
  cefr: Cefr;
  feedback?: string;
  modelAnswer?: string;
  stub?: boolean;
}

export interface Tips {
  title: string;
  bullets: string[];
}

export interface Transcript {
  transcript: string;
  language?: string | null;
  durationSec?: number;
  model?: string;
  asr?: boolean;
  /** WS06: deterministic audio evidence (server-computed, contract-shaped). */
  features?: AudioFeatures | null;
  /** WS06-02: present when the upload was queued (HTTP 202) instead of done. */
  jobId?: string;
  queued?: boolean;
}

/** WS06-03 contract (snake_case by spec). Uncomputed values stay null. */
export interface AudioFeatures {
  duration_sec: number | null;
  speech_sec: number | null;
  words_per_minute: number | null;
  pause_count: number;
  long_pause_count: number;
  mean_pause_ms: number | null;
  asr_confidence: number | null;
  prosody: null;
  alignment: null;
  quality: { snr: number | null; clipping: boolean; vad: boolean };
}

/** WS06-02: owner-scoped job status (WS07 job record, safe fields only). */
export interface JobStatus {
  id: string;
  type?: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled" | "expired";
  progress?: number;
  errorCode?: string | null;
  errorMessage?: string | null;
  result?: Record<string, unknown> | null;
}

export interface AttemptSummary {
  id: number;
  type: "writing" | "speaking";
  task: string;
  cefr: Cefr | "";
  overall: number | null;
  createdAt: string | null;
}

export interface TrendPoint {
  id: number;
  createdAt: string | null;
  overall: number | null;
  bands: Record<string, number>;
}

export interface Trends {
  writing: TrendPoint[];
  speaking: TrendPoint[];
  reading?: TrendPoint[];
  listening?: TrendPoint[];
}

// Stored attempt detail — superset of WritingEval/SpeakingEval plus meta, so the
// saved feedback re-renders with the existing skill renderers.
export type AttemptDetail = (WritingEval | SpeakingEval) & {
  id: number;
  type: "writing" | "speaking";
  task: string;
  prompt: string;
  body: string;
  createdAt: string | null;
};

// ── Guided lessons (Phase 2d-1) ──────────────────────────────────────────────
export interface LessonExerciseItem {
  prompt: string;
  answer: string;
  distractor?: string;
  feedback?: string;
}
export interface LessonExercise {
  type: string;
  instruction: string;
  items: LessonExerciseItem[];
}
export interface Lesson {
  goal: string;
  skill: Skill;
  warmup?: { instruction: string; duration_minutes?: number };
  teach: { explanation: string; examples: string[] };
  exercises: LessonExercise[];
  produce: { instruction: string; prefill?: string; duration_minutes?: number };
  review: { collocations: string[]; tip: string };
  stub?: boolean;
}
export interface LessonToday {
  day: number;
  focus: Skill;
  skill: Skill;
  band: string;
  lesson: Lesson | null;
}

export interface MockScore {
  id: number;
  listening: number;
  reading: number;
  overall: number;
  createdAt: string | null;
}

export interface PronounceTarget {
  text: string;
  focus?: string;
  tips: string[];
  stub?: boolean;
}
export interface PronounceFeedback {
  summary: string;
  wordTips: { word: string; tip: string }[];
  prosody: string[];
  stub?: boolean;
}

export interface VocabWord {
  word: string;
  pos?: string;
  definition: string;
  example?: string;
  collocations?: string[];
}
export interface VocabSet {
  topic: string;
  band?: string;
  words: VocabWord[];
  stub?: boolean;
}
export interface Flashcard {
  id: number;
  front: string;
  back: string;
  ease: number;
  interval: number;
  reps: number;
  lapses: number;
  due: string | null;
}
export interface CardStats {
  total: number;
  due: number;
}

export interface AccountUser {
  id: number;
  email: string | null;
  name: string;
  goal: string;
  targetBand: number;
  country?: string | null;
  examDate?: string | null;
  bio?: string | null;
  avatar?: string | null;
  skillTargets?: Record<string, string>;
  reminderTime?: string | null;
  reminderTz?: string | null;
  isAdmin?: boolean;
  /** Whether a local password is set (false for Google-only accounts). */
  hasPassword?: boolean;
  /** WS03-05: email ownership verified (Google-verified claims adopt true). */
  emailVerified?: boolean;
  /** Only present on the Google sign-in response: true on first-ever sign-in. */
  isNew?: boolean;
}

export interface AdminUser {
  id: number;
  email: string | null;
  name: string;
  targetBand: number;
  country?: string | null;
  examDate?: string | null;
  attempts: number;
  createdAt?: string | null;
}

export interface AdminStats {
  totalAccounts: number;
  totalProfiles: number;
  anonymousProfiles: number;
  totalAttempts: number;
  totalMocks: number;
  totalCards: number;
}
