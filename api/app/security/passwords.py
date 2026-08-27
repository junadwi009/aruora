"""WS03-04 — password hashing and new-password policy.

Hashing: Argon2id when argon2-cffi is installed (the preferred modern slow
hash), transparently falling back to Werkzeug's scrypt otherwise. Legacy
Werkzeug hashes verify and are rehashed to the preferred backend on the next
successful login — no flag-day password reset.

Policy (NIST SP 800-63B style): length-based only for new passwords. No forced
composition rules, no periodic rotation; known/common passwords are blocked
against a small local list (privacy-preserving — nothing leaves the process).
"""
from __future__ import annotations

from werkzeug.security import check_password_hash

try:  # Preferred backend; requirements.txt pins argon2-cffi.
    from argon2 import PasswordHasher as _Argon2Hasher
    from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

    _ARGON2 = _Argon2Hasher(
        time_cost=3, memory_cost=64 * 1024, parallelism=4, hash_len=32, salt_len=16
    )
    HAVE_ARGON2 = True
except ImportError:  # pragma: no cover - exercised only without the dependency
    HAVE_ARGON2 = False

# Werkzeug hash prefixes ("scrypt:32768:8:1$salt$hash" / "pbkdf2:sha256:...").
_LEGACY_PREFIXES = ("scrypt:", "pbkdf2:")

MAX_PASSWORD_CHARS = 128

# Small local blocklist of the most commonly used/leaked passwords. This is a
# privacy-preserving local check (no external HIBP call in the request path).
_COMMON_PASSWORDS = frozenset({
    "123456", "password", "123456789", "12345678", "12345", "qwerty", "111111",
    "1234567", "dragon", "123123", "abc123", "football", "monkey", "letmein",
    "696969", "shadow", "master", "666666", "qwertyuiop", "123321", "mustang",
    "1234567890", "michael", "superman", "69696969", "admin", "welcome",
    "login", "password1", "passw0rd", "p@ssw0rd", "iloveyou", "trustno1",
    "sunshine", "princess", "admin123", "welcome1", "administrator",
    "password123", "qwerty123", "1q2w3e4r", "zaq12wsx", "letmein123",
    "changeme", "secret", "asdfgh", "zxcvbnm", "test123", "guest", "root",
    "toor", "pass123", "qazwsx", "starwars", "solo", "whatever", "freedom",
})


def hash_password(password: str) -> str:
    """Hash with the preferred backend (Argon2id, else Werkzeug scrypt)."""
    if HAVE_ARGON2:
        return _ARGON2.hash(password)
    from werkzeug.security import generate_password_hash

    return generate_password_hash(password)  # Werkzeug 3 defaults to scrypt


def verify_password(stored: str, password: str) -> bool:
    """Verify against any supported hash format. Never raises on bad input."""
    if not stored or not isinstance(stored, str):
        return False
    if stored.startswith("$argon2"):
        if not HAVE_ARGON2:  # pragma: no cover - mismatched environments
            return False
        try:
            _ARGON2.verify(stored, password)
            return True
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    if stored.startswith(_LEGACY_PREFIXES):
        try:
            return check_password_hash(stored, password)
        except (ValueError, TypeError):
            return False
    return False


def needs_rehash(stored: str) -> bool:
    """True when `stored` should be upgraded to the preferred backend."""
    if not stored:
        return False
    if stored.startswith("$argon2"):
        if not HAVE_ARGON2:  # pragma: no cover
            return False
        try:
            return _ARGON2.check_needs_rehash(stored)
        except (InvalidHashError, ValueError):
            return True
    # Any non-argon2 hash we can verify is a legacy hash worth upgrading.
    return True


def validate_new_password(password: str, *, min_chars: int = 15, context: str = "") -> list[str]:
    """Return a list of policy problems ([] = acceptable).

    NIST-aligned: length + blocklist only. Spaces and Unicode are allowed; no
    arbitrary composition rules; max length guards against DoS-sized inputs.
    """
    problems: list[str] = []
    pw = password or ""
    if len(pw) < min_chars:
        problems.append(f"Password must be at least {min_chars} characters")
    if len(pw) > MAX_PASSWORD_CHARS:
        problems.append(f"Password must be at most {MAX_PASSWORD_CHARS} characters")
    probe = pw.strip().lower()
    if probe in _COMMON_PASSWORDS:
        problems.append("This password is too common — choose something more unique")
    ctx = (context or "").strip().lower()
    local_part = ctx.split("@")[0] if ctx else ""
    if len(local_part) > 3 and local_part in probe:
        problems.append("Password must not contain your email name")
    return problems
