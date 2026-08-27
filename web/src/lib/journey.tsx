import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { PlacementResult, Milestone } from "./types";
import { currentPath, pathForStep, pushUrl, stepFromPath } from "./urlSync";

export type Step =
  | "welcome"
  | "login"
  | "forgot"
  | "onboarding"
  | "placement"
  | "generating"
  | "results"
  | "register"
  | "program"
  | "milestones"
  | "app";

export interface JourneyContextValue {
  step: Step;
  go: (step: Step) => void;
  placementResult: PlacementResult | null;
  setPlacementResult: (result: PlacementResult | null) => void;
  milestones: Milestone[];
  setMilestones: (milestones: Milestone[]) => void;
}

const JourneyContext = createContext<JourneyContextValue | null>(null);

export const JourneyProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  // WS13-01/03: deep-linkable journey — boot from the URL when it maps to a
  // known step (refresh on /onboarding returns to onboarding), otherwise the
  // welcome default.
  const [step, setStep] = useState<Step>(
    () => (stepFromPath(currentPath()) ?? "welcome") as Step
  );
  const [placementResult, setPlacementResult] = useState<PlacementResult | null>(
    null
  );
  const [milestones, setMilestones] = useState<Milestone[]>([]);

  const go = useCallback((next: Step) => {
    setStep(next);
    pushUrl(pathForStep(next));
  }, []);

  // Browser back/forward restores the matching journey step (WS13-03).
  useEffect(() => {
    const onPop = () => {
      const s = stepFromPath(currentPath());
      if (s) setStep(s as Step);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const value = useMemo<JourneyContextValue>(
    () => ({
      step,
      go,
      placementResult,
      setPlacementResult,
      milestones,
      setMilestones,
    }),
    [step, go, placementResult, milestones]
  );

  return (
    <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>
  );
};

export function useJourney(): JourneyContextValue {
  const ctx = useContext(JourneyContext);
  if (!ctx) {
    throw new Error("useJourney must be used within a JourneyProvider");
  }
  return ctx;
}
