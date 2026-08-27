import React, { useEffect, useState } from "react";
import { BookOpen, Headphones, Mic, PenLine, ArrowRight, MapPin, Target, CalendarDays } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { useView } from "./viewContext";
import { useT } from "../../lib/i18n";
import type { Skill, Milestone } from "../../lib/types";

interface HomeProps {
  levels: Record<string, CefrBand>;
}

// Labels render via t("nav." + skill) below — no static label field needed.
const SKILLS: { skill: Skill; icon: React.ReactNode }[] = [
  { skill: "reading", icon: <BookOpen size={18} aria-hidden="true" /> },
  { skill: "listening", icon: <Headphones size={18} aria-hidden="true" /> },
  { skill: "speaking", icon: <Mic size={18} aria-hidden="true" /> },
  { skill: "writing", icon: <PenLine size={18} aria-hidden="true" /> },
];

const NEXT_BAND: Record<CefrBand, CefrBand> = {
  A1A2: "B1",
  B1: "B2",
  B2: "C1",
  C1: "C2",
  C2: "C2",
};

// WS23 hierarchy: lowest assessed band = the biggest gap (position 5).
const BAND_ORDER: CefrBand[] = ["A1A2", "B1", "B2", "C1", "C2"];

function weakestSkill(levels: Record<string, CefrBand>): Skill | null {
  const assessed = SKILLS
    .filter(({ skill }) => levels[skill])
    .sort((a, b) => BAND_ORDER.indexOf(levels[a.skill]) - BAND_ORDER.indexOf(levels[b.skill]));
  return assessed.length >= 2 ? assessed[0].skill : null;
}

function daysUntil(iso?: string | null): number | null {
  if (!iso) return null;
  const d = new Date(iso + "T00:00:00");
  if (isNaN(d.getTime())) return null;
  const diff = Math.ceil((d.getTime() - Date.now()) / 86_400_000);
  return diff;
}

// Display-font style, applied to headings + the greeting.
const DISPLAY = { fontFamily: "var(--font-display)" } as const;
// Shared surface-card inline style (warm border + soft elevation).
const CARD = { border: "1px solid var(--color-border)", boxShadow: "var(--shadow-e1)" } as const;

export const Home: React.FC<HomeProps> = ({ levels }) => {
  const { setView } = useView();
  const { t } = useT();
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [examDays, setExamDays] = useState<number | null>(null);
  const [streak, setStreak] = useState<{ current: number; today: number } | null>(null);
  const [name, setName] = useState<string>("");
  const [goal, setGoal] = useState<string>("");
  const [targetBand, setTargetBand] = useState<number | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.milestones().then((m) => { if (active) setMilestones(Array.isArray(m) ? m : []); }),
      api.accountMe().then((u) => {
        if (active) {
          setExamDays(daysUntil(u.examDate));
          setName(u.name || "");
          setGoal(u.goal || "");
          setTargetBand(typeof u.targetBand === "number" ? u.targetBand : null);
        }
      }),
      api.statsActivity().then((a) => { if (active) setStreak({ current: a.current, today: a.today }); }),
    ]).finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, []);

  const DAILY_GOAL = 1; // one practice/eval a day keeps the streak alive
  const hour = new Date().getHours();
  const greetKey = hour < 12 ? "home.greetMorning" : hour < 18 ? "home.greetAfternoon" : "home.greetEvening";
  const hasStreak = !!streak && (streak.current > 0 || streak.today > 0);
  // Right rail only exists once there's real streak / exam data to show.
  const showRail = hasStreak || examDays !== null;
  // WS23: mark the weakest assessed skill (biggest gap), never fabricate one.
  const gapSkill = weakestSkill(levels);
  const goalLabel = (g: string): string => {
    if (g === "work") return t("onb.goalWork");
    if (g === "study_abroad") return t("onb.goalStudy");
    return t("onb.goalOther");
  };

  return (
    <main className="flex-1 overflow-y-auto p-4 md:p-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-7">
        {/* Organic banner hero — greeting + the day's single call to action */}
        <section aria-labelledby="today-heading">
          <div
            className="relative overflow-hidden rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_60%,transparent)] p-7 md:p-8"
            style={{
              background:
                "linear-gradient(120deg, color-mix(in srgb, var(--color-warning) 16%, var(--color-surface)) 0%, color-mix(in srgb, var(--color-primary-600) 14%, var(--color-surface)) 100%)",
              boxShadow: "var(--shadow-premium)",
            }}
          >
            <span
              aria-hidden="true"
              className="premium-blob"
              style={{ top: "-3rem", right: "-2rem", width: "16rem", height: "16rem", background: "color-mix(in srgb, var(--color-surface) 60%, transparent)" }}
            />
            <div className="relative z-10 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-primary-700)]">
                  {t("home.today")}
                </p>
                <h1 id="today-heading" className="text-2xl font-bold tracking-tight text-[var(--color-text)] md:text-3xl" style={DISPLAY}>
                  {t(greetKey)}{name ? `, ${name}` : ""}
                </h1>
                <p className="mt-1.5 max-w-md text-sm text-[var(--color-text-2)]">{t("home.todaySub")}</p>
              </div>
              <Button pill size="lg" onClick={() => setView("session")} className="shrink-0 gap-2">
                {t("home.start")}
                <ArrowRight size={18} aria-hidden="true" />
              </Button>
            </div>
          </div>
        </section>

        {/* WS23 journey hierarchy — Destination → Target → Deadline.
            Answers "where am I going, what am I aiming for, by when?" before
            any flow/gamification surface. */}
        <section aria-labelledby="journey-heading">
          <h2 id="journey-heading" className="mb-3 text-lg font-bold text-[var(--color-text)]" style={DISPLAY}>
            {t("home.journey")}
          </h2>
          <Card>
            <ul className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <li className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] text-[var(--color-primary-600)]" aria-hidden="true">
                  <MapPin size={18} />
                </span>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]">{t("home.destination")}</p>
                  <p className="text-sm font-bold text-[var(--color-text)]" style={DISPLAY}>
                    {goal ? goalLabel(goal) : t("home.noDestination")}
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] text-[var(--color-primary-600)]" aria-hidden="true">
                  <Target size={18} />
                </span>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]">{t("home.target")}</p>
                  <p className="text-sm font-bold tabular-nums text-[var(--color-text)]" style={DISPLAY}>
                    {targetBand !== null ? targetBand.toFixed(1) : "—"}
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] text-[var(--color-primary-600)]" aria-hidden="true">
                  <CalendarDays size={18} />
                </span>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]">{t("home.deadline")}</p>
                  <p className="text-sm font-bold tabular-nums text-[var(--color-text)]" style={DISPLAY}>
                    {examDays !== null && examDays > 0 ? `${examDays} ${t("home.daysToGo")}` : "—"}
                  </p>
                </div>
              </li>
            </ul>
            <p className="mt-4 border-t border-[var(--color-border)] pt-3 text-[11px] leading-relaxed text-[var(--color-muted)]">
              {t("home.estimateNote")}
            </p>
          </Card>
        </section>

        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
          {/* Main column — spans full width when there's no right-rail data yet,
              so a fresh account doesn't leave the right third empty. */}
          <div className={`flex flex-col gap-7 ${showRail ? "lg:col-span-8" : "lg:col-span-12"}`}>
            {/* Skill map */}
            <section aria-labelledby="skills-heading">
              <h2 id="skills-heading" className="mb-3 text-lg font-bold text-[var(--color-text)]" style={DISPLAY}>
                {t("home.yourSkills")}
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {SKILLS.map(({ skill, icon }) => {
                  const band = levels[skill];
                  const nextBand = band ? NEXT_BAND[band] : "B1";
                  return (
                    <Card key={skill} variant="interactive" onClick={() => setView(skill)}>
                      <div className="mb-3 flex items-start justify-between">
                        <span
                          className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-lg)] text-[var(--color-primary-600)]"
                          style={{ background: "color-mix(in srgb, var(--color-primary-600) 10%, transparent)" }}
                        >
                          {icon}
                        </span>
                        {skill === gapSkill ? (
                          <span className="rounded-[var(--radius-pill,999px)] bg-[color-mix(in_srgb,var(--color-warning)_14%,transparent)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--color-warning-text)]">
                            {t("home.biggestGap")}
                          </span>
                        ) : band ? (
                          <LevelChip band={band} />
                        ) : null}
                      </div>
                      <p className="text-sm font-bold text-[var(--color-text)]" style={DISPLAY}>{t("nav." + skill)}</p>
                      <p className="mt-0.5 text-xs text-[var(--color-muted)]">
                        {band ? `${t("home.targeting")} ${nextBand}` : t("home.notAssessed")}
                      </p>
                    </Card>
                  );
                })}
              </div>
            </section>

            {/* Program milestones — skeleton while loading, empty-state nudge, or the list */}
            <section aria-labelledby="milestones-heading">
              <h2 id="milestones-heading" className="mb-3 text-lg font-bold text-[var(--color-text)]" style={DISPLAY}>
                {t("home.milestones")}
              </h2>
              {!loaded ? (
                <Card>
                  <div className="flex flex-col gap-3" aria-hidden="true">
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="h-4 rounded bg-[var(--color-surface-2)] animate-pulse" style={{ width: `${80 - i * 14}%` }} />
                    ))}
                  </div>
                </Card>
              ) : milestones.length > 0 ? (
                <Card>
                  <ol className="flex flex-col gap-3">
                    {milestones.map((m) => (
                      <li key={m.idx} className="flex items-center gap-3 text-sm">
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--color-primary-600)_12%,transparent)] text-xs font-bold tabular-nums text-[var(--color-primary-700)]">
                          {m.idx + 1}
                        </span>
                        <span className="flex-1 text-[var(--color-text)]">{m.title}</span>
                        <span className="text-xs tabular-nums text-[var(--color-muted)]">{t("session.day")} {m.dayTarget}</span>
                      </li>
                    ))}
                  </ol>
                </Card>
              ) : (
                <Card>
                  <div className="flex items-center justify-between gap-4">
                    <p className="text-sm text-[var(--color-muted)]">{t("home.milestonesEmpty")}</p>
                    <Button size="sm" pill onClick={() => setView("session")} className="shrink-0">{t("home.start")}</Button>
                  </div>
                </Card>
              )}
            </section>

            {/* Quick links */}
            <section aria-labelledby="quicklinks-heading">
              <h2 id="quicklinks-heading" className="mb-3 text-lg font-bold text-[var(--color-text)]" style={DISPLAY}>
                {t("home.quickAccess")}
              </h2>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" pill size="sm" onClick={() => setView("reading")}>{t("nav.practice")}</Button>
                <Button variant="secondary" pill size="sm" onClick={() => setView("test")}>{t("nav.test")}</Button>
                <Button variant="secondary" pill size="sm" onClick={() => setView("pronounce")}>{t("nav.pronounce")}</Button>
                <Button variant="secondary" pill size="sm" onClick={() => setView("roleplay")}>{t("nav.roleplay")}</Button>
                <Button variant="secondary" pill size="sm" onClick={() => setView("vocab")}>{t("nav.vocab")}</Button>
                <Button variant="secondary" pill size="sm" onClick={() => setView("tips")}>{t("nav.tips")}</Button>
              </div>
            </section>
          </div>

          {/* Right rail — real streak + exam-countdown widgets */}
          {showRail && (
            <aside className="flex flex-col gap-4 lg:col-span-4">
              {hasStreak && (
                <div className="rounded-[var(--radius-2xl)] bg-[var(--color-surface)] p-5" style={CARD}>
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-bold text-[var(--color-text)]" style={DISPLAY}>🔥 {streak!.current}-{t("home.streak")}</p>
                      <p className="mt-0.5 text-xs text-[var(--color-muted)]">
                        {streak!.today >= DAILY_GOAL ? t("home.goalDone") : t("home.goalTodo")}
                      </p>
                    </div>
                    <span className={`text-3xl font-bold tabular-nums ${streak!.today >= DAILY_GOAL ? "text-[var(--color-success)]" : "text-[var(--color-muted)]"}`}>
                      {streak!.today}/{DAILY_GOAL}
                    </span>
                  </div>
                </div>
              )}
              {examDays !== null && (
                <div className="rounded-[var(--radius-2xl)] bg-[var(--color-surface)] p-5" style={CARD}>
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]">{t("home.examCountdown")}</p>
                      <p className="mt-0.5 text-sm text-[var(--color-text)]">
                        {examDays > 0 ? `${examDays} ${t("home.daysToGo")}` : examDays === 0 ? t("home.examToday") : "—"}
                      </p>
                    </div>
                    {examDays > 0 && <span className="text-3xl font-bold tabular-nums text-[var(--color-primary-600)]">{examDays}</span>}
                  </div>
                </div>
              )}
            </aside>
          )}
        </div>
      </div>
    </main>
  );
};
