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

  return (
    <div className="journey-bg flex min-h-full items-center justify-center p-6">
      <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-5 text-center">
        <div
          className="self-center flex items-center justify-center w-12 h-12 rounded-[var(--radius-xl)]"
          style={{ background: "linear-gradient(135deg, var(--color-primary-600), var(--color-primary-800))" }}
          aria-hidden="true"
        >
          <KeyRound size={22} className="text-white" />
        </div>
        <h1 className="text-xl font-bold text-[var(--color-text)]">{t("auth.resetTitle")}</h1>
        {sent ? (
          <>
            <p className="text-sm text-[var(--color-muted)]">
              If an account exists for <strong>{email}</strong>, we've sent a reset link. Check your
              inbox (and spam). The link works for 1 hour.
            </p>
            <Button variant="secondary" onClick={onBack} className="w-full">{t("auth.backToSignin")}</Button>
          </>
        ) : (
          <>
            <p className="text-sm text-[var(--color-muted)]">
              {t("auth.resetSub")}
            </p>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-label="Email"
              placeholder="you@example.com"
              className="min-h-11 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
            />
            <Button type="submit" loading={busy} disabled={!email.trim()} className="w-full">{t("auth.sendLink")}</Button>
            <button type="button" onClick={onBack} className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] min-h-11">
              {t("auth.backToSignin")}
            </button>
          </>
        )}
      </form>
    </div>
  );
};
