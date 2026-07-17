import React, { useState } from "react";
import { LogIn, UserPlus } from "lucide-react";
import { api } from "../../lib/api/client";
import type { AccountUser } from "../../lib/types";
import { Button } from "../ui/Button";
import { PasswordInput } from "../ui/PasswordInput";
import { useT } from "../../lib/i18n";
import { GoogleButton } from "./GoogleButton";

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
  const [googleClientId, setGoogleClientId] = useState("");

  React.useEffect(() => {
    api.health().then((h) => setGoogleClientId(h.googleClientId || "")).catch(() => {});
  }, []);

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
      setError(err instanceof Error ? err.message : t("auth.genericError"));
    } finally {
      setBusy(false);
    }
  };

  const labelCls =
    "text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]";
  const inputCls =
    "min-h-11 px-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]";

  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden bg-[var(--color-bg)] p-6">
      {/* Ambient gradient blobs — decorative */}
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          top: 0,
          left: 0,
          width: "20rem",
          height: "20rem",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--color-primary-600) 28%, transparent), transparent)",
        }}
      />
      <span
        aria-hidden="true"
        className="premium-blob"
        style={{
          bottom: 0,
          right: 0,
          width: "20rem",
          height: "20rem",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--color-danger) 20%, transparent), transparent)",
        }}
      />

      <form
        onSubmit={submit}
        className="relative z-10 flex w-full max-w-md flex-col gap-5 rounded-[var(--radius-3xl)] border border-[color-mix(in_srgb,var(--color-border)_70%,transparent)] bg-[var(--color-surface)] p-8"
        style={{ boxShadow: "var(--shadow-premium-card)" }}
      >
        <div className="mb-2 flex flex-col items-center gap-3 text-center">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary-600)] text-white"
            style={{ boxShadow: "var(--shadow-premium)" }}
            aria-hidden="true"
          >
            {isLogin ? <LogIn size={24} /> : <UserPlus size={24} />}
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-display)" }}>
            {isLogin ? t("auth.welcomeBack") : t("auth.createAccount")}
          </h1>
          <p className="max-w-xs text-sm text-[var(--color-muted)]">
            {isLogin ? t("auth.signinSub") : t("auth.registerSub")}
          </p>
        </div>

        <label className="flex flex-col gap-2">
          <span className={labelCls}>{t("auth.email")}</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputCls}
            placeholder="you@example.com"
          />
        </label>

        <label className="flex flex-col gap-2">
          <span className={labelCls}>{t("auth.password")}</span>
          <PasswordInput
            autoComplete={isLogin ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputCls}
            placeholder={t("auth.passwordPlaceholder")}
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

        <Button type="submit" pill loading={busy} className="w-full">
          {isLogin ? t("auth.signIn") : t("auth.createBtn")}
        </Button>

        {googleClientId && (
          <>
            <div className="flex items-center gap-2 text-[11px] text-[var(--color-muted)]">
              <span className="h-px flex-1 bg-[var(--color-border)]" />
              {t("auth.or")}
              <span className="h-px flex-1 bg-[var(--color-border)]" />
            </div>
            <GoogleButton clientId={googleClientId} onSuccess={onSuccess} onError={setError} />
          </>
        )}

        {isLogin && onForgot && (
          <button
            type="button"
            onClick={onForgot}
            className="text-xs font-semibold text-[var(--color-primary-700)] hover:underline underline-offset-2 min-h-11"
            style={{ fontFamily: "var(--font-display)" }}
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
