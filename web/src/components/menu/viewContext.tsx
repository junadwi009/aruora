import React, {createContext, useCallback, useContext, useEffect, useMemo, useRef, useState} from "react";
import {currentPath, pathForView, pushUrl, viewFromPath} from "../../lib/urlSync";
export type View = "home" | "journey" | "practice" | "reading" | "listening" | "speaking" | "writing" | "test" | "tips" | "progress" | "session" | "pronounce" | "vocab" | "roleplay" | "settings";
export interface Prefill { skill: string; text: string }
export interface ViewContextValue {
  view: View; setView: (v: View) => void;
  goWithPrefill: (skill: string, text: string) => void;
  consumePrefill: (skill: string) => string | null;
}
const ViewContext = createContext<ViewContextValue | null>(null);
export const ViewProvider: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [view,setViewState] = useState<View>(() => (viewFromPath(currentPath()) ?? "home") as View);
  const prefill = useRef<Prefill | null>(null);
  const setView = useCallback((v: View) => {pushUrl(pathForView(v));},[]);
  const goWithPrefill = useCallback((skill: string,text: string) => {
    if (!["reading","listening","speaking","writing"].includes(skill)) return;
    prefill.current = {skill,text}; if(!pushUrl(pathForView(skill))) prefill.current=null;
  },[]);
  useEffect(() => {
    const update = () => {const v = viewFromPath(currentPath()); if (v) setViewState(v as View);};
    window.addEventListener("popstate",update); window.addEventListener("aruora:navigate",update);
    return () => {window.removeEventListener("popstate",update); window.removeEventListener("aruora:navigate",update);};
  },[]);
  const consumePrefill = useCallback((skill: string) => {
    if (!prefill.current || prefill.current.skill !== skill) return null;
    const text = prefill.current.text; prefill.current = null; return text;
  },[]);
  const value = useMemo(() => ({view,setView,goWithPrefill,consumePrefill}),[view,setView,goWithPrefill,consumePrefill]);
  return <ViewContext.Provider value={value}>{children}</ViewContext.Provider>;
};
export function useView(): ViewContextValue {
  const c = useContext(ViewContext); if (!c) throw new Error("useView must be used within a ViewProvider"); return c;
}
