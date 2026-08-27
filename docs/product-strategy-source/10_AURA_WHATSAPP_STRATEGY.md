# 10 — Aura WhatsApp Strategy

## Strategic Decision

### [High confidence]

WhatsApp is a useful future **entry/re-engagement channel**, but should **not** be the core ARUORA learning product and should **not** be a dependency for initial UAT.

---

# Why

WhatsApp can reduce friction for:
- reminders
- re-engagement
- simple profiling
- result notification
- Study Pod invitation

But:
- core assessment UX is better in ARUORA
- community data should remain owned by ARUORA
- automated messaging has variable cost
- Meta pricing changes are scheduled for 1 October 2026

---

# Current Pricing Constraint

### VERIFIED as of 21 Aug 2026

A Twilio notice describing Meta's announced change states:

From **1 October 2026**:
- service messages / free-form business replies inside the 24-hour customer service window become billable per message
- utility templates inside that window also become billable

Inbound user messages remain free under the described structure.

Special eligible free-entry-point windows remain a separate case.

### Consequence

Do not model Aura WhatsApp as permanently free infrastructure.

---

# Recommended Rollout

## UAT
No bot required.

Optional:
- manual WhatsApp group/channel only if needed operationally
- do not expose users automatically

## Founding Beta
Test optional opt-in:

> “Would you like Aura reminders on WhatsApp?”

Measure demand before building deeply.

## Later
Use API for:
- reminder
- placement result
- reactivation
- match availability
- scheduled Study Pod event

---

# Keep Core in ARUORA

WhatsApp:

```text
communicate
remind
invite
re-engage
```

ARUORA:

```text
assess
train
score
track
match
reputation
mentor/tutor
```

Principle:

> **WhatsApp communicates. ARUORA owns the learning relationship.**

---

# Cost Control

- bundle information in fewer messages
- do not send multiple conversational filler messages
- allow preference / mute
- event-triggered outbound only
- track cost per reactivated learner
- review official Meta rate card before production
- avoid provider markup when direct Cloud API is operationally appropriate

---

# Aura Identity

Customer-facing wording:

> **Chat with Aura**

Never:

> ARUORA WhatsApp Bot

Aura is the companion. “Bot” is implementation detail.
