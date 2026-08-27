# ARUORA IELTS — Privacy Notice (canonical)

Status: **DRAFT for legal review** — publish the web version
(`web/public/legal/privacy.html`) only after operator details are filled in and
legal sign-off. Mirrored as a static public page so it is reachable **before
public signup** (WS12-03).

Canonical policy workstream: WS12. This document is engineering-owned;
final wording/applicability requires legal review (Indonesia PDP Law
UU No. 27/2022; GDPR assessment if/when offered to EU data subjects).

---

## 1. Operator and contact

- Operator: **[OPERATOR LEGAL ENTITY]** ("ARUORA", "we")
- Contact/DSR inbox: **[PRIVACY@CONTACT]** · Security/breach contact: **[SECURITY@CONTACT]**
- Response SLA for data-subject requests: **[SLA — align with applicable law; internal target 14 days]**

## 2. What we collect

| Category | Examples | Purpose |
|---|---|---|
| Account data | email, display name | authentication, account recovery |
| Profile data (optional) | country, exam date, bio, avatar, goal/target band | product features, readiness estimate |
| Learning content | practice essays, speaking transcripts | scoring feedback (AI-estimated) |
| Learning history | attempts, scores, cards, programs, lessons | progress tracking, export |
| Voice recordings | speaking practice audio | transcription/scoring only — **ephemeral by default (deleted after processing, ≤ 30 min)**, never used for speaker identification |
| Security metadata | hashed IP, device string, audit events | fraud/abuse prevention, security |
| Product analytics | content-free events (names, counts, cohort tags) | improving the product; **never** raw essays/transcripts/audio |
| Payment data | none collected today | — |

We do **not** collect nationality, date of birth, gender, or identity
documents. Eligibility is self-declared (see Terms: adult-only beta).

## 3. AI processing disclosure

Practice content (essays, transcripts, generated-task inputs) is processed by
third-party AI providers **through the OpenRouter router** to produce
estimated feedback. Sub-processors for the current release are listed in the
public vendor register (maintained in-repo: `docs/privacy/VENDOR_REGISTER.md`,
summarised in the published notice). Speech-to-text runs **locally** on our
server (faster-whisper) — no third party receives raw audio.

- AI band scores are **estimates**, not official IELTS results.
- Your content is **not** used to train models. If this ever changes it will
  require separate, explicit opt-in consent.

## 4. Retention

| Data | Retention |
|---|---|
| Account + learning data | until you delete your account (then removed by cascade; financial/audit records kept per policy, de-identified) |
| Raw audio | deleted immediately after transcription (TTL ≤ 30 min for stuck files) |
| Security/audit metadata | bounded security retention (policy: review per release) |
| Analytics events | max 180 days (purge job) |
| Expired sessions/tokens | purged within 72 h / 168 h of expiry |

## 5. Your rights

Depending on applicable law you may request: access/export, correction,
deletion, consent withdrawal, and restriction/objection. Engineering support:

- **Export**: Settings → Export (full JSON of your learning data).
- **Deletion**: Settings → Delete account (immediate cascade delete).
- **Correction**: profile editing in-app.
- Requests may also be sent to **[PRIVACY@CONTACT]**; we verify identity
  in-app before acting on sensitive operations.

## 6. Cookies and local storage

We use only strictly-necessary cookies: an opaque session cookie (`ar_sid`)
and a CSRF cookie. No advertising or cross-site tracking cookies. Product
analytics events are content-free and pseudonymous.

## 7. International transfers

AI sub-processors may process content outside your country. The vendor
register records regions/transfer bases per release; we apply the strictest
available retention/training opt-outs at the router.

## 8. Security & breach notification

Encryption in transit; least-privilege database roles; no raw audio
retention; secrets injected by the deployment environment. Suspected breaches:
**[SECURITY@CONTACT]**. We are prepared to meet statutory notification
timelines, including Indonesia PDP 3×24-hour written notification where
applicable (runbook: `docs/runbooks/INCIDENT_RESPONSE.md`).

## 9. Children

This beta is **not** directed at minors and eligibility is adult-only
(see Terms). If we later serve minors, jurisdiction-specific age/consent
flows will be built first (WS12-08).
