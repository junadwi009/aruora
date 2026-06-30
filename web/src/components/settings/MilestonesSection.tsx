import React, { useEffect, useState } from "react";
import { Plus, Trash2, Check } from "lucide-react";
import { api } from "../../lib/api/client";
import type { Milestone } from "../../lib/types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";

const SKILLS = ["listening", "reading", "writing", "speaking"] as const;
const BANDS = ["A1A2", "B1", "B2", "C1", "C2"] as const;

export const MilestonesSection: React.FC = () => {
  const [items, setItems] = useState<Milestone[] | null>(null);

  const load = () => api.milestones().then((m) => setItems(m)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  if (items === null) return <Card className="text-sm text-[var(--color-muted)]">Loading milestones…</Card>;

  if (items.length === 0) {
    return (
      <Card>
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">Milestones</p>
        <p className="text-sm text-[var(--color-muted)]">Choose a program first to set milestones.</p>
      </Card>
    );
  }

  const addMilestone = async () => {
    await api.milestoneAdd({ title: "New milestone", dayTarget: 30, targets: {} });
    load();
  };

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">Milestones</p>
        <Button variant="secondary" size="sm" onClick={addMilestone}><Plus size={14} className="mr-1" /> Add</Button>
      </div>
      <ul className="flex flex-col gap-3">
        {items.map((m) => (
          <MilestoneRow key={m.id} m={m} onChanged={load} />
        ))}
      </ul>
    </Card>
  );
};

const MilestoneRow: React.FC<{ m: Milestone; onChanged: () => void }> = ({ m, onChanged }) => {
  const [title, setTitle] = useState(m.title);
  const [dayTarget, setDayTarget] = useState(m.dayTarget);
  const [targets, setTargets] = useState<Record<string, string>>({ ...m.targets });
  const [saved, setSaved] = useState(false);

  const save = async () => {
    if (m.id == null) return;
    await api.milestoneUpdate(m.id, { title, dayTarget, targets });
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
    onChanged();
  };
  const remove = async () => {
    if (m.id == null) return;
    await api.milestoneDelete(m.id);
    onChanged();
  };

  return (
    <li className="flex flex-col gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">
      <div className="flex gap-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)} aria-label="Milestone title"
          className="flex-1 min-h-9 px-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)]" />
        <input type="number" value={dayTarget} onChange={(e) => setDayTarget(Number(e.target.value))} aria-label="Day target"
          className="w-20 min-h-9 px-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)]" />
      </div>
      <div className="flex flex-wrap gap-2">
        {SKILLS.map((sk) => (
          <label key={sk} className="flex items-center gap-1 text-xs text-[var(--color-muted)]">
            <span className="capitalize w-16">{sk}</span>
            <select value={targets[sk] ?? ""} onChange={(e) => setTargets((t) => ({ ...t, [sk]: e.target.value }))}
              className="min-h-8 px-1 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]">
              <option value="">—</option>
              {BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" onClick={save}>{saved ? <><Check size={14} className="mr-1" />Saved</> : "Save"}</Button>
        <Button variant="ghost" size="sm" onClick={remove} aria-label="Delete milestone"><Trash2 size={14} /></Button>
      </div>
    </li>
  );
};
