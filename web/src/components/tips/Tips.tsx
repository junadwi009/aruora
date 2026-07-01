import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import { api } from "../../lib/api/client";
import type { Tips as TipsData } from "../../lib/types";
import { useT } from "../../lib/i18n";
import { Card } from "../ui/Card";
import { TipsSidePanel } from "./TipsSidePanel";

const SKILLS = ["reading", "listening", "writing", "speaking"] as const;
type Skill = (typeof SKILLS)[number];

const SKILL_LABEL_KEYS: Record<Skill, string> = {
  reading: "nav.reading",
  listening: "nav.listening",
  writing: "nav.writing",
  speaking: "nav.speaking",
};

interface AccordionState {
  open: boolean;
  data: TipsData | null;
  loading: boolean;
  error: string | null;
}

export const Tips: React.FC = () => {
  const { t } = useT();
  const [sections, setSections] = useState<Record<Skill, AccordionState>>(() =>
    Object.fromEntries(
      SKILLS.map((s) => [s, { open: false, data: null, loading: false, error: null }])
    ) as Record<Skill, AccordionState>
  );

  const toggleSection = (skill: Skill) => {
    const section = sections[skill];
    const nowOpen = !section.open;

    // If opening for the first time and no data yet, fetch
    if (nowOpen && !section.data && !section.loading) {
      setSections((prev) => ({
        ...prev,
        [skill]: { ...prev[skill], open: true, loading: true },
      }));
      api
        .tips(skill)
        .then((data) => {
          setSections((prev) => ({
            ...prev,
            [skill]: { open: true, data, loading: false, error: null },
          }));
        })
        .catch((e: unknown) => {
          setSections((prev) => ({
            ...prev,
            [skill]: {
              ...prev[skill],
              loading: false,
              error: e instanceof Error ? e.message : t("tips.loadError"),
            },
          }));
        });
    } else {
      setSections((prev) => ({
        ...prev,
        [skill]: { ...prev[skill], open: nowOpen },
      }));
    }
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 md:px-6 py-3 z-10"
        style={{ boxShadow: "var(--shadow-e1)" }}
      >
        <h1 className="text-base font-semibold text-[var(--color-text)] tracking-tight">{t("nav.tips")}</h1>
      </div>

      <div className="p-4 md:p-6 flex flex-col xl:flex-row gap-6 items-start">
      <div className="w-full max-w-2xl flex flex-col gap-3">
        {SKILLS.map((skill) => {
          const section = sections[skill];
          const headingId = `tips-heading-${skill}`;
          const panelId = `tips-panel-${skill}`;

          return (
            <Card key={skill} className="p-0 overflow-hidden">
              {/* Accordion trigger — rounded header, chevron rotate */}
              <button
                type="button"
                id={headingId}
                aria-expanded={section.open}
                aria-controls={panelId}
                onClick={() => toggleSection(skill)}
                className={[
                  "w-full flex items-center justify-between px-5 py-4",
                  "text-sm font-semibold text-[var(--color-text)] transition-colors",
                  "hover:bg-[var(--color-surface-2)]",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
                ].join(" ")}
              >
                <span>{t(SKILL_LABEL_KEYS[skill])}</span>
                <ChevronDown
                  size={16}
                  aria-hidden="true"
                  className={[
                    "text-[var(--color-muted)] transition-transform",
                    section.open ? "rotate-180" : "",
                  ].join(" ")}
                />
              </button>

              {/* Accordion panel */}
              {section.open && (
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={headingId}
                  className="px-5 pb-5 border-t border-[var(--color-border)]"
                >
                  {section.loading && (
                    <p className="text-xs text-[var(--color-muted)] pt-4">{t("common.loading")}</p>
                  )}
                  {section.error && (
                    <p className="text-xs text-[var(--color-danger)] pt-4">{section.error}</p>
                  )}
                  {section.data && (
                    <div className="pt-4">
                      {section.data.title && (
                        <p className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-widest mb-3">
                          {section.data.title}
                        </p>
                      )}
                      <ul className="flex flex-col gap-2.5">
                        {section.data.bullets.map((bullet, i) => (
                          <li
                            key={i}
                            className="flex gap-3 text-sm text-[var(--color-text)] leading-relaxed"
                            style={{ fontFamily: "var(--font-reading)" }}
                          >
                            <span className="shrink-0 mt-1.5 w-1.5 h-1.5 rounded-full bg-[var(--color-primary-600)]" aria-hidden="true" />
                            <span>{bullet}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      <TipsSidePanel />
      </div>
    </main>
  );
};
