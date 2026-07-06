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
    <div className="journey-bg flex min-h-full flex-col gap-7 p-6 max-w-lg mx-auto">
      <div className="animate-fade-slide-in flex flex-col gap-2">
        <h1 style={{ fontFamily: "var(--font-display)" }} className="text-2xl font-bold text-[var(--color-text)] tracking-tight leading-tight">
          {t("program.choose")}
        </h1>
        <p className="text-sm text-[var(--color-muted)] leading-relaxed">
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

      <div className="pt-1">
        <Button
          size="lg"
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
