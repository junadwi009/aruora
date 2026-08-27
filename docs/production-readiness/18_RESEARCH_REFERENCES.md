# 18 — Research References

Research date: **2026-08-21**. Prefer these primary/official sources. Re-verify live provider/library policies at implementation/release time because some operational guidance changes.

## IELTS scoring and claims
1. IELTS — Understanding IELTS test scores / overall band rounding  
   https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail  
   Key use: official examples include average 6.25 → band 6.5 and rule that `.25` rounds to the next half and `.75` to the next whole.

2. IELTS — IELTS Speaking Key Assessment Criteria  
   https://ielts.org/cdn/ielts-guides/ielts-speaking-key-assessment-criteria.pdf  
   Key use: four criteria include Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, and Pronunciation; pronunciation includes audio/phonological evidence.

3. IELTS — IELTS and the CEFR  
   https://ielts.org/organisations/ielts-for-organisations/compare-ielts/ielts-and-the-cefr  
   Key use: IELTS and CEFR are not one-to-one equivalents; C1 boundary around 6.5/7 is explicitly nuanced.

4. IELTS — Copyright and trade mark statement  
   https://ielts.org/legal/ielts-copyright-and-trade-mark-statement  
   Key use: IELTS trademarks/logos are protected; website material has commercial reuse restrictions and permission requirements.

## AI scoring validity/security
5. OWASP GenAI Security Project — **LLM Top 10 2026** (published 2026-08-03)  
   https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/  
   Key use: current GenAI/LLM application risk baseline, including Prompt Injection, Sensitive Information Disclosure, Excessive Agency, Supply Chain, Data/Model Poisoning, Unbounded Consumption, Misinformation, Hidden Context Exposure, Vector/Embedding Weaknesses, and Improper Output Handling.

6. OWASP GenAI — LLM Top 10 2026 guide/download  
   https://genai.owasp.org/download/56791/  
   Key use: 2026 control/attack guidance. In the 2026 ranking, Prompt Injection remains LLM01, Unbounded Consumption is LLM06, and Improper Output Handling is LLM10.

7. OWASP GenAI — Prompt Injection background page  
   https://genai.owasp.org/llmrisk/llm01-prompt-injection/  
   Key use: user-controlled instructions can alter model behavior; prompt separation is necessary but not a complete mitigation, so application-layer authorization/output validation remains mandatory.

8. Mizumoto/related authors, Computers and Education: Artificial Intelligence (2024) — “Large language models and automated essay scoring of English language learner writing: Insights into validity and reliability”  
   https://www.sciencedirect.com/science/article/pii/S2666920X24000353  
   Key use: some strong LLMs show useful AES validity/reliability, but performance varies by model/time and requires empirical validation.

9. Kim (2025), TESOL Quarterly — “Automated Essay Scoring With GPT-4 for a Local Placement Test…”  
   https://onlinelibrary.wiley.com/doi/10.1002/tesq.3405

## Web/API/application security
10. OWASP API Security Top 10 — 2023  
    https://owasp.org/API-Security/editions/2023/en/0x11-t10/  
    Key use: Broken Object Level Authorization, Broken Authentication, Unrestricted Resource Consumption, Function Level Authorization, etc.

11. OWASP API4:2023 — Unrestricted Resource Consumption  
    https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/

12. OWASP Session Management Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html  
    Key use: server-side invalidation, session renewal after privilege changes, idle/absolute expiry, cookie security, no tokens in logs.

13. OWASP CSRF Prevention Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html  
    Key use: SameSite is defense-in-depth; stateful apps should use a deliberate CSRF strategy.

14. OWASP Password Storage Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html  
    Key use: Argon2id preferred; adaptive slow hashing.

15. OWASP Forgot Password Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html  
    Key use: cryptographically random reset tokens must be single-use and expire.

16. OWASP Logging Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html  
    Key use: exclude/mask tokens, passwords, DB strings, keys, sensitive PII.

17. OWASP HTTP Security Response Headers Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html

18. OWASP Content Security Policy Cheat Sheet  
    https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html

19. NIST SP 800-63B (current 800-63-4 publication site)  
    https://pages.nist.gov/800-63-4/sp800-63b.html  
    Key use: password length, blocklists, no arbitrary composition/periodic rotation, rate limiting, secure storage.

## Flask/Gunicorn/runtime
20. Flask — Deploying to Production  
    https://flask.palletsprojects.com/en/stable/deploying/

21. Flask — Security Considerations / Trusted Hosts  
    https://flask.palletsprojects.com/en/stable/web-security/

22. Flask — Tell Flask it is Behind a Proxy / ProxyFix  
    https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/

23. Gunicorn — Design  
    https://docs.gunicorn.org/en/stable/design.html  
    Key use: sync worker handles one request at a time; long blocking external calls motivate other worker/workload designs and buffering proxy.

## PostgreSQL / containers
24. Docker Official Image — postgres  
    https://hub.docker.com/_/postgres  
    Key use: PostgreSQL 18+ changes version-specific `PGDATA` and the volume target to `/var/lib/postgresql`.

25. PostgreSQL 18 — Continuous Archiving and Point-in-Time Recovery (PITR)  
    https://www.postgresql.org/docs/18/continuous-archiving.html  
    Key use: WAL archiving/base backups and point-in-time recovery design.

26. PostgreSQL 18 — SQL Dump / backup documentation  
    https://www.postgresql.org/docs/18/backup-dump.html  
    Key use: understand logical dump scope/limitations; production recovery strategy should match workload/RPO/RTO.

## Observability
27. OpenTelemetry Python — Getting Started  
    https://opentelemetry.io/docs/languages/python/getting-started/  
    Key use: vendor-neutral traces/metrics instrumentation baseline.

28. OpenTelemetry Python — Instrumentation  
    https://opentelemetry.io/docs/languages/python/instrumentation/  
    Key use: context propagation and instrumentation design across Flask/workers.

## CI/supply chain
29. GitHub Docs — Artifact attestations  
    https://docs.github.com/en/actions/concepts/security/artifact-attestations  
    Key use: build provenance, SBOM association, SLSA-oriented assurance.

30. GitHub Docs — Quickstart for securing your repository  
    https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository  
    Key use: CodeQL and Secret Protection features for repository security.

## Privacy / legal
31. Indonesia — UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi  
    https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022  
    Key use: controller/processor duties, subject rights, security, transfers, and data protection framework.

32. Official law PDF — Article 46 breach notification  
    https://peraturan.bpk.go.id/Download/224884/UU%20Nomor%2027%20Tahun%202022.pdf  
    Key use: written notification no later than 3×24 hours under Article 46.

33. EU GDPR — EUR-Lex Regulation (EU) 2016/679  
    https://eur-lex.europa.eu/eli/reg/2016/679/oj  
    Key use if applicable: privacy by design/default and breach-notification obligations.

## Accessibility
34. W3C — WCAG 2.2  
    https://www.w3.org/TR/WCAG22/  
    Key use: current W3C accessibility Recommendation.

35. W3C — WCAG 2 Level AA Conformance  
    https://www.w3.org/WAI/WCAG2AA-Conformance

## Research caveats
- Security standards define controls but do not replace threat modeling for this codebase.
- Automated essay/speaking scoring research does not validate this application’s chosen provider/model/prompt. The repository needs its own licensed/consented evaluation set.
- LLM provider retention/routing terms, package versions, vulnerability advisories, and cloud service capabilities must be rechecked immediately before implementation/release.
- This pack does not provide legal advice; trademark/data-protection obligations require counsel or qualified review for the jurisdictions actually served.

## Supplied ARUORA source packs

This v2 program also incorporates the user-supplied packs dated 2026-08-21, preserved under:
- `docs/brand-source/`
- `docs/product-strategy-source/`

The market strategy pack labels evidence as VERIFIED / COMMUNITY SIGNAL / HYPOTHESIS / DECISION. Preserve those distinctions when implementing or publishing claims.

Time-sensitive external facts in the strategy pack—such as WhatsApp pricing, IELTS policy/test fees, scholarship rules, visa/immigration rules, or provider features—must be re-verified from current primary sources before implementation or public copy is frozen.

Do not convert market hypotheses or working UAT thresholds into “industry benchmark” claims.

## AI usage accounting and caching — 2026-08 research

36. OpenRouter Docs — Usage Accounting  
    https://openrouter.ai/docs/cookbook/administration/usage-accounting  
    Key use: provider responses expose detailed usage including prompt/completion tokens, cost, reasoning tokens where applicable, and cached-token details. The docs currently state older `usage: {include: true}` flags are deprecated because full usage is returned automatically.

37. OpenRouter Docs — Prompt Caching  
    https://openrouter.ai/docs/guides/best-practices/prompt-caching  
    Key use: stable prompt prefixes can receive provider-specific cache benefits; cache-write/read economics and model support differ by provider/model.

38. OpenRouter Docs — Response Caching (Beta)  
    https://openrouter.ai/docs/guides/features/response-caching  
    Key use: identical full requests can be replayed from OpenRouter cache with zero billable usage on hits; this is beta, is not suitable when a fresh/different task is required, and is disabled when account-level ZDR is enforced.

39. OpenRouter Docs — Zero Data Retention  
    https://openrouter.ai/docs/guides/features/zdr  
    Key use: ZDR routing and caching/privacy boundaries. Re-check before release because provider policies change.

40. OpenRouter — Providers / data practices  
    https://openrouter.ai/providers  
    Key use: upstream providers have different retention/training practices; privacy-safe routing must be explicit rather than assumed from the router alone.


## Auto-RAG / retrieval architecture — 2026-08 research

Research refreshed 2026-08-21. Re-verify implementation details before shipping.

- pgvector — vector similarity search for PostgreSQL, exact search, HNSW/IVFFlat, metadata filtering, hybrid search with PostgreSQL full-text search, and RRF/cross-encoder examples: https://github.com/pgvector/pgvector
- Microsoft Azure AI Search — current RAG guidance describes classic hybrid keyword+vector retrieval with semantic ranking, plus agentic retrieval for more complex query planning: https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview
- Microsoft Azure AI Search — hybrid search combines text and vector retrieval and merges results using Reciprocal Rank Fusion: https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview
- AWS Bedrock Knowledge Bases — retrieval supports metadata filtering and reranking; current documentation warns that guardrails on model input/output do not automatically apply to retrieved references: https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-retrieve.html
- OWASP GenAI — current vector/embedding guidance treats retrieval/vector infrastructure as a trust boundary with poisoning, leakage/access-control and retrieval risks: https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/ and current 2026 Top 10 publication.
- OWASP GenAI Prompt Injection — RAG does not fully mitigate prompt injection: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- Ragas — retrieval evaluation concepts include Context Precision, Context Recall, and Faithfulness; useful as conceptual metrics even if ARUORA implements its own harness: https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
