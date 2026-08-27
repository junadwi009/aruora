# 03 — Identity, Session, and Account Security

## Goal
Replace self-host-friendly account/session assumptions with controls suitable for untrusted internet traffic and multiple users.

## Dependencies
Run after the ownership/cascade model in `04_MULTI_USER_DATA_ISOLATION.md` is stable enough to avoid conflicting identity migrations.

## WS03 ownership
Expected areas:
- `api/app/routes/account.py`
- `api/app/routes/auth.py`
- `api/app/session.py`
- `api/app/config.py`
- account/session models + dedicated migrations
- account/security tests
- frontend auth client/screens only as required by API contract changes

## Task WS03-01 — Move authenticated sessions server-side
The reviewed app uses Flask signed-cookie sessions. Signed cookies protect integrity but do not provide straightforward central revocation.

Target:
- browser stores only an opaque session identifier in an `HttpOnly`, `Secure`, `SameSite` cookie;
- session state lives in Redis or another shared server-side store;
- logout invalidates server state;
- password change/reset, privilege change, suspicious activity, and “logout all devices” can revoke sessions;
- idle and absolute expiry are enforced server-side.

Store only necessary session data: user ID, role/privilege snapshot, issued time, last activity, CSRF/session nonce, and optional device metadata. Do not put password hashes, OAuth tokens, or learner content in session state.

## Task WS03-02 — Rotate session identity at authentication boundaries
Regenerate/replace the session identifier after:
- successful local login;
- successful Google/OIDC login;
- password reset;
- privilege/admin elevation;
- security-sensitive account recovery.

Old identifiers must become invalid.

## Task WS03-03 — CSRF protection
Cookie authentication means browsers attach credentials automatically. `SameSite=Lax` is defense-in-depth, not the sole production control.

Implement one consistent state-changing API policy:
- synchronizer token or signed double-submit/cookie-to-header pattern; and/or
- strict custom header + Fetch Metadata/Origin validation appropriate to the same-origin SPA.

Requirements:
- all `POST`, `PUT`, `PATCH`, `DELETE` authenticated browser requests are protected;
- no state change via `GET`;
- login/account recovery flows are covered where applicable;
- reject unexpected cross-site requests;
- tests explicitly prove forged requests fail.

## Task WS03-04 — Password policy and storage
For password-only accounts, align new-password UX with modern NIST guidance:
- minimum 15 characters for single-factor password authentication unless a reviewed product decision adopts MFA-backed shorter minimums;
- allow at least 64 characters;
- allow spaces and Unicode;
- no arbitrary “uppercase + symbol + digit” composition rule;
- no periodic forced rotation absent compromise;
- block known/common/compromised passwords using a privacy-preserving/local mechanism;
- rate-limit failed attempts.

Password storage target: explicit modern slow password hashing. Prefer Argon2id with parameters benchmarked for the production CPU budget; support transparent rehash on successful login so existing hashes migrate safely.

Do not perform a flag-day password reset solely to change hashing algorithm.

## Task WS03-05 — Email verification
Before a new local account can use expensive/persistent production features:
- verify ownership of the email address;
- use a single-use expiring verification token;
- rate-limit resend;
- generic responses must not become an enumeration oracle.

Google accounts may treat a provider-verified email as verified only after issuer/audience/signature/expiry verification and the provider’s `email_verified` claim.

## Task WS03-06 — Password reset redesign
Current reset design must become stateful enough for one-time use.

Target reset record:
- random token generated cryptographically;
- only a token hash stored server-side;
- bound to user;
- `expires_at`;
- `used_at`/revocation state;
- request metadata sufficient for security audit, without logging the token;
- successful use revokes all reset tokens for that user and optionally all active sessions.

Forgot-password response remains generic regardless of account existence.

## Task WS03-06B — Production email/account-recovery safety
The reviewed mailer intentionally logs the complete email body when SMTP is absent in development. That body may contain password-reset or verification links. This behavior must never become a production fallback.

Production requirements:
- account-recovery/verification email delivery is configured through an approved provider or the feature is explicitly disabled;
- production startup/readiness fails when email-dependent account flows are enabled but mail configuration is missing;
- never log reset/verification URLs, token query parameters, magic links, authorization codes, or email bodies containing them;
- log only delivery metadata such as provider message ID, template ID, outcome, latency, and a privacy-safe recipient reference;
- provider/webhook failures must not echo secrets/tokens;
- bounce/complaint handling should suppress repeated delivery where applicable;
- recovery emails should have short-lived links, HTTPS origins, and an allow-listed canonical application base URL rather than trusting request Host headers.

Add a production-mode test proving that an unavailable email provider does not expose a reset token in logs.

## Task WS03-07 — Admin security
Administrative surfaces are higher risk than ordinary user functions.

Before public launch:
- explicit RBAC/role table or equivalent normalized policy; do not rely only on an environment email list long-term;
- mandatory MFA/passkey/TOTP for admin accounts before GA;
- reauthentication for destructive admin actions;
- audit log for user deletion, role change, password reset actions, and admin login;
- admin UI/API must use the same CSRF/session protections.

For public beta, an environment allow-list may temporarily remain only if the release gate documents the residual risk and admin access is strongly protected.

## Task WS03-08 — Authentication abuse controls
Redis-backed controls keyed by both account identifier and client/network signal:
- login failure throttle;
- registration throttle;
- forgot/reset throttle;
- email verification resend throttle;
- Google/OIDC failure throttle.

Avoid permanent attacker-triggered account lockout. Prefer progressive delay/risk response.

## Task WS03-09 — Session management UX
Add:
- current session information;
- “log out all devices”;
- clear behavior when idle/absolute timeout occurs;
- no frontend `fail open` behavior that makes an auth outage look like an unlocked app. Backend authorization remains authoritative, but the UI should show an outage/sign-in failure rather than proceeding optimistically.

## ARUORA profile/status boundaries

`Founding Learner`, `Verified Achiever`, `Peer Mentor`, and future tutor labels are product/community statuses, not authentication roles unless explicitly mapped through a reviewed authorization model.

Do not use a badge string to grant admin/tutor capabilities.

Progressive profile fields such as destination, deadline, target band, acquisition source, and peer opt-in must be changeable without changing the account's security identity.

Future WhatsApp phone ownership/consent must remain separate from login authentication unless a dedicated verified-phone auth flow is deliberately added.

## Security tests
Must include:
- session identifier changes after login;
- revoked session fails on next protected request;
- logout invalidates server state;
- password reset token cannot be reused;
- password reset revokes old sessions according to policy;
- CSRF missing/invalid/cross-origin request rejected;
- generic forgot response for existent/non-existent users;
- user cannot self-assign admin role;
- Google token wrong audience/issuer/expired/unverified email rejected;
- brute-force controls work across two app processes against shared Redis.

## Exit criteria
No public authenticated request depends on an irrevocable client-only session, all unsafe browser methods have CSRF protection, reset tokens are single-use, and administrative access has a documented stronger assurance level.
