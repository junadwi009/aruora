import React, { useState } from "react";
import { Briefcase, GraduationCap, Circle } from "lucide-react";
import { Button, Field, RadioCard, Slider, StepIndicator } from "../ui";
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
    <div className="journey-bg relative flex min-h-full items-center justify-center overflow-hidden p-6">
      {/* Ambient gradient blobs — decorative */}
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          top: 0,
          left: 0,
          width: "20rem",
          height: "20rem",
          background:
            "linear-gradient(135deg, color-mix(in srgb, var(--color-primary-600) 28%, transparent), transparent)",
        }}
      />
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          bottom: 0,
          right: 0,
          width: "20rem",
          height: "20rem",
          background:
            "linear-gradient(135deg, color-mix(in srgb, var(--color-primary-600) 16%, transparent), transparent)",
        }}
      />

      <div
        className="animate-fade-slide-in relative z-10 flex w-full max-w-md flex-col gap-6 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8"
        style={{ boxShadow: "var(--shadow-premium-card)" }}
      >
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
            <div className="rounded-[var(--radius-2xl)] border border-[color-mix(in_srgb,var(--color-primary-600)_25%,transparent)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)] p-6 text-center">
              <div
                className="text-5xl font-bold tabular-nums text-[var(--color-primary-700)]"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {targetBand.toFixed(1)}
              </div>
            </div>
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
            pill
            onClick={back}
            disabled={current === 0 || submitting}
          >
            {t("common.back")}
          </Button>
          <Button pill onClick={next} disabled={!stepValid || submitting} loading={submitting}>
            {isLast ? t("onb.startPlacement") : t("common.next")}
          </Button>
        </div>
      </div>
    </div>
  );
};
