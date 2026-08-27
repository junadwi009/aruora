"""WS02-06: prompts must stay free of copyrighted/official descriptor text.

ARUORA rubrics use original internal paraphrases of publicly described criteria.
Official IELTS material and trademarks must not be republished without a
documented permission/licence (a Legal/IP audit ticket is required for any
retained official text — see docs/production-readiness/02 §Task WS02-06).
"""

import re
from pathlib import Path

PROMPTS_FILE = Path(__file__).resolve().parents[1] / "app" / "services" / "prompts.py"

# Phrases that historically appeared in (or are distinctive to) the official
# public band descriptor documents, plus references to those documents.
FORBIDDEN_PATTERNS = [
    r"attracts no attention",
    r"fully extended and well-supported",
    r"skilfully managed",
    r"very natural control",
    r"rare minor errors occur only as 'slips'",
    r"slips'\.",
    r"full range of phonological features",
    r"L1 accent has minimal effect",
    r"positive features of Band \d",
    r"Is intelligible throughout",
    r"Band Descriptors",           # no references to official descriptor documents
    r"public version",
]

# Product-claim wording rules (02 §Product wording requirements).
FORBIDDEN_CLAIMS = [
    r"official score",
    r"certified IELTS examiner",
    r"guaranteed band",
]

# The model must never be presented AS an examiner/official authority.
PERSONA_PATTERNS = [
    r"fully trained IELTS examiner",
    r"You are an IELTS examiner\b",
]


def test_prompts_contain_no_forbidden_descriptor_phrases():
    text = PROMPTS_FILE.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_PATTERNS:
        assert not re.search(pattern, text), (
            f"prompts.py contains protected/verbatim material matching {pattern!r}"
        )


def test_prompts_make_no_official_score_claims():
    text = PROMPTS_FILE.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_CLAIMS:
        assert not re.search(pattern, text, flags=re.IGNORECASE), (
            f"prompts.py violates claim wording rules: {pattern!r}"
        )


def test_prompts_use_practice_estimate_persona():
    text = PROMPTS_FILE.read_text(encoding="utf-8")
    for pattern in PERSONA_PATTERNS:
        assert not re.search(pattern, text, flags=re.IGNORECASE), (
            f"prompts.py must not present the model as an official authority: {pattern!r}"
        )
    # Estimation framing is present for both scored skills.
    assert "practice estimate" in text


def test_scoring_prompts_label_cefr_alignment_approximate():
    text = PROMPTS_FILE.read_text(encoding="utf-8")
    score_section = text.split("SCORE_PROMPTS")[1]
    assert "approximate" in score_section.lower()
