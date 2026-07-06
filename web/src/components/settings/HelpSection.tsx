import React, { useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";
import { Card } from "../ui/Card";
import { useT } from "../../lib/i18n";

const FAQ: { qKey: string; aKey: string }[] = [
  { qKey: "set.faqQ1", aKey: "set.faqA1" },
  { qKey: "set.faqQ2", aKey: "set.faqA2" },
  { qKey: "set.faqQ3", aKey: "set.faqA3" },
  { qKey: "set.faqQ4", aKey: "set.faqA4" },
  { qKey: "set.faqQ5", aKey: "set.faqA5" },
];

export const HelpSection: React.FC = () => {
  const { t } = useT();
  const [open, setOpen] = useState<number | null>(null);
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-center gap-2 mb-1">
        <HelpCircle size={16} className="text-[var(--color-muted)]" aria-hidden="true" />
        <p className="text-sm font-semibold text-[var(--color-text)]">{t("settings.help")}</p>
      </div>
      {FAQ.map((item, i) => (
        <div key={i} className="border-b border-[var(--color-border)] last:border-0">
          <button type="button" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}
            className="w-full flex items-center justify-between gap-2 py-2.5 text-left min-h-11">
            <span className="text-sm font-medium text-[var(--color-text)]">{t(item.qKey)}</span>
            <ChevronDown size={16} className={`shrink-0 text-[var(--color-muted)] transition-transform ${open === i ? "rotate-180" : ""}`} />
          </button>
          {open === i && <p className="text-sm text-[var(--color-muted)] leading-relaxed pb-3">{t(item.aKey)}</p>}
        </div>
      ))}
    </Card>
  );
};
