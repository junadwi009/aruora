import React from "react";
import { Card, Textarea } from "../ui";
import { useT } from "../../lib/i18n";

interface WritingSectionData {
  seconds: number;
  taskType: string;
  targetWords: number;
  prompt: string;
}

export interface WritingSectionProps {
  section: WritingSectionData;
  value: string;
  setValue: (val: string) => void;
}

function countWords(text: string): number {
  return text.trim() === "" ? 0 : text.trim().split(/\s+/).length;
}

export const WritingSection: React.FC<WritingSectionProps> = ({
  section,
  value,
  setValue,
}) => {
  const { t } = useT();
  const wordCount = countWords(value);

  const metTarget = wordCount >= section.targetWords;

  return (
    <div className="flex flex-col gap-5 max-w-2xl">
      {/* Prompt card */}
      <Card className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-widest text-[var(--color-muted)]">
            {section.taskType === "task1" ? t("place.task1") : t("place.task2")}
          </span>
          {/* Word count chip */}
          <span
            className={[
              "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold tabular-nums transition-colors",
              metTarget
                ? "bg-[color-mix(in_srgb,var(--color-success)_15%,transparent)] text-[var(--color-success)]"
                : "bg-[var(--color-surface-2)] text-[var(--color-muted)]",
            ].join(" ")}
          >
            {wordCount} / {section.targetWords} {t("place.words")}
          </span>
        </div>
        <p className="text-sm text-[var(--color-text)] leading-relaxed">
          {section.prompt}
        </p>
      </Card>

      <Textarea
        label={t("place.yourResponse")}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        wordCount={wordCount}
        targetWords={section.targetWords}
        rows={14}
        placeholder={t("place.writeResponsePlaceholder")}
      />
    </div>
  );
};
