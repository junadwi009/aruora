import React from "react";
import {
  Home,
  BookOpen,
  Headphones,
  Mic,
  PenLine,
  ClipboardCheck,
  Lightbulb,
  LineChart,
  Settings,
  Volume2,
  Layers,
} from "lucide-react";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { useView, type View } from "./viewContext";
import { useT } from "../../lib/i18n";

interface SidebarProps {
  levels: Record<string, CefrBand>;
}

interface NavEntry {
  view: View;
  icon: React.ReactNode;
  skill?: string;
}

// Labels are rendered via t("nav." + view) below — no static label needed here.
const NAV_ENTRIES: NavEntry[] = [
  { view: "home", icon: <Home size={18} aria-hidden="true" /> },
  { view: "reading", icon: <BookOpen size={18} aria-hidden="true" />, skill: "reading" },
  { view: "listening", icon: <Headphones size={18} aria-hidden="true" />, skill: "listening" },
  { view: "speaking", icon: <Mic size={18} aria-hidden="true" />, skill: "speaking" },
  { view: "writing", icon: <PenLine size={18} aria-hidden="true" />, skill: "writing" },
  { view: "pronounce", icon: <Volume2 size={18} aria-hidden="true" /> },
  { view: "vocab", icon: <Layers size={18} aria-hidden="true" /> },
  { view: "test", icon: <ClipboardCheck size={18} aria-hidden="true" /> },
  { view: "tips", icon: <Lightbulb size={18} aria-hidden="true" /> },
  { view: "progress", icon: <LineChart size={18} aria-hidden="true" /> },
];

export const Sidebar: React.FC<SidebarProps> = ({ levels }) => {
  const { view, setView } = useView();
  const { t } = useT();

  return (
    <nav
      aria-label={t("menu.mainNav")}
      className="flex flex-col h-full w-64 bg-[var(--color-surface)] border-r border-[var(--color-border)] py-4"
      style={{ boxShadow: "var(--shadow-e1)" }}
    >
      {/* Brand mark — solid ink, display wordmark (no gradient fingerprint) */}
      <div className="px-4 mb-7 flex items-center gap-2.5">
        <div
          className="flex items-center justify-center w-9 h-9 rounded-[var(--radius-md)] shrink-0 bg-[var(--color-text)]"
          style={{ boxShadow: "var(--shadow-e1)" }}
          aria-hidden="true"
        >
          <BookOpen size={16} className="text-[var(--color-surface)]" />
        </div>
        <span
          className="text-lg font-bold text-[var(--color-text)] tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          IELTS Coach
        </span>
      </div>

      <ul className="flex-1 flex flex-col gap-0.5 px-2" role="list">
        {NAV_ENTRIES.map((entry) => {
          const isActive = view === entry.view;
          const band = entry.skill ? levels[entry.skill] : undefined;
          return (
            <li key={entry.view}>
              <button
                onClick={() => setView(entry.view)}
                aria-current={isActive ? "page" : undefined}
                className={[
                  "relative w-full flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] text-sm",
                  "transition-[background-color,color] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
                  "min-h-[44px]",
                  isActive
                    ? "font-semibold text-[var(--color-text)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)]"
                    : "font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)]",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {isActive && (
                  <span
                    aria-hidden="true"
                    className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-full bg-[var(--color-primary-600)]"
                  />
                )}
                {entry.icon}
                <span className="flex-1 text-left">{t("nav." + entry.view)}</span>
                {band && <LevelChip band={band} />}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="px-2 mt-auto pt-2 border-t border-[var(--color-border)]">
        <button
          onClick={() => setView("settings")}
          aria-current={view === "settings" ? "page" : undefined}
          className={[
            "relative w-full flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] text-sm",
            "transition-[background-color,color] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
            "min-h-[44px]",
            view === "settings"
              ? "font-semibold text-[var(--color-text)] bg-[color-mix(in_srgb,var(--color-primary-600)_8%,transparent)]"
              : "font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)]",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {view === "settings" && (
            <span
              aria-hidden="true"
              className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-full bg-[var(--color-primary-600)]"
            />
          )}
          <Settings size={18} aria-hidden="true" />
          <span className="flex-1 text-left">{t("nav.settings")}</span>
        </button>
      </div>
    </nav>
  );
};
