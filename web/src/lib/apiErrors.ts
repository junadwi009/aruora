/**
 * WS13-04 — consistent API failure UX.
 *
 * Backend errors arrive as { error: { code, message } } ApiError envelopes.
 * Raw provider messages never reach the client (gateway contract), and each
 * known code gets ONE safe, actionable user sentence. Unknown codes fall
 * back to a neutral generic line — never a stack trace, never "Something
 * went wrong" when a safe actionable status exists.
 */

export const API_ERROR_COPY: Record<string, string> = {
  VALIDATION: "Please check the highlighted fields and try again.",
  INVALID_JSON: "That request could not be read — please retry.",
  UNAUTHORIZED: "Please sign in to continue.",
  SESSION_EXPIRED: "Your session expired — sign in again to keep your progress.",
  FORBIDDEN: "You don't have access to that.",
  NOT_FOUND: "That item is no longer available.",
  RATE_LIMITED: "Too many attempts — wait a moment and try again.",
  GEN_CAP_REACHED: "You've reached today's generation limit — stored practice is still available, and fresh sets return tomorrow.",
  POOL_EMPTY: "New practice content is being prepared — try again shortly.",
  LLM_UNAVAILABLE: "The AI coach is unavailable right now — please try again in a moment.",
  LLM_BAD_OUTPUT: "The AI coach returned an unusable response — nothing was saved. Please try again.",
  PAYLOAD_TOO_LARGE: "That upload is too large.",
  SERVICE_UNAVAILABLE: "Brief maintenance is in progress — try again soon.",
  MAINTENANCE: "Brief maintenance is in progress — try again soon.",
  AI_DISABLED: "AI features are temporarily paused — your saved work is safe.",
  NOT_CONFIGURED: "This feature isn't configured on this deployment yet.",
  NETWORK: "You appear to be offline — check your connection and retry.",
};

const GENERIC = "Something interrupted that action — please try again.";

export interface ApiErrorLike {
  code?: string;
  message?: string;
}

/** Map any thrown value to a safe, user-ready sentence. */
export function describeApiError(e: unknown): string {
  // A bare TypeError from fetch() means the request never completed —
  // network/offline. Check before message fallbacks.
  if (typeof TypeError !== "undefined" && e instanceof TypeError) {
    return API_ERROR_COPY.NETWORK;
  }
  if (e && typeof e === "object") {
    const err = e as ApiErrorLike & { code?: unknown };
    const hasCode = typeof err.code === "string" && err.code.length > 0;
    if (hasCode && API_ERROR_COPY[err.code as string]) {
      return API_ERROR_COPY[err.code as string];
    }
    // Only trust server-authored messages on genuine ApiError envelopes
    // (they carry a `code`). Plain Errors never reach the user.
    if (hasCode && typeof err.message === "string" && err.message.trim()) {
      return err.message;
    }
  }
  return GENERIC;
}
