"""Build and inspect the first real universal crypto export package."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from crypto_platform.integration.universal import (
    ExportContext,
    UniversalPackageBuilder,
)


DATABASE_PATH = (
    ROOT
    / "data"
    / "crypto_intelligence.duckdb"
).resolve()

OUTPUT_DIRECTORY = (
    ROOT
    / "data"
    / "exports"
    / "universal"
    / "crypto_validation_001"
).resolve()

RUN_ID = (
    "crypto-universal-export-validation-001"
)


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Source database not found: {DATABASE_PATH}"
        )

    if OUTPUT_DIRECTORY.exists():
        if any(OUTPUT_DIRECTORY.iterdir()):
            raise FileExistsError(
                "Validation output already exists and "
                "is not empty. Remove it before rerunning: "
                f"{OUTPUT_DIRECTORY}"
            )

    context = ExportContext.create(
        source_database=DATABASE_PATH,
        output_directory=OUTPUT_DIRECTORY,
        run_id=RUN_ID,
        generated_at_utc=datetime.now(
            timezone.utc
        ),
    )

    result = UniversalPackageBuilder(
        context
    ).build()

    expected_files = {
        "asset_master.csv",
        "forecasts.csv",
        "platform_status.csv",
        "portfolio_positions.csv",
        "recommendations.csv",
        "risk_metrics.csv",
        "export_manifest.csv",
        "package_summary.json",
        "validation_report.json",
    }

    actual_files = {
        path.name
        for path in OUTPUT_DIRECTORY.iterdir()
        if path.is_file()
    }

    missing_files = sorted(
        expected_files - actual_files
    )

    unexpected_files = sorted(
        actual_files - expected_files
    )

    if missing_files:
        raise RuntimeError(
            "Package is missing required files: "
            + ", ".join(missing_files)
        )

    if unexpected_files:
        raise RuntimeError(
            "Package contains unexpected files: "
            + ", ".join(unexpected_files)
        )

    summary = json.loads(
        (
            OUTPUT_DIRECTORY
            / "package_summary.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    validation = json.loads(
        (
            OUTPUT_DIRECTORY
            / "validation_report.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    if summary["status"] != "PASS":
        raise RuntimeError(
            "Package summary status is not PASS."
        )

    if validation["status"] != "PASS":
        raise RuntimeError(
            "Validation report status is not PASS."
        )

    if summary["holdings_available"] is not False:
        raise RuntimeError(
            "Package incorrectly reports holdings."
        )

    if validation["holdings_available"] is not False:
        raise RuntimeError(
            "Validation incorrectly reports holdings."
        )

    print(
        "PASS: Real universal crypto package built."
    )

    print()
    print(f"Run ID: {result.run_id}")
    print(f"Output: {result.output_directory}")

    print()
    print("Dataset counts:")

    for name, count in sorted(
        result.dataset_counts.items()
    ):
        print(f"- {name}: {count}")

    print()
    print(
        "Manifest records: "
        f"{result.manifest_count}"
    )

    print()
    print("Files:")

    for name in sorted(actual_files):
        path = OUTPUT_DIRECTORY / name

        print(
            f"- {name}: "
            f"{path.stat().st_size} bytes"
        )


if __name__ == "__main__":
    main()