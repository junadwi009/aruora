import React from "react";
import { GraduationCap } from "lucide-react";
import { Timer, Button } from "../ui";
import { useT } from "../../lib/i18n";

export interface TestFrameProps {
  sectionName: string;
  stepIndex: number;
  stepCount: number;
  seconds: number;
  onTimeUp: () => void;
  onNext: () => void;
  nextLabel?: string;
  children: React.ReactNode;
  running?: boolean;
}

export const TestFrame: React.FC<TestFrameProps> = ({
  sectionName,
  stepIndex,
  stepCount,
  seconds,
  onTimeUp,
  onNext,
  nextLabel,
  children,
  running = true,
}) => {
  const { t } = useT();
  return (
    <div className="flex flex-col min-h-full bg-[var(--color-bg)]">
      {/* Sticky header — real test-chrome feel */}
      <header
        className="sticky top-0 z-10 flex flex-col gap-3 border-b border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] px-4 pt-3 pb-0 sm:px-6"
        style={{ boxShadow: "var(--shadow-premium)" }}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <span
              aria-hidden="true"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-primary-600)]"
              style={{ background: "color-mix(in srgb, var(--color-primary-600) 12%, transparent)" }}
            >
              <GraduationCap size={18} />
            </span>
            <div className="flex min-w-0 flex-col">
              <span
                className="truncate text-base font-bold tracking-tight text-[var(--color-text)]"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {sectionName}
              </span>
              <span className="text-[11px] font-bold uppercase tracking-wider tabular-nums text-[var(--color-muted)]">
                {stepIndex} {t("place.ofStep")} {stepCount}
              </span>
            </div>
          </div>
          {/* Timer chip — pill with primary tint */}
          <span
            className="inline-flex shrink-0 items-center rounded-full px-3.5 py-1.5"
            style={{ background: "color-mix(in srgb, var(--color-primary-600) 10%, transparent)" }}
          >
            <Timer seconds={seconds} onExpire={onTimeUp} running={running} />
          </span>
        </div>
        {/* Brand-filled progress bar flush to header bottom */}
        <div className="h-1 -mx-4 bg-[var(--color-surface-2)] sm:-mx-6">
          <div
            className="h-full bg-[var(--color-primary-600)] transition-[width] duration-[var(--duration-slow)]"
            style={{ width: `${Math.min(100, Math.round((stepIndex / stepCount) * 100))}%` }}
            role="progressbar"
            aria-valuenow={stepIndex}
            aria-valuemin={0}
            aria-valuemax={stepCount}
            aria-label={`${t("place.section")} ${stepIndex} ${t("place.ofStep")} ${stepCount}`}
          />
        </div>
      </header>

      {/* Scrollable workspace */}
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 md:py-8">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>

      {/* Sticky footer — pill CTA */}
      <footer
        className="sticky bottom-0 flex justify-end border-t border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] px-4 py-3 sm:px-6"
        style={{ boxShadow: "0 -4px 24px -8px rgba(99,102,241,.10)" }}
      >
        <Button onClick={onNext} size="lg" pill>
          {nextLabel ?? t("common.next")}
        </Button>
      </footer>
    </div>
  );
};
