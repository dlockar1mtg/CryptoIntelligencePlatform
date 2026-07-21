from __future__ import annotations

import hashlib
import json
import math
import pickle
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score

from crypto_platform.platform import ROOT, load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA, FEATURES

MODULE8_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module8_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    target_horizon_days INTEGER,
    training_rows INTEGER,
    validation_folds INTEGER,
    ml_ensemble_weight DOUBLE,
    promoted BOOLEAN,
    model_artifact_path VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS ml_model_registry(
    model_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    trained_at_utc TIMESTAMPTZ,
    target_horizon_days INTEGER,
    model_type VARCHAR,
    training_start DATE,
    training_end DATE,
    training_rows INTEGER,
    feature_count INTEGER,
    feature_hash VARCHAR,
    model_artifact_path VARCHAR,
    training_r_squared DOUBLE,
    training_mae DOUBLE,
    active BOOLEAN
);

CREATE TABLE IF NOT EXISTS ml_walk_forward_results(
    run_id VARCHAR,
    fold_number INTEGER,
    train_start DATE,
    train_end DATE,
    test_start DATE,
    test_end DATE,
    training_rows INTEGER,
    test_rows INTEGER,
    correlation DOUBLE,
    r_squared DOUBLE,
    mean_absolute_error DOUBLE,
    directional_accuracy_pct DOUBLE,
    top_quintile_return_pct DOUBLE,
    bottom_quintile_return_pct DOUBLE,
    top_minus_bottom_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number)
);

CREATE TABLE IF NOT EXISTS ml_walk_forward_regime_results(
    run_id VARCHAR,
    fold_number INTEGER,
    cycle_phase VARCHAR,
    test_rows INTEGER,
    correlation DOUBLE,
    mean_absolute_error DOUBLE,
    directional_accuracy_pct DOUBLE,
    average_actual_return_pct DOUBLE,
    average_predicted_return_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number, cycle_phase)
);

CREATE TABLE IF NOT EXISTS ml_predictions_current(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    rules_score DOUBLE,
    rules_signal VARCHAR,
    ml_predicted_excess_return_pct DOUBLE,
    ml_percentile_rank DOUBLE,
    ml_signal VARCHAR,
    ml_confidence DOUBLE,
    ensemble_score DOUBLE,
    ensemble_signal VARCHAR,
    ensemble_confidence DOUBLE,
    ml_weight DOUBLE,
    promotion_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS ml_feature_importance(
    run_id VARCHAR,
    feature_name VARCHAR,
    permutation_importance DOUBLE,
    permutation_std DOUBLE,
    normalized_importance DOUBLE,
    rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_name)
);

CREATE TABLE IF NOT EXISTS ml_shap_explanations(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    feature_name VARCHAR,
    feature_value DOUBLE,
    shap_value DOUBLE,
    absolute_shap_value DOUBLE,
    direction VARCHAR,
    rank INTEGER,
    baseline_prediction DOUBLE,
    model_prediction DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, feature_name)
);

CREATE TABLE IF NOT EXISTS ensemble_validation_summary(
    run_id VARCHAR PRIMARY KEY,
    validation_folds INTEGER,
    average_correlation DOUBLE,
    average_directional_accuracy_pct DOUBLE,
    average_top_minus_bottom_pct DOUBLE,
    average_mae DOUBLE,
    recommended_ml_weight DOUBLE,
    promoted BOOLEAN,
    promotion_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_ml_predictions AS
SELECT p.*
FROM ml_predictions_current p
JOIN (
    SELECT run_id FROM module8_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_ml_feature_importance AS
SELECT p.*
FROM ml_feature_importance p
JOIN (
    SELECT run_id FROM module8_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_ml_shap_explanations AS
SELECT p.*
FROM ml_shap_explanations p
JOIN (
    SELECT run_id FROM module8_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_ml_walk_forward_results AS
SELECT p.*
FROM ml_walk_forward_results p
JOIN (
    SELECT run_id FROM module8_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_ml_regime_validation AS
SELECT p.*
FROM ml_walk_forward_regime_results p
JOIN (
    SELECT run_id FROM module8_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_ensemble_validation AS
SELECT p.*
FROM ensemble_validation_summary p
JOIN (
    SELECT run_id FROM module8_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def safe_correlation(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if (
        len(actual) < 2
        or float(np.std(actual)) == 0.0
        or float(np.std(predicted)) == 0.0
    ):
        return None
    return float(np.corrcoef(actual, predicted)[0, 1])

def signal_from_score(score: float) -> str:
    if score >= 80:
        return "STRONG_BUY"
    if score >= 68:
        return "BUY"
    if score >= 48:
        return "HOLD"
    if score >= 35:
        return "REDUCE"
    return "AVOID"

def ml_signal_from_percentile(percentile: float) -> str:
    if percentile >= 85:
        return "STRONG_BUY"
    if percentile >= 65:
        return "BUY"
    if percentile >= 40:
        return "HOLD"
    if percentile >= 20:
        return "REDUCE"
    return "AVOID"

class Module8Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA,
            MODULE3_SCHEMA,
            MODULE5_SCHEMA,
            MODULE6_SCHEMA,
            MODULE7_SCHEMA,
            MODULE8_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module8"]
        self.run_id = str(uuid.uuid4())
        self.model_id = str(uuid.uuid4())
        self.started = utcnow()
        self.model_directory = ROOT / "data" / "models"
        self.model_directory.mkdir(parents=True, exist_ok=True)

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m8_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m8_stage"
        )
        self.conn.unregister("_m8_stage")

    def training_frame(self) -> pd.DataFrame:
        horizon = int(self.config["predictive_engine"]["target_horizon_days"])
        frame = self.conn.execute(
            """
            SELECT s.*, p.excess_vs_btc_pct AS target_excess_return_pct,
                   p.forward_return_pct, p.positive_return,
                   p.outperformed_btc
            FROM model_snapshots_daily s
            JOIN signal_forward_performance p
              ON s.asset_id=p.asset_id
             AND s.observation_date=p.signal_date
            WHERE p.horizon_days=?
              AND p.completed=TRUE
              AND p.excess_vs_btc_pct IS NOT NULL
            ORDER BY s.observation_date, s.asset_id
            """,
            [horizon],
        ).fetchdf()
        if not frame.empty:
            frame["observation_date"] = pd.to_datetime(
                frame["observation_date"]
            )
        return frame

    def current_feature_frame(self) -> pd.DataFrame:
        frame = self.conn.execute(
            """
            SELECT *
            FROM latest_model_snapshots
            ORDER BY asset_id
            """
        ).fetchdf()
        if not frame.empty:
            frame["observation_date"] = pd.to_datetime(
                frame["observation_date"]
            )
        return frame

    def model(self) -> GradientBoostingRegressor:
        cfg = self.config["predictive_engine"]
        return GradientBoostingRegressor(
            loss="squared_error",
            learning_rate=float(cfg["learning_rate"]),
            n_estimators=int(cfg["max_iter"]),
            max_depth=3,
            min_samples_leaf=int(cfg["min_samples_leaf"]),
            min_samples_split=max(20, int(cfg["min_samples_leaf"])),
            max_features=None,
            random_state=int(cfg["random_seed"]),
            validation_fraction=0.15,
            n_iter_no_change=15,
            tol=1e-4,
        )

    def prepare(
        self,
        train: pd.DataFrame,
        test: pd.DataFrame | None = None,
    ) -> tuple[np.ndarray, np.ndarray | None, pd.Series]:
        medians = train[FEATURES].astype(float).median()
        x_train = train[FEATURES].astype(float).fillna(medians).to_numpy()
        x_test = None
        if test is not None:
            x_test = test[FEATURES].astype(float).fillna(medians).to_numpy()
        return x_train, x_test, medians

    def walk_forward(
        self, frame: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
        cfg = self.config["validation"]
        target = "target_excess_return_pct"
        training_days = int(cfg["training_days"])
        test_days = int(cfg["test_days"])
        step_days = int(cfg["step_days"])
        earliest = frame["observation_date"].min()
        latest = frame["observation_date"].max()
        test_start = earliest + pd.Timedelta(days=training_days)
        fold_number = 0
        folds: list[dict[str, Any]] = []
        regimes: list[dict[str, Any]] = []

        while test_start <= latest:
            train_start = test_start - pd.Timedelta(days=training_days)
            train_end = test_start - pd.Timedelta(days=1)
            test_end = test_start + pd.Timedelta(days=test_days - 1)
            train = frame[
                (frame["observation_date"] >= train_start)
                & (frame["observation_date"] <= train_end)
            ]
            test = frame[
                (frame["observation_date"] >= test_start)
                & (frame["observation_date"] <= test_end)
            ]
            if (
                len(train) >= int(cfg["minimum_training_rows"])
                and len(test) >= int(cfg["minimum_test_rows"])
            ):
                fold_number += 1
                x_train, x_test, _ = self.prepare(train, test)
                y_train = train[target].astype(float).to_numpy()
                y_test = test[target].astype(float).to_numpy()
                model = self.model()
                model.fit(x_train, y_train)
                prediction = model.predict(x_test)

                corr = safe_correlation(y_test, prediction)
                mae = float(mean_absolute_error(y_test, prediction))
                r2 = float(r2_score(y_test, prediction))
                directional = float(
                    (np.sign(y_test) == np.sign(prediction)).mean() * 100
                )
                ranking = pd.DataFrame({
                    "actual": y_test,
                    "prediction": prediction,
                }).sort_values("prediction")
                quintile = max(1, len(ranking) // 5)
                bottom = float(ranking.head(quintile)["actual"].mean())
                top = float(ranking.tail(quintile)["actual"].mean())

                folds.append({
                    "run_id": self.run_id,
                    "fold_number": fold_number,
                    "train_start": train_start.date(),
                    "train_end": train_end.date(),
                    "test_start": test_start.date(),
                    "test_end": min(test_end, latest).date(),
                    "training_rows": len(train),
                    "test_rows": len(test),
                    "correlation": corr,
                    "r_squared": r2,
                    "mean_absolute_error": mae,
                    "directional_accuracy_pct": directional,
                    "top_quintile_return_pct": top,
                    "bottom_quintile_return_pct": bottom,
                    "top_minus_bottom_pct": top - bottom,
                    "calculated_at_utc": utcnow(),
                })

                regime_test = test.copy()
                regime_test["prediction"] = prediction
                regime_test["actual"] = y_test
                minimum_regime = int(
                    self.config["regimes"]["minimum_rows_per_regime"]
                )
                for phase, group in regime_test.groupby("cycle_phase"):
                    if len(group) < minimum_regime:
                        continue
                    actual = group["actual"].to_numpy()
                    predicted = group["prediction"].to_numpy()
                    regimes.append({
                        "run_id": self.run_id,
                        "fold_number": fold_number,
                        "cycle_phase": phase,
                        "test_rows": len(group),
                        "correlation": safe_correlation(
                            actual, predicted
                        ),
                        "mean_absolute_error": float(
                            mean_absolute_error(actual, predicted)
                        ),
                        "directional_accuracy_pct": float(
                            (
                                np.sign(actual)
                                == np.sign(predicted)
                            ).mean()
                            * 100
                        ),
                        "average_actual_return_pct": float(
                            np.mean(actual)
                        ),
                        "average_predicted_return_pct": float(
                            np.mean(predicted)
                        ),
                        "calculated_at_utc": utcnow(),
                    })
            test_start += pd.Timedelta(days=step_days)

        fold_frame = pd.DataFrame(folds)
        regime_frame = pd.DataFrame(regimes)
        self.upsert("ml_walk_forward_results", fold_frame)
        self.upsert(
            "ml_walk_forward_regime_results", regime_frame
        )

        valid_correlations = (
            fold_frame["correlation"].dropna()
            if not fold_frame.empty
            else pd.Series(dtype=float)
        )
        summary = {
            "folds": float(len(fold_frame)),
            "average_correlation": (
                float(valid_correlations.mean())
                if not valid_correlations.empty
                else 0.0
            ),
            "average_directional": (
                float(
                    fold_frame["directional_accuracy_pct"].mean()
                )
                if not fold_frame.empty
                else 0.0
            ),
            "average_spread": (
                float(
                    fold_frame["top_minus_bottom_pct"].mean()
                )
                if not fold_frame.empty
                else 0.0
            ),
            "average_mae": (
                float(fold_frame["mean_absolute_error"].mean())
                if not fold_frame.empty
                else 0.0
            ),
        }
        return fold_frame, regime_frame, summary

    def promotion_weight(
        self, validation: dict[str, float]
    ) -> tuple[float, bool, str]:
        cfg = self.config["ensemble"]
        minimum_folds = int(
            self.config["validation"]["minimum_folds_for_promotion"]
        )
        folds = int(validation["folds"])
        correlation = validation["average_correlation"]
        directional = validation["average_directional"]
        spread = validation["average_spread"]

        if folds < minimum_folds:
            return 0.0, False, "Insufficient walk-forward folds."
        if correlation < float(cfg["minimum_positive_correlation"]):
            return (
                0.0,
                False,
                "Average walk-forward correlation did not clear the minimum.",
            )
        correlation_factor = clamp(
            correlation / 0.35 * 100, 0, 100
        ) / 100
        spread_factor = clamp(
            spread
            / float(cfg["target_top_minus_bottom_pct"])
            * 100,
            0,
            100,
        ) / 100
        direction_factor = clamp(
            directional
            / float(cfg["target_directional_accuracy_pct"])
            * 100,
            0,
            100,
        ) / 100
        evidence = (
            correlation_factor * 0.45
            + spread_factor * 0.35
            + direction_factor * 0.20
        )
        maximum = float(cfg["maximum_ml_weight"])
        minimum = float(cfg["minimum_ml_weight"])
        weight = max(minimum, min(maximum, maximum * evidence))
        promoted = bool(weight >= 0.10)
        reason = (
            "ML promoted with evidence-weighted ensemble influence."
            if promoted
            else "ML retained for research with minimal ensemble influence."
        )
        return float(weight), promoted, reason

    def train_final(
        self, frame: pd.DataFrame
    ) -> tuple[
        GradientBoostingRegressor,
        pd.Series,
        np.ndarray,
        np.ndarray,
        str,
    ]:
        target = "target_excess_return_pct"
        x, _, medians = self.prepare(frame)
        y = frame[target].astype(float).to_numpy()
        model = self.model()
        model.fit(x, y)
        prediction = model.predict(x)
        feature_hash = hashlib.sha256(
            json.dumps(FEATURES).encode("utf-8")
        ).hexdigest()
        artifact_path = (
            self.model_directory
            / f"crypto_ml_model_{self.run_id}.joblib"
        )
        joblib.dump(
            {
                "model": model,
                "features": FEATURES,
                "medians": medians.to_dict(),
                "target_horizon_days": int(
                    self.config["predictive_engine"][
                        "target_horizon_days"
                    ]
                ),
                "trained_at_utc": utcnow().isoformat(),
            },
            artifact_path,
        )

        self.conn.execute(
            "UPDATE ml_model_registry SET active=FALSE"
        )
        registry = pd.DataFrame([{
            "model_id": self.model_id,
            "run_id": self.run_id,
            "trained_at_utc": utcnow(),
            "target_horizon_days": int(
                self.config["predictive_engine"][
                    "target_horizon_days"
                ]
            ),
            "model_type": "GradientBoostingRegressor",
            "training_start": frame["observation_date"].min().date(),
            "training_end": frame["observation_date"].max().date(),
            "training_rows": len(frame),
            "feature_count": len(FEATURES),
            "feature_hash": feature_hash,
            "model_artifact_path": str(artifact_path),
            "training_r_squared": float(r2_score(y, prediction)),
            "training_mae": float(mean_absolute_error(y, prediction)),
            "active": True,
        }])
        self.upsert("ml_model_registry", registry)
        return model, medians, x, y, str(artifact_path)

    def global_importance(
        self,
        model: GradientBoostingRegressor,
        x: np.ndarray,
        y: np.ndarray,
    ) -> pd.DataFrame:
        cfg = self.config["explainability"]
        result = permutation_importance(
            model,
            x,
            y,
            n_repeats=int(cfg["global_permutation_repeats"]),
            random_state=int(
                self.config["predictive_engine"]["random_seed"]
            ),
            scoring="neg_mean_absolute_error",
        )
        importances = np.maximum(result.importances_mean, 0.0)
        total = float(importances.sum()) or 1.0
        rows = []
        ordering = np.argsort(-importances)
        ranks = {
            int(feature_index): rank + 1
            for rank, feature_index in enumerate(ordering)
        }
        for index, feature in enumerate(FEATURES):
            rows.append({
                "run_id": self.run_id,
                "feature_name": feature,
                "permutation_importance": float(
                    result.importances_mean[index]
                ),
                "permutation_std": float(
                    result.importances_std[index]
                ),
                "normalized_importance": float(
                    importances[index] / total * 100
                ),
                "rank": ranks[index],
                "calculated_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("ml_feature_importance", frame)
        return frame

    def approximate_shap(
        self,
        model: GradientBoostingRegressor,
        row: np.ndarray,
        baseline: np.ndarray,
        permutations: int,
        seed: int,
    ) -> tuple[np.ndarray, float, float]:
        """Monte Carlo Shapley approximation with batched predictions."""
        rng = np.random.default_rng(seed)
        contributions = np.zeros(len(row), dtype=float)
        baseline_prediction = float(
            model.predict(baseline.reshape(1, -1))[0]
        )
        model_prediction = float(
            model.predict(row.reshape(1, -1))[0]
        )
        for _ in range(permutations):
            ordering = rng.permutation(len(row))
            states = np.repeat(
                baseline.reshape(1, -1), len(row) + 1, axis=0
            )
            current = baseline.copy()
            for step, feature_index in enumerate(ordering, start=1):
                current = current.copy()
                current[feature_index] = row[feature_index]
                states[step] = current
            predictions = model.predict(states)
            deltas = np.diff(predictions)
            for feature_index, delta in zip(ordering, deltas):
                contributions[feature_index] += float(delta)
        contributions /= max(permutations, 1)
        return contributions, baseline_prediction, model_prediction

    def current_predictions(
        self,
        model: GradientBoostingRegressor,
        medians: pd.Series,
        training_frame: pd.DataFrame,
        ml_weight: float,
        promoted: bool,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        current = self.current_feature_frame()
        if current.empty:
            raise RuntimeError(
                "No current historical snapshots are available."
            )
        x_current = (
            current[FEATURES]
            .astype(float)
            .fillna(medians)
            .to_numpy()
        )
        prediction = model.predict(x_current)
        percentiles = pd.Series(prediction).rank(pct=True).to_numpy() * 100

        current_rules = self.conn.execute(
            """
            SELECT asset_id, overall_score, signal, confidence
            FROM latest_asset_signals
            """
        ).fetchdf()
        current = current.merge(
            current_rules, on="asset_id", how="left"
        )
        current["ml_prediction"] = prediction
        current["ml_percentile"] = percentiles

        train_target = training_frame[
            "target_excess_return_pct"
        ].astype(float)
        target_std = float(train_target.std(ddof=0)) or 1.0
        rows = []
        shap_rows = []
        baseline = (
            training_frame[FEATURES]
            .astype(float)
            .fillna(medians)
            .median()
            .to_numpy()
        )
        shap_cfg = self.config["explainability"]
        permutations = int(shap_cfg["shap_permutations"])
        top_features = int(shap_cfg["top_features_per_asset"])
        base_seed = int(
            self.config["predictive_engine"]["random_seed"]
        )

        for row_index, row in current.iterrows():
            rules_score = float(
                row["overall_score"]
                if pd.notna(row["overall_score"])
                else row["historical_overall_score"]
            )
            rules_confidence = float(
                row["confidence"]
                if pd.notna(row["confidence"])
                else 50.0
            )
            percentile = float(row["ml_percentile"])
            ml_score = percentile
            ensemble_score = (
                rules_score * (1.0 - ml_weight)
                + ml_score * ml_weight
            )
            prediction_value = float(row["ml_prediction"])
            distance_strength = min(
                1.0, abs(prediction_value) / target_std
            )
            ml_confidence = clamp(
                45
                + distance_strength * 25
                + (15 if promoted else 0),
                35,
                90,
            )
            ensemble_confidence = clamp(
                rules_confidence * (1.0 - ml_weight)
                + ml_confidence * ml_weight,
                35,
                95,
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": row["asset_id"],
                "observation_date": row["observation_date"].date(),
                "rules_score": rules_score,
                "rules_signal": (
                    row["signal"]
                    if pd.notna(row["signal"])
                    else signal_from_score(rules_score)
                ),
                "ml_predicted_excess_return_pct": prediction_value,
                "ml_percentile_rank": percentile,
                "ml_signal": ml_signal_from_percentile(percentile),
                "ml_confidence": ml_confidence,
                "ensemble_score": ensemble_score,
                "ensemble_signal": signal_from_score(ensemble_score),
                "ensemble_confidence": ensemble_confidence,
                "ml_weight": ml_weight,
                "promotion_status": (
                    "PROMOTED" if promoted else "RESEARCH_ONLY"
                ),
                "calculated_at_utc": utcnow(),
            })

            contributions, baseline_prediction, model_prediction = (
                self.approximate_shap(
                    model=model,
                    row=x_current[row_index],
                    baseline=baseline,
                    permutations=permutations,
                    seed=base_seed + row_index,
                )
            )
            ordering = np.argsort(-np.abs(contributions))[:top_features]
            for rank, feature_index in enumerate(ordering, start=1):
                value = float(x_current[row_index][feature_index])
                contribution = float(contributions[feature_index])
                shap_rows.append({
                    "run_id": self.run_id,
                    "asset_id": row["asset_id"],
                    "observation_date": row["observation_date"].date(),
                    "feature_name": FEATURES[feature_index],
                    "feature_value": value,
                    "shap_value": contribution,
                    "absolute_shap_value": abs(contribution),
                    "direction": (
                        "POSITIVE"
                        if contribution > 0
                        else "NEGATIVE"
                        if contribution < 0
                        else "NEUTRAL"
                    ),
                    "rank": rank,
                    "baseline_prediction": baseline_prediction,
                    "model_prediction": model_prediction,
                    "calculated_at_utc": utcnow(),
                })

        prediction_frame = pd.DataFrame(rows)
        shap_frame = pd.DataFrame(shap_rows)
        self.upsert("ml_predictions_current", prediction_frame)
        self.upsert("ml_shap_explanations", shap_frame)
        return prediction_frame, shap_frame

    def run(self) -> dict[str, Any]:
        frame = self.training_frame()
        minimum = int(
            self.config["predictive_engine"][
                "minimum_training_rows"
            ]
        )
        if len(frame) < minimum:
            raise RuntimeError(
                f"Module 8 requires at least {minimum} completed "
                f"training rows; found {len(frame)}."
            )

        self.conn.execute(
            """
            INSERT INTO module8_runs(
                run_id,started_at_utc,status,target_horizon_days,
                training_rows,validation_folds,ml_ensemble_weight,
                promoted,model_artifact_path,notes,platform_version
            ) VALUES (?,?,'RUNNING',?,0,0,0,FALSE,NULL,NULL,'4.0.0')
            """,
            [
                self.run_id,
                self.started,
                int(
                    self.config["predictive_engine"][
                        "target_horizon_days"
                    ]
                ),
            ],
        )

        folds, regimes, validation = self.walk_forward(frame)
        ml_weight, promoted, promotion_reason = (
            self.promotion_weight(validation)
        )
        model, medians, x, y, artifact_path = self.train_final(frame)
        importance = self.global_importance(model, x, y)
        predictions, shap = self.current_predictions(
            model=model,
            medians=medians,
            training_frame=frame,
            ml_weight=ml_weight,
            promoted=promoted,
        )

        ensemble_summary = pd.DataFrame([{
            "run_id": self.run_id,
            "validation_folds": int(validation["folds"]),
            "average_correlation": validation["average_correlation"],
            "average_directional_accuracy_pct": validation[
                "average_directional"
            ],
            "average_top_minus_bottom_pct": validation[
                "average_spread"
            ],
            "average_mae": validation["average_mae"],
            "recommended_ml_weight": ml_weight,
            "promoted": promoted,
            "promotion_reason": promotion_reason,
            "calculated_at_utc": utcnow(),
        }])
        self.upsert(
            "ensemble_validation_summary", ensemble_summary
        )

        notes = (
            f"training_rows={len(frame)}; folds={len(folds)}; "
            f"regime_rows={len(regimes)}; ml_weight={ml_weight:.3f}; "
            f"promoted={promoted}; predictions={len(predictions)}; "
            f"explanations={len(shap)}."
        )
        self.conn.execute(
            """
            UPDATE module8_runs
            SET completed_at_utc=?,status='SUCCESS',
                training_rows=?,validation_folds=?,
                ml_ensemble_weight=?,promoted=?,
                model_artifact_path=?,notes=?
            WHERE run_id=?
            """,
            [
                utcnow(),
                len(frame),
                len(folds),
                ml_weight,
                promoted,
                artifact_path,
                notes,
                self.run_id,
            ],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "training_rows": len(frame),
            "validation_folds": len(folds),
            "ml_weight": ml_weight,
            "promoted": promoted,
            "prediction_count": len(predictions),
            "explanation_count": len(shap),
            "model_artifact_path": artifact_path,
        }

def run_module8() -> dict[str, Any]:
    return Module8Runner().run()
