import React from "react";
import { Button } from "../ui";
import { ClipboardList, Clock, Mic } from "lucide-react";
import { useT } from "../../lib/i18n";

export interface PlacementIntroProps {
  onBegin: () => void;
}

export const PlacementIntro: React.FC<PlacementIntroProps> = ({ onBegin }) => {
  const { t } = useT();
  return (
    <div className="journey-bg flex min-h-full items-center justify-center p-6">
      <div
        className="animate-fade-slide-in flex w-full max-w-lg flex-col gap-7 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8"
        style={{ boxShadow: "var(--shadow-premium-card)" }}
      >
        {/* Heading */}
        <div className="flex flex-col gap-3">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary-600)] text-white"
            style={{ boxShadow: "var(--shadow-premium)" }}
            aria-hidden="true"
          >
            <ClipboardList size={24} />
          </div>
          <h1
            className="text-2xl font-bold leading-tight tracking-tight text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {t("place.introTitle")}
          </h1>
          <p className="text-base leading-relaxed text-[var(--color-muted)]">
            {t("place.introSubtitle")}
          </p>
        </div>

        {/* Fact list */}
        <ul className="flex flex-col gap-4 text-sm text-[var(--color-text)]">
          <li className="flex items-start gap-3">
            <span
              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)]"
              style={{ background: "color-mix(in srgb, var(--color-primary-600) 12%, transparent)" }}
              aria-hidden="true"
            >
              <Clock size={16} className="text-[var(--color-primary-600)]" />
            </span>
            <span className="pt-1">
              <strong>{t("place.factTimeStrong")}</strong> {t("place.factTimeRest")}
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span
              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)]"
              style={{ background: "color-mix(in srgb, var(--color-primary-600) 12%, transparent)" }}
              aria-hidden="true"
            >
              <ClipboardList size={16} className="text-[var(--color-primary-600)]" />
            </span>
            <span className="pt-1">
              {t("place.factCoversPre")} <strong>{t("place.factCoversStrong")}</strong> {t("place.factCoversRest")}
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span
              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)]"
              style={{ background: "color-mix(in srgb, var(--color-primary-600) 12%, transparent)" }}
              aria-hidden="true"
            >
              <Mic size={16} className="text-[var(--color-primary-600)]" />
            </span>
            <span className="pt-1">
              {t("place.factSpeakingPre")} <strong>{t("place.factSpeakingStrong")}</strong> {t("place.factSpeakingRest")}
            </span>
          </li>
        </ul>

        {/* Footer note */}
        <p className="border-t border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] pt-5 text-xs text-[var(--color-muted)]">
          {t("place.accommodationsPre")}{" "}
          <strong>{t("place.accommodationsStrong")}</strong> {t("place.accommodationsRest")}
        </p>

        {/* CTA */}
        <div className="flex justify-end">
          <Button size="lg" pill onClick={onBegin}>
            {t("place.begin")}
          </Button>
        </div>
      </div>
    </div>
  );
};
