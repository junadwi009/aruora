// Registers jest-dom matchers (toBeDisabled, toBeEnabled, etc.) on Vitest's expect.
import "@testing-library/jest-dom/vitest";

// jsdom doesn't have ResizeObserver — Recharts' ResponsiveContainer needs it.
// Provide a no-op stub so tests don't crash.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// jsdom in this setup doesn't expose localStorage — provide an in-memory shim.
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();
  globalThis.localStorage = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => void store.set(k, String(v)),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size;
    },
  } as Storage;
}
