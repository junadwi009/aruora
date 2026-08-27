"""WS07 — job infrastructure package.

Layers:
  - ``service.JobService``  job records, idempotency, backpressure (WS07-03/05/07)
  - ``handlers``            per-type handlers + retry policy (WS07-06/10)
  - ``celery_app``          queue split + worker bootstrap (WS07-04)

Queue split (WS07-04): ``asr`` (low concurrency), ``llm_score``,
``llm_generate`` (replenishment), ``mail`` — deployed as separate worker
processes so heavy queues never share all slots with critical security mail.
"""
