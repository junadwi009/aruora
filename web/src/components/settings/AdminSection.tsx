import React, { useEffect, useState } from "react";
import { ShieldCheck, Trash2, KeyRound } from "lucide-react";
import { api } from "../../lib/api/client";
import type { AdminUser, AdminStats } from "../../lib/types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

/**
 * Master-admin panel. Only rendered when the signed-in account is in
 * ADMIN_EMAILS (the parent gates on `user.isAdmin`); every endpoint is also
 * server-enforced, so this is a convenience surface, not a security boundary.
 */
export const AdminSection: React.FC<{ selfId: number }> = ({ selfId }) => {
  const { t } = useT();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [flash, setFlash] = useState<string>("");

  const load = () => {
    api.adminUsers().then(setUsers).catch(() => setUsers([]));
    api.adminStats().then(setStats).catch(() => setStats(null));
  };
  useEffect(load, []);

  const remove = async (u: AdminUser) => {
    if (!window.confirm(t("admin.confirmDelete"))) return;
    setBusy(u.id);
    try { await api.adminDeleteUser(u.id); load(); }
    finally { setBusy(null); }
  };

  const resetPw = async (u: AdminUser) => {
    setBusy(u.id);
    try { await api.adminResetUser(u.id); setFlash(t("admin.resetSent")); setTimeout(() => setFlash(""), 2500); }
    finally { setBusy(null); }
  };

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <ShieldCheck size={16} className="text-[var(--color-primary-600)]" />
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">{t("admin.title")}</p>
      </div>
      <p className="text-sm text-[var(--color-muted)]">{t("admin.sub")}</p>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: t("admin.accounts"), value: stats.totalAccounts },
            { label: t("admin.attempts"), value: stats.totalAttempts },
            { label: t("admin.anon"), value: stats.anonymousProfiles },
          ].map((s) => (
            <div key={s.label} className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-2 text-center">
              <div className="text-lg font-semibold text-[var(--color-text)] tabular-nums">{s.value}</div>
              <div className="text-[11px] text-[var(--color-muted)]">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {flash && <p className="text-xs text-[var(--color-primary-600)]" role="status">{flash}</p>}

      {/* User list */}
      {users === null ? (
        <p className="text-sm text-[var(--color-muted)]">{t("common.loading")}</p>
      ) : users.length === 0 ? (
        <p className="text-sm text-[var(--color-muted)]">{t("admin.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {users.map((u) => (
            <li key={u.id} className="flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] p-2.5">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-sm font-medium text-[var(--color-text)] truncate">{u.email}</span>
                  {u.id === selfId && (
                    <span className="text-[10px] uppercase tracking-wide text-[var(--color-primary-600)] border border-[var(--color-primary-600)] rounded px-1">{t("admin.you")}</span>
                  )}
                </div>
                <div className="text-[11px] text-[var(--color-muted)]">
                  {u.name || "—"} · {u.attempts} {t("admin.attempts").toLowerCase()}
                </div>
              </div>
              <Button variant="ghost" size="sm" disabled={busy === u.id} onClick={() => resetPw(u)}
                aria-label={`${t("admin.resetPw")} — ${u.email}`} title={t("admin.resetPw")}>
                <KeyRound size={14} />
              </Button>
              {u.id !== selfId && (
                <Button variant="ghost" size="sm" disabled={busy === u.id} onClick={() => remove(u)}
                  aria-label={`${t("admin.delete")} — ${u.email}`} title={t("admin.delete")}>
                  <Trash2 size={14} className="text-[var(--color-danger,#dc2626)]" />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
};
