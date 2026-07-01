import React from "react";
import { Check } from "lucide-react";
import { useT } from "../../lib/i18n";

export interface StepIndicatorProps {
  steps: string[];
  current: number;
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({
  steps,
  current,
}) => {
  const { t } = useT();
  return (
    <ol className="flex items-center gap-0" aria-label={t("ui.progressSteps")}>
      {steps.map((step, i) => {
        const done = i < current;
        const active = i === current;
        const isLast = i === steps.length - 1;

        return (
          <li key={i} className="flex items-center">
            {/* Circle */}
            <span className="flex flex-col items-center gap-1">
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
                ]
                  .filter(Boolean)
                  .join(" ")}
                aria-current={active ? "step" : undefined}
              >
                {done ? (
                  <Check size={14} aria-label={t("ui.completed")} />
                ) : (
                  i + 1
                )}
              </span>
              <span
                className={[
                  "text-xs whitespace-nowrap",
                  active
                    ? "font-semibold text-[var(--color-text)]"
                    : done
                    ? "font-medium text-[var(--color-primary-600)]"
                    : "text-[var(--color-muted)]",
                ].join(" ")}
              >
                {step}
              </span>
            </span>

            {/* Connector line */}
            {!isLast && (
              <span
                className={[
                  "h-px w-8 mx-1 mb-5 flex-shrink-0 rounded-full",
                  "transition-colors",
                  done
                    ? "bg-[var(--color-primary-600)]"
                    : "bg-[var(--color-border)]",
                ].join(" ")}
                aria-hidden="true"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
};
