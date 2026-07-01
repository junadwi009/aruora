import React from "react";
import { Card, Button } from "../ui";
import { ClipboardList, Clock, Mic } from "lucide-react";
import { useT } from "../../lib/i18n";

export interface PlacementIntroProps {
  onBegin: () => void;
}

export const PlacementIntro: React.FC<PlacementIntroProps> = ({ onBegin }) => {
  const { t } = useT();
  return (
    <div className="journey-bg flex min-h-full items-center justify-center p-6">
      <Card className="animate-fade-slide-in w-full max-w-lg flex flex-col gap-7">
        {/* Heading */}
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-bold text-[var(--color-text)] tracking-tight leading-tight">
            {t("place.introTitle")}
          </h1>
          <p className="text-[var(--color-muted)] text-base leading-relaxed">
            {t("place.introSubtitle")}
          </p>
        </div>

        {/* Fact list */}
        <ul className="flex flex-col gap-4 text-sm text-[var(--color-text)]">
          <li className="flex items-start gap-3">
            <span
              className="mt-0.5 shrink-0 flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)]"
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
              className="mt-0.5 shrink-0 flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)]"
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
              className="mt-0.5 shrink-0 flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)]"
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
        <p className="text-xs text-[var(--color-muted)] border-t border-[var(--color-border)] pt-5">
          {t("place.accommodationsPre")}{" "}
          <strong>{t("place.accommodationsStrong")}</strong> {t("place.accommodationsRest")}
        </p>

        {/* CTA */}
        <div className="flex justify-end">
          <Button size="lg" onClick={onBegin}>
            {t("place.begin")}
          </Button>
        </div>
      </Card>
    </div>
  );
};
