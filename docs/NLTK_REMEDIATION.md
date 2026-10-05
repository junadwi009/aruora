# NLTK runtime removal — metric-preserving remediation

## What is closed, and what is not

The application no longer installs NLTK, TextBlob, textstat or LexicalRichness in
its production dependency graph. The affected NLTK model-file APIs are absent;
this is dependency removal, not an assertion that upstream NLTK is patched and
not an advisory exception. `pip-audit --strict` remains fail-closed.

The replacement covers ONLY the English readability/TTR/MTLD functions actually
used by ARUORA. Their algorithm and data semantics are preserved, including the
original default tokenization, apostrophes/dashes, CMU first pronunciation,
easy-word exclusions, operation order, MTLD threshold, bidirectional mean and
final rounding. It is not a general substitute for the libraries' full APIs.
The MIT-derived subset and data notices are in
`api/app/services/METRIC_THIRD_PARTY_NOTICES.txt`.

The syntax pipeline remains spaCy 3.8.13 + en_core_web_sm 3.8.0 +
TextDescriptives 2.8.2. Judge models, rubric/prompt code, normalization and
scoring orchestration were not changed by this remediation. Identical
preprocessing does not guarantee identical stochastic provider responses or
establish a new IELTS calibration claim.

## Immutable data, not executable models

Profile: `english-textstat-0.7.13-lexicalrichness-0.5.1-cmu06-pyphen-0.18.1`.

The CMU 0.6 dictionary is pinned to nltk_data commit
`550b6625bcef1f2abff2ff770a5a0d272c9c6b2a`; ZIP SHA-256 is
`d07cca47fd72ad32ea9d8ad1219f85301eeaf4568f8b6b73747506a71fb5afd6`.
Its 123,455 first-pronunciation entries match the reference dictionary exactly.
The 2,941-word English easy-word list is read from a SHA-256-pinned textstat
wheel as DATA only. The wheel is never installed or executed in production.
Only fixed named archive entries are read with size limits; no general archive
extraction, pickle/model deserialization, or caller-selected path is introduced.
Pyphen 0.18.1 is pinned to preserve out-of-dictionary fallback behavior.

Build/development preparation is explicit:

```sh
pip install -r api/requirements.txt
python api/app/services/metric_resources.py --prepare
python api/app/services/metric_resources.py --check
```

The Dockerfile performs preparation at image build time. Requests never fetch
corpora. Missing/tampered resources fail scoring instead of quietly replacing
valid metrics with zeros. Generated data is ignored by Git and the Docker build
context; a local cache cannot overwrite the image's verified data.

## Differential acceptance

`.github/workflows/metric-compatibility.yml` compares the replacement with
`essay_metrics.py` frozen at `e392189d67096d0cf90a78e3405ede9e4f307ebc`.
Baseline source SHA-256:
`a04fbbdf9ed2482faa1cde430f6c91f69da5607742134a7b51e725eb6b66dc9b`.

The reference libraries run only in a disposable test process with synthetic
strings and frozen dictionary data. Their model import/export APIs are not
exercised. No provider credential, real account or learner document is supplied.
The reference-only libraries are then uninstalled; `pip check`, import absence
and the production metric tests must pass. No vulnerable distribution is copied
into an application image, and no advisory is ignored by the security workflow.

Acceptance requires exact equality of all returned fields on **309** synthetic
samples, including short text, punctuation, apostrophes, Unicode, numbers,
unknown words, repeated text, MTLD boundaries and near-limit essays. Both syntax
outputs must be populated; tests must not pass by silently degrading both sides.
All **123,455** dictionary entries are compared, not only words in that corpus.
Initial and subsequent compatibility runs passed with **zero mismatches**.
The aggregate report is an Actions artifact; the current commit's precise
workflow results belong in the PR handoff, not an unverified evergreen badge.

Changing this profile, resource hashes, formula/tokenization code or syntax
model requires rerunning the differential pack and assessing calibration impact.
Do not update the profile to a newer dictionary merely because it is available.

## Production image acceptance

`Production image smoke` builds the complete API (including spaCy and Whisper
base models) and nginx frontend images. An offline container must compute
nonzero metrics, retain syntax, load Whisper locally, and prove NLTK is absent.
A disposable localhost TLS edge starts the production Compose topology and
exercises real account cookies/CSRF, owner isolation, queued Writing/Speaking,
idempotency, restart persistence, desktop/mobile browser submission, and a
synthetic database restore into a separate database. The browser test has no
API route mocks; inference itself is explicitly the offline stub.

This is stronger than build-only or mocked browser testing, but is NOT a
persistent staging deployment, a public-certificate audit, real mail/Google
sign-in, paid-provider calibration, load testing, or a full OS-image CVE scan.
Do not infer those outcomes from a green image-smoke workflow.

## Additional defect caught by full-stack testing

General API traffic formerly shared rate-limit counter keys with registration
and login. The image test reproduced a 429 on a legitimate second registration.
Counters now include a finite, server-selected policy prefix while retaining
IP/email/user dimensions, shared Redis enforcement and existing limits.
Tests cover isolation, retained denial, multiple service instances and failures
in escalation/check/TTL operations. No throttling was disabled to pass the smoke.

The subsequent screenshot review found that the fixed-height React root let the
legal footer overlap the longer authentication document. Only public/auth roots
now use intrinsic height; workspace scrolling remains viewport-bound. Browser
assertions require the legal footer to follow the entire auth layout and retain
its links, in both desktop and mobile image tests.

Primary sources inspected for this remediation:
- https://github.com/nltk/nltk/security/advisories/GHSA-8mgp-746c-j5xp
- https://github.com/textstat/textstat/tree/0.7.13
- https://github.com/LSYS/LexicalRichness/tree/v0.5.1
- https://github.com/nltk/nltk_data/blob/550b6625bcef1f2abff2ff770a5a0d272c9c6b2a/index.xml
