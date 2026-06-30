import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: true, port: 5173 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    // keep vitest to unit tests under src/; Playwright e2e specs live in ./e2e
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
