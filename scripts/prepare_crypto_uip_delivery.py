from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.production.hosted import prepare_uip_delivery


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare checksum-verified Crypto delivery for UIP.")
    parser.add_argument("--run-summary", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data" / "operations" / "crypto" / "uip_delivery",
    )
    args = parser.parse_args()
    result = prepare_uip_delivery(args.run_summary, args.output_root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
