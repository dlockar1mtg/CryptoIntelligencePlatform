from __future__ import annotations

import argparse
import hashlib
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

    with tempfile.TemporaryDirectory(prefix="crypto_m39_generation_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.module38 import (
                PREDICTIVE_METHODOLOGY_GENERATION,
                run_module38,
            )
            from crypto_platform.module39 import run_module39

            m38_result = run_module38()
            require(int(m38_result["forecast_rows"]) == 30, "Expected 30 remediated Module 38 forecasts")
            m39_result = run_module39()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

        with duckdb.connect(str(temp_db), read_only=True) as con:
            latest_m38 = con.execute(
                """
                SELECT run_id, methodology_generation
                FROM module38_runs
                WHERE status='SUCCESS'
                ORDER BY started_at_utc DESC LIMIT 1
                """
            ).fetchone()
            require(latest_m38 is not None, "No successful disposable Module 38 run")
            require(str(latest_m38[1]) == PREDICTIVE_METHODOLOGY_GENERATION, "Latest Module 38 generation was not persisted")

            legacy_tagged = con.execute(
                """
                SELECT COUNT(*)
                FROM module38_runs
                WHERE run_id<>? AND methodology_generation IS NOT NULL
                """,
                [latest_m38[0]],
            ).fetchone()[0]
            require(int(legacy_tagged) == 0, "Legacy Module 38 runs were unexpectedly assigned the new generation")

            latest_m39 = con.execute(
                """
                SELECT s.run_id, s.stable_feature_pct, s.current_drift_status,
                       s.validation_status, s.advancement_recommendation
                FROM m39_validation_summary s
                JOIN module39_runs r USING(run_id)
                WHERE r.status='SUCCESS'
                ORDER BY r.started_at_utc DESC LIMIT 1
                """
            ).fetchone()
            require(latest_m39 is not None, "No successful disposable Module 39 run")
            require(latest_m39[1] is None, "Insufficient stability evidence must remain NULL/missing")
            require(str(latest_m39[2]) == "BASELINE_REQUIRED", "Expected BASELINE_REQUIRED drift status")
            require(str(latest_m39[3]) != "PASSED", "Generation semantics repair must not auto-certify predictive skill")

            drift_counts = con.execute(
                """
                SELECT drift_status, COUNT(*)
                FROM m39_forecast_drift
                WHERE run_id=?
                GROUP BY drift_status
                ORDER BY drift_status
                """,
                [latest_m39[0]],
            ).fetchall()
            require(drift_counts == [("BASELINE_REQUIRED", 30)], f"Unexpected drift status distribution: {drift_counts}")

            stability = con.execute(
                """
                SELECT MIN(folds), MAX(folds), COUNT(*),
                       COUNT(DISTINCT stability_grade)
                FROM m39_feature_stability
                WHERE run_id=?
                """,
                [latest_m39[0]],
            ).fetchone()
            require(int(stability[0]) == 1 and int(stability[1]) == 1, "First-generation stability should have one independent forecast-date snapshot")
            require(int(stability[2]) == 270, "Expected 270 stability rows")

    after = sha256(source)
    require(before == after, "Source database changed during disposable generation semantics validation")

    print("CRYPTO_MODULE39_GENERATION_AWARE_DISPOSABLE_VALIDATION=PASS")
    print("METHODOLOGY_GENERATION_PERSISTED=TRUE")
    print("LEGACY_RUNS_REMAIN_UNTAGGED=TRUE")
    print("STABLE_FEATURE_PCT=MISSING_INSUFFICIENT_EVIDENCE")
    print("CURRENT_DRIFT_STATUS=BASELINE_REQUIRED")
    print("BASELINE_REQUIRED_DRIFT_ROWS=30")
    print("INDEPENDENT_STABILITY_SNAPSHOTS=1")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("PREDICTIVE_SKILL_AUTO_CERTIFIED=FALSE")
    print("NEXT_GATE=CHECKPOINT_GENERATION_AWARE_SEMANTICS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
