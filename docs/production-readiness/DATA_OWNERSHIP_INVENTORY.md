# ARUORA IELTS — Persistent Data Ownership Inventory

WS04-01 deliverable. Source of truth for every persistent entity's owner,
lifecycle, and protection class. Update this table whenever a migration adds a
table or column; review alongside `12_PRIVACY_COMPLIANCE.md`.

Reviewed at commit range introducing revision `c8d21e4b7a30` (2026-08-27).

## Class codes

- **user** — owned by one authenticated profile (`user_id`), scoped in every lookup, deleted on account deletion.
- **global** — shared reference/task-pool content; no owner; must NOT disappear with any user.
- **system** — security/ops metadata; user-attributed but never exported; deleted/pseudonymised per retention policy.
- **draft-profile** — per-browser-session profile before credentials are attached (documented lifecycle, see note below).

## Inventory

| Table | Owner | Owner FK | NOT NULL | Delete behaviour | Export | Retention class | Admin visibility |
|---|---|---|---|---|---|---|---|
| `user_profile` | self | — | — | account deletion deletes row (+ session cookie cleared) | full profile (**excl.** password_hash/google_sub) | account lifetime (PII) | list via admin (minimal fields); never hashes/tokens |
| `skill_levels` | user | user_id | yes | CASCADE from profile | yes (`skillLevels`) | learning state | counts only |
| `placement_combos` | global | — | — | retained | no (content) | task pool | aggregate |
| `placement_items` | global | combo_id | — | retained | no (content) | task pool | aggregate |
| `placement_attempts` | user | user_id | yes | CASCADE | yes (`placementAttempts`) | learning history | counts only |
| `generated_sets` | global | — | — | retired by content process, not users | no (content) | task pool | count only |
| `test_gate` | system | user_id (PK) | yes | CASCADE | **no** (anti-abuse counter) | security | not exposed |
| `feedback` | user | user_id | yes | CASCADE | yes (stars/insight) | user-authored content | surfaced to admin for review |
| `gen_usage` | system | user_id | yes | CASCADE | **no** (entitlement counter; ledger in WS27 supersedes) | billing-adjacent counter | aggregates only |
| `programs` | user | user_id | yes | CASCADE | yes (`programs`) | learning history | counts only |
| `milestones` | user (via program) | program_id → programs.user_id | yes | CASCADE through program | yes (`milestones`) | learning history | counts only |
| `attempts` | user | user_id (**NOT NULL since c8d21e4b7a30**) | yes | CASCADE | yes (`attempts`, incl. scoreMetadata envelope) | learner content (essays/transcripts) | NEVER exposed to other admins/users |
| `mocks` | user | user_id (**NOT NULL**) | yes | CASCADE | yes (`mocks`) | learning history | counts only |
| `lessons` | user | user_id (composite PK) | yes | CASCADE | yes (`lessons`) | cached generated content | counts only |
| `cards` | user | user_id (**NOT NULL**) | yes | CASCADE | yes (`cards`) | learner content | counts only |
| `analytics_events` | system (pseudonymised) | user_id **nullable** | — | CASCADE when attributed; unattributed beacons expire via 180d purge | **no** (content-free by construction; PII-shaped values rejected at write) | bounded retention (180d cron hook `purge_old_analytics_events`) | admin aggregate only (`/api/admin/analytics/summary`), cohorts never merged |
| `user_profile.acquisition_source` / `cohort_id` | user (dimension) | — | no | dies with profile | yes (as dimensions) | account lifetime | admin summary breakdown |

## Session/anonymous draft-profile lifecycle (WS04-02 policy)

A first visit may create an empty `user_profile` bound to the browser session
cookie (no email/password). It holds no PII until:

- registration / Google sign-in attaches credentials to it
  (`attach_credentials` / `upsert_google_user`), or
- every persistent child row (attempts, mocks, cards, programs, lessons,
  feedback, gen_usage, test_gate, skill levels, placement attempts) is written
  with that session's `user_id` — which requires the signed-in session.

Legacy nullable-owner rows from local development are discarded once by
migration `c8d21e4b7a30`; `attempts.user_id`, `mocks.user_id`,
`cards.user_id` are now NOT NULL. No new nullable ownership may be introduced.

## Scoping rules enforced in code

1. Every ID-parameterized read/update/delete includes the ownership predicate
   inside the SQL (`WHERE id = :x AND user_id = :uid`) — fetch-then-compare is
   forbidden (repositories §WS04-03).
2. Nested objects scope through their parent chain
   (`milestones ⋈ programs.user_id`) — parent-chain rule §WS04-05.
3. Cross-user or unallocated IDs return generic 404/`false` — no existence
   disclosure.
4. Admin methods are explicit (list/stats/delete/reset), role-gated against
   ADMIN_EMAILS, paginated (≤500), and return minimal fields (§WS04-06).
5. Export contains only the requesting user's rows + excludes secrets
   (`password_hash`, `google_sub`) and non-portable counters (§WS04-07).
6. Account deletion relies on schema-declared `ON DELETE CASCADE`
   (PostgreSQL prod parity; SQLite dev/test enables `PRAGMA foreign_keys=ON`)
   so new child tables cannot be forgotten (§WS04-04).
7. FK integrity is live on SQLite too, so orphan inserts fail loudly in CI.

## RLS status (WS04-08)

Deferred by design until application-level scoping is fully proven in a
public deployment (per 04 §Task WS04-08). When adopted: transaction-local user
context policies on all `user`-class tables, separate audited background/admin
roles, pooling reset verification. RLS must never replace repository scoping.

## Future ARUORA data classes (reserve rows when introduced)

destination/goal/deadline profile; target & previous-score metadata;
readiness snapshots/recommendations; acquisition/cohort metadata; analytics
identity mapping; notification/channel preferences; Study Pool opt-in &
preferences; Pod membership / peer feedback / blocks & reports; human-help &
tutor interactions — each lands here as **user** (or relationship rows
authorized from BOTH acting user and relationship context) before shipping.
