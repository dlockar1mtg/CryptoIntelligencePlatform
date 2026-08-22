from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EXPECTED_DEVELOPMENT_RESULTS_SHA256 = "a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_V4_7D_FINAL_RESULTS_SHA256 = "fe82f2b8cdfe817bfbb825cd2d97eb7d02711c8d1a2d3e5b3daf6c17fe756a48"
SUPPORTED_365D_ASSETS = {"bitcoin", "ethereum", "solana", "chainlink", "avalanche"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_content_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--development-results", required=True)
    parser.add_argument("--v4-7d-final-results", required=True)
    parser.add_argument("--addendum", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runner_path = Path(args.runner).resolve()
    manifest_path = Path(args.v4_manifest).resolve()
    development_path = Path(args.development_results).resolve()
    final7_path = Path(args.v4_7d_final_results).resolve()
    addendum_path = Path(args.addendum).resolve()
    output_path = Path(args.output).resolve()

    for path in (runner_path, manifest_path, development_path, final7_path, addendum_path):
        require(path.is_file(), f"Required validation input missing: {path}")
    require(not output_path.exists(), "Auxiliary diagnostic output already exists; runner validation is pre-execution only")

    require(sha256(development_path) == EXPECTED_DEVELOPMENT_RESULTS_SHA256, "Unexpected V4 development-results hash")
    require(sha256(final7_path) == EXPECTED_V4_7D_FINAL_RESULTS_SHA256, "Unexpected V4 7d final-holdout results hash")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    development = json.loads(development_path.read_text(encoding="utf-8"))
    final7 = json.loads(final7_path.read_text(encoding="utf-8"))
    addendum = addendum_path.read_text(encoding="utf-8")
    source = runner_path.read_text(encoding="utf-8")
    ast.parse(source)

    require(manifest.get("experiment_id") == EXPERIMENT_ID, "Unexpected V4 manifest experiment id")
    require(manifest.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest content hash field")
    require(manifest_content_hash(manifest) == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "V4 manifest canonical content hash mismatch")
    require(manifest.get("candidate_safe_membership_required") is True, "Candidate-safe membership control missing")
    require(manifest.get("exact_calendar_target_date_required") is True, "Exact-calendar target requirement missing")
    require(manifest.get("holdout_outcome_values_read_during_membership_selection") is False, "V4 holdout values were read during membership selection")
    require(manifest.get("v3_final_holdout_reused") is False, "V3 final holdout was reused by V4")

    groups = [g for g in manifest.get("groups", []) if int(g.get("horizon_days", -1)) == 365]
    require(len(groups) == 5, "Expected five V4 365d groups")
    require({str(g["asset_id"]) for g in groups} == SUPPORTED_365D_ASSETS, "Unexpected V4 365d supported asset set")
    for group in groups:
        asset = str(group["asset_id"])
        dev = list(group.get("v4_development_origin_dates", []))
        holdout = list(group.get("v4_final_holdout_origin_dates", []))
        require(len(dev) == 50 and len(set(dev)) == 50, f"Unexpected development membership for {asset}")
        require(set(dev).isdisjoint(set(holdout)), f"Development/final-holdout overlap for {asset}")

    require(development.get("experiment_id") == EXPERIMENT_ID, "Unexpected development-results experiment id")
    require(development.get("selected_winners", {}).get("365") is None, "V4 365d is not frozen NO_QUALIFIED_WINNER")
    require(development.get("horizon_results", {}).get("365", {}).get("qualified_winner_exists") is False, "Unexpected V4 365d qualified-winner state")
    require(development.get("v4_final_holdout_outcomes_viewed") is False, "Development evidence indicates premature V4 holdout exposure")
    require(development.get("v3_final_holdout_outcomes_viewed") is False, "Development evidence indicates V3 final-holdout exposure")

    require(final7.get("evaluation_scope") == "7D_FINAL_HOLDOUT_ONLY", "Preserved final-holdout result is not 7d-only")
    require(final7.get("v4_7d_final_holdout_outcomes_viewed") is True, "V4 7d final holdout is not recorded as consumed")
    require(final7.get("v4_30d_final_holdout_outcomes_viewed") is False, "V4 30d final holdout is marked viewed")
    require(final7.get("v4_365d_final_holdout_outcomes_viewed") is False, "V4 365d final holdout is marked viewed")
    require(final7.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout is marked viewed")
    require(final7.get("post_holdout_tuning_allowed") is False, "Post-holdout tuning is unexpectedly allowed")
    require(final7.get("recommendation_policy_changed") is False, "Recommendation policy unexpectedly changed")
    require(final7.get("production_promotion_allowed") is False, "Production promotion unexpectedly allowed")

    for text in (
        "development-only and selection-neutral",
        "winner_gate_affected=false",
        "365D_DEVELOPMENT_AUXILIARY_ONLY",
        "NO_QUALIFIED_WINNER",
        "No date shifting or target approximation is allowed",
        "realized_forward_drawdown_pct",
    ):
        require(text in addendum, f"Governance addendum missing required text: {text}")

    required_source_fragments = (
        'duckdb.connect(str(database), read_only=True)',
        'v4_development_origin_dates',
        'v4_final_holdout_origin_dates',
        'timedelta(days=365)',
        'range(366)',
        'actual_return > 15.0',
        'btc_relative = actual_return - btc_return',
        'drawdown = 100.0 * min',
        '"selection_neutral": True',
        '"winner_gate_affected": False',
        '"v4_365d_development_decision": "NO_QUALIFIED_WINNER"',
        '"v4_30d_final_holdout_outcomes_viewed": False',
        '"v4_365d_final_holdout_outcomes_viewed": False',
        '"v3_final_holdout_outcomes_viewed": False',
        '"post_holdout_tuning_allowed": False',
        '"missing_values_synthesized": False',
        'hashes_after == hashes_before',
        'refusing overwrite',
    )
    for fragment in required_source_fragments:
        require(fragment in source, f"Runner missing required fail-closed contract fragment: {fragment}")

    prohibited_source_fragments = (
        "fit_predict(",
        ".fit(",
        "model_list(",
        "choose_winner(",
        "development_selection_gate_pass =",
        "production_promotion_allowed\": True",
        "recommendation_policy_changed\": True",
        "fillna(0",
        "interpolate(",
        "nearest",
    )
    for fragment in prohibited_source_fragments:
        require(fragment not in source, f"Runner contains prohibited selection/tuning/synthesis behavior: {fragment}")

    require("xrp" not in source.split("SUPPORTED_365D_ASSETS =", 1)[1].split("\n", 2)[0].lower(), "Runner appears to include XRP365 in supported assets")

    print("CRYPTO_V4_365D_AUXILIARY_DIAGNOSTIC_RUNNER_VALIDATION=PASS")
    print("DIAGNOSTIC_SCOPE=365D_DEVELOPMENT_AUXILIARY_ONLY")
    print("EXPECTED_SUPPORTED_ASSETS=5")
    print("EXPECTED_DEVELOPMENT_ROWS=250")
    print("EXPECTED_BTC_RELATIVE_ELIGIBLE_ROWS=200")
    print("DATABASE_OPEN_MODE=READ_ONLY")
    print("MODEL_FITTING_ALLOWED=FALSE")
    print("WINNER_SELECTION_ALLOWED=FALSE")
    print("SELECTION_NEUTRAL=TRUE")
    print("WINNER_GATE_AFFECTED=FALSE")
    print("V4_365D_DEVELOPMENT_DECISION=NO_QUALIFIED_WINNER")
    print("V4_7D_FINAL_HOLDOUT_OUTCOMES_VIEWED=TRUE")
    print("V4_30D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_365D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("POST_HOLDOUT_TUNING_ALLOWED=FALSE")
    print("DIAGNOSTIC_EXECUTION_PERFORMED=FALSE")
    print("NEXT_GATE=AUTHORIZE_SELECTION_NEUTRAL_V4_365D_DEVELOPMENT_AUXILIARY_DIAGNOSTIC_EXECUTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
