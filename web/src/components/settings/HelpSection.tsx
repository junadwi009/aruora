import React, { useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";
import { Card } from "../ui/Card";

const FAQ: { q: string; a: string }[] = [
  {
    q: "How does the placement test work?",
    a: "You answer Listening, Reading, Writing and Speaking tasks once. We estimate a CEFR level per skill and an overall band, then build a study plan around your weak skills.",
  },
  {
    q: "Why do bands say “estimate”?",
    a: "Reading/Listening bands come from short practice sets (not a full 40-question paper), and Writing/Speaking are AI-scored. Treat them as guidance, not an official IELTS result.",
  },
  {
    q: "Is speech recognition exact?",
    a: "No — pronunciation feedback is approximate (a browser recogniser plus AI tips), not phoneme-level scoring. Use it to spot patterns, not as a precise grade.",
  },
  {
    q: "Where is my data stored?",
    a: "Everything stays in this app’s own database, scoped to your account. Other accounts can’t see your attempts, cards or progress.",
  },
  {
    q: "Does the app work offline?",
    a: "The journey and practice run on built-in sample content with no internet. Generating fresh material and AI scoring need a connection.",
  },
];

export const HelpSection: React.FC = () => {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-center gap-2 mb-1">
        <HelpCircle size={16} className="text-[var(--color-muted)]" aria-hidden="true" />
        <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">Help</p>
      </div>
      {FAQ.map((item, i) => (
        <div key={i} className="border-b border-[var(--color-border)] last:border-0">
          <button type="button" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}
            className="w-full flex items-center justify-between gap-2 py-2.5 text-left min-h-11">
            <span className="text-sm font-medium text-[var(--color-text)]">{item.q}</span>
            <ChevronDown size={16} className={`shrink-0 text-[var(--color-muted)] transition-transform ${open === i ? "rotate-180" : ""}`} />
          </button>
          {open === i && <p className="text-sm text-[var(--color-muted)] leading-relaxed pb-3">{item.a}</p>}
        </div>
      ))}
    </Card>
  );
};
