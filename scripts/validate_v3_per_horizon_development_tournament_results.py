from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3"
EXPECTED_EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"
EXPECTED_HORIZONS = ["7", "30", "90", "180", "365"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    args = parser.parse_args()

    path = Path(args.results).resolve()
    require(path.is_file(), f"Tournament results missing: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))

    require(report.get("experiment_id") == EXPECTED_EXPERIMENT_ID, "Unexpected experiment id")
    require(report.get("evidence_class") == EXPECTED_EVIDENCE_CLASS, "Unexpected evidence class")
    require(report.get("strict_point_in_time_claim_allowed") is False, "Strict point-in-time claim must remain blocked")
    require(report.get("v2_consumed_origins_excluded_from_selection_training_and_validation") is True, "V2 consumed-origin exclusion missing")
    require(report.get("v3_final_holdout_origins_excluded_from_selection_training_and_validation") is True, "V3 holdout-origin exclusion missing")
    require(report.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout outcomes were viewed")
    require(report.get("governed_native_context_lags_enforced") is True, "Governed native-context lags were not enforced")
    require(report.get("recommendation_policy_changed") is False, "Recommendation policy changed during tournament")
    require(report.get("production_promotion_allowed") is False, "Development tournament cannot production-promote")
    require(int(report.get("development_folds", 0)) == 5, "Expected five development folds")
    require(int(report.get("origins_per_fold_per_supported_asset", 0)) == 10, "Expected ten origins per fold per supported asset")

    horizon_results = report.get("horizon_results")
    require(isinstance(horizon_results, dict), "Missing horizon results")
    require(sorted(horizon_results.keys(), key=int) == EXPECTED_HORIZONS, "Unexpected horizon result set")

    selected = report.get("selected_winners")
    require(isinstance(selected, dict), "Missing selected winners")
    require(sorted(selected.keys(), key=int) == EXPECTED_HORIZONS, "Unexpected selected-winner horizon set")

    for horizon in EXPECTED_HORIZONS:
        block = horizon_results[horizon]
        candidates = block.get("candidate_results")
        require(isinstance(candidates, dict) and len(candidates) >= 5, f"Missing candidate leaderboard for {horizon}d")
        winner = block.get("selected_development_winner")
        qualified = block.get("qualified_winner_exists")
        require(bool(winner is not None) == bool(qualified), f"Winner qualification mismatch for {horizon}d")
        require(selected[horizon] == winner, f"Selected winner mismatch for {horizon}d")

        for family, metrics in candidates.items():
            require(int(metrics.get("development_rows", 0)) > 0, f"No development rows for {horizon}d {family}")
            require("directional_accuracy_pct" in metrics, f"Directional accuracy missing for {horizon}d {family}")
            require("model_minus_development_majority_accuracy_pct_points" in metrics, f"Baseline-adjusted skill missing for {horizon}d {family}")
            require("raw_brier_score" in metrics, f"Raw Brier missing for {horizon}d {family}")
            require("assets_nonnegative_baseline_adjusted_skill" in metrics, f"Asset robustness count missing for {horizon}d {family}")

    all_winners = all(selected[h] is not None for h in EXPECTED_HORIZONS)
    require(report.get("all_five_horizons_have_qualified_winners") is all_winners, "All-winners flag mismatch")

    expected_next = (
        "FREEZE_V3_HORIZON_WINNERS_BEFORE_FINAL_HOLDOUT"
        if all_winners
        else "REVIEW_HORIZONS_WITH_NO_QUALIFIED_DEVELOPMENT_WINNER_WITHOUT_VIEWING_V3_HOLDOUT"
    )
    require(report.get("next_gate") == expected_next, "Unexpected next gate")

    print("CRYPTO_V3_PER_HORIZON_DEVELOPMENT_TOURNAMENT_RESULTS_VALIDATION=PASS")
    print("INDEPENDENT_HORIZON_LEADERBOARDS=5")
    print("V2_CONSUMED_ORIGINS_EXCLUDED=TRUE")
    print("V3_FINAL_HOLDOUT_ORIGINS_EXCLUDED=TRUE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("GOVERNED_NATIVE_CONTEXT_LAGS_ENFORCED=TRUE")
    print(f"ALL_FIVE_HORIZONS_HAVE_QUALIFIED_WINNERS={str(all_winners).upper()}")
    for horizon in EXPECTED_HORIZONS:
        print(f"WINNER_{horizon}D={selected[horizon] or 'NO_QUALIFIED_WINNER'}")
    print(f"NEXT_GATE={expected_next}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
