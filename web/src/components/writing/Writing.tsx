import React, { useEffect, useState } from "react";
import { api } from "../../lib/api/client";
import type { WritingEval, EssayMetrics } from "../../lib/types";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Textarea } from "../ui/Textarea";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { Badge } from "../ui/Badge";
import { useView } from "../menu/viewContext";
import { useT } from "../../lib/i18n";

const STATIC_PROMPT =
  "Some people think that the best way to increase road safety is to increase the minimum legal age for driving cars or riding motorbikes. To what extent do you agree or disagree?";

type Phase = "editor" | "loading" | "feedback";

function countWords(text: string): number {
  return text.trim() === "" ? 0 : text.trim().split(/\s+/).length;
}

export const Writing: React.FC = () => {
  const { consumePrefill } = useView();
  const { t } = useT();
  const [phase, setPhase] = useState<Phase>("editor");
  const [essay, setEssay] = useState("");
  const [result, setResult] = useState<WritingEval | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  // Consume a one-shot prefill handed off from a guided lesson's Produce step.
  useEffect(() => {
    const t = consumePrefill("writing");
    if (t) setEssay((prev) => (prev ? prev : t));
  }, [consumePrefill]);

  const wordCount = countWords(essay);

  const handleEvaluate = async () => {
    if (!essay.trim()) return;
    setPhase("loading");
    setApiError(null);
    try {
      const data = await api.writingEvaluate({
        taskType: "task2",
        prompt: STATIC_PROMPT,
        essay,
      });
      setResult(data);
      setPhase("feedback");
    } catch (e: unknown) {
      setApiError(e instanceof Error ? e.message : t("write.evalFailed"));
      setPhase("editor");
    }
  };

  const handleRevise = () => {
    setPhase("editor");
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10">
        <h1 className="text-base font-semibold text-[var(--color-text)]">{t("nav.writing")}</h1>
      </div>

      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col gap-4">
        {/* Prompt */}
        <Card>
          <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-1">
            {t("write.task2Prompt")}
          </p>
          <p className="text-sm text-[var(--color-text)] leading-relaxed">{STATIC_PROMPT}</p>
        </Card>

        {(phase === "editor" || phase === "loading") && (
          <>
            <Textarea
              label={t("write.yourEssay")}
              value={essay}
              onChange={(e) => setEssay(e.target.value)}
              wordCount={wordCount}
              targetWords={250}
              rows={12}
              placeholder={t("write.essayPlaceholder")}
              disabled={phase === "loading"}
            />
            {apiError && (
              <p className="text-xs text-[var(--color-danger)]">{apiError}</p>
            )}
            <Button
              onClick={handleEvaluate}
              loading={phase === "loading"}
              disabled={wordCount < 10 || phase === "loading"}
            >
              {t("write.evaluate")}
            </Button>
          </>
        )}

        {phase === "feedback" && result && (
          <FeedbackView result={result} onRevise={handleRevise} />
        )}
      </div>
    </main>
  );
};

// ---------------------------------------------------------------------------
// FeedbackView sub-component
// ---------------------------------------------------------------------------
interface FeedbackViewProps {
  result: WritingEval;
  onRevise?: () => void;
}

const CRIT_LABEL_KEYS: Record<string, string> = {
  taskAchievement: "write.crit.taskAchievement",
  coherenceCohesion: "write.crit.coherenceCohesion",
  lexicalResource: "write.crit.lexicalResource",
  grammaticalRange: "write.crit.grammaticalRange",
};

// ---------------------------------------------------------------------------
// MetricsPanel sub-component
// ---------------------------------------------------------------------------
interface StatRowProps {
  label: string;
  value: string | number | null;
}

const StatRow: React.FC<StatRowProps> = ({ label, value }) => {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex items-baseline justify-between gap-2 py-1.5 border-b border-[var(--color-border)] last:border-0">
      <span className="text-xs text-[var(--color-muted)] flex-shrink-0">{label}</span>
      <span className="text-sm font-semibold tabular-nums text-[var(--color-text)] text-right">
        {value}
      </span>
    </div>
  );
};

const MetricsPanel: React.FC<{ metrics: EssayMetrics }> = ({ metrics }) => {
  const { t } = useT();
  const { wordCount, sentenceCount, readability, lexicalDiversity, syntax } = metrics;
  return (
    <Card variant="stat">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">
          {t("write.languageMetrics")}
        </p>
        <Badge tone="neutral" className="text-[10px]">
          {t("write.supporting")}
        </Badge>
      </div>

      <div className="flex flex-col">
        <StatRow label={t("write.metric.wordCount")} value={wordCount} />
        <StatRow label={t("write.metric.sentenceCount")} value={sentenceCount} />
        <StatRow
          label={t("write.metric.fleschKincaid")}
          value={readability.fleschKincaidGrade}
        />
        <StatRow label={t("write.metric.gunningFog")} value={readability.gunningFog} />
        <StatRow
          label={t("write.metric.lexDiversityMtld")}
          value={lexicalDiversity.mtld !== null ? lexicalDiversity.mtld : "—"}
        />
        <StatRow
          label={t("write.metric.lexDiversityTtr")}
          value={lexicalDiversity.ttr}
        />
        {syntax && (
          <>
            <StatRow
              label={t("write.metric.meanSentenceLength")}
              value={syntax.meanSentenceLength}
            />
            <StatRow
              label={t("write.metric.meanDependencyDepth")}
              value={syntax.meanDependencyDepth}
            />
            <StatRow label={t("write.metric.longWords")} value={syntax.nLongWords} />
          </>
        )}
      </div>

      <p className="mt-3 text-[11px] text-[var(--color-muted)] leading-snug">
        {t("write.metricsNote")}
      </p>
    </Card>
  );
};

export const FeedbackView: React.FC<FeedbackViewProps> = ({ result, onRevise }) => {
  const { t } = useT();
  return (
  <div className="flex flex-col gap-4">
    {/* CEFR + band summary */}
    <Card>
      <div className="flex items-center gap-3 mb-3">
        <LevelChip band={result.cefr as CefrBand} />
        <span className="text-xs text-[var(--color-muted)]">
          {t("write.cefrEstimate")}
        </span>
      </div>

      {Object.keys(result.bands).length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(result.bands).map(([key, val]) => (
            <div key={key} className="flex flex-col">
              <span className="text-xs text-[var(--color-muted)]">
                {CRIT_LABEL_KEYS[key] ? t(CRIT_LABEL_KEYS[key]) : key}
              </span>
              <span className="text-sm font-semibold text-[var(--color-text)]">
                {val}
                <Badge tone="neutral" className="ml-1 text-[10px]">{t("common.estimate")}</Badge>
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>

    {/* Corrections */}
    {Array.isArray(result.corrections) && result.corrections.length > 0 && (
      <Card>
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">
          {t("write.corrections")}
        </p>
        <ul className="flex flex-col gap-1 text-sm text-[var(--color-text)]">
          {result.corrections.map((c, i) => (
            <li key={i} className="leading-snug">
              {typeof c === "string" ? c : JSON.stringify(c)}
            </li>
          ))}
        </ul>
      </Card>
    )}

    {/* Model rewrite */}
    {result.rewrite && (
      <Card>
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">
          {t("write.modelRewrite")}
        </p>
        <p className="text-sm text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
          {result.rewrite}
        </p>
      </Card>
    )}

    {/* Metrics panel */}
    {result.metrics && <MetricsPanel metrics={result.metrics} />}

    {onRevise && (
      <Button variant="secondary" onClick={onRevise}>
        ↩ {t("write.revise")}
      </Button>
    )}
  </div>
  );
};
