"""WS02-04: transcript-only Speaking estimates cannot include a pronunciation score."""

from app.domain.scoring import normalize_speaking_estimate


def test_normalize_strips_fabricated_pronunciation_and_recomputes_overall():
    """A non-compliant model returned a pronunciation number; server must strip it
    and recompute overall from the three text-assessable criteria only."""
    result = {
        "bands": {
            "fluencyCoherence": 6.0,
            "lexicalResource": 6.5,
            "grammaticalRange": 5.5,
            "pronunciation": 7.0,   # fabricated from transcript
            "overall": 6.5,         # includes the fabricated criterion
        },
        "cefr": "B2",
    }
    out = normalize_speaking_estimate(result)
    assert out["bands"]["pronunciation"] == "unassessed"
    # mean(6.0, 6.5, 5.5) = 6.0 — NOT influenced by pronunciation 7.0
    assert out["bands"]["overall"] == 6.0


def test_normalize_official_rounding_applies_to_speaking_overall():
    """mean(7.0, 7.0, 6.5)=6.8333... -> 7.0 per IELTS rounding."""
    result = {"bands": {"fluencyCoherence": 7.0, "lexicalResource": 7.0,
                        "grammaticalRange": 6.5, "pronunciation": 9.0}}
    out = normalize_speaking_estimate(result)
    assert out["bands"]["overall"] == 7.0


def test_normalize_is_idempotent_on_compliant_payload():
    compliant = {"bands": {"fluencyCoherence": 5.0, "lexicalResource": 5.5,
                           "grammaticalRange": 4.5, "pronunciation": "unassessed",
                           "overall": 5.0}}
    once = normalize_speaking_estimate(dict(compliant))
    twice = normalize_speaking_estimate(dict(once))
    assert twice == once


def test_normalize_tolerates_missing_bands():
    assert normalize_speaking_estimate({}) == {}
    assert normalize_speaking_estimate({"bands": None})["bands"] is None


def test_speaking_evaluate_route_enforces_unassessed(client_with_seed, monkeypatch):
    """Live-mode route: a fabricated pronunciation score never reaches the client/persistence."""
    # Arrange a gateway that (badly) fabricates a full examiner-like result.
    class _BadGateway:
        def score(self, task, **kw):
            return {
                "bands": {"fluencyCoherence": 6.0, "lexicalResource": 6.0,
                          "grammaticalRange": 6.0, "pronunciation": 8.0,
                          "overall": 7.0},
                "cefr": "B2",
                "feedback": "ok",
                "score_metadata": {"score_method": "llm_estimate"},
            }

    monkeypatch.setattr(
        "app.routes.speaking._gateway", lambda: _BadGateway()
    )
    r = client_with_seed.post(
        "/api/speaking/evaluate",
        json={"part": "part2", "question": "Describe a book", "transcript": "I read books."},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["bands"]["pronunciation"] == "unassessed"
    assert body["bands"]["overall"] == 6.0


def test_speaking_stub_is_compliant(client_with_seed):
    r = client_with_seed.post(
        "/api/speaking/evaluate",
        json={"part": "part2", "question": "q", "transcript": "I read many books today."},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["stub"] is True
    assert body["bands"]["pronunciation"] == "unassessed"
