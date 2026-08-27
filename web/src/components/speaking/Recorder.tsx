import React, { useEffect, useRef, useState } from "react";
import { Mic, Square, Loader2, AlertCircle } from "lucide-react";
import { api } from "../../lib/api/client";
import type { Transcript } from "../../lib/types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

interface RecorderProps {
  /** Called with the transcribed text once ASR returns. */
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

type State = "checking" | "idle" | "recording" | "transcribing" | "unavailable" | "error";

const supportsRecording = () =>
  typeof navigator !== "undefined" &&
  !!navigator.mediaDevices?.getUserMedia &&
  typeof window !== "undefined" &&
  typeof window.MediaRecorder !== "undefined";

export const Recorder: React.FC<RecorderProps> = ({ onTranscript, disabled }) => {
  const { t } = useT();
  const [state, setState] = useState<State>("checking");
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Probe server ASR readiness + browser capability once on mount.
  useEffect(() => {
    let cancelled = false;
    if (!supportsRecording()) {
      setState("unavailable");
      return;
    }
    api
      .health()
      .then((h) => {
        if (!cancelled) setState(h.asrReady ? "idle" : "unavailable");
      })
      .catch(() => {
        if (!cancelled) setState("unavailable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const stopTracks = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  };

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = handleStop;
      recorderRef.current = mr;
      mr.start();
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
      setState("recording");
    } catch {
      setError(t("rec.micBlocked"));
      setState("error");
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    recorderRef.current?.stop(); // fires onstop → handleStop
  };

  const handleStop = async () => {
    stopTracks();
    setState("transcribing");
    const blob = new Blob(chunksRef.current, {
      type: recorderRef.current?.mimeType || "audio/webm",
    });
    try {
      const out = await api.speakingTranscribe(blob);
      const done = await waitForTranscript(out);
      const text = (done.transcript || "").trim();
      if (text) onTranscript(text);
      setState("idle");
      if (!text) setError(t("rec.noSpeech"));
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : t("rec.transcribeFailed")
      );
      setState("error");
    }
  };

  // WS06-02: a queued upload answers 202 {jobId} — poll the owner-scoped job
  // status until the result is ready. A direct 200 transcript (dev topology)
  // resolves immediately.
  const waitForTranscript = async (first: Transcript): Promise<Transcript> => {
    if (!first.queued || !first.jobId) return first;
    let out = first;
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const st = await api.jobStatus(out.jobId as string);
      if (st.status === "succeeded") {
        return (st.result ?? {}) as unknown as Transcript;
      }
      if (st.status === "failed" || st.status === "cancelled" || st.status === "expired") {
        throw new Error(st.errorMessage || t("rec.transcribeFailed"));
      }
    }
    throw new Error(t("rec.transcribeFailed"));
  };

  const mmss = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(
    elapsed % 60
  ).padStart(2, "0")}`;

  // --- Unavailable: keep the typed-only fallback explicit ---
  if (state === "unavailable") {
    return (
      <Card className="bg-[var(--color-surface-2)]">
        <div className="flex items-start gap-2">
          <AlertCircle size={16} className="mt-0.5 text-[var(--color-muted)]" />
          <div>
            <p className="text-xs font-medium text-[var(--color-text)]">
              {t("rec.unavailableTitle")}
            </p>
            <p className="text-xs text-[var(--color-muted)]">
              {t("rec.unavailableBody")}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="bg-[var(--color-surface-2)]">
      <div className="flex items-center gap-3">
        {state === "recording" ? (
          <Button variant="destructive" size="sm" onClick={stopRecording} disabled={disabled}>
            <Square size={14} className="mr-1.5" /> {t("rec.stop")} ({mmss})
          </Button>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={startRecording}
            loading={state === "transcribing"}
            disabled={disabled || state === "checking" || state === "transcribing"}
          >
            {state === "transcribing" ? (
              <>
                <Loader2 size={14} className="mr-1.5 animate-spin" /> {t("rec.transcribing")}
              </>
            ) : (
              <>
                <Mic size={14} className="mr-1.5" /> {t("rec.recordAnswer")}
              </>
            )}
          </Button>
        )}

        <p className="text-xs text-[var(--color-muted)]" aria-live="polite">
          {state === "recording"
            ? t("rec.statusRecording")
            : state === "transcribing"
            ? t("rec.statusTranscribing")
            : t("rec.statusIdle")}
        </p>
      </div>

      {error && (
        <p className="mt-2 text-xs text-[var(--color-danger)]">{error}</p>
      )}
    </Card>
  );
};
