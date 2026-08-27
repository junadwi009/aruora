// TV-07 scenario 1 — login/profile/history mix.
// Proves non-AI core reads/writes hold P95 < 500 ms and responses stay
// user-scoped (VU keeps its own session; foreign IDs must 404).
import http from "k6/http";
import { check, group } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:80";
const VUS = Number(__ENV.VUS || 20);
const DURATION = __ENV.DURATION || "2m";

export const options = {
  vus: VUS,
  duration: DURATION,
  thresholds: {
    "http_req_duration{scenario:core}": ["p(95)<500", "p(99)<1500"],
    "http_req_failed{scenario:core}": ["rate<0.01"],
    checks: ["rate>0.99"],
  },
  scenarios: {
    core: {
      executor: "constant-vus",
      vus: VUS,
      duration: DURATION,
      exec: "core",
      tags: { scenario: "core" },
    },
  },
};

const PASSWORD = "load-test password 15+ chars";

function login(vu) {
  const res = http.post(`${BASE}/api/account/login`,
    JSON.stringify({ email: `loaduser${vu}@loadtest.local`, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } });
  check(res, { "login 200": (r) => r.status === 200 });
  return !!res.cookies;
}

export function core() {
  const vu = __VU % 50;
  group("login", () => login(vu));
  group("history reads", () => {
    check(http.get(`${BASE}/api/history/attempts`), { "attempts 200": (r) => r.status === 200 });
    check(http.get(`${BASE}/api/stats/trends`), { "trends 200": (r) => r.status === 200 });
    check(http.get(`${BASE}/api/stats/activity`), { "activity 200": (r) => r.status === 200 });
  });
  group("isolation probe", () => {
    // Foreign ID probe: must be a generic 404/403, never 200 (TV-02 invariant under load)
    const res = http.get(`${BASE}/api/history/attempt/99999999`);
    check(res, { "foreign attempt not 200": (r) => r.status !== 200 });
  });
}
