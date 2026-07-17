import React, { useState } from "react";
import { QuizNavigator } from "../ui";
import { Play } from "lucide-react";
import { useT } from "../../lib/i18n";
import type { PlacementItem } from "../../lib/types";

interface ListeningClip {
  title: string;
  transcript: string;
}

interface ListeningSectionData {
  seconds: number;
  clips: ListeningClip[];
}

export interface ListeningSectionProps {
  section: ListeningSectionData;
  items: PlacementItem[];
  answers: Record<number, string>;
  setAnswer: (id: number, val: string) => void;
}

export const ListeningSection: React.FC<ListeningSectionProps> = ({
  section,
  items,
  answers,
  setAnswer,
}) => {
  const { t } = useT();
  const [played, setPlayed] = useState<Set<number>>(new Set());
  const [currentQ, setCurrentQ] = useState(0);

  const hasSpeechSynthesis = typeof window !== "undefined" && "speechSynthesis" in window;

  const playClip = (index: number) => {
    if (!hasSpeechSynthesis) return;
    const clip = section.clips[index];
    if (!clip) return;
    const utterance = new SpeechSynthesisUtterance(clip.transcript);
    window.speechSynthesis.speak(utterance);
    setPlayed((prev) => new Set([...prev, index]));
  };

  const statuses = items.map((item) =>
    answers[item.id] !== undefined && answers[item.id] !== ""
      ? ("answered" as const)
      : ("unanswered" as const)
  );

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      {/* Audio clips */}
      <div className="flex flex-col gap-3">
        <h2 className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]">
          {t("place.audioClips")}
        </h2>
        {!hasSpeechSynthesis && (
          <p className="text-sm text-[var(--color-muted)] italic">
            {t("place.noSpeechSynthesis")}
          </p>
        )}
        {section.clips.map((clip, i) => (
          <div
            key={i}
            className="flex items-center gap-4 rounded-[var(--radius-2xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-4"
            style={{ boxShadow: "var(--shadow-premium)" }}
          >
            {/* Styled play button */}
            <button
              type="button"
              onClick={() => playClip(i)}
              disabled={played.has(i) || !hasSpeechSynthesis}
              aria-label={`${t("place.playClip")}: ${clip.title}`}
              className={[
                "inline-flex items-center justify-center w-10 h-10 rounded-full shrink-0 transition-[background-color,box-shadow,transform]",
                "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
                played.has(i) || !hasSpeechSynthesis
                  ? "bg-[var(--color-surface-2)] text-[var(--color-muted)] cursor-not-allowed"
                  : "bg-[var(--color-primary-600)] text-white hover:bg-[var(--color-primary-700)] hover:shadow-[var(--shadow-e2)] active:scale-95",
              ].join(" ")}
            >
              <Play size={16} aria-hidden="true" />
            </button>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-medium text-[var(--color-text)] truncate">{clip.title}</span>
              <span className="text-xs text-[var(--color-muted)]">
                {played.has(i) ? t("place.played") : t("place.tapToPlayOnce")}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Question navigator */}
      {items.length > 0 && (
        <QuizNavigator
          count={items.length}
          current={currentQ}
          statuses={statuses}
          onJump={setCurrentQ}
        />
      )}

      {/* Questions */}
      <div className="flex flex-col gap-4">
        {items.map((item, qi) => {
          const payload = item.payload as { stem: string; options?: string[] };
          const hasOptions = Array.isArray(payload.options) && payload.options.length > 0;

          return (
            <div
              key={item.id}
              id={`q-${qi}`}
              data-qi={qi}
              className="flex flex-col gap-3 rounded-[var(--radius-2xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-5"
              style={{ boxShadow: "var(--shadow-premium)" }}
            >
              <span className="text-[11px] font-bold uppercase tracking-wider tabular-nums text-[var(--color-muted)]">
                {t("place.question")} {qi + 1}
              </span>
              <p className="text-sm font-semibold text-[var(--color-text)] leading-relaxed">
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
                          "flex min-h-11 items-center gap-2.5 cursor-pointer text-sm font-semibold rounded-[var(--radius-lg)] px-3 py-2 border transition-colors",
                          answers[item.id] === opt
                            ? "border-[var(--color-primary-600)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)] text-[var(--color-primary-700)]"
                            : "border-[var(--color-border)] text-[var(--color-text)] hover:border-[var(--color-primary-600)] hover:bg-[var(--color-surface-2)]",
                        ].join(" ")}
                      >
                        <input
                          type="radio"
                          name={`listening-q-${item.id}`}
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
                  className="min-h-11 px-3 py-2 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-2)] text-sm text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
                  placeholder={t("place.yourAnswer")}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
