# speaking-asr-whisper — 2026-06-29

Phase 2b-2: local speech-to-text for the Speaking tab via **faster-whisper** (model `base`, CPU/int8). Replaces the typed-only "ASR deferred" placeholder with a real record → transcribe → edit flow. Fully offline (model baked into the api image); transcript stays editable and the typed fallback survives when ASR is off.

## What changed
- **`api/app/services/asr.py`** (new) — `transcribe(audio_bytes, config)` decodes the upload (PyAV handles webm/opus/wav/m4a/mp3 — no system ffmpeg) and returns `{transcript, language, durationSec, model, asr:true}`. `WhisperModel` is a process-level singleton keyed by (model,device,compute_type), loaded lazily on first call. `asr_ready(config)` is a **cheap** probe (config flag + `importlib.util.find_spec("faster_whisper")`, no model load) used by `/api/health`. Any load/decode/transcribe failure surfaces as `ApiError("ASR_UNAVAILABLE", 502)` so the route keeps the typed fallback usable.
- **`api/app/routes/speaking.py`** — new `POST /api/speaking/transcribe` accepting a multipart `audio` file → `asr.transcribe`; 422 on missing/empty audio.
- **`api/app/routes/health.py`** — `asrReady` now reflects `asr_ready(cfg)` (was hard-coded `false`).
- **`api/app/config.py`** — `ASR_ENABLED` / `ASR_MODEL` / `ASR_DEVICE` / `ASR_COMPUTE_TYPE` (+ a `_truthy` helper). **`.env.example`** documents them.
- **`api/requirements.txt`** — `faster-whisper==1.1.1` (pulls ctranslate2 + PyAV + tokenizers/onnxruntime). **`api/Dockerfile`** — bakes the `base` model into the HF cache at build time and sets `HF_HUB_OFFLINE=1` so runtime needs no network (~+145 MB image).
- **`web/src/lib/api/client.ts`** — `speakingTranscribe(blob)` + an `upload()` helper that sends `FormData` **without** forcing `Content-Type` (browser sets the multipart boundary). **`web/src/lib/types.ts`** — `Transcript` type.
- **`web/src/components/speaking/Recorder.tsx`** (new) + **`Speaking.tsx`** — Recorder probes health `asrReady` + browser `MediaRecorder` support; records mic audio, POSTs the blob, appends the transcript into the still-editable textarea; degrades to an explicit "voice recording unavailable, type instead" card when ASR is off or recording is unsupported/blocked.

## Decisions
- **faster-whisper over openai-whisper** — CTranslate2 backend is far faster/smaller on CPU; `base` + `int8` is the speed/size sweet spot for a single-user app. Model is configurable via env but only `base` is baked offline.
- **Multipart upload, not base64 JSON** — avoids a ~33% payload bloat on audio and keeps the existing JSON request helper untouched.
- **Transcript is editable** — IELTS Speaking is scored on the transcript; ASR is imperfect, so the learner can correct it before Evaluate. This also means a transcribe failure never blocks scoring.

## How to verify
- Unit (offline, model mocked): `cd api && .venv/Scripts/python -m pytest -q` → **65 passed** (8 new: 5 asr wrapper + 2 route + 1 health probe). `cd web && npm test` → **15 passed** (new client multipart test); `npx tsc --noEmit` clean; `npm run build` OK.
- Live (real model): _see Verification below._

## Verification (live)
Rebuilt the api image (`docker compose build api` → exit 0; image ~1.38 GB → grows for the whisper stack + baked model) and recreated the container.
- `GET /api/health` → `{"ok":true,"asrReady":true,"llmMode":"live","providerConfigured":true}` — the cheap probe sees the baked model without loading it.
- Generated a known speech sample via Windows SAPI ("**The library opens at nine o'clock every morning and many students go there to study quietly.**") and POSTed it:
  - `POST /api/speaking/transcribe` (multipart wav) → `200`, `{"asr":true,"language":"en","durationSec":5.79,"model":"base","transcript":"The library opens at 9 o'clock every morning and many students go there to study quietly."}` — near-perfect (Whisper normalized "nine" → "9").
- `POST /api/speaking/transcribe` with no file → `422 {"error":{"code":"VALIDATION",...}}`.

## Caveats / known limits
- `base` is the smallest useful multilingual model; accuracy on heavy accents / noisy mics is limited. Larger models (`small`/`medium`) are env-switchable but not baked (would need `HF_HUB_OFFLINE=0` or a rebuild).
- CPU/int8 transcription of a ~6s clip took ~9–10s wall in the container (`beam_size=5`); gunicorn timeout is already 120s (raised in Phase 2a) so even a full 2-min answer is within budget. Drop `beam_size` to 1 if latency matters more than accuracy.
- **Per-worker model load:** the singleton is per process, and the api runs **2 gunicorn workers**, so the first request to *each* worker pays a one-time model load (~1–2s). Both live calls above were ~9–10s because each likely hit a different (cold) worker; a third call to a warm worker is faster. A warm-up at boot or `--workers 1` would make latency uniform.
- No pronunciation/fluency scoring from the audio itself yet — only the transcript feeds the examiner. Phoneme-level pronunciation assessment remains a future phase.

## Commits
- `3fe16bd` feat(api): local faster-whisper ASR for Speaking transcribe
- `b73b15d` feat(web): voice recording + local transcription on Speaking
- `2ac0203` build(api): bake faster-whisper base model; docs: ASR update log
