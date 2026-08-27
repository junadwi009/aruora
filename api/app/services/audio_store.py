"""WS06-02/07 — ephemeral private audio store.

Raw learner audio is written to a private, non-served directory keyed by an
unguessable token. There is deliberately NO URL/interface to read audio over
HTTP: only the ASR worker touches the file, and it deletes it when done
(retention policy, WS06-07). Stale files (crashed worker, failed upload) are
purged by TTL on the next save.

Contract:
- ``save(bytes) -> key``           — persists audio, returns the opaque key
- ``path(key) -> Path``            — worker-side filesystem path (no URL)
- ``delete(key)``                  — immediate removal after processing
- ``purge_expired()``              — remove files older than the TTL
- ``read(key) -> bytes | None``    — worker read; missing/expired → None
"""
from __future__ import annotations

import os
import secrets
import time
from pathlib import Path


class AudioStore:
    def __init__(self, base_dir: str, ttl_min: int = 30) -> None:
        self._dir = Path(base_dir)
        self._ttl_s = max(1, int(ttl_min) * 60)

    def _ensure_dir(self) -> Path:
        # Created lazily and idempotently; 0o700 keeps it private to the
        # service account (worker and api share it only when on one host).
        self._dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        return self._dir

    def _path_for(self, key: str) -> Path:
        return self._dir / key

    def save(self, audio_bytes: bytes) -> str:
        """Persist raw audio under an unguessable key (no user data in it)."""
        self.purge_expired()
        d = self._ensure_dir()
        key = secrets.token_urlsafe(24)
        tmp = d / (key + ".part")
        tmp.write_bytes(audio_bytes)
        os.replace(tmp, d / key)  # atomic publish; never a half-written object
        return key

    def path(self, key: str) -> Path | None:
        if not key or "/" in key or "\\" in key or ".." in key:
            return None  # the key is a token, never a path segment
        p = self._path_for(key)
        if not p.exists():
            return None
        if time.time() - p.stat().st_mtime > self._ttl_s:
            return None  # expired: treat as absent, janitor removes it later
        return p

    def read(self, key: str) -> bytes | None:
        p = self.path(key)
        if p is None:
            return None
        try:
            return p.read_bytes()
        except OSError:
            return None

    def delete(self, key: str) -> None:
        if not key or "/" in key or "\\" in key or ".." in key:
            return
        p = self._path_for(key)
        try:
            p.unlink(missing_ok=True)
        except OSError:  # best effort; purge_expired is the backstop
            pass

    def purge_expired(self) -> int:
        """Best-effort janitor: returns how many stale objects were removed."""
        try:
            files = [p for p in self._dir.iterdir() if p.is_file()]
        except (FileNotFoundError, NotADirectoryError):
            return 0
        now = time.time()
        removed = 0
        for p in files:
            try:
                if now - p.stat().st_mtime > self._ttl_s:
                    p.unlink()
                    removed += 1
            except OSError:
                continue
        return removed


def store_for_config(cfg) -> AudioStore:
    """The process-wide ephemeral store for learner audio (WS06-07 defaults)."""
    return AudioStore(getattr(cfg, "ASR_AUDIO_DIR", "data/audio_tmp"),
                      ttl_min=int(getattr(cfg, "ASR_AUDIO_TTL_MIN", 30)))
