from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import BayesianRidge
from sklearn.preprocessing import StandardScaler

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def finite_summary(series: pd.Series) -> dict:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return {"count": 0}
    return {
        "count": int(len(values)),
        "min": float(values.min()),
        "p01": float(values.quantile(0.01)),
        "median": float(values.median()),
        "p99": float(values.quantile(0.99)),
        "max": float(values.max()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    require(args.source_commit == EXPECTED_SOURCE_COMMIT, "Unexpected certified source commit")
    root = Path(__file__).resolve().parents[1]
    source_db = Path(args.database).resolve()
    require(source_db.is_file(), f"Crypto database missing: {source_db}")
    source_hash_before = sha256(source_db)

    with tempfile.TemporaryDirectory(prefix="crypto-m38-feature-diagnostic-") as tmp:
        disposable_db = Path(tmp) / source_db.name
        shutil.copy2(source_db, disposable_db)
        require(sha256(disposable_db) == source_hash_before, "Disposable database copy hash mismatch")
        previous_override = os.environ.get("CRYPTO_DATABASE_PATH")
        os.environ["CRYPTO_DATABASE_PATH"] = str(disposable_db)
        try:
            from crypto_platform.module38 import Module38Runner, ASSETS

            runner = Module38Runner()
            try:
                price_frame = runner.prices()
                horizons = [int(v) for v in runner.cfg["horizons_days"]]
                configured_validation = int(runner.cfg["validation_rows"])
                absolute_minimum = int(runner.cfg.get("absolute_minimum_training_rows", 90))
                minimum_validation = int(runner.cfg.get("minimum_validation_rows", 30))
                maximum_validation_share = float(runner.cfg.get("maximum_validation_share", 0.25))

                capacity = []
                detailed = []
                for asset in ASSETS:
                    asset_frame = price_frame[price_frame["asset_id"] == asset].copy()
                    for horizon in horizons:
                        features = runner.build_features(asset_frame, horizon)
                        usable_rows = len(features)
                        adaptive_validation = min(
                            configured_validation,
                            max(minimum_validation, int(usable_rows * maximum_validation_share)),
                        )
                        adaptive_validation = min(adaptive_validation, usable_rows - absolute_minimum)
                        validation_rows = adaptive_validation
                        train_end = usable_rows - validation_rows - horizon
                        eligible = validation_rows >= minimum_validation and train_end >= absolute_minimum
                        record = {
                            "asset_id": asset,
                            "horizon_days": horizon,
                            "usable_feature_rows": int(usable_rows),
                            "validation_rows": int(validation_rows),
                            "purge_rows": int(horizon),
                            "purged_training_rows": int(max(train_end, 0)),
                            "absolute_minimum_training_rows": absolute_minimum,
                            "eligible_after_purge": bool(eligible),
                        }
                        capacity.append(record)

                        if asset == "ethereum" and horizon == 90 and eligible:
                            columns = [c for c in features.columns if c not in {"observation_date", "target_return"}]
                            train = features.iloc[:train_end]
                            validation = features.iloc[usable_rows - validation_rows:]
                            scaler = StandardScaler()
                            x_train = scaler.fit_transform(train[columns])
                            x_validation = scaler.transform(validation[columns])
                            y_train = train["target_return"].to_numpy(dtype=float)
                            y_validation = validation["target_return"].to_numpy(dtype=float)
                            model = BayesianRidge().fit(x_train, y_train)
                            predictions = model.predict(x_validation)
                            errors = predictions - y_validation
                            feature_stats = {
                                c: {
                                    "train": finite_summary(train[c]),
                                    "validation": finite_summary(validation[c]),
                                    "scaled_validation_abs_max": float(np.max(np.abs(x_validation[:, i]))),
                                    "coefficient": float(model.coef_[i]),
                                }
                                for i, c in enumerate(columns)
                            }
                            worst_idx = np.argsort(np.abs(errors))[::-1][:10]
                            worst_rows = []
                            for idx in worst_idx:
                                row = validation.iloc[int(idx)]
                                worst_rows.append({
                                    "observation_date": str(pd.Timestamp(row["observation_date"]).date()),
                                    "actual_return_pct": float(y_validation[idx] * 100),
                                    "predicted_return_pct": float(predictions[idx] * 100),
                                    "absolute_error_pct": float(abs(errors[idx]) * 100),
                                })
                            detailed.append({
                                "asset_id": asset,
                                "horizon_days": horizon,
                                "train_target_return": finite_summary(pd.Series(y_train * 100)),
                                "validation_target_return": finite_summary(pd.Series(y_validation * 100)),
                                "prediction_return": finite_summary(pd.Series(predictions * 100)),
                                "feature_stats": feature_stats,
                                "worst_validation_rows": worst_rows,
                            })
            finally:
                runner.conn.close()
        finally:
            if previous_override is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = previous_override

    source_hash_after = sha256(source_db)
    require(source_hash_before == source_hash_after, "Source Crypto database changed during diagnostic")

    missing = [r for r in capacity if not r["eligible_after_purge"]]
    payload = {
        "status": "CRYPTO_MODULE38_PURGED_FEATURE_STABILITY_DIAGNOSTIC_COMPLETE",
        "source_commit": args.source_commit,
        "source_database_unchanged": True,
        "capacity_by_asset_horizon": capacity,
        "ineligible_after_purge": missing,
        "ethereum_90d_bayesian_diagnostic": detailed,
        "next_gate": "REPAIR_FEATURE_OR_MODEL_STABILITY_AND_LONG_HORIZON_CAPACITY_BEFORE_MODULE39",
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_MODULE38_PURGED_FEATURE_STABILITY_DIAGNOSTIC=COMPLETE")
    print(f"INELIGIBLE_AFTER_PURGE_GROUPS={len(missing)}")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=REPAIR_FEATURE_OR_MODEL_STABILITY_AND_LONG_HORIZON_CAPACITY_BEFORE_MODULE39")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
