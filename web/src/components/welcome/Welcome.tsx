import React from "react";
import { BookOpen } from "lucide-react";
import { Button } from "../ui";
import { useJourney } from "../../lib/journey";
import { useT } from "../../lib/i18n";

export const Welcome: React.FC = () => {
  const { go } = useJourney();
  const { t } = useT();

  return (
    <div className="journey-bg flex min-h-full items-center justify-center p-6">
      <div className="animate-fade-slide-in flex max-w-sm flex-col items-center gap-8 text-center">

        {/* Brand mark */}
        <div className="flex flex-col items-center gap-3">
          <div
            className="flex items-center justify-center w-14 h-14 rounded-[var(--radius-xl)]"
            style={{
              background: "linear-gradient(135deg, var(--color-primary-600), var(--color-primary-800))",
              boxShadow: "var(--shadow-e3)",
            }}
            aria-hidden="true"
          >
            <BookOpen size={26} className="text-white" />
          </div>
          <span className="text-xs font-semibold tracking-widest text-[var(--color-muted)] uppercase">
            IELTS Coach
          </span>
        </div>

        {/* Heading */}
        <div className="flex flex-col gap-3">
          <h1
            className="text-4xl font-bold text-[var(--color-text)] tracking-tight leading-tight"
            style={{ textWrap: "balance" } as React.CSSProperties}
          >
            {t("welcome.title")}
          </h1>
          <p className="text-base text-[var(--color-muted)] leading-relaxed">
            {t("welcome.subtitle")}
          </p>
        </div>

        {/* CTAs */}
        <div className="flex flex-col items-center gap-3 w-full">
          <Button
            size="lg"
            onClick={() => go("onboarding")}
            className="min-w-[12rem]"
          >
            {t("welcome.getStarted")}
          </Button>
          <button
            type="button"
            onClick={() => go("login")}
            className={[
              "text-sm text-[var(--color-muted)] underline-offset-2",
              "hover:text-[var(--color-text)] hover:underline",
              "transition-colors focus-visible:outline-2 focus-visible:outline-offset-2",
              "focus-visible:outline-[var(--color-primary-600)] rounded",
              "min-h-[44px] px-2",
            ].join(" ")}
          >
            {t("welcome.haveAccount")}
          </button>
        </div>
      </div>
    </div>
  );
};
