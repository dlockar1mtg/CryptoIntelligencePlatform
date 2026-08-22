from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import duckdb

LEDGER_ID = "ETHEREUM_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1"
TIMEZONE = "America/Chicago"
ASSET_ID = "ethereum"
EXPECTED_DATABASE_SHA256 = "0e5745889491c435d884cf7e3c9be080fb708d79dd9ba308f05006bcbb4657e3"
EXPECTED_BITCOIN_OBSERVATION_SHA256 = "b43aaba705282e7b1ee630604623e2bd9bf1e582848270e085ed38cf3347725f"
EXPECTED_BITCOIN_OBSERVATION_ID = "btc-prospective-ae5efdd0b4cb150f"
ALIGNMENT_ID = "CRYPTO_BTC_ETH_STRATEGIC_ALIGNMENT_UIP_OUTPUT_V1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def repo_relative(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def exact_price(conn: duckdb.DuckDBPyConnection, asset_id: str, date_text: str) -> float | None:
    row = conn.execute(
        """
        SELECT price_usd
        FROM canonical_market_daily
        WHERE lower(CAST(asset_id AS VARCHAR)) = ?
          AND observation_date = ?::DATE
          AND price_usd IS NOT NULL
        ORDER BY observation_date DESC
        LIMIT 1
        """,
        [asset_id.lower(), date_text],
    ).fetchone()
    return None if row is None else float(row[0])


def exact_return(conn: duckdb.DuckDBPyConnection, asset_id: str, end_date: str, days: int) -> float | None:
    end = datetime.fromisoformat(end_date).date()
    start = end - timedelta(days=days)
    end_price = exact_price(conn, asset_id, end.isoformat())
    start_price = exact_price(conn, asset_id, start.isoformat())
    if end_price is None or start_price is None or start_price == 0:
        return None
    return end_price / start_price - 1.0


def latest_table_date(conn: duckdb.DuckDBPyConnection, table: str) -> str | None:
    exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
        [table],
    ).fetchone()[0]
    if not exists:
        return None
    row = conn.execute(f'SELECT MAX(observation_date) FROM "{table}"').fetchone()
    return None if row is None or row[0] is None else str(row[0])


def latest_module42(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name='m42_asset_recommendations'"
    ).fetchone()[0]
    if not exists:
        return {"available": False, "recommendation_date": None, "action": None, "investment_score": None}
    row = conn.execute(
        """
        SELECT recommendation_date, best_action, investment_score
        FROM m42_asset_recommendations
        WHERE lower(CAST(asset_id AS VARCHAR)) = 'ethereum'
        ORDER BY recommendation_date DESC, calculated_at_utc DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return {"available": False, "recommendation_date": None, "action": None, "investment_score": None}
    return {
        "available": True,
        "recommendation_date": str(row[0]),
        "action": None if row[1] is None else str(row[1]),
        "investment_score": None if row[2] is None else float(row[2]),
    }


def running_high_drawdown(conn: duckdb.DuckDBPyConnection, asset_id: str, end_date: str) -> float | None:
    rows = conn.execute(
        """
        SELECT price_usd
        FROM canonical_market_daily
        WHERE lower(CAST(asset_id AS VARCHAR)) = ?
          AND observation_date <= ?::DATE
          AND price_usd IS NOT NULL
        ORDER BY observation_date
        """,
        [asset_id.lower(), end_date],
    ).fetchall()
    values = [float(row[0]) for row in rows]
    if not values:
        return None
    high = max(values)
    if high <= 0:
        return None
    return values[-1] / high - 1.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--eth-manifest", required=True)
    parser.add_argument("--eth-records-dir", required=True)
    parser.add_argument("--alignment-governance", required=True)
    parser.add_argument("--bitcoin-manifest", required=True)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    database = Path(args.database).resolve()
    eth_manifest_path = Path(args.eth_manifest).resolve()
    eth_records_dir = Path(args.eth_records_dir).resolve()
    alignment_path = Path(args.alignment_governance).resolve()
    bitcoin_manifest_path = Path(args.bitcoin_manifest).resolve()

    for name, path in {
        "repo_root": repo_root,
        "database": database,
        "eth_manifest": eth_manifest_path,
        "alignment_governance": alignment_path,
        "bitcoin_manifest": bitcoin_manifest_path,
    }.items():
        require(path.exists(), f"Required input missing: {name}={path}")

    require(sha256(database) == EXPECTED_DATABASE_SHA256, "Canonical database hash mismatch")

    alignment_text = alignment_path.read_text(encoding="utf-8")
    for marker in (
        ALIGNMENT_ID,
        "FIRST_ETHEREUM_PROSPECTIVE_OBSERVATION_AUTHORIZED=TRUE",
        "ETH_BITCOIN_CYCLE_CONTEXT_ALLOWED=TRUE",
        "ETH_BITCOIN_CYCLE_ACTION_RULE_ALLOWED=FALSE",
        "SYNTHETIC_ETH_HALVING_CYCLE_ALLOWED=FALSE",
        "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    ):
        require(marker in alignment_text, f"Missing alignment marker: {marker}")

    eth_manifest = read_json(eth_manifest_path)
    require(eth_manifest.get("ledger_id") == LEDGER_ID, "Unexpected Ethereum ledger id")
    require(int(eth_manifest.get("record_count", -1)) == 0, "First Ethereum capture requires record_count=0")
    require(eth_manifest.get("append_only_observation_records") is True, "Append-only Ethereum ledger marker missing")
    require(eth_manifest.get("synthetic_eth_halving_cycle_allowed") is False, "Synthetic ETH halving cycle unexpectedly allowed")
    require(eth_manifest.get("autonomous_execution_authorized") is False, "Autonomous execution unexpectedly authorized")

    existing_eth_records = sorted(eth_records_dir.rglob("*.json")) if eth_records_dir.exists() else []
    require(len(existing_eth_records) == 0, "First Ethereum capture requires no existing records")

    bitcoin_manifest = read_json(bitcoin_manifest_path)
    require(int(bitcoin_manifest.get("record_count", 0)) >= 1, "Bitcoin prospective ledger has no observation")
    btc_record_rel = bitcoin_manifest.get("last_observation_file") or bitcoin_manifest.get("first_observation_file")
    require(bool(btc_record_rel), "Bitcoin observation path missing from manifest")
    btc_record_path = (repo_root / str(btc_record_rel)).resolve()
    require(btc_record_path.is_file(), "Bitcoin observation file missing")
    require(sha256(btc_record_path) == EXPECTED_BITCOIN_OBSERVATION_SHA256, "Bitcoin observation hash mismatch")
    btc_record = read_json(btc_record_path)
    require(btc_record.get("observation_id") == EXPECTED_BITCOIN_OBSERVATION_ID, "Unexpected Bitcoin observation id")
    require(btc_record.get("asset_id") == "bitcoin", "Unexpected Bitcoin observation asset")
    require(btc_record.get("cycle_context", {}).get("calendar_only_action_authorized") is False, "Bitcoin calendar-only action unexpectedly authorized")

    conn = duckdb.connect(str(database), read_only=True)
    try:
        latest_eth = conn.execute(
            """
            SELECT observation_date, price_usd
            FROM canonical_market_daily
            WHERE lower(CAST(asset_id AS VARCHAR))='ethereum'
              AND price_usd IS NOT NULL
            ORDER BY observation_date DESC
            LIMIT 1
            """
        ).fetchone()
        require(latest_eth is not None, "No canonical Ethereum price discovered")
        observation_date = str(latest_eth[0])
        observation_price = float(latest_eth[1])
        require(observation_date == "2026-08-21", "Ethereum canonical price is not current for 2026-08-21")

        eth_return_7d = exact_return(conn, "ethereum", observation_date, 7)
        eth_return_30d = exact_return(conn, "ethereum", observation_date, 30)
        btc_return_7d = exact_return(conn, "bitcoin", observation_date, 7)
        btc_return_30d = exact_return(conn, "bitcoin", observation_date, 30)
        eth_btc_relative_7d = None if eth_return_7d is None or btc_return_7d is None else eth_return_7d - btc_return_7d
        eth_btc_relative_30d = None if eth_return_30d is None or btc_return_30d is None else eth_return_30d - btc_return_30d
        eth_drawdown = running_high_drawdown(conn, "ethereum", observation_date)
        raw_macro_date = latest_table_date(conn, "macro_observations")
        latest_raw_macro_date = latest_table_date(conn, "latest_macro_observations")
        macro_regime_date = latest_table_date(conn, "macro_regime_daily")
        latest_macro_regime_date = latest_table_date(conn, "latest_macro_regime")
        module42 = latest_module42(conn)
    finally:
        conn.close()

    now = datetime.now(ZoneInfo(TIMEZONE))
    require(now.date().isoformat() == "2026-08-21", "First Ethereum observation authorization is scoped to 2026-08-21")

    module42_current = bool(module42["available"] and module42["recommendation_date"] == observation_date)

    record: dict[str, Any] = {
        "ledger_id": LEDGER_ID,
        "schema_version": 1,
        "observation_timestamp": now.isoformat(),
        "operating_date": now.date().isoformat(),
        "operating_timezone": TIMEZONE,
        "asset_id": ASSET_ID,
        "asset_role": "SECONDARY_LONG_DURATION_CRYPTO_ASSET",
        "record_scope": "BOTH_NEW_CAPITAL_AND_EXISTING_HOLDINGS",
        "source_authorities": {
            "alignment_governance": repo_relative(alignment_path, repo_root),
            "canonical_database_sha256_read_only": EXPECTED_DATABASE_SHA256,
            "bitcoin_cycle_context_observation_id": EXPECTED_BITCOIN_OBSERVATION_ID,
            "bitcoin_cycle_context_observation_sha256": EXPECTED_BITCOIN_OBSERVATION_SHA256,
            "bitcoin_cycle_context_observation_path": repo_relative(btc_record_path, repo_root),
        },
        "observed_ethereum_price": {
            "observation_date": observation_date,
            "price_usd": observation_price,
            "source": "canonical_market_daily",
        },
        "decision_layers": {
            "strategic_state": "INSUFFICIENT_EVIDENCE",
            "strategic_reason": "Bitcoin cycle context is cross-market context only; no governed current Ethereum strategic policy combines ETH-specific trend, drawdown, macro, valuation/network, and portfolio evidence into a stronger state.",
            "tactical_new_capital_state": "INSUFFICIENT_EVIDENCE",
            "tactical_reason": "No governed live Ethereum V4 tactical inference or other certified current tactical timing signal is available.",
            "existing_position_state": "INSUFFICIENT_EVIDENCE",
            "existing_position_reason": "No governed current personal Ethereum holdings context is available and no strategic distribution or risk-reduction state is established.",
        },
        "bitcoin_cycle_context": {
            "context_role": "CROSS_MARKET_CONTEXT_ONLY_NOT_ETH_ACTION_RULE",
            "most_recent_bitcoin_halving_date": btc_record.get("cycle_context", {}).get("most_recent_halving_date"),
            "bitcoin_days_since_halving_at_btc_observation": btc_record.get("cycle_context", {}).get("days_since_halving"),
            "bitcoin_descriptive_phase": btc_record.get("cycle_context", {}).get("descriptive_phase"),
            "historical_interpretation": btc_record.get("cycle_context", {}).get("historical_interpretation"),
            "bitcoin_calendar_only_action_authorized": False,
            "synthetic_ethereum_halving_cycle": None,
        },
        "ethereum_market_evidence": {
            "return_7d_exact": eth_return_7d,
            "return_30d_exact": eth_return_30d,
            "eth_minus_btc_return_7d_exact": eth_btc_relative_7d,
            "eth_minus_btc_return_30d_exact": eth_btc_relative_30d,
            "drawdown_from_running_high": eth_drawdown,
            "missing_exact_feature_values_remain_null": True,
        },
        "macro_liquidity_evidence": {
            "raw_macro_observations_latest_date": raw_macro_date,
            "latest_macro_observations_latest_date": latest_raw_macro_date,
            "derived_macro_regime_latest_date": macro_regime_date,
            "latest_derived_macro_regime_date": latest_macro_regime_date,
            "derived_macro_regime_used_for_state_assignment": False,
        },
        "module42_context": {
            "available": module42["available"],
            "recommendation_date": module42["recommendation_date"],
            "native_action": module42["action"],
            "native_investment_score": module42["investment_score"],
            "current_for_observation_date": module42_current,
            "final_btc_eth_authority": False,
        },
        "v4_tactical_evidence": {
            "live_ethereum_inference_available": False,
            "value": None,
            "missing_reason": "No separately governed live Ethereum V4 operational inference was produced for this observation.",
        },
        "portfolio_context": {
            "current_ethereum_portfolio_weight": None,
            "undeployed_capital_available_to_ethereum": None,
            "governed_current_personal_portfolio_context_available": False,
        },
        "deployment_context": {
            "target_or_max_deployment_ceiling": None,
            "new_capital_deployment_authorized_by_this_record": False,
            "existing_position_sale_authorized_by_this_record": False,
        },
        "evidence_quality": {
            "missing_evidence_synthesized": False,
            "synthetic_eth_halving_cycle_allowed": False,
            "outcome_peeking_allowed": False,
            "nearest_date_substitution_allowed_for_outcomes": False,
            "bitcoin_cycle_context_alone_can_select_eth_state": False,
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
            "btc_eth_recommendation_policy_skill_certified": False,
            "production_policy_change_authorized": False,
            "autonomous_execution_authorized": False,
            "canonical_database_write_authorized": False,
        },
    }

    seed = (
        f"{LEDGER_ID}|{record['observation_timestamp']}|ethereum|{observation_price}|"
        f"{EXPECTED_DATABASE_SHA256}|{EXPECTED_BITCOIN_OBSERVATION_SHA256}"
    ).encode("utf-8")
    observation_id = "eth-prospective-" + hashlib.sha256(seed).hexdigest()[:16]
    record["observation_id"] = observation_id
    record_bytes = json_bytes(record)
    record_hash = hashlib.sha256(record_bytes).hexdigest()
    filename = f"{record['operating_date']}_{now.strftime('%Y%m%dT%H%M%S%z')}_{observation_id}.json"
    record_path = eth_records_dir / filename
    record_rel = repo_relative(record_path, repo_root)

    if not args.capture:
        print("FIRST_PROSPECTIVE_ETHEREUM_OBSERVATION_PREFLIGHT=PASS")
        print(f"PROPOSED_OBSERVATION_ID={observation_id}")
        print(f"PROPOSED_RECORD_SHA256={record_hash}")
        print(f"ETHEREUM_PRICE_USD={observation_price}")
        print(f"ETH_RETURN_7D_EXACT={eth_return_7d}")
        print(f"ETH_RETURN_30D_EXACT={eth_return_30d}")
        print(f"ETH_MINUS_BTC_RETURN_7D_EXACT={eth_btc_relative_7d}")
        print("STRATEGIC_STATE=INSUFFICIENT_EVIDENCE")
        print("TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE")
        print("EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE")
        print("BITCOIN_CYCLE_CONTEXT_ROLE=CROSS_MARKET_CONTEXT_ONLY_NOT_ETH_ACTION_RULE")
        print("FIRST_PROSPECTIVE_ETHEREUM_OBSERVATION_CAPTURED=FALSE")
        print("CANONICAL_DATABASE_MODIFIED=FALSE")
        print("NEXT_GATE=EXECUTE_FIRST_PROSPECTIVE_ETHEREUM_OBSERVATION_CAPTURE")
        return 0

    require(not record_path.exists(), "Ethereum observation path already exists")
    database_hash_before = sha256(database)
    manifest_hash_before = sha256(eth_manifest_path)
    eth_records_dir.mkdir(parents=True, exist_ok=True)

    temp_record = record_path.with_suffix(record_path.suffix + ".tmp")
    temp_manifest = eth_manifest_path.with_suffix(eth_manifest_path.suffix + ".tmp")
    require(not temp_record.exists(), "Temporary Ethereum record exists")
    require(not temp_manifest.exists(), "Temporary Ethereum manifest exists")

    temp_record.write_bytes(record_bytes)
    require(sha256(temp_record) == record_hash, "Temporary Ethereum record hash mismatch")

    updated_manifest = dict(eth_manifest)
    updated_manifest["record_count"] = 1
    updated_manifest["first_observation_id"] = observation_id
    updated_manifest["first_observation_file"] = record_rel
    updated_manifest["first_observation_sha256"] = record_hash
    updated_manifest["last_observation_id"] = observation_id
    updated_manifest["last_observation_file"] = record_rel
    updated_manifest["last_observation_sha256"] = record_hash
    updated_manifest["next_gate"] = "BUILD_AND_VALIDATE_BTC_ETH_UIP_STRATEGIC_OVERLAY_V1"
    temp_manifest.write_bytes(json_bytes(updated_manifest))

    os.replace(temp_record, record_path)
    os.replace(temp_manifest, eth_manifest_path)

    require(sha256(record_path) == record_hash, "Final Ethereum record hash mismatch")
    final_manifest = read_json(eth_manifest_path)
    require(int(final_manifest.get("record_count", -1)) == 1, "Ethereum manifest record_count is not one")
    require(final_manifest.get("first_observation_id") == observation_id, "Ethereum manifest observation id mismatch")
    require(final_manifest.get("first_observation_sha256") == record_hash, "Ethereum manifest observation hash mismatch")
    require(sha256(database) == database_hash_before == EXPECTED_DATABASE_SHA256, "Canonical database changed during Ethereum capture")
    require(sha256(eth_manifest_path) != manifest_hash_before, "Ethereum manifest did not change")

    print("FIRST_PROSPECTIVE_ETHEREUM_OBSERVATION_CAPTURE=PASS")
    print(f"OBSERVATION_ID={observation_id}")
    print(f"OBSERVATION_FILE={record_rel}")
    print(f"OBSERVATION_SHA256={record_hash}")
    print(f"ETHEREUM_PRICE_USD={observation_price}")
    print("STRATEGIC_STATE=INSUFFICIENT_EVIDENCE")
    print("TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE")
    print("EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE")
    print("BITCOIN_CYCLE_CONTEXT_ROLE=CROSS_MARKET_CONTEXT_ONLY_NOT_ETH_ACTION_RULE")
    print("LEDGER_RECORD_COUNT=1")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=BUILD_AND_VALIDATE_BTC_ETH_UIP_STRATEGIC_OVERLAY_V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
