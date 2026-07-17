import React, { useState } from "react";
import { KeyRound } from "lucide-react";
import { api } from "../../lib/api/client";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

export const ForgotPassword: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const { t } = useT();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setBusy(true);
    try {
      await api.accountForgot(email.trim());
      setSent(true);
    } finally {
      setBusy(false);
    }
  };

  const labelCls =
    "text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]";
  const inputCls =
    "min-h-11 px-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]";

  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden bg-[var(--color-bg)] p-6">
      {/* Ambient gradient blobs — decorative */}
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          top: 0,
          left: 0,
          width: "20rem",
          height: "20rem",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--color-primary-600) 28%, transparent), transparent)",
        }}
      />
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          bottom: 0,
          right: 0,
          width: "20rem",
          height: "20rem",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--color-danger) 20%, transparent), transparent)",
        }}
      />

      <form
        onSubmit={submit}
        className="relative z-10 flex w-full max-w-md flex-col gap-5 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8 text-center"
        style={{ boxShadow: "var(--shadow-premium-card)" }}
      >
        <div className="mb-2 flex flex-col items-center gap-3 text-center">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary-600)] text-white"
            style={{ boxShadow: "var(--shadow-premium)" }}
            aria-hidden="true"
          >
            <KeyRound size={24} />
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-display)" }}>
            {t("auth.resetTitle")}
          </h1>
          <p className="max-w-xs text-sm text-[var(--color-muted)]">
            {sent ? (
              <>
                {t("auth.resetSentBefore")}<strong className="text-[var(--color-text)]">{email}</strong>{t("auth.resetSentAfter")}
              </>
            ) : (
              t("auth.resetSub")
            )}
          </p>
        </div>

        {sent ? (
          <Button variant="secondary" pill onClick={onBack} className="w-full">{t("auth.backToSignin")}</Button>
        ) : (
          <>
            <label className="flex flex-col gap-2 text-left">
              <span className={labelCls}>{t("auth.email")}</span>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-label={t("auth.email")}
                placeholder="you@example.com"
                className={inputCls}
              />
            </label>
            <Button type="submit" pill loading={busy} disabled={!email.trim()} className="w-full">{t("auth.sendLink")}</Button>
            <button type="button" onClick={onBack} className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] underline-offset-2 hover:underline min-h-11">
              {t("auth.backToSignin")}
            </button>
          </>
        )}
      </form>
    </div>
  );
};
