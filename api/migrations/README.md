# Database migrations (Alembic)

The schema is owned by Alembic — **not** `create_all`. The api image runs
`alembic upgrade head` before starting (see `api/Dockerfile`), so a fresh DB is
built by the migrations and an existing DB is upgraded **in place** (no data loss).

`migrations/versions/8326c9605659_initial_schema.py` is the baseline (all tables).

## Making a schema change

1. Edit the models in `app/data/models.py`.
2. Autogenerate a migration (point `DATABASE_URL` at a DB that's already at head):

   ```bash
   cd api
   DATABASE_URL=postgresql+psycopg://ielts:ielts@localhost:5432/ielts \
     .venv/Scripts/python -m alembic revision --autogenerate -m "what changed"
   ```

3. Review the generated file in `migrations/versions/` (autogenerate is a draft —
   check column types, server defaults, data backfills).
4. Apply: `alembic upgrade head` (or just redeploy — the Dockerfile runs it).

## Notes

- Do NOT reintroduce `Base.metadata.create_all` in the app/startup path — it
  masks missing migrations (it can create new tables but never ALTERs existing
  ones, so column adds would be silently skipped).
- Tests build their own SQLite schema with `Base.metadata.create_all` directly;
  that's fine — tests don't run migrations.
- SQLite can't ALTER every construct; if a future migration needs it, use
  Alembic's batch mode (`with op.batch_alter_table(...)`).
