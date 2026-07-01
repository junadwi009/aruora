import React from "react";
import { Card, Textarea } from "../ui";
import { Recorder } from "../speaking/Recorder";
import { useT } from "../../lib/i18n";

interface SpeakingPart2Cue {
  cue: string;
}

interface SpeakingSectionData {
  seconds: number;
  part1: string[];
  part2: SpeakingPart2Cue;
  part3: string[];
}

export interface SpeakingSectionProps {
  section: SpeakingSectionData;
  value: string;
  setValue: (val: string) => void;
}

export const SpeakingSection: React.FC<SpeakingSectionProps> = ({
  section,
  value,
  setValue,
}) => {
  const { t } = useT();
  return (
    <div className="flex flex-col gap-7 max-w-2xl">
      {/* Part 1 */}
      {section.part1.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-widest">
            {t("place.speakingPart1")}
          </h2>
          <ol className="flex flex-col gap-2">
            {section.part1.map((q, i) => (
              <li
                key={i}
                className="flex gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-text)] leading-relaxed"
                style={{ boxShadow: "var(--shadow-e1)" }}
              >
                <span className="text-[var(--color-muted)] shrink-0 tabular-nums">{i + 1}.</span>
                <span>{q}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Part 2 */}
      {section.part2?.cue && (
        <div className="flex flex-col gap-3">
          <h2 className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-widest">
            {t("place.speakingPart2")}
          </h2>
          <Card variant="stat" className="text-sm text-[var(--color-text)] leading-relaxed border-l-4 border-l-[var(--color-primary-600)]">
            {section.part2.cue}
          </Card>
        </div>
      )}

      {/* Part 3 */}
      {section.part3.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-widest">
            {t("place.speakingPart3")}
          </h2>
          <ol className="flex flex-col gap-2">
            {section.part3.map((q, i) => (
              <li
                key={i}
                className="flex gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-text)] leading-relaxed"
                style={{ boxShadow: "var(--shadow-e1)" }}
              >
                <span className="text-[var(--color-muted)] shrink-0 tabular-nums">{i + 1}.</span>
                <span>{q}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Record (local ASR) — fills the editable transcript below */}
      <Recorder
        onTranscript={(t) => setValue(value ? `${value} ${t}`.trim() : t)}
      />

      {/* Transcript (recorded above, or typed) — editable */}
      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold text-[var(--color-primary-600)] uppercase tracking-widest">
          {t("place.yourResponseTranscript")}
        </p>
        <Textarea
          label={t("place.speakingTextareaLabel")}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          rows={8}
          placeholder={t("place.speakingTextareaPlaceholder")}
        />
      </div>
    </div>
  );
};
