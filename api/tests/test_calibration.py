"""WS02-05: calibration harness contract — format validation and metrics."""

import pytest

from app.domain.calibration import (
    CALIBRATION_GATES,
    evaluate_run,
    exact_band_agreement,
    gates_pass,
    mean_absolute_error,
    quadratic_weighted_kappa,
    repeated_run_stability,
    run_consistency_check,
    subgroup_errors,
    validate_dataset,
    validate_record,
)


def _sample(**over):
    base = {
        "sample_id": "anon-001",
        "skill": "writing",
        "task_type": "task2",
        "prompt_license": "internal-or-permitted",
        "response": "Internally written practice response. No copyrighted text.",
        "human_scores": [{"rater": "R1", "overall": 6.5}, {"rater": "R2", "overall": 6.5}],
        "adjudicated_score": 6.5,
    }
    base.update(over)
    return base


# ── Format validation ────────────────────────────────────────────────────────

def test_valid_record_passes():
    validate_record(_sample())


def test_missing_key_rejected():
    bad = _sample()
    del bad["adjudicated_score"]
    with pytest.raises(ValueError, match="missing keys"):
        validate_record(bad)


def test_bad_skill_and_license_rejected():
    with pytest.raises(ValueError, match="bad skill"):
        validate_record(_sample(skill="listening"))
    with pytest.raises(ValueError, match="prompt_license"):
        validate_record(_sample(prompt_license="scraped-from-web"))


def test_unlicensed_license_values_only():
    # 'internal-or-permitted' | 'original' | 'licensed' — nothing scraped/copied.
    assert validate_record(_sample(prompt_license="original")) is None


def test_duplicate_sample_ids_rejected():
    with pytest.raises(ValueError, match="duplicate sample_id"):
        validate_dataset([_sample(), _sample(sample_id="anon-001")])


def test_empty_human_scores_rejected():
    with pytest.raises(ValueError, match="human_scores"):
        validate_record(_sample(human_scores=[]))


def test_score_bounds_enforced():
    with pytest.raises(ValueError, match="out of range|3.0-9.0"):
        validate_record(_sample(adjudicated_score=2.5))


# ── Metrics math ─────────────────────────────────────────────────────────────

def test_exact_agreement_counts_rounded_matches():
    preds = [6.5, 6.75, 5.5]   # 6.75 quantizes to 7.0
    refs = [6.5, 7.0, 6.0]
    assert exact_band_agreement(preds, refs) == 2 / 3


def test_within_half_band_counts_near_misses():
    preds = [6.5, 6.5, 6.5]
    refs = [6.5, 6.0, 7.5]
    assert within_half(preds, refs) == 2 / 3


def within_half(preds, refs):
    from app.domain.calibration import within_half_band_agreement
    return within_half_band_agreement(preds, refs)


def test_mae_basic():
    preds = [6.0, 7.0]
    refs = [6.5, 6.0]
    assert mean_absolute_error(preds, refs) == pytest.approx(0.75)


def test_perfect_predictions_yield_qwk_one():
    refs = [6.0, 6.5, 7.0, 5.5]
    assert quadratic_weighted_kappa(refs, refs) == pytest.approx(1.0)


def test_inverted_predictions_yield_negative_qwk():
    # Systematic opposite-end errors must score below zero agreement
    refs = [4.0, 4.5, 8.0, 8.5]
    preds = [8.5, 8.0, 4.5, 4.0]
    assert quadratic_weighted_kappa(preds, refs) < 0


def test_constant_prediction_qwk_is_zero_or_negative():
    refs = [5.0, 6.0, 7.0, 8.0]
    preds = [6.0, 6.0, 6.0, 6.0]
    assert quadratic_weighted_kappa(preds, refs) <= 0.0


def test_repeated_run_stability_reports_worst_sample():
    run1 = [6.0, 7.0, 5.5]
    run2 = [6.5, 7.0, 5.5]   # sample 0 moved by 0.5
    run3 = [7.0, 7.0, 5.5]   # sample 0 now moved by 1.0 across runs
    assert repeated_run_stability([run1, run2, run3]) == pytest.approx(1.0)


def test_stability_of_identical_runs_is_zero():
    runs = [[6.0]] * 3
    assert repeated_run_stability(runs) == 0.0


# ── Promotion gate logic ─────────────────────────────────────────────────────

def test_gates_fail_for_weak_candidate():
    ev = {"exact_agreement": 0.30, "within_half_agreement": 0.70,
          "mae": 0.80, "qwk": 0.55}
    ok, failing = gates_pass(ev, stability_spread=1.5)
    assert not ok
    assert set(failing) == {"exact_agreement_min", "within_half_agreement_min",
                            "mae_max", "qwk_min", "repeat_stability_max_spread"}


def test_gates_pass_for_strong_candidate():
    ev = {"exact_agreement": 0.50, "within_half_agreement": 0.90,
          "mae": 0.35, "qwk": 0.78}
    ok, failing = gates_pass(ev, stability_spread=0.5)
    assert ok and failing == []


def test_evaluation_snapshot_shape():
    ev = evaluate_run([6.5] * 4, [6.5] * 4)
    assert ev == {"n": 4, "exact_agreement": 1.0, "within_half_agreement": 1.0,
                  "mae": 0.0, "qwk": 1.0}


def test_subgroup_errors_break_down_by_label():
    preds = [6.0, 5.0, 7.0, 7.0]
    refs = [6.0, 6.0, 7.0, 6.5]
    groups = ["writing/task2", "writing/task2", "speaking/part2", "speaking/part2"]
    out = subgroup_errors(preds, refs, groups)
    assert out["writing/task2"]["n"] == 2
    assert out["writing/task2"]["exact_agreement"] == 0.5
    assert out["speaking/part2"]["mae"] == pytest.approx(0.25)


def test_consistency_check_summarises_runs():
    summary = run_consistency_check([[6.0, 7.0], [7.0, 7.0]])
    assert summary["max_spread"] == 1.0
    assert summary["per_sample_std_top"][0] >= summary["per_sample_std_top"][-1]


def test_gates_are_frozen_values():
    """Guard against silent threshold tuning (AGENTS: no benchmark claims)."""
    assert CALIBRATION_GATES == {
        "exact_agreement_min": 0.45,
        "within_half_agreement_min": 0.85,
        "mae_max": 0.50,
        "qwk_min": 0.70,
        "repeat_stability_max_spread": 1.0,
    }


# ── WS05-09: promotion report gate ───────────────────────────────────────────

from app.domain.calibration import build_promotion_report  # noqa: E402


def _good_run_inputs():
    refs = [6.0, 6.5, 7.0, 5.5, 4.5, 8.0] * 3
    preds = list(refs)
    runs = [list(preds)] * 3
    return refs, preds, runs


def test_promotion_report_passes_strong_candidate():
    refs, preds, runs = _good_run_inputs()
    rep = build_promotion_report(
        candidate_name="model-b/prompt-v2", baseline_name="model-a/prompt-v1",
        preds=preds, refs=refs, repeat_runs=runs,
        subgroups=["writing/task2"] * 9 + ["speaking/part2"] * 9,
        invalid_output_rate=0.0, adversarial_passed=True,
        latency_ms_p50=2100.0, cost_per_1k_usd=0.002,
    )
    assert rep["promote"] is True and rep["failing_gates"] == []
    assert rep["evaluation"]["qwk"] == 1.0
    assert "writing/task2" in rep["subgroups"]


def test_promotion_report_blocks_on_injection_failure():
    """Strong clean-data scores cannot bypass the adversarial gate."""
    refs, preds, runs = _good_run_inputs()
    rep = build_promotion_report(
        candidate_name="shiny-new", baseline_name="baseline",
        preds=preds, refs=refs, repeat_runs=runs,
        adversarial_passed=False,
    )
    assert rep["promote"] is False
    assert "adversarial_injection_passed" in rep


def test_promotion_report_blocks_weak_numeric_candidate():
    refs = [6.0, 6.5, 7.0, 5.5]
    preds = [5.0, 5.5, 6.0, 4.5]        # consistently 1 band low
    rep = build_promotion_report(
        candidate_name="cheap-model", baseline_name="prod",
        preds=preds, refs=refs, repeat_runs=[[*preds], [*preds]],
        adversarial_passed=True,
    )
    assert rep["promote"] is False
    assert rep["failing_gates"], "weak candidate must trip numeric gates"
    assert abs(rep["systematic_bias"]) == 1.0   # documented over/under-scoring


def test_promotion_report_blocks_high_invalid_rate():
    refs, preds, runs = _good_run_inputs()
    rep = build_promotion_report(
        candidate_name="flaky", baseline_name="prod",
        preds=preds, refs=refs, repeat_runs=runs,
        adversarial_passed=True, invalid_output_rate=0.15,
    )
    assert rep["promote"] is False
