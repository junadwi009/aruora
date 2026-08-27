# 05 — UAT & Validation Strategy

## Core Principle

Controlled users answer:

> **Can people use it?**

Voluntary market users answer:

> **Do people want it enough to return?**

Do not mix these signals.

---

# Wave 0 — Internal QA

Users:
2–5.

Test:
- registration
- auth
- onboarding
- placement
- result
- program
- practice
- progress
- settings
- session recovery
- mobile/desktop
- microphone/audio
- API/LLM failure

Exit:
- P0 = 0
- P1 = 0

---

# Wave 1 — Lecturer Controlled UAT

Recommended:
20–50 students.

Source:
lecturer partnership.

## Purpose
- usability
- comprehension
- bugs
- placement friction
- learning flow
- baseline feedback

## Bias
They may participate because the lecturer asked them to.

Therefore:
- do not treat completion as organic demand
- do not treat praise as strong PMF evidence
- compare against LinkedIn cohort later

---

# Lecturer Expert Review

Lecturer gets a separate evaluation form.

Assess:
- pedagogical logic
- placement reasonableness
- feedback quality
- misleading claims
- skill progression
- learning-plan coherence

Student and lecturer feedback should not use the same questionnaire.

---

# Wave 2 — LinkedIn Market UAT

Recommended:
30–50 qualified learners.

Recruitment framing:

> **ARUORA IELTS — Founding Learner UAT**

Qualification:
- actively preparing / planning IELTS
- scholarship, study, career or retake goal
- willing to use product multiple times
- willing to provide feedback

## Purpose
Measure:
- voluntary signup
- placement completion
- first meaningful action
- D1 / D7 return
- peer-practice interest
- target/deadline profile

---

# Initial Decision Thresholds

These are **working thresholds**, not industry benchmarks.

| Metric | Initial Signal |
|---|---:|
| Registration completion | >80% |
| Placement started | >75% of registered |
| Placement completed | >60% |
| First meaningful session | >45% |
| Placement perceived useful | >70% respondents |
| Plan perceived relevant | >70% respondents |
| D1 meaningful return | >35–40% |
| D7 meaningful return | >20–25% |
| Peer-practice interest | >40% |
| P0/P1 bugs | 0 |

Do not optimize blindly for these numbers. Use qualitative evidence too.

---

# UAT Cohort IDs

Example:

```text
internal_qa_01
lecturer_uat_01
linkedin_uat_01
founding_beta_01
```

Required field:

```text
acquisition_source
```

Suggested enum:

```text
lecturer_partner
linkedin_founder
referral
campus_community
organic
paid
```

---

# Interview Sample

From first 30–50 users, interview:

- 2 heavy users
- 2 normal users
- 2 low-activity users
- 2 churned users
- 2 high-intent scholarship/retaker users

Ask about behavior, not feature wishlists.

Good:
- Why do you need IELTS?
- What did you use before?
- Where do you normally get stuck?
- What do you do when stuck?
- When would you pay a person for help?
- What made you return?

Avoid:
- “What features should we build?”

---

# Exit to Founding Beta

Proceed when:

1. P0/P1 blockers = 0
2. placement/result flow is understood
3. major misleading scoring issues are resolved
4. voluntary users demonstrate meaningful return
5. telemetry is reliable
6. there is at least some peer-practice demand

If retention is weak:
**do not add community to hide the problem.**
