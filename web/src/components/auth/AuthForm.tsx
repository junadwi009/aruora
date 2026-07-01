import React, { useState } from "react";
import { LogIn, UserPlus } from "lucide-react";
import { api } from "../../lib/api/client";
import type { AccountUser } from "../../lib/types";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

interface AuthFormProps {
  mode: "login" | "register";
  onSuccess: (user: AccountUser) => void;
  onSwitch?: () => void;
  onSkip?: () => void;
  onForgot?: () => void;
}

export const AuthForm: React.FC<AuthFormProps> = ({ mode, onSuccess, onSwitch, onSkip, onForgot }) => {
  const { t } = useT();
  const isLogin = mode === "login";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || password.length < 6) {
      setError(t("auth.badCreds"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const user = isLogin
        ? await api.accountLogin({ email: email.trim(), password, remember })
        : await api.accountRegister({ email: email.trim(), password });
      onSuccess(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="journey-bg flex min-h-full items-center justify-center p-6">
      <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-5">
        <div className="flex flex-col items-center gap-2 text-center">
          <div
            className="flex items-center justify-center w-12 h-12 rounded-[var(--radius-xl)]"
            style={{ background: "linear-gradient(135deg, var(--color-primary-600), var(--color-primary-800))" }}
            aria-hidden="true"
          >
            {isLogin ? <LogIn size={22} className="text-white" /> : <UserPlus size={22} className="text-white" />}
          </div>
          <h1 className="text-xl font-bold text-[var(--color-text)]">
            {isLogin ? t("auth.welcomeBack") : t("auth.createAccount")}
          </h1>
          <p className="text-sm text-[var(--color-muted)]">
            {isLogin ? t("auth.signinSub") : t("auth.registerSub")}
          </p>
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-[var(--color-muted)]">{t("auth.email")}</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="min-h-11 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
            placeholder="you@example.com"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-[var(--color-muted)]">{t("auth.password")}</span>
          <input
            type="password"
            autoComplete={isLogin ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="min-h-11 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
            placeholder="At least 6 characters"
          />
        </label>

        {isLogin && (
          <label className="flex items-center gap-2 text-sm text-[var(--color-text)] cursor-pointer select-none">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 accent-[var(--color-primary-600)]"
            />
            <span>{t("auth.remember")}</span>
            <span className="text-xs text-[var(--color-muted)]">{t("auth.rememberHint")}</span>
          </label>
        )}

        {error && <p className="text-xs text-[var(--color-danger)]" role="alert">{error}</p>}

        <Button type="submit" loading={busy} className="w-full">
          {isLogin ? t("auth.signIn") : t("auth.createBtn")}
        </Button>

        {isLogin && onForgot && (
          <button
            type="button"
            onClick={onForgot}
            className="text-xs text-[var(--color-muted)] hover:text-[var(--color-text)] underline-offset-2 hover:underline min-h-11"
          >
            {t("auth.forgot")}
          </button>
        )}

        {onSwitch && (
          <button
            type="button"
            onClick={onSwitch}
            className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] underline-offset-2 hover:underline min-h-11"
          >
            {isLogin ? t("auth.toRegister") : t("auth.toLogin")}
          </button>
        )}

        {onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="text-xs text-[var(--color-muted)] hover:text-[var(--color-text)] min-h-11"
          >
            {t("auth.maybeLater")}
          </button>
        )}
      </form>
    </div>
  );
};
