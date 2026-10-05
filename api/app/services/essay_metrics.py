"""
Deterministic essay-quality metrics for Writing evaluation.

English readability and lexical diversity use the frozen compatibility subset
in metric_compat.py. Syntax retains the existing spaCy/TextDescriptives pipeline.
Output names, final rounding and metric arithmetic are unchanged. Missing or
tampered frozen readability resources fail scoring rather than fabricate zeros.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
_nlp = None
_nlp_attempted = False


def _get_nlp():
    """Load the existing syntax pipeline once; preserve its optional behavior."""
    global _nlp, _nlp_attempted
    if _nlp_attempted:
        return _nlp
    _nlp_attempted = True
    try:
        import spacy
        import textdescriptives  # noqa: F401 — registers the spaCy factories
        nlp = spacy.load("en_core_web_sm")
        nlp.add_pipe("textdescriptives/dependency_distance")
        nlp.add_pipe("textdescriptives/descriptive_stats")
        _nlp = nlp
        logger.info("essay_metrics: spaCy pipeline loaded (en_core_web_sm + textdescriptives)")
    except Exception as exc:
        logger.warning("essay_metrics: spaCy unavailable — syntax section will be None. %s", exc)
        _nlp = None
    return _nlp


def compute_metrics(essay: str) -> dict:
    """Compute the existing camelCase metric contract for English Writing."""
    text = (essay or "").strip()
    if not text:
        return _empty_metrics()
    word_count = len(text.split())
    if word_count == 0:
        return _empty_metrics()
    readability = _compute_readability(text)
    import re as _re
    sentence_count = max(1, len(_re.split(r"[.!?]+", text.rstrip(".!? "))))
    lexical_diversity = _compute_lexical_diversity(text)
    syntax, sentence_count_spacy = _compute_syntax(text)
    if sentence_count_spacy is not None:
        sentence_count = sentence_count_spacy
    return {
        "wordCount": word_count,
        "sentenceCount": sentence_count,
        "readability": readability,
        "lexicalDiversity": lexical_diversity,
        "syntax": syntax,
    }


def _empty_metrics() -> dict:
    return {
        "wordCount": 0,
        "sentenceCount": 0,
        "readability": {
            "fleschReadingEase": 0.0,
            "fleschKincaidGrade": 0.0,
            "gunningFog": 0.0,
        },
        "lexicalDiversity": {"ttr": 0.0, "mtld": None},
        "syntax": None,
    }


def _round(value, ndigits: int = 2) -> float:
    import math
    try:
        f = float(value)
        if not math.isfinite(f):
            return 0.0
        return round(f, ndigits)
    except (TypeError, ValueError):
        return 0.0


def _compute_readability(text: str) -> dict:
    from app.services import metric_compat as textstat
    # This check is deliberately OUTSIDE the legacy numerical fallback.
    textstat.ensure_resources()
    try:
        return {
            "fleschReadingEase": _round(textstat.flesch_reading_ease(text), 1),
            "fleschKincaidGrade": _round(textstat.flesch_kincaid_grade(text), 1),
            "gunningFog": _round(textstat.gunning_fog(text), 1),
        }
    except Exception as exc:
        logger.warning("essay_metrics: readability error — %s", exc)
        return {"fleschReadingEase": 0.0, "fleschKincaidGrade": 0.0, "gunningFog": 0.0}


def _compute_lexical_diversity(text: str) -> dict:
    try:
        from app.services.metric_compat import LexicalRichness
        lr = LexicalRichness(text)
        ttr = _round(lr.ttr, 2)
        mtld: float | None = None
        try:
            mtld = _round(lr.mtld(), 1)
        except Exception:
            mtld = None
        return {"ttr": ttr, "mtld": mtld}
    except Exception as exc:
        logger.warning("essay_metrics: lexical diversity error — %s", exc)
        return {"ttr": 0.0, "mtld": None}


def _compute_syntax(text: str) -> tuple[dict | None, int | None]:
    nlp = _get_nlp()
    if nlp is None:
        return None, None
    try:
        doc = nlp(text)
        sents = list(doc.sents)
        sentence_count = len(sents)
        mean_sent_len: float | None = None
        try:
            ds = doc._.descriptive_stats
            if ds and "sentence_length_mean" in ds:
                mean_sent_len = _round(ds["sentence_length_mean"], 1)
        except Exception:
            pass
        mean_dep_depth: float | None = None
        try:
            dd = doc._.dependency_distance
            if dd and "dependency_distance_mean" in dd:
                mean_dep_depth = _round(dd["dependency_distance_mean"], 2)
        except Exception:
            pass
        n_long_words: int | None = None
        try:
            n_long_words = sum(
                1 for tok in doc
                if not tok.is_punct and not tok.is_space and len(tok.text) >= 7
            )
        except Exception:
            pass
        syntax = {
            "meanSentenceLength": mean_sent_len,
            "meanDependencyDepth": mean_dep_depth,
            "nLongWords": n_long_words,
        }
        return syntax, sentence_count
    except Exception as exc:
        logger.warning("essay_metrics: syntax error — %s", exc)
        return None, None
