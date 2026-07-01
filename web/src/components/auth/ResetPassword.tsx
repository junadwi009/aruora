import React, { useState } from "react";
import { KeyRound } from "lucide-react";
import { api } from "../../lib/api/client";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

/** Shown when the app is opened via a ?reset_token=… link. */
export const ResetPassword: React.FC<{ token: string; onDone: () => void }> = ({ token, onDone }) => {
  const { t } = useT();
  const [pw, setPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pw.length < 6) { setError(t("auth.pwTooShort")); return; }
    setBusy(true);
    setError(null);
    try {
      await api.accountReset({ token, newPassword: pw });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.resetLinkInvalid"));
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
        <h1 className="text-xl font-bold text-[var(--color-text)]">{t("auth.newPassword")}</h1>
        {done ? (
          <>
            <p className="text-sm text-[var(--color-success)]">{t("auth.resetDone")}</p>
            <Button onClick={onDone} className="w-full">{t("auth.goSignin")}</Button>
          </>
        ) : (
          <>
            <input
              type="password"
              autoComplete="new-password"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              aria-label={t("auth.newPasswordAria")}
              placeholder={t("auth.newPasswordPlaceholder")}
              className="min-h-11 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
            />
            {error && <p className="text-xs text-[var(--color-danger)]" role="alert">{error}</p>}
            <Button type="submit" loading={busy} disabled={!pw} className="w-full">{t("auth.resetBtn")}</Button>
            <button type="button" onClick={onDone} className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] min-h-11">
              {t("common.cancel")}
            </button>
          </>
        )}
      </form>
    </div>
  );
};
