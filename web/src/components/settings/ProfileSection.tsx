import React, { useEffect, useRef, useState } from "react";
import { UserRound, Upload } from "lucide-react";
import { api } from "../../lib/api/client";
import type { AccountUser } from "../../lib/types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

export const ProfileSection: React.FC = () => {
  const { t } = useT();
  const [user, setUser] = useState<AccountUser | null>(null);
  const [anon, setAnon] = useState(false);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [examDate, setExamDate] = useState("");
  const [bio, setBio] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = (u: AccountUser) => {
    setUser(u);
    setName(u.name ?? "");
    setCountry(u.country ?? "");
    setExamDate(u.examDate ?? "");
    setBio(u.bio ?? "");
  };

  useEffect(() => {
    api.accountMe().then(load).catch(() => setAnon(true));
  }, []);

  if (anon) {
    return (
      <Card>
        <p className="text-sm font-semibold text-[var(--color-text)] mb-2">{t("settings.profile")}</p>
        <p className="text-sm text-[var(--color-muted)]">{t("set.profileAnon")}</p>
      </Card>
    );
  }
  if (!user) return <Card className="text-sm text-[var(--color-muted)]">{t("set.loadingProfile")}</Card>;

  const save = async () => {
    setBusy(true);
    setSaved(false);
    try {
      const updated = await api.accountProfile({ name, country, examDate, bio });
      load(updated);
      setSaved(true);
    } finally {
      setBusy(false);
    }
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 2_000_000) { alert(t("set.imageTooLarge")); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      const dataUrl = String(reader.result);
      await api.accountAvatar(dataUrl);
      setUser((u) => (u ? { ...u, avatar: dataUrl } : u));
    };
    reader.readAsDataURL(f);
  };

  return (
    <Card className="flex flex-col gap-3">
      <p className="text-sm font-semibold text-[var(--color-text)]">{t("settings.profile")}</p>

      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-full overflow-hidden bg-[var(--color-surface-2)] flex items-center justify-center shrink-0">
          {user.avatar ? (
            <img src={user.avatar} alt={t("set.avatarAlt")} className="w-full h-full object-cover" />
          ) : (
            <UserRound size={28} className="text-[var(--color-muted)]" aria-hidden="true" />
          )}
        </div>
        <div>
          <Button variant="secondary" size="sm" onClick={() => fileRef.current?.click()}>
            <Upload size={14} className="mr-1.5" /> {t("set.uploadPhoto")}
          </Button>
          <input ref={fileRef} type="file" accept="image/*" onChange={onFile} className="hidden" aria-label={t("set.profilePhoto")} />
          <p className="text-[11px] text-[var(--color-muted)] mt-1">{t("set.photoHint")}</p>
        </div>
      </div>

      <Field label={t("set.displayName")} value={name} onChange={setName} placeholder={t("set.yourName")} />
      <Field label={t("set.country")} value={country} onChange={setCountry} placeholder={t("set.countryEg")} />
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-[var(--color-muted)]">{t("set.examDate")}</span>
        <input type="date" value={examDate} onChange={(e) => setExamDate(e.target.value)}
          className="min-h-10 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]" />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-[var(--color-muted)]">{t("set.notes")}</span>
        <textarea value={bio} onChange={(e) => setBio(e.target.value)} rows={2} placeholder={t("set.notesPlaceholder")}
          className="px-3 py-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)]" />
      </label>

      <div className="flex items-center gap-3">
        <Button onClick={save} loading={busy}>{t("set.saveProfile")}</Button>
        {saved && <span className="text-xs text-[var(--color-success)]">{t("common.saved")}</span>}
      </div>
    </Card>
  );
};

const Field: React.FC<{ label: string; value: string; onChange: (v: string) => void; placeholder?: string }> = ({
  label, value, onChange, placeholder,
}) => (
  <label className="flex flex-col gap-1">
    <span className="text-xs font-medium text-[var(--color-muted)]">{label}</span>
    <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
      className="min-h-10 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]" />
  </label>
);
