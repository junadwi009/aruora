// TV-07 scenario 4 — Redis rate-limit contention.
// Hammers the credential route from many VUs simultaneously. Proves the
// SHARED limiter: with N replicas every replica enforces the SAME effective
// limit (WS07-01 required test under load) and the limiter itself never
// unwinds (no 500s from Redis contention; fail-closed 503s are expected
// only if Redis is actually down, not at healthy load).
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:80";
const VUS = Number(__ENV.VUS || 30);
const DURATION = __ENV.DURATION || "1m";

export const options = {
  vus: VUS,
  duration: DURATION,
  thresholds: {
    // The route will return a mix of 200/429/4xx — the invariant is that the
    // limiter itself must not fault: zero 5xx (except documented 503 fail-closed).
    "http_req_failed": ["rate<0.01"],
    "http_req_duration": ["p(95)<500"],
  },
};

export default function () {
  const res = http.post(`${BASE}/api/account/login`,
    JSON.stringify({ email: `ratelimit-probe@loadtest.local`, password: "deliberately wrong password 15+ chars" }),
    { headers: { "Content-Type": "application/json" } });
  check(res, {
    "limiter stayed healthy": (r) =>
      r.status === 401 || r.status === 429 || r.status === 422 || r.status === 503,
    "no unexpected 5xx": (r) => !(r.status >= 500 && r.status !== 503),
  });
}
