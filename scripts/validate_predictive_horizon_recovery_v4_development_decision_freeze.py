from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_RESULTS_SHA256 = "a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb"
EXPECTED_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_DECISIONS = {
    "7": "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
    "30": "NO_QUALIFIED_WINNER",
    "365": "NO_QUALIFIED_WINNER",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--results", required=True)
    args = parser.parse_args()

    freeze_path = Path(args.freeze).resolve()
    results_path = Path(args.results).resolve()
    require(freeze_path.is_file(), "Missing V4 development decision freeze")
    require(results_path.is_file(), "Missing V4 development results")
    require(sha256(results_path) == EXPECTED_RESULTS_SHA256, "Unexpected V4 development-results hash")

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))

    require(freeze.get("experiment_id") == "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4", "Unexpected freeze experiment id")
    require(freeze.get("development_results_sha256") == EXPECTED_RESULTS_SHA256, "Freeze is not pinned to authoritative results")
    require(freeze.get("v4_manifest_content_sha256") == EXPECTED_MANIFEST_CONTENT_SHA256, "Freeze is not pinned to candidate-safe manifest")
    require(freeze.get("candidate_safe_membership_required") is True, "Freeze lacks candidate-safe control")
    require(freeze.get("development_decisions_frozen") is True, "Development decisions are not frozen")
    require(results.get("v4_final_holdout_outcomes_viewed") is False, "V4 final holdout has already been viewed")
    require(results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout has already been viewed")

    for horizon, expected in EXPECTED_DECISIONS.items():
        row = freeze["decisions"][horizon]
        result_row = results["horizon_results"][horizon]
        actual_result = result_row.get("selected_development_winner") or "NO_QUALIFIED_WINNER"
        require(row.get("decision") == expected, f"Unexpected frozen decision for {horizon}d")
        require(actual_result == expected, f"Freeze/results mismatch for {horizon}d")

    require(freeze["decisions"]["7"].get("eligible_for_v4_final_holdout") is True, "7d winner not authorized for final holdout")
    require(freeze["decisions"]["30"].get("eligible_for_v4_final_holdout") is False, "30d no-winner incorrectly authorized")
    require(freeze["decisions"]["365"].get("eligible_for_v4_final_holdout") is False, "365d no-winner incorrectly authorized")
    require(freeze["decisions"]["365"].get("v5_challenger_signal") == "V4_365D_LONG_TREND_LOGIT", "365d challenger signal missing")
    require(freeze["decisions"]["365"].get("v4_failure_reason") == "SINGLE_ASSET_POSITIVE_GAIN_CONCENTRATION", "365d failure reason changed")

    policy = freeze["v4_final_holdout_policy"]
    require(policy.get("open_only_for_qualified_development_winners") is True, "Final holdout policy changed")
    require(policy.get("eligible_horizons") == [7], "Unexpected final-holdout eligible horizons")
    require(policy.get("ineligible_horizons") == [30, 365], "Unexpected final-holdout ineligible horizons")
    require(policy.get("post_holdout_tuning_allowed") is False, "Post-holdout tuning was enabled")
    require(freeze.get("v4_final_holdout_outcomes_viewed_at_freeze") is False, "Freeze records V4 holdout exposure")
    require(freeze.get("v3_final_holdout_outcomes_viewed_at_freeze") is False, "Freeze records V3 holdout exposure")
    require(freeze.get("recommendation_policy_changed") is False, "Recommendation policy changed")
    require(freeze.get("production_promotion_allowed") is False, "Production promotion allowed")

    print("CRYPTO_V4_DEVELOPMENT_DECISION_FREEZE_VALIDATION=PASS")
    print(f"V4_DEVELOPMENT_RESULTS_SHA256={EXPECTED_RESULTS_SHA256}")
    print("DECISION_7D=V4_7D_VOLATILITY_STATE_EXTRA_TREES")
    print("DECISION_30D=NO_QUALIFIED_WINNER")
    print("DECISION_365D=NO_QUALIFIED_WINNER")
    print("FINAL_HOLDOUT_ELIGIBLE_HORIZONS=7")
    print("FINAL_HOLDOUT_INELIGIBLE_HORIZONS=30,365")
    print("365D_LONG_TREND_RESERVED_AS_V5_CHALLENGER=TRUE")
    print("V4_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("POST_HOLDOUT_TUNING_ALLOWED=FALSE")
    print("NEXT_GATE=BUILD_AND_VALIDATE_7D_ONLY_V4_FINAL_HOLDOUT_RUNNER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
