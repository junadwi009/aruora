import React, { useState } from "react";
import { Sun, Moon, LogOut, Settings2 } from "lucide-react";
import { api } from "../../lib/api/client";
import {
  getTheme, setTheme, getFont, setFont,
  type Theme, type Font,
} from "../../lib/settings";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";
import { ProfileSection } from "./ProfileSection";
import { TargetsSection } from "./TargetsSection";
import { SecuritySection } from "./SecuritySection";
import { MilestonesSection } from "./MilestonesSection";
import { RemindersSection } from "./RemindersSection";
import { DataSection } from "./DataSection";
import { HelpSection } from "./HelpSection";
import { AdminSection } from "./AdminSection";
import type { AccountUser } from "../../lib/types";

const FONTS: { value: Font; labelKey: string; hint: string }[] = [
  { value: "default", labelKey: "set.fontDefault", hint: "Inter · Lexend" },
  { value: "dyslexic", labelKey: "set.fontDyslexic", hint: "OpenDyslexic" },
  { value: "hyperlegible", labelKey: "set.fontHyper", hint: "Atkinson Hyperlegible" },
];

export const Settings: React.FC = () => {
  const { t, lang, setLang } = useT();
  const [theme, setThemeState] = useState<Theme>(getTheme());
  const [font, setFontState] = useState<Font>(getFont());
  const [account, setAccount] = useState<AccountUser | null>(null);
  const hasAccount = !!account?.email;

  React.useEffect(() => {
    api.accountMe().then(setAccount).catch(() => setAccount(null));
  }, []);

  const pickTheme = (t: Theme) => { setTheme(t); setThemeState(t); };
  const pickFont = (f: Font) => { setFont(f); setFontState(f); };

  const logout = async () => {
    try { await api.accountLogout(); } finally { window.location.reload(); }
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div
        className="sticky top-0 bg-[var(--color-surface)] border-b border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] px-4 md:px-6 py-4 z-10 flex items-center gap-3"
        style={{ boxShadow: "var(--shadow-e1)" }}
      >
        <div
          className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-lg)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] text-[var(--color-primary-600)]"
          aria-hidden="true"
        >
          <Settings2 size={20} />
        </div>
        <h1 style={{ fontFamily: "var(--font-display)" }} className="text-xl font-bold text-[var(--color-text)] tracking-tight">{t("settings.title")}</h1>
      </div>

      <div className="p-4 md:p-6 max-w-xl mx-auto flex flex-col gap-4">
        {/* Language */}
        <Card className="flex flex-col gap-3">
          <p className="text-sm font-semibold text-[var(--color-text)]">{t("settings.language")}</p>
          <div className="grid grid-cols-2 gap-2">
            <Button variant={lang === "en" ? "primary" : "secondary"} onClick={() => setLang("en")}>English</Button>
            <Button variant={lang === "id" ? "primary" : "secondary"} onClick={() => setLang("id")}>Bahasa Indonesia</Button>
          </div>
        </Card>

        {/* Theme */}
        <Card className="flex flex-col gap-3">
          <p className="text-sm font-semibold text-[var(--color-text)]">{t("settings.appearance")}</p>
          <div className="grid grid-cols-2 gap-2">
            <Button variant={theme === "light" ? "primary" : "secondary"} onClick={() => pickTheme("light")}>
              <Sun size={16} className="mr-1.5" /> {t("common.light")}
            </Button>
            <Button variant={theme === "dark" ? "primary" : "secondary"} onClick={() => pickTheme("dark")}>
              <Moon size={16} className="mr-1.5" /> {t("common.dark")}
            </Button>
          </div>
        </Card>

        {/* Font */}
        <Card className="flex flex-col gap-3">
          <p className="text-sm font-semibold text-[var(--color-text)]">{t("settings.font")}</p>
          <div className="flex flex-col gap-2">
            {FONTS.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => pickFont(f.value)}
                aria-pressed={font === f.value}
                className={[
                  "flex items-center justify-between px-3 py-2.5 rounded-[var(--radius-md)] border text-left min-h-11",
                  font === f.value
                    ? "border-[var(--color-primary-600)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)]"
                    : "border-[var(--color-border)]",
                ].join(" ")}
              >
                <span className="text-sm font-medium text-[var(--color-text)]">{t(f.labelKey)}</span>
                <span className="text-xs text-[var(--color-muted)]">{f.hint}</span>
              </button>
            ))}
          </div>
          <p className="text-[11px] text-[var(--color-muted)]">
            {t("set.fontHint")}
          </p>
        </Card>

        {/* Profile + photo */}
        <ProfileSection />

        {/* Band targets */}
        <TargetsSection />

        {/* Security — change password (or set one for Google-only accounts) */}
        <SecuritySection hasAccount={hasAccount} hasPassword={account?.hasPassword ?? true} />

        {/* Study reminder */}
        <RemindersSection />

        {/* Program milestones editor */}
        <MilestonesSection />

        {/* Data & privacy */}
        {hasAccount && <DataSection />}

        {/* Help / FAQ */}
        <HelpSection />

        {/* Master-admin (only when the account is in ADMIN_EMAILS) */}
        {account?.isAdmin && <AdminSection selfId={account.id} />}

        {/* Account */}
        {hasAccount && (
          <Card className="flex items-center justify-between">
            <p className="text-sm text-[var(--color-text)]">{t("set.signedIn")}</p>
            <Button variant="secondary" size="sm" onClick={logout}>
              <LogOut size={14} className="mr-1.5" /> {t("common.signOut")}
            </Button>
          </Card>
        )}
      </div>
    </main>
  );
};
