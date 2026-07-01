"""Backend language plumbing: X-Lang → Tips fixture + LLM langNote injection.

Practice content (passages, transcripts, questions, prompts, roleplay reply)
stays English; only learner-facing guidance prose localizes.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.config import Config
from app.data.models import Base
from app.data.repositories import Repository
from app.data.seed import seed_all
from app.services.llm import LlmGateway
from app.services.prompts import lang_note, SCORE_PROMPTS, GENERATE_PROMPTS


def _client():
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    seed_all(Session)
    overrides = {
        "TESTING": True, "SESSION_SECRET": "test",
        "REPO": Repository(Session),
        "GATEWAY": LlmGateway(Config({"LLM_MODE": "stub"})),
    }
    return create_app(overrides).test_client()


# ── lang_note helper ─────────────────────────────────────────────────────────

def test_lang_note_id_nonempty_en_empty():
    assert lang_note("en") == ""
    assert lang_note(None) == ""
    note = lang_note("id")
    assert "Bahasa Indonesia" in note
    # must protect the English-only fields
    assert "KEEP IN ENGLISH" in note


def test_learner_facing_prompts_carry_langnote_placeholder():
    for tmpl in (SCORE_PROMPTS["writing"], SCORE_PROMPTS["speaking"],
                 SCORE_PROMPTS["pronounce"], GENERATE_PROMPTS["lesson"]):
        assert "{langNote}" in tmpl
    # roleplay reply is practice content → must NOT localize
    assert "{langNote}" not in SCORE_PROMPTS["roleplay"]
    # exam content generators stay English → no placeholder
    assert "{langNote}" not in GENERATE_PROMPTS["reading"]


# ── Tips route localizes by X-Lang ───────────────────────────────────────────

def test_tips_default_english():
    r = _client().get("/api/tips/reading")
    assert r.status_code == 200
    assert r.get_json()["title"] == "Reading strategy"


def test_tips_indonesian_with_header():
    r = _client().get("/api/tips/reading", headers={"X-Lang": "id"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["title"] == "Strategi Reading"
    assert len(body["bullets"]) == 5


def test_tips_unknown_skill_404():
    assert _client().get("/api/tips/nope", headers={"X-Lang": "id"}).status_code == 404


# ── Gateway injects langNote into a live-style format (no network) ────────────

def test_gateway_score_accepts_lang_kwarg():
    """score(..., lang=...) must be accepted and not crash in stub mode."""
    gw = LlmGateway(Config({"LLM_MODE": "stub"}))
    # stub mode ignores lang but the kwarg must be accepted
    out = gw.score("writing", lang="id", taskType="task2", prompt="p", essay="e",
                   metricsSummary="words=1")
    assert "bands" in out
