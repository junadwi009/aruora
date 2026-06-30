import React, { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

const HOURS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);

export const RemindersSection: React.FC = () => {
  const { t } = useT();
  const [anon, setAnon] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [time, setTime] = useState("09:00");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.accountMe()
      .then((u) => { if (u.reminderTime) { setEnabled(true); setTime(u.reminderTime); } })
      .catch(() => setAnon(true));
  }, []);

  if (anon) return null;

  const save = async () => {
    setBusy(true);
    setSaved(false);
    try {
      await api.accountProfile({ reminderTime: enabled ? time : null });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Bell size={16} className="text-[var(--color-muted)]" aria-hidden="true" />
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">{t("set.reminder")}</p>
      </div>

      <label className="flex items-center justify-between gap-3">
        <span className="text-sm text-[var(--color-text)]">Daily email reminder</span>
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} aria-label="Enable reminder" className="w-5 h-5" />
      </label>

      {enabled && (
        <label className="flex items-center justify-between gap-3">
          <span className="text-sm text-[var(--color-text)]">Time</span>
          <select value={time} onChange={(e) => setTime(e.target.value)}
            className="min-h-9 px-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]">
            {HOURS.map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        </label>
      )}

      <p className="text-[11px] text-[var(--color-muted)]">
        Emails require SMTP on the server; the time is by the server's clock.
      </p>

      <div className="flex items-center gap-3">
        <Button onClick={save} loading={busy}>Save reminder</Button>
        {saved && <span className="text-xs text-[var(--color-success)]">Saved</span>}
      </div>
    </Card>
  );
};
