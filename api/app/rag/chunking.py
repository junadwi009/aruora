"""
WS28 — structure-aware chunking (28 §7 step 5) and deterministic hashing
tokenizer utilities.

Chunking rules:
- heading boundaries take priority;
- paragraphs stay intact where possible;
- modest overlap at most;
- hard token cap per chunk;
- never merge unrelated sections just to fill a target size.
"""

from __future__ import annotations

import re

# Rough token estimate: words + punctuation clusters. Good enough for budget
# arithmetic; the embedding gateway counts what its provider actually reports.
_WORD_RE = re.compile(r"[A-Za-z0-9']+|[^\sA-Za-z0-9]")


def estimate_tokens(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def _split_headings(text: str) -> list[tuple[list[str], str]]:
    """Yield (heading_path, body) sections split on markdown-ish headings."""
    sections: list[tuple[list[str], str]] = []
    path: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            sections.append((list(path), "\n".join(buf).strip()))
            buf.clear()

    for line in (text or "").splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)$", line.strip())
        if m:
            flush()
            depth = len(m.group(1))
            title = m.group(2).strip()
            # maintain a heading stack: depth-1 slice
            path = path[: depth - 1]
            path.append(title)
        else:
            buf.append(line)
    flush()
    if not sections:
        sections.append(([], (text or "").strip()))
    return [(p, b) for p, b in sections if b]


_PARA_SPLIT = re.compile(r"\n\s*\n+")


def chunk_text(
    text: str,
    *,
    max_tokens: int = 220,
    overlap_tokens: int = 40,
) -> list[dict]:
    """
    Structure-aware chunker. Returns [{heading_path, text, token_count}].

    Oversized paragraphs are sliced with `overlap_tokens` of carry-over;
    heading metadata is preserved so retrieval can cite section context.
    """
    chunks: list[dict] = []
    for headings, body in _split_headings(text):
        paras = [p.strip() for p in _PARA_SPLIT.split(body) if p.strip()]
        cur: list[str] = []
        cur_tokens = 0

        def flush_cur():
            nonlocal cur, cur_tokens
            joined = "\n\n".join(cur).strip()
            if joined:
                chunks.append({
                    "heading_path": " > ".join(headings),
                    "text": joined,
                    "token_count": estimate_tokens(joined),
                })
            cur = []
            cur_tokens = 0

        for para in paras:
            ptok = estimate_tokens(para)
            if ptok > max_tokens:
                # hard-slice an oversized paragraph with overlap
                flush_cur()
                words = para.split()
                size = max(10, max_tokens * 3 // 4)   # ~word budget
                step = max(1, size - overlap_tokens)
                for i in range(0, len(words), step):
                    piece = " ".join(words[i:i + size])
                    chunks.append({
                        "heading_path": " > ".join(headings),
                        "text": piece,
                        "token_count": estimate_tokens(piece),
                    })
                    if i + size >= len(words):
                        break
                continue
            if cur_tokens + ptok > max_tokens and cur:
                flush_cur()
            cur.append(para)
            cur_tokens += ptok
        flush_cur()
    return chunks
