import {defineConfig} from "@playwright/test";
/** Browser contract regressions with synthetic API fixtures, NOT full-stack UAT. */
export default defineConfig({
  testDir:"./e2e",
  testMatch:"uat-regressions.spec.ts",
  timeout:30000,
  fullyParallel:true,
  retries:0,
  reporter:[["list"],["html",{open:"never"}]],
  use:{baseURL:"http://127.0.0.1:5173",browserName:"chromium",trace:"retain-on-failure",screenshot:"only-on-failure"},
  webServer:{command:"npm run dev -- --host 127.0.0.1",url:"http://127.0.0.1:5173",reuseExistingServer:!process.env.CI,timeout:60000},
});
