// TV-07 scenario 5 — progress/history with realistic row counts.
// Seeds each of the N users with S attempts (default 200 → 50 users = 10k
// rows) via direct DB seeding is out of k6 scope; this scenario assumes the
// staging DB was pre-seeded (see README). Proves indexed history queries hold
// P95 < 500 ms with realistic volumes (WS08-09: (user_id, created_at) index
// follow-up is validated here).
import http from "k6/http";
import { check, group } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:80";
const VUS = Number(__ENV.VUS || 20);
const DURATION = __ENV.DURATION || "2m";

export const options = {
  vus: VUS,
  duration: DURATION,
  thresholds: {
    "http_req_duration{scenario:progress}": ["p(95)<500"],
    "http_req_failed{scenario:progress}": ["rate<0.01"],
  },
  scenarios: {
    progress: {
      executor: "constant-vus",
      vus: VUS,
      duration: DURATION,
      exec: "progress",
      tags: { scenario: "progress" },
    },
  },
};

const PASSWORD = "load-test password 15+ chars";

export function progress() {
  const vu = __VU % 50;
  if (!__ITER) {
    http.post(`${BASE}/api/account/login`,
      JSON.stringify({ email: `loaduser${vu}@loadtest.local`, password: PASSWORD }),
      { headers: { "Content-Type": "application/json" } });
  }
  group("history + trends on realistic volumes", () => {
    check(http.get(`${BASE}/api/history/attempts`), {
      "attempts 200": (r) => r.status === 200,
    });
    check(http.get(`${BASE}/api/stats/trends`), {
      "trends 200": (r) => r.status === 200,
    });
  });
}
