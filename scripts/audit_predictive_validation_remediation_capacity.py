from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"
ASSETS = ["bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"]
HORIZONS = [7, 30, 90, 180]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    require(args.source_commit == EXPECTED_SOURCE_COMMIT, "Unexpected certified source commit")

    db = Path(args.database).resolve()
    require(db.is_file(), f"Database not found: {db}")
    before = sha256(db)

    con = duckdb.connect(str(db), read_only=True)
    try:
        price_rows = con.execute(
            """
            SELECT asset_id,
                   COUNT(*) AS row_count,
                   MIN(observation_date) AS first_date,
                   MAX(observation_date) AS last_date
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            GROUP BY asset_id
            ORDER BY asset_id
            """
        ).fetchall()

        signal_rows = con.execute(
            """
            SELECT historical_signal,
                   horizon_days,
                   COUNT(*) AS completed_rows
            FROM signal_forward_performance
            WHERE completed=TRUE
            GROUP BY historical_signal, horizon_days
            ORDER BY historical_signal, horizon_days
            """
        ).fetchall()

        forecast_memory = con.execute(
            """
            SELECT horizon_days,
                   COUNT(*) AS forecasts,
                   SUM(CASE WHEN outcome_status='MATURED' THEN 1 ELSE 0 END) AS matured,
                   MIN(forecast_date) AS first_forecast_date,
                   MAX(forecast_date) AS last_forecast_date
            FROM m40_forecast_memory
            GROUP BY horizon_days
            ORDER BY horizon_days
            """
        ).fetchall()

        module44 = con.execute(
            """
            SELECT horizon_days,
                   COUNT(*) AS decisions,
                   SUM(CASE WHEN outcome_status='MATURED' THEN 1 ELSE 0 END) AS matured
            FROM m44_decision_outcomes
            GROUP BY horizon_days
            ORDER BY horizon_days
            """
        ).fetchall()

        existing_model_validation = con.execute(
            """
            SELECT asset_id,
                   horizon_days,
                   MAX(validation_rows) AS validation_rows,
                   COUNT(DISTINCT model_key) AS models
            FROM m38_model_validation
            GROUP BY asset_id, horizon_days
            ORDER BY asset_id, horizon_days
            """
        ).fetchall()
    finally:
        con.close()

    after = sha256(db)
    require(before == after, "Read-only audit changed the database")

    coverage = []
    price_map = {row[0]: row for row in price_rows}
    validation_map = {(row[0], int(row[1])): row for row in existing_model_validation}

    for asset in ASSETS:
        row = price_map.get(asset)
        require(row is not None, f"Missing canonical price history for {asset}")
        total_rows = int(row[1])
        for horizon in HORIZONS:
            # Conservative capacity estimate for a true purged split:
            # reserve horizon rows between training labels and test origins,
            # retain at least 90 training origins and 30 testing origins.
            estimated_origins = max(total_rows - horizon, 0)
            minimum_required = 90 + horizon + 30
            feasible = total_rows >= minimum_required
            existing = validation_map.get((asset, horizon))
            coverage.append({
                "asset_id": asset,
                "horizon_days": horizon,
                "canonical_price_rows": total_rows,
                "estimated_forward_origins": estimated_origins,
                "conservative_minimum_price_rows": minimum_required,
                "purged_holdout_capacity": "SUFFICIENT" if feasible else "INSUFFICIENT",
                "existing_validation_rows": int(existing[2]) if existing else 0,
                "existing_model_count": int(existing[3]) if existing else 0,
                "first_date": str(row[2]),
                "last_date": str(row[3]),
            })

    insufficient = [x for x in coverage if x["purged_holdout_capacity"] != "SUFFICIENT"]

    payload = {
        "status": "CRYPTO_PREDICTIVE_VALIDATION_REMEDIATION_CAPACITY_AUDIT_COMPLETE",
        "source_commit": args.source_commit,
        "database": str(db),
        "read_only": True,
        "database_unchanged": True,
        "purged_holdout_capacity": coverage,
        "signal_forward_completed_by_label_horizon": [
            {
                "historical_signal": row[0],
                "horizon_days": int(row[1]),
                "completed_rows": int(row[2]),
            }
            for row in signal_rows
        ],
        "forecast_memory_by_horizon": [
            {
                "horizon_days": int(row[0]),
                "forecasts": int(row[1]),
                "matured": int(row[2] or 0),
                "first_forecast_date": str(row[3]),
                "last_forecast_date": str(row[4]),
            }
            for row in forecast_memory
        ],
        "module44_by_horizon": [
            {
                "horizon_days": int(row[0]),
                "decisions": int(row[1]),
                "matured": int(row[2] or 0),
            }
            for row in module44
        ],
        "insufficient_purged_holdout_groups": insufficient,
        "remediation_feasibility": "SUPPORTED" if not insufficient else "PARTIAL",
        "required_changes": [
            "MODULE38_PURGED_CHRONOLOGICAL_HOLDOUT",
            "MODULE39_TRUE_ROLLING_ORIGIN_FROM_DATE_LEVEL_REALIZED_OUTCOMES",
            "MODULE39_DIRECT_PROBABILITY_CALIBRATION_FROM_REALIZED_BINARY_OUTCOMES",
            "PRESERVE_MODULE44_FORWARD_ONLY_MATURITY",
            "DO_NOT_USE_EXISTING_M39_ROLLING_ORIGIN_ROWS_AS_CERTIFICATION_EVIDENCE",
        ],
        "next_gate": "IMPLEMENT_VALIDATION_METHODOLOGY_REMEDIATION_IN_BRANCH_WITH_FAIL_CLOSED_REGRESSION_TESTS",
    }

    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_PREDICTIVE_VALIDATION_REMEDIATION_CAPACITY_AUDIT=COMPLETE")
    print(f"REMEDIATION_FEASIBILITY={payload['remediation_feasibility']}")
    print(f"INSUFFICIENT_PURGED_HOLDOUT_GROUPS={len(insufficient)}")
    print("DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=IMPLEMENT_VALIDATION_METHODOLOGY_REMEDIATION_IN_BRANCH_WITH_FAIL_CLOSED_REGRESSION_TESTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
