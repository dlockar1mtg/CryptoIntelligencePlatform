from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA

MODULE7_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module7_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    primary_horizon_days INTEGER,
    calibration_samples INTEGER,
    walk_forward_folds INTEGER,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS score_bin_performance(
    run_id VARCHAR,
    horizon_days INTEGER,
    score_bin_low DOUBLE,
    score_bin_high DOUBLE,
    sample_count INTEGER,
    average_forward_return_pct DOUBLE,
    median_forward_return_pct DOUBLE,
    positive_rate_pct DOUBLE,
    average_excess_vs_btc_pct DOUBLE,
    btc_outperformance_rate_pct DOUBLE,
    reliability_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, horizon_days, score_bin_low)
);

CREATE TABLE IF NOT EXISTS learned_signal_thresholds(
    run_id VARCHAR,
    horizon_days INTEGER,
    signal_name VARCHAR,
    lower_score DOUBLE,
    upper_score DOUBLE,
    expected_forward_return_pct DOUBLE,
    expected_excess_vs_btc_pct DOUBLE,
    positive_rate_pct DOUBLE,
    sample_count INTEGER,
    reliability_score DOUBLE,
    recommended_for_live_use BOOLEAN,
    methodology VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, horizon_days, signal_name)
);

CREATE TABLE IF NOT EXISTS feature_importance_results(
    run_id VARCHAR,
    horizon_days INTEGER,
    feature_name VARCHAR,
    standardized_coefficient DOUBLE,
    absolute_importance DOUBLE,
    permutation_importance DOUBLE,
    direction VARCHAR,
    sample_count INTEGER,
    train_r_squared DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, horizon_days, feature_name)
);

CREATE TABLE IF NOT EXISTS walk_forward_results(
    run_id VARCHAR,
    fold_number INTEGER,
    train_start DATE,
    train_end DATE,
    test_start DATE,
    test_end DATE,
    training_rows INTEGER,
    test_rows INTEGER,
    correlation DOUBLE,
    mean_absolute_error DOUBLE,
    directional_accuracy_pct DOUBLE,
    top_quintile_return_pct DOUBLE,
    bottom_quintile_return_pct DOUBLE,
    top_minus_bottom_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number)
);

CREATE TABLE IF NOT EXISTS walk_forward_predictions(
    run_id VARCHAR,
    fold_number INTEGER,
    asset_id VARCHAR,
    signal_date DATE,
    actual_excess_return_pct DOUBLE,
    predicted_excess_return_pct DOUBLE,
    predicted_rank_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number, asset_id, signal_date)
);

CREATE TABLE IF NOT EXISTS valuation_validation_summary(
    run_id VARCHAR,
    valuation_label VARCHAR,
    horizon_days INTEGER,
    sample_count INTEGER,
    positive_rate_pct DOUBLE,
    average_forward_return_pct DOUBLE,
    median_forward_return_pct DOUBLE,
    average_excess_vs_btc_pct DOUBLE,
    btc_outperformance_rate_pct DOUBLE,
    reliability_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, valuation_label, horizon_days)
);

CREATE TABLE IF NOT EXISTS calibrated_signal_reliability(
    run_id VARCHAR,
    historical_signal VARCHAR,
    horizon_days INTEGER,
    sample_count INTEGER,
    reliability_score DOUBLE,
    calibrated_confidence DOUBLE,
    historical_positive_rate_pct DOUBLE,
    historical_average_return_pct DOUBLE,
    historical_average_excess_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, historical_signal, horizon_days)
);

CREATE OR REPLACE VIEW latest_score_bin_performance AS
SELECT x.*
FROM score_bin_performance x
JOIN (
    SELECT run_id FROM module7_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_learned_signal_thresholds AS
SELECT x.*
FROM learned_signal_thresholds x
JOIN (
    SELECT run_id FROM module7_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_feature_importance AS
SELECT x.*
FROM feature_importance_results x
JOIN (
    SELECT run_id FROM module7_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_walk_forward_results AS
SELECT x.*
FROM walk_forward_results x
JOIN (
    SELECT run_id FROM module7_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_valuation_validation_summary AS
SELECT x.*
FROM valuation_validation_summary x
JOIN (
    SELECT run_id FROM module7_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_calibrated_signal_reliability AS
SELECT x.*
FROM calibrated_signal_reliability x
JOIN (
    SELECT run_id FROM module7_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

FEATURES = [
    "return_30d_pct",
    "return_90d_pct",
    "return_365d_pct",
    "price_vs_sma50_pct",
    "price_vs_sma200_pct",
    "rsi_14",
    "volatility_30d_pct",
    "max_drawdown_365d_pct",
    "momentum_score",
    "trend_score",
    "risk_score",
    "historical_overall_score",
    "expected_return_proxy_pct",
]

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def safe_mean(series: pd.Series) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return float(clean.mean()) if not clean.empty else None

def reliability_score(sample_count: int, positive_rate: float | None, excess: float | None) -> float:
    sample_factor = min(1.0, sample_count / 300.0)
    direction_factor = (
        abs(float(positive_rate) - 50.0) / 50.0
        if positive_rate is not None else 0.0
    )
    excess_factor = min(1.0, abs(float(excess or 0.0)) / 25.0)
    return float(clamp(100 * (
        sample_factor * 0.55
        + direction_factor * 0.20
        + excess_factor * 0.25
    )))

def standardize_train_test(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    train_values = train[feature_columns].astype(float)
    medians = train_values.median()
    train_values = train_values.fillna(medians)
    test_values = test[feature_columns].astype(float).fillna(medians)
    means = train_values.mean()
    stds = train_values.std(ddof=0).replace(0, 1.0)
    x_train = ((train_values - means) / stds).to_numpy()
    x_test = ((test_values - means) / stds).to_numpy()
    return x_train, x_test, means.to_numpy(), stds.to_numpy()

def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    x_aug = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(x_aug.shape[1]) * alpha
    penalty[0, 0] = 0.0
    beta = np.linalg.pinv(x_aug.T @ x_aug + penalty) @ x_aug.T @ y
    return beta[1:], float(beta[0])

def ridge_predict(x: np.ndarray, coef: np.ndarray, intercept: float) -> np.ndarray:
    return intercept + x @ coef

def r_squared(y: np.ndarray, prediction: np.ndarray) -> float | None:
    denominator = float(np.sum((y - y.mean()) ** 2))
    if denominator <= 0:
        return None
    return float(1 - np.sum((y - prediction) ** 2) / denominator)

class Module7Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module7"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m7_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m7_stage"
        )
        self.conn.unregister("_m7_stage")

    def modeling_frame(self, horizon_days: int) -> pd.DataFrame:
        frame = self.conn.execute(
            """
            SELECT s.*, p.forward_return_pct, p.excess_vs_btc_pct,
                   p.positive_return, p.outperformed_btc
            FROM model_snapshots_daily s
            JOIN signal_forward_performance p
              ON s.asset_id=p.asset_id
             AND s.observation_date=p.signal_date
            WHERE p.horizon_days=?
              AND p.completed=TRUE
            ORDER BY s.observation_date, s.asset_id
            """,
            [horizon_days],
        ).fetchdf()
        if not frame.empty:
            frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame

    def score_bins(self, frame: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
        width = int(self.config["calibration"]["score_bin_width"])
        rows = []
        work = frame.copy()
        work["score_bin_low"] = (
            np.floor(work["historical_overall_score"] / width) * width
        ).clip(0, 100 - width)
        for low, group in work.groupby("score_bin_low"):
            count = len(group)
            positive = float(group["positive_return"].mean() * 100)
            excess = safe_mean(group["excess_vs_btc_pct"])
            rows.append({
                "run_id": self.run_id,
                "horizon_days": horizon_days,
                "score_bin_low": float(low),
                "score_bin_high": float(low + width),
                "sample_count": count,
                "average_forward_return_pct": safe_mean(group["forward_return_pct"]),
                "median_forward_return_pct": float(group["forward_return_pct"].median()),
                "positive_rate_pct": positive,
                "average_excess_vs_btc_pct": excess,
                "btc_outperformance_rate_pct": (
                    float(group["outperformed_btc"].mean() * 100)
                    if group["outperformed_btc"].notna().any() else None
                ),
                "reliability_score": reliability_score(count, positive, excess),
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows).sort_values("score_bin_low")
        self.upsert("score_bin_performance", result)
        return result

    def learned_thresholds(
        self, bins: pd.DataFrame, horizon_days: int
    ) -> pd.DataFrame:
        minimum = int(self.config["calibration"]["minimum_samples_per_band"])
        eligible = bins[bins["sample_count"] >= minimum].copy()
        if eligible.empty:
            return pd.DataFrame()

        # Rank score bins by realized excess return, with positive-rate support.
        eligible["quality"] = (
            eligible["average_excess_vs_btc_pct"].fillna(0) * 0.65
            + (eligible["positive_rate_pct"] - 50) * 0.35
        )
        eligible = eligible.sort_values("score_bin_low")
        score_min = float(eligible["score_bin_low"].min())
        score_max = float(eligible["score_bin_high"].max())

        # Use empirical score quantiles, then attach realized statistics.
        score_values = np.repeat(
            eligible["score_bin_low"].to_numpy(),
            eligible["sample_count"].astype(int).to_numpy(),
        )
        quantiles = np.quantile(score_values, [0.20, 0.40, 0.65, 0.85])
        boundaries = [score_min, *[float(q) for q in quantiles], score_max]
        names = ["AVOID", "REDUCE", "HOLD", "BUY", "STRONG_BUY"]
        rows = []

        for index, name in enumerate(names):
            lower = boundaries[index]
            upper = boundaries[index + 1]
            if index == len(names) - 1:
                group = eligible[
                    (eligible["score_bin_low"] >= lower)
                    & (eligible["score_bin_low"] <= upper)
                ]
            else:
                group = eligible[
                    (eligible["score_bin_low"] >= lower)
                    & (eligible["score_bin_low"] < upper)
                ]
            if group.empty:
                continue
            total = int(group["sample_count"].sum())
            weights = group["sample_count"] / total
            avg_return = float(
                (group["average_forward_return_pct"] * weights).sum()
            )
            avg_excess = float(
                (group["average_excess_vs_btc_pct"].fillna(0) * weights).sum()
            )
            positive = float(
                (group["positive_rate_pct"] * weights).sum()
            )
            reliability = float(
                (group["reliability_score"] * weights).sum()
            )
            rows.append({
                "run_id": self.run_id,
                "horizon_days": horizon_days,
                "signal_name": name,
                "lower_score": lower,
                "upper_score": upper,
                "expected_forward_return_pct": avg_return,
                "expected_excess_vs_btc_pct": avg_excess,
                "positive_rate_pct": positive,
                "sample_count": total,
                "reliability_score": reliability,
                "recommended_for_live_use": bool(
                    total >= minimum
                    and reliability >= 55
                    and len(bins) >= 5
                ),
                "methodology": (
                    "Empirical score quantiles with realized forward-return "
                    "and Bitcoin-relative performance diagnostics."
                ),
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("learned_signal_thresholds", result)
        return result

    def feature_importance(
        self, frame: pd.DataFrame, horizon_days: int
    ) -> pd.DataFrame:
        cfg = self.config["feature_importance"]
        target = cfg["target"]
        work = frame.dropna(subset=[target]).copy()
        if len(work) < int(cfg["minimum_training_rows"]):
            return pd.DataFrame()

        split = int(len(work) * 0.80)
        train = work.iloc[:split].copy()
        test = work.iloc[split:].copy()
        x_train, x_test, _, _ = standardize_train_test(train, test, FEATURES)
        y_train = train[target].astype(float).to_numpy()
        y_test = test[target].astype(float).to_numpy()

        coef, intercept = ridge_fit(
            x_train, y_train, float(cfg["ridge_alpha"])
        )
        train_prediction = ridge_predict(x_train, coef, intercept)
        base_prediction = ridge_predict(x_test, coef, intercept)
        base_mae = float(np.mean(np.abs(y_test - base_prediction)))
        rng = np.random.default_rng(int(cfg["random_seed"]))
        repeats = int(cfg["permutation_repeats"])
        permutation = []

        for index in range(len(FEATURES)):
            losses = []
            for _ in range(repeats):
                shuffled = x_test.copy()
                rng.shuffle(shuffled[:, index])
                prediction = ridge_predict(shuffled, coef, intercept)
                losses.append(float(np.mean(np.abs(y_test - prediction))))
            permutation.append(max(0.0, float(np.mean(losses) - base_mae)))

        total_abs = float(np.sum(np.abs(coef))) or 1.0
        total_perm = float(np.sum(permutation)) or 1.0
        train_r2 = r_squared(y_train, train_prediction)
        rows = []
        for name, coefficient, perm in zip(FEATURES, coef, permutation):
            rows.append({
                "run_id": self.run_id,
                "horizon_days": horizon_days,
                "feature_name": name,
                "standardized_coefficient": float(coefficient),
                "absolute_importance": float(abs(coefficient) / total_abs * 100),
                "permutation_importance": float(perm / total_perm * 100),
                "direction": (
                    "POSITIVE" if coefficient > 0
                    else "NEGATIVE" if coefficient < 0
                    else "NEUTRAL"
                ),
                "sample_count": len(work),
                "train_r_squared": train_r2,
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("feature_importance_results", result)
        return result

    def walk_forward(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        cfg = self.config["walk_forward"]
        target = self.config["feature_importance"]["target"]
        work = frame.dropna(subset=[target]).sort_values(
            ["observation_date", "asset_id"]
        )
        if work.empty:
            return pd.DataFrame(), pd.DataFrame()

        training_days = int(cfg["training_days"])
        test_days = int(cfg["test_days"])
        step_days = int(cfg["step_days"])
        earliest = work["observation_date"].min()
        latest = work["observation_date"].max()
        test_start = earliest + pd.Timedelta(days=training_days)
        fold = 0
        fold_rows = []
        prediction_rows = []

        while test_start <= latest:
            train_start = test_start - pd.Timedelta(days=training_days)
            train_end = test_start - pd.Timedelta(days=1)
            test_end = test_start + pd.Timedelta(days=test_days - 1)
            train = work[
                (work["observation_date"] >= train_start)
                & (work["observation_date"] <= train_end)
            ]
            test = work[
                (work["observation_date"] >= test_start)
                & (work["observation_date"] <= test_end)
            ]
            if (
                len(train) >= int(cfg["minimum_training_rows"])
                and len(test) >= int(cfg["minimum_test_rows"])
            ):
                fold += 1
                x_train, x_test, _, _ = standardize_train_test(
                    train, test, FEATURES
                )
                y_train = train[target].astype(float).to_numpy()
                y_test = test[target].astype(float).to_numpy()
                coef, intercept = ridge_fit(
                    x_train, y_train,
                    float(self.config["feature_importance"]["ridge_alpha"]),
                )
                prediction = ridge_predict(x_test, coef, intercept)
                correlation = (
                    float(np.corrcoef(y_test, prediction)[0, 1])
                    if len(y_test) > 1
                    and np.std(y_test) > 0
                    and np.std(prediction) > 0
                    else None
                )
                mae = float(np.mean(np.abs(y_test - prediction)))
                direction = float(
                    (np.sign(y_test) == np.sign(prediction)).mean() * 100
                )
                test_copy = test.copy()
                test_copy["prediction"] = prediction
                test_copy["actual"] = y_test
                test_copy["predicted_rank_pct"] = (
                    test_copy["prediction"].rank(pct=True) * 100
                )
                quintile = max(1, len(test_copy) // 5)
                ordered = test_copy.sort_values("prediction")
                bottom = float(ordered.head(quintile)["actual"].mean())
                top = float(ordered.tail(quintile)["actual"].mean())

                fold_rows.append({
                    "run_id": self.run_id,
                    "fold_number": fold,
                    "train_start": train_start.date(),
                    "train_end": train_end.date(),
                    "test_start": test_start.date(),
                    "test_end": min(test_end, latest).date(),
                    "training_rows": len(train),
                    "test_rows": len(test),
                    "correlation": correlation,
                    "mean_absolute_error": mae,
                    "directional_accuracy_pct": direction,
                    "top_quintile_return_pct": top,
                    "bottom_quintile_return_pct": bottom,
                    "top_minus_bottom_pct": top - bottom,
                    "calculated_at_utc": utcnow(),
                })
                for _, row in test_copy.iterrows():
                    prediction_rows.append({
                        "run_id": self.run_id,
                        "fold_number": fold,
                        "asset_id": row["asset_id"],
                        "signal_date": row["observation_date"].date(),
                        "actual_excess_return_pct": row["actual"],
                        "predicted_excess_return_pct": row["prediction"],
                        "predicted_rank_pct": row["predicted_rank_pct"],
                        "calculated_at_utc": utcnow(),
                    })
            test_start += pd.Timedelta(days=step_days)

        folds = pd.DataFrame(fold_rows)
        predictions = pd.DataFrame(prediction_rows)
        self.upsert("walk_forward_results", folds)
        self.upsert("walk_forward_predictions", predictions)
        return folds, predictions

    def valuation_validation(self) -> pd.DataFrame:
        snapshots = self.conn.execute(
            """
            SELECT s.asset_id, s.observation_date, s.valuation_label,
                   p.horizon_days, p.forward_return_pct,
                   p.excess_vs_btc_pct, p.positive_return,
                   p.outperformed_btc
            FROM model_snapshots_daily s
            JOIN signal_forward_performance p
              ON s.asset_id=p.asset_id
             AND s.observation_date=p.signal_date
            WHERE p.completed=TRUE
            """
        ).fetchdf()
        if snapshots.empty:
            return pd.DataFrame()
        allowed = set(
            int(value)
            for value in self.config["historical_valuation"]["horizons_days"]
        )
        snapshots = snapshots[snapshots["horizon_days"].isin(allowed)]
        minimum = int(self.config["historical_valuation"]["minimum_samples"])
        rows = []
        for (label, horizon), group in snapshots.groupby(
            ["valuation_label", "horizon_days"]
        ):
            if len(group) < minimum:
                continue
            positive = float(group["positive_return"].mean() * 100)
            excess = safe_mean(group["excess_vs_btc_pct"])
            rows.append({
                "run_id": self.run_id,
                "valuation_label": label,
                "horizon_days": int(horizon),
                "sample_count": len(group),
                "positive_rate_pct": positive,
                "average_forward_return_pct": safe_mean(group["forward_return_pct"]),
                "median_forward_return_pct": float(group["forward_return_pct"].median()),
                "average_excess_vs_btc_pct": excess,
                "btc_outperformance_rate_pct": (
                    float(group["outperformed_btc"].mean() * 100)
                    if group["outperformed_btc"].notna().any() else None
                ),
                "reliability_score": reliability_score(
                    len(group), positive, excess
                ),
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("valuation_validation_summary", result)
        return result

    def calibrated_reliability(self, horizon_days: int) -> pd.DataFrame:
        frame = self.conn.execute(
            """
            SELECT historical_signal, sample_count, positive_rate_pct,
                   average_forward_return_pct, average_excess_vs_btc_pct
            FROM signal_validation_summary
            WHERE horizon_days=?
            """,
            [horizon_days],
        ).fetchdf()
        if frame.empty:
            return pd.DataFrame()
        minimum = int(
            self.config["confidence"]["minimum_reliability_samples"]
        )
        maximum = float(
            self.config["confidence"]["maximum_calibrated_confidence"]
        )
        rows = []
        for _, row in frame.iterrows():
            reliability = reliability_score(
                int(row["sample_count"]),
                float(row["positive_rate_pct"]),
                row["average_excess_vs_btc_pct"],
            )
            confidence = min(
                maximum,
                35
                + reliability * 0.45
                + min(1.0, int(row["sample_count"]) / max(minimum, 1)) * 15
            )
            rows.append({
                "run_id": self.run_id,
                "historical_signal": row["historical_signal"],
                "horizon_days": horizon_days,
                "sample_count": int(row["sample_count"]),
                "reliability_score": reliability,
                "calibrated_confidence": confidence,
                "historical_positive_rate_pct": row["positive_rate_pct"],
                "historical_average_return_pct": row["average_forward_return_pct"],
                "historical_average_excess_pct": row["average_excess_vs_btc_pct"],
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("calibrated_signal_reliability", result)
        return result

    def run(self) -> dict[str, Any]:
        horizon = int(self.config["calibration"]["primary_horizon_days"])
        frame = self.modeling_frame(horizon)
        minimum_total = int(
            self.config["calibration"]["minimum_total_samples"]
        )
        if len(frame) < minimum_total:
            raise RuntimeError(
                f"Module 7 requires at least {minimum_total} completed "
                f"{horizon}-day observations; found {len(frame)}."
            )

        self.conn.execute(
            """
            INSERT INTO module7_runs(
                run_id,started_at_utc,status,primary_horizon_days,
                calibration_samples,walk_forward_folds,notes,platform_version
            ) VALUES (?,?,'RUNNING',?,0,0,NULL,'4.0.0')
            """,
            [self.run_id, self.started, horizon],
        )

        bins = self.score_bins(frame, horizon)
        thresholds = self.learned_thresholds(bins, horizon)
        importance = self.feature_importance(frame, horizon)
        folds, predictions = self.walk_forward(frame)
        valuation = self.valuation_validation()
        reliability = self.calibrated_reliability(horizon)

        recommended_count = (
            int(thresholds["recommended_for_live_use"].sum())
            if not thresholds.empty else 0
        )
        notes = (
            f"samples={len(frame)}; bins={len(bins)}; "
            f"thresholds={len(thresholds)}; recommended={recommended_count}; "
            f"features={len(importance)}; folds={len(folds)}; "
            f"valuation_rows={len(valuation)}."
        )
        self.conn.execute(
            """
            UPDATE module7_runs
            SET completed_at_utc=?,status='SUCCESS',
                calibration_samples=?,walk_forward_folds=?,notes=?
            WHERE run_id=?
            """,
            [utcnow(), len(frame), len(folds), notes, self.run_id],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "primary_horizon_days": horizon,
            "calibration_samples": len(frame),
            "walk_forward_folds": len(folds),
            "learned_thresholds": len(thresholds),
            "thresholds_recommended": recommended_count,
        }

def run_module7() -> dict[str, Any]:
    return Module7Runner().run()
