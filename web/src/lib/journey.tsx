import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { PlacementResult, Milestone } from "./types";

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
  const [step, setStep] = useState<Step>("welcome");
  const [placementResult, setPlacementResult] = useState<PlacementResult | null>(
    null
  );
  const [milestones, setMilestones] = useState<Milestone[]>([]);

  const go = useCallback((next: Step) => setStep(next), []);

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
