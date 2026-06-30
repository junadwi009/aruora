import React, { useState } from "react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

export const SecuritySection: React.FC<{ hasAccount: boolean }> = ({ hasAccount }) => {
  const { t } = useT();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next.length < 6) { setMsg({ ok: false, text: "New password must be at least 6 characters." }); return; }
    setBusy(true);
    setMsg(null);
    try {
      await api.accountPassword({ currentPassword: current, newPassword: next });
      setMsg({ ok: true, text: "Password changed." });
      setCurrent(""); setNext("");
    } catch (err) {
      setMsg({ ok: false, text: err instanceof Error ? err.message : "Could not change password." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">{t("settings.security")}</p>
      {!hasAccount ? (
        <p className="text-sm text-[var(--color-muted)]">Register an email/password account to set a password.</p>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)}
            placeholder="Current password"
            className="min-h-10 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]" />
          <input type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)}
            placeholder="New password (min 6 chars)"
            className="min-h-10 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]" />
          {msg && <p className={`text-xs ${msg.ok ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}`} role="status">{msg.text}</p>}
          <Button type="submit" loading={busy} disabled={!current || !next} className="self-start">Change password</Button>
        </form>
      )}
    </Card>
  );
};
