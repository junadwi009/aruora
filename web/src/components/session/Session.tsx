import React, { useEffect, useState } from "react";
import { GraduationCap, Check, X, ArrowRight, RefreshCw } from "lucide-react";
import { api } from "../../lib/api/client";
import type { Lesson, LessonToday, LessonExercise } from "../../lib/types";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { useView } from "../menu/viewContext";

type Stage = "teach" | "exercises" | "produce" | "review";
const STAGES: Stage[] = ["teach", "exercises", "produce", "review"];
const STAGE_LABEL: Record<Stage, string> = {
  teach: "Learn",
  exercises: "Practice",
  produce: "Produce",
  review: "Review",
};

export const Session: React.FC = () => {
  const { goWithPrefill, setView } = useView();
  const [meta, setMeta] = useState<LessonToday | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("teach");

  useEffect(() => {
    let cancelled = false;
    api
      .lessonToday()
      .then((m) => !cancelled && setMeta(m))
      .catch(() => !cancelled && setError("Could not load today's session."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const generate = async (force = false) => {
    if (!meta) return;
    setGenerating(true);
    setError(null);
    try {
      const m = await api.lessonGenerate({ day: meta.day, focus: meta.focus, band: meta.band, force });
      setMeta(m);
      setStage("teach");
    } catch {
      setError("Generation failed. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const lesson = meta?.lesson ?? null;

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GraduationCap size={18} className="text-[var(--color-primary-600)]" aria-hidden="true" />
          <h1 className="text-base font-semibold text-[var(--color-text)]">
            Guided session{meta ? ` · Day ${meta.day}` : ""}
          </h1>
        </div>
        {lesson && (
          <Button variant="ghost" size="sm" onClick={() => generate(true)} loading={generating} aria-label="Regenerate lesson">
            <RefreshCw size={14} className="mr-1" /> Regenerate
          </Button>
        )}
      </div>

      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col gap-4">
        {loading && <Card className="py-12 text-center text-sm text-[var(--color-muted)]">Loading…</Card>}

        {!loading && error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}

        {!loading && !lesson && (
          <Card className="flex flex-col items-center gap-4 py-10 text-center">
            <p className="text-base font-semibold text-[var(--color-text)]">Today's focus: {meta?.focus}</p>
            <p className="text-sm text-[var(--color-muted)] max-w-xs">
              A short Teach → Practice → Produce → Review session, generated for your current level.
            </p>
            <Button onClick={() => generate(false)} loading={generating}>
              {generating ? "Generating…" : "Generate today's lesson"}
            </Button>
          </Card>
        )}

        {!loading && lesson && (
          <>
            {/* Goal + stage stepper */}
            <Card variant="stat">
              <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-1">Goal</p>
              <p className="text-sm text-[var(--color-text)]">{lesson.goal}</p>
              <div className="flex gap-1.5 mt-3" role="tablist" aria-label="Session stages">
                {STAGES.map((s) => (
                  <button
                    key={s}
                    role="tab"
                    aria-selected={stage === s}
                    onClick={() => setStage(s)}
                    className={[
                      "flex-1 text-xs font-medium py-1.5 rounded-[var(--radius-md)] min-h-9",
                      stage === s
                        ? "bg-[var(--color-primary-600)] text-white"
                        : "bg-[var(--color-surface-2)] text-[var(--color-muted)]",
                    ].join(" ")}
                  >
                    {STAGE_LABEL[s]}
                  </button>
                ))}
              </div>
            </Card>

            {stage === "teach" && <Teach lesson={lesson} onNext={() => setStage("exercises")} />}
            {stage === "exercises" && (
              <Exercises lesson={lesson} onNext={() => setStage("produce")} />
            )}
            {stage === "produce" && (
              <Produce
                lesson={lesson}
                onOpenSkill={() => goWithPrefill(lesson.skill, lesson.produce.prefill ?? "")}
                onNext={() => setStage("review")}
              />
            )}
            {stage === "review" && <Review lesson={lesson} onDone={() => setView("home")} />}
          </>
        )}
      </div>
    </main>
  );
};

// ── Teach ────────────────────────────────────────────────────────────────────
const Teach: React.FC<{ lesson: Lesson; onNext: () => void }> = ({ lesson, onNext }) => (
  <Card className="flex flex-col gap-3">
    <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">Learn</p>
    <p className="text-sm text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
      {lesson.teach.explanation}
    </p>
    {lesson.teach.examples?.length > 0 && (
      <ul className="flex flex-col gap-1.5 mt-1">
        {lesson.teach.examples.map((ex, i) => (
          <li key={i} className="text-sm text-[var(--color-text)] pl-3 border-l-2 border-[var(--color-primary-600)]">
            {ex}
          </li>
        ))}
      </ul>
    )}
    <Button className="self-end mt-2" onClick={onNext}>
      Practice <ArrowRight size={14} className="ml-1" />
    </Button>
  </Card>
);

// ── Exercises (auto-checked, immediate feedback) ──────────────────────────────
const Exercises: React.FC<{ lesson: Lesson; onNext: () => void }> = ({ lesson, onNext }) => (
  <div className="flex flex-col gap-4">
    {lesson.exercises.map((ex, i) => (
      <ExerciseBlock key={i} exercise={ex} />
    ))}
    <Button className="self-end" onClick={onNext}>
      Produce <ArrowRight size={14} className="ml-1" />
    </Button>
  </div>
);

const ExerciseBlock: React.FC<{ exercise: LessonExercise }> = ({ exercise }) => (
  <Card className="flex flex-col gap-3">
    <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">{exercise.instruction}</p>
    {exercise.items.map((item, i) => (
      <ExerciseItem key={i} prompt={item.prompt} answer={item.answer} feedback={item.feedback} />
    ))}
  </Card>
);

const ExerciseItem: React.FC<{ prompt: string; answer: string; feedback?: string }> = ({
  prompt,
  answer,
  feedback,
}) => {
  const [value, setValue] = useState("");
  const [checked, setChecked] = useState(false);
  const correct = value.trim().toLowerCase() === answer.trim().toLowerCase();

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-sm text-[var(--color-text)]">{prompt}</p>
      <div className="flex gap-2">
        <input
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setChecked(false);
          }}
          className="flex-1 min-h-10 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
          placeholder="Your answer…"
          aria-label="Your answer"
        />
        <Button variant="secondary" size="sm" onClick={() => setChecked(true)} disabled={!value.trim()}>
          Check
        </Button>
      </div>
      {checked && (
        <p
          className={`text-xs flex items-start gap-1 ${
            correct ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"
          }`}
          role="status"
        >
          {correct ? <Check size={14} className="mt-0.5" /> : <X size={14} className="mt-0.5" />}
          {correct ? "Correct!" : `Answer: ${answer}. ${feedback ?? ""}`}
        </p>
      )}
    </div>
  );
};

// ── Produce (hands off to the skill tab, prefilled) ───────────────────────────
const Produce: React.FC<{ lesson: Lesson; onOpenSkill: () => void; onNext: () => void }> = ({
  lesson,
  onOpenSkill,
  onNext,
}) => (
  <Card className="flex flex-col gap-3">
    <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">Produce</p>
    <p className="text-sm text-[var(--color-text)] leading-relaxed">{lesson.produce.instruction}</p>
    {lesson.produce.prefill && (
      <p className="text-sm text-[var(--color-muted)] italic pl-3 border-l-2 border-[var(--color-border)]">
        {lesson.produce.prefill}
      </p>
    )}
    <div className="flex gap-2 justify-end">
      <Button variant="ghost" size="sm" onClick={onNext}>
        Skip to review
      </Button>
      <Button onClick={onOpenSkill} className="capitalize">
        Open {lesson.skill} <ArrowRight size={14} className="ml-1" />
      </Button>
    </div>
  </Card>
);

// ── Review (collocations + tip) ───────────────────────────────────────────────
const Review: React.FC<{ lesson: Lesson; onDone: () => void }> = ({ lesson, onDone }) => (
  <Card className="flex flex-col gap-3">
    <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">Review — keep these</p>
    <ul className="flex flex-wrap gap-2">
      {lesson.review.collocations.map((c, i) => (
        <li
          key={i}
          className="text-sm px-2.5 py-1 rounded-full bg-[var(--color-surface-2)] text-[var(--color-text)]"
        >
          {c}
        </li>
      ))}
    </ul>
    {lesson.review.tip && (
      <p className="text-sm text-[var(--color-text)] mt-1">💡 {lesson.review.tip}</p>
    )}
    <Button className="self-end mt-2" onClick={onDone}>
      Finish
    </Button>
  </Card>
);
