import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./fonts.css";
import "./app.css";
import App from "./App";
import { applySettings } from "./lib/settings";
import { I18nProvider } from "./lib/i18n";

// Apply persisted theme + font before first paint.
applySettings();

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("No #root element found");

createRoot(rootEl).render(
  <StrictMode>
    <I18nProvider>
      <App />
    </I18nProvider>
  </StrictMode>
);
