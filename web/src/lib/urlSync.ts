/**
 * WS13-01/03 — URL synchronization for the journey + app shell.
 *
 * Gives every major state a stable, shareable, refresh-surviving URL without
 * pulling a router dependency into the current context-driven navigation:
 *
 *   /                     → welcome
 *   /login /register /forgot-password
 *   /onboarding /placement /placement/results /program /milestones
 *   /app                  → home
 *   /app/<view>           → reading|listening|writing|speaking|pronounce|
 *                           vocab|roleplay|test|tips|progress|settings|session
 *
 * Rules (WS13-03): never encode tokens or private result payloads in the URL
 * — placement results stay in memory only; the URL merely points at the
 * screen. popstate (back/forward) restores the matching state.
 */

export type Step = string; // journey Step union — kept loose to avoid a cycle
export type View = string; // app View union — same

const STEP_TO_PATH: Record<string, string> = {
  welcome: "/",
  login: "/login",
  register: "/register",
  forgot: "/forgot-password",
  onboarding: "/onboarding",
  placement: "/placement",
  generating: "/placement/generating",
  results: "/placement/results",
  program: "/program",
  milestones: "/milestones",
  app: "/app",
};

const PATH_TO_STEP: Record<string, string> = Object.fromEntries(
  Object.entries(STEP_TO_PATH).map(([k, v]) => [v, k])
);

const KNOWN_VIEWS = new Set([
  "home", "reading", "listening", "speaking", "writing", "test", "tips",
  "progress", "session", "pronounce", "vocab", "roleplay", "settings",
]);

export function pathForStep(step: string): string {
  return STEP_TO_PATH[step] ?? "/";
}

export function stepFromPath(path: string): string | null {
  const clean = (path || "/").replace(/\/+$/, "") || "/";
  return PATH_TO_STEP[clean] ?? null;
}

export function pathForView(view: string): string {
  const v = KNOWN_VIEWS.has(view) ? view : "home";
  return v === "home" ? "/app" : `/app/${v}`;
}

export function viewFromPath(path: string): string | null {
  const m = /^\/app(?:\/([a-z-]+))?$/.exec((path || "").replace(/\/+$/, ""));
  if (!m) return null;
  const v = m[1] ?? "home";
  return KNOWN_VIEWS.has(v) ? v : null;
}

/** Push a new history entry (guards non-browser environments/tests). */
export function pushUrl(url: string): void {
  try {
    if (typeof window !== "undefined" && window.history?.pushState) {
      window.history.pushState({}, "", url);
    }
  } catch {
    /* history may be unavailable in exotic embeds — never break navigation */
  }
}

/** Replace the current entry (used for redirects/normalization). */
export function replaceUrl(url: string): void {
  try {
    if (typeof window !== "undefined" && window.history?.replaceState) {
      window.history.replaceState({}, "", url);
    }
  } catch {
    /* ignore */
  }
}

export function currentPath(): string {
  try {
    return typeof window !== "undefined" ? window.location.pathname : "/";
  } catch {
    return "/";
  }
}
