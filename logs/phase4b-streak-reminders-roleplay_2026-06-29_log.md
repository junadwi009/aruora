# phase4b-streak-reminders-roleplay — 2026-06-29

Final Phase 4 batch: activity streak, per-word color pronunciation, study reminders, and AI Speaking roleplay. Completes Phase 4.

## Streak + daily goal (`843ee70`)
- `repo.activity_stats` derives current/longest streak + today's count + active-days from the user's attempt timestamps — **no new table**. `GET /api/stats/activity`. Home shows a 🔥 streak + daily-goal card.

## Per-word color pronunciation (`843ee70`)
- The Pronounce drill colors each target word **green (clear) / red (missed)** after an attempt, with a legend. Builds on the existing `wordAccuracy`.

## Study reminders (`36ed4c9`)
- `user_profile` += `reminder_time`/`reminder_last_sent`. `repo.due_reminders`/`mark_reminder_sent`; profile PATCH accepts `reminderTime`; `/me` returns it. Token-protected `POST /api/internal/reminders/run` (`REMINDER_TOKEN`) sends each due user **one reminder per day** via the mailer (hour/today overridable for tests). Settings `RemindersSection` (toggle + hour). README documents the hourly cron; `.env.example` documents SMTP_*/APP_BASE_URL/REMINDER_TOKEN/SESSION_TIMEOUT_MIN.
- Driven by an external scheduler (cron) — no in-process scheduler/dependency added.

## AI Speaking roleplay (`c7aa604`)
- `prompts.ROLEPLAY` + `POST /api/speaking/roleplay` (one partner turn from scenario + history) + offline stub. New `Roleplay` view: pick a scenario → converse by typing or recording (reuses the ASR Recorder) → AI replies each turn → "End & get feedback" runs the speaking examiner over your turns and shows the band feedback. Home quick link.

## Verify
- api `pytest -q` → 126 passed (+7 across the batch). web `npm test` → 50; tsc clean; build OK.
- Live (recreated DB): roleplay → real model reply; reminder time saved; `/api/internal/reminders/run` → 401 without the token (safe default). Streak card + color pronunciation render.

## Caveats
- Reminders fire only if an external cron calls the endpoint AND SMTP is configured (dev logs the email). The reminder hour is the server's clock (no per-user timezone yet).
- Roleplay scoring reuses the single-turn speaking examiner over concatenated user turns — it's a reasonable approximation, not a true multi-turn assessment.
- Streak counts any attempt (writing/speaking/reading/listening practice), once per day.

## Commits
- `843ee70` streak + color pronunciation · `36ed4c9` study reminders · `c7aa604` AI roleplay
