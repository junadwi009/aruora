import React, { useState } from "react";
import { Briefcase, GraduationCap, Circle } from "lucide-react";
import { Button, Field, RadioCard, Slider, StepIndicator, Card } from "../ui";
import { api, ApiError } from "../../lib/api/client";
import { useJourney } from "../../lib/journey";
import { useT } from "../../lib/i18n";
import type { Goal } from "../../lib/types";

const STEP_KEYS = ["onb.name", "onb.goal", "onb.target"];

const GOALS: { value: Goal; titleKey: string; descKey: string; icon: React.ReactNode }[] = [
  {
    value: "work",
    titleKey: "onb.goalWork",
    descKey: "onb.goalWorkDesc",
    icon: <Briefcase size={20} />,
  },
  {
    value: "study_abroad",
    titleKey: "onb.goalStudy",
    descKey: "onb.goalStudyDesc",
    icon: <GraduationCap size={20} />,
  },
  {
    value: "other",
    titleKey: "onb.goalOther",
    descKey: "onb.goalOtherDesc",
    icon: <Circle size={20} />,
  },
];

export const Onboarding: React.FC = () => {
  const { go } = useJourney();
  const { t } = useT();
  const STEPS = STEP_KEYS.map((k) => t(k));
  const [current, setCurrent] = useState(0);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState<Goal | null>(null);
  const [targetBand, setTargetBand] = useState(6.0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isLast = current === STEPS.length - 1;

  const stepValid =
    current === 0 ? name.trim().length >= 1 : current === 1 ? goal !== null : true;

  const back = () => {
    setError(null);
    setCurrent((c) => Math.max(0, c - 1));
  };

  const finish = async () => {
    if (!goal) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.onboarding({ name: name.trim(), goal, targetBand });
      go("placement");
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : t("onb.errorGeneric");
      setError(msg);
      setSubmitting(false);
    }
  };

  const next = () => {
    if (!stepValid) return;
    if (isLast) {
      void finish();
      return;
    }
    setError(null);
    setCurrent((c) => Math.min(STEPS.length - 1, c + 1));
  };

  return (
    <div className="journey-bg flex min-h-full items-center justify-center p-6">
      <Card className="animate-fade-slide-in flex w-full max-w-md flex-col gap-6">
        <StepIndicator steps={STEPS} current={current} />

        {current === 0 && (
          <div className="flex flex-col gap-2">
            <h2 style={{ fontFamily: "var(--font-display)" }} className="text-lg font-semibold text-[var(--color-text)] tracking-tight">
              {t("onb.nameHeading")}
            </h2>
            <Field
              label={t("onb.nameLabel")}
              placeholder={t("onb.namePlaceholder")}
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
        )}

        {current === 1 && (
          <div className="flex flex-col gap-2">
            <h2 style={{ fontFamily: "var(--font-display)" }} className="text-lg font-semibold text-[var(--color-text)] tracking-tight">
              {t("onb.goalHeading")}
            </h2>
            <div role="radiogroup" aria-label={t("onb.goal")} className="flex flex-col gap-3">
              {GOALS.map((g) => (
                <RadioCard
                  key={g.value}
                  selected={goal === g.value}
                  onSelect={() => setGoal(g.value)}
                  icon={g.icon}
                  title={t(g.titleKey)}
                  description={t(g.descKey)}
                />
              ))}
            </div>
          </div>
        )}

        {current === 2 && (
          <div className="flex flex-col gap-2">
            <h2 style={{ fontFamily: "var(--font-display)" }} className="text-lg font-semibold text-[var(--color-text)] tracking-tight">
              {t("onb.targetHeading")}
            </h2>
            <Slider
              label={t("onb.targetLabel")}
              min={4.0}
              max={9.0}
              step={0.5}
              value={targetBand}
              onChange={setTargetBand}
            />
          </div>
        )}

        {error && (
          <p role="alert" className="text-sm text-[var(--color-danger)]">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between gap-3">
          <Button
            variant="secondary"
            onClick={back}
            disabled={current === 0 || submitting}
          >
            {t("common.back")}
          </Button>
          <Button onClick={next} disabled={!stepValid || submitting} loading={submitting}>
            {isLast ? t("onb.startPlacement") : t("common.next")}
          </Button>
        </div>
      </Card>
    </div>
  );
};
