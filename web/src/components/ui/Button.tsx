import React from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  /** Stretch to full container width */
  fullWidth?: boolean;
  /** Fully-rounded pill shape — the approachable-premium CTA look. */
  pill?: boolean;
}

const variantClasses: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-[var(--color-primary-600)] text-white border-transparent " +
    "hover:bg-[var(--color-primary-700)] hover:shadow-[var(--shadow-premium-card)] " +
    "active:scale-[.98]",
  secondary:
    "bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] " +
    "hover:bg-[var(--color-surface-2)] hover:border-[var(--color-primary-600)] " +
    "active:scale-[.98]",
  ghost:
    "bg-transparent text-[var(--color-muted)] border-transparent " +
    "hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] " +
    "active:scale-[.98]",
  destructive:
    "bg-[var(--color-danger)] text-white border-transparent " +
    "hover:opacity-90 active:scale-[.98]",
};

const sizeClasses: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "min-h-[44px] px-4 text-sm gap-1.5",
  md: "min-h-[44px] px-5 text-sm gap-2",
  lg: "min-h-[48px] px-7 text-base gap-2 font-semibold",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      fullWidth = false,
      pill = false,
      disabled,
      children,
      className = "",
      ...rest
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={loading || disabled}
        className={[
          "inline-flex items-center justify-center font-medium",
          pill ? "rounded-full" : "rounded-[var(--radius-md)]",
          "transition-[background-color,box-shadow,transform,border-color,color]",
          "transition-duration-[var(--duration-base)] ease-[var(--ease-default)]",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]",
          // Disabled: clean muted state — not a washed-out version of the active colour
          "disabled:bg-[var(--color-surface-2)] disabled:text-[var(--color-muted)] disabled:border-transparent",
          "disabled:shadow-none disabled:cursor-not-allowed disabled:pointer-events-none",
          variantClasses[variant],
          sizeClasses[size],
          fullWidth ? "w-full" : "",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        {...rest}
      >
        {loading && (
          <Loader2
            size={16}
            className="animate-spin"
            aria-hidden="true"
          />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
