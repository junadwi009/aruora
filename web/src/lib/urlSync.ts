/** Same-origin routing. Tokens and learner answers never enter application paths. */
export type Step = string;
export type View = string;
const STEP_TO_PATH: Record<string,string> = {
  welcome: "/", login: "/login", register: "/register", forgot: "/forgot-password",
  onboarding: "/onboarding", placement: "/placement", generating: "/placement/generating",
  results: "/placement/results", program: "/program", milestones: "/milestones", app: "/app"
};
const PATH_TO_STEP = Object.fromEntries(Object.entries(STEP_TO_PATH).map(([k,v]) => [v,k]));
const KNOWN_VIEWS = new Set(["home","journey","practice","reading","listening","speaking","writing","test","tips","progress","session","pronounce","vocab","roleplay","settings"]);
const clean = (path: string) => (path || "/").replace(/\/+$/, "") || "/";
export function pathForStep(step: string): string { return STEP_TO_PATH[step] ?? "/"; }
export function pathForView(view: string): string { const v = KNOWN_VIEWS.has(view) ? view : "home"; return v === "home" ? "/app" : `/app/${v}`; }
export function viewFromPath(path: string): string | null {
  const m = /^\/app(?:\/([a-z-]+))?$/.exec(clean(path));
  if (!m) return null;
  const v = m[1] ?? "home";
  return KNOWN_VIEWS.has(v) ? v : null;
}
export function stepFromPath(path: string): string | null {
  // A known nested workspace URL must mount the app, not fall back to Welcome.
  if (viewFromPath(path)) return "app";
  const step = PATH_TO_STEP[clean(path)];
  return typeof step === "string" ? step : null;
}
/** Never honor arbitrary return URLs, including protocol-relative or encoded URLs. */
export function safeAppReturn(value: string | null | undefined): string {
  if (!value || value.includes("\\") || value.includes("%") || value.includes("?") || value.includes("#") || value.startsWith("//")) return "/app";
  const v = viewFromPath(value);
  return v ? pathForView(v) : "/app";
}
export function currentPath(): string {
  try { return typeof window !== "undefined" ? window.location.pathname : "/"; } catch { return "/"; }
}
function localUrl(url: string): boolean { return url.startsWith("/") && !url.startsWith("//") && !/[\\\x00-\x20]/.test(url); }
function changeUrl(url: string, replace: boolean): boolean {
  if (!localUrl(url)) throw new Error("Only local navigation is permitted");
  try {
    if (typeof window !== "undefined") {
      if (!replace && !window.dispatchEvent(new Event("aruora:before-navigate", {cancelable:true}))) return false;
      if (replace) window.history.replaceState({}, "", url);
      else if (window.location.pathname + window.location.search + window.location.hash !== url) window.history.pushState({}, "", url);
      window.dispatchEvent(new Event("aruora:navigate"));
      return true;
    }
  } catch { /* Navigation is unavailable in some sandboxed embeds. */ }
  return false;
}
export const pushUrl = (url: string): boolean => changeUrl(url, false);
export const replaceUrl = (url: string): boolean => changeUrl(url, true);
