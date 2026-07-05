import React from "react";

export interface RadioCardProps {
  selected: boolean;
  onSelect: () => void;
  icon?: React.ReactNode;
  title: string;
  description?: string;
}

export const RadioCard: React.FC<RadioCardProps> = ({
  selected,
  onSelect,
  icon,
  title,
  description,
}) => {
  const handleKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect();
      return;
    }
    // Roving Arrow-key navigation within the enclosing role="radiogroup".
    const NEXT = ["ArrowDown", "ArrowRight"];
    const PREV = ["ArrowUp", "ArrowLeft"];
    if (!NEXT.includes(e.key) && !PREV.includes(e.key)) return;
    const group = e.currentTarget.closest('[role="radiogroup"]');
    if (!group) return;
    const radios = Array.from(group.querySelectorAll<HTMLElement>('[role="radio"]'));
    const idx = radios.indexOf(e.currentTarget);
    if (idx === -1) return;
    e.preventDefault();
    const delta = NEXT.includes(e.key) ? 1 : -1;
    radios[(idx + delta + radios.length) % radios.length].focus();
  };

  return (
    <div
      role="radio"
      aria-checked={selected}
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={handleKey}
      className={[
        "flex items-start gap-3 p-4 rounded-[var(--radius-lg)] border cursor-pointer",
        "transition-[transform,box-shadow,background-color,border-color]",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
        "active:scale-[.99]",
        selected
          ? "border-[var(--color-primary-600)] bg-[var(--color-primary-50)] " +
            "shadow-[var(--shadow-e2)] outline outline-2 outline-[var(--color-primary-600)]"
          : "border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-e1)] " +
            "hover:bg-[var(--color-surface-2)] hover:-translate-y-px hover:shadow-[var(--shadow-e2)] " +
            "hover:border-[var(--color-primary-600)]",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {icon && (
        <span
          className={[
            "mt-0.5 flex-shrink-0",
            selected ? "text-[var(--color-primary-600)]" : "text-[var(--color-muted)]",
          ].join(" ")}
          aria-hidden="true"
        >
          {icon}
        </span>
      )}
      <div className="flex-1">
        <p className="text-sm font-semibold text-[var(--color-text)]">{title}</p>
        {description && (
          <p className="text-xs text-[var(--color-muted)] mt-0.5">{description}</p>
        )}
      </div>
      {/* Visual indicator (not color-only: uses checkmark symbol) */}
      <span
        className={[
          "mt-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0",
          "transition-colors",
          selected
            ? "border-[var(--color-primary-600)] bg-[var(--color-primary-600)]"
            : "border-[var(--color-border)]",
        ]
          .filter(Boolean)
          .join(" ")}
        aria-hidden="true"
      >
        {selected && (
          <span className="text-white text-[8px] leading-none">✓</span>
        )}
      </span>
    </div>
  );
};
