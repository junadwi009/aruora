# ARUORA Market & Product Strategy v1.0

**Product:** ARUORA  
**Initial Track:** ARUORA IELTS  
**Initial Market:** Indonesia  
**Status:** Recommended execution baseline  
**Research cutoff:** 21 August 2026  

---

## Executive Decision

ARUORA should **not** launch as a broad language-learning platform and should **not** compete on “AI IELTS practice” alone.

### Recommended strategy

> **Indonesia-first → IELTS-only → Free Founding Beta → Controlled UAT → Market UAT → learner pooling → manual Study Pods → community automation → verified mentor/tutor supply.**

Initial sequence:

```text
Internal QA
    ↓
Lecturer / Student Controlled UAT
    ↓
Fix product + scoring + onboarding friction
    ↓
LinkedIn Market UAT
    ↓
Free Founding Beta
    ↓
Study Pool
    ↓
Manual Study Pods
    ↓
Community Beta
    ↓
Human Feedback Validation
    ↓
Peer Mentor / Tutor Pilot
```

---

## Why this recommendation

1. ARUORA already enters a crowded IELTS-prep space.
2. Official providers now offer free AI-assisted preparation and personalized study tools.
3. Therefore “AI + adaptive practice” is **not sufficient differentiation**.
4. ARUORA's stronger opportunity is to become a **goal-driven preparation network**:
   - current readiness
   - target score
   - deadline
   - scholarship / study / career context
   - similar-level learner matching
   - peer practice
   - escalation to qualified humans
5. The lecturer partnership gives ARUORA a low-risk controlled UAT cohort before exposing the product to organic market users.
6. LinkedIn is suitable for the second cohort because users who voluntarily join provide a cleaner signal of real demand than students who were instructed to participate.
7. Community and tutor marketplace must be earned through observed behavior, not built upfront.

---

## Key Strategic Rule

> **Do not optimize for registered users. Optimize for density of serious learners.**

Early North Star:

### Weekly Meaningful Learners (WML)

A user counts when they complete at least one meaningful learning action in a rolling week.

Examples:
- completed Reading/Listening set
- submitted Writing
- completed Speaking practice
- completed mock assessment
- completed assigned learning session

---

## Pack Structure

| File | Purpose |
|---|---|
| `00_RECOMMENDED_STRATEGY.md` | Final chosen strategy |
| `01_MARKET_EVIDENCE.md` | Verified market evidence and limitations |
| `02_COMPETITIVE_LANDSCAPE.md` | Competitive implication |
| `03_TARGET_SEGMENTS_AND_JTBD.md` | Audience by behavior/job-to-be-done |
| `04_POSITIONING_AND_VALUE_PROP.md` | Product positioning |
| `05_UAT_AND_VALIDATION.md` | Lecturer + LinkedIn UAT |
| `06_ACQUISITION_AND_POOLING.md` | User acquisition and founding pool |
| `07_MATCHING_AND_STUDY_PODS.md` | Similar-level learner matching |
| `08_COMMUNITY_FLYWHEEL.md` | Community lifecycle |
| `09_TUTOR_SUPPLY_STRATEGY.md` | Community-to-tutor model |
| `10_AURA_WHATSAPP_STRATEGY.md` | WhatsApp role and cost constraints |
| `11_MONETIZATION_HYPOTHESES.md` | What to monetize later |
| `12_ANALYTICS_AND_EXPERIMENTS.md` | Event tracking and metrics |
| `13_PRODUCT_ROADMAP.md` | Recommended phased roadmap |
| `14_RISK_REGISTER.md` | Main strategic risks |
| `15_SOURCE_REGISTER.md` | Source register |
| `16_AGENT_EXECUTION_GUIDE.md` | How Codex/Claude should use this pack |

---

## Evidence Labels

Throughout this pack:

- **VERIFIED** = supported by a source listed in `15_SOURCE_REGISTER.md`
- **COMMUNITY SIGNAL** = anecdotal behavior found in public user discussions; useful for hypothesis generation, not prevalence estimates
- **HYPOTHESIS** = ARUORA product/business assumption that requires validation
- **DECISION** = recommended implementation choice based on current evidence and constraints

---

## Important Limitation

No reliable public source was found that establishes the exact Indonesian **IELTS preparation software market TAM/SAM/SOM**.

This pack therefore does **not** invent a market-size number.

Demand is assessed using proxies:
- scholarship applicant volume
- outbound student demand
- IELTS test economics
- official IELTS-prep competition
- LinkedIn audience availability
- learner behavior signals
- later JLPT/Japan opportunity

Actual ARUORA market sizing should be recalculated after Founding Beta using first-party:
- qualified signup rate
- target distribution
- retention
- exam intent
- willingness to pay
- conversion to human help
