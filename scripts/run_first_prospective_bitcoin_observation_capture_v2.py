from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LEDGER_ID = "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1"
SCHEMA_VERSION = 1
TIMEZONE = "America/Chicago"
ASSET_ID = "bitcoin"
AUTHORIZATION_ID = "BITCOIN_FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZATION_V1"
V4_RUN_ID = "BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_V1"
MACRO_RUN_ID = "BITCOIN_FIRST_OBSERVATION_GITHUB_FRED_MACRO_REFRESH_V1"
EXPECTED_V4_SHA256 = "4fb9c06cc69ac47e22bb881954e05b61f5b8dba0392133d601f5946807b739c2"
EXPECTED_MACRO_SHA256 = "67626cb87b9c041d47a685bc9a41fd47ab15c07f6db419a0e3c0d92b028d65c9"
EXPECTED_V2_RESULT_SHA256 = "ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca"
EXPECTED_EXTENDED_HISTORY_SHA256 = "549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961"
HALVING_DATE = date(2024, 4, 20)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def table_latest_time(macro: dict, name: str) -> str | None:
    table = macro.get("after", {}).get("macro_tables", {}).get(name, {})
    return table.get("latest_time")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--v4-operationalization", required=True)
    parser.add_argument("--macro-evidence", required=True)
    parser.add_argument("--v2-result", required=True)
    parser.add_argument("--extended-history", required=True)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()

    database = Path(args.database).resolve()
    manifest_path = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()
    authorization = Path(args.authorization).resolve()
    v4_path = Path(args.v4_operationalization).resolve()
    macro_path = Path(args.macro_evidence).resolve()
    v2_result = Path(args.v2_result).resolve()
    extended_history = Path(args.extended_history).resolve()

    for name, path in {
        "database": database,
        "manifest": manifest_path,
        "authorization": authorization,
        "v4_operationalization": v4_path,
        "macro_evidence": macro_path,
        "v2_result": v2_result,
        "extended_history": extended_history,
    }.items():
        require(path.is_file(), f"Required input missing: {name}={path}")

    authorization_text = authorization.read_text(encoding="utf-8")
    for marker in (
        AUTHORIZATION_ID,
        "FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZED=TRUE",
        "STRATEGIC_STATE=INSUFFICIENT_EVIDENCE",
        "TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE",
        "EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE",
        "V4_RECOMPUTE_FOR_CAPTURE_AUTHORIZED=FALSE",
        "CANONICAL_DATABASE_WRITE_AUTHORIZED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    ):
        require(marker in authorization_text, f"Authorization marker missing: {marker}")

    require(sha256(v4_path) == EXPECTED_V4_SHA256, "Frozen V4 operationalization hash mismatch")
    require(sha256(macro_path) == EXPECTED_MACRO_SHA256, "FRED macro evidence hash mismatch")
    require(sha256(v2_result) == EXPECTED_V2_RESULT_SHA256, "Preserved V2 result hash mismatch")
    require(sha256(extended_history) == EXPECTED_EXTENDED_HISTORY_SHA256, "Extended-history source hash mismatch")

    manifest = read_json(manifest_path)
    require(manifest.get("ledger_id") == LEDGER_ID, "Unexpected ledger id")
    require(int(manifest.get("record_count", -1)) == 0, "First capture requires manifest record_count=0")
    require(manifest.get("append_only_observation_records") is True, "Append-only ledger marker missing")
    require(manifest.get("outcomes_unknown_at_initial_observation") is True, "Unknown-outcome marker missing")
    require(manifest.get("autonomous_execution_authorized") is False, "Autonomous execution unexpectedly authorized")

    existing_records = sorted(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(existing_records) == 0, "First capture requires no existing observation JSON records")

    v4 = read_json(v4_path)
    macro = read_json(macro_path)

    require(v4.get("run_id") == V4_RUN_ID, "Unexpected V4 operationalization run id")
    v4_7d = v4.get("v4_7d", {})
    require(v4_7d.get("winner") == "V4_7D_VOLATILITY_STATE_EXTRA_TREES", "Unexpected V4 winner")
    require(v4_7d.get("forecast_date") == "2026-08-21", "Unexpected V4 forecast date")
    require(abs(float(v4_7d.get("raw_probability_positive")) - 0.7689586293159024) <= 1e-12, "Unexpected V4 probability")
    require(v4_7d.get("predicted_direction") == "POSITIVE", "Unexpected V4 direction")
    require(v4_7d.get("model_selection_reopened") is False, "V4 model selection was reopened")
    require(v4_7d.get("post_holdout_tuning_performed") is False, "V4 post-holdout tuning occurred")
    require(v4_7d.get("outcome_peeking_allowed") is False, "V4 outcome peeking unexpectedly allowed")
    require(v4.get("module42_rerun_performed") is False, "Module42 was rerun in V4 operationalization")

    require(macro.get("run_id") == MACRO_RUN_ID, "Unexpected macro evidence run id")
    require(macro.get("fred_api_key_configured") is True, "FRED key was not configured")
    require(macro.get("fred_api_key_value_recorded") is False, "FRED key value was recorded")
    require(macro.get("module1_incremental_refresh_executed") is True, "Module 1 incremental refresh missing")
    require(macro.get("module1_full_refresh_executed") is False, "Full refresh unexpectedly executed")
    require(macro.get("module6_sync_executed") is True, "Module 6 sync missing")
    require(macro.get("module42_rerun_performed") is False, "Module42 was rerun in macro evidence")
    require(macro.get("first_prospective_observation_captured") is False, "Macro evidence already captured an observation")
    require(int(macro.get("ledger_record_count", -1)) == 0, "Macro evidence ledger count is not zero")
    require(macro.get("production_pipeline_executed") is False, "Production pipeline unexpectedly executed")
    require(macro.get("production_policy_changed") is False, "Production policy unexpectedly changed")
    require(macro.get("autonomous_execution_authorized") is False, "Autonomous execution unexpectedly authorized")

    observation_price = macro.get("after", {}).get("bitcoin") or {}
    require(observation_price.get("observation_date") == "2026-08-21", "Unexpected observation-time Bitcoin date")
    require(abs(float(observation_price.get("price_usd")) - 78345.0) <= 1e-9, "Unexpected observation-time Bitcoin price")

    require(table_latest_time(macro, "macro_observations") == "2026-08-21", "Raw macro observations are not current")
    require(table_latest_time(macro, "latest_macro_observations") == "2026-08-21", "Latest macro observations are not current")
    require(table_latest_time(macro, "macro_regime_daily") == "2026-07-28", "Derived macro regime date changed from reviewed evidence")
    require(table_latest_time(macro, "latest_macro_regime") == "2026-07-28", "Latest derived macro regime date changed from reviewed evidence")

    database_hash_before = sha256(database)
    manifest_hash_before = sha256(manifest_path)
    now = datetime.now(ZoneInfo(TIMEZONE))
    operating_date = now.date()
    days_since_halving = (operating_date - HALVING_DATE).days

    seed = (
        f"{LEDGER_ID}|{now.isoformat()}|{ASSET_ID}|{EXPECTED_V4_SHA256}|{EXPECTED_MACRO_SHA256}|"
        "INSUFFICIENT_EVIDENCE|INSUFFICIENT_EVIDENCE|INSUFFICIENT_EVIDENCE"
    ).encode("utf-8")
    observation_id = "btc-prospective-" + hashlib.sha256(seed).hexdigest()[:16]

    record = {
        "ledger_id": LEDGER_ID,
        "schema_version": SCHEMA_VERSION,
        "observation_id": observation_id,
        "observation_timestamp": now.isoformat(),
        "operating_date": operating_date.isoformat(),
        "operating_timezone": TIMEZONE,
        "asset_id": ASSET_ID,
        "record_scope": "BOTH_NEW_CAPITAL_AND_EXISTING_HOLDINGS",
        "source_authorities": {
            "capture_authorization": {
                "id": AUTHORIZATION_ID,
                "path": str(authorization),
            },
            "v4_operationalization": {
                "run_id": V4_RUN_ID,
                "sha256": EXPECTED_V4_SHA256,
                "path": str(v4_path),
            },
            "fred_macro_refresh": {
                "run_id": MACRO_RUN_ID,
                "sha256": EXPECTED_MACRO_SHA256,
                "path": str(macro_path),
            },
            "preserved_v2_result_sha256": EXPECTED_V2_RESULT_SHA256,
            "extended_history_sha256": EXPECTED_EXTENDED_HISTORY_SHA256,
            "canonical_database_sha256_read_only": database_hash_before,
        },
        "observed_bitcoin_price": {
            "price_usd": float(observation_price["price_usd"]),
            "observation_date": observation_price["observation_date"],
            "source": "FRED_ENABLED_SCRATCH_REFRESH_AFTER_BITCOIN_SNAPSHOT",
            "source_evidence_sha256": EXPECTED_MACRO_SHA256,
        },
        "portfolio_context": {
            "current_bitcoin_portfolio_weight": None,
            "undeployed_capital_available_to_bitcoin": None,
            "governed_current_personal_portfolio_context_available": False,
            "missing_reason": "No governed current personal Bitcoin holdings or undeployed-capital source was available at capture time.",
        },
        "decision_layers": {
            "strategic_state": "INSUFFICIENT_EVIDENCE",
            "strategic_reason": "Raw FRED observations are current, but the governed derived macro regime remains dated 2026-07-28; current portfolio/deployment context and point-in-time-safe valuation/on-chain evidence are unavailable; cycle phase cannot independently select a strategic action.",
            "tactical_new_capital_state": "INSUFFICIENT_EVIDENCE",
            "tactical_reason": "The positive V4 7-day forecast can support ACCELERATE only inside an already allowed strategic regime and governed deployment ceiling; neither prerequisite is currently established.",
            "existing_position_state": "INSUFFICIENT_EVIDENCE",
            "existing_position_reason": "Governed current personal Bitcoin holdings context is unavailable and no strategic distribution or risk-reduction state is established.",
        },
        "module42": {
            "live_action": None,
            "recommendation_score": None,
            "missing_reason": "No live governed Module42 action was produced for this capture; historical July 28 action was not reconstructed from later data.",
            "module42_rerun_performed": False,
        },
        "v4_7d_tactical_evidence": {
            "winner": v4_7d["winner"],
            "forecast_date": v4_7d["forecast_date"],
            "raw_probability_positive": float(v4_7d["raw_probability_positive"]),
            "predicted_direction": v4_7d["predicted_direction"],
            "v4_source_bitcoin_price_usd": float(v4.get("refresh", {}).get("canonical_bitcoin_after", {}).get("price_usd")),
            "v4_source_bitcoin_date": v4.get("refresh", {}).get("canonical_bitcoin_after", {}).get("observation_date"),
            "feature_values": v4_7d.get("feature_values"),
            "evidence_class": v4_7d.get("evidence_class"),
            "strict_point_in_time_claim_allowed": v4_7d.get("strict_point_in_time_claim_allowed"),
            "model_selection_reopened": False,
            "post_holdout_tuning_performed": False,
            "recomputed_for_capture": False,
        },
        "other_forecasts": {
            "forecast_30d": None,
            "forecast_90d": None,
            "forecast_180d": None,
            "missing_reason": "No governed current values were available for these horizons at capture time.",
        },
        "cycle_context": {
            "most_recent_halving_date": HALVING_DATE.isoformat(),
            "days_since_halving": days_since_halving,
            "estimated_next_halving_date": None,
            "estimated_next_halving_distance_days": None,
            "normalized_cycle_position": None,
            "descriptive_phase": "POST_HALVING_RESET_ACCUMULATION_CONTEXT_HYPOTHESIS",
            "calendar_only_action_authorized": False,
            "sample_size_completed_cycles": 3,
            "historical_interpretation": "PATTERN_SUPPORTED_DESCRIPTIVELY",
            "uncertainty_note": "Cycle phase is descriptive context only; next-halving timing and normalized cycle position remain missing because no separately governed uncertainty-aware estimate is supplied for this capture.",
        },
        "market_state": {
            "drawdown_from_running_or_all_time_high": None,
            "medium_long_trend": {
                "return_7d": v4_7d.get("feature_values", {}).get("return_7d"),
                "return_30d": v4_7d.get("feature_values", {}).get("return_30d"),
                "distance_sma20": v4_7d.get("feature_values", {}).get("distance_sma20"),
                "distance_sma50": v4_7d.get("feature_values", {}).get("distance_sma50"),
            },
            "volatility_state": {
                "volatility_7d": v4_7d.get("feature_values", {}).get("volatility_7d"),
                "volatility_14d": v4_7d.get("feature_values", {}).get("volatility_14d"),
                "volatility_30d": v4_7d.get("feature_values", {}).get("volatility_30d"),
                "volatility_ratio_7d_30d": v4_7d.get("feature_values", {}).get("volatility_ratio_7d_30d"),
            },
            "drawdown_missing_reason": "No separately governed current drawdown-from-high value was supplied to this capture.",
        },
        "macro_liquidity_evidence": {
            "raw_macro_observations_latest_date": table_latest_time(macro, "macro_observations"),
            "latest_macro_observations_latest_date": table_latest_time(macro, "latest_macro_observations"),
            "derived_macro_regime_latest_date": table_latest_time(macro, "macro_regime_daily"),
            "latest_derived_macro_regime_date": table_latest_time(macro, "latest_macro_regime"),
            "raw_fred_current_for_operating_date": True,
            "derived_macro_regime_current_for_operating_date": False,
            "derived_regime_value_used_for_state_assignment": False,
            "stale_reason": "Derived macro regime remains dated 2026-07-28 after current FRED observations and Module 6 sync; it is preserved as stale evidence and not promoted to August 21.",
            "source_evidence_sha256": EXPECTED_MACRO_SHA256,
        },
        "valuation_onchain_evidence": {
            "available": False,
            "value": None,
            "missing_reason": "No governed point-in-time-safe valuation/on-chain evidence was supplied at capture time.",
        },
        "deployment_context": {
            "planned_entry_or_tranche_structure": None,
            "target_or_max_deployment_ceiling": None,
            "new_capital_deployment_authorized_by_this_record": False,
            "existing_position_sale_authorized_by_this_record": False,
        },
        "transaction_cost_assumption": {
            "status": "NOT_APPLIED",
            "basis_points": None,
            "reason": "No deployment or sale action is authorized by this insufficient-evidence observation.",
        },
        "evidence_quality": {
            "missing_evidence_synthesized": False,
            "synthetic_zero_allowed": False,
            "synthetic_neutral_allowed": False,
            "synthetic_worst_case_allowed": False,
            "outcome_peeking_allowed": False,
            "nearest_date_substitution_allowed": False,
            "uncertainty_notes": [
                "Bitcoin recommendation-policy skill remains uncertified.",
                "The V4 evidence class does not support a strict vintage point-in-time historical claim.",
                "The current raw macro observations and derived macro-regime freshness differ and are recorded separately.",
                "Portfolio and deployment context are missing rather than inferred.",
            ],
        },
        "outcomes": {
            "return_7d_exact": None,
            "return_30d_exact": None,
            "return_90d_exact": None,
            "return_180d_exact": None,
            "return_365d_exact": None,
            "return_1095d_exact": None,
            "status": "UNMATURED_AT_INITIAL_CAPTURE",
        },
        "policy_authority": {
            "bitcoin_recommendation_policy_skill_certified": False,
            "btc_eth_recommendation_policy_skill_not_certified": True,
            "production_policy_change_authorized": False,
            "autonomous_execution_authorized": False,
            "canonical_database_write_authorized": False,
        },
    }

    record_bytes = canonical_json_bytes(record)
    record_hash = hashlib.sha256(record_bytes).hexdigest()
    timestamp_token = now.strftime("%Y%m%dT%H%M%S%z")
    filename = f"{operating_date.isoformat()}_{timestamp_token}_{observation_id}.json"
    record_path = records_dir / filename
    require(not record_path.exists(), "Observation record path already exists")

    if not args.capture:
        print("FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_PREFLIGHT=PASS")
        print(f"PROPOSED_OBSERVATION_ID={observation_id}")
        print(f"PROPOSED_RECORD_SHA256={record_hash}")
        print("STRATEGIC_STATE=INSUFFICIENT_EVIDENCE")
        print("TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE")
        print("EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE")
        print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
        print("CANONICAL_DATABASE_MODIFIED=FALSE")
        print("NEXT_GATE=EXECUTE_AUTHORIZED_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE")
        return 0

    records_dir.mkdir(parents=True, exist_ok=True)
    temp_record = record_path.with_suffix(record_path.suffix + ".tmp")
    temp_manifest = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    require(not temp_record.exists(), "Temporary record path already exists")
    require(not temp_manifest.exists(), "Temporary manifest path already exists")

    temp_record.write_bytes(record_bytes)
    require(sha256(temp_record) == record_hash, "Temporary observation record hash mismatch")

    updated_manifest = dict(manifest)
    updated_manifest["record_count"] = 1
    updated_manifest["first_observation_id"] = observation_id
    updated_manifest["first_observation_file"] = str(record_path.relative_to(manifest_path.parent.parent.parent.parent)) if False else str(record_path)
    updated_manifest["first_observation_sha256"] = record_hash
    updated_manifest["last_observation_id"] = observation_id
    updated_manifest["last_observation_sha256"] = record_hash
    updated_manifest["next_gate"] = "PRESERVE_AND_REVIEW_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION"
    temp_manifest.write_bytes(canonical_json_bytes(updated_manifest))

    os.replace(temp_record, record_path)
    os.replace(temp_manifest, manifest_path)

    require(sha256(record_path) == record_hash, "Final observation record hash mismatch")
    final_manifest = read_json(manifest_path)
    require(int(final_manifest.get("record_count", -1)) == 1, "Manifest record count was not updated to one")
    require(final_manifest.get("first_observation_id") == observation_id, "Manifest first observation id mismatch")
    require(final_manifest.get("first_observation_sha256") == record_hash, "Manifest first observation hash mismatch")
    require(sha256(database) == database_hash_before, "Canonical database changed during observation capture")
    require(manifest_hash_before != sha256(manifest_path), "Manifest did not change during authorized capture")

    print("FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE=PASS")
    print(f"OBSERVATION_ID={observation_id}")
    print(f"OBSERVATION_FILE={record_path}")
    print(f"OBSERVATION_SHA256={record_hash}")
    print("STRATEGIC_STATE=INSUFFICIENT_EVIDENCE")
    print("TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE")
    print("EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE")
    print(f"OBSERVED_BITCOIN_PRICE_USD={float(observation_price['price_usd'])}")
    print(f"V4_7D_RAW_PROBABILITY_POSITIVE={float(v4_7d['raw_probability_positive'])}")
    print(f"V4_7D_PREDICTED_DIRECTION={v4_7d['predicted_direction']}")
    print("DERIVED_MACRO_REGIME_CURRENT=FALSE")
    print("LEDGER_RECORD_COUNT=1")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=PRESERVE_AND_REVIEW_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
