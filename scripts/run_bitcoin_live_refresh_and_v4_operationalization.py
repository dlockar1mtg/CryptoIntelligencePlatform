from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import Module38Runner
from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import selected_v3_origins_for_group
from scripts.preflight_predictive_horizon_recovery_v4_development import v4_split_origin
from scripts.run_predictive_horizon_recovery_v4_development import fit_predict, manifest_content_hash
from scripts.run_v3_per_horizon_development_tournament import build_relative_market as build_v3_relative_market
from scripts.v4_horizon_recovery_model_spec import (
    EVIDENCE_CLASS,
    NATIVE_LAG_DAYS,
    attach_lagged_native,
    attach_relative,
    build_price_features,
    build_relative_market,
    candidate_features,
)

RUN_ID = "BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_V1"
WINNER = "V4_7D_VOLATILITY_STATE_EXTRA_TREES"
HORIZON = 7
EXPECTED_V3_RESULTS_SHA256 = "33b039fd83a27f868bc660584e775ea64743954e87bd70a8f120c952588b5fd1"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_DEVELOPMENT_RESULTS_SHA256 = "a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_head(repo_root: Path) -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, capture_output=True, check=False)
    require(proc.returncode == 0, f"Could not resolve repository HEAD: {proc.stderr.strip()}")
    return proc.stdout.strip()


def run_command(command: list[str], repo_root: Path, env: dict[str, str]) -> dict:
    proc = subprocess.run(command, cwd=repo_root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return {"command": command, "exit_code": int(proc.returncode), "output": proc.stdout}


def latest_bitcoin(conn: duckdb.DuckDBPyConnection, table: str) -> dict | None:
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    if table not in tables:
        return None
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}
    if not {"asset_id", "observation_date", "price_usd"}.issubset(columns):
        return None
    row = conn.execute(
        f"SELECT observation_date, price_usd FROM {table} WHERE asset_id='bitcoin' AND price_usd IS NOT NULL ORDER BY observation_date DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {"observation_date": str(row[0]), "price_usd": float(row[1])}


def latest_macro(conn: duckdb.DuckDBPyConnection) -> dict:
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    report: dict[str, object] = {}
    for table in ("macro_observations", "latest_macro_observations", "macro_regime_daily", "latest_macro_regime"):
        if table not in tables:
            report[table] = {"exists": False}
            continue
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}
        time_col = next((c for c in ("observation_date", "regime_date", "calculation_date", "date") if c in cols), None)
        latest = conn.execute(f"SELECT MAX({time_col}) FROM {table}").fetchone()[0] if time_col else None
        report[table] = {"exists": True, "time_column": time_col, "latest_time": None if latest is None else str(latest)}
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--governance", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--v3-results", required=True)
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--development-results", required=True)
    parser.add_argument("--decision-freeze", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    database = Path(args.database).resolve()
    governance = Path(args.governance).resolve()
    ledger_manifest_path = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    v3_results_path = Path(args.v3_results).resolve()
    v4_path = Path(args.v4_manifest).resolve()
    development_results_path = Path(args.development_results).resolve()
    decision_freeze_path = Path(args.decision_freeze).resolve()
    output = Path(args.output).resolve()

    for path in (repo_root, database, governance, ledger_manifest_path, v2_path, v3_path, v3_results_path, v4_path, development_results_path, decision_freeze_path):
        require(path.exists(), f"Required operationalization input missing: {path}")
    require(not output.exists(), "Operationalization output already exists; refusing overwrite")

    governance_text = governance.read_text(encoding="utf-8")
    for marker in (
        "MODULE1_INCREMENTAL_REFRESH_AUTHORIZED=TRUE",
        "MODULE1_FULL_REFRESH_AUTHORIZED=FALSE",
        "MODULE6_SYNC_AUTHORIZED=TRUE",
        "MODULE6_RESEARCH_PHASE_AUTHORIZED=FALSE",
        "V4_7D_FROZEN_FAMILY_OPERATIONAL_REFIT_AUTHORIZED=TRUE",
        "V4_MODEL_SELECTION_REOPENED=FALSE",
        "V4_POST_HOLDOUT_TUNING_AUTHORIZED=FALSE",
        "V4_HYPERPARAMETER_SEARCH_AUTHORIZED=FALSE",
        "V4_FEATURE_CONTRACT_CHANGE_AUTHORIZED=FALSE",
        "MODULE42_RERUN_AUTHORIZED=FALSE",
        "FIRST_PROSPECTIVE_OBSERVATION_CAPTURE_AUTHORIZED=FALSE",
    ):
        require(marker in governance_text, f"Governance missing required marker: {marker}")

    ledger_manifest = json_load(ledger_manifest_path)
    require(int(ledger_manifest.get("record_count", -1)) == 0, "Forward-evidence ledger is not empty")
    record_files = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(record_files) == 0, "Forward-evidence records already exist")

    v3_results_hash = sha256(v3_results_path)
    development_results_hash = sha256(development_results_path)
    require(v3_results_hash == EXPECTED_V3_RESULTS_SHA256, "Unexpected V3 development-results hash")
    require(development_results_hash == EXPECTED_DEVELOPMENT_RESULTS_SHA256, "Unexpected V4 development-results hash")

    v2 = json_load(v2_path)
    v3 = json_load(v3_path)
    v3_results = json_load(v3_results_path)
    v4 = json_load(v4_path)
    development_results = json_load(development_results_path)
    freeze = json_load(decision_freeze_path)

    require(v3_results.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout unexpectedly viewed")
    require(v4.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest content hash")
    require(manifest_content_hash(v4) == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "V4 manifest canonical content hash mismatch")
    require(development_results.get("selected_winners", {}).get("7") == WINNER, "Frozen V4 7d winner changed")
    require(development_results.get("selected_winners", {}).get("30") is None, "V4 30d no-winner decision changed")
    require(development_results.get("selected_winners", {}).get("365") is None, "V4 365d no-winner decision changed")
    require(freeze.get("development_decisions_frozen") is True, "V4 development decisions are not frozen")
    require(freeze.get("decisions", {}).get("7", {}).get("decision") == WINNER, "Decision freeze winner changed")
    require(freeze.get("v4_final_holdout_policy", {}).get("post_holdout_tuning_allowed") is False, "Post-holdout tuning unexpectedly allowed")

    repo_head = git_head(repo_root)
    db_before = sha256(database)
    tracked_before = {
        "governance": sha256(governance), "ledger_manifest": sha256(ledger_manifest_path),
        "v2_manifest": sha256(v2_path), "v3_manifest": sha256(v3_path),
        "v3_results": v3_results_hash, "v4_manifest": sha256(v4_path),
        "development_results": development_results_hash, "decision_freeze": sha256(decision_freeze_path),
    }

    with duckdb.connect(str(database), read_only=True) as conn:
        price_before = latest_bitcoin(conn, "canonical_market_daily")
        asset_market_before = latest_bitcoin(conn, "asset_market_daily")
        macro_before = latest_macro(conn)

    env = dict(os.environ)
    env["CRYPTO_DATABASE_PATH"] = str(database)
    module1 = run_command([sys.executable, "run_module1.py"], repo_root, env)
    require(module1["exit_code"] == 0, "Module 1 incremental refresh failed")
    require("--full-refresh" not in module1["command"], "Full refresh was unexpectedly invoked")
    module6 = run_command([sys.executable, "run_module6.py", "--phase", "sync"], repo_root, env)
    require(module6["exit_code"] == 0, "Module 6 sync failed")

    db_after_refresh = sha256(database)
    with duckdb.connect(str(database), read_only=True) as conn:
        price_after = latest_bitcoin(conn, "canonical_market_daily")
        asset_market_after = latest_bitcoin(conn, "asset_market_daily")
        macro_after = latest_macro(conn)
        prices = conn.execute(
            "SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd FROM canonical_market_daily "
            "WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') AND price_usd IS NOT NULL ORDER BY observation_date, asset_id"
        ).fetchdf()
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        context = pd.DataFrame(columns=["observation_date"] + list(NATIVE_LAG_DAYS))
        if "crypto_features_daily" in tables:
            context = conn.execute("SELECT observation_date," + ",".join(NATIVE_LAG_DAYS) + " FROM crypto_features_daily ORDER BY observation_date").fetchdf()

    require(price_after is not None, "No refreshed canonical Bitcoin price is available")
    require(prices.shape[0] > 0, "Canonical core price history is empty after refresh")
    prices["observation_date"] = pd.to_datetime(prices["observation_date"])
    if not context.empty:
        context["observation_date"] = pd.to_datetime(context["observation_date"])

    settings = yaml.safe_load((repo_root / "config" / "settings.yaml").read_text(encoding="utf-8"))
    runner = object.__new__(Module38Runner)
    runner.cfg = settings["module38"]
    random_state = int(runner.cfg["random_state"])

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in v3["groups"]}
    v4_groups = {(g["asset_id"], int(g["horizon_days"])): g for g in v4["groups"]}
    require(("bitcoin", HORIZON) in v4_groups, "Bitcoin 7d V4 group missing")
    group = v4_groups[("bitcoin", HORIZON)]
    holdout_dates = set(group["v4_final_holdout_origin_dates"])

    relative_v4 = build_relative_market(prices)
    relative_v4["observation_date"] = pd.to_datetime(relative_v4["observation_date"])
    relative_v3 = build_v3_relative_market(prices)
    relative_v3["observation_date"] = pd.to_datetime(relative_v3["observation_date"])

    bitcoin_prices = prices[prices["asset_id"] == "bitcoin"].copy()
    v3_features = runner.build_features(bitcoin_prices, HORIZON).reset_index(drop=True)
    v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[("bitcoin", HORIZON)])
    v3_features.loc[v3_mask, "target_return"] = np.nan
    selected_v3_indices = selected_v3_origins_for_group(
        v3_features, HORIZON, runner, context, relative_v3, "bitcoin",
        v2_dates[("bitcoin", HORIZON)], v3_final_dates[("bitcoin", HORIZON)],
    )
    selected_v3_dates = {pd.Timestamp(v3_features.iloc[index]["observation_date"]).date().isoformat() for index in selected_v3_indices}
    excluded = set(v2_dates[("bitcoin", HORIZON)]) | set(v3_final_dates[("bitcoin", HORIZON)]) | selected_v3_dates | holdout_dates

    features = build_price_features(bitcoin_prices, HORIZON).reset_index(drop=True)
    holdout_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(holdout_dates)
    features.loc[holdout_mask, ["target_return", "target_positive", "target_exceeds_15pct"]] = np.nan
    latest_date = pd.Timestamp(features["observation_date"].max())
    current_rows = features.index[pd.to_datetime(features["observation_date"]) == latest_date].tolist()
    require(len(current_rows) == 1, "Could not resolve exactly one current Bitcoin feature row")
    origin_idx = int(current_rows[0])
    require(latest_date.date().isoformat() not in excluded, "Prospective origin collides with a governed excluded origin")

    origin_date, train, validation, current = v4_split_origin(features, origin_idx, HORIZON, runner, excluded)
    columns = candidate_features(HORIZON, WINNER)
    train_f = attach_relative(attach_lagged_native(train, context, columns), relative_v4, "bitcoin", columns)
    validation_f = attach_relative(attach_lagged_native(validation, context, columns), relative_v4, "bitcoin", columns)
    current_f = attach_relative(attach_lagged_native(current, context, columns), relative_v4, "bitcoin", columns)

    complete_train = train_f.dropna(subset=columns + ["target_return"]).copy()
    complete_validation = validation_f.dropna(subset=columns + ["target_return"]).copy()
    require(len(complete_train) >= int(runner.cfg.get("absolute_minimum_training_rows", 90)), "Insufficient complete prospective V4 training rows")
    require(len(complete_validation) >= int(runner.cfg.get("minimum_validation_rows", 30)), "Insufficient complete prospective V4 validation rows")
    require(len(current_f.dropna(subset=columns)) == 1, "Required current V4 features are missing; forecast must remain unavailable")

    probability, predicted_return = fit_predict(HORIZON, WINNER, train_f, validation_f, current_f, columns, random_state)
    require(predicted_return is None, "Frozen V4 7d classifier unexpectedly returned a regression prediction")
    predicted_positive = int(float(probability) >= 0.5)

    db_after_forecast = sha256(database)
    require(db_after_forecast == db_after_refresh, "V4 operational refit modified the canonical database")
    tracked_after = {
        "governance": sha256(governance), "ledger_manifest": sha256(ledger_manifest_path),
        "v2_manifest": sha256(v2_path), "v3_manifest": sha256(v3_path),
        "v3_results": sha256(v3_results_path), "v4_manifest": sha256(v4_path),
        "development_results": sha256(development_results_path), "decision_freeze": sha256(decision_freeze_path),
    }
    require(tracked_after == tracked_before, "Frozen governance/model evidence changed during live operationalization")
    require(int(json_load(ledger_manifest_path).get("record_count", -1)) == 0, "Ledger manifest changed during operationalization")
    final_record_files = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(final_record_files) == 0, "Observation record unexpectedly created")

    feature_values = {name: float(current_f.iloc[0][name]) for name in columns}
    report = {
        "run_id": RUN_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit_sha": repo_head,
        "asset_id": "bitcoin",
        "refresh": {
            "module1_mode": "incremental", "module1_full_refresh": False,
            "module1_exit_code": module1["exit_code"], "module1_output": module1["output"],
            "module6_phase": "sync", "module6_exit_code": module6["exit_code"], "module6_output": module6["output"],
            "database_sha256_before": db_before, "database_sha256_after_refresh": db_after_refresh,
            "canonical_bitcoin_before": price_before, "canonical_bitcoin_after": price_after,
            "asset_market_bitcoin_before": asset_market_before, "asset_market_bitcoin_after": asset_market_after,
            "macro_before": macro_before, "macro_after": macro_after,
            "fred_api_key_configured": bool(os.getenv("FRED_API_KEY", "").strip()),
        },
        "v4_7d": {
            "winner": WINNER, "horizon_days": HORIZON,
            "forecast_date": origin_date.date().isoformat(),
            "latest_canonical_bitcoin_source_date": price_after["observation_date"],
            "database_sha256_used": db_after_refresh,
            "evidence_class": EVIDENCE_CLASS, "strict_point_in_time_claim_allowed": False,
            "feature_list": columns, "feature_values": feature_values,
            "training_window_start": pd.Timestamp(complete_train["observation_date"].iloc[0]).date().isoformat(),
            "training_window_end": pd.Timestamp(complete_train["observation_date"].iloc[-1]).date().isoformat(),
            "validation_window_start": pd.Timestamp(complete_validation["observation_date"].iloc[0]).date().isoformat(),
            "validation_window_end": pd.Timestamp(complete_validation["observation_date"].iloc[-1]).date().isoformat(),
            "complete_training_rows": int(len(complete_train)), "complete_validation_rows": int(len(complete_validation)),
            "random_state": random_state, "raw_probability_positive": float(probability),
            "predicted_positive": predicted_positive,
            "predicted_direction": "POSITIVE" if predicted_positive else "NEGATIVE_OR_FLAT",
            "contract_preserving_operational_refit": True, "model_selection_reopened": False,
            "post_holdout_tuning_performed": False, "hyperparameter_search_performed": False,
            "feature_contract_changed": False, "outcome_peeking_allowed": False,
        },
        "module42_rerun_performed": False,
        "personal_portfolio_context_supplied": False,
        "first_prospective_observation_captured": False,
        "ledger_record_count": 0,
        "btc_eth_recommendation_policy_skill_certified": False,
        "production_policy_changed": False,
        "autonomous_execution_authorized": False,
        "next_gate": "REVIEW_BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_RESULTS",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION=PASS")
    print("MODULE1_INCREMENTAL_REFRESH_EXECUTED=TRUE")
    print("MODULE1_FULL_REFRESH_EXECUTED=FALSE")
    print("MODULE6_SYNC_EXECUTED=TRUE")
    print(f"REFRESHED_CANONICAL_BITCOIN_DATE={price_after['observation_date']}")
    print(f"V4_7D_WINNER={WINNER}")
    print(f"V4_7D_FORECAST_DATE={origin_date.date().isoformat()}")
    print(f"V4_7D_RAW_PROBABILITY_POSITIVE={float(probability):.12f}")
    print(f"V4_7D_PREDICTED_DIRECTION={'POSITIVE' if predicted_positive else 'NEGATIVE_OR_FLAT'}")
    print("V4_MODEL_SELECTION_REOPENED=FALSE")
    print("V4_POST_HOLDOUT_TUNING_PERFORMED=FALSE")
    print("MODULE42_RERUN_PERFORMED=FALSE")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("LEDGER_RECORD_COUNT=0")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=REVIEW_BITCOIN_LIVE_REFRESH_AND_V4_OPERATIONALIZATION_RESULTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
