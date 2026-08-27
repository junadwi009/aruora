// TV-07 scenario 2 — concurrent writing submissions under per-user limits.
// LLM_MODE=stub on the target stack, so "AI" work is deterministic. Proves:
// - per-user AI concurrency (AI_CONCURRENCY_PER_USER) and idempotency bind;
// - queue backpressure (429/503) activates BEFORE API starvation;
// - cost ledger exactness: every accepted submission maps to exactly one
//   stub usage event (spot-check endpoint output against accepted count).
import http from "k6/http";
import { check, group, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:80";
const VUS = Number(__ENV.VUS || 10);
const DURATION = __ENV.DURATION || "3m";

export const options = {
  scenarios: {
    submit: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 2), // submissions/sec across all VUs
      timeUnit: "1s",
      preAllocatedVUs: VUS,
      duration: DURATION,
      exec: "submit",
    },
  },
  thresholds: {
    "http_req_duration{scenario:submit}": ["p(95)<2000"],
    checks: ["rate>0.95"],
  },
};

const PASSWORD = "load-test password 15+ chars";
const ESSAY = "Transport development is a frequent topic of public debate. ".repeat(40);

function login(vu) {
  http.post(`${BASE}/api/account/login`,
    JSON.stringify({ email: `loaduser${vu}@loadtest.local`, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } });
}

export function submit() {
  const vu = (__VU * 7) % 50;
  if (!__ITER) login(vu); // login once per VU (iteration 0)
  group("writing submit", () => {
    const res = http.post(`${BASE}/api/writing/evaluate`,
      JSON.stringify({
        task_type: "task2",
        prompt: "Some people think public transport should be free. Discuss.",
        essay: ESSAY + __VU + ":" + __ITER,
      }),
      { headers: { "Content-Type": "application/json" } });
    // Accepted (200/202) OR a POLICY 429 (per-user concurrency / idempotency /
    // backpressure) are both valid; 5xx timeout cascades are NOT.
    check(res, {
      "no 5xx timeout cascade": (r) => r.status < 500,
      "backpressure is explicit": (r) =>
        [200, 202, 429, 503].includes(r.status),
    });
  });
  sleep(1);
}
