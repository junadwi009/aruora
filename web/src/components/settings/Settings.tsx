import React, { useState } from "react";
import { Sun, Moon, LogOut } from "lucide-react";
import { api } from "../../lib/api/client";
import {
  getTheme, setTheme, getFont, setFont,
  type Theme, type Font,
} from "../../lib/settings";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { ProfileSection } from "./ProfileSection";
import { SecuritySection } from "./SecuritySection";
import { MilestonesSection } from "./MilestonesSection";
import { HelpSection } from "./HelpSection";

const FONTS: { value: Font; label: string; hint: string }[] = [
  { value: "default", label: "Default", hint: "Inter · Lexend" },
  { value: "dyslexic", label: "Dyslexia-friendly", hint: "OpenDyslexic" },
  { value: "hyperlegible", label: "Hyperlegible", hint: "Atkinson Hyperlegible" },
];

export const Settings: React.FC = () => {
  const [theme, setThemeState] = useState<Theme>(getTheme());
  const [font, setFontState] = useState<Font>(getFont());
  const [hasAccount, setHasAccount] = useState(false);

  React.useEffect(() => {
    api.accountMe().then((u) => setHasAccount(!!u.email)).catch(() => setHasAccount(false));
  }, []);

  const pickTheme = (t: Theme) => { setTheme(t); setThemeState(t); };
  const pickFont = (f: Font) => { setFont(f); setFontState(f); };

  const logout = async () => {
    try { await api.accountLogout(); } finally { window.location.reload(); }
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10">
        <h1 className="text-base font-semibold text-[var(--color-text)]">Settings</h1>
      </div>

      <div className="p-4 md:p-6 max-w-xl mx-auto flex flex-col gap-4">
        {/* Theme */}
        <Card className="flex flex-col gap-3">
          <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">Appearance</p>
          <div className="grid grid-cols-2 gap-2">
            <Button variant={theme === "light" ? "primary" : "secondary"} onClick={() => pickTheme("light")}>
              <Sun size={16} className="mr-1.5" /> Light
            </Button>
            <Button variant={theme === "dark" ? "primary" : "secondary"} onClick={() => pickTheme("dark")}>
              <Moon size={16} className="mr-1.5" /> Dark
            </Button>
          </div>
        </Card>

        {/* Font */}
        <Card className="flex flex-col gap-3">
          <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">Reading font</p>
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
                <span className="text-sm font-medium text-[var(--color-text)]">{f.label}</span>
                <span className="text-xs text-[var(--color-muted)]">{f.hint}</span>
              </button>
            ))}
          </div>
          <p className="text-[11px] text-[var(--color-muted)]">
            Dyslexia-friendly and Hyperlegible improve readability for some learners.
          </p>
        </Card>

        {/* Profile + photo */}
        <ProfileSection />

        {/* Security — change password */}
        <SecuritySection hasAccount={hasAccount} />

        {/* Program milestones editor */}
        <MilestonesSection />

        {/* Help / FAQ */}
        <HelpSection />

        {/* Account */}
        {hasAccount && (
          <Card className="flex items-center justify-between">
            <p className="text-sm text-[var(--color-text)]">Signed in</p>
            <Button variant="secondary" size="sm" onClick={logout}>
              <LogOut size={14} className="mr-1.5" /> Sign out
            </Button>
          </Card>
        )}
      </div>
    </main>
  );
};
