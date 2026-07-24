# Test-Phase Feedback Gate + Token-Efficiency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-time 7-hour test-phase feedback gate and three coordinated token-efficiency controls (pool-freeze, daily generation cap, free review model) to IELTS Coach, then verify/document the existing Docker setup.

**Architecture:** Backend is Flask 3 + SQLAlchemy 2 + Alembic + PostgreSQL, with a thin blueprint-per-feature layout and an ownership-scoped `Repository` facade. All LLM access funnels through `LlmGateway`. Frontend is React 19 + Vite + TypeScript with an in-house i18n dict and a `client.ts` fetch wrapper. New tables (`test_gate`, `feedback`, `gen_usage`) are added via one Alembic migration; tests auto-create them via `Base.metadata.create_all`. The gate is enforced client-side (blocking modal) driven by server state; efficiency controls are enforced server-side in the generation routes.

**Tech Stack:** Python 3.11 / Flask / SQLAlchemy 2 / Alembic / pytest; React 19 / Vite 6 / TypeScript / Vitest; OpenRouter via OpenAI SDK.

## Global Constraints

- **i18n (EN + ID):** every user-facing string goes through `web/src/lib/i18n.tsx` (`t(key)`), added to BOTH the `EN` and `ID` dicts. Never hardcode UI text.
- **Multi-user scoping:** `test_gate`, `feedback`, `gen_usage` are keyed by `user_id`; every repo method filters by owner. Admin endpoints guard via the `ADMIN_EMAILS` allow-list (`_require_admin` in `api/app/routes/admin.py`).
- **Update-log:** each meaningful change → `logs/{feature}_{YYYY-MM-DD}_log.md` (what/why/how-to-test/caveats/commit hash).
- **In-stack:** no new heavy dependencies. Reuse `mailer.send_email`, `_repo`, `_gateway`, `_require_uid`, the `PasscodeGate` component pattern, and the existing `ApiError`.
- **Admin allow-list:** admin iff signed-in email ∈ `ADMIN_EMAILS`. No `is_admin` column.
- **Config defaults (env-overridable):** `GATE_ENABLED=1`, `GATE_LOCK_SECONDS=25200`, `GATE_HEARTBEAT_SEC=60`, `POOL_TARGET=7`, `DAILY_GEN_CAP=20`, `MODEL_SCORE=deepseek/deepseek-chat-v3.1:free`.
- **Alembic head at start:** `9413f2a93a7e` (add_reminder_tz). New migration's `down_revision` = `9413f2a93a7e`.
- **Migrations are alembic-only in prod** (no `create_all` in `create_app`); tests create tables from metadata in `conftest.py`.

---

## File Structure

**Backend — create:**
- `api/app/routes/feedback.py` — gate + feedback + admin-feedback endpoints (new blueprint `gate`).
- `api/app/routes/_gencap.py` — `enforce_gen_cap(uid, repo, cfg)` shared helper.
- `api/migrations/versions/<rev>_test_gate_feedback_genusage.py` — schema migration.
- `api/tests/test_gate.py`, `api/tests/test_efficiency.py` — tests.

**Backend — modify:**
- `api/app/data/models.py` — add `TestGate`, `Feedback`, `GenUsage` models.
- `api/app/data/repositories.py` — add gate/feedback/gen-usage/pool methods.
- `api/app/config.py` — add gate + efficiency config; change `MODEL_SCORE` default.
- `api/app/routes/reading.py`, `api/app/routes/listening.py` — pool-freeze + cap.
- `api/app/routes/vocab.py`, `api/app/routes/lesson.py`, `api/app/routes/pronounce.py` — cap.
- `api/app/__init__.py` — register the new `gate` blueprint.

**Frontend — create:**
- `web/src/lib/gate.ts` — focus-aware heartbeat + gate-state hook.
- `web/src/components/gate/FeedbackGate.tsx` — blocking modal.

**Frontend — modify:**
- `web/src/lib/api/client.ts` — `gateStatus`, `gateHeartbeat`, `gateUnlock` calls.
- `web/src/lib/i18n.tsx` — new EN + ID keys.
- `web/src/App.tsx` — render `<FeedbackGate>` when locked.

**Infra — modify:**
- `.env.example`, `README.md` — document new env vars.

---

## Task 1: Data models — TestGate, Feedback, GenUsage

**Files:**
- Modify: `api/app/data/models.py` (append after `GeneratedSet`, before `Program`)
- Test: `api/tests/test_efficiency.py` (new)

**Interfaces:**
- Consumes: `Base`, `now`, `String`, `Integer`, `DateTime`, `ForeignKey` (already imported in models.py).
- Produces: ORM classes `TestGate` (`user_id` PK/FK, `active_seconds` int, `unlocked_at` datetime|None), `Feedback` (`id`, `user_id` FK, `stars` int, `insight` str, `created_at`), `GenUsage` (`id`, `user_id` FK, `day` str `YYYY-MM-DD`, `count` int).

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_efficiency.py`:

```python
from app.data.models import TestGate, Feedback, GenUsage


def test_models_have_expected_columns():
    assert TestGate.__tablename__ == "test_gate"
    assert set(TestGate.__table__.columns.keys()) >= {"user_id", "active_seconds", "unlocked_at"}
    assert Feedback.__tablename__ == "feedback"
    assert set(Feedback.__table__.columns.keys()) >= {"id", "user_id", "stars", "insight", "created_at"}
    assert GenUsage.__tablename__ == "gen_usage"
    assert set(GenUsage.__table__.columns.keys()) >= {"id", "user_id", "day", "count"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py::test_models_have_expected_columns -v`
Expected: FAIL with `ImportError: cannot import name 'TestGate'`.

- [ ] **Step 3: Write minimal implementation**

In `api/app/data/models.py`, add after the `GeneratedSet` class (line ~80):

```python
class TestGate(Base):
    __tablename__ = "test_gate"
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), primary_key=True)
    active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"))
    stars: Mapped[int] = mapped_column(Integer)
    insight: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class GenUsage(Base):
    __tablename__ = "gen_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"))
    day: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD (UTC)
    count: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py::test_models_have_expected_columns -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/app/data/models.py api/tests/test_efficiency.py
git commit -m "feat(data): add TestGate, Feedback, GenUsage models"
```

---

## Task 2: Repository methods — gate, feedback, gen-usage, pool

**Files:**
- Modify: `api/app/data/repositories.py` (import block near line 15; new methods after `serve_any_set`, line ~478)
- Test: `api/tests/test_efficiency.py`

**Interfaces:**
- Consumes: `TestGate`, `Feedback`, `GenUsage`, `GeneratedSet` models; `self._sf()` session factory; `select`, `func` (already imported); `datetime`, `timezone` (already imported).
- Produces on `Repository`:
  - `gate_get(uid) -> dict` → `{"active_seconds": int, "unlocked_at": datetime|None}` (creates row lazily).
  - `gate_add_seconds(uid, secs) -> int` → new `active_seconds`.
  - `gate_unlock(uid) -> None` (idempotent; sets `unlocked_at` if unset).
  - `feedback_add(uid, stars, insight) -> int` (returns id).
  - `feedback_list() -> list[dict]` (admin; all rows, newest first).
  - `gen_count_today(uid, day) -> int`.
  - `gen_incr_today(uid, day) -> int` → new count.
  - `count_sets(skill, band) -> int`.
  - `add_set(skill, band, payload, source="generated") -> int` (returns id).

- [ ] **Step 1: Write the failing test**

Append to `api/tests/test_efficiency.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.models import Base
from app.data.repositories import Repository


def _repo():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(bind=eng))


def test_gate_accumulate_and_unlock():
    r = _repo()
    assert r.gate_get(1)["active_seconds"] == 0
    assert r.gate_add_seconds(1, 60) == 60
    assert r.gate_add_seconds(1, 60) == 120
    assert r.gate_get(1)["unlocked_at"] is None
    r.gate_unlock(1)
    assert r.gate_get(1)["unlocked_at"] is not None
    r.gate_unlock(1)  # idempotent, no raise


def test_feedback_add_and_list():
    r = _repo()
    fid = r.feedback_add(1, 5, "Really useful for listening drills.")
    assert isinstance(fid, int)
    rows = r.feedback_list()
    assert rows[0]["stars"] == 5 and rows[0]["user_id"] == 1


def test_gen_usage_counter_is_per_day():
    r = _repo()
    assert r.gen_count_today(1, "2026-07-25") == 0
    assert r.gen_incr_today(1, "2026-07-25") == 1
    assert r.gen_incr_today(1, "2026-07-25") == 2
    assert r.gen_count_today(1, "2026-07-26") == 0


def test_pool_count_and_add():
    r = _repo()
    assert r.count_sets("reading", "B2") == 0
    r.add_set("reading", "B2", {"passage": "x"})
    assert r.count_sets("reading", "B2") == 1
    assert r.count_sets("reading", "B1") == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py -v -k "gate_accumulate or feedback_add or gen_usage or pool_count"`
Expected: FAIL with `AttributeError: 'Repository' object has no attribute 'gate_get'`.

- [ ] **Step 3: Write minimal implementation**

In `api/app/data/repositories.py`, add to the model import block (line ~15):

```python
    Feedback,
    GenUsage,
    TestGate,
```

Then append after `serve_any_set` (line ~478):

```python
    # ── Test-phase gate + feedback ─────────────────────────────────────────────

    def gate_get(self, uid: int) -> dict:
        with self._sf() as s:
            g = s.get(TestGate, uid)
            if g is None:
                g = TestGate(user_id=uid, active_seconds=0)
                s.add(g)
                s.commit()
                s.refresh(g)
            return {"active_seconds": g.active_seconds, "unlocked_at": g.unlocked_at}

    def gate_add_seconds(self, uid: int, secs: int) -> int:
        with self._sf() as s:
            g = s.get(TestGate, uid)
            if g is None:
                g = TestGate(user_id=uid, active_seconds=0)
                s.add(g)
            g.active_seconds = (g.active_seconds or 0) + max(0, int(secs))
            s.commit()
            return g.active_seconds

    def gate_unlock(self, uid: int) -> None:
        with self._sf() as s:
            g = s.get(TestGate, uid)
            if g is None:
                g = TestGate(user_id=uid, active_seconds=0)
                s.add(g)
            if g.unlocked_at is None:
                g.unlocked_at = now()
            s.commit()

    def feedback_add(self, uid: int, stars: int, insight: str) -> int:
        with self._sf() as s:
            f = Feedback(user_id=uid, stars=int(stars), insight=insight)
            s.add(f)
            s.commit()
            s.refresh(f)
            return f.id

    def feedback_list(self) -> list[dict]:
        with self._sf() as s:
            rows = s.execute(select(Feedback).order_by(Feedback.created_at.desc())).scalars().all()
            return [
                {"id": f.id, "user_id": f.user_id, "stars": f.stars,
                 "insight": f.insight, "created_at": f.created_at.isoformat()}
                for f in rows
            ]

    # ── Generation cap ─────────────────────────────────────────────────────────

    def gen_count_today(self, uid: int, day: str) -> int:
        with self._sf() as s:
            row = s.execute(
                select(GenUsage).where(GenUsage.user_id == uid, GenUsage.day == day)
            ).scalars().first()
            return row.count if row else 0

    def gen_incr_today(self, uid: int, day: str) -> int:
        with self._sf() as s:
            row = s.execute(
                select(GenUsage).where(GenUsage.user_id == uid, GenUsage.day == day)
            ).scalars().first()
            if row is None:
                row = GenUsage(user_id=uid, day=day, count=0)
                s.add(row)
            row.count += 1
            s.commit()
            return row.count

    # ── Pool sizing ────────────────────────────────────────────────────────────

    def count_sets(self, skill: str, band: str) -> int:
        with self._sf() as s:
            return s.execute(
                select(func.count()).select_from(GeneratedSet).where(
                    GeneratedSet.skill == skill, GeneratedSet.band == band
                )
            ).scalar_one()

    def add_set(self, skill: str, band: str, payload: dict, source: str = "generated") -> int:
        with self._sf() as s:
            idx = s.execute(
                select(func.count()).select_from(GeneratedSet).where(
                    GeneratedSet.skill == skill, GeneratedSet.band == band
                )
            ).scalar_one()
            row = GeneratedSet(skill=skill, band=band, set_index=idx, payload=payload, source=source)
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py -v`
Expected: PASS (all model + repo tests).

- [ ] **Step 5: Commit**

```bash
git add api/app/data/repositories.py api/tests/test_efficiency.py
git commit -m "feat(data): repo methods for gate, feedback, gen-usage, pool"
```

---

## Task 3: Config — gate + efficiency knobs, free review model

**Files:**
- Modify: `api/app/config.py` (in `Config.__init__`, near the existing `MODEL_SCORE` line 66)
- Test: `api/tests/test_efficiency.py`

**Interfaces:**
- Produces on `Config`: `GATE_ENABLED: bool`, `GATE_LOCK_SECONDS: int`, `GATE_HEARTBEAT_SEC: int`, `POOL_TARGET: int`, `DAILY_GEN_CAP: int`; `MODEL_SCORE` default changed to the free model.

- [ ] **Step 1: Write the failing test**

Append to `api/tests/test_efficiency.py`:

```python
from app.config import Config


def test_efficiency_config_defaults():
    c = Config({})
    assert c.GATE_ENABLED is True
    assert c.GATE_LOCK_SECONDS == 25200
    assert c.GATE_HEARTBEAT_SEC == 60
    assert c.POOL_TARGET == 7
    assert c.DAILY_GEN_CAP == 20
    assert c.MODEL_SCORE == "deepseek/deepseek-chat-v3.1:free"


def test_efficiency_config_overrides():
    c = Config({"POOL_TARGET": 3, "DAILY_GEN_CAP": 0, "GATE_ENABLED": "0"})
    assert c.POOL_TARGET == 3
    assert c.DAILY_GEN_CAP == 0
    assert c.GATE_ENABLED is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py -v -k "config_defaults or config_overrides"`
Expected: FAIL with `AttributeError: 'Config' object has no attribute 'GATE_ENABLED'`.

- [ ] **Step 3: Write minimal implementation**

In `api/app/config.py`, change the `MODEL_SCORE` line (66) default and add new lines directly below it:

```python
        self.MODEL_GENERATE = o.get("MODEL_GENERATE", os.getenv("MODEL_GENERATE", "anthropic/claude-haiku-4-5"))
        self.MODEL_SCORE = o.get("MODEL_SCORE", os.getenv("MODEL_SCORE", "deepseek/deepseek-chat-v3.1:free"))
        # Test-phase feedback gate (Feature A).
        self.GATE_ENABLED = _truthy(o.get("GATE_ENABLED", os.getenv("GATE_ENABLED", "1")))
        self.GATE_LOCK_SECONDS = int(o.get("GATE_LOCK_SECONDS", os.getenv("GATE_LOCK_SECONDS", "25200")))
        self.GATE_HEARTBEAT_SEC = int(o.get("GATE_HEARTBEAT_SEC", os.getenv("GATE_HEARTBEAT_SEC", "60")))
        # Token efficiency (Feature B). POOL_TARGET sets per (skill,band) before
        # generation freezes; DAILY_GEN_CAP=0 means unlimited.
        self.POOL_TARGET = int(o.get("POOL_TARGET", os.getenv("POOL_TARGET", "7")))
        self.DAILY_GEN_CAP = int(o.get("DAILY_GEN_CAP", os.getenv("DAILY_GEN_CAP", "20")))
```

(Note: `_truthy` treats `"0"` as False, so the override test passes.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py -v -k "config"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/app/config.py api/tests/test_efficiency.py
git commit -m "feat(config): gate + efficiency knobs; free review model default"
```

---

## Task 4: Alembic migration for the three tables

**Files:**
- Create: `api/migrations/versions/<rev>_test_gate_feedback_genusage.py`

**Interfaces:**
- Consumes: Alembic `op`, `sqlalchemy as sa`. `down_revision = "9413f2a93a7e"`.
- Produces: DDL for `test_gate`, `feedback`, `gen_usage`.

- [ ] **Step 1: Generate the revision stub**

Run: `cd api && .venv/Scripts/python -m alembic revision -m "test_gate feedback genusage"`
Expected: prints `Generating .../versions/<rev>_test_gate_feedback_genusage.py`.

- [ ] **Step 2: Write the migration body**

Replace the generated file's `upgrade`/`downgrade` and set `down_revision`:

```python
down_revision = "9413f2a93a7e"

def upgrade() -> None:
    op.create_table(
        "test_gate",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_profile.id"), primary_key=True),
        sa.Column("active_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_profile.id"), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("insight", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "gen_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_profile.id"), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_gen_usage_user_day", "gen_usage", ["user_id", "day"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_gen_usage_user_day", table_name="gen_usage")
    op.drop_table("gen_usage")
    op.drop_table("feedback")
    op.drop_table("test_gate")
```

- [ ] **Step 3: Verify the migration applies (SQLite smoke)**

Run: `cd api && DATABASE_URL="sqlite+pysqlite:///migtest.db" .venv/Scripts/python -m alembic upgrade head && rm -f migtest.db`
Expected: `Running upgrade 9413f2a93a7e -> <rev>` with no error.

- [ ] **Step 4: Commit**

```bash
git add api/migrations/versions/*_test_gate_feedback_genusage.py
git commit -m "feat(db): migration for test_gate, feedback, gen_usage"
```

---

## Task 5: Gate + feedback API blueprint

**Files:**
- Create: `api/app/routes/feedback.py`
- Modify: `api/app/__init__.py` (blueprint import ~line 165 and register ~line 186)
- Test: `api/tests/test_gate.py` (new)

**Interfaces:**
- Consumes: `_repo`, `_cfg`, `_require_uid` from `_deps`; `_require_admin`, `_is_admin_email` from `routes.admin`; `mailer.send_email`; `ApiError`; repo methods from Task 2; config from Task 3; `current_uid`, `_repo().get_user_by_id`.
- Produces endpoints: `GET /api/gate/status`, `POST /api/gate/heartbeat`, `POST /api/gate/unlock`, `GET /api/admin/feedback`. Blueprint name `gate`.
- `_locked(cfg, gate, is_admin) -> bool` helper: `cfg.GATE_ENABLED and not is_admin and gate["unlocked_at"] is None and gate["active_seconds"] >= cfg.GATE_LOCK_SECONDS`.

- [ ] **Step 1: Write the failing test**

Create `api/tests/test_gate.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway


def _client(overrides=None):
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)
    gw = LlmGateway(Config({"LLM_MODE": "stub"}))
    cfg = {"TESTING": True, "REPO": repo, "GATEWAY": gw, "GATE_LOCK_SECONDS": 120}
    cfg.update(overrides or {})
    app = create_app(cfg)
    c = app.test_client()
    c.post("/api/account/register", json={"email": "u@example.com", "password": "secret123"})
    return c


def test_status_starts_unlocked_and_not_locked():
    c = _client()
    r = c.get("/api/gate/status")
    assert r.status_code == 200
    j = r.get_json()
    assert j["locked"] is False and j["unlocked"] is False
    assert j["thresholdSeconds"] == 120


def test_heartbeat_accumulates_and_locks_at_threshold():
    c = _client()
    # heartbeat clamps to 2x interval; default interval 60 -> max 120/tick
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    j = c.post("/api/gate/heartbeat", json={"seconds": 120}).get_json()
    assert j["activeSeconds"] == 240
    assert j["locked"] is True


def test_heartbeat_clamps_huge_jumps():
    c = _client()
    j = c.post("/api/gate/heartbeat", json={"seconds": 99999}).get_json()
    assert j["activeSeconds"] == 120  # clamped to 2x GATE_HEARTBEAT_SEC (60)


def test_unlock_requires_valid_stars_and_insight():
    c = _client()
    assert c.post("/api/gate/unlock", json={"stars": 0, "insight": "x"}).status_code == 422
    assert c.post("/api/gate/unlock", json={"stars": 5, "insight": "short"}).status_code == 422
    ok = c.post("/api/gate/unlock", json={"stars": 4, "insight": "Great for listening practice, thanks!"})
    assert ok.status_code == 200 and ok.get_json()["unlocked"] is True


def test_unlock_makes_status_permanently_unlocked():
    c = _client()
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    c.post("/api/gate/heartbeat", json={"seconds": 120})  # now locked
    c.post("/api/gate/unlock", json={"stars": 5, "insight": "Solid feedback on my essays here."})
    j = c.get("/api/gate/status").get_json()
    assert j["locked"] is False and j["unlocked"] is True


def test_admin_never_locked_and_can_list_feedback():
    c = _client(overrides={"ADMIN_EMAILS": "u@example.com"})
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    c.post("/api/gate/heartbeat", json={"seconds": 120})
    assert c.get("/api/gate/status").get_json()["locked"] is False
    # a normal user's feedback should be listable by admin
    c.post("/api/gate/unlock", json={"stars": 3, "insight": "Admin can read this insight row."})
    rows = c.get("/api/admin/feedback").get_json()
    assert any(r["stars"] == 3 for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_gate.py -v`
Expected: FAIL — 404s (blueprint not registered).

- [ ] **Step 3: Write the blueprint**

Create `api/app/routes/feedback.py`:

```python
"""
Test-phase feedback gate (Feature A).

Each user accumulates focused in-app time via /api/gate/heartbeat. At
GATE_LOCK_SECONDS the app locks until the user submits a rating + insight
(/api/gate/unlock), which is stored and emailed to the admin. One-time:
once unlocked, never locks again. Admins are exempt.
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _cfg, _repo, _require_uid
from app.routes.admin import _is_admin_email, _require_admin
from app.services import mailer
from app.session import current_uid

bp = Blueprint("gate", __name__)

MIN_INSIGHT = 20


def _is_admin_uid(uid) -> bool:
    u = _repo().get_user_by_id(uid) if uid else None
    return bool(u and _is_admin_email(u.email))


def _locked(cfg, gate: dict, is_admin: bool) -> bool:
    return (
        cfg.GATE_ENABLED
        and not is_admin
        and gate["unlocked_at"] is None
        and gate["active_seconds"] >= cfg.GATE_LOCK_SECONDS
    )


@bp.get("/api/gate/status")
def gate_status():
    uid = _require_uid()
    cfg = _cfg()
    is_admin = _is_admin_uid(uid)
    gate = _repo().gate_get(uid)
    return jsonify({
        "activeSeconds": gate["active_seconds"],
        "thresholdSeconds": cfg.GATE_LOCK_SECONDS,
        "heartbeatSec": cfg.GATE_HEARTBEAT_SEC,
        "locked": _locked(cfg, gate, is_admin),
        "unlocked": gate["unlocked_at"] is not None,
        "isAdmin": is_admin,
    }), 200


@bp.post("/api/gate/heartbeat")
def gate_heartbeat():
    uid = _require_uid()
    cfg = _cfg()
    is_admin = _is_admin_uid(uid)
    body = request.get_json(force=True) or {}
    try:
        secs = int(body.get("seconds", cfg.GATE_HEARTBEAT_SEC))
    except (TypeError, ValueError):
        secs = cfg.GATE_HEARTBEAT_SEC
    secs = max(0, min(secs, 2 * cfg.GATE_HEARTBEAT_SEC))  # clamp resumed-tab jumps
    active = _repo().gate_add_seconds(uid, secs)
    gate = {"active_seconds": active, "unlocked_at": _repo().gate_get(uid)["unlocked_at"]}
    return jsonify({
        "activeSeconds": active,
        "locked": _locked(cfg, gate, is_admin),
        "unlocked": gate["unlocked_at"] is not None,
    }), 200


@bp.post("/api/gate/unlock")
def gate_unlock():
    uid = _require_uid()
    cfg = _cfg()
    body = request.get_json(force=True) or {}
    try:
        stars = int(body.get("stars", 0))
    except (TypeError, ValueError):
        stars = 0
    insight = (body.get("insight") or "").strip()
    if not (1 <= stars <= 5):
        raise ApiError("VALIDATION", "stars must be 1–5", 422)
    if len(insight) < MIN_INSIGHT:
        raise ApiError("VALIDATION", f"insight must be at least {MIN_INSIGHT} characters", 422)
    repo = _repo()
    repo.feedback_add(uid, stars, insight)
    repo.gate_unlock(uid)
    u = repo.get_user_by_id(uid)
    admin_to = next(iter(cfg.ADMIN_EMAILS), None) or (cfg.SMTP_FROM or "")
    if admin_to:
        mailer.send_email(
            cfg, admin_to, "[IELTS Coach] New test feedback",
            f"User {getattr(u, 'email', uid)} rated {stars}/5.\n\nInsight:\n{insight}",
        )
    return jsonify({"unlocked": True}), 200


@bp.get("/api/admin/feedback")
def admin_feedback():
    _require_admin()
    return jsonify(_repo().feedback_list()), 200
```

In `api/app/__init__.py` add the import (after line 165, `admin_bp`):

```python
    from .routes.feedback import bp as gate_bp
```

and register it (after `app.register_blueprint(admin_bp)`):

```python
    app.register_blueprint(gate_bp)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_gate.py -v`
Expected: PASS (all 6 tests).

- [ ] **Step 5: Commit**

```bash
git add api/app/routes/feedback.py api/app/__init__.py api/tests/test_gate.py
git commit -m "feat(api): test-phase feedback gate endpoints"
```

---

## Task 6: Generation-cap helper + wire the two pooled skills

**Files:**
- Create: `api/app/routes/_gencap.py`
- Modify: `api/app/routes/reading.py`, `api/app/routes/listening.py`
- Test: `api/tests/test_efficiency.py`

**Interfaces:**
- Consumes: `_repo`, `_cfg`, `_gateway`, `_require_uid`; repo `count_sets/add_set/serve_set/serve_any_set/gen_count_today/gen_incr_today`; config `POOL_TARGET/DAILY_GEN_CAP`; `ApiError`.
- Produces in `_gencap.py`:
  - `_today() -> str` (UTC `YYYY-MM-DD`).
  - `cap_reached(uid, repo, cfg) -> bool` (`DAILY_GEN_CAP>0 and count>=cap`).
  - `note_generation(uid, repo) -> None` (increments today's counter).
  - `GEN_CAP_MSG = "GEN_CAP_REACHED"` error code constant.

- [ ] **Step 1: Write the failing test**

Append to `api/tests/test_efficiency.py`:

```python
def _seeded_client(overrides=None):
    from app import create_app
    from app.data.seed import seed_all
    from app.services.llm import LlmGateway
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    repo = Repository(Session)

    class FakeGW:
        calls = 0
        def generate(self, *a, **k):
            FakeGW.calls += 1
            return {"passage": "generated", "questions": []}
    gw = FakeGW()
    cfg = {"TESTING": True, "REPO": repo, "GATEWAY": gw, "POOL_TARGET": 2, "DAILY_GEN_CAP": 3}
    cfg.update(overrides or {})
    app = create_app(cfg)
    c = app.test_client()
    c.post("/api/account/register", json={"email": "g@example.com", "password": "secret123"})
    return c, repo, gw


def test_reading_generates_until_pool_target_then_serves():
    c, repo, gw = _seeded_client()
    # POOL_TARGET=2: first two calls generate + grow pool
    c.post("/api/reading/generate", json={"band": "B2"})
    c.post("/api/reading/generate", json={"band": "B2"})
    assert repo.count_sets("reading", "B2") == 2
    assert gw.calls == 2
    # third call: pool full -> serve from pool, no new generate
    c.post("/api/reading/generate", json={"band": "B2"})
    assert gw.calls == 2
    assert repo.count_sets("reading", "B2") == 2


def test_new_band_reenters_generation():
    c, repo, gw = _seeded_client()
    c.post("/api/reading/generate", json={"band": "B2"})
    c.post("/api/reading/generate", json={"band": "B2"})  # B2 pool full (target 2)
    before = gw.calls
    c.post("/api/reading/generate", json={"band": "C1"})  # new band -> generates
    assert gw.calls == before + 1
    assert repo.count_sets("reading", "C1") == 1


def test_daily_cap_blocks_further_generation():
    c, repo, gw = _seeded_client(overrides={"POOL_TARGET": 99, "DAILY_GEN_CAP": 2})
    c.post("/api/listening/generate", json={"band": "B1"})
    c.post("/api/listening/generate", json={"band": "B1"})
    # cap=2 reached; pool has 2 sets -> fall back to serve, status 200, no generate
    r = c.post("/api/listening/generate", json={"band": "B1"})
    assert r.status_code == 200
    assert gw.calls == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py -v -k "reading_generates or new_band or daily_cap"`
Expected: FAIL — currently reading/listening always call generate (gw.calls keeps rising) and don't grow the pool.

- [ ] **Step 3: Write the helper and rewire routes**

Create `api/app/routes/_gencap.py`:

```python
"""Shared token-efficiency helpers for generation routes (Feature B)."""
from datetime import datetime, timezone

GEN_CAP_CODE = "GEN_CAP_REACHED"


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def cap_reached(uid: int, repo, cfg) -> bool:
    if cfg.DAILY_GEN_CAP <= 0:
        return False
    return repo.gen_count_today(uid, today_utc()) >= cfg.DAILY_GEN_CAP


def note_generation(uid: int, repo) -> None:
    repo.gen_incr_today(uid, today_utc())
```

Replace `api/app/routes/reading.py` body:

```python
"""
POST /api/reading/generate — serve a reading set.

Efficiency (Feature B): once POOL_TARGET sets exist for (reading, band) the
pool is frozen and we serve a random stored set (no LLM). Below target, and
while under the daily cap, we generate + grow the pool. When capped, we fall
back to the pool if one exists, else 429.
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _repo, _require_uid
from app.routes._gencap import cap_reached, note_generation

bp = Blueprint("reading", __name__)


@bp.post("/api/reading/generate")
def reading_generate():
    uid = _require_uid()
    band = (request.get_json(force=True) or {}).get("band", "B2")
    repo, cfg = _repo(), _cfg()

    if repo.count_sets("reading", band) >= cfg.POOL_TARGET:
        return jsonify(repo.serve_set("reading", band)), 200

    if cap_reached(uid, repo, cfg):
        served = repo.serve_set("reading", band) or repo.serve_any_set("reading")
        if served is not None:
            return jsonify(served), 200
        raise ApiError("GEN_CAP_REACHED", "Daily generation limit reached", 429)

    out = _gateway().generate("generate", skill="reading", band=band)
    repo.add_set("reading", band, out)
    note_generation(uid, repo)
    return jsonify(out), 200
```

Replace `api/app/routes/listening.py` body identically but for `"listening"` and default band `"B1"`:

```python
"""
POST /api/listening/generate — serve a listening set (see reading.py for the
efficiency policy; identical pool-freeze + daily-cap behaviour).
"""
from flask import Blueprint, jsonify, request

from app.errors import ApiError
from app.routes._deps import _cfg, _gateway, _repo, _require_uid
from app.routes._gencap import cap_reached, note_generation

bp = Blueprint("listening", __name__)


@bp.post("/api/listening/generate")
def listening_generate():
    uid = _require_uid()
    band = (request.get_json(force=True) or {}).get("band", "B1")
    repo, cfg = _repo(), _cfg()

    if repo.count_sets("listening", band) >= cfg.POOL_TARGET:
        return jsonify(repo.serve_set("listening", band)), 200

    if cap_reached(uid, repo, cfg):
        served = repo.serve_set("listening", band) or repo.serve_any_set("listening")
        if served is not None:
            return jsonify(served), 200
        raise ApiError("GEN_CAP_REACHED", "Daily generation limit reached", 429)

    out = _gateway().generate("generate", skill="listening", band=band)
    repo.add_set("listening", band, out)
    note_generation(uid, repo)
    return jsonify(out), 200
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/app/routes/_gencap.py api/app/routes/reading.py api/app/routes/listening.py api/tests/test_efficiency.py
git commit -m "feat(api): pool-freeze + daily gen cap for reading/listening"
```

---

## Task 7: Apply the daily cap to vocab, lesson, pronounce

**Files:**
- Modify: `api/app/routes/vocab.py`, `api/app/routes/lesson.py`, `api/app/routes/pronounce.py`
- Test: `api/tests/test_efficiency.py`

**Interfaces:**
- Consumes: `cap_reached`, `note_generation` from `_gencap`; `_cfg`, `_repo`, `_require_uid`. These routes have no pool, so a reached cap → 429 `GEN_CAP_REACHED`.

- [ ] **Step 1: Write the failing test**

Append to `api/tests/test_efficiency.py`:

```python
def test_vocab_capped_returns_429():
    c, repo, gw = _seeded_client(overrides={"DAILY_GEN_CAP": 1})
    # vocab route is POST /api/vocab (not /generate); FakeGW.generate returns a dict
    first = c.post("/api/vocab", json={"level": "B1", "topic": "travel"})
    assert first.status_code == 200
    second = c.post("/api/vocab", json={"level": "B1", "topic": "travel"})
    assert second.status_code == 429
    assert second.get_json()["error"]["code"] == "GEN_CAP_REACHED"
```

(Note: `_seeded_client`'s `FakeGW.generate` already returns a dict for any args, so vocab's call succeeds.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py::test_vocab_capped_returns_429 -v`
Expected: FAIL — second call returns 200 (no cap yet).

- [ ] **Step 3: Add the guard to each route**

In `api/app/routes/vocab.py`, at the top of the generate handler (after `uid = _require_uid()` — add that binding if the route currently calls `_require_uid()` without capturing it), insert:

```python
from app.routes._gencap import cap_reached, note_generation
from app.routes._deps import _cfg, _repo
from app.errors import ApiError
```

and inside the handler, before the `_gateway().generate(...)` call:

```python
    if cap_reached(uid, _repo(), _cfg()):
        raise ApiError("GEN_CAP_REACHED", "Daily generation limit reached", 429)
```

and immediately after a successful generate:

```python
    note_generation(uid, _repo())
```

Apply the identical three-part edit (import, pre-check, post-increment) to
`api/app/routes/lesson.py` (around line 67, the `_gateway().generate("lesson", ...)` call) and
`api/app/routes/pronounce.py` (around line 20, the `_gateway().generate("generate", skill="pronounce", ...)` call — cap only the generate, NOT the `score` call on line 29).

Ensure each handler binds `uid = _require_uid()` (replace a bare `_require_uid()` if present).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && .venv/Scripts/python -m pytest tests/test_efficiency.py -v`
Expected: PASS.

- [ ] **Step 5: Full API suite (regression)**

Run: `cd api && .venv/Scripts/python -m pytest -q`
Expected: PASS (no regressions in existing suites).

- [ ] **Step 6: Commit**

```bash
git add api/app/routes/vocab.py api/app/routes/lesson.py api/app/routes/pronounce.py api/tests/test_efficiency.py
git commit -m "feat(api): apply daily gen cap to vocab, lesson, pronounce"
```

---

## Task 8: Frontend — API client + i18n strings

**Files:**
- Modify: `web/src/lib/api/client.ts`, `web/src/lib/i18n.tsx`

**Interfaces:**
- Produces on the api client: `gateStatus()`, `gateHeartbeat(seconds)`, `gateUnlock(stars, insight)` returning the JSON shapes from Task 5.
- Produces i18n keys: `gate.title`, `gate.body`, `gate.starsLabel`, `gate.insightLabel`, `gate.insightPlaceholder`, `gate.submit`, `gate.thanks`, `gate.validation`, `gen.capReached`.

- [ ] **Step 1: Add client methods**

In `web/src/lib/api/client.ts`, add near the other exported api calls (follow the existing `request<T>()` style):

```typescript
export type GateStatus = {
  activeSeconds: number; thresholdSeconds: number; heartbeatSec: number;
  locked: boolean; unlocked: boolean; isAdmin: boolean;
};

export const gateStatus = () => request<GateStatus>("/api/gate/status");
export const gateHeartbeat = (seconds: number) =>
  request<{ activeSeconds: number; locked: boolean; unlocked: boolean }>(
    "/api/gate/heartbeat", { method: "POST", body: JSON.stringify({ seconds }) });
export const gateUnlock = (stars: number, insight: string) =>
  request<{ unlocked: boolean }>(
    "/api/gate/unlock", { method: "POST", body: JSON.stringify({ stars, insight }) });
```

(If the file exports a single `api` object rather than free functions, add these as members following that pattern instead.)

- [ ] **Step 2: Add i18n keys (EN + ID)**

In `web/src/lib/i18n.tsx`, add to the `EN` dict:

```typescript
  // test-phase gate
  "gate.title": "Quick check-in before you continue",
  "gate.body": "Thanks for testing IELTS Coach! To keep going, please rate your experience and share one insight.",
  "gate.starsLabel": "Your rating",
  "gate.insightLabel": "Your insight",
  "gate.insightPlaceholder": "What worked, what didn't, what to improve… (at least 20 characters)",
  "gate.submit": "Submit & continue",
  "gate.thanks": "Thank you! Enjoy the app.",
  "gate.validation": "Please give a star rating and at least 20 characters of insight.",
  "gen.capReached": "You've reached today's practice-generation limit. Please come back tomorrow.",
```

and the matching Indonesian strings to the `ID` dict:

```typescript
  // test-phase gate
  "gate.title": "Cek sebentar sebelum lanjut",
  "gate.body": "Terima kasih sudah menguji IELTS Coach! Untuk melanjutkan, beri rating dan satu masukan.",
  "gate.starsLabel": "Rating kamu",
  "gate.insightLabel": "Masukan kamu",
  "gate.insightPlaceholder": "Apa yang bagus, apa yang kurang, apa yang perlu diperbaiki… (minimal 20 karakter)",
  "gate.submit": "Kirim & lanjut",
  "gate.thanks": "Terima kasih! Selamat belajar.",
  "gate.validation": "Beri rating bintang dan minimal 20 karakter masukan.",
  "gen.capReached": "Kamu sudah mencapai batas pembuatan soal hari ini. Silakan kembali besok.",
```

- [ ] **Step 3: Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/api/client.ts web/src/lib/i18n.tsx
git commit -m "feat(web): gate api client methods + EN/ID strings"
```

---

## Task 9: Frontend — focus-aware heartbeat hook

**Files:**
- Create: `web/src/lib/gate.ts`
- Test: `web/src/lib/gate.test.ts` (new, Vitest)

**Interfaces:**
- Consumes: `gateStatus`, `gateHeartbeat` from client.
- Produces: `useGate()` hook returning `{ locked: boolean; loading: boolean; refresh: () => void; markUnlocked: () => void }`. Starts an interval that, only when `document.visibilityState === "visible"` and `document.hasFocus()`, POSTs a heartbeat of `heartbeatSec` seconds and updates `locked`. Interval cleared on unmount. No heartbeat once `unlocked` or `isAdmin` is true.

- [ ] **Step 1: Write the failing test**

Create `web/src/lib/gate.test.ts`:

```typescript
import { describe, expect, it, vi, beforeEach } from "vitest";
import { computeShouldBeat } from "./gate";

describe("computeShouldBeat", () => {
  it("beats only when visible, focused, locked-eligible, not admin/unlocked", () => {
    expect(computeShouldBeat({ visible: true, focused: true, unlocked: false, isAdmin: false })).toBe(true);
    expect(computeShouldBeat({ visible: false, focused: true, unlocked: false, isAdmin: false })).toBe(false);
    expect(computeShouldBeat({ visible: true, focused: false, unlocked: false, isAdmin: false })).toBe(false);
    expect(computeShouldBeat({ visible: true, focused: true, unlocked: true, isAdmin: false })).toBe(false);
    expect(computeShouldBeat({ visible: true, focused: true, unlocked: false, isAdmin: true })).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/lib/gate.test.ts`
Expected: FAIL — `computeShouldBeat` not exported.

- [ ] **Step 3: Write the hook**

Create `web/src/lib/gate.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from "react";
import { gateHeartbeat, gateStatus, type GateStatus } from "./api/client";

export function computeShouldBeat(s: {
  visible: boolean; focused: boolean; unlocked: boolean; isAdmin: boolean;
}): boolean {
  return s.visible && s.focused && !s.unlocked && !s.isAdmin;
}

export function useGate() {
  const [status, setStatus] = useState<GateStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const timer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await gateStatus();
      setStatus(s);
    } catch {
      setStatus(null); // signed-out / error → no gate
    } finally {
      setLoading(false);
    }
  }, []);

  const markUnlocked = useCallback(() => {
    setStatus((prev) => (prev ? { ...prev, locked: false, unlocked: true } : prev));
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    if (!status) return;
    const intervalMs = Math.max(15, status.heartbeatSec) * 1000;
    timer.current = window.setInterval(async () => {
      const should = computeShouldBeat({
        visible: document.visibilityState === "visible",
        focused: document.hasFocus(),
        unlocked: status.unlocked,
        isAdmin: status.isAdmin,
      });
      if (!should) return;
      try {
        const r = await gateHeartbeat(status.heartbeatSec);
        if (r.locked) setStatus((prev) => (prev ? { ...prev, locked: true } : prev));
      } catch { /* ignore transient heartbeat errors */ }
    }, intervalMs);
    return () => { if (timer.current) window.clearInterval(timer.current); };
  }, [status]);

  return { locked: !!status?.locked, loading, refresh, markUnlocked };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/lib/gate.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/gate.ts web/src/lib/gate.test.ts
git commit -m "feat(web): focus-aware gate heartbeat hook"
```

---

## Task 10: Frontend — FeedbackGate modal + App wiring

**Files:**
- Create: `web/src/components/gate/FeedbackGate.tsx`
- Modify: `web/src/App.tsx`
- Test: `web/src/components/gate/FeedbackGate.test.tsx` (new)

**Interfaces:**
- Consumes: `useI18n`/`t` from i18n; `gateUnlock` from client; `useGate` from `lib/gate`.
- `FeedbackGate` props: `{ onUnlocked: () => void }`. Renders stars (1–5) + textarea; submit disabled until `stars>=1 && insight.trim().length>=20`; on success calls `onUnlocked`.
- App: after the signed-in branch resolves, if `gate.locked` render `<FeedbackGate onUnlocked={gate.markUnlocked} />` INSTEAD of the app shell.

- [ ] **Step 1: Write the failing test**

Create `web/src/components/gate/FeedbackGate.test.tsx`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FeedbackGate } from "./FeedbackGate";

vi.mock("../../lib/api/client", () => ({
  gateUnlock: vi.fn(async () => ({ unlocked: true })),
}));
vi.mock("../../lib/i18n", () => ({
  useI18n: () => ({ t: (k: string) => k, lang: "en" }),
}));

describe("FeedbackGate", () => {
  it("disables submit until rating + 20-char insight, then unlocks", async () => {
    const onUnlocked = vi.fn();
    render(<FeedbackGate onUnlocked={onUnlocked} />);
    const submit = screen.getByRole("button", { name: "gate.submit" });
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /star-4/i }));
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "This is a sufficiently long insight." },
    });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    await waitFor(() => expect(onUnlocked).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/gate/FeedbackGate.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the component**

Create `web/src/components/gate/FeedbackGate.tsx`:

```tsx
import { useState } from "react";
import { Star } from "lucide-react";
import { useI18n } from "../../lib/i18n";
import { gateUnlock } from "../../lib/api/client";

const MIN = 20;

export function FeedbackGate({ onUnlocked }: { onUnlocked: () => void }) {
  const { t } = useI18n();
  const [stars, setStars] = useState(0);
  const [insight, setInsight] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const valid = stars >= 1 && insight.trim().length >= MIN;

  async function submit() {
    if (!valid || busy) return;
    setBusy(true); setErr(null);
    try {
      await gateUnlock(stars, insight.trim());
      onUnlocked();
    } catch {
      setErr(t("gate.validation"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-[var(--surface)] p-6 shadow-xl">
        <h2 className="text-xl font-semibold">{t("gate.title")}</h2>
        <p className="mt-2 text-sm opacity-80">{t("gate.body")}</p>

        <div className="mt-4">
          <div className="mb-1 text-sm font-medium">{t("gate.starsLabel")}</div>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                aria-label={`star-${n}`}
                aria-pressed={stars >= n}
                onClick={() => setStars(n)}
                className="p-1"
              >
                <Star className={stars >= n ? "fill-amber-400 stroke-amber-400" : "stroke-current opacity-40"} />
              </button>
            ))}
          </div>
        </div>

        <label className="mt-4 block">
          <span className="mb-1 block text-sm font-medium">{t("gate.insightLabel")}</span>
          <textarea
            value={insight}
            onChange={(e) => setInsight(e.target.value)}
            placeholder={t("gate.insightPlaceholder")}
            rows={4}
            className="w-full rounded-lg border border-[var(--border)] bg-transparent p-2 text-sm"
          />
        </label>

        {err && <p className="mt-2 text-sm text-red-500">{err}</p>}

        <button
          type="button"
          disabled={!valid || busy}
          onClick={submit}
          className="mt-4 w-full rounded-lg bg-[var(--accent)] px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          {t("gate.submit")}
        </button>
      </div>
    </div>
  );
}
```

(If `--surface`/`--accent`/`--border` tokens differ, use the same tokens `PasscodeGate.tsx` uses — check `web/src/components/auth/PasscodeGate.tsx` and mirror them.)

- [ ] **Step 4: Wire into App.tsx**

In `web/src/App.tsx`, import at top:

```tsx
import { useGate } from "./lib/gate";
import { FeedbackGate } from "./components/gate/FeedbackGate";
```

In the authenticated component (the one that renders the app shell after sign-in — the block near line 141 `return (`), call the hook at the top and short-circuit:

```tsx
  const gate = useGate();
  if (gate.locked) {
    return <FeedbackGate onUnlocked={gate.markUnlocked} />;
  }
```

Place this AFTER the sign-in/passcode checks so only signed-in users can be gated (an anonymous user has no `uid`, and `gateStatus` will error → `locked=false`).

- [ ] **Step 5: Run tests + typecheck**

Run: `cd web && npx vitest run src/components/gate/FeedbackGate.test.tsx && npx tsc --noEmit`
Expected: PASS + no type errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/gate/FeedbackGate.tsx web/src/components/gate/FeedbackGate.test.tsx web/src/App.tsx
git commit -m "feat(web): FeedbackGate modal + App gating"
```

---

## Task 11: Client cap-reached UX (429 handling)

**Files:**
- Modify: the reading/listening/vocab practice components that call the generate endpoints, OR the shared `request<T>()` error surface in `web/src/lib/api/client.ts`.
- Test: covered by manual verification (Task 13); no new unit test required.

**Interfaces:**
- Consumes: `ApiError` (already thrown by `request<T>()` with `.code`). When `.code === "GEN_CAP_REACHED"`, show `t("gen.capReached")` as a friendly notice rather than a generic error toast.

- [ ] **Step 1: Locate the generate call sites**

Run: `cd web && grep -rn "reading/generate\|listening/generate\|/api/vocab\|/lesson\|pronounce" src/components | head`
Expected: prints the components that trigger generation.

- [ ] **Step 2: Add a friendly branch**

In each generate call site's `catch (e)` (or in a shared helper), add:

```tsx
import { ApiError } from "../../lib/api/client"; // adjust relative path
// ...
} catch (e) {
  if (e instanceof ApiError && e.code === "GEN_CAP_REACHED") {
    setNotice(t("gen.capReached"));   // use the component's existing notice/toast state
    return;
  }
  // ...existing error handling...
}
```

If there is a single shared toast/error boundary, add the `GEN_CAP_REACHED → t("gen.capReached")` mapping there once instead of per-component (DRY).

- [ ] **Step 3: Typecheck + web unit tests**

Run: `cd web && npx tsc --noEmit && npm test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web/src
git commit -m "feat(web): friendly daily-cap-reached notice"
```

---

## Task 12: Docker — env wiring + docs

**Files:**
- Modify: `.env.example`, `README.md`

**Interfaces:**
- No compose change needed (api already gets `.env` via `env_file`); this task documents and verifies.

- [ ] **Step 1: Add env vars to `.env.example`**

Append a documented block:

```bash
# ── Test-phase feedback gate (Feature A) ──
GATE_ENABLED=1              # 0 disables the gate entirely
GATE_LOCK_SECONDS=25200     # lock after this much focused use (7h). Set 60 to demo.
GATE_HEARTBEAT_SEC=60       # client heartbeat interval

# ── Token efficiency (Feature B) ──
POOL_TARGET=7               # stored sets per (skill,band) before generation freezes
DAILY_GEN_CAP=20            # per-user generations/day across all skills; 0 = unlimited
MODEL_SCORE=deepseek/deepseek-chat-v3.1:free   # free review model; override to upgrade
```

- [ ] **Step 2: Add a README section**

Under a new "### Test-phase gate & efficiency knobs" heading in `README.md`, list the same vars in prose and note: gate is one-time per user, admins are exempt (`ADMIN_EMAILS`), and free-model scoring can be upgraded via `MODEL_SCORE`.

- [ ] **Step 3: Verify the stack boots + migration runs**

Run: `docker compose up --build -d && docker compose exec api python -m alembic upgrade head`
Expected: all three services healthy; `alembic upgrade` ends at the new head (or "already at head").

- [ ] **Step 4: Smoke the gate quickly**

Set `GATE_LOCK_SECONDS=120` in `.env`, `docker compose up -d`, sign in, and confirm the gate appears after ~2 focused heartbeats; submit feedback; confirm it disappears and the admin email is logged (`docker compose logs api | grep -i feedback`).

- [ ] **Step 5: Commit**

```bash
git add .env.example README.md
git commit -m "docs: document test-gate + efficiency env vars; verify docker"
```

---

## Task 13: Full regression + update-log

**Files:**
- Create: `logs/test-gate-token-efficiency_2026-07-25_log.md`

- [ ] **Step 1: Run the whole backend suite**

Run: `cd api && .venv/Scripts/python -m pytest -q`
Expected: PASS.

- [ ] **Step 2: Run web tests + typecheck + build**

Run: `cd web && npm test && npx tsc --noEmit && npm run build`
Expected: PASS + successful production build.

- [ ] **Step 3: Secret scan**

Run: `bash tests/secret_scan.sh`
Expected: no secrets flagged.

- [ ] **Step 4: Write the update log**

Create `logs/test-gate-token-efficiency_2026-07-25_log.md` documenting: what changed (Features A/B/C), files touched, why, how to test (`pytest -q`, forced-lock demo via `GATE_LOCK_SECONDS=60`, pool-freeze via repeated `reading/generate`), caveats (free model rate limits/JSON reliability — override `MODEL_SCORE`; active-time is focus-based and approximate), and the final commit hash.

- [ ] **Step 5: Commit**

```bash
git add logs/test-gate-token-efficiency_2026-07-25_log.md
git commit -m "docs: update log for test-gate + token-efficiency"
```

---

## Self-Review Notes (coverage map)

- Spec §2 Gate → Tasks 1,2,3,4,5,8,9,10 (+§2.6 config Task 3, §2.4 endpoints Task 5, §2.2 heartbeat Tasks 5/9).
- Spec §3.1 B1 pool-freeze → Task 6 (incl. level-progression via new-band test).
- Spec §3.2 B2 daily cap → Tasks 6 (reading/listening) + 7 (vocab/lesson/pronounce); "pure pool-serve doesn't count" enforced by only calling `note_generation` after a real generate.
- Spec §3.3 B3 free model → Task 3 (`MODEL_SCORE` default; gateway already reads config).
- Spec §4 Docker → Task 12. Spec §5 cross-cutting (i18n Task 8/10, scoping Tasks 2/5/6, update-log Task 13, migration Task 4).
- Spec §6 testing → tests embedded per task + Task 13 regression. Spec §7 out-of-scope respected (single star+insight, one-time gate, no topology change).
```
