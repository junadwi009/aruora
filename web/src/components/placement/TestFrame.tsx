import React from "react";
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
    <div className="flex flex-col min-h-full">
      {/* Sticky header — real test-chrome feel */}
      <header
        className="sticky top-0 z-10 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 pt-3 pb-0 flex flex-col gap-2"
        style={{ boxShadow: "var(--shadow-e1)" }}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-base font-semibold text-[var(--color-text)] tracking-tight">
              {sectionName}
            </span>
            <span className="text-sm font-medium text-[var(--color-muted)] tabular-nums">
              {stepIndex} {t("place.ofStep")} {stepCount}
            </span>
          </div>
          <Timer seconds={seconds} onExpire={onTimeUp} running={running} />
        </div>
        {/* Brand-filled progress bar flush to header bottom */}
        <div className="h-1 -mx-4 bg-[var(--color-surface-2)]">
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

      {/* Scrollable body */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        {children}
      </main>

      {/* Sticky footer */}
      <footer
        className="sticky bottom-0 bg-[var(--color-surface)] border-t border-[var(--color-border)] px-4 py-3 flex justify-end"
        style={{ boxShadow: "0 -2px 8px -4px rgba(15,23,42,.08)" }}
      >
        <Button onClick={onNext} size="lg">
          {nextLabel ?? t("common.next")}
        </Button>
      </footer>
    </div>
  );
};
