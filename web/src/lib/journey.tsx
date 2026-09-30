import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { PlacementResult, Milestone } from "./types";
import { currentPath, pathForStep, pushUrl, stepFromPath } from "./urlSync";
export type Step = "welcome" | "login" | "forgot" | "onboarding" | "placement" | "generating" | "results" | "register" | "program" | "milestones" | "app";
export interface JourneyContextValue {
  step: Step; go: (step: Step) => void;
  placementResult: PlacementResult | null; setPlacementResult: (r: PlacementResult | null) => void;
  milestones: Milestone[]; setMilestones: (m: Milestone[]) => void;
}
const JourneyContext = createContext<JourneyContextValue | null>(null);
export const JourneyProvider: React.FC<{ children: React.ReactNode }> = ({children}) => {
  const [step, setStep] = useState<Step>(() => (stepFromPath(currentPath()) ?? "welcome") as Step);
  const [placementResult,setPlacementResult] = useState<PlacementResult | null>(null);
  const [milestones,setMilestones] = useState<Milestone[]>([]);
  const go = useCallback((s: Step) => { pushUrl(pathForStep(s)); }, []);
  useEffect(() => {
    const update = () => { const s = stepFromPath(currentPath()); if (s) setStep(s as Step); };
    window.addEventListener("popstate",update); window.addEventListener("aruora:navigate",update);
    return () => { window.removeEventListener("popstate",update); window.removeEventListener("aruora:navigate",update); };
  },[]);
  const value = useMemo(() => ({step,go,placementResult,setPlacementResult,milestones,setMilestones}),[step,go,placementResult,milestones]);
  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
};
export function useJourney(): JourneyContextValue {
  const c = useContext(JourneyContext); if (!c) throw new Error("useJourney must be used within a JourneyProvider"); return c;
}
