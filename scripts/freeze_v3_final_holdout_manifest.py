from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS
from crypto_platform.module39_validation import split_capacity

MANIFEST_VERSION = "1.0.0"
EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3"
HOLDOUT_ROWS_PER_GROUP = 10
EXPECTED_SUPPORTED_GROUPS = 29


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_manifest_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "predictive_model_tournament_v3_final_holdout_manifest.json"),
    )
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_manifest_path = Path(args.v2_manifest).resolve()
    output = Path(args.output).resolve()
    require(source.is_file(), f"Database missing: {source}")
    require(v2_manifest_path.is_file(), f"V2 manifest missing: {v2_manifest_path}")
    require(not output.exists(), f"Frozen V3 final holdout manifest already exists: {output}")

    before_db = sha256(source)
    before_v2 = sha256(v2_manifest_path)
    v2 = json.loads(v2_manifest_path.read_text(encoding="utf-8"))
    require(v2.get("supported_groups") == 29, "Unexpected V2 supported-group count")
    v2_dates_by_group = {
        (g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"])
        for g in v2["groups"]
    }

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v3_holdout_freeze_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import load_all, connect
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
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    require(sha256(source) == before_db, "Source database changed during V3 holdout freeze")
    require(sha256(v2_manifest_path) == before_v2, "V2 manifest changed during V3 holdout freeze")

    m38 = settings["module38"]
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
            key = (asset, horizon)
            if key not in v2_dates_by_group:
                unsupported.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "candidate_rows": len(candidate_dates),
                    "reason": "NO_V2_SUPPORTED_GROUP_OR_NO_SAFE_POINT_IN_TIME_CANDIDATES",
                })
                continue

            v2_consumed = v2_dates_by_group[key]
            unused = [d for d in candidate_dates if d.date().isoformat() not in v2_consumed]
            require(
                len(unused) >= HOLDOUT_ROWS_PER_GROUP,
                f"Insufficient fresh V3 final holdout capacity for {asset} {horizon}d",
            )
            selected = unused[-HOLDOUT_ROWS_PER_GROUP:]
            selected_iso = [d.date().isoformat() for d in selected]
            require(not set(selected_iso).intersection(v2_consumed), f"V2/V3 overlap for {asset} {horizon}d")

            groups.append({
                "asset_id": asset,
                "horizon_days": horizon,
                "safe_candidate_origins": len(candidate_dates),
                "v2_consumed_origins": len(v2_consumed),
                "unused_safe_origins_before_v3": len(unused),
                "v3_final_holdout_origin_dates": selected_iso,
            })

    require(len(groups) == EXPECTED_SUPPORTED_GROUPS, f"Expected 29 supported V3 groups, found {len(groups)}")
    require(
        any(r["asset_id"] == "xrp" and int(r["horizon_days"]) == 365 for r in unsupported),
        "Expected explicit XRP 365d unsupported group",
    )

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "holdout_role": "FINAL_POST_TOURNAMENT_SELECTION_HOLDOUT",
        "holdout_outcomes_viewed_before_freeze": False,
        "selection_rule": "chronologically latest 10 safe unused origins after excluding consumed V2 holdout origins",
        "rows_per_supported_group": HOLDOUT_ROWS_PER_GROUP,
        "supported_groups": len(groups),
        "unsupported_groups": unsupported,
        "v2_manifest_file_sha256": before_v2,
        "groups": groups,
    }
    manifest["manifest_content_sha256"] = canonical_manifest_hash(manifest)

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
        "source_database_unchanged": sha256(source) == before_db,
        "v2_manifest_unchanged": sha256(v2_manifest_path) == before_v2,
    }, indent=2))
    print("CRYPTO_V3_FINAL_HOLDOUT_MANIFEST_FREEZE=PASS")
    print("V3_HOLDOUT_OUTCOMES_VIEWED_BEFORE_FREEZE=FALSE")
    print("SUPPORTED_GROUPS=29")
    print("ROWS_PER_SUPPORTED_GROUP=10")
    print("TOTAL_FROZEN_HOLDOUT_ROWS=290")
    print("V2_V3_HOLDOUT_OVERLAP=FALSE")
    print("NEXT_GATE=VALIDATE_AND_CHECKPOINT_FROZEN_V3_FINAL_HOLDOUT_MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
