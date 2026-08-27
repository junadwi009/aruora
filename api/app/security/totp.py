"""WS03-07 — minimal RFC 6238 TOTP (stdlib only, no new dependency).

Used for optional mandatory MFA on admin accounts: when ADMIN_TOTP_SECRET is
configured (base32), admin logins and destructive-admin reauthentication must
present a valid code. Verification allows ±1 time-step of clock drift and
compares in constant time.
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import secrets
import time


def _b32(secret: str) -> bytes:
    pad = "=" * ((8 - len(secret.strip().replace(" ", "")) % 8) % 8)
    return base64.b32decode(secret.strip().replace(" ", "").upper() + pad, casefold=True)


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _code_at(secret: str, counter: int, digits: int = 6) -> str:
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(_b32(secret), msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct_int(digest, offset) & 0x7FFFFFFF) % (10 ** digits)
    return str(value).zfill(digits)


def struct_int(digest: bytes, offset: int) -> int:
    return int.from_bytes(digest[offset:offset + 4], "big")


def totp_verify(secret: str, code: str, *, period: int = 30, digits: int = 6,
                window: int = 1, at: float | None = None) -> bool:
    """True when `code` matches the TOTP at ±`window` steps of `at` (now)."""
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    if not (code.isdigit() and len(code) == digits):
        return False
    now = time.time() if at is None else at
    counter = int(now // period)
    ok = False
    for delta in range(-window, window + 1):
        expected = _code_at(secret, counter + delta, digits)
        if hmac.compare_digest(expected, code):
            ok = True
    return ok
