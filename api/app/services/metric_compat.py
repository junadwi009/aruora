"""The exact English subset used by ARUORA, without NLTK or model-file APIs.

Adapted from MIT-licensed textstat 0.7.13 and LexicalRichness 0.5.1.
See METRIC_THIRD_PARTY_NOTICES.txt for attribution and license terms.
Not a replacement for the libraries' other languages, tokenizers or metrics.
Arithmetic order, apostrophe rules, first pronunciation, easy-word exclusion,
MTLD threshold and statistics.mean intentionally preserve the reference behavior.
"""
from __future__ import annotations

from functools import lru_cache
from importlib.metadata import version
import re
from statistics import mean
import string

from .metric_resources import MetricResourceError, load_resources


@lru_cache(maxsize=1)
def _pyphen():
    if version("pyphen") != "0.18.1":
        raise MetricResourceError("The metric profile requires the frozen Pyphen version")
    from pyphen import Pyphen
    return Pyphen(lang="en_US")


def ensure_resources() -> None:
    load_resources()
    _pyphen()


def words(text: str, *, lowercase: bool = False) -> list[str]:
    # textstat backend defaults, not textstatistics.remove_punctuation defaults.
    text = re.sub(r"\'(?![tsd]|ve|ll|re)", "", text)
    text = re.sub(r"[^\w\s\']", "", text)
    if lowercase:
        text = text.lower()
    return text.split()


def sentence_count(text: str) -> int:
    if not text:
        return 0
    sentences = re.findall(r"\b[^.!?]+[.!?]*", text, re.UNICODE)
    ignored = sum(len(words(sentence)) <= 2 for sentence in sentences)
    return max(1, len(sentences) - ignored)


def syllable_count(text: str) -> int:
    if not text:
        return 0
    cmu, _ = load_resources()
    dictionary = _pyphen()
    count = 0
    for word in words(text, lowercase=True):
        if word in cmu:
            count += cmu[word]
        else:
            count += len(dictionary.positions(word)) + 1
    return count


def _ratios(text: str) -> tuple[float, float]:
    count = len(words(text))
    sentences = sentence_count(text)
    length = count / sentences if sentences else 0.0
    syllables = syllable_count(text) / count if count else 0.0
    return length, syllables


def flesch_reading_ease(text: str) -> float:
    length, syllables = _ratios(text)
    if length == 0 or syllables == 0:
        return 0.0
    return 206.835 - 1.015 * length - 84.6 * syllables


def flesch_kincaid_grade(text: str) -> float:
    length, syllables = _ratios(text)
    if length == 0 or syllables == 0:
        return 0.0
    return (0.39 * length) + (11.8 * syllables) - 15.59


def gunning_fog(text: str) -> float:
    tokens = words(text)
    _, easy = load_resources()
    difficult = sum(word.lower() not in easy and syllable_count(word.lower()) >= 3 for word in tokens)
    if not tokens:
        return 0.0
    percent = 100 * difficult / len(tokens)
    length = len(tokens) / sentence_count(text)
    return 0.4 * (length + percent)


def _preprocess(text: str) -> str:
    return re.sub(r"[0-9]+", "", text.lower()).replace("–", "").replace("—", "").replace("-", "")


class LexicalRichness:
    """Only the default tokenizer, TTR and MTLD used by this application."""
    def __init__(self, text: str) -> None:
        text = _preprocess(_preprocess(text))
        for mark in string.punctuation:
            text = text.replace(mark, " ")
        self.wordlist = text.split()
        self.words = len(self.wordlist)
        self.terms = len(set(self.wordlist))

    @property
    def ttr(self) -> float:
        return self.terms / self.words

    def mtld(self, threshold: float = 0.72) -> float:
        def measure(reverse: bool) -> float:
            terms: set[str] = set()
            counter = 0
            factors = 0
            iterator = reversed(self.wordlist) if reverse else iter(self.wordlist)
            for word in iterator:
                counter += 1
                terms.add(word)
                ratio = len(terms) / counter
                if ratio <= threshold:
                    counter = 0
                    terms = set()
                    factors += 1
            if counter > 0:
                factors += (1 - ratio) / (1 - threshold)
            if factors == 0:
                ratio = self.terms / self.words
                if ratio == 1:
                    factors += 1
                else:
                    factors += (1 - ratio) / (1 - threshold)
            return len(self.wordlist) / factors
        return mean((measure(False), measure(True)))
