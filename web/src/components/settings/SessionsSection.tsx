import React, { useEffect, useState } from "react";
import { MonitorSmartphone, LogOut } from "lucide-react";
import { api } from "../../lib/api/client";
import type { AccountSession } from "../../lib/types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

function shortDevice(ua: string): string {
  if (!ua) return "Browser";
  const os = /Windows/i.test(ua)
    ? "Windows"
    : /Android/i.test(ua)
      ? "Android"
      : /iPhone|iPad|iOS/i.test(ua)
        ? "iOS"
        : /Mac OS X/i.test(ua)
          ? "macOS"
          : /Linux/i.test(ua)
            ? "Linux"
            : "";
  const browser = /Edg\//i.test(ua)
    ? "Edge"
    : /Chrome\//i.test(ua)
      ? "Chrome"
      : /Safari\//i.test(ua)
        ? "Safari"
        : /Firefox\//i.test(ua)
          ? "Firefox"
          : "";
  return [browser, os].filter(Boolean).join(" · ") || "Browser";
}

/** WS03-09 — "Devices & sessions": see active sessions and revoke them. */
export const SessionsSection: React.FC = () => {
  const { t } = useT();
  const [rows, setRows] = useState<AccountSession[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.accountSessions().then(setRows).catch(() => setRows(null));
  };
  useEffect(load, []);

  const revokeOthers = async () => {
    setBusy(true);
    try {
      await api.accountRevokeOtherSessions();
      load();
    } finally {
      setBusy(false);
    }
  };

  const revokeAll = async () => {
    setBusy(true);
    try {
      await api.accountRevokeAllSessions();
    } catch {
      // even if the call failed, the server may have revoked: reload to auth
    } finally {
      window.location.reload(); // this session may be dead either way
    }
  };

  if (rows === null) return null; // section only shows for signed-in accounts

  return (
    <Card className="flex flex-col gap-3">
      <p className="text-sm font-semibold text-[var(--color-text)]">{t("set.sessionsTitle")}</p>
      <ul className="flex flex-col gap-2">
        {rows.map((s, i) => (
          <li
            key={i}
            className="flex items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2"
          >
            <span className="flex items-center gap-2 min-w-0">
              <MonitorSmartphone size={16} className="shrink-0 text-[var(--color-muted)]" aria-hidden="true" />
              <span className="text-sm text-[var(--color-text)] truncate">
                {shortDevice(s.device)}
                {s.current && <span className="ml-2 text-xs text-[var(--color-primary-700)] font-semibold">{t("set.sessionCurrent")}</span>}
              </span>
            </span>
            <span className="text-[11px] text-[var(--color-muted)] shrink-0">
              {s.lastSeenAt ? new Date(s.lastSeenAt).toLocaleDateString() : ""}
            </span>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        {rows.length > 1 && (
          <Button variant="secondary" size="sm" onClick={revokeOthers} loading={busy}>
            <LogOut size={14} className="mr-1.5" /> {t("set.sessionsRevokeOthers")}
          </Button>
        )}
        <Button variant="secondary" size="sm" onClick={revokeAll} loading={busy}>
          {t("set.sessionsRevokeAll")}
        </Button>
      </div>
      <p className="text-[11px] text-[var(--color-muted)]">{t("set.sessionsHint")}</p>
    </Card>
  );
};
