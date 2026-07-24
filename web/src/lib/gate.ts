import { useCallback, useEffect, useRef, useState } from "react";
import { api, type GateStatus } from "./api/client";

export function computeShouldBeat(s: {
  visible: boolean; focused: boolean; unlocked: boolean; isAdmin: boolean;
}): boolean {
  return s.visible && s.focused && !s.unlocked && !s.isAdmin;
}

export function useGate() {
  const [status, setStatus] = useState<GateStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const timer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await api.gateStatus();
      setStatus(s);
    } catch {
      setStatus(null); // signed-out / error → no gate
    } finally {
      setLoading(false);
    }
  }, []);

  const markUnlocked = useCallback(() => {
    setStatus((prev) => (prev ? { ...prev, locked: false, unlocked: true } : prev));
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    if (!status) return;
    const intervalMs = Math.max(15, status.heartbeatSec) * 1000;
    timer.current = window.setInterval(async () => {
      const should = computeShouldBeat({
        visible: document.visibilityState === "visible",
        focused: document.hasFocus(),
        unlocked: status.unlocked,
        isAdmin: status.isAdmin,
      });
      if (!should) return;
      try {
        const r = await api.gateHeartbeat(status.heartbeatSec);
        if (r.locked) setStatus((prev) => (prev ? { ...prev, locked: true } : prev));
      } catch { /* ignore transient heartbeat errors */ }
    }, intervalMs);
    return () => { if (timer.current) window.clearInterval(timer.current); };
  }, [status]);

  return { locked: !!status?.locked, loading, refresh, markUnlocked };
}
