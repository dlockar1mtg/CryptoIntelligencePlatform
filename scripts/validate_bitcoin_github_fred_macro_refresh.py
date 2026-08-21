from __future__ import annotations

import argparse
import json
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    workflow = Path(args.workflow).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()

    for path in (runner, workflow, manifest):
        require(path.is_file(), f"Required validation input missing: {path}")

    manifest_json = json.loads(manifest.read_text(encoding="utf-8"))
    require(int(manifest_json.get("record_count", -1)) == 0, "Ledger manifest is not empty")
    records = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(records) == 0, "Ledger record files already exist")

    runner_text = runner.read_text(encoding="utf-8")
    workflow_text = workflow.read_text(encoding="utf-8")

    for fragment in (
        '[sys.executable, "run_module1.py"]',
        '[sys.executable, "run_module6.py", "--phase", "sync"]',
        '"--full-refresh" not in module1["command"]',
        'FRED_API_KEY is not available in the GitHub execution environment',
        '"module42_rerun_performed": False',
        '"first_prospective_observation_captured": False',
        '"production_pipeline_executed": False',
        '"fred_api_key_value_recorded": False',
        '"ledger_record_count": 0',
    ):
        require(fragment in runner_text, f"Runner missing required control: {fragment}")

    for fragment in (
        "FRED_API_KEY: ${{ secrets.FRED_API_KEY }}",
        "COINGECKO_API_KEY: ${{ secrets.COINGECKO_API_KEY }}",
        "environment: staging",
        "python scripts/run_bitcoin_github_fred_macro_refresh.py",
        "actions/upload-artifact@v4",
        "github_fred_macro_refresh_trigger_v1.txt",
    ):
        require(fragment in workflow_text, f"Workflow missing required control: {fragment}")

    require("run_crypto_production_pipeline.py" not in workflow_text, "Full production pipeline is present in narrow macro workflow")
    require("run_module42" not in workflow_text.lower(), "Module42 is present in narrow macro workflow")
    require("--full-refresh" not in workflow_text, "Full-refresh flag is present in narrow macro workflow")

    print("BITCOIN_GITHUB_FRED_MACRO_REFRESH_VALIDATION=PASS")
    print("STAGING_SECRET_FRED_MAPPING_REQUIRED=TRUE")
    print("MODULE1_INCREMENTAL_ONLY=TRUE")
    print("MODULE1_FULL_REFRESH_AUTHORIZED=FALSE")
    print("MODULE6_SYNC_ONLY=TRUE")
    print("MODULE42_RERUN_AUTHORIZED=FALSE")
    print("PRODUCTION_PIPELINE_EXECUTION_AUTHORIZED=FALSE")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("LEDGER_RECORD_COUNT=0")
    print("NEXT_GATE=TRIGGER_GITHUB_FRED_MACRO_REFRESH_ONCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
