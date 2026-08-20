from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_EXPERIMENT = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"
EXPECTED_HORIZONS = (7, 30, 365)
EXPECTED_FAMILIES = {
    7: {
        "V4_7D_SHORT_TREND_REVERSAL_LOGIT",
        "V4_7D_RELATIVE_STRENGTH_GB",
        "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
    },
    30: {
        "V4_30D_TREND_REVERSAL_LOGIT",
        "V4_30D_RELATIVE_CONTEXT_GB",
        "V4_30D_VOLATILITY_STATE_EXTRA_TREES",
    },
    365: {
        "V4_365D_LONG_TREND_LOGIT",
        "V4_365D_LONG_REGIME_GB",
        "V4_365D_RETURN_MAGNITUDE_ENSEMBLE",
    },
}
EXPECTED_ROWS = {7: 300, 30: 300, 365: 250}
EXPECTED_WINNERS = {
    7: "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
    30: None,
    365: None,
}
EXPECTED_SHA256 = "7fa92f9edbcc414ae8e28d71fed9abac410fad67b28bda369f3689d2930f7f03"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def as_float(value, label: str) -> float:
    require(value is not None, f"Missing metric: {label}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Non-numeric metric: {label}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    args = parser.parse_args()

    path = Path(args.results).resolve()
    require(path.is_file(), f"V4 development results missing: {path}")
    actual_sha = sha256(path)
    require(actual_sha == EXPECTED_SHA256, f"Unexpected V4 development results SHA-256: {actual_sha}")

    report = json.loads(path.read_text(encoding="utf-8"))
    require(report.get("experiment_id") == EXPECTED_EXPERIMENT, "Unexpected V4 experiment id")
    require(report.get("evidence_class") == EXPECTED_EVIDENCE_CLASS, "Unexpected V4 evidence class")
    require(report.get("strict_point_in_time_claim_allowed") is False, "Strict point-in-time claim unexpectedly allowed")
    require(tuple(report.get("recovery_horizons", [])) == EXPECTED_HORIZONS, "Unexpected V4 recovery horizons")
    require(report.get("v2_consumed_origins_excluded") is True, "V2 consumed origins not excluded")
    require(report.get("v3_development_origins_excluded") is True, "V3 development origins not excluded")
    require(report.get("v3_final_holdout_origins_excluded") is True, "V3 final holdout origins not excluded")
    require(report.get("v4_final_holdout_origins_excluded") is True, "V4 final holdout origins not excluded")
    require(report.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout outcomes were viewed")
    require(report.get("v4_final_holdout_outcomes_viewed") is False, "V4 final holdout outcomes were viewed")
    require(report.get("recommendation_policy_changed") is False, "Recommendation policy changed during V4 development")
    require(report.get("production_promotion_allowed") is False, "V4 development improperly allows production promotion")
    require(report.get("next_gate") == "VALIDATE_AND_REVIEW_V4_DEVELOPMENT_RESULTS_BEFORE_ANY_FINAL_HOLDOUT_EXPOSURE", "Unexpected V4 next gate")

    horizon_results = report.get("horizon_results")
    selected_winners = report.get("selected_winners")
    require(isinstance(horizon_results, dict), "Missing horizon_results")
    require(isinstance(selected_winners, dict), "Missing selected_winners")
    require(set(horizon_results) == {str(h) for h in EXPECTED_HORIZONS}, "Unexpected horizon result keys")
    require(set(selected_winners) == {str(h) for h in EXPECTED_HORIZONS}, "Unexpected selected winner keys")

    for horizon in EXPECTED_HORIZONS:
        block = horizon_results[str(horizon)]
        candidates = block.get("candidate_results")
        require(isinstance(candidates, dict), f"Missing candidate results for {horizon}d")
        require(set(candidates) == EXPECTED_FAMILIES[horizon], f"Unexpected candidate set for {horizon}d")

        qualified = []
        for family, metrics in candidates.items():
            require(int(metrics.get("development_rows", 0)) == EXPECTED_ROWS[horizon], f"Unexpected row count for {horizon}d {family}")
            direction = as_float(metrics.get("directional_accuracy_pct"), f"{horizon}d {family} directional_accuracy_pct")
            baseline = as_float(metrics.get("development_majority_baseline_accuracy_pct"), f"{horizon}d {family} baseline_accuracy_pct")
            delta = as_float(metrics.get("model_minus_development_majority_accuracy_pct_points"), f"{horizon}d {family} baseline_adjusted")
            require(abs((direction - baseline) - delta) < 1e-8, f"Baseline-adjusted arithmetic mismatch for {horizon}d {family}")
            require(isinstance(metrics.get("assets_nonnegative_baseline_adjusted_skill"), int), f"Missing asset robustness count for {horizon}d {family}")
            require(isinstance(metrics.get("single_asset_explains_majority_of_positive_gain"), bool), f"Missing single-asset robustness flag for {horizon}d {family}")
            require(isinstance(metrics.get("single_fold_explains_majority_of_positive_gain"), bool), f"Missing single-fold robustness flag for {horizon}d {family}")
            as_float(metrics.get("mean_sign_strategy_return_pct_after_15bps_cost"), f"{horizon}d {family} economic return")
            as_float(metrics.get("turnover_units"), f"{horizon}d {family} turnover")
            require(isinstance(metrics.get("by_asset"), dict) and metrics["by_asset"], f"Missing by-asset evidence for {horizon}d {family}")
            require(isinstance(metrics.get("by_fold"), dict) and set(metrics["by_fold"]) == {"1", "2", "3", "4", "5"}, f"Missing five-fold evidence for {horizon}d {family}")
            gate = metrics.get("development_selection_gate_pass")
            require(isinstance(gate, bool), f"Missing selection-gate flag for {horizon}d {family}")
            if gate:
                qualified.append(family)

        expected_winner = EXPECTED_WINNERS[horizon]
        actual_winner = block.get("selected_development_winner")
        require(actual_winner == expected_winner, f"Unexpected selected winner for {horizon}d")
        require(selected_winners[str(horizon)] == expected_winner, f"Top-level winner mismatch for {horizon}d")
        require(block.get("qualified_winner_exists") is (expected_winner is not None), f"Qualified-winner flag mismatch for {horizon}d")
        if expected_winner is None:
            require(not qualified, f"Qualified candidate exists despite NO_QUALIFIED_WINNER for {horizon}d")
        else:
            require(expected_winner in qualified, f"Selected winner did not pass gate for {horizon}d")

    require(report.get("all_recovery_horizons_have_qualified_winners") is False, "All-recovery-winners flag should be false")

    print("CRYPTO_V4_DEVELOPMENT_RESULTS_VALIDATION=PASS")
    print(f"V4_DEVELOPMENT_RESULTS_SHA256={actual_sha}")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    for horizon in EXPECTED_HORIZONS:
        winner = EXPECTED_WINNERS[horizon] or "NO_QUALIFIED_WINNER"
        print(f"WINNER_{horizon}D={winner}")

    for horizon in EXPECTED_HORIZONS:
        print(f"===== {horizon}D DEVELOPMENT LEADERBOARD =====")
        block = horizon_results[str(horizon)]
        rows = []
        for family, metrics in block["candidate_results"].items():
            rows.append((
                family,
                float(metrics["model_minus_development_majority_accuracy_pct_points"]),
                float(metrics["directional_accuracy_pct"]),
                float(metrics["development_majority_baseline_accuracy_pct"]),
                int(metrics["assets_nonnegative_baseline_adjusted_skill"]),
                bool(metrics["single_asset_explains_majority_of_positive_gain"]),
                bool(metrics["single_fold_explains_majority_of_positive_gain"]),
                float(metrics["mean_sign_strategy_return_pct_after_15bps_cost"]),
                metrics.get("raw_brier_score"),
                bool(metrics["development_selection_gate_pass"]),
            ))
        rows.sort(key=lambda item: (-item[1], -item[2], item[0]))
        for row in rows:
            family, delta, direction, baseline, assets_nonnegative, single_asset, single_fold, economic, brier, gate = row
            brier_text = "NA" if brier is None else f"{float(brier):.6f}"
            print(
                f"{family}|DIR={direction:.4f}|BASE={baseline:.4f}|DELTA_PP={delta:.4f}|"
                f"NONNEG_ASSETS={assets_nonnegative}|SINGLE_ASSET={str(single_asset).upper()}|"
                f"SINGLE_FOLD={str(single_fold).upper()}|ECON_AFTER_COST={economic:.6f}|"
                f"BRIER={brier_text}|GATE={str(gate).upper()}"
            )
        selected = block.get("selected_development_winner") or "NO_QUALIFIED_WINNER"
        print(f"SELECTED_{horizon}D={selected}")

    print("NEXT_GATE=REVIEW_V4_DEVELOPMENT_LEADERBOARDS_AND_FREEZE_DECISIONS_BEFORE_ANY_FINAL_HOLDOUT_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
