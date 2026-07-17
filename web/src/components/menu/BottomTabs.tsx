import React from "react";
import { Home, BookOpen, ClipboardCheck, Lightbulb, LineChart } from "lucide-react";
import { useView, type View } from "./viewContext";
import { useT } from "../../lib/i18n";

interface TabEntry {
  view: View;
  tkey: string;
  icon: React.ReactNode;
}

const TABS: TabEntry[] = [
  { view: "home", tkey: "nav.home", icon: <Home size={20} aria-hidden="true" /> },
  { view: "reading", tkey: "nav.practice", icon: <BookOpen size={20} aria-hidden="true" /> },
  { view: "test", tkey: "nav.test", icon: <ClipboardCheck size={20} aria-hidden="true" /> },
  { view: "tips", tkey: "nav.tips", icon: <Lightbulb size={20} aria-hidden="true" /> },
  { view: "progress", tkey: "nav.progress", icon: <LineChart size={20} aria-hidden="true" /> },
];

export const BottomTabs: React.FC = () => {
  const { view, setView } = useView();
  const { t } = useT();

  return (
    <nav
      aria-label={t("menu.bottomNav")}
      className="fixed bottom-0 left-0 right-0 bg-[var(--color-surface)] border-t border-[var(--color-border)] pb-[env(safe-area-inset-bottom)] z-50"
      style={{ boxShadow: "0 -2px 12px -4px rgba(15,23,42,.10)" }}
    >
      <ul className="flex items-stretch" role="list">
        {TABS.map((tab) => {
          const isActive = view === tab.view;
          return (
            <li key={tab.view} className="flex-1 relative">
              {/* Active indicator bar at top */}
              {isActive && (
                <span
                  className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-[var(--color-primary-600)]"
                  aria-hidden="true"
                />
              )}
              <button
                onClick={() => setView(tab.view)}
                aria-current={isActive ? "page" : undefined}
                className={[
                  "w-full flex flex-col items-center justify-center gap-1 py-2 min-h-[56px] text-xs font-semibold",
                  "transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
                  isActive
                    ? "text-[var(--color-primary-600)]"
                    : "text-[var(--color-muted)] hover:text-[var(--color-text)]",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <span
                  className={[
                    "flex h-8 w-10 items-center justify-center rounded-full transition-colors",
                    isActive ? "bg-[color-mix(in_srgb,var(--color-primary-600)_12%,transparent)]" : "",
                  ].join(" ")}
                >
                  {tab.icon}
                </span>
                <span>{t(tab.tkey)}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};
