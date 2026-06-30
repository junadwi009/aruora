import React, { useEffect, useState } from "react";
import { api } from "../../lib/api/client";
import type { SpeakingEval } from "../../lib/types";
import { useView } from "../menu/viewContext";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Textarea } from "../ui/Textarea";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { Badge } from "../ui/Badge";
import { Recorder } from "./Recorder";

const STATIC_QUESTION =
  "Describe a place you have visited that made a strong impression on you. You should say: where it is, when you went there, what you did there, and explain why it made such a strong impression.";

type Phase = "editor" | "loading" | "feedback";

const CRIT_LABELS: Record<string, string> = {
  fluency: "Fluency & Coherence",
  lexicalResource: "Lexical Resource",
  grammaticalRange: "Grammatical Range",
  pronunciation: "Pronunciation",
};

export const Speaking: React.FC = () => {
  const { consumePrefill } = useView();
  const [phase, setPhase] = useState<Phase>("editor");
  const [transcript, setTranscript] = useState("");
  const [question, setQuestion] = useState(STATIC_QUESTION);
  const [result, setResult] = useState<SpeakingEval | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  // A guided lesson's Produce step can hand off a cue-card prompt.
  useEffect(() => {
    const t = consumePrefill("speaking");
    if (t) setQuestion(t);
  }, [consumePrefill]);

  const handleEvaluate = async () => {
    if (!transcript.trim()) return;
    setPhase("loading");
    setApiError(null);
    try {
      const data = await api.speakingEvaluate({
        part: "part2",
        question,
        transcript,
      });
      setResult(data);
      setPhase("feedback");
    } catch (e: unknown) {
      setApiError(e instanceof Error ? e.message : "Evaluation failed");
      setPhase("editor");
    }
  };

  const handleRetry = () => {
    setPhase("editor");
    setResult(null);
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10">
        <h1 className="text-base font-semibold text-[var(--color-text)]">Speaking</h1>
      </div>

      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col gap-4">
        {/* Cue card */}
        <Card>
          <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-1">
            Part 2 — Cue Card
          </p>
          <p className="text-sm text-[var(--color-text)] leading-relaxed">{question}</p>
        </Card>

        {(phase === "editor" || phase === "loading") && (
          <>
            {/* Record your answer — transcribed locally, then editable */}
            <Recorder
              onTranscript={(text) =>
                setTranscript((prev) => (prev ? `${prev} ${text}`.trim() : text))
              }
              disabled={phase === "loading"}
            />

            <Textarea
              label="Your spoken response (transcript)"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              rows={8}
              placeholder="Record above, or type what you would say…"
              disabled={phase === "loading"}
            />
            {apiError && (
              <p className="text-xs text-[var(--color-danger)]">{apiError}</p>
            )}
            <Button
              onClick={handleEvaluate}
              loading={phase === "loading"}
              disabled={transcript.trim().length < 10 || phase === "loading"}
            >
              Evaluate
            </Button>
          </>
        )}

        {phase === "feedback" && result && (
          <SpeakingFeedback result={result} onRetry={handleRetry} />
        )}
      </div>
    </main>
  );
};

// ---------------------------------------------------------------------------
// SpeakingFeedback sub-component
// ---------------------------------------------------------------------------
interface SpeakingFeedbackProps {
  result: SpeakingEval;
  onRetry?: () => void;
}

export const SpeakingFeedback: React.FC<SpeakingFeedbackProps> = ({ result, onRetry }) => (
  <div className="flex flex-col gap-4">
    <Card>
      <div className="flex items-center gap-3 mb-3">
        <LevelChip band={result.cefr as CefrBand} />
        <span className="text-xs text-[var(--color-muted)]">
          CEFR estimate — bands are approximate
        </span>
      </div>

      {Object.keys(result.bands).length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(result.bands).map(([key, val]) => (
            <div key={key} className="flex flex-col">
              <span className="text-xs text-[var(--color-muted)]">
                {CRIT_LABELS[key] ?? key}
              </span>
              <span className="text-sm font-semibold text-[var(--color-text)]">
                {val}
                <Badge tone="neutral" className="ml-1 text-[10px]">estimate</Badge>
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>

    {result.feedback && (
      <Card>
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">
          Feedback
        </p>
        <p className="text-sm text-[var(--color-text)] leading-relaxed">{result.feedback}</p>
      </Card>
    )}

    {result.modelAnswer && (
      <Card>
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">
          Model Answer
        </p>
        <p className="text-sm text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
          {result.modelAnswer}
        </p>
      </Card>
    )}

    {onRetry && (
      <Button variant="secondary" onClick={onRetry}>
        ↩ Try again
      </Button>
    )}
  </div>
);
