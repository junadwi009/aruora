import React from "react";
import { useT } from "../../lib/i18n";

export type QuizStatus = "unanswered" | "answered" | "correct" | "wrong";

export interface QuizNavigatorProps {
  count: number;
  current: number;
  statuses: QuizStatus[];
  onJump: (index: number) => void;
}

const statusClasses: Record<QuizStatus, string> = {
  unanswered: "bg-[var(--color-surface-2)] text-[var(--color-muted)]",
  answered:
    "bg-[var(--color-primary-50)] text-[var(--color-primary-700)]",
  correct:
    "bg-[color-mix(in_srgb,var(--color-success)_15%,transparent)] text-[var(--color-success)]",
  wrong: "bg-[color-mix(in_srgb,var(--color-danger)_15%,transparent)] text-[var(--color-danger)]",
};

export const QuizNavigator: React.FC<QuizNavigatorProps> = ({
  count,
  current,
  statuses,
  onJump,
}) => {
  const { t } = useT();
  const statusLabel: Record<QuizStatus, string> = {
    unanswered: t("quiz.statusUnanswered"),
    answered: t("quiz.statusAnswered"),
    correct: t("quiz.statusCorrect"),
    wrong: t("quiz.statusWrong"),
  };
  return (
    <nav aria-label={t("quiz.navLabel")}>
      <ol className="flex flex-wrap gap-1">
        {Array.from({ length: count }, (_, i) => {
          const status = statuses[i] ?? "unanswered";
          const isCurrent = i === current;

          return (
            <li key={i}>
              <button
                type="button"
                onClick={() => onJump(i)}
                aria-label={`${t("quiz.question")} ${i + 1}, ${statusLabel[status]}`}
                aria-current={isCurrent ? "true" : undefined}
                className={[
                  "min-w-[2.75rem] min-h-11 w-11 h-11 rounded-[var(--radius-md)] text-sm font-medium transition-colors",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
                  statusClasses[status],
                  isCurrent
                    ? "outline outline-2 outline-[var(--color-primary-600)]"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {i + 1}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
