import React, { useState } from "react";
import { ClipboardCheck, ArrowRight } from "lucide-react";
import { api } from "../../lib/api/client";
import type { QuizSet, QuizQuestion } from "../../lib/types";
import { bandFromPct, roundHalf } from "../../lib/band";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Timer } from "../ui/Timer";
import { useView } from "../menu/viewContext";
import { useT } from "../../lib/i18n";

type Stage = "intro" | "listening" | "reading" | "result";

function norm(s: string): string {
  return s.toLowerCase().trim().replace(/\s+/g, " ");
}

function gradePct(set: QuizSet | null, answers: Record<number, string>): number {
  if (!set || set.questions.length === 0) return 0;
  const correct = set.questions.filter((q, i) => norm(answers[i] ?? "") === norm(q.answer)).length;
  return Math.round((correct / set.questions.length) * 100);
}

const MOCK_SECONDS = 30 * 60;

export const MockTest: React.FC = () => {
  const { setView } = useView();
  const { t } = useT();
  const [stage, setStage] = useState<Stage>("intro");
  const [listeningSet, setListeningSet] = useState<QuizSet | null>(null);
  const [readingSet, setReadingSet] = useState<QuizSet | null>(null);
  const [lAnswers, setLAnswers] = useState<Record<number, string>>({});
  const [rAnswers, setRAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ l: number; r: number; overall: number } | null>(null);

  const start = async () => {
    setLoading(true);
    setError(null);
    try {
      const [l, r] = await Promise.all([
        api.practiceSet("listening"),
        api.practiceSet("reading"),
      ]);
      setListeningSet(l);
      setReadingSet(r);
      setStage("listening");
    } catch {
      setError(t("test.loadError"));
    } finally {
      setLoading(false);
    }
  };

  const finish = async () => {
    const lBand = bandFromPct(gradePct(listeningSet, lAnswers));
    const rBand = bandFromPct(gradePct(readingSet, rAnswers));
    const overall = roundHalf((lBand + rBand) / 2);
    setResult({ l: lBand, r: rBand, overall });
    setStage("result");
    try {
      await api.mockSave({ listening: lBand, reading: rBand, overall });
    } catch {
      /* non-fatal — result still shown */
    }
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div
        className="sticky top-0 bg-[var(--color-surface)] border-b border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] px-4 md:px-6 py-4 z-10 flex items-center justify-between gap-3"
        style={{ boxShadow: "var(--shadow-e1)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-lg)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] text-[var(--color-primary-600)]"
            aria-hidden="true"
          >
            <ClipboardCheck size={20} />
          </div>
          <h1 style={{ fontFamily: "var(--font-display)" }} className="text-xl font-bold text-[var(--color-text)] tracking-tight">{t("test.title")}</h1>
        </div>
        {(stage === "listening" || stage === "reading") && (
          <Timer seconds={MOCK_SECONDS} onExpire={finish} />
        )}
      </div>

      <div className="p-4 md:p-6 max-w-3xl mx-auto flex flex-col gap-4">
        {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}

        {stage === "intro" && (
          <Card
            className="flex flex-col items-center gap-5 py-12 text-center rounded-[var(--radius-3xl)]"
            style={{ boxShadow: "var(--shadow-premium)" }}
          >
            <div
              className="flex h-16 w-16 items-center justify-center rounded-[var(--radius-2xl)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] text-[var(--color-primary-600)]"
              aria-hidden="true"
            >
              <ClipboardCheck size={30} />
            </div>
            <div className="flex flex-col gap-2">
              <p className="text-base font-semibold text-[var(--color-text)]">{t("test.introTitle")}</p>
              <p className="text-sm text-[var(--color-muted)] max-w-sm">
                {t("test.introBody")}
              </p>
            </div>
            <Button onClick={start} loading={loading} pill>
              {loading ? t("common.loading") : t("test.startMock")}
            </Button>
          </Card>
        )}

        {stage === "listening" && listeningSet && (
          <Section
            title={t("test.section1Listening")}
            set={listeningSet}
            answers={lAnswers}
            onAnswer={(i, v) => setLAnswers((p) => ({ ...p, [i]: v }))}
            isListening
            onNext={() => setStage("reading")}
            nextLabel={t("test.goToReading")}
          />
        )}

        {stage === "reading" && readingSet && (
          <Section
            title={t("test.section2Reading")}
            set={readingSet}
            answers={rAnswers}
            onAnswer={(i, v) => setRAnswers((p) => ({ ...p, [i]: v }))}
            onNext={finish}
            nextLabel={t("test.finishScore")}
          />
        )}

        {stage === "result" && result && (
          <Card
            className="flex flex-col gap-4 py-8 rounded-[var(--radius-3xl)]"
            style={{ boxShadow: "var(--shadow-premium)" }}
          >
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)] text-center">
              {t("test.estimatedResult")}
            </p>
            <div className="flex items-center justify-center gap-8">
              <ScorePill label={t("nav.listening")} band={result.l} />
              <ScorePill label={t("nav.reading")} band={result.r} />
              <ScorePill label={t("test.overall")} band={result.overall} highlight />
            </div>
            <p className="text-[11px] text-[var(--color-muted)] text-center">
              {t("test.estimateNote")}
            </p>
            <div className="flex justify-center gap-2">
              <Button variant="secondary" pill onClick={() => { setStage("intro"); setResult(null); setLAnswers({}); setRAnswers({}); }}>
                {t("test.newMock")}
              </Button>
              <Button pill onClick={() => setView("progress")}>
                {t("test.viewProgress")} <ArrowRight size={14} className="ml-1" />
              </Button>
            </div>
          </Card>
        )}
      </div>
    </main>
  );
};

const ScorePill: React.FC<{ label: string; band: number; highlight?: boolean }> = ({ label, band, highlight }) => (
  <div className="flex flex-col items-center gap-1">
    <span
      className={`tabular-nums font-bold leading-none ${highlight ? "text-4xl text-[var(--color-primary-600)]" : "text-3xl text-[var(--color-text)]"}`}
    >
      {band}
    </span>
    <span className="text-xs text-[var(--color-muted)]">{label}</span>
  </div>
);

// ── One section (reuses the local-grade pattern) ──────────────────────────────
interface SectionProps {
  title: string;
  set: QuizSet;
  answers: Record<number, string>;
  onAnswer: (i: number, v: string) => void;
  onNext: () => void;
  nextLabel: string;
  isListening?: boolean;
}

const Section: React.FC<SectionProps> = ({ title, set, answers, onAnswer, onNext, nextLabel, isListening }) => {
  const { t } = useT();
  const play = () => {
    if (!set.transcript || !window.speechSynthesis) return;
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(set.transcript));
  };
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[var(--color-text)]">{title}</h2>
        {isListening && set.transcript && (
          <Button variant="secondary" size="sm" onClick={play}>▶ {t("test.play")}</Button>
        )}
      </div>

      {!isListening && set.passage && (
        <Card>
          <div className="leading-[1.7] max-w-[66ch]" style={{ fontSize: "1.0625rem", fontFamily: "var(--font-reading)" }}>
            {set.passage.split("\n").map((p, i) => (
              <p key={i} className="mb-3 last:mb-0 text-[var(--color-text)]">{p}</p>
            ))}
          </div>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {set.questions.map((q: QuizQuestion, qi: number) => (
          <Card key={qi}>
            <p className="text-sm font-medium text-[var(--color-text)] mb-2">
              <span className="text-[var(--color-muted)] mr-1">{qi + 1}.</span>{q.stem}
            </p>
            {q.options ? (
              <div className="flex flex-col gap-1.5">
                {q.options.map((opt) => (
                  <label key={opt} className="flex items-center gap-2 px-3 py-2 rounded-[var(--radius-md)] border border-[var(--color-border)] cursor-pointer text-sm text-[var(--color-text)]">
                    <input type="radio" name={`mq-${title}-${qi}`} checked={answers[qi] === opt} onChange={() => onAnswer(qi, opt)} />
                    {opt}
                  </label>
                ))}
              </div>
            ) : (
              <input
                type="text"
                value={answers[qi] ?? ""}
                onChange={(e) => onAnswer(qi, e.target.value)}
                placeholder={t("test.yourAnswer")}
                aria-label={`${t("test.answer")} ${qi + 1}`}
                className="min-h-10 w-full px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)]"
              />
            )}
          </Card>
        ))}
      </div>

      <Button className="self-end" pill onClick={onNext}>
        {nextLabel} <ArrowRight size={14} className="ml-1" />
      </Button>
    </>
  );
};
