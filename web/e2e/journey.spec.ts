import { test, expect, Page } from "@playwright/test";

// Runs against the live stack (docker compose up). With multi-user accounts the
// app shell sits behind a real account + completed placement, so the e2e focuses
// on the journey *entry points* (load, login, onboarding). The in-app features
// are covered by the unit suite.

async function freshWelcome(page: Page) {
  await page.context().clearCookies();
  await page.goto("/");
  // Wait for Welcome (a returning logged-in session would skip it, but a fresh
  // context has no cookie).
  await page.getByRole("button", { name: /get started/i }).waitFor({ timeout: 15_000 });
}

test("loads and shows the IELTS Coach app", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.goto("/");
  await expect(page.getByText(/IELTS Coach|Dashboard/).first()).toBeVisible({ timeout: 15_000 });
  expect(errors.join("\n")).not.toMatch(/Uncaught|is not a function/);
});

test("i18n: Indonesian translates the Welcome screen", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ielts.lang", "id"));
  await page.reload();
  // "Get started" → "Mulai" in Indonesian
  await expect(page.getByRole("button", { name: /^mulai$/i })).toBeVisible({ timeout: 15_000 });
  await page.evaluate(() => localStorage.removeItem("ielts.lang"));
});

test("Welcome → sign-in screen", async ({ page }) => {
  await freshWelcome(page);
  await page.getByRole("button", { name: /already have an account/i }).click();
  await expect(page.getByRole("heading", { name: /welcome back/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /^sign in$/i })).toBeVisible();
});

test("Welcome → Get started → onboarding", async ({ page }) => {
  await freshWelcome(page);
  await page.getByRole("button", { name: /get started/i }).click();
  // Onboarding step 1 asks for a name.
  await expect(page.getByLabel(/name/i)).toBeVisible();
});

test("a registered account can sign in", async ({ page, request }) => {
  // Seed an account via the API, then sign in through the UI.
  const email = "e2e@example.com";
  await request.post("http://localhost:5050/api/account/register", {
    data: { email, password: "secret123" },
  });
  await request.post("http://localhost:5050/api/account/logout");

  await freshWelcome(page);
  await page.getByRole("button", { name: /already have an account/i }).click();
  await page.getByPlaceholder(/you@example/i).fill(email);
  await page.getByPlaceholder(/6 characters/i).fill("secret123");
  await page.getByRole("button", { name: /^sign in$/i }).click();
  // A signed-in account with no placement yet lands back on Welcome (no skill
  // levels) — the key assertion is that login succeeded without an error alert.
  await expect(page.getByRole("alert")).toHaveCount(0);
});
