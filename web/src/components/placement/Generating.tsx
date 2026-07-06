import React, { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api/client";
import { useJourney } from "../../lib/journey";
import { ProgressBar } from "../ui/ProgressBar";
import { useT } from "../../lib/i18n";

const STEP_KEYS = [
  "place.genStepReading",
  "place.genStepListening",
  "place.genStepSpeaking",
  "place.genStepWriting",
];

export const Generating: React.FC = () => {
  const { go } = useJourney();
  const { t } = useT();
  const STEPS = STEP_KEYS.map((k) => t(k));
  const [progress, setProgress] = useState(0);
  const [stepIdx, setStepIdx] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;

    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function start() {
      let jobId: string;
      try {
        const res = await api.practiceGenerate();
        if (!mounted.current) return;
        jobId = res.jobId;
      } catch {
        // stay on screen — server might not have this endpoint yet
        return;
      }

      intervalId = setInterval(async () => {
        if (!mounted.current) {
          if (intervalId) clearInterval(intervalId);
          return;
        }
        try {
          const status = await api.practiceStatus(jobId);
          if (!mounted.current) return;
          setProgress(Math.round((status.progress ?? 0) * 100));
          // advance visible step label
          setStepIdx(() => Math.min(STEPS.length - 1, Math.round((status.progress ?? 0) * (STEPS.length - 1))));
          if (status.done) {
            if (intervalId) clearInterval(intervalId);
            go("results");
          }
        } catch {
          if (intervalId) clearInterval(intervalId);
        }
      }, 600);
    }

    start();

    return () => {
      mounted.current = false;
      if (intervalId) clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="journey-bg flex min-h-full flex-col items-center justify-center gap-8 p-6">
      <div className="animate-fade-slide-in w-full max-w-md flex flex-col gap-6">
        {/* Heading */}
        <div className="text-center flex flex-col gap-2">
          <h1 style={{ fontFamily: "var(--font-display)" }} className="text-2xl font-bold text-[var(--color-text)] tracking-tight">
            {t("place.genTitle")}
          </h1>
          <p className="text-sm text-[var(--color-muted)]">
            {t("place.genSubtitle")}
          </p>
        </div>

        {/* Stepped checklist — elevated rows */}
        <ul className="flex flex-col gap-2" role="list">
          {STEPS.map((label, i) => {
            const isDone = i < stepIdx;
            const isActive = i === stepIdx;
            return (
              <li
                key={label}
                className={[
                  "flex items-center gap-3 rounded-[var(--radius-lg)] px-4 py-3",
                  "border transition-[opacity,box-shadow]",
                  isDone
                    ? "bg-[var(--color-surface)] border-[var(--color-border)] opacity-60"
                    : isActive
                    ? "bg-[var(--color-surface)] border-[var(--color-primary-600)] opacity-100"
                    : "bg-[var(--color-surface)] border-[var(--color-border)] opacity-30",
                ].join(" ")}
                style={isActive ? { boxShadow: "var(--shadow-e2)" } : { boxShadow: "var(--shadow-e1)" }}
              >
                {/* Status indicator */}
                {isDone ? (
                  <span
                    className="h-5 w-5 rounded-full flex-shrink-0 flex items-center justify-center"
                    style={{ background: "color-mix(in srgb, var(--color-success) 15%, transparent)" }}
                    aria-hidden="true"
                  >
                    <svg width="10" height="8" viewBox="0 0 10 8" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M1 4L3.5 6.5L9 1" stroke="var(--color-success)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </span>
                ) : isActive ? (
                  <span
                    className="h-5 w-5 rounded-full flex-shrink-0 border-2 border-[var(--color-primary-600)] animate-pulse"
                    style={{ background: "color-mix(in srgb, var(--color-primary-600) 20%, transparent)" }}
                    aria-hidden="true"
                  />
                ) : (
                  <span
                    className="h-5 w-5 rounded-full flex-shrink-0 bg-[var(--color-border)]"
                    aria-hidden="true"
                  />
                )}
                <span className="text-sm font-medium text-[var(--color-text)]">{label}</span>
              </li>
            );
          })}
        </ul>

        {/* Progress bar */}
        <ProgressBar value={progress} max={100} label={t("place.genProgressLabel")} />

        {/* aria-live status for screen readers */}
        <p
          className="text-center text-sm text-[var(--color-muted)] sr-only"
          aria-live="polite"
        >
          {STEPS[stepIdx]}
        </p>
      </div>
    </div>
  );
};
