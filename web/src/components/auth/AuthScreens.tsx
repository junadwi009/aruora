import React from "react";
import { useJourney } from "../../lib/journey";
import { AuthForm } from "./AuthForm";
import { ForgotPassword } from "./ForgotPassword";

/** Returning-user sign-in (from Welcome). On success jump straight into the app. */
export const LoginScreen: React.FC = () => {
  const { go } = useJourney();
  return (
    <AuthForm
      mode="login"
      onSuccess={() => go("app")}
      onSwitch={() => go("welcome")}
      onForgot={() => go("forgot")}
    />
  );
};

/** Forgot-password (from Login). */
export const ForgotScreen: React.FC = () => {
  const { go } = useJourney();
  return <ForgotPassword onBack={() => go("login")} />;
};

/** Registration after placement — attaches credentials to the anonymous profile. */
export const RegisterScreen: React.FC = () => {
  const { go } = useJourney();
  return (
    <AuthForm
      mode="register"
      onSuccess={() => go("program")}
      onSwitch={() => go("login")}
      onSkip={() => go("program")}
    />
  );
};
