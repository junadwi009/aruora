import React, { useEffect, useState } from "react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

const SKILLS = ["listening", "reading", "writing", "speaking"] as const;
const BANDS = ["A1A2", "B1", "B2", "C1", "C2"] as const;
const TARGET_BANDS = [4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5];

export const TargetsSection: React.FC = () => {
  const { t } = useT();
  const [anon, setAnon] = useState(false);
  const [targetBand, setTargetBand] = useState(6.0);
  const [skillTargets, setSkillTargets] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.accountMe()
      .then((u) => { setTargetBand(u.targetBand ?? 6.0); setSkillTargets({ ...(u.skillTargets ?? {}) }); })
      .catch(() => setAnon(true));
  }, []);

  if (anon) {
    return (
      <Card>
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">{t("settings.targets")}</p>
        <p className="text-sm text-[var(--color-muted)]">{t("set.targetsAnon")}</p>
      </Card>
    );
  }

  const save = async () => {
    setBusy(true);
    setSaved(false);
    try {
      await api.accountProfile({ targetBand, skillTargets });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">{t("settings.targets")}</p>

      <label className="flex items-center justify-between gap-3">
        <span className="text-sm text-[var(--color-text)]">{t("set.targetsOverall")}</span>
        <select value={targetBand} onChange={(e) => setTargetBand(Number(e.target.value))}
          className="min-h-9 px-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]">
          {TARGET_BANDS.map((b) => <option key={b} value={b}>{b.toFixed(1)}</option>)}
        </select>
      </label>

      <div className="flex flex-col gap-2">
        <p className="text-xs text-[var(--color-muted)]">{t("set.targetsPerSkill")}</p>
        {SKILLS.map((sk) => (
          <label key={sk} className="flex items-center justify-between gap-3">
            <span className="text-sm capitalize text-[var(--color-text)]">{sk}</span>
            <select value={skillTargets[sk] ?? ""} onChange={(e) => setSkillTargets((t) => ({ ...t, [sk]: e.target.value }))}
              className="min-h-9 px-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]">
              <option value="">—</option>
              {BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Button onClick={save} loading={busy}>{t("set.saveTargets")}</Button>
        {saved && <span className="text-xs text-[var(--color-success)]">{t("common.saved")}</span>}
      </div>
    </Card>
  );
};
