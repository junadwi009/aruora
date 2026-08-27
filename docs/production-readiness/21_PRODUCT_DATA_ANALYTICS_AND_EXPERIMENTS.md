# 21 — Product Data, Analytics, Cohorts, and Experiments

## Goal

Make product validation measurable before public growth while preventing analytics from becoming a second uncontrolled copy of learner PII and learning content.

## North Star

### Weekly Meaningful Learners (WML)

A learner counts at most once in a rolling 7-day window when they complete at least one meaningful learning action, for example:
- completed a Reading/Listening practice set;
- submitted and received a valid Writing evaluation;
- completed a Speaking practice/evaluation;
- completed a mock;
- completed an assigned Journey session.

Do not count:
- app opens only;
- page views only;
- chat messages only;
- notification opens without learning action;
- streak maintenance actions with no learning value.

## Canonical acquisition/cohort dimensions

Initial `acquisition_source` values:

```text
lecturer_partner
linkedin_founder
referral
campus_community
organic
paid
other
```

Initial cohort pattern:

```text
internal_qa_01
lecturer_uat_01
linkedin_uat_01
founding_beta_01
```

Cohort/source values must be server-owned or validated; never trust arbitrary client strings for analytics segmentation.

## Minimum event taxonomy

Implement a versioned event schema with these event families:

```text
landing_view
signup_started
signup_completed
onboarding_started
goal_selected
destination_selected
target_band_selected
deadline_added
onboarding_completed
placement_started
placement_skill_started
placement_skill_completed
placement_abandoned
placement_completed
result_viewed
program_viewed
program_selected
practice_started
practice_task_served
practice_completed
writing_submitted
speaking_submitted
mock_completed
feedback_viewed
feedback_helpful
app_returned
peer_interest_viewed
peer_opt_in
whatsapp_opt_in
human_help_interest
```

Future gated events:

```text
pod_invited
pod_joined
peer_session_started
peer_session_completed
whatsapp_reactivation
tutor_viewed
tutor_booked
```

Do not emit future-feature events until those surfaces exist.

## Analytics event envelope

Recommended minimum fields:

```json
{
  "event_name": "practice_completed",
  "event_version": 1,
  "event_id": "uuid",
  "occurred_at": "server timestamp",
  "user_id": "internal opaque id",
  "anonymous_id": "optional pre-auth id",
  "cohort_id": "linkedin_uat_01",
  "acquisition_source": "linkedin_founder",
  "properties": {}
}
```

Rules:
- server timestamps for authoritative completion events;
- idempotent event IDs for retryable clients;
- no essay/transcript/audio payload in analytics;
- no email/name/phone in generic event properties;
- coarse destination/category where possible;
- retention and deletion policy documented.

## Derived funnel

```text
Landing
→ Signup
→ Onboarding
→ Placement Started
→ Placement Completed
→ Result Viewed
→ Program Accepted
→ First Meaningful Session
→ D1 meaningful return
→ D7 meaningful return
→ optional Study Pool opt-in
→ optional peer interaction
```

## UAT cohort interpretation

Lecturer-controlled cohort:
- best for usability, bug discovery, comprehension, pedagogical review;
- participation is externally prompted;
- retention cannot be treated as clean market-demand evidence.

LinkedIn cohort:
- voluntary signup gives stronger demand signal;
- measure qualified activation and meaningful return separately.

Never merge these cohorts into a single retention number without breakdown.

## Experiment framework

Every experiment requires:
- hypothesis;
- primary metric;
- guardrail metric;
- cohort/eligibility;
- start/end decision rule;
- exposure event;
- minimum sample caveat;
- result and interpretation.

Initial experiments from product strategy:

1. goal-first vs score-first onboarding;
2. readiness-first vs streak/Flow-first home hierarchy;
3. Study Pool opt-in interest;
4. manual Study Pod usefulness after demand exists;
5. plateau → human-help escalation;
6. optional WhatsApp reminders/re-engagement.

## Analytics integrity

Never optimize only for:
- time in app;
- message volume;
- number of generated exercises;
- Flow length;
- raw registrations.

A metric is useful when it is causally close to learning value, retention of qualified learners, or validated business behavior.

## Privacy and deletion

Product analytics must join the same account-deletion/export governance as the primary database. If using a third-party analytics vendor:
- document vendor/region/retention;
- pseudonymize identity;
- provide deletion propagation where required;
- avoid raw learning text;
- disable session replay on sensitive practice/audio/result surfaces unless separately reviewed.

## Acceptance criteria

- WML is reproducibly computable;
- cohort/source tracking is present before UAT;
- critical funnel events are tested;
- analytics does not contain raw essays/transcripts/audio/secrets;
- lecturer and LinkedIn cohorts can be compared separately;
- product experiments have explicit decision records, not ad-hoc dashboard watching.

## Task Pool analytics

Add low-cardinality, content-free properties/events sufficient to evaluate WS27 without copying tasks into analytics.

Useful internal events/properties:

```text
practice_task_served
  source = pool | custom_generation
  pool_kind
  skill
  difficulty_bucket
  repeat_within_cooldown = true|false

pool_depleted             # operational/server event, not learner content
custom_generation_requested
custom_generation_completed
```

Do not send full task text, answer keys, prompts, model raw output, essays, transcripts, or provider cost secrets to generic product analytics.

Product dashboards should combine analytics with the audited usage ledger to derive:
- pool serve → completion conversion;
- “Try another” behavior;
- recent-repeat perception/actual repeat rate;
- cost per WML;
- cost per activated learner/cohort;
- custom-generation demand before deciding whether to monetize it.


## RAG experiment metrics

When evaluating WS28, do not optimize retrieval metrics in isolation. Compare RAG-grounded vs non-RAG content generation on accepted-task rate, factual defect rate, near-copy rejection, cost per ACTIVE task, learner task completion/helpfulness, and retrieval latency. Preserve cohort/experiment IDs without logging raw learner queries that contain sensitive content.
