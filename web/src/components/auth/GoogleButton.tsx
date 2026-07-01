import React, { useEffect, useRef } from "react";
import { api } from "../../lib/api/client";
import type { AccountUser } from "../../lib/types";

// Minimal typing for the Google Identity Services global.
interface GsiId {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
  renderButton: (el: HTMLElement, o: Record<string, unknown>) => void;
}
declare global {
  interface Window {
    google?: { accounts?: { id?: GsiId } };
  }
}

const GIS_SRC = "https://accounts.google.com/gsi/client";
let gisPromise: Promise<void> | null = null;

function loadGis(): Promise<void> {
  if (gisPromise) return gisPromise;
  gisPromise = new Promise<void>((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const s = document.createElement("script");
    s.src = GIS_SRC;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load Google Sign-In"));
    document.head.appendChild(s);
  });
  return gisPromise;
}

/**
 * "Sign in with Google" button (Google Identity Services). On success the ID
 * token is POSTed to /api/account/google, which verifies it and signs the user
 * in (by google_sub). Renders nothing if GIS fails to load.
 */
export const GoogleButton: React.FC<{
  clientId: string;
  onSuccess: (u: AccountUser) => void;
  onError?: (msg: string) => void;
}> = ({ clientId, onSuccess, onError }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    loadGis()
      .then(() => {
        const gid = window.google?.accounts?.id;
        if (cancelled || !gid || !ref.current) return;
        gid.initialize({
          client_id: clientId,
          callback: (resp) => {
            api.accountGoogle(resp.credential)
              .then(onSuccess)
              .catch((e) => onError?.(e instanceof Error ? e.message : "Google sign-in failed"));
          },
        });
        gid.renderButton(ref.current, {
          type: "standard", theme: "outline", size: "large",
          text: "continue_with", shape: "pill", width: 320,
        });
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [clientId, onSuccess, onError]);

  return <div ref={ref} className="flex justify-center min-h-11" />;
};
