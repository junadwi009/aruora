import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "interactive" | "hero" | "stat";
}

const variantClasses: Record<NonNullable<CardProps["variant"]>, string> = {
  default:
    "bg-[var(--color-surface)] " +
    "border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] " +
    "shadow-[var(--shadow-premium)]",
  interactive:
    "bg-[var(--color-surface)] " +
    "border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] " +
    "shadow-[var(--shadow-premium)] cursor-pointer premium-hover",
  hero:
    "bg-[var(--color-primary-600)] text-white border-transparent " +
    "shadow-[var(--shadow-premium-card)]",
  stat:
    "bg-[var(--color-surface-2)] " +
    "border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] " +
    "shadow-[var(--shadow-e1)]",
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ variant = "default", className = "", children, ...rest }, ref) => {
    // A clickable interactive card is a button: make it keyboard-operable and
    // focus-visible so it isn't a mouse-only <div>.
    const asButton = variant === "interactive" && typeof rest.onClick === "function";
    const buttonProps = asButton
      ? {
          role: "button" as const,
          tabIndex: 0,
          onKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              rest.onClick?.(e as unknown as React.MouseEvent<HTMLDivElement>);
            }
            rest.onKeyDown?.(e);
          },
        }
      : {};
    return (
      <div
        ref={ref}
        className={[
          "rounded-[var(--radius-2xl)] p-5",
          variantClasses[variant],
          asButton
            ? "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
            : "",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        {...rest}
        {...buttonProps}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = "Card";
