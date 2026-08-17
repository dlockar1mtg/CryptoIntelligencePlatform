from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS
from crypto_platform.module39_validation import TEST_ORIGINS_PER_FOLD, select_groups, split_capacity
from crypto_platform.platform import load_all, connect

MANIFEST_VERSION = "1.0.0"
EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V2"
HOLDOUT_ROWS_PER_GROUP = 10


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def eligible_origin_dates_without_outcomes(
    asset_frame: pd.DataFrame,
    horizon: int,
    minimum_training_rows: int,
    minimum_validation_rows: int,
    configured_validation: int,
    maximum_validation_share: float,
) -> list[pd.Timestamp]:
    frame = asset_frame.sort_values("observation_date").copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    price = frame["price_usd"].astype(float)
    returns = price.pct_change(fill_method=None)

    required = pd.DataFrame({
        "observation_date": frame["observation_date"],
        "return_1d": returns,
        "return_7d": price.pct_change(7, fill_method=None),
        "return_30d": price.pct_change(30, fill_method=None),
        "return_90d": price.pct_change(90, fill_method=None),
        "volatility_30d": returns.rolling(30).std(),
        "volatility_90d": returns.rolling(90).std(),
        "distance_sma50": price / price.rolling(50).mean() - 1,
        "distance_sma200": price / price.rolling(200).mean() - 1,
    }).replace([np.inf, -np.inf], np.nan)

    required = required.dropna().reset_index(drop=True)
    latest_market_date = pd.Timestamp(frame["observation_date"].max())
    matured = required[
        required["observation_date"] + pd.to_timedelta(int(horizon), unit="D") <= latest_market_date
    ].reset_index(drop=True)
    dates = pd.to_datetime(matured["observation_date"])

    candidates: list[pd.Timestamp] = []
    for idx in range(len(matured)):
        origin = dates.iloc[idx]
        due_mask = (
            dates + pd.to_timedelta(int(horizon), unit="D") <= origin
        ) & (dates < origin)
        usable_rows = int(due_mask.sum())
        adaptive_validation, train_end = split_capacity(
            usable_rows=usable_rows,
            horizon=int(horizon),
            minimum_training_rows=minimum_training_rows,
            minimum_validation_rows=minimum_validation_rows,
            configured_validation=configured_validation,
            maximum_validation_share=maximum_validation_share,
        )
        if adaptive_validation >= minimum_validation_rows and train_end >= minimum_training_rows:
            candidates.append(pd.Timestamp(origin))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "predictive_model_improvement_v2_holdout_manifest.json"),
    )
    args = parser.parse_args()

    database = Path(args.database).resolve()
    output = Path(args.output).resolve()
    require(database.is_file(), f"Database missing: {database}")
    require(not output.exists(), f"Frozen V2 holdout manifest already exists: {output}")

    previous_db = os.environ.get("CRYPTO_DATABASE_PATH")
    os.environ["CRYPTO_DATABASE_PATH"] = str(database)
    try:
        settings, _ = load_all()
        conn = connect(settings)
        prices = conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
            """
        ).fetchdf()
        conn.close()
    finally:
        if previous_db is None:
            os.environ.pop("CRYPTO_DATABASE_PATH", None)
        else:
            os.environ["CRYPTO_DATABASE_PATH"] = previous_db

    m38 = settings["module38"]
    folds = int(settings["module39"]["rolling_folds"])
    v1_rows = folds * TEST_ORIGINS_PER_FOLD
    minimum_training = int(m38.get("absolute_minimum_training_rows", 90))
    minimum_validation = int(m38.get("minimum_validation_rows", 30))
    configured_validation = int(m38["validation_rows"])
    maximum_validation_share = float(m38.get("maximum_validation_share", 0.25))

    groups: list[dict] = []
    unsupported: list[dict] = []
    for asset in ASSETS:
        asset_frame = prices[prices.asset_id == asset].copy()
        for horizon in [int(v) for v in m38["horizons_days"]]:
            candidate_dates = eligible_origin_dates_without_outcomes(
                asset_frame=asset_frame,
                horizon=horizon,
                minimum_training_rows=minimum_training,
                minimum_validation_rows=minimum_validation,
                configured_validation=configured_validation,
                maximum_validation_share=maximum_validation_share,
            )
            if len(candidate_dates) < v1_rows:
                unsupported.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "candidate_rows": len(candidate_dates),
                    "reason": "INSUFFICIENT_POINT_IN_TIME_REPLAY_HISTORY",
                })
                continue

            v1_indices = [
                idx
                for group in select_groups(list(range(len(candidate_dates))), folds)
                for idx in group
            ]
            v1_dates = {candidate_dates[idx].date().isoformat() for idx in v1_indices}
            unused = [
                d for d in candidate_dates
                if d.date().isoformat() not in v1_dates
            ]
            require(
                len(unused) >= HOLDOUT_ROWS_PER_GROUP,
                f"Insufficient V2 holdout capacity for {asset} {horizon}d",
            )

            # Freeze the chronologically latest ten unused matured origins. The rule is
            # deterministic and is applied before any realized forward return is loaded.
            selected = unused[-HOLDOUT_ROWS_PER_GROUP:]
            groups.append({
                "asset_id": asset,
                "horizon_days": horizon,
                "candidate_rows": len(candidate_dates),
                "v1_used_rows": len(v1_dates),
                "unused_rows_before_v2": len(unused),
                "v2_holdout_origin_dates": [d.date().isoformat() for d in selected],
            })

    require(len(groups) == 29, f"Expected 29 supported groups, found {len(groups)}")
    require(
        any(r["asset_id"] == "xrp" and int(r["horizon_days"]) == 365 for r in unsupported),
        "Expected explicit XRP 365d evidence gap",
    )

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "holdout_outcomes_viewed_before_freeze": False,
        "selection_rule": "chronologically latest 10 valid matured candidate origins not used by V1",
        "rows_per_supported_group": HOLDOUT_ROWS_PER_GROUP,
        "supported_groups": len(groups),
        "unsupported_groups": unsupported,
        "groups": groups,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["manifest_content_sha256"] = sha256_bytes(canonical)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "COMPLETE",
        "output": str(output),
        "supported_groups": len(groups),
        "rows_per_supported_group": HOLDOUT_ROWS_PER_GROUP,
        "total_frozen_holdout_rows": len(groups) * HOLDOUT_ROWS_PER_GROUP,
        "unsupported_groups": unsupported,
        "manifest_content_sha256": manifest["manifest_content_sha256"],
        "holdout_outcomes_viewed_before_freeze": False,
    }, indent=2))
    print("CRYPTO_V2_HOLDOUT_MANIFEST_FREEZE=PASS")
    print("V2_HOLDOUT_OUTCOMES_VIEWED_BEFORE_FREEZE=FALSE")
    print("SUPPORTED_GROUPS=29")
    print("ROWS_PER_SUPPORTED_GROUP=10")
    print("TOTAL_FROZEN_HOLDOUT_ROWS=290")
    print("NEXT_GATE=CHECKPOINT_FROZEN_V2_HOLDOUT_MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
