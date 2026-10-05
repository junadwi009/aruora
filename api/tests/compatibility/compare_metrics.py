"""Differential verification against a frozen, test-only legacy implementation.

The vulnerable baseline is used only in a disposable CI process with synthetic
text. No model import/export, real accounts, credentials, or provider calls.
Only an aggregate JSON report is retained, not installed packages or source.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import random
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def corpus() -> list[str]:
    cases = ["", "   ", "Hello world.", "One.", "?!...", "12345 67890.",
             "I can't, won't, and shouldn't ignore well-known evidence.",
             "Dr. Smith paid $12.50 for 3 books in 2026. They were useful!",
             "Students’ priorities—education, well-being, and work—often overlap.",
             "naïve café résumé coöperate İstanbul 中文 日本語 ١٢٣ 🤖",
             "tabs\tand\nnewlines\r\nshould not alter ownership or scoring.",
             "A b c. D e. F! There are enough words here.",
             "'tis 'the' 'team' 've 'll 're students' can't rock'n'roll",
             "well-known well–known well—known one_two a/b back\\slash",
             "qzxvbnm unknownwordxyz supercalifragilisticexpialidocious"]
    paragraphs = [
        "Public transport helps residents reach work and education. However, ticket prices can discourage frequent travel. A reliable service requires investment, trained staff, and careful planning. Local authorities should measure demand before deciding whether to remove fares.",
        "Technology can support independent learning when feedback is clear and accurate. Students need opportunities to revise their work, question an explanation, and practise difficult tasks. Automation should assist this process rather than hide uncertainty behind an impressive number.",
        "Some families prefer smaller homes near the city centre, while others value space and quiet streets. Neither choice suits everyone. Planning decisions should account for access to schools, public services, affordable housing, and safe travel.",
        "The cat sat on the mat. The cat looked at the door. The door was closed, so the cat waited. A visitor arrived and opened it. The cat went outside, looked around, and returned to the warm room.",
    ]
    cases += paragraphs
    for n in [1, 2, 3, 4, 10, 49, 50, 51, 100, 250, 500]:
        cases += ["word " * n, " ".join(f"word{chr(97 + i % 26)}" for i in range(n)),
                  (paragraphs[n % len(paragraphs)] + " ") * max(1, n // 40)]
    rng = random.Random(20261005)
    tokens = ("people education research transportation beautiful different opinion "
              "analysis costs evidence today responsibility difficulty computer "
              "cat read learned every extraordinary comfortable business money "
              "climate family future change qzxvbnm can't won't we're well-known "
              "a. 42 3.14 naïve İstanbul 東京").split()
    for _ in range(256):
        count = rng.randrange(1, 280)
        sample = []
        for i in range(count):
            word = rng.choice(tokens)
            if i % 11 == 0:
                word = word.upper()
            sample.append(word + rng.choice(["", "", "", ",", ".", "!", "?", "…", ";"]))
        cases.append(rng.choice([" ", "\n", "\t"]).join(sample))
    cases.append((paragraphs[0] + " ") * (30000 // (len(paragraphs[0]) + 1)))
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    from app.services import essay_metrics as candidate
    from app.services import metric_resources as resources
    from app.services.metric_compat import ensure_resources
    import nltk

    versions = {p: importlib.metadata.version(p) for p in
                ("textstat", "lexicalrichness", "nltk", "pyphen", "spacy", "textdescriptives", "en-core-web-sm")}
    assert versions["textstat"] == "0.7.13"
    assert versions["lexicalrichness"] == "0.5.1"
    assert versions["nltk"] == "3.10.3"
    assert versions["pyphen"] == "0.18.1"
    ensure_resources()
    archive = (resources.DATA_DIR / "cmudict.zip").read_bytes()
    resources._verify_cmu(archive)
    with tempfile.TemporaryDirectory(prefix="aruora-reference-corpus-") as directory:
        root = Path(directory)
        target = root / "corpora" / "cmudict"
        target.mkdir(parents=True)
        # Fixed named entry only; never extract arbitrary ZIP paths.
        (target / "cmudict").write_bytes(resources.read_zip_entry(archive, "cmudict/cmudict", 4_000_000))
        nltk.data.path[:] = [str(root)]
        def no_download(*args, **kwargs):
            raise AssertionError("Baseline tried to fetch an unfrozen resource")
        nltk.download = no_download
        original_dictionary = nltk.corpus.cmudict.dict()
        reference_counts = {word: sum(1 for p in variants[0] if p[-1].isdigit())
                            for word, variants in original_dictionary.items()}
        assert reference_counts == resources.load_resources()[0], "First-pronunciation dictionary drift"
        spec = importlib.util.spec_from_file_location("aruora_frozen_legacy_metrics", args.baseline)
        assert spec is not None and spec.loader is not None
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
        cases = corpus()
        failures = []
        for index, text in enumerate(cases):
            before = baseline.compute_metrics(text)
            after = candidate.compute_metrics(text)
            if before != after:
                failures.append({"case": index, "before": before, "after": after})
            if text.strip():
                assert before["syntax"] is not None and after["syntax"] is not None, "Syntax degraded during comparison"
        assert candidate.compute_metrics(cases[15])["readability"]["fleschKincaidGrade"] != 0, "Readability silently degraded"
        report = {"profile": resources.PROFILE, "referenceVersions": versions,
                  "baselineSourceSha256": hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
                  "corpusSha256": hashlib.sha256(json.dumps(cases, ensure_ascii=False).encode()).hexdigest(),
                  "sampleCount": len(cases), "dictionaryWordsCompared": len(reference_counts),
                  "exactMetricEquality": not failures, "mismatchCount": len(failures),
                  "mismatches": failures[:10],
                  "scope": "Deterministic metrics only; no claim of identical stochastic provider responses"}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items() if k != "mismatches"}, sort_keys=True))
        assert not failures, f"{len(failures)} metric mismatches; see aggregate report"


if __name__ == "__main__":
    main()
