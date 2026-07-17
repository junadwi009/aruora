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
        className="relative z-10 flex w-full max-w-md flex-col items-center gap-5 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8 text-center"
        style={{ boxShadow: "var(--shadow-premium-card)" }}
      >
        <div className="mb-2 flex flex-col items-center gap-3 text-center">
          <div
            className="flex h-14 w-14 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary-600)] text-white"
            style={{ boxShadow: "var(--shadow-premium)" }}
            aria-hidden="true"
          >
            <Lock size={26} />
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-display)" }}>
            {t("auth.passcodeTitle")}
          </h1>
          <p className="max-w-xs text-sm text-[var(--color-muted)]">{t("auth.passcodeSub")}</p>
        </div>
        <input
          type="password"
          inputMode="numeric"
          autoFocus
          value={passcode}
          onChange={(e) => setPasscode(e.target.value)}
          aria-label={t("auth.passcodeAria")}
          placeholder="••••"
          className="w-full min-h-11 px-4 text-center tracking-[0.5em] rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
        />
        {error && <p className="text-xs text-[var(--color-danger)]" role="alert">{error}</p>}
        <Button type="submit" pill loading={busy} disabled={!passcode.trim()} className="w-full">
          {t("auth.unlock")}
        </Button>
      </form>
    </div>
  );
};
