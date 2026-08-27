# 12 — Privacy, Data Protection, and Public-Product Compliance

## Goal
Define data handling before real users upload essays, transcripts, profile data, and voice recordings. This is an engineering checklist, not legal advice; final policies and jurisdictional applicability require legal review.

## Regulatory baseline
For an Indonesia-operated public service, review compliance with **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi**. The law covers controller/processor obligations, data-subject rights, transfers, security, and breach notification. Article 46 requires written breach notification no later than 3×24 hours to the data subject and institution under the law.

If offering services to people covered by EU GDPR, assess GDPR applicability separately; GDPR includes privacy-by-design/default and a 72-hour supervisory-authority breach notification rule where applicable.

## Task WS12-01 — Data inventory and classification
Maintain a living inventory:
| Data | Purpose | Sensitivity | Retention | Processor/vendor | Export? | Delete? |
|---|---|---|---|---|---|---|
| email/name | account | personal | account life + policy | mail/OIDC | yes | yes |
| essay | learning/scoring | personal content | user policy | LLM provider | yes | yes |
| transcript | learning/scoring | personal content | user policy | ASR/LLM | yes | yes |
| raw voice audio | ASR/pronunciation | high privacy impact | ephemeral by default | storage/worker | opt-in if retained | yes |
| score/metrics | progress | profile/learning | user policy | DB | yes | yes |
| security audit | fraud/security | restricted | defined security retention | logging | generally limited | policy-based |

Do not collect nationality, DOB, gender, ID documents, or other official-test identity data unless the product has a concrete need and legal basis. This is a practice platform, not the official test registration system.

## Task WS12-02 — Data minimization
- Send LLM provider only the content needed to perform the task.
- Do not send email/name/user ID alongside essays unless necessary.
- Do not retain raw audio by default after processing.
- Do not store request bodies in observability tools.
- Keep profile fields optional unless the feature requires them.
- Avoid collecting sensitive demographics merely for analytics.

## Task WS12-03 — Privacy notice
Before public signup, publish a clear notice covering:
- operator/contact;
- collected data;
- purposes/legal basis where applicable;
- AI/ASR providers and cross-border processing categories;
- retention periods/criteria;
- user rights;
- export/delete/correction procedures;
- security/breach contact;
- cookies/analytics;
- whether content is used for model improvement (default recommendation: no without separate consent).

## Task WS12-04 — Terms and AI disclaimer
Terms/product copy must state:
- independent preparation service;
- AI score is estimated/non-official;
- no guarantee of future test result/admission/visa outcome;
- availability limits;
- acceptable use/abuse;
- content rights/licensing for user-submitted material;
- prohibited submission of content the user has no right to upload where relevant.

## Task WS12-05 — IELTS trademark/copyright review
IELTS.org states that IELTS and its logos are protected trademarks and that protected website material is not available for commercial republication/use without permission.

Before monetized/public launch:
- do not use IELTS logo/official-looking visual identity without permission;
- audit product name/domain/app title so it does not imply ownership/endorsement;
- audit prompts/fixtures/screenshots for copied official descriptors/sample tests;
- obtain permission or replace protected material with licensed/original content;
- keep documented legal approval for final public naming/copy.

A technically accurate disclaimer does not automatically solve trademark confusion; branding itself needs review.

## Task WS12-05B — Logs, analytics, and AI payload minimization
Production observability must not silently become a second copy of learner content.

Policy:
- do not log raw essays, transcripts, audio, passwords, reset links, auth cookies, API keys, or full database URLs by default;
- use event IDs, user pseudonymous IDs, byte/word counts, model/version, duration, status, and error class for operational telemetry;
- treat replay/session-recording analytics as a separate privacy review, with sensitive input masking enabled before use;
- debug payload capture requires an explicit short-lived incident mode, restricted access, and automatic expiry/deletion;
- ensure error-reporting/LLM tracing vendors do not ingest learner payloads unless disclosed and contractually approved.

## Task WS12-06 — Data-subject requests
Product must support at minimum according to applicable law/policy:
- access/export;
- correction/profile update;
- deletion;
- consent withdrawal where consent is the basis;
- restriction/objection workflows where applicable.

Engineering requirements:
- authenticated request;
- identity re-check for sensitive operations;
- auditable request/completion;
- delete external blobs/provider-stored artifacts where controllable;
- defined SLA aligned with applicable law;
- no hidden orphan user data.

## Task WS12-07 — Audio and biometric caution
Voice recordings are highly identifying personal data. Processing speech for pronunciation does not necessarily mean the system is using “biometric data for unique identification”, but the legal classification depends on purpose/implementation/jurisdiction.

Default design:
- no speaker identification;
- no voiceprint templates;
- no cross-user voice matching;
- ephemeral raw audio;
- explicit opt-in for retained playback/training use;
- separate legal review before any biometric identity feature.

## Task WS12-08 — Children/minors
Indonesia’s PDP law treats child data as specific personal data. IELTS learners can include minors.

Before knowingly onboarding minors:
- determine age/consent rules for target jurisdictions;
- build age-appropriate privacy/parental consent flow if required;
- minimize profiling/analytics;
- avoid retaining voice recordings by default.

Lower-risk public-beta option: define and enforce an adult-only eligibility policy until the minor-data flow has been reviewed.

## Task WS12-09 — Vendor register / DPAs
Maintain vendor/subprocessor register for:
- hosting;
- managed PostgreSQL/Redis;
- object storage;
- email;
- observability;
- LLM router/model providers;
- analytics.

For each: data categories, region, retention, security terms, incident notification, deletion, training use, transfer basis where applicable, and DPA/contract status.

## Task WS12-10 — Breach response
Incident runbook must be capable of producing:
- what data was exposed;
- when/how;
- affected users/records estimate;
- containment/recovery steps;
- regulator/institution notification data;
- user communication.

Design internal escalation so a 3×24-hour Indonesia requirement or 72-hour GDPR requirement (when applicable) is operationally possible; do not wait until the last hour to begin legal assessment.

## Task WS12-11 — RAG source/privacy governance

Before activating a RAG source, record owner, provenance, trust tier, allowed use, copyright/license status, personal-data classification, update policy, and retention.

Do not place ordinary learner profile/history, essays, transcripts, audio, email, phone, or peer messages into a shared knowledge index. If a future private RAG feature is validated, require per-user/tenant namespaces, pre-retrieval ACL filtering, export/deletion of source artifacts and embeddings, and cross-tenant retrieval tests.

Public accessibility of a webpage is not sufficient evidence that its content may be copied into generated practice material.

## ARUORA product-specific privacy requirements

Classify and govern:
- destination/institution/country intent;
- exam/application deadlines;
- previous/self-reported score;
- cohort/acquisition source;
- Study Pool preferences;
- future peer relationships/reports/blocks;
- WhatsApp phone/consent/preferences;
- future tutor/human-help records.

Study Pool must be explicit opt-in, revocable, and must not automatically reveal email/phone/private learning artifacts.

Future peer/community launch requires code of conduct, report/block/leave controls, moderation workflow, and age/minor policy before live matching.

WhatsApp or other messaging consent must be channel-specific; account registration is not marketing/re-engagement consent.

## Exit criteria
There is a documented data inventory/retention policy, raw audio is minimized, export/delete is end-to-end, vendor AI processing is disclosed/reviewed, public branding/IP has approval or a safer rebrand, and incident response can meet applicable notification timelines.
