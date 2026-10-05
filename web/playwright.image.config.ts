import {defineConfig} from "@playwright/test";

export default defineConfig({
  testDir:"./e2e",
  testMatch:"image-stack.spec.ts",
  timeout:120000,
  expect:{timeout:30000},
  workers:1,
  retries:0,
  reporter:[["list"],["html",{outputFolder:"image-playwright-report",open:"never"}]],
  outputDir:"image-test-results",
  use:{baseURL:"https://localhost:8443",browserName:"chromium",ignoreHTTPSErrors:true,
       trace:"retain-on-failure",screenshot:"only-on-failure"},
});
