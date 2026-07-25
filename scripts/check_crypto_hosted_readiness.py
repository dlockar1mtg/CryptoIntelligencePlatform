from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.production.hosted import HostedThresholds, evaluate_hosted_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Certify hosted Crypto database health and freshness.")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "crypto_intelligence.duckdb")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "operations" / "crypto" / "hosted_readiness.json")
    parser.add_argument("--daily-market-max-age-hours", type=float, default=72.0)
    parser.add_argument("--macro-max-age-days", type=float, default=60.0)
    parser.add_argument("--collection-max-age-hours", type=float, default=72.0)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    result = evaluate_hosted_database(
        args.database,
        HostedThresholds(
            daily_market_max_age_hours=args.daily_market_max_age_hours,
            macro_max_age_days=args.macro_max_age_days,
            collection_max_age_hours=args.collection_max_age_hours,
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if args.strict and result["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
