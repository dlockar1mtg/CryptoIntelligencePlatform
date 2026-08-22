from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    require(database.is_file(), f"Database missing: {database}")

    previous = os.environ.get("CRYPTO_DATABASE_PATH")
    os.environ["CRYPTO_DATABASE_PATH"] = str(database)
    try:
        from crypto_platform.platform import load_all, connect
        from crypto_platform.module17 import MODULE17_SCHEMA
        from crypto_platform.module18 import MODULE18_SCHEMA
        from crypto_platform.module19 import MODULE19_SCHEMA

        settings, _ = load_all()
        conn = connect(settings)
        try:
            conn.execute(MODULE17_SCHEMA)
            conn.execute(MODULE18_SCHEMA)
            conn.execute(MODULE19_SCHEMA)

            registry = conn.execute(
                """
                SELECT feature_key, feature_class, source_type,
                       production_eligible, registry_status,
                       first_date, latest_date,
                       active_window_days, active_window_coverage_pct
                FROM latest_feature_registry
                ORDER BY registry_status, feature_key
                """
            ).fetchdf()

            warehouse = conn.execute(
                """
                SELECT MIN(observation_date) AS first_date,
                       MAX(observation_date) AS latest_date,
                       COUNT(*) AS rows
                FROM crypto_features_daily
                """
            ).fetchone()

            columns = [
                str(row[1])
                for row in conn.execute(
                    "PRAGMA table_info('crypto_features_daily')"
                ).fetchall()
            ]
        finally:
            conn.close()
    finally:
        if previous is None:
            os.environ.pop("CRYPTO_DATABASE_PATH", None)
        else:
            os.environ["CRYPTO_DATABASE_PATH"] = previous

    candidates = registry[
        (registry["production_eligible"] == True)
        & registry["registry_status"].isin(["PROMOTED_SHADOW", "WATCHLIST"])
    ].copy()

    candidate_rows = []
    for _, row in candidates.iterrows():
        key = str(row["feature_key"])
        candidate_rows.append({
            "feature_key": key,
            "feature_class": row["feature_class"],
            "source_type": row["source_type"],
            "registry_status": row["registry_status"],
            "first_date": row["first_date"],
            "latest_date": row["latest_date"],
            "active_window_days": None if row["active_window_days"] is None else int(row["active_window_days"]),
            "active_window_coverage_pct": None if row["active_window_coverage_pct"] is None else float(row["active_window_coverage_pct"]),
            "warehouse_column_present": key in columns,
        })

    payload = {
        "status": "COMPLETE",
        "audit_scope": "V2_NATIVE_FEATURE_CANDIDATE_CAPACITY_WITHOUT_V2_HOLDOUT_OUTCOMES",
        "v2_holdout_outcomes_viewed": False,
        "registry_performance_metrics_exposed": False,
        "candidate_rule": "production_eligible AND registry_status IN (PROMOTED_SHADOW, WATCHLIST)",
        "warehouse": {
            "first_date": warehouse[0],
            "latest_date": warehouse[1],
            "rows": int(warehouse[2] or 0),
        },
        "registry_rows": int(len(registry)),
        "candidate_features": candidate_rows,
        "candidate_feature_count": len(candidate_rows),
        "all_candidate_columns_present": all(r["warehouse_column_present"] for r in candidate_rows),
        "next_gate": "DEFINE_V2_NATIVE_FEATURE_AUGMENTED_DIRECTION_CHALLENGER" if candidate_rows else "REASSESS_V2_FEATURE_SOURCE_CAPACITY",
    }

    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_V2_NATIVE_FEATURE_CANDIDATE_CAPACITY_AUDIT=PASS")
    print("V2_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("REGISTRY_PERFORMANCE_METRICS_EXPOSED=FALSE")
    print(f"CANDIDATE_FEATURES={len(candidate_rows)}")
    print(f"ALL_CANDIDATE_COLUMNS_PRESENT={'TRUE' if payload['all_candidate_columns_present'] else 'FALSE'}")
    print(f"NEXT_GATE={payload['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
