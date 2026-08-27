# 04 — Multi-User Data Isolation and Authorization

## Goal
Make cross-user data access structurally difficult and regression-testable. This workstream addresses OWASP API object-level authorization risk, not just login.

## Current risks to eliminate
The reviewed schema has several persistent entities with nullable `user_id`, manual child deletion, and newer user-owned tables not included in account deletion. A public platform cannot rely on “the UI only sends my IDs.”

## WS04 ownership
Expected areas:
- `api/app/data/models.py`
- `api/app/data/repositories.py`
- Alembic migrations
- every route that accepts a user-owned object ID
- repository/authorization/account-deletion tests

This workstream owns the core user-ownership migration. WS03 should consume it rather than creating a competing ownership migration.

## Task WS04-01 — Inventory every persistent entity
Create a table in code/docs listing for each model:
- owner type: user / global reference / admin/system;
- FK path to owner;
- nullable?;
- delete behavior;
- export behavior;
- retention class;
- admin visibility.

Minimum reviewed user-owned candidates include profiles/accounts, skill levels, placement attempts, test gate, feedback, generation usage, programs/milestones, attempts, mocks, lessons, cards, reminders/account metadata, and any future audio/job records.

## Task WS04-02 — Remove ambiguous anonymous persistence
For a public multi-user release, persistent learner history should require an authenticated account unless anonymous persistence has a fully separate tenant key and lifecycle.

Recommended default:
- public/anonymous users may view landing/demo content;
- persistent attempts/cards/programs/etc. require `user_id NOT NULL`;
- migrate or delete old anonymous rows according to a one-time documented migration policy.

Do not leave nullable ownership merely because old local development supported anonymous use.

## Task WS04-03 — Scoped repository methods
Forbidden pattern:
```python
row = session.get(Attempt, attempt_id)
# later compare user_id
```

Preferred pattern:
```python
select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == uid)
```

The ownership predicate should be part of the data lookup. Return not-found semantics that do not disclose another user’s object existence.

Apply this to get/update/delete/history/detail/milestone/card and every future ID route.

## Task WS04-04 — Foreign keys and cascades
For true user-owned child rows:
- add intentional `ON DELETE CASCADE` where account deletion should remove the child;
- mirror appropriate SQLAlchemy relationship/passive-delete semantics if relationships are introduced;
- use `RESTRICT`/no cascade for global reference data that must not disappear;
- add indexes needed for cascade/scoped lookups.

Account deletion should not maintain a fragile hard-coded list of every future child table.

## Task WS04-05 — Parent-chain ownership
`Milestone` is owned through `Program`. Any milestone CRUD must scope through the parent’s `user_id`, not trust that a milestone ID belongs to the current user.

Use the same rule for nested future objects.

## Task WS04-06 — Admin access model
Never reuse ordinary repository functions with “skip ownership checks” booleans.

Use explicit admin/service methods with:
- role check at route/service boundary;
- audit event;
- minimal returned fields;
- pagination;
- no password hashes/reset tokens/session IDs.

## Task WS04-07 — Data export and deletion
Export:
- contains only the requesting user’s data;
- includes all user-owned product data that the privacy policy says is portable;
- excludes secrets/internal security metadata that should not be disclosed;
- supports large export through a job if necessary.

Deletion:
- API is idempotent from user perspective;
- cascades all user-owned persistent data or puts data into a documented deletion queue if external blobs/vendors are involved;
- deletes/revokes sessions, reset tokens, audio objects, and queued work where applicable;
- preserves only records with a documented legal/security retention basis and pseudonymizes them if possible.

## Task WS04-08 — Optional PostgreSQL RLS defense-in-depth
RLS is recommended only after application-level scoping is correct and tests are green.

If adopted:
- user-owned tables receive policies based on a transaction-local user context;
- app role must not bypass RLS;
- background/admin roles are separate and audited;
- connection pooling resets transaction-local context correctly.

Do not use RLS as a substitute for correct repository authorization.

## New ARUORA user-owned data classes

Include these in ownership/privacy inventory when introduced:
- destination/goal/deadline profile;
- target/previous-score metadata;
- readiness snapshots/recommendations;
- acquisition/cohort metadata;
- analytics identity mapping;
- notification/channel preferences;
- Study Pool opt-in/preferences;
- future Pod membership, peer feedback, blocks/reports;
- future human-help/tutor interactions.

Relationship tables require authorization from both the acting user and the relationship context. A Pod ID alone must never authorize access to every member's private learning history.

Study Pool must not expose direct contact information by default.

## Required BOLA test matrix
For each ID-based user route:
1. create User A object;
2. create User B;
3. authenticate B;
4. attempt GET/PUT/PATCH/DELETE on A’s ID;
5. assert no data disclosure and no mutation;
6. verify A’s row remains unchanged.

Add tests for guessed sequential IDs, nested IDs, history detail, exports, and admin-only functions.

## Migration safety
- Take a pre-migration backup in staging.
- Backfill or explicitly discard legacy nullable-owner rows.
- Add constraints only after the backfill.
- Run migration against a copy/snapshot of realistic data.
- Verify downgrade/rollback strategy; destructive data ownership changes may require forward-fix rather than downgrade.

## Exit criteria
Every persistent learner row has an unambiguous ownership/lifecycle, every user-object lookup includes an ownership predicate, account deletion is complete by schema design, and the BOLA matrix passes.
