"""
WS02-05 — Calibration harness contract.

A FROZEN calibration dataset format plus the promotion metrics that gate any
model/prompt/rubric change. No model or prompt update may reach production
solely because qualitative examples "look better".

Dataset format (one JSON object per sample, file = list of records):

    {
      "sample_id": "anon-001",
      "skill": "writing",                       # writing | speaking
      "task_type": "task2",                     # task1 | task2 | part1 | part2 | part3
      "prompt_license": "internal-or-permitted",# internal-or-permitted | original | licensed
      "response": "<learner response text>",
      "human_scores": [{"rater": "R1", "overall": 6.5}],
      "adjudicated_score": 6.5                  # consensus reference band
    }

Rules:
- Only ANONYMISED, internal-or-licensed material may enter a calibration set.
  Never commit official/copyrighted test content or private user data.
- The set is frozen: contents and ordering must not change between candidate
  evaluation runs; version it via ``CALIBRATION_SET_VERSION``.

Promotion metrics (all required for any judge-model/prompt promotion):
- exact-band agreement
- within-0.5 agreement
- mean absolute error (MAE)
- quadratic-weighted kappa (ordinal agreement)
- repeated-run stability (max per-sample spread across repeat runs)

FROZEN PROMOTION GATES — CALIBRATION_GATES below. Changing a gate value is a
product decision requiring documented sign-off in the release notes.
"""

from __future__ import annotations

import math
from statistics import mean as _mean
from statistics import pstdev

# Bump when adding/removing samples after documented review (never silently).
CALIBRATION_SET_VERSION = "cal-v1"

REQUIRED_KEYS = {
    "sample_id",
    "skill",
    "task_type",
    "prompt_license",
    "response",
    "human_scores",
    "adjudicated_score",
}
ALLOWED_SKILLS = {"writing", "speaking"}
ALLOWED_LICENSES = {"internal-or-permitted", "original", "licensed"}

# Frozen promotion gates (see module docstring). Do NOT tune per-release.
CALIBRATION_GATES: dict[str, float] = {
    "exact_agreement_min": 0.45,
    "within_half_agreement_min": 0.85,
    "mae_max": 0.50,
    "qwk_min": 0.70,
    "repeat_stability_max_spread": 1.0,  # max band spread on any one sample
}

_VALID_BANDS = [3.0 + 0.5 * i for i in range(13)]  # 3.0 .. 9.0


def validate_record(rec: dict) -> None:
    """Raise ValueError if *rec* violates the frozen sample format."""
    missing = REQUIRED_KEYS - set(rec)
    if missing:
        raise ValueError(f"sample {rec.get('sample_id', '?')}: missing keys {sorted(missing)}")
    if rec["skill"] not in ALLOWED_SKILLS:
        raise ValueError(f"sample {rec['sample_id']}: bad skill {rec['skill']!r}")
    if rec["prompt_license"] not in ALLOWED_LICENSES:
        raise ValueError(
            f"sample {rec['sample_id']}: prompt_license must be one of "
            f"{sorted(ALLOWED_LICENSES)}"
        )
    hs = rec["human_scores"]
    if not isinstance(hs, list) or len(hs) == 0:
        raise ValueError(f"sample {rec['sample_id']}: human_scores must be a non-empty list")
    for h in hs:
        if not isinstance(h, dict) or "rater" not in h or "overall" not in h:
            raise ValueError(f"sample {rec['sample_id']}: each human_scores item needs rater+overall")
    adj = rec["adjudicated_score"]
    if not isinstance(adj, (int, float)) or adj < 3.0 or adj > 9.0:
        raise ValueError(f"sample {rec['sample_id']}: adjudicated_score out of 3.0-9.0")
    if not isinstance(rec["response"], str) or not rec["response"].strip():
        raise ValueError(f"sample {rec['sample_id']}: response must be non-empty text")


def validate_dataset(records: list[dict]) -> list[dict]:
    """Validate every record; return them unchanged (fail fast otherwise)."""
    seen: set[str] = set()
    for rec in records:
        validate_record(rec)
        sid = rec["sample_id"]
        if sid in seen:
            raise ValueError(f"duplicate sample_id {sid!r}")
        seen.add(sid)
    return records


def _quantize_band(x: float) -> float:
    """Snap a predicted score to the nearest legal half-band (ties UP)."""
    snapped = round(x * 2) / 2
    return min(max(snapped, 3.0), 9.0)


# ---------------------------------------------------------------------------
# Pairwise metrics — preds/refs are parallel sequences of numeric bands
# ---------------------------------------------------------------------------

def exact_band_agreement(preds: list[float], refs: list[float]) -> float:
    """Fraction of samples where the rounded prediction equals the reference."""
    hits = sum(1 for p, r in zip(preds, refs) if _quantize_band(p) == r)
    return hits / len(refs) if refs else 0.0


def within_half_band_agreement(preds: list[float], refs: list[float]) -> float:
    """Fraction of samples within 0.5 band of the reference."""
    hits = sum(1 for p, r in zip(preds, refs) if abs(_quantize_band(p) - r) <= 0.5 + 1e-9)
    return hits / len(refs) if refs else 0.0


def mean_absolute_error(preds: list[float], refs: list[float]) -> float:
    return _mean(abs(p - r) for p, r in zip(preds, refs)) if refs else 0.0


def quadratic_weighted_kappa(preds: list[float], refs: list[float]) -> float:
    """
    Quadratic-weighted Cohen's kappa over the 13 legal half-bands (3.0–9.0).

    Justified ordinal-agreement metric per WS02-05; implemented locally so no
    heavyweight dependency is needed at eval time.
    """
    n_levels = len(_VALID_BANDS)
    idx_of = {b: i for i, b in enumerate(_VALID_BANDS)}
    n = len(refs)
    if n == 0:
        return 0.0

    obs = [[0.0] * n_levels for _ in range(n_levels)]
    for p, r in zip(preds, refs):
        try:
            i, j = idx_of[_quantize_band(p)], idx_of[r]
        except KeyError:
            raise ValueError(f"reference band out of range: {p!r}/{r!r}")
        obs[i][j] += 1.0
    row = [sum(rowi) for rowi in obs]
    col = [sum(obs[i][j] for i in range(n_levels)) for j in range(n_levels)]

    w = [[(i - j) ** 2 / (n_levels - 1) ** 2 for j in range(n_levels)]
         for i in range(n_levels)]

    expected = [[row[i] * col[j] / n for j in range(n_levels)] for i in range(n_levels)]
    num = sum(w[i][j] * obs[i][j] for i in range(n_levels) for j in range(n_levels))
    den = sum(w[i][j] * expected[i][j] for i in range(n_levels) for j in range(n_levels))
    if math.isclose(den, 0.0):
        return 1.0 if math.isclose(num, 0.0) else 0.0
    return 1.0 - num / den


def repeated_run_stability(runs: list[list[float]]) -> float:
    """
    Max per-sample band spread across repeated runs of the SAME samples.

    ``runs[k][i]`` is the k-th run's prediction for sample i. Returns the
    largest (max-min) spread observed on any single sample.
    """
    if not runs:
        return 0.0
    length = min(len(r) for r in runs)
    worst = 0.0
    for i in range(length):
        vals = [_quantize_band(r[i]) for r in runs]
        worst = max(worst, max(vals) - min(vals))
    return worst


def evaluate_run(preds: list[float], refs: list[float]) -> dict:
    """Compute the promotion-gate snapshot for one candidate run."""
    return {
        "n": len(refs),
        "exact_agreement": round(exact_band_agreement(preds, refs), 4),
        "within_half_agreement": round(within_half_band_agreement(preds, refs), 4),
        "mae": round(mean_absolute_error(preds, refs), 4),
        "qwk": round(quadratic_weighted_kappa(preds, refs), 4),
    }


def gates_pass(evaluation: dict, stability_spread: float) -> tuple[bool, list[str]]:
    """Return (all_gates_pass, failing_gate_names) for a promotion decision."""
    failures: list[str] = []
    g = CALIBRATION_GATES
    if evaluation.get("exact_agreement", 0.0) < g["exact_agreement_min"]:
        failures.append("exact_agreement_min")
    if evaluation.get("within_half_agreement", 0.0) < g["within_half_agreement_min"]:
        failures.append("within_half_agreement_min")
    if evaluation.get("mae", 1e9) > g["mae_max"]:
        failures.append("mae_max")
    if evaluation.get("qwk", 0.0) < g["qwk_min"]:
        failures.append("qwk_min")
    if stability_spread > g["repeat_stability_max_spread"] + 1e-9:
        failures.append("repeat_stability_max_spread")
    return (not failures), failures


def subgroup_errors(
    preds: list[float],
    refs: list[float],
    subgroups: list[str],
) -> dict[str, dict]:
    """
    Per-subgroup MAE/exact agreement (where lawful/appropriate). Subgroups are
    coarse labels only (e.g. skill/task_type); never learner identity data.
    """
    buckets: dict[str, list[int]] = {}
    for i, grp in enumerate(subgroups):
        buckets.setdefault(grp, []).append(i)
    out: dict[str, dict] = {}
    for grp, idxs in sorted(buckets.items()):
        p = [preds[i] for i in idxs]
        r = [refs[i] for i in idxs]
        out[grp] = {
            "n": len(idxs),
            "mae": round(mean_absolute_error(p, r), 4),
            "exact_agreement": round(exact_band_agreement(p, r), 4),
        }
    return out


def build_promotion_report(
    *,
    candidate_name: str,
    baseline_name: str,
    preds: list[float],
    refs: list[float],
    repeat_runs: list[list[float]],
    subgroups: list[str] | None = None,
    invalid_output_rate: float = 0.0,
    adversarial_passed: bool = False,
    latency_ms_p50: float | None = None,
    cost_per_1k_usd: float | None = None,
) -> dict:
    """
    WS05-09 minimum comparison report required before promoting a judge
    model/prompt/rubric change against the currently deployed version.

    ``promote`` is True ONLY when the frozen numeric gates pass AND the
    candidate survived the adversarial prompt-injection suite (a model cannot
    score well on clean data while obeying injected instructions on hostile
    data).
    """
    evaluation = evaluate_run(preds, refs)
    consistency = run_consistency_check(repeat_runs)

    systematic_bias = round(_mean([p - r for p, r in zip(preds, refs)]), 4) if preds else 0.0

    gates_ok, failing = gates_pass(evaluation, stability_spread=consistency["max_spread"])
    promote = bool(gates_ok and adversarial_passed and invalid_output_rate <= 0.02)

    return {
        "candidate": candidate_name,
        "baseline": baseline_name,
        "evaluation": evaluation,
        "repeated_run": consistency,
        "systematic_bias": systematic_bias,
        "subgroups": subgroup_errors(preds, refs, subgroups) if subgroups else {},
        "schema_invalid_rate": round(invalid_output_rate, 4),
        "adversarial_injection_passed": bool(adversarial_passed),
        "latency_ms_p50": latency_ms_p50,
        "cost_per_1k_usd": cost_per_1k_usd,
        "failing_gates": failing,
        "promote": promote,
    }


def run_consistency_check(run_values: list[list[float]]) -> dict:
    """Repeated-run summary used alongside gates_pass (spread + per-sample stds)."""
    if not run_values:
        return {"max_spread": 0.0, "per_sample_std_top": []}
    length = min(len(r) for r in run_values)
    max_spread = 0.0
    stds: list[float] = []
    for i in range(length):
        vals = [_quantize_band(r[i]) for r in run_values]
        max_spread = max(max_spread, max(vals) - min(vals))
        if len(run_values) > 1:
            stds.append(round(pstdev(vals), 4))
    stds.sort(reverse=True)
    return {"max_spread": max_spread, "per_sample_std_top": stds[:5]}
