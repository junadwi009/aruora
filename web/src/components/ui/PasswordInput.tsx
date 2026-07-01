import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useT } from "../../lib/i18n";

/**
 * Password input with a show/hide (eye) toggle. Drop-in for
 * `<input type="password">` — pass the same className/props. The toggle button is
 * removed from the tab order (tabIndex={-1}) so it doesn't interrupt form flow.
 */
export const PasswordInput: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = ({ className, ...props }) => {
  const { t } = useT();
  const [show, setShow] = useState(false);
  return (
    <div className="relative w-full">
      <input
        {...props}
        type={show ? "text" : "password"}
        className={[className, "w-full pr-10"].filter(Boolean).join(" ")}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={t(show ? "auth.hidePassword" : "auth.showPassword")}
        aria-pressed={show}
        tabIndex={-1}
        className="absolute right-0 top-0 h-full px-3 flex items-center text-[var(--color-muted)] hover:text-[var(--color-text)]"
      >
        {show ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
      </button>
    </div>
  );
};
