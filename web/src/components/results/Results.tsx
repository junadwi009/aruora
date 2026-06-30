import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { useJourney } from "../../lib/journey";
import { useT } from "../../lib/i18n";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { LevelChip } from "../ui/LevelChip";
import { ProgressBar } from "../ui/ProgressBar";
import type { CefrBand } from "../ui/LevelChip";
import type { Skill } from "../../lib/types";

const SKILL_LABELS: Record<Skill, string> = {
  listening: "Listening",
  reading: "Reading",
  writing: "Writing",
  speaking: "Speaking",
};

const SKILLS: Skill[] = ["listening", "reading", "writing", "speaking"];

/** Convert an IELTS band (0-9) to a 0-100 radar value for display */
function bandToRadar(band: number): number {
  return Math.round((band / 9) * 100);
}

export const Results: React.FC = () => {
  const { placementResult, go } = useJourney();
  const { t } = useT();

  if (!placementResult) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-4 p-6">
        <p className="text-[var(--color-muted)]">No results yet.</p>
        <Button variant="secondary" onClick={() => go("placement")}>
          Take placement test
        </Button>
      </div>
    );
  }

  const { perSkill, overallBand, cefr, gapToTarget } = placementResult;

  // Build radar data
  const radarData = SKILLS.map((skill) => {
    const s = perSkill[skill];
    const band = s?.ieltsApprox ?? (s?.ielts ?? 0) ?? 0;
    return { skill: SKILL_LABELS[skill], band, radarValue: bandToRadar(band) };
  });

  // Strengths-first headline line
  const bestSkill = SKILLS.reduce((best, sk) => {
    const bBand = perSkill[best]?.ieltsApprox ?? perSkill[best]?.ielts ?? 0;
    const sBand = perSkill[sk]?.ieltsApprox ?? perSkill[sk]?.ielts ?? 0;
    return (sBand ?? 0) > (bBand ?? 0) ? sk : best;
  }, SKILLS[0]);
  const headline = `Your ${SKILL_LABELS[bestSkill]} is your strongest skill — let's build from here.`;

  return (
    <div className="animate-fade-slide-in flex min-h-full flex-col gap-6 p-6 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          <h1
            className="text-4xl font-bold text-[var(--color-text)] tracking-tight tabular-nums"
            style={{ textWrap: "balance" } as React.CSSProperties}
          >
            Overall Band {overallBand.toFixed(1)}
          </h1>
          <LevelChip band={cefr as CefrBand} />
        </div>
        <p className="text-sm text-[var(--color-muted)]">{headline}</p>
      </div>

      {/* Radar chart */}
      <Card>
        <h2 className="text-xs font-semibold text-[var(--color-muted)] mb-4 uppercase tracking-widest">
          Skill Radar
        </h2>
        {/* Chart — may render at 0×0 in jsdom, that's fine */}
        <div style={{ width: "100%", height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData} outerRadius={90}>
              <PolarGrid />
              <PolarAngleAxis dataKey="skill" />
              <Radar
                name="Band"
                dataKey="radarValue"
                stroke="var(--color-primary-600, #4f46e5)"
                fill="var(--color-primary-600, #4f46e5)"
                fillOpacity={0.25}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* A11y: data-table equivalent, visually accessible below the chart */}
        <table className="w-full text-sm mt-4 border-collapse">
          <caption className="sr-only">Skill band scores</caption>
          <thead>
            <tr>
              <th className="text-left py-1 pr-4 text-[var(--color-muted)] font-medium">Skill</th>
              <th className="text-left py-1 text-[var(--color-muted)] font-medium">Approx. Band</th>
            </tr>
          </thead>
          <tbody>
            {radarData.map(({ skill, band }) => (
              <tr key={skill} className="border-t border-[var(--color-border)]">
                <td className="py-1.5 pr-4 text-[var(--color-text)]">{skill}</td>
                <td className="py-1.5 text-[var(--color-text)] tabular-nums font-semibold">
                  {band > 0 ? band.toFixed(1) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Skill cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {SKILLS.map((skill) => {
          const s = perSkill[skill];
          if (!s) return null;
          const approx = s.ieltsApprox ?? s.ielts ?? 0;
          const isLowConf = s.confidence === "low";
          // Gap to target per-skill — fall back to overall gap
          const gap = gapToTarget;
          // Progress = how far through the gap we are (0 = at bottom, 100 = at target)
          const progressVal = gap > 0 ? Math.max(0, Math.min(100, (1 - gap / 3) * 100)) : 100;

          return (
            <Card key={skill}>
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold text-[var(--color-text)]">
                  {SKILL_LABELS[skill]}
                </span>
                <LevelChip band={s.cefr as CefrBand} />
              </div>
              <p className="text-sm text-[var(--color-muted)] mb-3">
                {approx > 0 ? (
                  <>
                    Approx. IELTS band:{" "}
                    <span className="font-semibold text-[var(--color-text)] tabular-nums">
                      {approx.toFixed(1)}
                    </span>
                  </>
                ) : (
                  "Band not yet estimated"
                )}
              </p>
              <ProgressBar
                value={progressVal}
                max={100}
                label="Gap to target"
              />
              {isLowConf && (
                <p className="text-xs text-[var(--color-muted)] mt-2 opacity-70">
                  Estimate — will refine with practice
                </p>
              )}
            </Card>
          );
        })}
      </div>

      {/* CTA */}
      <div className="flex justify-center pt-2">
        <Button size="lg" onClick={() => go("register")} className="min-w-[14rem]">
          {t("results.saveCta")}
        </Button>
      </div>
    </div>
  );
};

// Default export enables lazy(() => import("./Results")) in App.tsx
export default Results;
