import React, { useEffect, useRef, useState } from "react";
import { BookOpen, Headphones } from "lucide-react";
import { api, ApiError } from "../../lib/api/client";
import { bandFromPct } from "../../lib/band";
import type { QuizQuestion, QuizSet } from "../../lib/types";
import type { CefrBand } from "../ui/LevelChip";
import { LevelChip } from "../ui/LevelChip";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { QuizNavigator } from "../ui/QuizNavigator";
import type { QuizStatus } from "../ui/QuizNavigator";
import { useT } from "../../lib/i18n";

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function norm(s: string): string {
  return s.toLowerCase().trim().replace(/\s+/g, " ");
}

const NEXT_BAND: Record<CefrBand, CefrBand> = {
  A1A2: "B1",
  B1: "B2",
  B2: "C1",
  C1: "C2",
  C2: "C2",
};

export interface QuizRunnerProps {
  skill: string;
  band?: CefrBand;
  mode: "reading" | "listening";
}

// ---------------------------------------------------------------------------
// component
// ---------------------------------------------------------------------------
export const QuizRunner: React.FC<QuizRunnerProps> = ({ skill, band, mode }) => {
  const { t } = useT();
  const [set, setSet] = useState<QuizSet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // answers: indexed by question index, value = user's answer string
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);

  // listening TTS state
  const [speaking, setSpeaking] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  // current question index (for navigator scroll target)
  const [current, setCurrent] = useState(0);

  const questionRefs = useRef<(HTMLDivElement | null)[]>([]);

  const load = () => {
    setLoading(true);
    setError(null);
    setAnswers({});
    setSubmitted(false);
    setSpeaking(false);
    setShowTranscript(false);
    setCurrent(0);
    api
      .practiceSet(skill, band)
      .then((data) => {
        setSet(data);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.code === "GEN_CAP_REACHED") {
          setError(t("gen.capReached"));
        } else {
          setError(e instanceof Error ? e.message : t("quiz.loadError"));
        }
        setLoading(false);
      });
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [skill, band]);

  // ---- TTS ----
  const handlePlay = () => {
    if (!set?.transcript) return;
    if (!window.speechSynthesis) {
      alert(t("quiz.ttsUnavailableAlert"));
      return;
    }
    const utt = new SpeechSynthesisUtterance(set.transcript);
    utt.onstart = () => setSpeaking(true);
    utt.onend = () => setSpeaking(false);
    utt.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utt);
  };

  // ---- grading ----
  const handleSubmit = () => {
    if (!set) return;
    setSubmitted(true);
    if (mode === "listening") setShowTranscript(true);
    // Persist the score so it shows in Progress trends (fire-and-forget).
    const total = set.questions.length;
    if (total > 0) {
      const correct = correctCount();
      const band = bandFromPct(Math.round((correct / total) * 100));
      api.practiceAttempt({ skill: mode, band, correct, total }).catch(() => {});
    }
  };

  const getStatus = (qi: number): QuizStatus => {
    if (!submitted) return answers[qi] !== undefined ? "answered" : "unanswered";
    const q = set!.questions[qi];
    return norm(answers[qi] ?? "") === norm(q.answer) ? "correct" : "wrong";
  };

  const correctCount = () => {
    if (!set) return 0;
    return set.questions.filter((q, i) => norm(answers[i] ?? "") === norm(q.answer)).length;
  };

  // ---- jump to question ----
  const handleJump = (idx: number) => {
    setCurrent(idx);
    questionRefs.current[idx]?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  // ---- render ----
  if (loading) {
    return (
      <main className="flex-1 flex items-center justify-center p-6">
        <p className="text-[var(--color-muted)]">{t("quiz.loadingSet")}</p>
      </main>
    );
  }

  if (error || !set) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
        <p className="text-[var(--color-danger)]">{error ?? t("quiz.noSet")}</p>
        <Button onClick={load}>{t("quiz.retry")}</Button>
      </main>
    );
  }

  const n = set.questions.length;
  const statuses: QuizStatus[] = Array.from({ length: n }, (_, i) => getStatus(i));

  const correct = correctCount();
  const pct = n > 0 ? Math.round((correct / n) * 100) : 0;

  return (
    <main className="flex-1 overflow-y-auto">
      {/* Header */}
      <div
        className="sticky top-0 bg-[var(--color-surface)] border-b border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] px-4 md:px-6 py-4 flex items-center gap-3 z-10"
        style={{ boxShadow: "var(--shadow-premium)" }}
      >
        <div
          className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[var(--radius-lg)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] text-[var(--color-primary-600)]"
          aria-hidden="true"
        >
          {mode === "reading" ? <BookOpen size={20} /> : <Headphones size={20} />}
        </div>
        <h1 style={{ fontFamily: "var(--font-display)" }} className="text-xl font-bold text-[var(--color-text)] capitalize flex-1 tracking-tight">
          {skill}
        </h1>
        {band && <LevelChip band={band} />}
        {band && (
          <span className="text-xs text-[var(--color-muted)] hidden sm:inline">
            {t("quiz.level")}: {band} · {t("quiz.targeting")} {NEXT_BAND[band]}
          </span>
        )}
      </div>

      <div className="p-4 md:p-6 max-w-5xl mx-auto">
        {/* Navigator */}
        <div className="mb-4">
          <QuizNavigator
            count={n}
            current={current}
            statuses={statuses}
            onJump={handleJump}
          />
        </div>

        {/* Score card (after submit) — polished big tabular-nums score */}
        {submitted && (
          <Card
            className="mb-6 flex items-center gap-5"
            style={{
              background: pct >= 70
                ? "color-mix(in srgb, var(--color-success) 8%, var(--color-surface))"
                : "color-mix(in srgb, var(--color-warning) 8%, var(--color-surface))",
              border: `1px solid ${pct >= 70 ? "color-mix(in srgb, var(--color-success) 25%, transparent)" : "color-mix(in srgb, var(--color-warning) 25%, transparent)"}`,
            }}
          >
            <div className="flex flex-col">
              <span
                className="text-4xl font-bold tabular-nums leading-none"
                style={{ color: pct >= 70 ? "var(--color-success)" : "var(--color-warning)" }}
              >
                {correct}/{n}
              </span>
              <span className="text-sm text-[var(--color-muted)] mt-1">
                {pct}% {t("quiz.correct")}
              </span>
            </div>
            <Button variant="secondary" size="sm" className="ml-auto" onClick={load}>
              {t("quiz.newSet")}
            </Button>
          </Card>
        )}

        {/* Two-pane layout for reading */}
        <div className={mode === "reading" && set.passage ? "md:grid md:grid-cols-2 md:gap-8" : ""}>
          {/* Passage — Lexend 18px lh 1.7 ~66ch */}
          {mode === "reading" && set.passage && (
            <div className="mb-4 md:mb-0">
              <Card className="h-full">
                <div
                  className="text-[var(--color-text)] leading-[1.7] max-w-[66ch]"
                  style={{ fontSize: "1.125rem", fontFamily: "var(--font-reading)" }}
                >
                  {set.passage.split("\n").map((para, i) => (
                    <p key={i} className="mb-4 last:mb-0">{para}</p>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {mode === "listening" && (
            <div className="mb-4">
              <Card>
                <div className="flex items-center gap-3 mb-2">
                  <Button
                    variant="primary"
                    size="sm"
                    pill
                    onClick={handlePlay}
                    disabled={speaking}
                    aria-label={speaking ? t("quiz.playing") : t("quiz.playAudio")}
                  >
                    {speaking ? t("quiz.playing") : `▶ ${t("test.play")}`}
                  </Button>
                  {!window.speechSynthesis && (
                    <span className="text-xs text-[var(--color-warning)]">
                      {t("quiz.ttsUnavailable")}
                    </span>
                  )}
                </div>
                {showTranscript && set.transcript && (
                  <div className="mt-3 border-t border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] pt-3">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)] mb-2">{t("quiz.transcript")}</p>
                    <p
                      className="text-sm text-[var(--color-text)] leading-relaxed"
                      style={{ fontFamily: "var(--font-reading)" }}
                    >
                      {set.transcript}
                    </p>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Questions */}
          <div className="flex flex-col gap-4">
            {set.questions.map((q: QuizQuestion, qi: number) => (
              <div
                key={qi}
                ref={(el) => { questionRefs.current[qi] = el; }}
                data-qi={qi}
              >
                <QuestionItem
                  question={q}
                  index={qi}
                  answer={answers[qi]}
                  submitted={submitted}
                  status={getStatus(qi)}
                  onChange={(val) => {
                    setAnswers((prev) => ({ ...prev, [qi]: val }));
                    setCurrent(qi);
                  }}
                />
              </div>
            ))}

            {/* Submit / New set */}
            {!submitted && (
              <Button
                className="mt-2 self-start"
                pill
                onClick={handleSubmit}
                disabled={Object.keys(answers).length === 0}
              >
                {t("quiz.submit")}
              </Button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
};

// ---------------------------------------------------------------------------
// QuestionItem sub-component
// ---------------------------------------------------------------------------
interface QuestionItemProps {
  question: QuizQuestion;
  index: number;
  answer?: string;
  submitted: boolean;
  status: QuizStatus;
  onChange: (val: string) => void;
}

const QuestionItem: React.FC<QuestionItemProps> = ({
  question,
  index,
  answer,
  submitted,
  status,
  onChange,
}) => {
  const { t } = useT();
  const borderColor =
    submitted
      ? status === "correct"
        ? "border-[var(--color-success)]"
        : "border-[var(--color-danger)]"
      : "border-[var(--color-border)]";

  return (
    <Card className={`border-2 ${borderColor}`}>
      <p className="text-sm font-medium text-[var(--color-text)] mb-3">
        <span className="text-[var(--color-muted)] mr-1">{index + 1}.</span>
        {question.stem}
      </p>

      {question.options ? (
        <fieldset>
          <legend className="sr-only">{t("quiz.question")} {index + 1} {t("quiz.options")}</legend>
          <div className="flex flex-col gap-2">
            {question.options.map((opt) => {
              const selected = answer === opt;
              const isCorrect = norm(opt) === norm(question.answer);
              let optColor = "border-[var(--color-border)] text-[var(--color-text)]";
              if (submitted && isCorrect) optColor = "border-[var(--color-success)] text-[var(--color-success)] bg-[color-mix(in_srgb,var(--color-success)_10%,transparent)]";
              else if (submitted && selected && !isCorrect) optColor = "border-[var(--color-danger)] text-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_10%,transparent)]";
              else if (selected) optColor = "border-[var(--color-primary-600)] text-[var(--color-primary-600)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)]";

              return (
                <label
                  key={opt}
                  className={`flex min-h-11 items-center gap-2 px-4 py-3 rounded-[var(--radius-lg)] border cursor-pointer text-sm font-medium transition-colors ${optColor}`}
                >
                  <input
                    type="radio"
                    name={`q-${index}`}
                    value={opt}
                    checked={selected}
                    disabled={submitted}
                    onChange={() => onChange(opt)}
                    className="sr-only"
                  />
                  {opt}
                </label>
              );
            })}
          </div>
        </fieldset>
      ) : (
        <input
          type="text"
          value={answer ?? ""}
          disabled={submitted}
          onChange={(e) => onChange(e.target.value)}
          placeholder={t("quiz.typeAnswer")}
          aria-label={`${t("quiz.answerForQuestion")} ${index + 1}`}
          className="min-h-11 w-full px-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)] text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
        />
      )}

      {submitted && question.explanation && (
        <p className="mt-3 text-xs text-[var(--color-muted)] leading-relaxed border-t border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] pt-3">
          {question.explanation}
        </p>
      )}
    </Card>
  );
};
