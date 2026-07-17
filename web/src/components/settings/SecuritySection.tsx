import React, { useState } from "react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { PasswordInput } from "../ui/PasswordInput";
import { useT } from "../../lib/i18n";

export const SecuritySection: React.FC<{ hasAccount: boolean; hasPassword?: boolean }> = ({
  hasAccount,
  hasPassword = true,
}) => {
  const { t } = useT();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  // Once a Google-only user sets their first password, switch to change mode.
  const [passwordSet, setPasswordSet] = useState(false);

  // "Set password" mode: signed-in account with no local password yet (Google).
  const setMode = hasAccount && !hasPassword && !passwordSet;

  const inputCls =
    "min-h-10 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next.length < 8) { setMsg({ ok: false, text: t("set.passwordMinChars") }); return; }
    setBusy(true);
    setMsg(null);
    try {
      // In set mode there is no current password to send.
      await api.accountPassword({ currentPassword: setMode ? "" : current, newPassword: next });
      setMsg({ ok: true, text: setMode ? t("set.passwordSetDone") : t("set.passwordChanged") });
      setCurrent(""); setNext("");
      if (setMode) setPasswordSet(true);
    } catch (err) {
      setMsg({ ok: false, text: err instanceof Error ? err.message : t("set.passwordChangeError") });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <p className="text-sm font-semibold text-[var(--color-text)]">{t("settings.security")}</p>
      {!hasAccount ? (
        <p className="text-sm text-[var(--color-muted)]">{t("set.securityAnon")}</p>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          {setMode ? (
            <p className="text-sm text-[var(--color-muted)]">{t("set.setPasswordHint")}</p>
          ) : (
            <PasswordInput autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)}
              placeholder={t("set.currentPassword")}
              className={inputCls} />
          )}
          <PasswordInput autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)}
            placeholder={t("set.newPassword")}
            className={inputCls} />
          {msg && <p className={`text-xs ${msg.ok ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}`} role="status">{msg.text}</p>}
          <Button type="submit" loading={busy} disabled={setMode ? !next : (!current || !next)} className="self-start">
            {setMode ? t("set.setPassword") : t("set.changePassword")}
          </Button>
        </form>
      )}
    </Card>
  );
};
