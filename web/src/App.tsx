import { lazy, Suspense, useEffect, useState } from "react";
import { api } from "./lib/api/client";
import { JourneyProvider, useJourney } from "./lib/journey";
import { useGate } from "./lib/gate";
import { Welcome } from "./components/welcome/Welcome";
import { Onboarding } from "./components/onboarding/Onboarding";
import { PlacementRunner } from "./components/placement/PlacementRunner";
import { Generating } from "./components/placement/Generating";
import { Program } from "./components/program/Program";
import { Milestones } from "./components/milestones/Milestones";
import { AppShell } from "./components/menu/AppShell";
import { PasscodeGate } from "./components/auth/PasscodeGate";
import { LoginScreen, RegisterScreen, ForgotScreen } from "./components/auth/AuthScreens";
import { ResetPassword } from "./components/auth/ResetPassword";
import { FeedbackGate } from "./components/gate/FeedbackGate";

// Code-split: recharts lives only in Results, so lazy-loading it keeps the main chunk smaller
const Results = lazy(() => import("./components/results/Results"));

function Placeholder({ name }: { name: string }) {
  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <p className="text-[var(--color-muted)]">{name}</p>
    </div>
  );
}

function Journey() {
  const { step, go } = useJourney();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .skillLevels()
      .then((levels) => {
        if (!active) return;
        if (Array.isArray(levels) && levels.length > 0) go("app");
      })
      .catch(() => {
        /* stay at welcome on error */
      })
      .finally(() => {
        if (active) setChecking(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (checking) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <p className="text-[var(--color-muted)]">Loading…</p>
      </div>
    );
  }

  switch (step) {
    case "welcome":
      return <Welcome />;
    case "login":
      return <LoginScreen />;
    case "forgot":
      return <ForgotScreen />;
    case "register":
      return <RegisterScreen />;
    case "onboarding":
      return <Onboarding />;
    case "placement":
      return <PlacementRunner />;
    case "generating":
      return <Generating />;
    case "results":
      return (
        <Suspense fallback={<div className="p-6">Loading…</div>}>
          <Results />
        </Suspense>
      );
    case "program":
      return <Program />;
    case "milestones":
      return <Milestones />;
    case "app":
      return <AppShell />;
    default:
      return <Placeholder name={step} />;
  }
}

export default function App() {
  // null = checking, true = may proceed, false = passcode required
  const [unlocked, setUnlocked] = useState<boolean | null>(null);
  // Password reset via emailed ?reset_token=… link takes precedence over everything.
  const [resetToken, setResetToken] = useState<string | null>(() =>
    typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("reset_token") : null
  );

  useEffect(() => {
    let active = true;
    api
      .authStatus()
      .then((s) => active && setUnlocked(!s.authRequired || s.authenticated))
      .catch(() => active && setUnlocked(true)); // fail open (e.g. status route unreachable)
    return () => {
      active = false;
    };
  }, []);

  // Idle session timeout (Phase 3a): the client fires this on a SESSION_EXPIRED
  // response — reload to return to the sign-in / welcome screen.
  useEffect(() => {
    const onExpired = () => window.location.reload();
    window.addEventListener("ielts:session-expired", onExpired);
    return () => window.removeEventListener("ielts:session-expired", onExpired);
  }, []);

  if (resetToken) {
    return (
      <ResetPassword
        token={resetToken}
        onDone={() => {
          window.history.replaceState({}, "", window.location.pathname);
          setResetToken(null);
        }}
      />
    );
  }

  if (unlocked === null) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <p className="text-[var(--color-muted)]">Loading…</p>
      </div>
    );
  }

  if (!unlocked) {
    return <PasscodeGate onUnlock={() => setUnlocked(true)} />;
  }

  return <GatedJourney />;
}

// Test-phase feedback gate: sits after the passcode check and only ever locks
// signed-in users (useGate's status stays null — locked=false — for anonymous
// visitors, since /api/gate/status 401s until they're authenticated).
function GatedJourney() {
  const gate = useGate();
  if (gate.locked) {
    return <FeedbackGate onUnlocked={gate.markUnlocked} />;
  }

  return (
    <JourneyProvider>
      <Journey />
    </JourneyProvider>
  );
}
