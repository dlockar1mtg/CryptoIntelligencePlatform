from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_RESULTS_SHA256 = "a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb"
EXPECTED_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"

EXPECTED_CANDIDATES = {
    "7": [
        "V4_7D_SHORT_TREND_REVERSAL_LOGIT",
        "V4_7D_RELATIVE_STRENGTH_GB",
        "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
    ],
    "30": [
        "V4_30D_TREND_REVERSAL_LOGIT",
        "V4_30D_RELATIVE_CONTEXT_GB",
        "V4_30D_VOLATILITY_STATE_EXTRA_TREES",
    ],
    "365": [
        "V4_365D_LONG_TREND_LOGIT",
        "V4_365D_LONG_REGIME_GB",
        "V4_365D_RETURN_MAGNITUDE_ENSEMBLE",
    ],
}

EXPECTED_DECISIONS = {
    "7": "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
    "30": None,
    "365": None,
}

ASSET_GATE = {"7": 4, "30": 4, "365": 3}
EXPECTED_ROWS = {"7": 300, "30": 300, "365": 250}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def recompute_gate(metrics: dict, horizon: str) -> bool:
    return bool(
        float(metrics["model_minus_development_majority_accuracy_pct_points"]) > 0.0
        and int(metrics["assets_nonnegative_baseline_adjusted_skill"]) >= ASSET_GATE[horizon]
        and metrics["single_asset_explains_majority_of_positive_gain"] is False
        and metrics["single_fold_explains_majority_of_positive_gain"] is False
        and float(metrics["mean_sign_strategy_return_pct_after_15bps_cost"]) > 0.0
        and int(metrics["development_rows"]) == EXPECTED_ROWS[horizon]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    args = parser.parse_args()

    path = Path(args.results).resolve()
    require(path.is_file(), f"Missing V4 development-results artifact: {path}")
    result_hash = sha256(path)
    require(result_hash == EXPECTED_RESULTS_SHA256, "Unexpected V4 development-results physical hash")

    report = json.loads(path.read_text(encoding="utf-8"))
    require(report.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected V4 experiment id")
    require(report.get("evidence_class") == "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME", "Unexpected V4 evidence class")
    require(report.get("strict_point_in_time_claim_allowed") is False, "V4 improperly allows strict point-in-time claim")
    require(report.get("v4_manifest_content_sha256") == EXPECTED_MANIFEST_CONTENT_SHA256, "V4 results are not pinned to candidate-safe manifest")
    require(report.get("candidate_safe_membership_required") is True, "Candidate-safe membership marker missing")
    require(report.get("avalanche365_exception_governed") is True, "Governed Avalanche365 exception marker missing")
    require(report.get("v2_consumed_origins_excluded") is True, "V2 consumed-origin exclusion marker missing")
    require(report.get("v3_development_origins_excluded") is True, "V3 development-origin exclusion marker missing")
    require(report.get("v3_final_holdout_origins_excluded") is True, "V3 final-holdout origin exclusion marker missing")
    require(report.get("v4_final_holdout_origins_excluded") is True, "V4 final-holdout origin exclusion marker missing")
    require(report.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has been viewed")
    require(report.get("v4_final_holdout_outcomes_viewed") is False, "V4 final holdout has been viewed")
    require(report.get("recommendation_policy_changed") is False, "Recommendation policy changed during V4 development")
    require(report.get("production_promotion_allowed") is False, "V4 development improperly allows production promotion")
    require(list(report.get("recovery_horizons", [])) == [7, 30, 365], "Unexpected V4 recovery horizons")

    horizon_results = report.get("horizon_results", {})
    require(set(horizon_results) == {"7", "30", "365"}, "Unexpected V4 horizon-result set")

    recomputed_decisions: dict[str, str | None] = {}
    for horizon in ("7", "30", "365"):
        horizon_result = horizon_results[horizon]
        candidates = horizon_result.get("candidate_results", {})
        require(set(candidates) == set(EXPECTED_CANDIDATES[horizon]), f"Unexpected candidate set for {horizon}d")

        passing = []
        for candidate in EXPECTED_CANDIDATES[horizon]:
            metrics = candidates[candidate]
            require(int(metrics.get("development_rows", -1)) == EXPECTED_ROWS[horizon], f"Unexpected development coverage for {candidate}")
            recomputed = recompute_gate(metrics, horizon)
            require(bool(metrics.get("development_selection_gate_pass")) == recomputed, f"Stored V4 gate decision does not recompute for {candidate}")
            if recomputed:
                passing.append(candidate)

        stored_winner = horizon_result.get("selected_development_winner")
        require(bool(horizon_result.get("qualified_winner_exists")) == (stored_winner is not None), f"Winner-existence marker mismatch for {horizon}d")
        if stored_winner is not None:
            require(stored_winner in passing, f"Selected {horizon}d winner did not pass frozen gate")
        else:
            require(not passing, f"{horizon}d has passing candidate but stores NO_QUALIFIED_WINNER")

        require(stored_winner == EXPECTED_DECISIONS[horizon], f"Unexpected frozen V4 development decision for {horizon}d")
        recomputed_decisions[horizon] = stored_winner

    require(report.get("selected_winners") == recomputed_decisions, "Top-level V4 selected-winner map mismatch")
    require(report.get("all_recovery_horizons_have_qualified_winners") is False, "V4 incorrectly claims all horizons have winners")
    require(report.get("next_gate") == "VALIDATE_AND_REVIEW_V4_DEVELOPMENT_RESULTS_BEFORE_ANY_FINAL_HOLDOUT_EXPOSURE", "Unexpected V4 development next-gate marker")

    long_trend = horizon_results["365"]["candidate_results"]["V4_365D_LONG_TREND_LOGIT"]
    require(float(long_trend["model_minus_development_majority_accuracy_pct_points"]) > 0.0, "365d long-trend challenger did not beat baseline")
    require(int(long_trend["assets_nonnegative_baseline_adjusted_skill"]) >= 3, "365d long-trend challenger lacks cross-asset breadth")
    require(long_trend["single_asset_explains_majority_of_positive_gain"] is True, "365d long-trend expected concentration failure is absent")
    require(long_trend["single_fold_explains_majority_of_positive_gain"] is False, "365d long-trend unexpectedly fails fold concentration")
    require(float(long_trend["mean_sign_strategy_return_pct_after_15bps_cost"]) > 0.0, "365d long-trend challenger lacks positive after-cost diagnostic")
    require(long_trend["development_selection_gate_pass"] is False, "365d long-trend must remain disqualified under frozen V4 gate")

    print("CRYPTO_V4_DEVELOPMENT_RESULTS_VALIDATION=PASS")
    print(f"V4_DEVELOPMENT_RESULTS_SHA256={result_hash}")
    print("DECISION_7D=V4_7D_VOLATILITY_STATE_EXTRA_TREES")
    print("DECISION_30D=NO_QUALIFIED_WINNER")
    print("DECISION_365D=NO_QUALIFIED_WINNER")
    print("365D_LONG_TREND_STRONG_CHALLENGER_BUT_GATE_FAIL=TRUE")
    print("365D_LONG_TREND_FAILURE_REASON=SINGLE_ASSET_POSITIVE_GAIN_CONCENTRATION")
    print("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("PRODUCTION_PROMOTION_ALLOWED=FALSE")
    print("NEXT_GATE=PRESERVE_RESULTS_AND_FREEZE_V4_DEVELOPMENT_DECISIONS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
