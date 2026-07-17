import React from "react";
import { useJourney } from "../../lib/journey";
import { Button } from "../ui/Button";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { useT } from "../../lib/i18n";

const SKILL_LABEL_KEYS: Record<string, string> = {
  listening: "nav.listening",
  reading: "nav.reading",
  writing: "nav.writing",
  speaking: "nav.speaking",
};

export const Milestones: React.FC = () => {
  const { milestones, go } = useJourney();
  const { t } = useT();

  if (!milestones || milestones.length === 0) {
    return (
      <div className="flex min-h-full items-center justify-center bg-[var(--color-bg)] p-6">
        <div
          className="flex w-full max-w-md flex-col items-center gap-4 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8 text-center"
          style={{ boxShadow: "var(--shadow-premium-card)" }}
        >
          <p className="text-sm text-[var(--color-muted)]">
            {t("mile.empty")}
          </p>
          <Button variant="secondary" pill onClick={() => go("program")}>
            {t("mile.backToProgram")}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden bg-[var(--color-bg)] p-6">
      {/* Ambient gradient blob — decorative */}
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          bottom: 0,
          right: 0,
          width: "20rem",
          height: "20rem",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--color-primary-600) 22%, transparent), transparent)",
        }}
      />

      <div
        className="animate-fade-slide-in relative z-10 flex w-full max-w-lg flex-col gap-7 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8"
        style={{ boxShadow: "var(--shadow-premium-card)" }}
      >
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 style={{ fontFamily: "var(--font-display)" }} className="text-2xl font-bold text-[var(--color-text)] tracking-tight">
            {t("mile.title")}
          </h1>
          <p className="max-w-sm text-sm text-[var(--color-muted)] leading-relaxed">
            {t("mile.subtitle")}
          </p>
        </div>

        {/* Vertical stepper */}
        <ol className="flex flex-col list-none" role="list">
          {milestones.map((m, stepIdx) => {
            const isLast = stepIdx === milestones.length - 1;
            return (
              <li key={m.idx} className="flex gap-4">
                {/* Left column: node + connecting line */}
                <div className="flex flex-col items-center">
                  {/* Node */}
                  <div
                    className="flex items-center justify-center w-9 h-9 rounded-full shrink-0 border border-[color-mix(in_srgb,var(--color-primary-600)_30%,transparent)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,var(--color-surface))] text-xs font-bold tabular-nums text-[var(--color-primary-700)]"
                    style={{ boxShadow: "var(--shadow-premium)" }}
                  >
                    {m.dayTarget}
                  </div>
                  {/* Connecting line */}
                  {!isLast && (
                    <div className="w-0.5 flex-1 my-1 bg-[var(--color-border)]" />
                  )}
                </div>

                {/* Right column: content */}
                <div className={["flex flex-col gap-2 pb-6 flex-1", isLast ? "pb-0" : ""].join(" ")}>
                  <p className="text-sm font-semibold text-[var(--color-text)] leading-snug">
                    {m.title}
                  </p>
                  {m.targets && Object.keys(m.targets).length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(m.targets).map(([skill, band]) => (
                        <span
                          key={skill}
                          className="inline-flex items-center gap-1.5"
                        >
                          <span className="text-xs text-[var(--color-muted)]">
                            {SKILL_LABEL_KEYS[skill] ? t(SKILL_LABEL_KEYS[skill]) : skill}
                          </span>
                          <LevelChip band={band as CefrBand} />
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        <Button
          size="lg"
          pill
          onClick={() => go("app")}
          className="w-full"
        >
          {t("mile.goToDashboard")}
        </Button>
      </div>
    </div>
  );
};
