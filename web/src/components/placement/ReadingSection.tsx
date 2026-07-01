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
    <div className="md:grid md:grid-cols-2 md:gap-8 flex flex-col gap-6">
      {/* Left pane: passage — Lexend 18px / lh 1.7 / ~66ch */}
      <div className="flex flex-col gap-4">
        <h2 className="text-base font-semibold text-[var(--color-text)] tracking-tight">
          {section.title}
        </h2>
        <div
          aria-label={t("place.readingPassage")}
          className="text-[18px] leading-[1.7] max-w-[66ch] text-[var(--color-text)]"
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
      <div className="flex flex-col gap-4">
        <h2 className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-widest">
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
                className="flex flex-col gap-3 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
                style={{ boxShadow: "var(--shadow-e1)" }}
              >
                <p className="text-sm font-medium text-[var(--color-text)] leading-relaxed">
                  <span className="text-[var(--color-muted)] mr-2 tabular-nums">{qi + 1}.</span>
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
                            "flex items-center gap-2.5 cursor-pointer text-sm rounded-[var(--radius-md)] px-3 py-2 border transition-colors",
                            answers[item.id] === opt
                              ? "border-[var(--color-primary-600)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)] text-[var(--color-primary-700)]"
                              : "border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-2)]",
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
                    className="min-h-11 px-3 py-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
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
