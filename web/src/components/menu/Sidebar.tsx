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
  label: string;
  icon: React.ReactNode;
  skill?: string;
}

const NAV_ENTRIES: NavEntry[] = [
  { view: "home", label: "Home", icon: <Home size={18} aria-hidden="true" /> },
  { view: "reading", label: "Reading", icon: <BookOpen size={18} aria-hidden="true" />, skill: "reading" },
  { view: "listening", label: "Listening", icon: <Headphones size={18} aria-hidden="true" />, skill: "listening" },
  { view: "speaking", label: "Speaking", icon: <Mic size={18} aria-hidden="true" />, skill: "speaking" },
  { view: "writing", label: "Writing", icon: <PenLine size={18} aria-hidden="true" />, skill: "writing" },
  { view: "pronounce", label: "Pronounce", icon: <Volume2 size={18} aria-hidden="true" /> },
  { view: "vocab", label: "Vocab", icon: <Layers size={18} aria-hidden="true" /> },
  { view: "test", label: "Test", icon: <ClipboardCheck size={18} aria-hidden="true" /> },
  { view: "tips", label: "Tips", icon: <Lightbulb size={18} aria-hidden="true" /> },
  { view: "progress", label: "Progress", icon: <LineChart size={18} aria-hidden="true" /> },
];

export const Sidebar: React.FC<SidebarProps> = ({ levels }) => {
  const { view, setView } = useView();
  const { t } = useT();

  return (
    <nav
      aria-label="Main navigation"
      className="flex flex-col h-full w-64 bg-[var(--color-surface)] border-r border-[var(--color-border)] py-4"
      style={{ boxShadow: "var(--shadow-e1)" }}
    >
      {/* Brand mark */}
      <div className="px-4 mb-6 flex items-center gap-2.5">
        <div
          className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] shrink-0"
          style={{
            background: "linear-gradient(135deg, var(--color-primary-600), var(--color-primary-800))",
            boxShadow: "var(--shadow-e2)",
          }}
          aria-hidden="true"
        >
          <BookOpen size={14} className="text-white" />
        </div>
        <span className="text-sm font-bold text-[var(--color-text)] tracking-tight">IELTS Coach</span>
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
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] text-sm font-medium",
                  "transition-[background-color,color] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
                  "min-h-[44px]",
                  isActive
                    ? "bg-[var(--color-primary-50)] text-[var(--color-primary-700)]"
                    : "text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)]",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
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
            "w-full flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] text-sm font-medium",
            "transition-[background-color,color] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
            "min-h-[44px]",
            view === "settings"
              ? "bg-[var(--color-primary-50)] text-[var(--color-primary-700)]"
              : "text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)]",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <Settings size={18} aria-hidden="true" />
          <span className="flex-1 text-left">{t("nav.settings")}</span>
        </button>
      </div>
    </nav>
  );
};
