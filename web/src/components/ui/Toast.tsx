import React, { useEffect } from "react";
import { X, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import { useT } from "../../lib/i18n";

export type ToastTone = "neutral" | "success" | "warning" | "danger" | "info";

export interface ToastProps {
  message: string;
  tone?: ToastTone;
  onDismiss: () => void;
}

const toneConfig: Record<
  ToastTone,
  // aria-hidden in lucide-react is Booleanish (boolean | "true" | "false")
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  { classes: string; Icon: React.FC<any> }
> = {
  neutral: {
    classes: "bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)]",
    Icon: Info,
  },
  success: {
    classes: "bg-[color-mix(in_srgb,var(--color-success)_10%,white)] border border-[var(--color-success)] text-[var(--color-success)]",
    Icon: CheckCircle2,
  },
  warning: {
    classes: "bg-[color-mix(in_srgb,var(--color-warning)_10%,white)] border border-[var(--color-warning)] text-[var(--color-warning)]",
    Icon: AlertTriangle,
  },
  danger: {
    classes: "bg-[color-mix(in_srgb,var(--color-danger)_10%,white)] border border-[var(--color-danger)] text-[var(--color-danger)]",
    Icon: XCircle,
  },
  info: {
    classes: "bg-[color-mix(in_srgb,var(--color-info)_10%,white)] border border-[var(--color-info)] text-[var(--color-info)]",
    Icon: Info,
  },
};

export const Toast: React.FC<ToastProps> = ({
  message,
  tone = "neutral",
  onDismiss,
}) => {
  const { t } = useT();
  useEffect(() => {
    const id = setTimeout(onDismiss, 4000);
    return () => clearTimeout(id);
  }, [onDismiss]);

  const { classes, Icon } = toneConfig[tone];

  return (
    <div
      role="status"
      aria-live="polite"
      className={[
        "flex items-start gap-3 px-4 py-3 rounded-[var(--radius-md)] shadow-md max-w-sm",
        classes,
      ].join(" ")}
    >
      <Icon size={16} aria-hidden="true" />
      <p className="flex-1 text-sm">{message}</p>
      <button
        type="button"
        onClick={onDismiss}
        aria-label={t("ui.dismissNotification")}
        className={[
          "min-h-11 min-w-11 flex items-center justify-center rounded",
          "opacity-60 hover:opacity-100",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
        ].join(" ")}
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
};
