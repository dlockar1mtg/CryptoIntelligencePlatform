from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import Module38Runner, ASSETS
from crypto_platform.platform import load_all
from scripts.run_module39_true_replay_rehearsal import split_capacity

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    if args.source_commit != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError("Unexpected certified source commit")

    db = Path(args.database).resolve()
    before = sha256(db)
    settings, _ = load_all()
    runner = object.__new__(Module38Runner)
    runner.cfg = settings["module38"]

    minimum_training_rows = int(settings["module39"]["minimum_training_rows"])
    minimum_validation_rows = int(settings["module38"].get("minimum_validation_rows", 30))
    configured_validation = int(settings["module38"]["validation_rows"])
    maximum_validation_share = float(settings["module38"].get("maximum_validation_share", 0.25))
    horizon = 365

    with duckdb.connect(str(db), read_only=True) as con:
        prices = con.execute(
            """
            SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
            """
        ).fetchdf()

    prices["observation_date"] = pd.to_datetime(prices["observation_date"])
    print("CRYPTO_MODULE39_365_REPLAY_CANDIDATE_DIAGNOSTIC=BEGIN")
    for asset in ASSETS:
        frame = prices[prices.asset_id == asset].copy()
        features = runner.build_features(frame, horizon).reset_index(drop=True)
        dates = pd.to_datetime(features["observation_date"])
        candidate_count = 0
        best = None
        for idx in range(len(features)):
            origin = dates.iloc[idx]
            due_mask = (dates + pd.to_timedelta(horizon, unit="D") <= origin) & (dates < origin)
            usable_rows = int(due_mask.sum())
            adaptive_validation, train_end = split_capacity(
                usable_rows=usable_rows,
                horizon=horizon,
                minimum_training_rows=minimum_training_rows,
                minimum_validation_rows=minimum_validation_rows,
                configured_validation=configured_validation,
                maximum_validation_share=maximum_validation_share,
            )
            if best is None or train_end > best["train_end"]:
                best = {
                    "origin": str(origin.date()),
                    "usable_rows": usable_rows,
                    "adaptive_validation": adaptive_validation,
                    "train_end": train_end,
                }
            if adaptive_validation >= minimum_validation_rows and train_end >= minimum_training_rows:
                candidate_count += 1
        print(
            f"ASSET={asset} FEATURE_ROWS={len(features)} "
            f"FIRST={dates.iloc[0].date() if len(dates) else 'NONE'} "
            f"LAST={dates.iloc[-1].date() if len(dates) else 'NONE'} "
            f"CANDIDATES={candidate_count} BEST={best}"
        )

    after = sha256(db)
    if before != after:
        raise RuntimeError("Source database changed during diagnostic")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("CRYPTO_MODULE39_365_REPLAY_CANDIDATE_DIAGNOSTIC=COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
