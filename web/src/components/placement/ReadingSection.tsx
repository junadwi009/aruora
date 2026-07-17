import React, { useState } from "react";
import { QuizNavigator } from "../ui";
import { useT } from "../../lib/i18n";
import type { PlacementItem } from "../../lib/types";

interface ReadingSectionData {
  seconds: number;
  title: string;
  passage: string;
}

export interface ReadingSectionProps {
  section: ReadingSectionData;
  items: PlacementItem[];
  answers: Record<number, string>;
  setAnswer: (id: number, val: string) => void;
}

export const ReadingSection: React.FC<ReadingSectionProps> = ({
  section,
  items,
  answers,
  setAnswer,
}) => {
  const { t } = useT();
  const [currentQ, setCurrentQ] = useState(0);

  const statuses = items.map((item) =>
    answers[item.id] !== undefined && answers[item.id] !== ""
      ? ("answered" as const)
      : ("unanswered" as const)
  );

  return (
    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12 lg:gap-8">
      {/* Left pane: passage — Lexend 18px / lh 1.7 / ~66ch */}
      <div
        className="flex flex-col gap-4 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-6 md:p-8 lg:col-span-7 lg:max-h-[560px] lg:overflow-y-auto"
        style={{ boxShadow: "var(--shadow-premium)" }}
      >
        <span className="w-fit rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-[var(--color-primary-700)]" style={{ background: "color-mix(in srgb, var(--color-primary-600) 10%, transparent)" }}>
          {t("place.readingPassage")}
        </span>
        <h2
          className="text-2xl font-bold tracking-tight text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {section.title}
        </h2>
        <div
          aria-label={t("place.readingPassage")}
          className="max-w-[66ch] text-[18px] leading-[1.7] text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-reading)" }}
        >
          {section.passage.split("\n").map((para, i) => (
            <p key={i} className="mb-4">
              {para}
            </p>
          ))}
        </div>
      </div>

      {/* Right pane: questions */}
      <div className="flex flex-col gap-4 lg:col-span-5">
        <h2 className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]">
          {t("place.questions")}
        </h2>

        {items.length > 0 && (
          <QuizNavigator
            count={items.length}
            current={currentQ}
            statuses={statuses}
            onJump={setCurrentQ}
          />
        )}

        <div className="flex flex-col gap-4">
          {items.map((item, qi) => {
            const payload = item.payload as { stem: string; options?: string[] };
            const hasOptions = Array.isArray(payload.options) && payload.options.length > 0;

            return (
              <div
                key={item.id}
                id={`rq-${qi}`}
                data-qi={qi}
                className="flex flex-col gap-3 rounded-[var(--radius-2xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-5"
                style={{ boxShadow: "var(--shadow-premium)" }}
              >
                <span className="text-[11px] font-bold uppercase tracking-wider tabular-nums text-[var(--color-muted)]">
                  {t("place.question")} {qi + 1}
                </span>
                <p className="text-sm font-semibold leading-relaxed text-[var(--color-text)]">
                  {payload.stem}
                </p>

                {hasOptions ? (
                  <fieldset>
                    <legend className="sr-only">{t("place.question")} {qi + 1}</legend>
                    <div className="flex flex-col gap-2">
                      {payload.options!.map((opt) => (
                        <label
                          key={opt}
                          className={[
                            "flex min-h-11 cursor-pointer items-center gap-2.5 rounded-[var(--radius-lg)] border px-3 py-2 text-sm font-semibold transition-colors",
                            answers[item.id] === opt
                              ? "border-[var(--color-primary-600)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)] text-[var(--color-primary-700)]"
                              : "border-[var(--color-border)] text-[var(--color-text)] hover:border-[var(--color-primary-600)] hover:bg-[var(--color-surface-2)]",
                          ].join(" ")}
                        >
                          <input
                            type="radio"
                            name={`reading-q-${item.id}`}
                            value={opt}
                            checked={answers[item.id] === opt}
                            onChange={() => {
                              setAnswer(item.id, opt);
                              setCurrentQ(qi);
                            }}
                            className="sr-only"
                          />
                          {opt}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                ) : (
                  <input
                    type="text"
                    aria-label={`${t("place.answerForQuestion")} ${qi + 1}`}
                    value={answers[item.id] ?? ""}
                    onChange={(e) => {
                      setAnswer(item.id, e.target.value);
                      setCurrentQ(qi);
                    }}
                    className="min-h-11 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
                    placeholder={t("place.yourAnswer")}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
