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


def run_inventory(con: duckdb.DuckDBPyConnection, limit: int = 12) -> list[dict]:
    runs = con.execute(
        """
        SELECT run_id, started_at_utc, completed_at_utc, status, forecast_rows,
               mean_validation_mae_pct, recommendation
        FROM module38_runs
        WHERE status='SUCCESS'
        ORDER BY started_at_utc DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    out = []
    for row in runs:
        run_id = str(row[0])
        horizons = [
            int(r[0])
            for r in con.execute(
                "SELECT DISTINCT horizon_days FROM m38_model_validation WHERE run_id=? ORDER BY 1",
                [run_id],
            ).fetchall()
        ]
        counts = [
            {
                "horizon_days": int(r[0]),
                "model_rows": int(r[1]),
                "assets": int(r[2]),
                "mean_mae_pct": float(r[3]),
                "mean_rmse_pct": float(r[4]),
                "mean_directional_accuracy_pct": float(r[5]),
            }
            for r in con.execute(
                """
                SELECT horizon_days, COUNT(*) AS model_rows,
                       COUNT(DISTINCT asset_id) AS assets,
                       AVG(validation_mae_pct), AVG(validation_rmse_pct),
                       AVG(directional_accuracy_pct)
                FROM m38_model_validation
                WHERE run_id=?
                GROUP BY horizon_days ORDER BY horizon_days
                """,
                [run_id],
            ).fetchall()
        ]
        out.append({
            "run_id": run_id,
            "started_at_utc": str(row[1]),
            "completed_at_utc": str(row[2]),
            "forecast_rows": int(row[4]),
            "mean_validation_mae_pct": None if row[5] is None else float(row[5]),
            "recommendation": None if row[6] is None else str(row[6]),
            "horizons": horizons,
            "horizon_rollup": counts,
        })
    return out


def detailed_validation(con: duckdb.DuckDBPyConnection, run_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT asset_id, horizon_days, model_key, validation_rows,
               validation_mae_pct, validation_rmse_pct,
               directional_accuracy_pct
        FROM m38_model_validation
        WHERE run_id=?
        ORDER BY horizon_days, validation_mae_pct DESC, asset_id, model_key
        """,
        [run_id],
    ).fetchall()
    return [
        {
            "asset_id": str(r[0]),
            "horizon_days": int(r[1]),
            "model_key": str(r[2]),
            "validation_rows": int(r[3]),
            "validation_mae_pct": float(r[4]),
            "validation_rmse_pct": float(r[5]),
            "directional_accuracy_pct": float(r[6]),
        }
        for r in rows
    ]


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
    configured_horizons = [int(v) for v in settings["module38"]["horizons_days"]]
    source_hash_before = sha256(source_db)

    with duckdb.connect(str(source_db), read_only=True) as con:
        source_runs = run_inventory(con)

    with tempfile.TemporaryDirectory(prefix="crypto-m38-diagnostic-") as tmp:
        disposable_db = Path(tmp) / source_db.name
        shutil.copy2(source_db, disposable_db)
        env = os.environ.copy()
        env["CRYPTO_DATABASE_PATH"] = str(disposable_db)
        proc = subprocess.run(
            [sys.executable, "run_module38.py"],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
        )
        print("MODULE38_DIAGNOSTIC_STDOUT_BEGIN")
        print(proc.stdout.rstrip())
        print("MODULE38_DIAGNOSTIC_STDOUT_END")
        if proc.stderr.strip():
            print("MODULE38_DIAGNOSTIC_STDERR_BEGIN")
            print(proc.stderr.rstrip())
            print("MODULE38_DIAGNOSTIC_STDERR_END")
        require(proc.returncode == 0, f"Disposable Module 38 diagnostic run failed: {proc.returncode}")

        with duckdb.connect(str(disposable_db), read_only=True) as con:
            corrected_run_id = str(
                con.execute(
                    "SELECT run_id FROM module38_runs WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1"
                ).fetchone()[0]
            )
            corrected_horizons = [
                int(r[0])
                for r in con.execute(
                    "SELECT DISTINCT horizon_days FROM m38_model_validation WHERE run_id=? ORDER BY 1",
                    [corrected_run_id],
                ).fetchall()
            ]
            corrected_detail = detailed_validation(con, corrected_run_id)
            corrected_rollup = run_inventory(con, 1)[0]

    source_hash_after = sha256(source_db)
    require(source_hash_before == source_hash_after, "Source Crypto database changed during diagnostic")

    prior_latest_horizons = source_runs[0]["horizons"] if source_runs else []
    payload = {
        "status": "CRYPTO_MODULE38_HORIZON_MISMATCH_DIAGNOSTIC_COMPLETE",
        "source_commit": args.source_commit,
        "source_database_unchanged": True,
        "configured_module38_horizons": configured_horizons,
        "latest_source_run_horizons": prior_latest_horizons,
        "corrected_disposable_horizons": corrected_horizons,
        "source_recent_successful_runs": source_runs,
        "corrected_disposable_run": corrected_rollup,
        "corrected_validation_detail": corrected_detail,
        "horizon_set_matches_config": corrected_horizons == configured_horizons,
        "latest_source_horizon_set_matches_config": prior_latest_horizons == configured_horizons,
        "next_gate": "REPAIR_COMPARISON_BASELINE_SELECTION_OR_INVESTIGATE_CORRECTED_HORIZON_COVERAGE",
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_MODULE38_HORIZON_MISMATCH_DIAGNOSTIC=COMPLETE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
