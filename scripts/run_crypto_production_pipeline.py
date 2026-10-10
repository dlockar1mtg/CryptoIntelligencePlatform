"""CLI for the governed Crypto production pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.production import PipelineOptions, ProductionOrchestrator, ProductionStage


def _parse_stages(value: str) -> tuple[ProductionStage, ...]:
    if value.strip().lower() == "all":
        return tuple(ProductionStage)
    requested = [item.strip() for item in value.split(",") if item.strip()]
    try:
        return tuple(ProductionStage(item) for item in requested)
    except ValueError as exc:
        valid = ", ".join(stage.value for stage in ProductionStage)
        raise argparse.ArgumentTypeError(f"Unknown stage. Valid values: {valid}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the governed Crypto production pipeline.")
    parser.add_argument("--stages", default="all", type=_parse_stages)
    parser.add_argument("--start-module", type=int)
    parser.add_argument("--end-module", type=int)
    parser.add_argument("--full-refresh", action="store_true")
    parser.add_argument("--skip-coingecko", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument("--database", type=Path)
    parser.add_argument(
        "--weekly-research",
        action="store_true",
        help=(
            "Run research-only modules (which the UIP delivery does not read) only on a "
            "full refresh, or when their last successful run is missing or over 7 days old. "
            "Skipped modules are recorded as SKIPPED_WEEKLY."
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data" / "operations" / "crypto" / "production_runs",
    )
    args = parser.parse_args()

    options = PipelineOptions(
        repository_root=ROOT,
        output_root=args.output_root,
        stages=args.stages,
        start_module=args.start_module,
        end_module=args.end_module,
        resume=args.resume,
        full_refresh=args.full_refresh,
        skip_coingecko=args.skip_coingecko,
        export_universal=not args.no_export,
        source_database=args.database,
        weekly_research=args.weekly_research,
    )
    summary = ProductionOrchestrator(options).run()
    print(json.dumps({
        "run_id": summary.run_id,
        "status": summary.status,
        "run_directory": summary.run_directory,
        "modules_recorded": len(summary.module_results),
        "modules_skipped_weekly": [
            item["module"] for item in summary.module_results
            if item.get("status") == "SKIPPED_WEEKLY"
        ],
        "universal_export": summary.universal_export,
    }, indent=2))
    return 0 if summary.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
