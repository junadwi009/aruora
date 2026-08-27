import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { currentPath, pathForView, pushUrl, viewFromPath } from "../../lib/urlSync";

export type View =
  | "home"
  | "reading"
  | "listening"
  | "speaking"
  | "writing"
  | "test"
  | "tips"
  | "progress"
  | "session"
  | "pronounce"
  | "vocab"
  | "roleplay"
  | "settings";

export interface Prefill {
  skill: string;
  text: string;
}

export interface ViewContextValue {
  view: View;
  setView: (v: View) => void;
  /** Navigate to a skill view carrying a one-shot prefill (lesson Produce handoff). */
  goWithPrefill: (skill: string, text: string) => void;
  /** Read-and-clear the pending prefill for a skill (consumed once on mount). */
  consumePrefill: (skill: string) => string | null;
}

const ViewContext = createContext<ViewContextValue | null>(null);

export const ViewProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // WS13-01: /app/<view> deep links — boot from the URL when it maps to a
  // known shell view (refresh on /app/writing returns to writing).
  const [view, setViewState] = useState<View>(
    () => (viewFromPath(currentPath()) as View) ?? "home"
  );
  const [prefill, setPrefill] = useState<Prefill | null>(null);

  const setView = useCallback((v: View) => {
    setViewState(v);
    pushUrl(pathForView(v));
  }, []);

  const goWithPrefill = useCallback((skill: string, text: string) => {
    setPrefill({ skill, text });
    setViewState(skill as View);
    pushUrl(pathForView(skill));
  }, []);

  // Back/forward restores the matching shell view while inside /app.
  useEffect(() => {
    const onPop = () => {
      const v = viewFromPath(currentPath());
      if (v) setViewState(v as View);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const consumePrefill = useCallback(
    (skill: string) => {
      if (prefill && prefill.skill === skill) {
        const t = prefill.text;
        setPrefill(null);
        return t;
      }
      return null;
    },
    [prefill]
  );

  const value = useMemo<ViewContextValue>(
    () => ({ view, setView, goWithPrefill, consumePrefill }),
    [view, setView, goWithPrefill, consumePrefill]
  );

  return <ViewContext.Provider value={value}>{children}</ViewContext.Provider>;
};

export function useView(): ViewContextValue {
  const ctx = useContext(ViewContext);
  if (!ctx) throw new Error("useView must be used within a ViewProvider");
  return ctx;
}
