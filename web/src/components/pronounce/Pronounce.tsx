import React, { useState } from "react";
import { Volume2, RefreshCw } from "lucide-react";
import { api } from "../../lib/api/client";
import type { PronounceTarget, PronounceFeedback } from "../../lib/types";
import { wordAccuracy } from "../../lib/pron";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Recorder } from "../speaking/Recorder";

const SEED: PronounceTarget = {
  text: "The early train to the city usually arrives before eight in the morning.",
  focus: "sentence stress on content words",
  tips: ["Stress the content words.", "Reduce 'the' to a quick schwa.", "Link words smoothly."],
};

export const Pronounce: React.FC = () => {
  const [target, setTarget] = useState<PronounceTarget>(SEED);
  const [loadingTarget, setLoadingTarget] = useState(false);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [result, setResult] = useState<{ accuracy: number; missed: string[] } | null>(null);
  const [feedback, setFeedback] = useState<PronounceFeedback | null>(null);
  const [busy, setBusy] = useState(false);

  const newSentence = async () => {
    setLoadingTarget(true);
    setTranscript(null);
    setResult(null);
    setFeedback(null);
    try {
      setTarget(await api.pronounceSentence({ level: "B1" }));
    } catch {
      /* keep current target */
    } finally {
      setLoadingTarget(false);
    }
  };

  const speak = () => {
    if (window.speechSynthesis) window.speechSynthesis.speak(new SpeechSynthesisUtterance(target.text));
  };

  const onTranscript = async (text: string) => {
    setTranscript(text);
    const acc = wordAccuracy(target.text, text);
    setResult(acc);
    setBusy(true);
    try {
      setFeedback(
        await api.pronounceFeedback({ target: target.text, transcript: text, accuracy: acc.accuracy, missed: acc.missed })
      );
    } catch {
      setFeedback(null);
    } finally {
      setBusy(false);
    }
  };

  const missedSet = new Set((result?.missed ?? []).map((m) => m.toLowerCase()));

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10 flex items-center justify-between">
        <h1 className="text-base font-semibold text-[var(--color-text)]">Pronunciation drill</h1>
        <Button variant="ghost" size="sm" onClick={newSentence} loading={loadingTarget}>
          <RefreshCw size={14} className="mr-1" /> New sentence
        </Button>
      </div>

      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col gap-4">
        {/* Target */}
        <Card>
          <div className="flex items-start justify-between gap-3">
            <p className="text-lg leading-relaxed text-[var(--color-text)]" style={{ fontFamily: "var(--font-reading)" }}>
              {target.text.split(/\s+/).map((w, i) => {
                const bare = w.toLowerCase().replace(/[^a-z0-9']/g, "");
                const isMissed = result && missedSet.has(bare);
                return (
                  <span key={i} className={isMissed ? "text-[var(--color-danger)] underline decoration-wavy" : ""}>
                    {w}{" "}
                  </span>
                );
              })}
            </p>
            <Button variant="secondary" size="sm" onClick={speak} aria-label="Listen to target">
              <Volume2 size={16} />
            </Button>
          </div>
          {target.focus && (
            <p className="text-xs text-[var(--color-muted)] mt-2">Focus: {target.focus}</p>
          )}
        </Card>

        {/* Record */}
        <Recorder onTranscript={onTranscript} />

        {transcript !== null && (
          <Card>
            <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">
              Recogniser heard
            </p>
            <p className="text-sm text-[var(--color-text)]">{transcript || "(nothing detected)"}</p>
            {result && (
              <p className="mt-3 text-sm">
                <span className="font-semibold text-[var(--color-text)]">{result.accuracy}%</span>{" "}
                <span className="text-[var(--color-muted)]">word match (approximate)</span>
              </p>
            )}
          </Card>
        )}

        {busy && <Card className="text-sm text-[var(--color-muted)]">Getting tips…</Card>}

        {feedback && (
          <Card className="flex flex-col gap-3">
            <p className="text-sm text-[var(--color-text)] leading-relaxed">{feedback.summary}</p>
            {feedback.wordTips?.length > 0 && (
              <div>
                <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-1">Word tips</p>
                <ul className="flex flex-col gap-1">
                  {feedback.wordTips.map((t, i) => (
                    <li key={i} className="text-sm text-[var(--color-text)]">
                      <span className="font-semibold">{t.word}</span> — {t.tip}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {feedback.prosody?.length > 0 && (
              <div>
                <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-1">Stress & intonation</p>
                <ul className="list-disc pl-5 flex flex-col gap-1">
                  {feedback.prosody.map((p, i) => (
                    <li key={i} className="text-sm text-[var(--color-text)]">{p}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[11px] text-[var(--color-muted)]">
              Approximate (recogniser + tips) — not phoneme-level scoring.
            </p>
          </Card>
        )}
      </div>
    </main>
  );
};
