# 25 — Aura WhatsApp and Re-engagement Architecture

## Goal

Keep WhatsApp optional and cost-observable. ARUORA owns assessment/training/history; WhatsApp is a communication channel.

## Product boundary

WhatsApp may later:
- remind;
- re-engage;
- notify that a result is ready;
- invite to a Study Pod/session;
- deliver a compact approved summary;
- deep-link back into ARUORA.

WhatsApp must not become the authoritative store for:
- assessment state;
- progress history;
- score calibration;
- peer reputation;
- tutor records.

## UAT rule

No WhatsApp bot is required for internal or lecturer UAT.

Before API implementation, test an explicit preference:

> “Would you like Aura reminders on WhatsApp?”

Measure demand and incremental return before investing deeply.

## Consent/preferences

Store channel preferences separately from account authentication:
- WhatsApp opt-in timestamp;
- phone number in normalized protected field only if actually needed;
- locale/timezone;
- allowed message categories;
- quiet hours;
- unsubscribe/mute timestamp;
- provider message identifiers needed for operations.

Never infer consent from merely having a phone number.

## Security/privacy

- verify webhook signatures according to the chosen provider;
- isolate webhook endpoint from browser session assumptions;
- deduplicate events;
- do not log message bodies by default;
- minimize sensitive score/detail content in push messages;
- use short-lived authenticated deep links rather than embedding private data in URLs;
- rate-limit outbound and inbound automation;
- support STOP/unsubscribe semantics appropriate to channel/provider/regulation.

## Cost model

Pricing and provider policy are time-sensitive external dependencies. Before implementation or launch, re-check official Meta/provider pricing and template rules.

Track at minimum:
- messages sent by category;
- provider cost;
- cost per delivered reminder;
- cost per reactivated meaningful learner;
- opt-out rate;
- incremental WML/D7 contribution.

Do not assume the channel is permanently free.

## Architecture

Recommended flow:

```text
product event
→ notification policy
→ consent + quiet-hours check
→ outbound job queue
→ provider adapter
→ delivery webhook
→ message audit metadata
```

Provider adapter should be replaceable without changing product-domain logic.

## Aura voice

Customer-facing identity may say **Aura** / **Chat with Aura**. “Bot” is implementation detail.

Messages should be compact and action-oriented, not conversational filler that multiplies cost.

## Acceptance criteria before enabling

- explicit opt-in/out;
- verified webhook security;
- queue/retry/idempotency;
- quiet hours;
- cost dashboard/budget alert;
- privacy notice updated;
- deep links are safe;
- core product works fully without WhatsApp.
