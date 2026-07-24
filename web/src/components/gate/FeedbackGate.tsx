import React, { useState } from "react";
import { Star } from "lucide-react";
import { useT } from "../../lib/i18n";
import { api } from "../../lib/api/client";
import { Button } from "../ui/Button";

const MIN_INSIGHT_LENGTH = 20;

export const FeedbackGate: React.FC<{ onUnlocked: () => void }> = ({ onUnlocked }) => {
  const { t } = useT();
  const [stars, setStars] = useState(0);
  const [insight, setInsight] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = stars >= 1 && insight.trim().length >= MIN_INSIGHT_LENGTH;

  const submit = async () => {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.gateUnlock(stars, insight.trim());
      onUnlocked();
    } catch {
      setError(t("gate.validation"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex min-h-screen items-center justify-center overflow-y-auto bg-black/50 p-6">
      <div
        className="relative z-10 flex w-full max-w-md flex-col gap-5 rounded-[var(--radius-2xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8"
        style={{ boxShadow: "var(--shadow-premium-card)" }}
      >
        <div className="flex flex-col gap-2 text-center">
          <h2 className="text-2xl font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-display)" }}>
            {t("gate.title")}
          </h2>
          <p className="text-sm text-[var(--color-muted)]">{t("gate.body")}</p>
        </div>

        <div>
          <div className="mb-2 text-sm font-medium text-[var(--color-text)]">{t("gate.starsLabel")}</div>
          <div className="flex justify-center gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                aria-label={`star-${n}`}
                aria-pressed={stars >= n}
                onClick={() => setStars(n)}
                className="rounded-[var(--radius-md)] p-1.5 transition-colors hover:bg-[var(--color-surface-2)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
              >
                <Star
                  size={26}
                  className={
                    stars >= n
                      ? "fill-[var(--color-primary-600)] stroke-[var(--color-primary-600)]"
                      : "stroke-[var(--color-muted)]"
                  }
                />
              </button>
            ))}
          </div>
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-[var(--color-text)]">{t("gate.insightLabel")}</span>
          <textarea
            value={insight}
            onChange={(e) => setInsight(e.target.value)}
            placeholder={t("gate.insightPlaceholder")}
            rows={4}
            className="w-full rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3 text-sm text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
          />
        </label>

        {error && (
          <p className="text-xs text-[var(--color-danger)]" role="alert">
            {error}
          </p>
        )}

        <Button type="button" pill fullWidth loading={busy} disabled={!valid} onClick={submit}>
          {t("gate.submit")}
        </Button>
      </div>
    </div>
  );
};
