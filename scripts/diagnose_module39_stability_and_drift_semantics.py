from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    require(source.is_file(), f"Database missing: {source}")
    before = sha256(source)

    with tempfile.TemporaryDirectory(prefix="crypto_m39_semantics_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.module38 import run_module38
            from crypto_platform.module39 import run_module39

            m38_result = run_module38()
            require(int(m38_result["forecast_rows"]) == 30, "Expected remediated Module 38 to produce 30 forecasts")
            m39_result = run_module39()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

        with duckdb.connect(str(temp_db), read_only=True) as con:
            runs = con.execute(
                """
                SELECT run_id, started_at_utc, forecast_rows, horizons_completed,
                       assets_completed, mean_validation_mae_pct, recommendation,
                       platform_version
                FROM module38_runs
                WHERE status='SUCCESS'
                ORDER BY started_at_utc DESC
                LIMIT 8
                """
            ).fetchall()

            latest_m39 = con.execute(
                """
                SELECT run_id, validation_status, recommendation,
                       stable_feature_pct, current_drift_status,
                       mean_directional_accuracy_pct, mean_calibrated_brier
                FROM m39_validation_summary s
                JOIN module39_runs r USING(run_id)
                WHERE r.status='SUCCESS'
                ORDER BY r.started_at_utc DESC LIMIT 1
                """
            ).fetchone()
            require(latest_m39 is not None, "No successful disposable Module 39 run found")
            m39_run_id = str(latest_m39[0])

            stability = con.execute(
                """
                SELECT stability_grade, folds, COUNT(*) AS rows,
                       MIN(stability_score), MAX(stability_score), AVG(stability_score)
                FROM m39_feature_stability
                WHERE run_id=?
                GROUP BY stability_grade, folds
                ORDER BY folds, stability_grade
                """,
                [m39_run_id],
            ).fetchall()

            attribution_current = con.execute(
                """
                SELECT COUNT(*) AS rows,
                       COUNT(DISTINCT forecast_date) AS forecast_dates,
                       COUNT(DISTINCT run_id) AS runs,
                       COUNT(DISTINCT asset_id || ':' || CAST(horizon_days AS VARCHAR) || ':' || driver_key) AS groups
                FROM m38_forecast_attribution
                WHERE run_id=(SELECT source_module38_run_id FROM module39_runs WHERE run_id=?)
                """,
                [m39_run_id],
            ).fetchone()

            attribution_history = con.execute(
                """
                SELECT COUNT(*) AS rows,
                       COUNT(DISTINCT forecast_date) AS forecast_dates,
                       COUNT(DISTINCT run_id) AS runs,
                       MIN(forecast_date), MAX(forecast_date)
                FROM m38_forecast_attribution
                """
            ).fetchone()

            snapshot_distribution = con.execute(
                """
                SELECT snapshots, COUNT(*) AS groups
                FROM (
                    SELECT asset_id,horizon_days,driver_key,
                           COUNT(DISTINCT forecast_date) AS snapshots
                    FROM m38_forecast_attribution
                    GROUP BY asset_id,horizon_days,driver_key
                ) q
                GROUP BY snapshots
                ORDER BY snapshots
                """
            ).fetchall()

            drift_rows = con.execute(
                """
                SELECT asset_id,horizon_days,current_forecast_date,prior_forecast_date,
                       return_forecast_change_pct,probability_change,confidence_change,
                       interval_width_change_pct,model_weight_distance,
                       attribution_rank_change,drift_score,drift_status
                FROM m39_forecast_drift
                WHERE run_id=?
                ORDER BY drift_score DESC,asset_id,horizon_days
                """,
                [m39_run_id],
            ).fetchall()

            current_m38_id = con.execute(
                "SELECT source_module38_run_id FROM module39_runs WHERE run_id=?",
                [m39_run_id],
            ).fetchone()[0]

            prior_coverage = con.execute(
                """
                WITH previous AS (
                    SELECT run_id, started_at_utc, forecast_rows, horizons_completed,
                           assets_completed, mean_validation_mae_pct, recommendation,
                           platform_version
                    FROM module38_runs
                    WHERE status='SUCCESS' AND run_id<>?
                    ORDER BY started_at_utc DESC
                    LIMIT 1
                )
                SELECT p.run_id,p.started_at_utc,p.forecast_rows,p.horizons_completed,
                       p.assets_completed,p.mean_validation_mae_pct,p.recommendation,
                       p.platform_version,
                       COUNT(DISTINCT f.horizon_days) AS actual_horizons,
                       STRING_AGG(DISTINCT CAST(f.horizon_days AS VARCHAR), ',' ORDER BY CAST(f.horizon_days AS VARCHAR)) AS horizon_values
                FROM previous p
                LEFT JOIN m38_asset_forecasts f ON f.run_id=p.run_id
                GROUP BY ALL
                """,
                [current_m38_id],
            ).fetchone()

    after = sha256(source)
    require(before == after, "Source database changed during semantics diagnostic")

    critical = [row for row in drift_rows if str(row[-1]) == "CRITICAL"]
    warning = [row for row in drift_rows if str(row[-1]) == "WARNING"]
    stable = [row for row in drift_rows if str(row[-1]) == "STABLE"]

    payload = {
        "status": "CRYPTO_MODULE39_STABILITY_AND_DRIFT_SEMANTICS_DIAGNOSTIC_COMPLETE",
        "source_database_unchanged": True,
        "module38_result": m38_result,
        "module39_result": m39_result,
        "recent_module38_runs": [
            {
                "run_id": row[0],
                "started_at_utc": row[1],
                "forecast_rows": row[2],
                "horizons_completed": row[3],
                "assets_completed": row[4],
                "mean_validation_mae_pct": row[5],
                "recommendation": row[6],
                "platform_version": row[7],
            }
            for row in runs
        ],
        "latest_module39_summary": {
            "run_id": latest_m39[0],
            "validation_status": latest_m39[1],
            "recommendation": latest_m39[2],
            "stable_feature_pct": latest_m39[3],
            "current_drift_status": latest_m39[4],
            "mean_directional_accuracy_pct": latest_m39[5],
            "mean_calibrated_brier": latest_m39[6],
        },
        "stability_grade_distribution": [
            {
                "stability_grade": row[0],
                "folds": int(row[1]),
                "rows": int(row[2]),
                "min_score": float(row[3]),
                "max_score": float(row[4]),
                "mean_score": float(row[5]),
            }
            for row in stability
        ],
        "current_attribution_evidence": {
            "rows": int(attribution_current[0]),
            "forecast_dates": int(attribution_current[1]),
            "runs": int(attribution_current[2]),
            "asset_horizon_driver_groups": int(attribution_current[3]),
        },
        "all_attribution_history": {
            "rows": int(attribution_history[0]),
            "forecast_dates": int(attribution_history[1]),
            "runs": int(attribution_history[2]),
            "first_forecast_date": attribution_history[3],
            "last_forecast_date": attribution_history[4],
            "snapshot_count_distribution": [
                {"snapshots": int(row[0]), "groups": int(row[1])}
                for row in snapshot_distribution
            ],
        },
        "prior_module38_coverage": None if prior_coverage is None else {
            "run_id": prior_coverage[0],
            "started_at_utc": prior_coverage[1],
            "forecast_rows": prior_coverage[2],
            "horizons_completed": prior_coverage[3],
            "assets_completed": prior_coverage[4],
            "mean_validation_mae_pct": prior_coverage[5],
            "recommendation": prior_coverage[6],
            "platform_version": prior_coverage[7],
            "actual_horizons": prior_coverage[8],
            "horizon_values": prior_coverage[9],
        },
        "drift_counts": {
            "critical": len(critical),
            "warning": len(warning),
            "stable": len(stable),
            "total": len(drift_rows),
        },
        "critical_drift_rows": [
            {
                "asset_id": row[0],
                "horizon_days": int(row[1]),
                "current_forecast_date": row[2],
                "prior_forecast_date": row[3],
                "return_forecast_change_pct": float(row[4]),
                "probability_change": float(row[5]),
                "confidence_change": float(row[6]),
                "interval_width_change_pct": float(row[7]),
                "model_weight_distance": float(row[8]),
                "attribution_rank_change": float(row[9]),
                "drift_score": float(row[10]),
                "drift_status": row[11],
            }
            for row in critical
        ],
    }
    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_MODULE39_STABILITY_AND_DRIFT_SEMANTICS_DIAGNOSTIC=COMPLETE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"STABILITY_EVIDENCE_ROWS={sum(int(row[2]) for row in stability)}")
    print(f"CRITICAL_DRIFT_ROWS={len(critical)}")
    print("NEXT_GATE=INTERPRET_STABILITY_AND_DRIFT_SEMANTICS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
