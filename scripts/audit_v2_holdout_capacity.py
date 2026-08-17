from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS, Module38Runner
from crypto_platform.module39_validation import (
    TEST_ORIGINS_PER_FOLD,
    exact_candidates,
    select_groups,
)
from crypto_platform.platform import load_all, connect


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--holdout-rows", type=int, default=10)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Database missing: {database}")

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    os.environ["CRYPTO_DATABASE_PATH"] = str(database)
    try:
        settings, _ = load_all()
        conn = connect(settings)
        try:
            runner = object.__new__(Module38Runner)
            runner.cfg = settings["module38"]
            folds = int(settings["module39"]["rolling_folds"])
            used_per_group = folds * TEST_ORIGINS_PER_FOLD
            prices = conn.execute(
                """
                SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd
                FROM canonical_market_daily
                WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
                  AND price_usd IS NOT NULL
                ORDER BY observation_date, asset_id
                """
            ).fetchdf()
            prices["observation_date"] = pd.to_datetime(prices["observation_date"])

            rows = []
            for asset in ASSETS:
                asset_frame = prices[prices.asset_id == asset].copy()
                for horizon in [int(v) for v in runner.cfg["horizons_days"]]:
                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    candidates = exact_candidates(
                        features,
                        horizon,
                        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
                        int(runner.cfg.get("minimum_validation_rows", 30)),
                        int(runner.cfg["validation_rows"]),
                        float(runner.cfg.get("maximum_validation_share", 0.25)),
                    )
                    if len(candidates) < used_per_group:
                        rows.append(
                            {
                                "asset_id": asset,
                                "horizon_days": horizon,
                                "supported_v1": False,
                                "candidate_rows": len(candidates),
                                "unused_rows": 0,
                                "holdout_capacity": False,
                            }
                        )
                        continue
                    used = {i for group in select_groups(candidates, folds) for i in group}
                    unused = len([i for i in candidates if i not in used])
                    rows.append(
                        {
                            "asset_id": asset,
                            "horizon_days": horizon,
                            "supported_v1": True,
                            "candidate_rows": len(candidates),
                            "unused_rows": unused,
                            "holdout_capacity": unused >= args.holdout_rows,
                        }
                    )
        finally:
            conn.close()
    finally:
        if prior_env is None:
            os.environ.pop("CRYPTO_DATABASE_PATH", None)
        else:
            os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    supported = [r for r in rows if r["supported_v1"]]
    capable = [r for r in supported if r["holdout_capacity"]]
    payload = {
        "status": "COMPLETE",
        "outcomes_viewed": False,
        "v1_rows_per_supported_group": used_per_group,
        "proposed_holdout_rows_per_group": args.holdout_rows,
        "supported_groups": len(supported),
        "groups_with_capacity": len(capable),
        "all_supported_groups_have_capacity": (
            len(supported) > 0 and len(capable) == len(supported)
        ),
        "groups": rows,
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_V2_HOLDOUT_CAPACITY_AUDIT=PASS")
    print("HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print(f"SUPPORTED_GROUPS={len(supported)}")
    print(f"GROUPS_WITH_CAPACITY={len(capable)}")
    print(
        "ALL_SUPPORTED_GROUPS_HAVE_CAPACITY="
        + ("TRUE" if payload["all_supported_groups_have_capacity"] else "FALSE")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
