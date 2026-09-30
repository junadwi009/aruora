/** UI policy only. The server remains the source of scoring and authorization. */
export const SKILLS = ["listening", "reading", "writing", "speaking"] as const;
export type Skill = (typeof SKILLS)[number];
export type Locale = "en" | "id";
export type ExperiencePage = "home" | "journey" | "practice" | "progress" | "test" | "tips" | "settings" | "session" | Skill | "pronounce" | "vocab" | "roleplay";
export interface SkillEvidence {
  estimate: number | null;
  target: number;
  gap: number | null;
  assessed: boolean;
  confidence?: string;
}
export interface Readiness {
  method: string;
  generatedAt: string | null;
  targetBand: number;
  currentEstimate: number | null;
  perSkill: Record<Skill, SkillEvidence>;
  evidenceCoverage: { assessed: number; total: 4; complete: boolean; missing: Skill[] };
}
export interface Profile {
  id: number;
  name: string;
  goal: string;
  targetBand: number;
  examDate?: string | null;
  emailVerified?: boolean;
  /** Transient account-creation hint; not an authorization claim. */
  isNew?: boolean;
}
export interface Checkpoint { id?: number; idx: number; dayTarget: number; title: string; targets: Record<string, string> }
export interface Activity { current: number; longest: number; today: number; daysActive: number }
export type LoadState = "loading" | "ready" | "error";
export interface DashboardData {
  profile: Profile;
  readiness: Readiness | null;
  readinessState: LoadState;
  milestones: Checkpoint[];
  milestonesState: LoadState;
  activity: Activity | null;
  activityState: LoadState;
}
export const isSkill = (v: unknown): v is Skill => typeof v === "string" && (SKILLS as readonly string[]).includes(v);
export function band(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 9 ? v : null;
}
function object(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error("INVALID_READINESS_CONTRACT");
  return v as Record<string, unknown>;
}
/** Fail visibly on malformed API data, rather than turning outages into zero scores. */
export function parseReadiness(input: unknown): Readiness {
  const r = object(input), skills = object(r.perSkill);
  const target = band(r.targetBand);
  if (target === null || (typeof r.method !== "string" || !r.method.trim())) throw new Error("INVALID_READINESS_CONTRACT");
  const rows = {} as Record<Skill, SkillEvidence>;
  for (const s of SKILLS) {
    const row = object(skills[s]);
    const t = band(row.target);
    if (t === null || typeof row.assessed !== "boolean") throw new Error("INVALID_READINESS_CONTRACT");
    const value = row.estimate === null ? null : band(row.estimate);
    if (row.assessed && value === null) throw new Error("INVALID_READINESS_CONTRACT");
    if (!row.assessed && row.estimate !== null) throw new Error("INVALID_READINESS_CONTRACT");
    rows[s] = { estimate: value, target: t, gap: value === null ? null : Math.round((t - value) * 100) / 100, assessed: row.assessed };
  }
  const missing = SKILLS.filter(s => !rows[s].assessed);
  const avg = r.currentEstimate === null ? null : band(r.currentEstimate);
  if (r.currentEstimate !== null && avg === null) throw new Error("INVALID_READINESS_CONTRACT");
  if ((missing.length < 4 && avg === null) || (missing.length === 4 && avg !== null)) throw new Error("INVALID_READINESS_CONTRACT");
  // Coverage is verified against the individual rows. It is not a readiness percentage.
  return { method: r.method, generatedAt: typeof r.generatedAt === "string" && !Number.isNaN(Date.parse(r.generatedAt)) ? r.generatedAt : null,
    targetBand: target, currentEstimate: avg, perSkill: rows,
    evidenceCoverage: { assessed: 4 - missing.length, total: 4, complete: missing.length === 0, missing } };
}
export interface Recommendation { kind: "setup" | "assessment" | "evidence" | "gap" | "review" | "unavailable"; skill?: Skill; path: string; gap?: number }
/** Missing evidence first; then an actual positive target gap; never a CEFR guess. */
export function recommend(data: DashboardData): Recommendation {
  if (data.profile.isNew || !data.profile.name.trim() || !data.profile.goal) return { kind: "setup", path: "/onboarding" };
  if (data.readinessState !== "ready" || !data.readiness) return { kind: "unavailable", path: "/app/practice" };
  const r = data.readiness;
  if (r.evidenceCoverage.assessed === 0) return { kind: "assessment", path: "/placement" };
  const missingProductive = r.evidenceCoverage.missing.filter(s => s === "writing" || s === "speaking");
  if (missingProductive.length) {
    const skill = missingProductive[0];
    return {kind:"evidence",skill,path:`/app/${skill}`};
  }
  // Short objective practice records accuracy, not calibrated IELTS bands.
  // Missing L/R estimates must not trap the learner in an unresolvable loop.
  const ranked = SKILLS.filter(s => (r.perSkill[s].gap ?? 0) > 0).sort((a,b) => (r.perSkill[b].gap ?? 0) - (r.perSkill[a].gap ?? 0));
  if (!ranked.length) return { kind: "review", path: "/app/progress" };
  const skill = ranked[0];
  return { kind: "gap", skill, path: `/app/${skill}`, gap: r.perSkill[skill].gap! };
}
export function formatBand(v: number | null | undefined): string { return band(v) === null ? "—" : (v as number).toFixed(1); }
/** Legacy examDate can be a month normalized to day 1. Never manufacture an exact countdown. */
export function examMonth(value: string | null | undefined, lang: Locale): string | null {
  const m = /^(\d{4})-(\d{2})(?:-\d{2})?$/.exec(value ?? "");
  if (!m || Number(m[2]) < 1 || Number(m[2]) > 12 || Number(m[1]) < 1900 || Number(m[1]) > 2200) return null;
  return new Intl.DateTimeFormat(lang === "id" ? "id-ID" : "en-GB", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, 1)));
}
export function profileGoal(goal: string, lang: Locale): string {
  const labels: Record<string, [string,string]> = { work: ["Career goals", "Tujuan karier"], study_abroad: ["Study & scholarships", "Studi & beasiswa"], other: ["Personal learning goal", "Tujuan belajar pribadi"] };
  return labels[goal]?.[lang === "id" ? 1 : 0] ?? (lang === "id" ? "Tetapkan tujuanmu" : "Set your goal");
}
export function errorMessage(error: unknown, lang: Locale): string {
  const code = error && typeof error === "object" && "code" in error ? String(error.code) : "";
  if (code === "RATE_LIMITED") return lang === "id" ? "Terlalu banyak permintaan. Tunggu sebentar, lalu coba lagi." : "Too many requests. Wait a moment, then try again.";
  if (code === "EMAIL_UNVERIFIED") return lang === "id" ? "Verifikasi email sebelum menggunakan fitur ini." : "Verify your email before using this feature.";
  if (code === "UNAUTHORIZED" || code === "SESSION_EXPIRED") return lang === "id" ? "Sesi tidak tersedia. Silakan masuk kembali." : "Your session is unavailable. Please sign in again.";
  return lang === "id" ? "Data belum dapat dimuat. Data yang tidak tersedia tidak dihitung sebagai skor nol." : "We couldn't load this information. Missing data is not treated as a zero score.";
}
