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


# ── Phase 2c: attempt persistence ────────────────────────────────────────────

def test_save_and_list_attempts():
    repo = make_repo()
    wid = repo.save_attempt(
        type="writing", task="task2", prompt="Some prompt", body="My essay.",
        bands={"taskResponse": 6.0, "overall": 6.0}, criteria={"rewrite": "Better."},
        cefr="B2", metrics={"wordCount": 2},
    )
    sid = repo.save_attempt(
        type="speaking", task="part2", prompt="Describe a place", body="I went...",
        bands={"fluencyCoherence": 5.0, "overall": 5.0}, criteria={"feedback": "ok"},
        cefr="B1", metrics={},
    )
    assert isinstance(wid, int) and isinstance(sid, int)

    all_rows = repo.list_attempts()
    assert len(all_rows) == 2
    # newest first
    assert all_rows[0]["id"] == sid
    # summary shape
    assert all_rows[0]["type"] == "speaking"
    assert all_rows[0]["overall"] == 5.0
    assert all_rows[0]["cefr"] == "B1"
    assert "createdAt" in all_rows[0]

    writing_only = repo.list_attempts(type="writing")
    assert len(writing_only) == 1 and writing_only[0]["id"] == wid


def test_get_attempt_full_payload():
    repo = make_repo()
    wid = repo.save_attempt(
        type="writing", task="task2", prompt="P", body="Essay body.",
        bands={"taskResponse": 6.0, "overall": 6.0}, criteria={"rewrite": "Better.", "corrections": []},
        cefr="B2", metrics={"wordCount": 2},
    )
    full = repo.get_attempt(wid)
    assert full["id"] == wid
    assert full["type"] == "writing"
    assert full["prompt"] == "P"
    assert full["body"] == "Essay body."
    assert full["bands"]["overall"] == 6.0
    assert full["rewrite"] == "Better."   # criteria flattened into the payload
    assert full["metrics"]["wordCount"] == 2
    assert repo.get_attempt(9999) is None


def test_trends_groups_by_skill():
    repo = make_repo()
    repo.save_attempt(type="writing", task="task2", prompt="P", body="b",
                      bands={"overall": 5.5}, criteria={}, cefr="B1", metrics={})
    repo.save_attempt(type="writing", task="task2", prompt="P", body="b",
                      bands={"overall": 6.5}, criteria={}, cefr="B2", metrics={})
    repo.save_attempt(type="speaking", task="part2", prompt="P", body="b",
                      bands={"overall": 5.0}, criteria={}, cefr="B1", metrics={})
    tr = repo.trends()
    assert len(tr["writing"]) == 2
    assert len(tr["speaking"]) == 1
    # chronological (oldest first) for a trend line
    assert tr["writing"][0]["overall"] == 5.5
    assert tr["writing"][1]["overall"] == 6.5
    assert "createdAt" in tr["writing"][0]
