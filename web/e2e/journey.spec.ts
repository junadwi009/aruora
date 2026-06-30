import { test, expect, Page } from "@playwright/test";

// These run against the live stack (docker compose up). They are resilient to
// whether a profile already exists: the "I already have a profile" shortcut on
// Welcome forces the app shell, and if the app auto-enters the shell we skip it.

async function enterApp(page: Page) {
  await page.goto("/");
  // Wait for either Welcome (Get started) or the app shell (Dashboard).
  await Promise.race([
    page.getByRole("button", { name: /get started/i }).waitFor({ timeout: 15_000 }),
    page.getByRole("heading", { name: /dashboard/i }).waitFor({ timeout: 15_000 }),
  ]);
  const welcome = page.getByRole("button", { name: /get started/i });
  if (await welcome.isVisible().catch(() => false)) {
    await page.getByRole("button", { name: /already have a profile/i }).click();
  }
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
}

test("loads and shows the IELTS Coach app", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.goto("/");
  await expect(page.getByText(/IELTS Coach|Dashboard/).first()).toBeVisible({ timeout: 15_000 });
  // no hard crash in the console
  expect(errors.join("\n")).not.toMatch(/Uncaught|is not a function/);
});

test("enters the app shell and navigates to Vocabulary", async ({ page }) => {
  await enterApp(page);
  // "Vocab" appears in both the sidebar and the Home quick links — first is fine.
  await page.getByRole("button", { name: /^vocab$/i }).first().click();
  await expect(page.getByRole("heading", { name: /vocabulary/i })).toBeVisible();
});

test("enters the app shell and opens the Mock Test", async ({ page }) => {
  await enterApp(page);
  // "Test" appears in both the sidebar and the Home quick links — first match is fine.
  await page.getByRole("button", { name: /^test$/i }).first().click();
  await expect(page.getByText(/Listening \+ Reading mock/i)).toBeVisible();
});
