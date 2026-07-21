from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_platform.module3 import run_module3

def main():
    parser = argparse.ArgumentParser(
        description="Run Crypto Module 3 investment intelligence."
    )
    parser.add_argument(
        "--monthly",
        type=float,
        default=None,
        help="Override the configured monthly contribution amount.",
    )
    parser.add_argument(
        "--holdings-json",
        type=str,
        default=None,
        help=(
            "Optional JSON file mapping asset_id to current dollar value, "
            "for example {\"bitcoin\": 5000, \"ethereum\": 3000}."
        ),
    )
    args = parser.parse_args()

    holdings = None
    if args.holdings_json:
        holdings = json.loads(
            Path(args.holdings_json).read_text(encoding="utf-8")
        )

    print("Crypto Intelligence Platform — Module 3 v3.1")
    print("Portfolio, DCA, valuation zones, rebalancing, and scenarios\n")
    result = run_module3(args.monthly, holdings)

    print("Module 3 summary")
    print("----------------")
    print(f"Status:                 {result['status']}")
    print(f"Signal date:            {result['signal_date']}")
    print(f"Assets analyzed:        {result['assets_analyzed']}")
    print(f"Recommended monthly:    ${result['monthly_contribution_usd']:,.2f}")
    print(f"Recommended cash:       {result['cash_weight']:.1%}")
    print(f"Macro regime:           {result['macro_regime']}")
    print(f"Market regime:          {result['market_regime']}")
    print(f"Run ID:                 {result['run_id']}")

if __name__ == "__main__":
    main()
