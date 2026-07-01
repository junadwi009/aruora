import React, { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api/client";
import { useJourney } from "../../lib/journey";
import { useT } from "../../lib/i18n";
import type { PlacementStart } from "../../lib/types";
import { PlacementIntro } from "./PlacementIntro";
import { TestFrame } from "./TestFrame";
import { ListeningSection } from "./ListeningSection";
import { ReadingSection } from "./ReadingSection";
import { WritingSection } from "./WritingSection";
import { SpeakingSection } from "./SpeakingSection";

type Phase =
  | "loading"
  | "intro"
  | "listening"
  | "reading"
  | "writing"
  | "speaking"
  | "submitting";

const SECTION_ORDER: Phase[] = ["listening", "reading", "writing", "speaking"];
const SECTION_LABEL_KEYS: Record<string, string> = {
  listening: "nav.listening",
  reading: "nav.reading",
  writing: "nav.writing",
  speaking: "nav.speaking",
};

export const PlacementRunner: React.FC = () => {
  const { go, setPlacementResult } = useJourney();
  const { t } = useT();

  const [phase, setPhase] = useState<Phase>("loading");
  const [combo, setCombo] = useState<PlacementStart | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [writingText, setWritingText] = useState("");
  const [speakingText, setSpeakingText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const startedAt = useRef<number>(0);

  // Load combo on mount
  useEffect(() => {
    let active = true;
    api
      .placementStart()
      .then((c) => {
        if (!active) return;
        setCombo(c);
        setPhase("intro");
      })
      .catch((e) => {
        if (!active) return;
        setError(
          e instanceof Error ? e.message : t("place.errLoad")
        );
      });
    return () => {
      active = false;
    };
  }, []);

  const setAnswer = (id: number, val: string) => {
    setAnswers((prev) => ({ ...prev, [id]: val }));
  };

  const advancePhase = () => {
    setPhase((current) => {
      if (current === "intro") return "listening";
      const idx = SECTION_ORDER.indexOf(current);
      if (idx === -1) return current;
      if (idx < SECTION_ORDER.length - 1) {
        return SECTION_ORDER[idx + 1];
      }
      // After speaking — submit
      return "submitting";
    });
  };

  // Submit when phase becomes "submitting"
  useEffect(() => {
    if (phase !== "submitting" || !combo) return;

    const body = {
      comboId: combo.comboId,
      answers,
      writingSamples: {
        taskType:
          (combo.sections.writing as { taskType?: string })?.taskType ??
          "task2",
        prompt:
          (combo.sections.writing as { prompt?: string })?.prompt ?? "",
        essay: writingText,
      },
      speakingText,
      durationSec: Math.round((Date.now() - startedAt.current) / 1000),
    };

    api
      .placementSubmit(body)
      .then((result) => {
        setPlacementResult(result);
        go("generating");
      })
      .catch((e) => {
        setError(
          e instanceof Error ? e.message : t("place.errSubmit")
        );
        setPhase("speaking"); // go back so user can retry
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  // ---- Render ----

  if (error) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <p role="alert" className="text-[var(--color-danger)] text-sm">
          {error}
        </p>
      </div>
    );
  }

  if (phase === "loading" || !combo) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <p className="text-[var(--color-muted)]">{t("place.loadingTest")}</p>
      </div>
    );
  }

  if (phase === "submitting") {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <p className="text-[var(--color-muted)]">{t("place.submitting")}</p>
      </div>
    );
  }

  if (phase === "intro") {
    return (
      <PlacementIntro
        onBegin={() => {
          startedAt.current = Date.now();
          setPhase("listening");
        }}
      />
    );
  }

  // Section phases
  const listeningItems = combo.items.filter((i) => i.skill === "listening");
  const readingItems = combo.items.filter((i) => i.skill === "reading");

  const listeningSection = combo.sections.listening as {
    seconds: number;
    clips: { title: string; transcript: string }[];
  };
  const readingSection = combo.sections.reading as {
    seconds: number;
    title: string;
    passage: string;
  };
  const writingSection = combo.sections.writing as {
    seconds: number;
    taskType: string;
    targetWords: number;
    prompt: string;
  };
  const speakingSection = combo.sections.speaking as {
    seconds: number;
    part1: string[];
    part2: { cue: string };
    part3: string[];
  };

  const stepIndex = SECTION_ORDER.indexOf(phase) + 1;
  const stepCount = SECTION_ORDER.length;
  const sectionLabel = SECTION_LABEL_KEYS[phase] ? t(SECTION_LABEL_KEYS[phase]) : phase;
  const isLastSection = phase === "speaking";

  const getSectionSeconds = (): number => {
    switch (phase) {
      case "listening": return listeningSection?.seconds ?? 600;
      case "reading": return readingSection?.seconds ?? 600;
      case "writing": return writingSection?.seconds ?? 600;
      case "speaking": return speakingSection?.seconds ?? 600;
      default: return 600;
    }
  };

  return (
    <TestFrame
      sectionName={sectionLabel}
      stepIndex={stepIndex}
      stepCount={stepCount}
      seconds={getSectionSeconds()}
      onTimeUp={advancePhase}
      onNext={advancePhase}
      nextLabel={isLastSection ? t("place.submit") : t("common.next")}
      running={true}
    >
      {phase === "listening" && (
        <ListeningSection
          section={listeningSection}
          items={listeningItems}
          answers={answers}
          setAnswer={setAnswer}
        />
      )}
      {phase === "reading" && (
        <ReadingSection
          section={readingSection}
          items={readingItems}
          answers={answers}
          setAnswer={setAnswer}
        />
      )}
      {phase === "writing" && (
        <WritingSection
          section={writingSection}
          value={writingText}
          setValue={setWritingText}
        />
      )}
      {phase === "speaking" && (
        <SpeakingSection
          section={speakingSection}
          value={speakingText}
          setValue={setSpeakingText}
        />
      )}
    </TestFrame>
  );
};
