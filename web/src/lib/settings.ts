// Theme + accessible-font preferences, persisted in localStorage and applied to
// <html> (the .dark class + --font-* overrides defined in app.css / fonts.css).

export type Theme = "light" | "dark";
export type Font = "default" | "dyslexic" | "hyperlegible";

const THEME_KEY = "ielts.theme";
const FONT_KEY = "ielts.font";

// Each non-default font overrides BOTH the UI and reading stacks (all four
// families are already bundled via fonts.css — nothing here is wasted).
// Each non-default font overrides the UI, reading, AND display stacks so an
// a11y font applies to headings too (accessibility wins over the brand face).
const FONT_STACKS: Record<Exclude<Font, "default">, { ui: string; reading: string }> = {
  dyslexic: {
    ui: '"OpenDyslexic", "Atkinson Hyperlegible", system-ui, sans-serif',
    reading: '"OpenDyslexic", "Atkinson Hyperlegible", system-ui, sans-serif',
  },
  hyperlegible: {
    ui: '"Atkinson Hyperlegible", system-ui, sans-serif',
    reading: '"Atkinson Hyperlegible", system-ui, sans-serif',
  },
};

export function getTheme(): Theme {
  return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
}

export function getFont(): Font {
  const f = localStorage.getItem(FONT_KEY);
  return f === "dyslexic" || f === "hyperlegible" ? f : "default";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function applyFont(font: Font): void {
  const root = document.documentElement.style;
  if (font === "default") {
    root.removeProperty("--font-ui");
    root.removeProperty("--font-reading");
    root.removeProperty("--font-display");
    return;
  }
  const stack = FONT_STACKS[font];
  root.setProperty("--font-ui", stack.ui);
  root.setProperty("--font-reading", stack.reading);
  // Headings/brand follow the a11y font too (falls back to the brand face when default).
  root.setProperty("--font-display", stack.ui);
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
}

export function setFont(font: Font): void {
  localStorage.setItem(FONT_KEY, font);
  applyFont(font);
}

/** Apply persisted preferences — call once at app boot. */
export function applySettings(): void {
  applyTheme(getTheme());
  applyFont(getFont());
}
