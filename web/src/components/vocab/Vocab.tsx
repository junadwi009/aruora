import React, { useEffect, useState } from "react";
import { Layers, Plus, RotateCcw } from "lucide-react";
import { api } from "../../lib/api/client";
import type { VocabWord, Flashcard, CardStats } from "../../lib/types";
import { useT } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

type Mode = "build" | "review";

export const Vocab: React.FC = () => {
  const { t } = useT();
  const [mode, setMode] = useState<Mode>("build");
  const [stats, setStats] = useState<CardStats>({ total: 0, due: 0 });

  const refreshStats = () => api.cardsList().then((r) => setStats(r.stats)).catch(() => {});
  useEffect(() => { refreshStats(); }, []);

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers size={18} className="text-[var(--color-primary-600)]" aria-hidden="true" />
          <h1 className="text-base font-semibold text-[var(--color-text)]">{t("vocab.title")}</h1>
        </div>
        <div className="flex gap-1.5">
          <Button variant={mode === "build" ? "primary" : "secondary"} size="sm" onClick={() => setMode("build")}>
            {t("vocab.build")}
          </Button>
          <Button variant={mode === "review" ? "primary" : "secondary"} size="sm" onClick={() => { setMode("review"); }}>
            {t("vocab.review")}{stats.due > 0 ? ` (${stats.due})` : ""}
          </Button>
        </div>
      </div>

      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col gap-4">
        <p className="text-xs text-[var(--color-muted)]">{t("vocab.deckLabel")}: {stats.total} {t("vocab.cards")} · {stats.due} {t("vocab.due")}</p>
        {mode === "build" ? <Build onChange={refreshStats} /> : <Review onChange={refreshStats} />}
      </div>
    </main>
  );
};

// ── Build: generate vocab + add to deck ───────────────────────────────────────
const Build: React.FC<{ onChange: () => void }> = ({ onChange }) => {
  const { t } = useT();
  const [topic, setTopic] = useState("environment");
  const [words, setWords] = useState<VocabWord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState<Set<string>>(new Set());

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.vocab({ topic, level: "B1" });
      setWords(r.words ?? []);
      setAdded(new Set());
    } catch {
      setError(t("vocab.generateError"));
    } finally {
      setLoading(false);
    }
  };

  const addOne = async (w: VocabWord) => {
    await api.cardAdd({ front: w.word, back: `${w.definition}${w.example ? `\n\ne.g. ${w.example}` : ""}` });
    setAdded((p) => new Set(p).add(w.word));
    onChange();
  };

  const addAll = async () => {
    const fresh = words.filter((w) => !added.has(w.word));
    if (!fresh.length) return;
    await api.cardAdd({ cards: fresh.map((w) => ({ front: w.word, back: `${w.definition}${w.example ? `\n\ne.g. ${w.example}` : ""}` })) });
    setAdded(new Set(words.map((w) => w.word)));
    onChange();
  };

  return (
    <>
      <div className="flex gap-2">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder={t("vocab.topicPlaceholder")}
          aria-label={t("vocab.topicAria")}
          className="flex-1 min-h-10 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)]"
        />
        <Button onClick={generate} loading={loading} disabled={!topic.trim()}>
          {t("vocab.generate")}
        </Button>
      </div>
      {error && <p className="text-xs text-[var(--color-danger)]">{error}</p>}

      {words.length > 0 && (
        <div className="flex justify-end">
          <Button variant="secondary" size="sm" onClick={addAll}>
            <Plus size={14} className="mr-1" /> {t("vocab.addAll")}
          </Button>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {words.map((w) => (
          <Card key={w.word} className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--color-text)]">
                {w.word} {w.pos && <span className="text-xs font-normal text-[var(--color-muted)]">· {w.pos}</span>}
              </p>
              <p className="text-sm text-[var(--color-text)]">{w.definition}</p>
              {w.example && <p className="text-xs text-[var(--color-muted)] italic mt-0.5">{w.example}</p>}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => addOne(w)}
              disabled={added.has(w.word)}
              aria-label={`${t("vocab.add")} ${w.word}`}
            >
              {added.has(w.word) ? t("vocab.added") : <Plus size={16} />}
            </Button>
          </Card>
        ))}
      </div>
    </>
  );
};

// ── Review: SM-2 flip + grade ─────────────────────────────────────────────────
const GRADES: { labelKey: string; quality: number; variant: "secondary" | "primary" | "destructive" | "ghost" }[] = [
  { labelKey: "vocab.gradeAgain", quality: 1, variant: "destructive" },
  { labelKey: "vocab.gradeHard", quality: 3, variant: "secondary" },
  { labelKey: "vocab.gradeGood", quality: 4, variant: "primary" },
  { labelKey: "vocab.gradeEasy", quality: 5, variant: "ghost" },
];

const Review: React.FC<{ onChange: () => void }> = ({ onChange }) => {
  const { t } = useT();
  const [queue, setQueue] = useState<Flashcard[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const load = () => {
    api.cardsDue().then((d) => { setQueue(d); setIdx(0); setFlipped(false); }).catch(() => setQueue([]));
  };
  useEffect(() => { load(); }, []);

  if (queue === null) return <Card className="text-sm text-[var(--color-muted)]">{t("common.loading")}</Card>;

  if (queue.length === 0 || idx >= queue.length) {
    return (
      <Card className="flex flex-col items-center gap-3 py-10 text-center">
        <p className="text-base font-semibold text-[var(--color-text)]">{t("vocab.allCaughtUp")} 🎉</p>
        <p className="text-sm text-[var(--color-muted)]">{t("vocab.noCardsDue")}</p>
        <Button variant="secondary" size="sm" onClick={load}>
          <RotateCcw size={14} className="mr-1" /> {t("vocab.refresh")}
        </Button>
      </Card>
    );
  }

  const card = queue[idx];

  const grade = async (quality: number) => {
    await api.cardReview(card.id, quality);
    onChange();
    setFlipped(false);
    setIdx((i) => i + 1);
  };

  return (
    <>
      <p className="text-xs text-[var(--color-muted)] text-center">{idx + 1} {t("vocab.of")} {queue.length}</p>
      <Card className="min-h-40 flex flex-col items-center justify-center text-center gap-3 py-8">
        <p className="text-lg font-semibold text-[var(--color-text)]">{card.front}</p>
        {flipped ? (
          <p className="text-sm text-[var(--color-text)] whitespace-pre-wrap">{card.back}</p>
        ) : (
          <Button variant="secondary" size="sm" onClick={() => setFlipped(true)}>{t("vocab.showAnswer")}</Button>
        )}
      </Card>
      {flipped && (
        <div className="grid grid-cols-4 gap-2">
          {GRADES.map((g) => (
            <Button key={g.labelKey} variant={g.variant} size="sm" onClick={() => grade(g.quality)}>
              {t(g.labelKey)}
            </Button>
          ))}
        </div>
      )}
    </>
  );
};
