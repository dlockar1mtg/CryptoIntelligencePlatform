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

    with tempfile.TemporaryDirectory(prefix="crypto_m39_true_replay_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        prior = os.environ.get("CRYPTO_DATABASE_PATH")
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.module38 import run_module38
            from crypto_platform.module39 import run_module39

            module38_result = run_module38()
            require(
                int(module38_result["forecast_rows"]) == 30,
                f"Disposable remediated Module 38 produced {module38_result['forecast_rows']} forecasts; expected 30",
            )
            result = run_module39()
        finally:
            if prior is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior

        with duckdb.connect(str(temp_db), read_only=True) as con:
            latest_m38 = con.execute(
                "SELECT run_id, forecast_rows, recommendation, mean_validation_mae_pct "
                "FROM module38_runs WHERE status='SUCCESS' "
                "ORDER BY started_at_utc DESC LIMIT 1"
            ).fetchone()
            require(latest_m38 is not None, "Disposable remediated Module 38 did not finish successfully")

            latest = con.execute(
                "SELECT run_id, validation_status, recommendation, "
                "mean_calibrated_brier, mean_interval_coverage_pct, "
                "mean_directional_accuracy_pct FROM module39_runs "
                "WHERE status='SUCCESS' ORDER BY started_at_utc DESC LIMIT 1"
            ).fetchone()
            require(latest is not None, "Disposable Module 39 did not finish successfully")
            run_id = str(latest[0])
            validation_status = str(latest[1])
            advancement_recommendation = str(latest[2])
            calibration_rows = con.execute(
                "SELECT COUNT(*) FROM m39_probability_calibration WHERE run_id=?",
                [run_id],
            ).fetchone()[0]
            supported_calibration = con.execute(
                "SELECT COUNT(*) FROM m39_probability_calibration "
                "WHERE run_id=? AND validation_rows>0",
                [run_id],
            ).fetchone()[0]
            gap_calibration = con.execute(
                "SELECT COUNT(*) FROM m39_probability_calibration "
                "WHERE run_id=? AND calibration_method='UNCALIBRATED_EVIDENCE_GAP'",
                [run_id],
            ).fetchone()[0]
            rolling_rows = con.execute(
                "SELECT COUNT(*) FROM m39_rolling_origin_validation WHERE run_id=?",
                [run_id],
            ).fetchone()[0]
            gap_rows = con.execute(
                "SELECT asset_id,horizon_days,evidence_gap,available_candidates,required_candidates "
                "FROM m39_evidence_gaps WHERE run_id=? ORDER BY asset_id,horizon_days",
                [run_id],
            ).fetchall()
            bad_dates = con.execute(
                "SELECT COUNT(*) FROM m39_rolling_origin_validation "
                "WHERE run_id=? AND NOT training_end_date < testing_start_date",
                [run_id],
            ).fetchone()[0]

        require(int(latest_m38[1]) == 30, f"Expected refreshed Module 38 forecast_rows=30, got {latest_m38[1]}")
        require(int(calibration_rows) == 30, f"Expected 30 current calibration rows, got {calibration_rows}")
        require(int(supported_calibration) == 29, f"Expected 29 supported calibration rows, got {supported_calibration}")
        require(int(gap_calibration) == 1, f"Expected one uncalibrated evidence-gap forecast, got {gap_calibration}")
        require(int(rolling_rows) == 87, f"Expected 87 true rolling rows, got {rolling_rows}")
        require(len(gap_rows) == 1, f"Expected one explicit evidence gap, got {len(gap_rows)}")
        require(str(gap_rows[0][0]) == "xrp" and int(gap_rows[0][1]) == 365,
                f"Unexpected evidence gap: {gap_rows[0]}")
        require(int(bad_dates) == 0, f"Found {bad_dates} rolling rows with invalid chronology")

    after = sha256(source)
    require(before == after, "Source database changed during disposable Module 38/39 validation")

    payload = {
        "status": "CRYPTO_MODULE39_TRUE_REPLAY_DISPOSABLE_VALIDATION_COMPLETE",
        "source_database_unchanged": True,
        "module38_result": module38_result,
        "module39_result": result,
        "validation_status": validation_status,
        "advancement_recommendation": advancement_recommendation,
        "calibration_rows": int(calibration_rows),
        "supported_calibration_rows": int(supported_calibration),
        "uncalibrated_evidence_gap_rows": int(gap_calibration),
        "rolling_origin_rows": int(rolling_rows),
        "evidence_gaps": [
            {
                "asset_id": row[0],
                "horizon_days": int(row[1]),
                "evidence_gap": row[2],
                "available_candidates": int(row[3]),
                "required_candidates": int(row[4]),
            }
            for row in gap_rows
        ],
        "invalid_chronology_rows": int(bad_dates),
    }
    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_MODULE39_TRUE_REPLAY_DISPOSABLE_VALIDATION=PASS")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("REFRESHED_MODULE38_FORECAST_ROWS=30")
    print("SUPPORTED_CALIBRATION_GROUPS=29")
    print("EXPLICIT_EVIDENCE_GAPS=1")
    print("TRUE_ROLLING_ROWS=87")
    print("NEXT_GATE=INTERPRET_MODULE39_RUNTIME_AND_CHECKPOINT_SOURCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
