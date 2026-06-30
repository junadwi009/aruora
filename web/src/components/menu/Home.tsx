import React, { useEffect, useState } from "react";
import { BookOpen, Headphones, Mic, PenLine } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { useView } from "./viewContext";
import type { Skill, Milestone } from "../../lib/types";

interface HomeProps {
  levels: Record<string, CefrBand>;
}

const SKILLS: { skill: Skill; label: string; icon: React.ReactNode }[] = [
  { skill: "reading", label: "Reading", icon: <BookOpen size={18} aria-hidden="true" /> },
  { skill: "listening", label: "Listening", icon: <Headphones size={18} aria-hidden="true" /> },
  { skill: "speaking", label: "Speaking", icon: <Mic size={18} aria-hidden="true" /> },
  { skill: "writing", label: "Writing", icon: <PenLine size={18} aria-hidden="true" /> },
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

export const Home: React.FC<HomeProps> = ({ levels }) => {
  const { setView } = useView();
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [examDays, setExamDays] = useState<number | null>(null);

  useEffect(() => {
    api.milestones().then((m) => setMilestones(Array.isArray(m) ? m : [])).catch(() => {});
    api.accountMe().then((u) => setExamDays(daysUntil(u.examDate))).catch(() => {});
  }, []);

  return (
    <main className="flex-1 overflow-y-auto p-4 md:p-6 max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text)] mb-6">
        Dashboard
      </h1>

      {/* Today hero card — brand-tinted with accent left border */}
      <section aria-labelledby="today-heading" className="mb-6">
        <div
          className="rounded-[var(--radius-xl)] p-5 flex items-center justify-between gap-4"
          style={{
            background: "color-mix(in srgb, var(--color-primary-50) 60%, var(--color-surface))",
            border: "1px solid color-mix(in srgb, var(--color-primary-600) 20%, transparent)",
            borderLeft: "4px solid var(--color-primary-600)",
            boxShadow: "var(--shadow-e2)",
          }}
        >
          <div>
            <h2 id="today-heading" className="text-base font-semibold text-[var(--color-text)] mb-0.5">
              Today
            </h2>
            <p className="text-sm text-[var(--color-muted)]">Start today’s guided session</p>
          </div>
          <Button
            onClick={() => setView("session")}
            className="shrink-0"
          >
            Start
          </Button>
        </div>
      </section>

      {/* Exam countdown */}
      {examDays !== null && (
        <section className="mb-6">
          <div className="rounded-[var(--radius-xl)] px-5 py-4 flex items-center justify-between gap-4"
            style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", boxShadow: "var(--shadow-e1)" }}>
            <div>
              <p className="text-xs text-[var(--color-muted)] uppercase tracking-wide">Exam countdown</p>
              <p className="text-sm text-[var(--color-text)] mt-0.5">
                {examDays > 0 ? `${examDays} day${examDays === 1 ? "" : "s"} to go` : examDays === 0 ? "Exam is today — good luck!" : "Exam date has passed"}
              </p>
            </div>
            {examDays > 0 && <span className="text-3xl font-bold tabular-nums text-[var(--color-primary-600)]">{examDays}</span>}
          </div>
        </section>
      )}

      {/* Skill map — 2×2 elevated interactive cards */}
      <section aria-labelledby="skills-heading" className="mb-6">
        <h2
          id="skills-heading"
          className="text-sm font-semibold text-[var(--color-muted)] mb-3 tracking-tight uppercase"
        >
          Your Skills
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {SKILLS.map(({ skill, label, icon }) => {
            const band = levels[skill];
            const nextBand = band ? NEXT_BAND[band] : "B1";
            return (
              <Card
                key={skill}
                variant="interactive"
                className="cursor-pointer"
                onClick={() => setView(skill)}
              >
                <div className="flex items-start justify-between mb-3">
                  <span
                    className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] text-[var(--color-primary-600)]"
                    style={{ background: "color-mix(in srgb, var(--color-primary-600) 10%, transparent)" }}
                  >
                    {icon}
                  </span>
                  {band && <LevelChip band={band} />}
                </div>
                <p className="text-sm font-semibold text-[var(--color-text)]">{label}</p>
                <p className="text-xs text-[var(--color-muted)] mt-0.5">
                  {band ? `Targeting ${nextBand}` : "Not assessed yet"}
                </p>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Program milestones — real targets from the chosen plan */}
      {milestones.length > 0 && (
        <section aria-labelledby="milestones-heading" className="mb-6">
          <h2
            id="milestones-heading"
            className="text-sm font-semibold text-[var(--color-muted)] mb-3 tracking-tight uppercase"
          >
            Program Milestones
          </h2>
          <Card>
            <ol className="flex flex-col gap-2">
              {milestones.map((m) => (
                <li key={m.idx} className="flex items-center gap-3 text-sm">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-surface-2)] text-xs tabular-nums text-[var(--color-muted)] shrink-0">
                    {m.idx + 1}
                  </span>
                  <span className="flex-1 text-[var(--color-text)]">{m.title}</span>
                  <span className="text-xs text-[var(--color-muted)] tabular-nums">Day {m.dayTarget}</span>
                </li>
              ))}
            </ol>
          </Card>
        </section>
      )}

      {/* Quick links */}
      <section aria-labelledby="quicklinks-heading">
        <h2
          id="quicklinks-heading"
          className="text-sm font-semibold text-[var(--color-muted)] mb-3 tracking-tight uppercase"
        >
          Quick Access
        </h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={() => setView("reading")}>
            Practice
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setView("test")}>
            Test
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setView("pronounce")}>
            Pronounce
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setView("vocab")}>
            Vocab
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setView("tips")}>
            Tips
          </Button>
        </div>
      </section>
    </main>
  );
};
