import React, { useState } from "react";
import { Lock } from "lucide-react";
import { api } from "../../lib/api/client";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

export const PasscodeGate: React.FC<{ onUnlock: () => void }> = ({ onUnlock }) => {
  const { t } = useT();
  const [passcode, setPasscode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passcode.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.authLogin(passcode);
      onUnlock();
    } catch {
      setError(t("auth.wrongPasscode"));
      setPasscode("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="journey-bg flex min-h-full items-center justify-center p-6">
      <form onSubmit={submit} className="flex w-full max-w-xs flex-col items-center gap-5 text-center">
        <div
          className="flex items-center justify-center w-14 h-14 rounded-[var(--radius-xl)]"
          style={{ background: "linear-gradient(135deg, var(--color-primary-600), var(--color-primary-800))" }}
          aria-hidden="true"
        >
          <Lock size={24} className="text-white" />
        </div>
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-bold text-[var(--color-text)]">{t("auth.passcodeTitle")}</h1>
          <p className="text-sm text-[var(--color-muted)]">{t("auth.passcodeSub")}</p>
        </div>
        <input
          type="password"
          inputMode="numeric"
          autoFocus
          value={passcode}
          onChange={(e) => setPasscode(e.target.value)}
          aria-label="Passcode"
          placeholder="••••"
          className="w-full min-h-11 px-3 text-center tracking-widest rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
        />
        {error && <p className="text-xs text-[var(--color-danger)]" role="alert">{error}</p>}
        <Button type="submit" loading={busy} disabled={!passcode.trim()} className="w-full">
          {t("auth.unlock")}
        </Button>
      </form>
    </div>
  );
};
