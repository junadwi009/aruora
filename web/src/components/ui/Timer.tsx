import React, { useEffect, useRef, useState } from "react";
import { Clock } from "lucide-react";
import { useT } from "../../lib/i18n";

export interface TimerProps {
  seconds: number;
  onExpire?: () => void;
  running?: boolean;
}

function formatTime(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export const Timer: React.FC<TimerProps> = ({
  seconds,
  onExpire,
  running = true,
}) => {
  const { t } = useT();
  const [remaining, setRemaining] = useState(seconds);
  const expiredCalled = useRef(false);

  useEffect(() => {
    if (!running) return;
    if (remaining <= 0) {
      if (!expiredCalled.current) {
        expiredCalled.current = true;
        onExpire?.();
      }
      return;
    }

    const id = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 1;
        if (next <= 0) {
          clearInterval(id);
          if (!expiredCalled.current) {
            expiredCalled.current = true;
            onExpire?.();
          }
          return 0;
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(id);
  }, [running, remaining, onExpire]);

  const isLow = remaining < 120;

  return (
    <div
      className={`inline-flex items-center gap-1.5 font-mono text-sm ${
        isLow ? "text-[var(--color-warning)]" : "text-[var(--color-text)]"
      }`}
    >
      <Clock size={14} aria-hidden="true" />
      <span aria-live="polite" aria-label={t("timer.remaining")}>
        {formatTime(remaining)}
      </span>
      {isLow && remaining > 0 && (
        <span className="text-xs font-sans">{t("timer.timeLow")}</span>
      )}
    </div>
  );
};
