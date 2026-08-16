from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb
import yaml

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def latest_run_id(con: duckdb.DuckDBPyConnection) -> str:
    row = con.execute(
        "SELECT run_id FROM module38_runs WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1"
    ).fetchone()
    require(row is not None, "No successful Module 38 run found")
    return str(row[0])


def validation_rollup(con: duckdb.DuckDBPyConnection, run_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT horizon_days,
               COUNT(*) AS model_rows,
               COUNT(DISTINCT asset_id) AS assets,
               AVG(validation_mae_pct) AS mean_mae_pct,
               AVG(validation_rmse_pct) AS mean_rmse_pct,
               AVG(directional_accuracy_pct) AS mean_directional_accuracy_pct,
               MIN(validation_rows) AS min_validation_rows,
               MAX(validation_rows) AS max_validation_rows
        FROM m38_model_validation
        WHERE run_id=?
        GROUP BY horizon_days
        ORDER BY horizon_days
        """,
        [run_id],
    ).fetchall()
    return [
        {
            "horizon_days": int(r[0]),
            "model_rows": int(r[1]),
            "assets": int(r[2]),
            "mean_mae_pct": float(r[3]),
            "mean_rmse_pct": float(r[4]),
            "mean_directional_accuracy_pct": float(r[5]),
            "min_validation_rows": int(r[6]),
            "max_validation_rows": int(r[7]),
        }
        for r in rows
    ]


def run_summary(con: duckdb.DuckDBPyConnection, run_id: str) -> dict:
    row = con.execute(
        """
        SELECT status, forecast_rows, mean_validation_mae_pct,
               forecast_risk_status, recommendation
        FROM module38_runs
        WHERE run_id=?
        """,
        [run_id],
    ).fetchone()
    require(row is not None, f"Missing Module 38 run summary: {run_id}")
    return {
        "run_id": run_id,
        "status": str(row[0]),
        "forecast_rows": int(row[1]),
        "mean_validation_mae_pct": float(row[2]),
        "forecast_risk_status": str(row[3]),
        "recommendation": str(row[4]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    require(args.source_commit == EXPECTED_SOURCE_COMMIT, "Unexpected certified source commit")

    root = Path(__file__).resolve().parents[1]
    source_db = Path(args.database).resolve()
    require(source_db.is_file(), f"Crypto database missing: {source_db}")

    settings = yaml.safe_load((root / "config" / "settings.yaml").read_text(encoding="utf-8"))
    configured_horizons = {int(v) for v in settings["module38"]["horizons_days"]}

    source_hash_before = sha256(source_db)
    with duckdb.connect(str(source_db), read_only=True) as source_con:
        prior_run_id = latest_run_id(source_con)
        prior_summary = run_summary(source_con, prior_run_id)
        prior_rollup = validation_rollup(source_con, prior_run_id)

    with tempfile.TemporaryDirectory(prefix="crypto-m38-purged-") as tmp:
        disposable_db = Path(tmp) / source_db.name
        shutil.copy2(source_db, disposable_db)
        disposable_hash_before = sha256(disposable_db)
        require(disposable_hash_before == source_hash_before, "Disposable database copy hash mismatch")

        env = os.environ.copy()
        env["CRYPTO_DATABASE_PATH"] = str(disposable_db)
        proc = subprocess.run(
            [sys.executable, "run_module38.py"],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
        )
        print("MODULE38_DISPOSABLE_STDOUT_BEGIN")
        print(proc.stdout.rstrip())
        print("MODULE38_DISPOSABLE_STDOUT_END")
        if proc.stderr.strip():
            print("MODULE38_DISPOSABLE_STDERR_BEGIN")
            print(proc.stderr.rstrip())
            print("MODULE38_DISPOSABLE_STDERR_END")
        require(proc.returncode == 0, f"Disposable Module 38 run failed with exit code {proc.returncode}")

        with duckdb.connect(str(disposable_db), read_only=True) as disposable_con:
            corrected_run_id = latest_run_id(disposable_con)
            require(corrected_run_id != prior_run_id, "Disposable Module 38 run did not create a new successful run")
            corrected_summary = run_summary(disposable_con, corrected_run_id)
            corrected_rollup = validation_rollup(disposable_con, corrected_run_id)

        prior_by_h = {r["horizon_days"]: r for r in prior_rollup}
        corrected_by_h = {r["horizon_days"]: r for r in corrected_rollup}
        prior_horizons = set(prior_by_h)
        corrected_horizons = set(corrected_by_h)

        require(
            corrected_horizons == configured_horizons,
            "Corrected validation horizon set does not match configured Module 38 horizons",
        )

        comparison = []
        for horizon in sorted(prior_horizons & corrected_horizons):
            old = prior_by_h[horizon]
            new = corrected_by_h[horizon]
            require(new["assets"] == 6, f"Corrected asset coverage is incomplete for horizon {horizon}")
            require(new["model_rows"] == 18, f"Corrected model-row coverage is incomplete for horizon {horizon}")
            comparison.append({
                "horizon_days": horizon,
                "prior_mean_mae_pct": old["mean_mae_pct"],
                "corrected_mean_mae_pct": new["mean_mae_pct"],
                "mae_change_pct_points": new["mean_mae_pct"] - old["mean_mae_pct"],
                "prior_mean_rmse_pct": old["mean_rmse_pct"],
                "corrected_mean_rmse_pct": new["mean_rmse_pct"],
                "rmse_change_pct_points": new["mean_rmse_pct"] - old["mean_rmse_pct"],
                "prior_directional_accuracy_pct": old["mean_directional_accuracy_pct"],
                "corrected_directional_accuracy_pct": new["mean_directional_accuracy_pct"],
                "directional_change_pct_points": new["mean_directional_accuracy_pct"] - old["mean_directional_accuracy_pct"],
                "validation_rows": [new["min_validation_rows"], new["max_validation_rows"]],
            })

        restored_or_new = [corrected_by_h[h] for h in sorted(corrected_horizons - prior_horizons)]
        missing_from_corrected = sorted(configured_horizons - corrected_horizons)

    source_hash_after = sha256(source_db)
    require(source_hash_before == source_hash_after, "Source Crypto database changed during disposable rehearsal")

    payload = {
        "status": "CRYPTO_MODULE38_PURGED_DISPOSABLE_VALIDATION_COMPLETE",
        "source_commit": args.source_commit,
        "source_database_unchanged": True,
        "source_database_sha256": source_hash_before,
        "configured_horizons": sorted(configured_horizons),
        "prior_horizons": sorted(prior_horizons),
        "corrected_horizons": sorted(corrected_horizons),
        "prior_run": prior_summary,
        "corrected_disposable_run": corrected_summary,
        "common_horizon_comparison": comparison,
        "restored_or_new_horizons": restored_or_new,
        "missing_from_corrected": missing_from_corrected,
        "interpretation_guard": "Corrected Module 38 holdout metrics are diagnostic evidence only. Predictive skill remains uncertified until Module 39 true rolling-origin and realized-outcome calibration remediation are complete.",
        "next_gate": "INTERPRET_PURGED_HOLDOUT_IMPACT_THEN_REMEDIATE_MODULE39",
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_MODULE38_PURGED_DISPOSABLE_VALIDATION=COMPLETE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("CORRECTED_HORIZONS_MATCH_CONFIG=TRUE")
    print("NEXT_GATE=INTERPRET_PURGED_HOLDOUT_IMPACT_THEN_REMEDIATE_MODULE39")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
