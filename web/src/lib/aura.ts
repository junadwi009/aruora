/**
 * WS23 — Aura voice: approved reusable copy, separated from any future
 * generated freeform responses (23 §Aura voice implementation).
 *
 * Rules every string here must satisfy (enforced by aura.test.ts):
 * - no official-examiner claim, no guaranteed outcome;
 * - no guilt/shame framing, no fabricated user history;
 * - honest about estimates; acknowledges limits instead of inventing facts.
 * The exact evidence must exist before Aura says anything specific.
 *
 * Strings are interpolation-safe: they never embed user data inline. Context
 * is composed by the caller into clearly attributed sentences.
 */

export type AuraMoment =
  | "onboardingComplete"
  | "placementResult"
  | "recommendationExplainer"
  | "meaningfulImprovement"
  | "emptyState"
  | "reminderNote";

export const AURA_COPY: Record<AuraMoment, { en: string; id: string }> = {
  onboardingComplete: {
    en: "Your journey is set. Every session from here moves you toward your target.",
    id: "Perjalananmu sudah disiapkan. Setiap sesi dari sini membawamu mendekati target.",
  },
  placementResult: {
    en: "This is a starting point, not a verdict — a practice estimate to show where you are now.",
    id: "Ini titik awal, bukan vonis — sebuah estimasi latihan untuk menunjukkan posisi sekarang.",
  },
  recommendationExplainer: {
    en: "This session targets the skill where focused practice is most likely to move your estimate.",
    id: "Sesi ini melatih skill yang paling mungkin meningkatkan estimasi dengan latihan fokus.",
  },
  meaningfulImprovement: {
    en: "Real movement since your last attempts — this is what steady practice looks like.",
    id: "Ada kemajuan nyata dari latihanmu sebelumnya — beginilah rasanya latihan yang konsisten.",
  },
  emptyState: {
    en: "Nothing here yet. The first attempt is the hardest one — and it is enough to start.",
    id: "Belum ada apa-apa di sini. Percobaan pertama adalah yang tersulit — dan itu cukup untuk memulai.",
  },
  reminderNote: {
    en: "A short session today keeps your journey moving. Skip it without guilt if life happens.",
    id: "Sesi singkat hari ini menjaga perjalananmu tetap jalan. Lewati saja tanpa rasa bersalah bila ada hal lain.",
  },
};

/** Fragments that must NEVER appear in Aura copy (approved or generated). */
export const AURA_FORBIDDEN_PATTERNS: RegExp[] = [
  /official\s+(score|result|band)/i,
  /guaranteed?/i,
  /examiner/i,
  /certified/i,
  /(you\s+)?will\s+reach/i,
  /you\s+failed/i,
  /lazy/i,
];
