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

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete Crypto production pipeline against a disposable copy of the recovered production database.")
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    args = parser.parse_args()

    source_database = args.source_database.resolve()
    source_repo = args.source_repo.resolve()
    if not source_database.is_file():
        raise RuntimeError(f"Source database not found: {source_database}")
    if not source_repo.is_dir():
        raise RuntimeError(f"Source repository not found: {source_repo}")

    source_hash_before = sha256(source_database)
    source_size_before = source_database.stat().st_size
    source_env = load_env_file(source_repo / ".env")

    with tempfile.TemporaryDirectory(prefix="crypto-r2-full-pipeline-") as temp_name:
        temp_root = Path(temp_name)
        disposable_db = temp_root / "crypto_intelligence.duckdb"
        output_root = temp_root / "production_runs"
        delivery_root = temp_root / "uip_delivery"
        readiness_path = temp_root / "hosted_readiness.json"
        shutil.copy2(source_database, disposable_db)

        env = os.environ.copy()
        for key in ("FRED_API_KEY", "COINGECKO_API_KEY", "COINGECKO_PRO_API_KEY"):
            if source_env.get(key):
                env[key] = source_env[key]
        env["CRYPTO_DATABASE_PATH"] = str(disposable_db)
        env.pop("CRYPTO_PRODUCTION_RUN_ID", None)
        env.pop("CRYPTO_PRODUCTION_STAGE", None)
        env.pop("CRYPTO_PRODUCTION_MODULE", None)

        pipeline = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_crypto_production_pipeline.py"),
                "--database",
                str(disposable_db),
                "--output-root",
                str(output_root),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        run_summaries = sorted(output_root.glob("*/run_summary.json"), key=lambda p: p.stat().st_mtime)
        run_summary_path = run_summaries[-1] if run_summaries else None
        run_summary = json.loads(run_summary_path.read_text(encoding="utf-8")) if run_summary_path else {}

        readiness = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "check_crypto_hosted_readiness.py"),
                "--database",
                str(disposable_db),
                "--output",
                str(readiness_path),
                "--strict",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        readiness_payload = json.loads(readiness_path.read_text(encoding="utf-8")) if readiness_path.is_file() else {}

        delivery = None
        delivery_return_code = None
        if run_summary_path is not None and run_summary.get("status") == "PASS":
            delivery_run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "prepare_crypto_uip_delivery.py"),
                    "--run-summary",
                    str(run_summary_path),
                    "--output-root",
                    str(delivery_root),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            delivery_return_code = int(delivery_run.returncode)
            latest_path = delivery_root / "latest.json"
            if latest_path.is_file():
                latest = json.loads(latest_path.read_text(encoding="utf-8"))
                manifest_path = Path(latest["manifest"])
                if manifest_path.is_file():
                    delivery = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            delivery_return_code = -1

        source_hash_after = sha256(source_database)
        source_size_after = source_database.stat().st_size
        source_unchanged = source_hash_before == source_hash_after and source_size_before == source_size_after
        if not source_unchanged:
            raise RuntimeError("Source Crypto production database changed during disposable full-pipeline rehearsal.")

        modules = run_summary.get("module_results") or []
        failed_modules = [m for m in modules if m.get("status") not in {"PASS", "RESUMED_PASS"}]
        export = run_summary.get("universal_export") or {}
        dataset_counts = export.get("dataset_counts") or {}

        pass_status = (
            pipeline.returncode == 0
            and run_summary.get("status") == "PASS"
            and not failed_modules
            and export.get("status") == "PASS"
            and readiness.returncode == 0
            and readiness_payload.get("status") == "PASS"
            and delivery_return_code == 0
            and isinstance(delivery, dict)
            and delivery.get("status") == "PASS"
            and int(dataset_counts.get("asset_master", -1)) == 6
            and int(dataset_counts.get("forecasts", -1)) == 132
            and int(dataset_counts.get("recommendations", -1)) == 6
            and int(dataset_counts.get("risk_metrics", -1)) == 6
            and int(dataset_counts.get("portfolio_positions", -1)) == 0
            and int(dataset_counts.get("platform_status", -1)) == 1
            and source_unchanged
        )

        payload = {
            "status": "CRYPTO_R2_DISPOSABLE_FULL_PIPELINE_PASS" if pass_status else "CRYPTO_R2_DISPOSABLE_FULL_PIPELINE_FAIL",
            "mode": "DISPOSABLE_DATABASE_COPY",
            "full_refresh": False,
            "source_database": str(source_database),
            "source_database_sha256": source_hash_before,
            "source_database_unchanged": source_unchanged,
            "source_env_present": (source_repo / ".env").is_file(),
            "fred_api_key_available": bool(source_env.get("FRED_API_KEY")),
            "coingecko_api_key_available": bool(source_env.get("COINGECKO_API_KEY")),
            "coingecko_pro_api_key_available": bool(source_env.get("COINGECKO_PRO_API_KEY")),
            "pipeline_return_code": int(pipeline.returncode),
            "pipeline_stdout_tail": (pipeline.stdout or "")[-12000:],
            "pipeline_stderr_tail": (pipeline.stderr or "")[-12000:],
            "run_id": run_summary.get("run_id"),
            "run_status": run_summary.get("status"),
            "module_count": len(modules),
            "failed_modules": failed_modules,
            "universal_export": export,
            "hosted_readiness_return_code": int(readiness.returncode),
            "hosted_readiness": readiness_payload,
            "uip_delivery_return_code": delivery_return_code,
            "uip_delivery": delivery,
            "next_gate": "UIP_R2_CRYPTO_IMPORT_REHEARSAL" if pass_status else "R2_CRYPTO_FULL_PIPELINE_INVESTIGATION",
        }

        print(json.dumps(payload, indent=2, sort_keys=True))
        print(f"CRYPTO_R2_DISPOSABLE_FULL_PIPELINE={'PASS' if pass_status else 'FAIL'}")
        print(f"SOURCE_DATABASE_UNCHANGED={str(source_unchanged).upper()}")
        print(f"NEXT_GATE={payload['next_gate']}")
        return 0 if pass_status else 1


if __name__ == "__main__":
    raise SystemExit(main())
