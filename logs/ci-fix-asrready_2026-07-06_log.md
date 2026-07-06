# CI fix — env-dependent asrReady assertion + action bumps — 2026-07-06

CI job `API (pytest)` was red on **all three runs** (from the very first push,
`ccff585`) — a latent, environment-dependent test, not a regression from the
audit/redesign work.

## Root cause
`tests/test_health.py::test_health_ok` asserted `body["asrReady"] is False`, but
`asr_ready()` returns True whenever `ASR_ENABLED` (default on) **and**
`faster_whisper` is importable. Any full `pip install -r requirements.txt` (CI,
Docker, fresh venv) installs faster-whisper → `asrReady=True` → assert fails.
It passed locally only because the owner's `api/.venv` happens to **lack**
faster-whisper (verified: `find_spec('faster_whisper') → None` locally, present in
a clean venv). Reproduced by building a clean venv from `requirements.txt` and
running pytest: `1 failed (test_health_ok), 175 passed` — matching CI.

## What changed (files)
- `api/tests/test_health.py` — `test_health_ok` now builds the app with
  deterministic overrides `{"ASR_ENABLED": False, "LLM_MODE": "stub"}` so the
  assertion no longer depends on which packages happen to be installed or on
  ambient env vars. (The companion test already monkeypatches `asr_ready`.)
- `.github/workflows/ci.yml` — bumped `actions/checkout@v4→v7`,
  `actions/setup-python@v5→v6`, `actions/setup-node@v4→v6` to clear the
  "Node.js 20 deprecated" warnings.

## How to test / verify
- Clean venv (CI parity): `python -m venv x && x/Scripts/pip install -r api/requirements.txt
  && x/Scripts/python -m pytest -q api/tests/test_health.py` → 2 passed (was 1 failed).
- Local venv: still 2 passed. Full local suite unaffected.
- After push: CI run on GitHub should go green (watched via the public API).

## Caveats
- Owner's local `api/.venv` is missing `faster-whisper` (drifted from
  requirements.txt). Harmless for the suite now, but `pip install -r
  requirements.txt` locally would restore parity (~300 MB of wheels).
- During the clean-venv repro, spaCy failed to import in the *scratchpad* venv
  ("DLL load failed … filename too long" — Windows long-path artifact of the
  deep temp directory, causing 1 skip). Not related to CI, which downloads the
  model fine on Linux.

## Commit
- `2bf8bd5` — fix(ci): make health asrReady assertion environment-independent. Pushed with the Progress rollout.
