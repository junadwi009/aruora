import React, { useState } from "react";
import { useJourney } from "../../lib/journey";
import { api } from "../../lib/api/client";
import { RadioCard } from "../ui/RadioCard";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { useT } from "../../lib/i18n";

interface PlanOption {
  days: number;
  intensityKey: string;
  noteKey: string;
}

const PLANS: PlanOption[] = [
  {
    days: 30,
    intensityKey: "program.intensity30",
    noteKey: "program.note30",
  },
  {
    days: 90,
    intensityKey: "program.intensity90",
    noteKey: "program.note90",
  },
  {
    days: 180,
    intensityKey: "program.intensity180",
    noteKey: "program.note180",
  },
];

function getRecommended(gap: number): number {
  if (gap <= 0.5) return 30;
  if (gap <= 1.5) return 90;
  return 180;
}

export const Program: React.FC = () => {
  const { go, placementResult, setMilestones } = useJourney();
  const { t } = useT();
  const gap = placementResult?.gapToTarget ?? 1.0;
  const recommended = getRecommended(gap);

  const [selected, setSelected] = useState<number>(recommended);
  const [loading, setLoading] = useState(false);

  async function handleStart() {
    setLoading(true);
    try {
      const res = await api.program(selected);
      setMilestones(res.milestones);
      go("milestones");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden bg-[var(--color-bg)] p-6">
      {/* Ambient gradient blob — decorative */}
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          top: 0,
          left: 0,
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
          <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-primary-700)]">
            {t("program.durationAria")}
          </span>
          <h1 style={{ fontFamily: "var(--font-display)" }} className="text-2xl font-bold text-[var(--color-text)] tracking-tight leading-tight">
            {t("program.choose")}
          </h1>
          <p className="max-w-sm text-sm text-[var(--color-muted)] leading-relaxed">
            {t("program.recommendPre")}{" "}
            <strong className="text-[var(--color-text)]">{recommended}{t("program.dayPlanSuffix")}</strong>{" "}
            {t("program.recommendRest")}
          </p>
        </div>

        <div
          role="radiogroup"
          aria-label={t("program.durationAria")}
          className="flex flex-col gap-3"
        >
          {PLANS.map(({ days, intensityKey, noteKey }) => {
            const isRecommended = days === recommended;
            return (
              <div key={days} className="relative">
                {isRecommended && (
                  <div className="absolute -top-2.5 right-4 z-10">
                    <Badge tone="success">{t("program.recommended")}</Badge>
                  </div>
                )}
                <div
                  className={isRecommended && selected !== days
                    ? "ring-2 ring-[var(--color-accent-500)] ring-offset-2 rounded-[var(--radius-lg)]"
                    : ""}
                >
                  <RadioCard
                    selected={selected === days}
                    onSelect={() => setSelected(days)}
                    title={`${days}${t("program.dayPlanSuffix")}`}
                    description={`${t(intensityKey)} · ${t(noteKey)}`}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <Button
          size="lg"
          pill
          loading={loading}
          onClick={handleStart}
          className="w-full"
        >
          {t("program.start")} {selected}{t("program.dayPlanSuffix")}
        </Button>
      </div>
    </div>
  );
};
