import React, { useEffect, useState } from "react";
import { Target, GraduationCap } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { useT } from "../../lib/i18n";
import type { Skill } from "../../lib/types";

const SKILLS: Skill[] = ["reading", "listening", "writing", "speaking"];

// Approximate IELTS band → CEFR mapping (same thresholds the examiner prompts use).
const BAND_REF: { band: string; cefr: CefrBand; descKey: string }[] = [
  { band: "8.0+", cefr: "C2", descKey: "tips.descC2" },
  { band: "7.0–7.5", cefr: "C1", descKey: "tips.descC1" },
  { band: "6.0–6.5", cefr: "B2", descKey: "tips.descB2" },
  { band: "4.5–5.5", cefr: "B1", descKey: "tips.descB1" },
  { band: "≤4.0", cefr: "A1A2", descKey: "tips.descA" },
];

/**
 * Right-hand reference rail on the Tips page (fills the empty space on wide
 * screens): the learner's current level + target per skill, and a Band→CEFR
 * reference. Personalized cards are hidden gracefully when offline/anonymous;
 * the static Band→CEFR card always renders.
 */
export const TipsSidePanel: React.FC = () => {
  const { t } = useT();
  const [levels, setLevels] = useState<Record<string, CefrBand>>({});
  const [targetBand, setTargetBand] = useState<number | null>(null);
  const [skillTargets, setSkillTargets] = useState<Record<string, string>>({});

  useEffect(() => {
    api.skillLevels()
      .then((rows) => setLevels(Object.fromEntries((rows ?? []).map((r) => [r.skill, r.band as CefrBand]))))
      .catch(() => {});
    api.accountMe()
      .then((u) => { setTargetBand(u.targetBand ?? null); setSkillTargets(u.skillTargets ?? {}); })
      .catch(() => {});
  }, []);

  const hasLevels = Object.keys(levels).length > 0;

  return (
    <aside className="w-full xl:w-80 xl:shrink-0 flex flex-col gap-4 xl:sticky xl:top-20">
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

      {/* Band → CEFR reference */}
      <Card className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <GraduationCap size={16} className="text-[var(--color-primary-600)]" />
          <p className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-wide">{t("tips.bandRef")}</p>
        </div>
        <ul className="flex flex-col gap-2.5">
          {BAND_REF.map((r) => (
            <li key={r.cefr} className="flex items-start gap-3">
              <span className="w-14 shrink-0 text-sm font-semibold text-[var(--color-text)] tabular-nums">{r.band}</span>
              <LevelChip band={r.cefr} />
              <span className="text-xs text-[var(--color-muted)] leading-snug">{t(r.descKey)}</span>
            </li>
          ))}
        </ul>
        <p className="text-[11px] text-[var(--color-muted)] opacity-80">{t("tips.bandRefHint")}</p>
      </Card>
    </aside>
  );
};
