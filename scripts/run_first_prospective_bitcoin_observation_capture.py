from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import duckdb

LEDGER_ID = "BITCOIN_STRATEGIC_REGIME_FORWARD_EVIDENCE_LEDGER_V1"
SCHEMA_VERSION = 1
TIMEZONE = "America/Chicago"
ASSET_ID = "bitcoin"
EXPECTED_V2_RESULT_SHA256 = "ed22cfb5eb83ac860527ca3c47c6b8d9e10a7cb3827ebb89ebd33fe8a324b9ca"
EXPECTED_EXTENDED_HISTORY_SHA256 = "549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961"
HALVING_DATE = "2024-04-20"

STRATEGIC_STATES = {"ACCUMULATE", "HOLD", "DISTRIBUTE", "INSUFFICIENT_EVIDENCE"}
TACTICAL_STATES = {"ACCELERATE", "NORMAL", "DELAY", "NO_NEW_CAPITAL", "INSUFFICIENT_EVIDENCE"}
EXISTING_STATES = {"HOLD_EXISTING", "STAGED_DISTRIBUTION", "RISK_REDUCTION", "INSUFFICIENT_EVIDENCE"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@dataclass
class Discovery:
    tables: list[str]
    bitcoin_price: float | None
    bitcoin_price_date: str | None
    bitcoin_price_source: str | None
    candidate_tables: dict[str, list[str]]


def discover_database(db_path: Path) -> Discovery:
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        table_rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()
        tables = [row[0] for row in table_rows]

        candidate_tables: dict[str, list[str]] = {}
        keywords = {
            "price": ("price", "market", "canonical"),
            "recommendation": ("recommend", "module42", "signal", "action"),
            "forecast": ("forecast", "predict", "model"),
            "portfolio": ("portfolio", "holding", "position", "weight"),
            "macro": ("macro", "liquidity"),
        }
        for category, terms in keywords.items():
            candidate_tables[category] = [t for t in tables if any(term in t.lower() for term in terms)]

        bitcoin_price = None
        bitcoin_price_date = None
        bitcoin_price_source = None

        if "canonical_market_daily" in tables:
            cols = {
                row[1]
                for row in conn.execute("PRAGMA table_info('canonical_market_daily')").fetchall()
            }
            asset_col = next((c for c in ("asset_id", "asset", "symbol") if c in cols), None)
            date_col = next((c for c in ("date", "market_date", "observation_date", "timestamp") if c in cols), None)
            price_col = next((c for c in ("price_usd", "close", "price", "close_usd") if c in cols), None)
            if asset_col and date_col and price_col:
                rows = conn.execute(
                    f"SELECT {qident(date_col)}, {qident(price_col)} FROM canonical_market_daily "
                    f"WHERE lower(CAST({qident(asset_col)} AS VARCHAR)) IN ('bitcoin','btc') "
                    f"AND {qident(price_col)} IS NOT NULL ORDER BY {qident(date_col)} DESC LIMIT 1"
                ).fetchall()
                if rows:
                    bitcoin_price_date = str(rows[0][0])
                    bitcoin_price = float(rows[0][1])
                    bitcoin_price_source = "canonical_market_daily"

        return Discovery(
            tables=tables,
            bitcoin_price=bitcoin_price,
            bitcoin_price_date=bitcoin_price_date,
            bitcoin_price_source=bitcoin_price_source,
            candidate_tables=candidate_tables,
        )
    finally:
        conn.close()


def unmatured_outcomes() -> dict[str, Any]:
    return {
        "return_7d_exact": None,
        "return_30d_exact": None,
        "return_90d_exact": None,
        "return_180d_exact": None,
        "return_365d_exact": None,
        "return_1095d_exact": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--ledger-spec", required=True)
    parser.add_argument("--capture-design", required=True)
    parser.add_argument("--governance", required=True)
    parser.add_argument("--v2-result", required=True)
    parser.add_argument("--extended-history", required=True)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--inspection-output")
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()

    db = Path(args.database).resolve()
    manifest_path = Path(args.manifest).resolve()
    contract = Path(args.contract).resolve()
    ledger_spec = Path(args.ledger_spec).resolve()
    capture_design = Path(args.capture_design).resolve()
    governance = Path(args.governance).resolve()
    v2_result = Path(args.v2_result).resolve()
    extended_history = Path(args.extended_history).resolve()
    records_dir = Path(args.records_dir).resolve()

    for name, path in {
        "database": db,
        "manifest": manifest_path,
        "contract": contract,
        "ledger_spec": ledger_spec,
        "capture_design": capture_design,
        "governance": governance,
        "v2_result": v2_result,
        "extended_history": extended_history,
    }.items():
        require(path.is_file(), f"Required file missing: {name}={path}")

    require(sha256(v2_result) == EXPECTED_V2_RESULT_SHA256, "Preserved V2 result hash mismatch")
    require(sha256(extended_history) == EXPECTED_EXTENDED_HISTORY_SHA256, "Extended-history source hash mismatch")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("ledger_id") == LEDGER_ID, "Unexpected ledger id")
    require(int(manifest.get("record_count", -1)) == 0, "First-capture runner requires record_count=0")
    require(manifest.get("synthetic_initial_observation_allowed") is False, "Synthetic initial observation unexpectedly allowed")
    require(manifest.get("append_only_observation_records") is True, "Append-only ledger requirement missing")
    require(manifest.get("outcomes_unknown_at_initial_observation") is True, "Unknown-outcome requirement missing")
    require(manifest.get("autonomous_execution_authorized") is False, "Autonomous execution unexpectedly authorized")

    existing_records = sorted(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(existing_records) == 0, "First-capture runner requires no existing observation JSON records")

    discovery = discover_database(db)
    now = datetime.now(ZoneInfo(TIMEZONE))

    inspection = {
        "inspection_id": "FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_SOURCE_DISCOVERY_V1",
        "inspection_timestamp": now.isoformat(),
        "operating_date": now.date().isoformat(),
        "operating_timezone": TIMEZONE,
        "asset_id": ASSET_ID,
        "database_read_only": True,
        "table_count": len(discovery.tables),
        "candidate_tables": discovery.candidate_tables,
        "observed_bitcoin_price_usd": discovery.bitcoin_price,
        "observed_bitcoin_price_date": discovery.bitcoin_price_date,
        "observed_bitcoin_price_source": discovery.bitcoin_price_source,
        "module42_live_action_discovered": False,
        "v4_live_inference_discovered": False,
        "portfolio_context_discovered": False,
        "macro_liquidity_context_discovered": bool(discovery.candidate_tables.get("macro")),
        "missing_evidence_synthesized": False,
        "outcome_peeking_allowed": False,
        "capture_performed": False,
    }

    if args.inspection_output:
        inspection_output = Path(args.inspection_output).resolve()
        require(not inspection_output.exists(), "Inspection output already exists; refusing overwrite")
        inspection_output.parent.mkdir(parents=True, exist_ok=True)
        inspection_output.write_text(json.dumps(inspection, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_SOURCE_DISCOVERY=PASS")
    print(f"DATABASE_TABLE_COUNT={len(discovery.tables)}")
    print(f"BITCOIN_PRICE_DISCOVERED={'TRUE' if discovery.bitcoin_price is not None else 'FALSE'}")
    print(f"MODULE42_LIVE_ACTION_DISCOVERED={'TRUE' if inspection['module42_live_action_discovered'] else 'FALSE'}")
    print(f"V4_LIVE_INFERENCE_DISCOVERED={'TRUE' if inspection['v4_live_inference_discovered'] else 'FALSE'}")
    print(f"PORTFOLIO_CONTEXT_DISCOVERED={'TRUE' if inspection['portfolio_context_discovered'] else 'FALSE'}")
    print("MISSING_EVIDENCE_SYNTHESIZED=FALSE")
    print("OUTCOME_PEEKING_ALLOWED=FALSE")

    if not args.capture:
        print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
        print("CANONICAL_DATABASE_MODIFIED=FALSE")
        print("NEXT_GATE=REVIEW_FIRST_PROSPECTIVE_BITCOIN_SOURCE_DISCOVERY")
        return 0

    # Capture is intentionally fail-closed until governed live state-assignment inputs
    # are available and a separately reviewed authorization step explicitly permits it.
    raise RuntimeError(
        "Capture mode is not yet authorized after source discovery. Review discovered live evidence first."
    )


if __name__ == "__main__":
    raise SystemExit(main())
