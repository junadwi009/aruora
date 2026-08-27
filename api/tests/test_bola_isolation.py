"""WS04 — BOLA test matrix (docs/production-readiness/04 §Required matrix).

For each ID-based user route:
1. User A creates an object; 2. User B signs in; 3. B attacks A's ID;
4. no data disclosure, no mutation; 5. A's row remains unchanged.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.services.llm import LlmGateway


@pytest.fixture()
def two_users():
    """One shared repo; two independently authenticated browser sessions."""
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    repo = Repository(Session)
    app = create_app({"TESTING": True,
                      "REPO": repo,
                      "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"}))})
    a = app.test_client()
    b = app.test_client()
    a.post("/api/account/register",
           json={"email": "alice@example.com", "password": "correct horse battery staple"})
    b.post("/api/account/register",
           json={"email": "bob@example.com", "password": "correct horse battery staple"})
    # fetch ids from the session (each client's own /me)
    ida = a.get("/api/account/me").get_json()["id"]
    idb = b.get("/api/account/me").get_json()["id"]
    yield {"repo": repo, "a": a, "b": b, "ida": ida, "idb": idb}
    eng.dispose()


# ── history attempt detail ────────────────────────────────────────────────────

def test_bola_history_attempt_detail(two_users):
    d = two_users
    aid = d["repo"].save_attempt(
        d["ida"], type="writing", task="task2", prompt="p", body="A's private essay.",
        bands={"overall": 6.0}, criteria={}, cefr="B2", metrics={},
    )
    # B cannot read A's attempt…
    r = d["b"].get(f"/api/history/attempt/{aid}")
    assert r.status_code == 404
    assert "essay" not in r.get_data(as_text=True)
    # …and sequential-ID guessing of an unallocated id is equally not-found.
    assert d["b"].get("/api/history/attempt/999999").status_code == 404
    # A still reads it; body unchanged.
    mine = d["a"].get(f"/api/history/attempt/{aid}")
    assert mine.status_code == 200 and "A's private essay." in mine.get_json()["body"]


# ── cards: review + delete ────────────────────────────────────────────────────

def _mk_card(d):
    return d["a"].post(
        "/api/cards", json={"front": "relevant", "back": "pertinent"}
    ).get_json()["id"]


def test_bola_card_review_and_delete(two_users):
    d = two_users
    cid = _mk_card(d)

    # review — B cannot mutate A's card schedule
    r = d["b"].post(f"/api/cards/{cid}/review", json={"quality": 5})
    assert r.status_code == 404
    card = next(c for c in d["a"].get("/api/cards").get_json()["cards"]
                if c["id"] == cid)
    assert card["reps"] == 0 and card["interval"] == 0

    # delete — B cannot remove A's card
    assert d["b"].delete(f"/api/cards/{cid}").status_code == 404
    assert any(c["id"] == cid
               for c in d["a"].get("/api/cards").get_json()["cards"])

    # A can still delete their own card
    assert d["a"].delete(f"/api/cards/{cid}").status_code == 200
    assert all(c["id"] != cid
               for c in d["a"].get("/api/cards").get_json()["cards"])


# ── milestones through parent chain ──────────────────────────────────────────

def _mk_milestone(d):
    d["a"].post("/api/program", json={"lengthDays": 30})
    return d["a"].post(
        "/api/program/milestones",
        json={"title": "Private milestone", "dayTarget": 10, "targets": {}},
    ).get_json()["id"]


def test_bola_milestone_update_and_delete(two_users):
    d = two_users
    mid = _mk_milestone(d)

    # update — B cannot touch A's milestone (parent-chain ownership)
    r = d["b"].put(f"/api/program/milestones/{mid}",
                   json={"title": "HACKED", "dayTarget": 99})
    assert r.status_code == 404

    # delete — B cannot remove it either
    assert d["b"].delete(f"/api/program/milestones/{mid}").status_code == 404

    ms = [m for m in d["a"].get("/api/program/milestones").get_json()
          if m["id"] == mid]
    assert ms[0]["title"] == "Private milestone" and ms[0]["dayTarget"] == 10


# ── export contains only the requester's data ────────────────────────────────

def test_export_scoped_to_requester_only(two_users):
    d = two_users
    d["repo"].save_attempt(
        d["ida"], type="writing", task="t", prompt="p", body="AAA-only essay",
        bands={"overall": 6.0}, criteria={}, cefr="B2", metrics={},
    )
    d["repo"].save_attempt(
        d["idb"], type="writing", task="t", prompt="p", body="BBB-only essay",
        bands={"overall": 6.0}, criteria={}, cefr="B2", metrics={},
    )
    ea = d["a"].get("/api/account/export").get_json()
    eb = d["b"].get("/api/account/export").get_json()

    bodies_a = [x["body"] for x in ea["attempts"]]
    bodies_b = [x["body"] for x in eb["attempts"]]
    assert "AAA-only essay" in bodies_a and "BBB-only essay" not in bodies_a
    assert "BBB-only essay" in bodies_b and "AAA-only essay" not in bodies_b

    # No secrets ever leave the data layer via export.
    blob_a = str(ea)
    assert "password_hash" not in blob_a and "google_sub" not in blob_a


# ── account deletion removes every owned row (schema cascades) ───────────────

def test_account_deletion_cascades_all_owned_rows(two_users):
    d = two_users
    repo = d["repo"]
    uid = d["ida"]
    repo.save_attempt(uid, type="writing", task="t", prompt="p", body="x",
                      bands={"overall": 6.0}, criteria={}, cefr="B2", metrics={})
    repo.save_mock(uid, listening=6.0, reading=6.5, overall=6.0)
    repo.add_card(uid, "front", "back")
    prog = repo.create_program(uid, 30)
    repo.add_milestones(prog.id,
                        [{"idx": 0, "dayTarget": 15, "title": "m", "targets": {}}])
    repo.feedback_add(uid, 5, "great drills")
    repo.gen_incr_today(uid, "2026-08-27")
    repo.set_skill_level(uid, "reading", "B2")

    ok = repo.delete_account(uid)
    assert ok is True
    assert repo.delete_account(uid) is False          # idempotent second call

    sf = repo._sf
    with sf() as s:
        from sqlalchemy import text
        orphans = []
        for tbl, col in [("attempts", "user_id"), ("mocks", "user_id"),
                         ("cards", "user_id"), ("programs", "user_id"),
                         ("skill_levels", "user_id"), ("feedback", "user_id"),
                         ("gen_usage", "user_id")]:
            n = s.execute(text(
                f"SELECT COUNT(*) FROM {tbl} WHERE {col} = :u"
            ), {"u": uid}).scalar_one()
            if n:
                orphans.append((tbl, n))
        n_ms = s.execute(text(
            "SELECT COUNT(*) FROM milestones WHERE program_id = :p"
        ), {"p": prog.id}).scalar_one()
    assert orphans == [] and n_ms == 0, f"deletion left owned rows: {orphans}"

    # B survives intact
    assert d["b"].get("/api/account/me").status_code == 200