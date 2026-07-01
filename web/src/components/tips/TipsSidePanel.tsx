import React, { useEffect, useState } from "react";
import { Target, GraduationCap } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { useT } from "../../lib/i18n";
import type { Skill } from "../../lib/types";

const SKILLS: Skill[] = ["reading", "listening", "writing", "speaking"];

// Levels top → bottom (strongest first) with the approximate IELTS band range
// (same thresholds the examiner prompts use). Descriptor text is per-skill so the
// learner can self-assess — Reading/Listening cite a rough share of questions,
// Writing/Speaking describe how far they can produce / be understood.
const LEVELS: { cefr: CefrBand; band: string }[] = [
  { cefr: "C2", band: "8.0+" },
  { cefr: "C1", band: "7.0–7.5" },
  { cefr: "B2", band: "6.0–6.5" },
  { cefr: "B1", band: "4.5–5.5" },
  { cefr: "A1A2", band: "≤4.0" },
];

export const TipsSidePanel: React.FC = () => {
  const { t } = useT();
  const [levels, setLevels] = useState<Record<string, CefrBand>>({});
  const [targetBand, setTargetBand] = useState<number | null>(null);
  const [skillTargets, setSkillTargets] = useState<Record<string, string>>({});
  const [skill, setSkill] = useState<Skill>("reading");

  useEffect(() => {
    api.skillLevels()
      .then((rows) => setLevels(Object.fromEntries((rows ?? []).map((r) => [r.skill, r.band as CefrBand]))))
      .catch(() => {});
    api.accountMe()
      .then((u) => { setTargetBand(u.targetBand ?? null); setSkillTargets(u.skillTargets ?? {}); })
      .catch(() => {});
  }, []);

  const hasLevels = Object.keys(levels).length > 0;
  const current = levels[skill];

  return (
    <aside className="w-full min-w-0 flex flex-col gap-4 lg:sticky lg:top-20">
      {/* Your level & target */}
      <Card className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-[var(--color-primary-600)]" />
          <p className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-wide">{t("tips.levelTarget")}</p>
        </div>
        {targetBand != null && (
          <p className="text-sm text-[var(--color-text)]">
            {t("tips.overallTarget")}:{" "}
            <span className="font-semibold tabular-nums">{targetBand.toFixed(1)}</span>
          </p>
        )}
        <ul className="flex flex-col gap-2">
          {SKILLS.map((s) => {
            const cur = levels[s];
            const tgt = skillTargets[s] as CefrBand | undefined;
            return (
              <li key={s} className="flex items-center justify-between gap-2">
                <span className="text-sm text-[var(--color-text)]">{t("nav." + s)}</span>
                <span className="flex items-center gap-1.5">
                  {cur ? <LevelChip band={cur} /> : (
                    <span className="text-xs text-[var(--color-muted)]">{t("home.notAssessed")}</span>
                  )}
                  {tgt && (
                    <>
                      <span className="text-[var(--color-muted)] text-xs" aria-hidden="true">→</span>
                      <LevelChip band={tgt} />
                    </>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
        {!hasLevels && Object.keys(skillTargets).length === 0 && (
          <p className="text-xs text-[var(--color-muted)]">{t("tips.setTargets")}</p>
        )}
      </Card>

      {/* Per-skill self-assessment criteria ladder */}
      <Card className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <GraduationCap size={16} className="text-[var(--color-primary-600)]" />
          <p className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-wide">{t("tips.criteria")}</p>
        </div>

        {/* Skill toggle */}
        <div className="grid grid-cols-4 gap-1" role="tablist" aria-label={t("tips.criteria")}>
          {SKILLS.map((s) => (
            <button
              key={s}
              type="button"
              role="tab"
              aria-selected={skill === s}
              onClick={() => setSkill(s)}
              className={[
                "text-xs font-medium rounded-[var(--radius-sm)] px-1.5 py-1.5 transition-colors",
                skill === s
                  ? "bg-[var(--color-primary-600)] text-white"
                  : "text-[var(--color-muted)] hover:bg-[var(--color-surface-2)]",
              ].join(" ")}
            >
              {t("nav." + s)}
            </button>
          ))}
        </div>

        {/* Ladder */}
        <ul className="flex flex-col gap-1.5">
          {LEVELS.map((lv) => {
            const isCurrent = current === lv.cefr;
            return (
              <li
                key={lv.cefr}
                className={[
                  "rounded-[var(--radius-md)] border p-2.5",
                  isCurrent
                    ? "border-[var(--color-primary-600)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)]"
                    : "border-[var(--color-border)]",
                ].join(" ")}
              >
                <div className="flex items-center gap-2 mb-1">
                  <LevelChip band={lv.cefr} />
                  <span className="text-xs font-semibold text-[var(--color-text)] tabular-nums">{lv.band}</span>
                  {isCurrent && (
                    <span className="ml-auto text-[10px] uppercase tracking-wide font-semibold text-[var(--color-primary-600)] border border-[var(--color-primary-600)] rounded px-1">
                      {t("tips.here")}
                    </span>
                  )}
                </div>
                <p className="text-xs text-[var(--color-muted)] leading-snug">{t(`crit.${skill}.${lv.cefr}`)}</p>
              </li>
            );
          })}
        </ul>
        <p className="text-[11px] text-[var(--color-muted)] opacity-80">{t("tips.criteriaHint")}</p>
      </Card>
    </aside>
  );
};
