import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { I18nProvider, useT, getLang } from "./i18n";

beforeEach(() => localStorage.clear());

function Probe() {
  const { t, lang, setLang } = useT();
  return (
    <div>
      <span data-testid="label">{t("nav.reading")}</span>
      <span data-testid="lang">{lang}</span>
      <span data-testid="missing">{t("does.not.exist")}</span>
      <button onClick={() => setLang("id")}>id</button>
    </div>
  );
}

describe("i18n", () => {
  it("defaults to English and translates after switching to Indonesian", () => {
    render(<I18nProvider><Probe /></I18nProvider>);
    expect(screen.getByTestId("label").textContent).toBe("Reading");
    fireEvent.click(screen.getByText("id"));
    expect(screen.getByTestId("label").textContent).toBe("Membaca");
    expect(getLang()).toBe("id");
  });

  it("falls back to the key for unknown strings", () => {
    render(<I18nProvider><Probe /></I18nProvider>);
    expect(screen.getByTestId("missing").textContent).toBe("does.not.exist");
  });
});
