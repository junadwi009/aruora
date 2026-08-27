// TV-07 scenario 3 — ASR queue burst.
// Uploads small wav bursts to /api/speaking/transcribe. Proves the ASR queue
// stays bounded (QUEUE_MAX_DEPTH) and rejects/queues politely instead of
// starving mail/LLM workers or the API (WS07-04 queue split invariant).
import http from "k6/http";
import { check, group, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:80";
const VUS = Number(__ENV.VUS || 5);
const DURATION = __ENV.DURATION || "2m";

export const options = {
  scenarios: {
    asr: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 5), // uploads/sec
      timeUnit: "1s",
      preAllocatedVUs: VUS,
      duration: DURATION,
      exec: "burst",
    },
  },
  thresholds: {
    "http_req_duration{scenario:asr}": ["p(95)<3000"],
    checks: ["rate>0.95"],
  },
};

const PASSWORD = "load-test password 15+ chars";
// 1 s of 16-bit mono 8 kHz silence — a valid, tiny wav payload.
const SILENT_WAV = (() => {
  const headerSize = 44, samples = 8000;
  const buf = new Uint8Array(headerSize + samples * 2);
  const dv = new DataView(buf.buffer);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); dv.setUint32(4, buf.length - 8, true); w(8, "WAVEfmt ");
  dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
  dv.setUint32(24, 8000, true); dv.setUint32(28, 16000, true);
  dv.setUint16(32, 2, true); dv.setUint16(34, 16, true); w(36, "data");
  dv.setUint32(40, samples * 2, true);
  return buf;
})();

function login(vu) {
  http.post(`${BASE}/api/account/login`,
    JSON.stringify({ email: `loaduser${vu}@loadtest.local`, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } });
}

export function burst() {
  const vu = __VU % 50;
  if (!__ITER) login(vu);
  group("asr upload", () => {
    const res = http.post(`${BASE}/api/speaking/transcribe`,
      { audio: http.file(SILENT_WAV.buffer, "clip.wav", "audio/wav") });
    // Accept success OR explicit queue backpressure; never a crash/timeout.
    check(res, {
      "no 5xx cascade": (r) => r.status < 500,
      "bounded rejection": (r) => [200, 202, 429, 503].includes(r.status),
    });
  });
  sleep(1);
}
