import React from "react";
import { Check } from "lucide-react";
import { useT } from "../../lib/i18n";

export interface StepIndicatorProps {
  steps: string[];
  current: number;
}

/**
 * Responsive step indicator: each step is a fixed-width centred column whose
 * label wraps (never nowrap), and the connectors flex to fill the remaining
 * space — so it always fits its container regardless of label length/language.
 */
export const StepIndicator: React.FC<StepIndicatorProps> = ({ steps, current }) => {
  const { t } = useT();
  return (
    <ol className="flex w-full items-start" aria-label={t("ui.progressSteps")}>
      {steps.map((step, i) => {
        const done = i < current;
        const active = i === current;
        const isLast = i === steps.length - 1;

        return (
          <React.Fragment key={i}>
            {/* Step: circle + wrapping label */}
            <li className="flex w-20 shrink-0 flex-col items-center gap-1 text-center">
              <span
                className={[
                  "inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-semibold",
                  "transition-[background-color,box-shadow,border-color]",
                  done
                    ? "bg-[var(--color-primary-600)] text-white shadow-[var(--shadow-e2)]"
                    : active
                    ? "bg-[var(--color-primary-600)] text-white shadow-[var(--shadow-e3)] " +
                      "ring-4 ring-[var(--color-primary-100)]"
                    : "bg-[var(--color-surface-2)] text-[var(--color-muted)] border border-[var(--color-border)]",
                ].join(" ")}
                aria-current={active ? "step" : undefined}
              >
                {done ? <Check size={14} aria-label={t("ui.completed")} /> : i + 1}
              </span>
              <span
                className={[
                  "text-[11px] leading-tight break-words",
                  active
                    ? "font-semibold text-[var(--color-text)]"
                    : done
                    ? "font-medium text-[var(--color-primary-600)]"
                    : "text-[var(--color-muted)]",
                ].join(" ")}
              >
                {step}
              </span>
            </li>

            {/* Connector line — flexes to absorb remaining width, aligned to the circle */}
            {!isLast && (
              <span
                className={[
                  "mt-4 h-px flex-1 min-w-2 rounded-full transition-colors",
                  done ? "bg-[var(--color-primary-600)]" : "bg-[var(--color-border)]",
                ].join(" ")}
                aria-hidden="true"
              />
            )}
          </React.Fragment>
        );
      })}
    </ol>
  );
};
