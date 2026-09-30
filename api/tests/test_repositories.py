from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.models import Base, PlacementCombo, PlacementItem, GeneratedSet
from app.data.repositories import Repository


def make_repo():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return Repository(sessionmaker(bind=eng))


# ── verbatim test from brief ──────────────────────────────────────────────────

def test_user_and_skill_levels():
    repo = make_repo()
    u = repo.create_user("Arjuna", "work", 6.5, {})
    repo.set_skill_level(u.id, "reading", "C1")
    repo.set_skill_level(u.id, "reading", "C2")  # upsert
    levels = dict(repo.get_skill_levels(u.id))
    assert levels["reading"] == "C2"


# ── extra tests required by brief ────────────────────────────────────────────

def test_serve_set_returns_payload_or_none():
    repo = make_repo()
    # Insert two GeneratedSet rows for ("reading", "B2")
    sf = repo._sf
    with sf() as s:
        s.add(GeneratedSet(skill="reading", band="B2", set_index=0, payload={"q": "first"}))
        s.add(GeneratedSet(skill="reading", band="B2", set_index=1, payload={"q": "second"}))
        s.commit()

    result = repo.serve_set("reading", "B2")
    assert result is not None
    assert result.get("q") in ("first", "second")

    none_result = repo.serve_set("writing", "C1")
    assert none_result is None


def test_get_combo_shape():
    repo = make_repo()
    sf = repo._sf
    with sf() as s:
        s.add(PlacementCombo(combo_id=1, sections={"listening": 1, "reading": 1}, target_minutes=50))
        s.add(PlacementItem(combo_id=1, skill="listening", band_tag="B2", type="mc", payload={"q": "a"}, section_seconds=900))
        s.add(PlacementItem(combo_id=1, skill="reading", band_tag="B2", type="tfng", payload={"q": "b"}, section_seconds=1200))
        s.commit()

    combo = repo.get_combo(1)
    assert combo["comboId"] == 1
    assert combo["targetMinutes"] == 50
    assert isinstance(combo["sections"], dict)
    assert len(combo["items"]) == 2
    # check camelCase keys on items
    item_keys = set(combo["items"][0].keys())
    assert "bandTag" in item_keys
    assert "sectionSeconds" in item_keys
    assert "id" in item_keys
    assert "skill" in item_keys
    assert "type" in item_keys
    assert "payload" in item_keys

    # KeyError for unknown combo_id
    import pytest
    with pytest.raises(KeyError):
        repo.get_combo(999)


def test_program_and_milestones():
    repo = make_repo()
    u = repo.create_user("Arjuna", "work", 6.5, {})
    p = repo.create_program(u.id, 90)
    assert p.id is not None

    repo.add_milestones(p.id, [
        {"idx": 0, "dayTarget": 45, "title": "x", "targets": {"reading": "C1"}}
    ])

    milestones = repo.get_milestones(p.id)
    assert len(milestones) == 1
    m = milestones[0]
    assert m["idx"] == 0
    assert m["dayTarget"] == 45
    assert m["title"] == "x"
    assert m["targets"] == {"reading": "C1"}


# ── Phase 2c/3b: attempt persistence (user-scoped) ───────────────────────────

def _uid(repo):
    return repo.create_account("u%d@e.com" % id(repo), "correct horse battery staple").id


def test_save_and_list_attempts():
    repo = make_repo()
    uid = _uid(repo)
    wid = repo.save_attempt(
        uid, type="writing", task="task2", prompt="Some prompt", body="My essay.",
        bands={"taskResponse": 6.0, "overall": 6.0}, criteria={"rewrite": "Better."},
        cefr="B2", metrics={"wordCount": 2},
    )
    sid = repo.save_attempt(
        uid, type="speaking", task="part2", prompt="Describe a place", body="I went...",
        bands={"fluencyCoherence": 5.0, "overall": 5.0}, criteria={"feedback": "ok"},
        cefr="B1", metrics={},
    )
    assert isinstance(wid, int) and isinstance(sid, int)

    all_rows = repo.list_attempts(uid)
    assert len(all_rows) == 2
    assert all_rows[0]["id"] == sid  # newest first
    assert all_rows[0]["type"] == "speaking"
    assert all_rows[0]["overall"] is None
    assert all_rows[0]["scoreMethod"] is None
    assert all_rows[0]["modelProvider"] is None

    writing_only = repo.list_attempts(uid, type="writing")
    assert len(writing_only) == 1 and writing_only[0]["id"] == wid


def test_get_attempt_full_payload():
    repo = make_repo()
    uid = _uid(repo)
    wid = repo.save_attempt(
        uid, type="writing", task="task2", prompt="P", body="Essay body.",
        bands={"taskResponse": 6.0, "overall": 6.0}, criteria={"rewrite": "Better.", "corrections": []},
        cefr="B2", metrics={"wordCount": 2},
    )
    full = repo.get_attempt(uid, wid)
    assert full["prompt"] == "P" and full["rewrite"] == "Better."
    assert repo.get_attempt(uid, 9999) is None


def test_save_attempt_persists_scoring_metadata():
    """WS02-03: the AI-scoring metadata envelope is persisted and returned."""
    repo = make_repo()
    uid = _uid(repo)
    meta = {
        "score_method": "llm_estimate",
        "score_version": "1.0",
        "model_provider": "openrouter",
        "model_id": "test/model-1",
        "prompt_version": "1.0",
        "rubric_version": "1.0",
        "calibration_version": "1.0",
    }
    aid = repo.save_attempt(
        uid, type="writing", task="task2", prompt="P", body="Essay body.",
        bands={"overall": 6.0}, criteria={}, cefr="B2", metrics={},
        score_metadata=meta,
    )
    full = repo.get_attempt(uid, aid)
    sm = full["scoreMetadata"]
    assert sm["scoreMethod"] == "llm_estimate"
    assert sm["scoreVersion"] == "1.0"
    assert sm["modelProvider"] == "openrouter"
    assert sm["modelId"] == "test/model-1"
    assert sm["promptVersion"] == "1.0"
    assert sm["rubricVersion"] == "1.0"
    assert sm["calibrationVersion"] == "1.0"

def test_list_attempts_exposes_overall_for_trusted_non_stub_estimate():
    repo = make_repo()
    uid = _uid(repo)

    aid = repo.save_attempt(
        uid,
        type="speaking",
        task="part2",
        prompt="P",
        body="Transcript.",
        bands={"overall": 5.0},
        criteria={},
        cefr="B1",
        metrics={},
        score_metadata={
            "score_method": "llm_estimate",
            "score_version": "test-v1",
            "model_provider": "test-provider",
            "model_id": "test-model",
            "prompt_version": "test-prompt",
            "rubric_version": "test-rubric",
            "calibration_version": "test-calibration",
        },
    )

    row = repo.list_attempts(uid)[0]

    assert row["id"] == aid
    assert row["overall"] == 5.0
    assert row["scoreMethod"] == "llm_estimate"
    assert row["modelProvider"] == "test-provider"

def test_save_attempt_without_metadata_is_backwards_compatible():
    """Attempts saved without score_metadata keep working (nullable columns)."""
    repo = make_repo()
    uid = _uid(repo)
    aid = repo.save_attempt(
        uid, type="speaking", task="part2", prompt="P", body="T.",
        bands={"overall": 5.0}, criteria={}, cefr="B1", metrics={},
    )
    full = repo.get_attempt(uid, aid)
    assert full["scoreMetadata"]["scoreMethod"] is None


def test_attempts_are_isolated_per_user():
    """Security: one user can never see or read another user's attempts."""
    repo = make_repo()
    a = repo.create_account("a@e.com", "correct horse battery staple").id
    b = repo.create_account("b@e.com", "correct horse battery staple").id
    aid = repo.save_attempt(a, type="writing", task="t", prompt="p", body="x",
                            bands={"overall": 6.0}, criteria={}, cefr="B2", metrics={})
    # B's listing is empty; B cannot fetch A's attempt by id
    assert repo.list_attempts(b) == []
    assert repo.get_attempt(b, aid) is None
    assert repo.trends(b)["writing"] == []
    # A still sees their own
    assert len(repo.list_attempts(a)) == 1
    assert repo.get_attempt(a, aid) is not None


def test_trends_groups_by_skill():
    repo = make_repo()
    uid = _uid(repo)
    repo.save_attempt(uid, type="writing", task="t", prompt="P", body="b",
                      bands={"overall": 5.5}, criteria={}, cefr="B1", metrics={})
    repo.save_attempt(uid, type="writing", task="t", prompt="P", body="b",
                      bands={"overall": 6.5}, criteria={}, cefr="B2", metrics={})
    repo.save_attempt(uid, type="speaking", task="p", prompt="P", body="b",
                      bands={"overall": 5.0}, criteria={}, cefr="B1", metrics={})
    tr = repo.trends(uid)
    assert len(tr["writing"]) == 2 and len(tr["speaking"]) == 1
    assert tr["writing"][0]["overall"] == 5.5 and tr["writing"][1]["overall"] == 6.5


# ── Phase 2d-1/3b: lessons (user-scoped) ─────────────────────────────────────

def test_save_and_get_lesson_upsert():
    repo = make_repo()
    uid = _uid(repo)
    assert repo.get_lesson(uid, 1) is None
    repo.save_lesson(uid, 1, {"goal": "first"}, "writing")
    got = repo.get_lesson(uid, 1)
    assert got["day"] == 1 and got["lesson"]["goal"] == "first"
    repo.save_lesson(uid, 1, {"goal": "second"}, "listening")  # upsert
    assert repo.get_lesson(uid, 1)["lesson"]["goal"] == "second"
    # another user's day-1 is independent
    other = repo.create_account("o@e.com", "correct horse battery staple").id
    assert repo.get_lesson(other, 1) is None


# ── Phase 2d-2/3b: mock tests (user-scoped) ──────────────────────────────────

def test_save_and_list_mocks():
    repo = make_repo()
    uid = _uid(repo)
    a = repo.save_mock(uid, 6.0, 7.0, 6.5)
    b = repo.save_mock(uid, 5.5, 6.0, 6.0)
    assert isinstance(a, int) and isinstance(b, int)
    rows = repo.list_mocks(uid)
    assert len(rows) == 2 and rows[0]["id"] == b  # newest first
    # isolated
    other = repo.create_account("o2@e.com", "correct horse battery staple").id
    assert repo.list_mocks(other) == []


# ── Phase 2d-4/3b: flashcards (user-scoped) ──────────────────────────────────

def test_cards_add_list_stats_delete():
    from datetime import datetime, timezone
    repo = make_repo()
    uid = _uid(repo)
    cid = repo.add_card(uid, "ubiquitous", "present everywhere")
    n = repo.add_cards(uid, [{"front": "a", "back": "1"}, {"front": "b", "back": "2"}])
    assert isinstance(cid, int) and n == 2
    assert len(repo.list_cards(uid)) == 3
    assert repo.card_stats(uid)["total"] == 3
    now = datetime.now(timezone.utc)
    assert len(repo.due_cards(uid, now)) == 3
    assert repo.delete_card(uid, cid) is True
    assert repo.delete_card(uid, 999999) is False
    assert len(repo.list_cards(uid)) == 2
    # another user cannot delete this user's cards
    other = repo.create_account("o3@e.com", "correct horse battery staple").id
    remaining = repo.list_cards(uid)[0]["id"]
    assert repo.delete_card(other, remaining) is False
    assert repo.card_stats(other)["total"] == 0


def test_card_review_reschedules():
    from datetime import datetime, timezone
    repo = make_repo()
    uid = _uid(repo)
    cid = repo.add_card(uid, "front", "back")
    now = datetime.now(timezone.utc)
    out = repo.review_card(uid, cid, quality=4, now=now)
    assert out is not None and out["reps"] == 1 and out["interval"] == 1
    assert all(c["id"] != cid for c in repo.due_cards(uid, now))
    assert repo.review_card(uid, 999999, quality=4, now=now) is None
    # another user cannot review this user's card
    other = repo.create_account("o4@e.com", "correct horse battery staple").id
    assert repo.review_card(other, cid, quality=4, now=now) is None
