import { describe, it, expect, beforeEach } from "vitest";
import { getTheme, setTheme, getFont, setFont, applySettings } from "./settings";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.className = "";
  document.documentElement.removeAttribute("style");
});

describe("settings", () => {
  it("defaults to light + default font", () => {
    expect(getTheme()).toBe("light");
    expect(getFont()).toBe("default");
  });

  it("persists and applies the dark theme", () => {
    setTheme("dark");
    expect(getTheme()).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    setTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("applies a dyslexia font by overriding --font-ui", () => {
    setFont("dyslexic");
    expect(getFont()).toBe("dyslexic");
    expect(document.documentElement.style.getPropertyValue("--font-ui")).toMatch(/OpenDyslexic/i);
  });

  it("applySettings restores persisted choices on boot", () => {
    localStorage.setItem("ielts.theme", "dark");
    localStorage.setItem("ielts.font", "hyperlegible");
    applySettings();
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.style.getPropertyValue("--font-ui")).toMatch(/Atkinson/i);
  });
});
