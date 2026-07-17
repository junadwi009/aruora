import React from "react";
import { BookOpen, ArrowRight, Award, BookCheck, Sparkles } from "lucide-react";
import { Button } from "../ui";
import { useJourney } from "../../lib/journey";
import { useT } from "../../lib/i18n";

// Display-face style, reused for the wordmark + headline.
const DISPLAY = { fontFamily: "var(--font-display)" } as const;

export const Welcome: React.FC = () => {
  const { go } = useJourney();
  const { t } = useT();

  return (
    <div className="relative min-h-full overflow-hidden bg-[var(--color-bg)] px-6 py-8 md:px-10">
      {/* Ambient gradient blobs — purely decorative */}
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          top: "-4rem",
          left: "18%",
          width: "24rem",
          height: "24rem",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--color-primary-600) 30%, transparent), transparent)",
        }}
      />
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          bottom: "2rem",
          right: "6%",
          width: "20rem",
          height: "20rem",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--color-warning) 22%, transparent), transparent)",
        }}
      />

      <div className="relative z-10 mx-auto flex min-h-full max-w-6xl flex-col">
        {/* Brand header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary-600)] text-white"
              style={{ boxShadow: "var(--shadow-premium)" }}
              aria-hidden="true"
            >
              <BookOpen size={20} />
            </div>
            <span className="text-lg font-bold tracking-tight text-[var(--color-text)]" style={DISPLAY}>
              IELTS Coach
            </span>
          </div>
          <Button variant="ghost" pill size="sm" onClick={() => go("login")}>
            {t("auth.signIn")}
          </Button>
        </header>

        {/* Hero */}
        <div className="my-auto grid grid-cols-1 items-center gap-12 py-12 lg:grid-cols-12">
          <div className="flex flex-col gap-6 text-center lg:col-span-7 lg:text-left">
            <span
              className="mx-auto inline-flex items-center gap-1.5 self-center rounded-full border border-[color-mix(in_srgb,var(--color-primary-600)_25%,transparent)] bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)] px-3 py-1 text-xs font-bold uppercase tracking-wider text-[var(--color-primary-700)] lg:mx-0 lg:self-start"
              style={DISPLAY}
            >
              <Award size={14} /> {t("welcome.badge")}
            </span>

            <h1
              className="text-4xl font-bold leading-[1.12] tracking-tight text-[var(--color-text)] sm:text-5xl lg:text-6xl"
              style={{ textWrap: "balance", ...DISPLAY } as React.CSSProperties}
            >
              {t("welcome.title")}
            </h1>

            <p className="mx-auto max-w-xl text-base leading-relaxed text-[var(--color-muted)] lg:mx-0">
              {t("welcome.subtitle")}
            </p>

            <div className="mt-2 flex flex-col items-center gap-3 sm:flex-row lg:justify-start">
              <Button size="lg" pill onClick={() => go("onboarding")} className="w-full gap-2 sm:w-auto">
                {t("welcome.getStarted")}
                <ArrowRight size={18} aria-hidden="true" />
              </Button>
              <Button size="lg" pill variant="secondary" onClick={() => go("login")} className="w-full sm:w-auto">
                {t("welcome.haveAccount")}
              </Button>
            </div>
          </div>

          {/* Decorative illustration panel with floating stat cards */}
          <div className="flex justify-center lg:col-span-5">
            <div
              className="relative flex h-80 w-80 items-center justify-center rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8 sm:h-96 sm:w-96"
              style={{ boxShadow: "var(--shadow-premium-card)" }}
            >
              {/* Floating stat — reading band */}
              <div
                className="absolute -left-5 -top-5 flex max-w-[200px] items-center gap-3 rounded-[var(--radius-xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-4"
                style={{ boxShadow: "var(--shadow-premium)" }}
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--color-success)_14%,transparent)] text-[var(--color-success)]">
                  <BookCheck size={20} aria-hidden="true" />
                </span>
                <div>
                  <div className="text-[10px] font-bold uppercase text-[var(--color-muted)]" style={DISPLAY}>
                    {t("welcome.statReadingLabel")}
                  </div>
                  <div className="text-sm font-bold text-[var(--color-text)]" style={DISPLAY}>
                    {t("welcome.statReadingValue")}
                  </div>
                </div>
              </div>

              {/* Floating stat — smart system */}
              <div
                className="absolute -bottom-5 -right-5 max-w-[180px] rounded-[var(--radius-xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-4"
                style={{ boxShadow: "var(--shadow-premium)" }}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[var(--color-primary-600)]" />
                  <span className="text-[10px] font-bold uppercase text-[var(--color-muted)]" style={DISPLAY}>
                    {t("welcome.statSmartLabel")}
                  </span>
                </div>
                <div className="text-xs font-bold text-[var(--color-text)]" style={DISPLAY}>
                  {t("welcome.statSmartValue")}
                </div>
              </div>

              {/* Central mark */}
              <div className="relative flex h-40 w-40 items-center justify-center">
                <div className="absolute inset-0 animate-pulse rounded-full bg-[color-mix(in_srgb,var(--color-primary-600)_10%,transparent)]" />
                <div
                  className="relative flex h-28 w-28 items-center justify-center rounded-[var(--radius-3xl)] bg-[var(--color-primary-600)] text-white"
                  style={{ boxShadow: "var(--shadow-premium-card)" }}
                >
                  <Sparkles size={44} aria-hidden="true" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer note */}
        <p className="mt-4 border-t border-[color-mix(in_srgb,var(--color-border)_60%,transparent)] pt-6 text-center text-xs text-[var(--color-muted)]">
          {t("welcome.footnote")}
        </p>
      </div>
    </div>
  );
};
