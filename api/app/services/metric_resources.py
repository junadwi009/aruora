"""Immutable, data-only resources for the English metric compatibility profile.

Preparation is an explicit build/development command, never a request-time
network operation. Only two named data entries are read from checksum-pinned
upstream archives; no archive paths are extracted or executed.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
from functools import lru_cache
import urllib.request
import zipfile

PROFILE = "english-textstat-0.7.13-lexicalrichness-0.5.1-cmu06-pyphen-0.18.1"
DATA_DIR = Path(__file__).with_name("_metric_data")
CMU_URL = "https://raw.githubusercontent.com/nltk/nltk_data/550b6625bcef1f2abff2ff770a5a0d272c9c6b2a/packages/corpora/cmudict.zip"
CMU_SHA256 = "d07cca47fd72ad32ea9d8ad1219f85301eeaf4568f8b6b73747506a71fb5afd6"
TEXTSTAT_URL = "https://files.pythonhosted.org/packages/ca/31/0eb4cc5bb021b4ceaaa602c59ba16ce99256b9dd30981bef3f3a53d8555f/textstat-0.7.13-py3-none-any.whl"
TEXTSTAT_SHA256 = "04b1ec995d1e8b2e628759497e6b23204a9ec91dcd652447d8cbba9478f25471"
EASY_GIT_BLOB = "dc5488eba44e9af22cf5161efaf0d07615b1ac0e"


class MetricResourceError(RuntimeError):
    """Do not fabricate metrics when the immutable resource set is unavailable."""


def _bounded_read(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise MetricResourceError("Metric resource exceeds its size limit")
    return data


def _verify_cmu(data: bytes) -> None:
    if hashlib.sha256(data).hexdigest() != CMU_SHA256:
        raise MetricResourceError("CMU resource checksum mismatch")


def _verify_easy(data: bytes) -> None:
    # This is the exact Git object of textstat 0.7.13's bundled English list.
    digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if digest != EASY_GIT_BLOB:
        raise MetricResourceError("English word-list checksum mismatch")


def read_zip_entry(data: bytes, name: str, limit: int) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entry = archive.getinfo(name)
        if entry.is_dir() or entry.file_size > limit:
            raise MetricResourceError("Invalid metric archive entry")
        with archive.open(entry) as stream:
            result = stream.read(limit + 1)
        if len(result) > limit:
            raise MetricResourceError("Metric archive entry exceeds its size limit")
        return result


@lru_cache(maxsize=1)
def load_resources() -> tuple[dict[str, int], frozenset[str]]:
    """Return first-pronunciation syllable counts and the frozen easy-word set."""
    try:
        archive = _bounded_read(DATA_DIR / "cmudict.zip", 1_000_000)
        easy = _bounded_read(DATA_DIR / "easy_words.txt", 30_000)
        _verify_cmu(archive)
        _verify_easy(easy)
        raw = read_zip_entry(archive, "cmudict/cmudict", 4_000_000)
        counts: dict[str, int] = {}
        for line in raw.decode("utf-8").splitlines():
            pieces = line.split()
            if len(pieces) < 3 or not pieces[1].isdigit():
                raise MetricResourceError("Invalid CMU dictionary record")
            word = pieces[0].lower()
            # NLTK CMUDictCorpusReader preserves entry order; textstat uses [0].
            if word not in counts:
                counts[word] = sum(1 for phone in pieces[2:] if phone[-1].isdigit())
        if len(counts) < 100_000:
            raise MetricResourceError("Incomplete CMU dictionary")
        return counts, frozenset(line.strip() for line in easy.decode("utf-8").splitlines())
    except MetricResourceError:
        raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise MetricResourceError("Metric data is unavailable; run the explicit preparation command") from exc


def _download(url: str, expected: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ARUORA-metric-resource-builder/1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(limit + 1)
    if len(data) > limit or hashlib.sha256(data).hexdigest() != expected:
        raise MetricResourceError("Downloaded metric resource failed integrity verification")
    return data


def prepare() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DATA_DIR / "cmudict.zip"
    easy_path = DATA_DIR / "easy_words.txt"
    if archive_path.exists():
        archive = _bounded_read(archive_path, 1_000_000)
        _verify_cmu(archive)
    else:
        archive = _download(CMU_URL, CMU_SHA256, 1_000_000)
        temporary = archive_path.with_suffix(".tmp")
        temporary.write_bytes(archive)
        temporary.replace(archive_path)
    if easy_path.exists():
        _verify_easy(_bounded_read(easy_path, 30_000))
    else:
        wheel = _download(TEXTSTAT_URL, TEXTSTAT_SHA256, 2_000_000)
        easy = read_zip_entry(wheel, "textstat/resources/en/easy_words.txt", 30_000)
        _verify_easy(easy)
        temporary = easy_path.with_suffix(".tmp")
        temporary.write_bytes(easy)
        temporary.replace(easy_path)
    load_resources.cache_clear()
    counts, easy_words = load_resources()
    manifest = {"profile": PROFILE, "cmuSourceSha256": CMU_SHA256,
                "textstatSourceSha256": TEXTSTAT_SHA256,
                "easyWordsGitBlob": EASY_GIT_BLOB,
                "easyWordsSha256": hashlib.sha256(easy_path.read_bytes()).hexdigest(),
                "dictionaryWords": len(counts), "easyWords": len(easy_words)}
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare"]:
        prepare()
    elif sys.argv[1:] == ["--check"]:
        counts, easy = load_resources()
        print(json.dumps({"profile": PROFILE, "dictionaryWords": len(counts), "easyWords": len(easy)}))
    else:
        raise SystemExit("Usage: python app/services/metric_resources.py --prepare|--check")
