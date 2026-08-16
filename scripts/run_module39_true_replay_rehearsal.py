from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import Module38Runner, ASSETS
from crypto_platform.platform import load_all

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"
TEST_ORIGINS_PER_FOLD = 10


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def clip_probability(values):
    return np.clip(np.asarray(values, dtype=float), 1e-4, 1 - 1e-4)


def split_capacity(
    usable_rows: int,
    horizon: int,
    minimum_training_rows: int,
    minimum_validation_rows: int,
    configured_validation: int,
    maximum_validation_share: float,
) -> tuple[int, int]:
    adaptive_validation = min(
        configured_validation,
        max(minimum_validation_rows, int(usable_rows * maximum_validation_share)),
    )
    adaptive_validation = min(
        adaptive_validation,
        usable_rows - minimum_training_rows,
    )
    if adaptive_validation < minimum_validation_rows:
        return adaptive_validation, -1
    validation_start = usable_rows - adaptive_validation
    train_end = validation_start - horizon
    return adaptive_validation, train_end


def choose_test_indices(
    features: pd.DataFrame,
    horizon: int,
    minimum_training_rows: int,
    minimum_validation_rows: int,
    configured_validation: int,
    maximum_validation_share: float,
    folds: int,
) -> list[list[int]]:
    dates = pd.to_datetime(features["observation_date"])
    candidates = []
    for idx in range(len(features)):
        origin = dates.iloc[idx]
        due_mask = (
            dates + pd.to_timedelta(horizon, unit="D") <= origin
        ) & (dates < origin)
        usable_rows = int(due_mask.sum())
        adaptive_validation, train_end = split_capacity(
            usable_rows=usable_rows,
            horizon=horizon,
            minimum_training_rows=minimum_training_rows,
            minimum_validation_rows=minimum_validation_rows,
            configured_validation=configured_validation,
            maximum_validation_share=maximum_validation_share,
        )
        if (
            adaptive_validation >= minimum_validation_rows
            and train_end >= minimum_training_rows
        ):
            candidates.append(idx)

    required = folds * TEST_ORIGINS_PER_FOLD
    require(
        len(candidates) >= required,
        f"Insufficient replay candidates: horizon={horizon}, "
        f"have={len(candidates)}, need={required}",
    )
    chosen_positions = np.linspace(
        0,
        len(candidates) - 1,
        required,
        dtype=int,
    )
    chosen = [candidates[int(pos)] for pos in chosen_positions]
    return [
        chosen[
            i * TEST_ORIGINS_PER_FOLD:(i + 1) * TEST_ORIGINS_PER_FOLD
        ]
        for i in range(folds)
    ]


def point_in_time_prediction(
    runner: Module38Runner,
    features: pd.DataFrame,
    origin_idx: int,
    horizon: int,
) -> dict:
    origin_date = pd.Timestamp(features.iloc[origin_idx]["observation_date"])
    due_mask = (
        pd.to_datetime(features["observation_date"])
        + pd.to_timedelta(horizon, unit="D")
        <= origin_date
    )
    available = features.loc[due_mask].copy()
    available = available[
        pd.to_datetime(available["observation_date"]) < origin_date
    ].copy()

    cfg = runner.cfg
    minimum_training_rows = int(
        cfg.get("absolute_minimum_training_rows", 90)
    )
    minimum_validation_rows = int(
        cfg.get("minimum_validation_rows", 30)
    )
    configured_validation = int(cfg["validation_rows"])
    maximum_validation_share = float(
        cfg.get("maximum_validation_share", 0.25)
    )

    usable_rows = len(available)
    adaptive_validation, train_end = split_capacity(
        usable_rows=usable_rows,
        horizon=horizon,
        minimum_training_rows=minimum_training_rows,
        minimum_validation_rows=minimum_validation_rows,
        configured_validation=configured_validation,
        maximum_validation_share=maximum_validation_share,
    )
    require(
        adaptive_validation >= minimum_validation_rows,
        f"Insufficient internal validation at {origin_date.date()}",
    )
    require(
        train_end >= minimum_training_rows,
        f"Insufficient purged train at {origin_date.date()}",
    )
    validation_start = usable_rows - adaptive_validation

    train = available.iloc[:train_end].copy()
    validation = available.iloc[validation_start:].copy()
    current = features.iloc[[origin_idx]].copy()

    columns = [
        c
        for c in train.columns
        if c not in {"observation_date", "target_return"}
    ]
    current = current[columns]
    train_x = train[columns].astype(float).copy()
    val_x = validation[columns].astype(float).copy()
    current_x = current.astype(float).copy()
    training_min = train_x.min(axis=0)
    training_max = train_x.max(axis=0)
    val_x = val_x.clip(
        lower=training_min,
        upper=training_max,
        axis=1,
    )
    current_x = current_x.clip(
        lower=training_min,
        upper=training_max,
        axis=1,
    )

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_x)
    x_val = scaler.transform(val_x)
    x_current = scaler.transform(current_x)
    y_train = train["target_return"].to_numpy(dtype=float)
    y_val = validation["target_return"].to_numpy(dtype=float)

    preds = []
    residuals = []
    raw_weights = []
    for model in runner.model_suite(
        int(cfg["random_state"]) + horizon
    ).values():
        model.fit(x_train, y_train)
        val_pred = model.predict(x_val)
        current_pred = float(model.predict(x_current)[0])
        mae = float(np.mean(np.abs(y_val - val_pred)))
        raw_weights.append(1 / max(mae, 1e-6))
        preds.append(current_pred)
        residuals.extend((y_val - val_pred).tolist())

    weights = np.asarray(raw_weights, dtype=float)
    weights /= weights.sum()
    ensemble = float(
        np.dot(weights, np.asarray(preds, dtype=float))
    )
    residual_array = np.asarray(residuals, dtype=float)
    probability_positive = float(
        np.mean(ensemble + residual_array > 0)
    )

    actual = float(features.iloc[origin_idx]["target_return"])
    return {
        "forecast_date": str(origin_date.date()),
        "predicted_return_pct": ensemble * 100,
        "actual_return_pct": actual * 100,
        "raw_probability_positive": probability_positive,
        "observed_positive": int(actual > 0),
        "training_rows": len(train),
        "internal_validation_rows": len(validation),
    }


def calibration_holdout(rows: pd.DataFrame) -> dict:
    rows = rows.sort_values("forecast_date").reset_index(drop=True)
    split = max(int(len(rows) * 2 / 3), 1)
    train = rows.iloc[:split]
    test = rows.iloc[split:]
    raw_test = clip_probability(
        test["raw_probability_positive"].to_numpy()
    )
    observed_test = test["observed_positive"].astype(int).to_numpy()
    raw_brier = (
        float(brier_score_loss(observed_test, raw_test))
        if len(test)
        else math.nan
    )
    raw_ll = (
        float(log_loss(observed_test, raw_test, labels=[0, 1]))
        if len(test)
        else math.nan
    )

    method = "EVIDENCE_SHRINKAGE"
    calibrated_test = np.repeat(
        float(train["observed_positive"].mean())
        if len(train)
        else 0.5,
        len(test),
    )
    if (
        len(train) >= 20
        and train["observed_positive"].nunique() >= 2
        and train["raw_probability_positive"].nunique() >= 2
    ):
        x = train[["raw_probability_positive"]].to_numpy(dtype=float)
        y = train["observed_positive"].astype(int).to_numpy()
        logistic = LogisticRegression().fit(x, y)
        p_log = logistic.predict_proba(
            test[["raw_probability_positive"]].to_numpy(dtype=float)
        )[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip").fit(
            train["raw_probability_positive"].to_numpy(dtype=float),
            y,
        )
        p_iso = iso.predict(
            test["raw_probability_positive"].to_numpy(dtype=float)
        )
        candidates = []
        for name, probs in [("PLATT", p_log), ("ISOTONIC", p_iso)]:
            probs = clip_probability(probs)
            candidates.append(
                (
                    name,
                    probs,
                    float(brier_score_loss(observed_test, probs)),
                )
            )
        method, calibrated_test, _ = min(
            candidates,
            key=lambda x: x[2],
        )

    calibrated_test = clip_probability(calibrated_test)
    calibrated_brier = (
        float(brier_score_loss(observed_test, calibrated_test))
        if len(test)
        else math.nan
    )
    calibrated_ll = (
        float(
            log_loss(
                observed_test,
                calibrated_test,
                labels=[0, 1],
            )
        )
        if len(test)
        else math.nan
    )
    return {
        "calibration_method": method,
        "calibration_train_rows": len(train),
        "calibration_test_rows": len(test),
        "raw_brier_score": raw_brier,
        "calibrated_brier_score": calibrated_brier,
        "raw_log_loss": raw_ll,
        "calibrated_log_loss": calibrated_ll,
        "observed_positive_rate": float(
            rows["observed_positive"].mean()
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    require(
        args.source_commit == EXPECTED_SOURCE_COMMIT,
        "Unexpected certified source commit",
    )

    db = Path(args.database).resolve()
    require(db.is_file(), f"Database missing: {db}")
    before = sha256(db)

    settings, _ = load_all()
    runner = object.__new__(Module38Runner)
    runner.cfg = settings["module38"]
    folds = int(settings["module39"]["rolling_folds"])
    minimum_training_rows = int(
        settings["module39"]["minimum_training_rows"]
    )
    minimum_validation_rows = int(
        settings["module38"].get("minimum_validation_rows", 30)
    )
    configured_validation = int(
        settings["module38"]["validation_rows"]
    )
    maximum_validation_share = float(
        settings["module38"].get("maximum_validation_share", 0.25)
    )
    horizons = [
        int(v)
        for v in settings["module38"]["horizons_days"]
    ]

    with duckdb.connect(str(db), read_only=True) as con:
        prices = con.execute(
            """
            SELECT asset_id, observation_date, price_usd,
                   market_cap_usd, volume_24h_usd
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana',
                'chainlink','xrp','avalanche'
            )
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
            """
        ).fetchdf()

    prices["observation_date"] = pd.to_datetime(
        prices["observation_date"]
    )
    all_rows = []
    fold_rows = []
    calibration_rows = []

    for asset in ASSETS:
        asset_frame = prices[prices.asset_id == asset].copy()
        for horizon in horizons:
            features = runner.build_features(
                asset_frame,
                horizon,
            ).reset_index(drop=True)
            groups = choose_test_indices(
                features=features,
                horizon=horizon,
                minimum_training_rows=minimum_training_rows,
                minimum_validation_rows=minimum_validation_rows,
                configured_validation=configured_validation,
                maximum_validation_share=maximum_validation_share,
                folds=folds,
            )
            group_predictions = []
            for fold_number, indices in enumerate(groups, start=1):
                fold_predictions = [
                    point_in_time_prediction(
                        runner,
                        features,
                        idx,
                        horizon,
                    )
                    for idx in indices
                ]
                frame = pd.DataFrame(fold_predictions)
                frame["asset_id"] = asset
                frame["horizon_days"] = horizon
                frame["fold_number"] = fold_number
                all_rows.extend(frame.to_dict("records"))
                group_predictions.extend(fold_predictions)
                errors = (
                    frame["actual_return_pct"]
                    - frame["predicted_return_pct"]
                )
                direction = float(
                    (
                        np.sign(frame["actual_return_pct"])
                        == np.sign(frame["predicted_return_pct"])
                    ).mean()
                    * 100
                )
                brier = float(
                    brier_score_loss(
                        frame["observed_positive"],
                        clip_probability(
                            frame["raw_probability_positive"]
                        ),
                    )
                )
                fold_rows.append(
                    {
                        "asset_id": asset,
                        "horizon_days": horizon,
                        "fold_number": fold_number,
                        "training_rows_min": int(
                            frame["training_rows"].min()
                        ),
                        "training_rows_max": int(
                            frame["training_rows"].max()
                        ),
                        "testing_rows": len(frame),
                        "training_end_before_testing": True,
                        "testing_start_date": frame[
                            "forecast_date"
                        ].min(),
                        "testing_end_date": frame[
                            "forecast_date"
                        ].max(),
                        "mae_pct": float(errors.abs().mean()),
                        "rmse_pct": float(
                            np.sqrt(np.mean(errors ** 2))
                        ),
                        "directional_accuracy_pct": direction,
                        "brier_score": brier,
                    }
                )
            calibration = calibration_holdout(
                pd.DataFrame(group_predictions)
            )
            calibration.update(
                {
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "replay_rows": len(group_predictions),
                }
            )
            calibration_rows.append(calibration)

    all_frame = pd.DataFrame(all_rows)
    fold_frame = pd.DataFrame(fold_rows)
    cal_frame = pd.DataFrame(calibration_rows)
    after = sha256(db)
    require(
        before == after,
        "Source database changed during Module 39 replay rehearsal",
    )

    payload = {
        "status": "CRYPTO_MODULE39_TRUE_REPLAY_REHEARSAL_COMPLETE",
        "source_commit": args.source_commit,
        "source_database_unchanged": True,
        "replay_rows": len(all_frame),
        "asset_horizon_groups": int(
            all_frame.groupby(["asset_id", "horizon_days"]).ngroups
        ),
        "fold_rows": len(fold_frame),
        "folds_per_group": folds,
        "test_origins_per_fold": TEST_ORIGINS_PER_FOLD,
        "directional_accuracy_by_horizon": [
            {
                "horizon_days": int(h),
                "replay_rows": int(len(g)),
                "mae_pct": float(
                    (
                        g["actual_return_pct"]
                        - g["predicted_return_pct"]
                    ).abs().mean()
                ),
                "rmse_pct": float(
                    np.sqrt(
                        np.mean(
                            (
                                g["actual_return_pct"]
                                - g["predicted_return_pct"]
                            ) ** 2
                        )
                    )
                ),
                "directional_accuracy_pct": float(
                    (
                        np.sign(g["actual_return_pct"])
                        == np.sign(g["predicted_return_pct"])
                    ).mean()
                    * 100
                ),
                "raw_brier_score": float(
                    brier_score_loss(
                        g["observed_positive"],
                        clip_probability(
                            g["raw_probability_positive"]
                        ),
                    )
                ),
            }
            for h, g in all_frame.groupby("horizon_days")
        ],
        "fold_detail": fold_frame.to_dict("records"),
        "calibration_holdout": cal_frame.to_dict("records"),
        "implementation_guard": (
            "This is read-only replay evidence. It does not modify Module 39 "
            "or certify predictive skill by itself."
        ),
        "next_gate": (
            "USE_TRUE_REPLAY_EVIDENCE_TO_REPLACE_MODULE39_PSEUDO_ROLLING_"
            "AND_PROXY_CALIBRATION"
        ),
    }
    print(json.dumps(payload, indent=2))
    print("CRYPTO_MODULE39_TRUE_REPLAY_REHEARSAL=COMPLETE")
    print(f"REPLAY_ROWS={len(all_frame)}")
    print(
        f"ASSET_HORIZON_GROUPS={payload['asset_horizon_groups']}"
    )
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(
        "NEXT_GATE=USE_TRUE_REPLAY_EVIDENCE_TO_REPLACE_MODULE39_"
        "PSEUDO_ROLLING_AND_PROXY_CALIBRATION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
