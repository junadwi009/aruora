"""Behavioral regressions for the NLTK-free, frozen English metric subset."""
import pytest
from app.services.metric_compat import LexicalRichness, words, sentence_count, ensure_resources
from app.services.metric_resources import MetricResourceError, _verify_cmu, _verify_easy, load_resources
from app.services.essay_metrics import compute_metrics


@pytest.mark.parametrize("text, expected", [
    ("can't, won't", ["can't", "won't"]),
    ("well-known well–known", ["wellknown", "wellknown"]),
    ("12.5 and one_two", ["125", "and", "one_two"]),
    ("?!", []),
])
def test_reference_readability_tokens(text, expected):
    assert words(text) == expected


def test_reference_short_sentence_rule():
    assert sentence_count("One. Two words. Three words here.") == 1
    assert sentence_count("") == 0


def test_reference_mtld_does_not_invent_a_fifty_token_cutoff():
    assert LexicalRichness("hello world").ttr == 1
    assert LexicalRichness("hello world").mtld() == 2
    assert LexicalRichness("hello hello hello hello").mtld() == 2
    assert LexicalRichness("well-known 123 don't").wordlist == ["wellknown", "don", "t"]


def test_tampered_resources_fail_closed():
    with pytest.raises(MetricResourceError):
        _verify_cmu(b"not the pinned dictionary")
    with pytest.raises(MetricResourceError):
        _verify_easy(b"not the pinned easy words")


def test_resource_profile_is_complete():
    ensure_resources()
    counts, easy = load_resources()
    assert len(counts) > 100_000
    assert len(easy) > 2_000
    assert counts["hello"] == 2


def test_missing_resources_cannot_become_a_successful_zero_score(monkeypatch):
    from app.services import metric_compat
    def unavailable():
        raise MetricResourceError("Synthetic resource failure")
    monkeypatch.setattr(metric_compat, "ensure_resources", unavailable)
    with pytest.raises(MetricResourceError):
        compute_metrics("This synthetic essay must not receive fabricated metrics.")
