import React, { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

const HOURS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);

// A curated spread of IANA zones; the learner's detected zone is added on top.
const COMMON_TZ = [
  "Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura", "Asia/Singapore", "Asia/Kuala_Lumpur",
  "Asia/Bangkok", "Asia/Ho_Chi_Minh", "Asia/Manila", "Asia/Hong_Kong", "Asia/Shanghai",
  "Asia/Tokyo", "Asia/Seoul", "Asia/Kolkata", "Asia/Dubai", "Asia/Riyadh",
  "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow",
  "Australia/Perth", "Australia/Sydney", "Pacific/Auckland",
  "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Sao_Paulo",
  "UTC",
];

function detectTz(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Jakarta";
  } catch {
    return "Asia/Jakarta";
  }
}

export const RemindersSection: React.FC = () => {
  const { t } = useT();
  const [anon, setAnon] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [time, setTime] = useState("09:00");
  const [tz, setTz] = useState(detectTz());
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.accountMe()
      .then((u) => {
        if (u.reminderTime) { setEnabled(true); setTime(u.reminderTime); }
        if (u.reminderTz) setTz(u.reminderTz);
      })
      .catch(() => setAnon(true));
  }, []);

  if (anon) return null;

  // Ensure the detected/saved zone is selectable even if not in the curated list.
  const zones = COMMON_TZ.includes(tz) ? COMMON_TZ : [tz, ...COMMON_TZ];

  const save = async () => {
    setBusy(true);
    setSaved(false);
    try {
      await api.accountProfile({
        reminderTime: enabled ? time : null,
        reminderTz: enabled ? tz : null,
      });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Bell size={16} className="text-[var(--color-muted)]" aria-hidden="true" />
        <p className="text-sm font-semibold text-[var(--color-text)]">{t("set.reminder")}</p>
      </div>

      <label className="flex items-center justify-between gap-3">
        <span className="text-sm text-[var(--color-text)]">{t("set.reminderDaily")}</span>
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} aria-label={t("set.enableReminder")} className="w-5 h-5" />
      </label>

      {enabled && (
        <label className="flex items-center justify-between gap-3">
          <span className="text-sm text-[var(--color-text)]">{t("set.time")}</span>
          <select value={time} onChange={(e) => setTime(e.target.value)}
            className="min-h-9 px-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]">
            {HOURS.map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        </label>
      )}

      {enabled && (
        <label className="flex items-center justify-between gap-3">
          <span className="text-sm text-[var(--color-text)]">{t("set.timezone")}</span>
          <select value={tz} onChange={(e) => setTz(e.target.value)} aria-label={t("set.timezone")}
            className="min-h-9 px-2 max-w-[60%] rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]">
            {zones.map((z) => <option key={z} value={z}>{z.replace(/_/g, " ")}</option>)}
          </select>
        </label>
      )}

      <p className="text-[11px] text-[var(--color-muted)]">
        {t("set.reminderHint")}
      </p>

      <div className="flex items-center gap-3">
        <Button onClick={save} loading={busy}>{t("set.saveReminder")}</Button>
        {saved && <span className="text-xs text-[var(--color-success)]">{t("common.saved")}</span>}
      </div>
    </Card>
  );
};
