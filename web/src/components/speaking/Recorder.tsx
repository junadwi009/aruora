import React, { useEffect, useRef, useState } from "react";
import { Mic, Square, Loader2, AlertCircle } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";

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
      setError("Microphone access was blocked. You can type your answer instead.");
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
      const text = (out.transcript || "").trim();
      if (text) onTranscript(text);
      setState("idle");
      if (!text) setError("No speech was detected. Try recording again, or type your answer.");
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Transcription failed. You can type your answer instead."
      );
      setState("error");
    }
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
              Voice recording unavailable
            </p>
            <p className="text-xs text-[var(--color-muted)]">
              Speech transcription isn’t enabled on this server (or your browser blocks
              recording). Type your spoken answer below instead.
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
            <Square size={14} className="mr-1.5" /> Stop ({mmss})
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
                <Loader2 size={14} className="mr-1.5 animate-spin" /> Transcribing…
              </>
            ) : (
              <>
                <Mic size={14} className="mr-1.5" /> Record answer
              </>
            )}
          </Button>
        )}

        <p className="text-xs text-[var(--color-muted)]" aria-live="polite">
          {state === "recording"
            ? "Recording — speak now, then Stop."
            : state === "transcribing"
            ? "Converting your speech to text…"
            : "Record your answer; the transcript appears below and stays editable."}
        </p>
      </div>

      {error && (
        <p className="mt-2 text-xs text-[var(--color-danger)]">{error}</p>
      )}
    </Card>
  );
};
