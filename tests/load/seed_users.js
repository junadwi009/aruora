// TV-07 seed helper: creates N test users for the load scenarios.
// Usage: BASE_URL=http://localhost:80 k6 run tests/load/seed_users.js  [N=50]
import http from "k6/http";
import { check } from "k6";

export const options = { vus: 1, iterations: 1 };

const BASE = __ENV.BASE_URL || "http://localhost:80";
const N = Number(__ENV.N || 50);
const PASSWORD = "load-test password 15+ chars";

export default function () {
  for (let i = 0; i < N; i++) {
    const email = `loaduser${i}@loadtest.local`;
    const res = http.post(`${BASE}/api/account/register`,
      JSON.stringify({ email, password: PASSWORD }),
      { headers: { "Content-Type": "application/json" } });
    // 200 (created) or idempotent re-seed (validation/existing-account codes)
    check(res, { "register answered": (r) => r.status === 200 || r.status === 409 || r.status === 422 });
  }
  console.log(`seeded/verified ${N} users (loaduser0..${N - 1}@loadtest.local)`);
}
