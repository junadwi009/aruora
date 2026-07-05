import React, { useEffect, useState } from "react";
import { BookOpen, Headphones, Mic, PenLine } from "lucide-react";
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
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.milestones().then((m) => { if (active) setMilestones(Array.isArray(m) ? m : []); }),
      api.accountMe().then((u) => { if (active) { setExamDays(daysUntil(u.examDate)); setName(u.name || ""); } }),
      api.statsActivity().then((a) => { if (active) setStreak({ current: a.current, today: a.today }); }),
    ]).finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, []);

  const DAILY_GOAL = 1; // one practice/eval a day keeps the streak alive
  const hour = new Date().getHours();
  const greetKey = hour < 12 ? "home.greetMorning" : hour < 18 ? "home.greetAfternoon" : "home.greetEvening";
  const hasStreak = !!streak && (streak.current > 0 || streak.today > 0);

  return (
    <main className="flex-1 overflow-y-auto p-4 md:p-8 max-w-2xl">
      {/* Greeting — personal, time-aware, in the display face */}
      <header className="mb-7 md:mb-8">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-[var(--color-text)]" style={DISPLAY}>
          {t(greetKey)}{name ? `, ${name}` : ""}
        </h1>
        <p className="text-sm text-[var(--color-muted)] mt-1.5">{t("home.greetSub")}</p>
      </header>

      {/* Today hero — the day's single call to action */}
      <section aria-labelledby="today-heading" className="mb-6">
        <div
          className="rounded-[var(--radius-xl)] p-6 flex items-center justify-between gap-4 bg-[var(--color-surface)]"
          style={{ border: "1px solid var(--color-border)", boxShadow: "var(--shadow-e2)" }}
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-primary-700)] mb-1.5">
              {t("home.today")}
            </p>
            <h2 id="today-heading" className="text-lg font-semibold text-[var(--color-text)]" style={DISPLAY}>
              {t("home.todaySub")}
            </h2>
          </div>
          <Button onClick={() => setView("session")} className="shrink-0">
            {t("home.start")}
          </Button>
        </div>
      </section>

      {/* Stat row — streak + exam countdown side by side */}
      {(hasStreak || examDays !== null) && (
        <section className="mb-6 flex flex-col sm:flex-row gap-3">
          {hasStreak && (
            <div className="flex-1 rounded-[var(--radius-xl)] px-5 py-4 flex items-center justify-between gap-4 bg-[var(--color-surface)]" style={CARD}>
              <div>
                <p className="text-sm font-semibold text-[var(--color-text)]">🔥 {streak!.current}-{t("home.streak")}</p>
                <p className="text-xs text-[var(--color-muted)] mt-0.5">
                  {streak!.today >= DAILY_GOAL ? t("home.goalDone") : t("home.goalTodo")}
                </p>
              </div>
              <span className={`text-3xl font-bold tabular-nums ${streak!.today >= DAILY_GOAL ? "text-[var(--color-success)]" : "text-[var(--color-muted)]"}`}>
                {streak!.today}/{DAILY_GOAL}
              </span>
            </div>
          )}
          {examDays !== null && (
            <div className="flex-1 rounded-[var(--radius-xl)] px-5 py-4 flex items-center justify-between gap-4 bg-[var(--color-surface)]" style={CARD}>
              <div>
                <p className="text-xs text-[var(--color-muted)] uppercase tracking-wider">{t("home.examCountdown")}</p>
                <p className="text-sm text-[var(--color-text)] mt-0.5">
                  {examDays > 0 ? `${examDays} ${t("home.daysToGo")}` : examDays === 0 ? t("home.examToday") : "—"}
                </p>
              </div>
              {examDays > 0 && <span className="text-3xl font-bold tabular-nums text-[var(--color-primary-600)]">{examDays}</span>}
            </div>
          )}
        </section>
      )}

      {/* Skill map */}
      <section aria-labelledby="skills-heading" className="mb-7">
        <h2 id="skills-heading" className="text-base font-semibold text-[var(--color-text)] mb-3" style={DISPLAY}>
          {t("home.yourSkills")}
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {SKILLS.map(({ skill, icon }) => {
            const band = levels[skill];
            const nextBand = band ? NEXT_BAND[band] : "B1";
            return (
              <Card key={skill} variant="interactive" onClick={() => setView(skill)}>
                <div className="flex items-start justify-between mb-3">
                  <span
                    className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] text-[var(--color-primary-600)]"
                    style={{ background: "color-mix(in srgb, var(--color-primary-600) 10%, transparent)" }}
                  >
                    {icon}
                  </span>
                  {band && <LevelChip band={band} />}
                </div>
                <p className="text-sm font-semibold text-[var(--color-text)]">{t("nav." + skill)}</p>
                <p className="text-xs text-[var(--color-muted)] mt-0.5">
                  {band ? `${t("home.targeting")} ${nextBand}` : t("home.notAssessed")}
                </p>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Program milestones — skeleton while loading, empty-state nudge, or the list */}
      <section aria-labelledby="milestones-heading" className="mb-7">
        <h2 id="milestones-heading" className="text-base font-semibold text-[var(--color-text)] mb-3" style={DISPLAY}>
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
            <ol className="flex flex-col gap-2">
              {milestones.map((m) => (
                <li key={m.idx} className="flex items-center gap-3 text-sm">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-surface-2)] text-xs tabular-nums text-[var(--color-muted)] shrink-0">
                    {m.idx + 1}
                  </span>
                  <span className="flex-1 text-[var(--color-text)]">{m.title}</span>
                  <span className="text-xs text-[var(--color-muted)] tabular-nums">{t("session.day")} {m.dayTarget}</span>
                </li>
              ))}
            </ol>
          </Card>
        ) : (
          <Card>
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm text-[var(--color-muted)]">{t("home.milestonesEmpty")}</p>
              <Button size="sm" onClick={() => setView("session")} className="shrink-0">{t("home.start")}</Button>
            </div>
          </Card>
        )}
      </section>

      {/* Quick links */}
      <section aria-labelledby="quicklinks-heading">
        <h2 id="quicklinks-heading" className="text-base font-semibold text-[var(--color-text)] mb-3" style={DISPLAY}>
          {t("home.quickAccess")}
        </h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={() => setView("reading")}>{t("nav.practice")}</Button>
          <Button variant="secondary" size="sm" onClick={() => setView("test")}>{t("nav.test")}</Button>
          <Button variant="secondary" size="sm" onClick={() => setView("pronounce")}>{t("nav.pronounce")}</Button>
          <Button variant="secondary" size="sm" onClick={() => setView("roleplay")}>{t("nav.roleplay")}</Button>
          <Button variant="secondary" size="sm" onClick={() => setView("vocab")}>{t("nav.vocab")}</Button>
          <Button variant="secondary" size="sm" onClick={() => setView("tips")}>{t("nav.tips")}</Button>
        </div>
      </section>
    </main>
  );
};
