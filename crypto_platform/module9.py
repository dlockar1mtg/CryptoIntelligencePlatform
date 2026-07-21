from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.metrics import (
    balanced_accuracy_score,
    mean_absolute_error,
    roc_auc_score,
)

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA, FEATURES
from crypto_platform.module8 import MODULE8_SCHEMA

MODULE9_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module9_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    target_horizon_days INTEGER,
    training_rows INTEGER,
    validation_folds INTEGER,
    promoted BOOLEAN,
    predictive_weight DOUBLE,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS calibrated_walk_forward_results(
    run_id VARCHAR,
    fold_number INTEGER,
    train_start DATE,
    train_end DATE,
    test_start DATE,
    test_end DATE,
    training_rows INTEGER,
    test_rows INTEGER,
    regression_mae DOUBLE,
    raw_regression_mae DOUBLE,
    outperform_auc DOUBLE,
    positive_return_auc DOUBLE,
    outperform_balanced_accuracy_pct DOUBLE,
    positive_balanced_accuracy_pct DOUBLE,
    high_low_outperform_spread_pct DOUBLE,
    high_low_positive_spread_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number)
);

CREATE TABLE IF NOT EXISTS regime_model_validation(
    run_id VARCHAR,
    cycle_phase VARCHAR,
    sample_count INTEGER,
    outperform_auc DOUBLE,
    positive_return_auc DOUBLE,
    average_excess_return_pct DOUBLE,
    positive_return_rate_pct DOUBLE,
    usable BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, cycle_phase)
);

CREATE TABLE IF NOT EXISTS predictive_classification_current(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    cycle_phase VARCHAR,
    calibrated_excess_return_pct DOUBLE,
    probability_outperform_btc DOUBLE,
    probability_positive_return DOUBLE,
    global_probability_outperform DOUBLE,
    regime_probability_outperform DOUBLE,
    global_probability_positive DOUBLE,
    regime_probability_positive DOUBLE,
    predictive_score DOUBLE,
    predictive_signal VARCHAR,
    predictive_confidence DOUBLE,
    rules_score DOUBLE,
    rules_signal VARCHAR,
    final_ensemble_score DOUBLE,
    final_ensemble_signal VARCHAR,
    final_ensemble_confidence DOUBLE,
    predictive_weight DOUBLE,
    promotion_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS probability_calibration_bins(
    run_id VARCHAR,
    target_name VARCHAR,
    probability_bin_low DOUBLE,
    probability_bin_high DOUBLE,
    sample_count INTEGER,
    average_predicted_probability DOUBLE,
    observed_rate DOUBLE,
    calibration_error DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, target_name, probability_bin_low)
);

CREATE TABLE IF NOT EXISTS predictive_promotion_summary(
    run_id VARCHAR PRIMARY KEY,
    validation_folds INTEGER,
    average_outperform_auc DOUBLE,
    average_positive_auc DOUBLE,
    average_outperform_balanced_accuracy_pct DOUBLE,
    average_positive_balanced_accuracy_pct DOUBLE,
    average_probability_spread_pct DOUBLE,
    recommended_predictive_weight DOUBLE,
    promoted BOOLEAN,
    promotion_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_calibrated_walk_forward AS
SELECT x.*
FROM calibrated_walk_forward_results x
JOIN (
    SELECT run_id FROM module9_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_predictive_classifications AS
SELECT x.*
FROM predictive_classification_current x
JOIN (
    SELECT run_id FROM module9_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_regime_model_validation AS
SELECT x.*
FROM regime_model_validation x
JOIN (
    SELECT run_id FROM module9_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_probability_calibration AS
SELECT x.*
FROM probability_calibration_bins x
JOIN (
    SELECT run_id FROM module9_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_predictive_promotion AS
SELECT x.*
FROM predictive_promotion_summary x
JOIN (
    SELECT run_id FROM module9_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def safe_auc(y: np.ndarray, p: np.ndarray) -> float | None:
    if len(np.unique(y)) < 2:
        return None
    return float(roc_auc_score(y, p))

def score_signal(score: float) -> str:
    if score >= 80:
        return "STRONG_BUY"
    if score >= 68:
        return "BUY"
    if score >= 48:
        return "HOLD"
    if score >= 35:
        return "REDUCE"
    return "AVOID"

class Module9Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module9"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m9_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m9_stage"
        )
        self.conn.unregister("_m9_stage")

    def frame(self) -> pd.DataFrame:
        horizon = int(
            self.config["calibrated_prediction"]["target_horizon_days"]
        )
        frame = self.conn.execute(
            """
            SELECT s.*, p.excess_vs_btc_pct,
                   CAST(p.outperformed_btc AS INTEGER) AS outperform_target,
                   CAST(p.positive_return AS INTEGER) AS positive_target
            FROM model_snapshots_daily s
            JOIN signal_forward_performance p
              ON s.asset_id=p.asset_id
             AND s.observation_date=p.signal_date
            WHERE p.horizon_days=?
              AND p.completed=TRUE
              AND p.excess_vs_btc_pct IS NOT NULL
              AND p.outperformed_btc IS NOT NULL
              AND p.positive_return IS NOT NULL
            ORDER BY s.observation_date, s.asset_id
            """,
            [horizon],
        ).fetchdf()
        if not frame.empty:
            frame["observation_date"] = pd.to_datetime(
                frame["observation_date"]
            )
        return frame

    def prepare(
        self, train: pd.DataFrame, test: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray, pd.Series]:
        medians = train[FEATURES].astype(float).median()
        x_train = (
            train[FEATURES].astype(float).fillna(medians).to_numpy()
        )
        x_test = (
            test[FEATURES].astype(float).fillna(medians).to_numpy()
        )
        return x_train, x_test, medians

    def regressor(self) -> HistGradientBoostingRegressor:
        cfg = self.config["classification"]
        return HistGradientBoostingRegressor(
            learning_rate=float(cfg["learning_rate"]),
            max_iter=int(cfg["max_iter"]),
            max_leaf_nodes=int(cfg["max_leaf_nodes"]),
            min_samples_leaf=int(cfg["min_samples_leaf"]),
            l2_regularization=float(cfg["l2_regularization"]),
            random_state=int(cfg["random_seed"]),
            early_stopping=True,
        )

    def classifier(self) -> HistGradientBoostingClassifier:
        cfg = self.config["classification"]
        return HistGradientBoostingClassifier(
            learning_rate=float(cfg["learning_rate"]),
            max_iter=int(cfg["max_iter"]),
            max_leaf_nodes=int(cfg["max_leaf_nodes"]),
            min_samples_leaf=int(cfg["min_samples_leaf"]),
            l2_regularization=float(cfg["l2_regularization"]),
            random_state=int(cfg["random_seed"]),
            early_stopping=True,
        )

    def target_bounds(self, train: pd.DataFrame) -> tuple[float, float]:
        cfg = self.config["calibrated_prediction"]
        target = train["excess_vs_btc_pct"].astype(float)
        low = float(target.quantile(
            float(cfg["lower_winsor_quantile"])
        ))
        high = float(target.quantile(
            float(cfg["upper_winsor_quantile"])
        ))
        absolute = float(cfg["max_absolute_prediction_pct"])
        return max(-absolute, low), min(absolute, high)

    def probability_spread(
        self, actual: np.ndarray, probability: np.ndarray
    ) -> float:
        frame = pd.DataFrame({
            "actual": actual, "probability": probability
        }).sort_values("probability")
        size = max(1, len(frame) // 5)
        return float(
            (
                frame.tail(size)["actual"].mean()
                - frame.head(size)["actual"].mean()
            ) * 100
        )

    def calibration_rows(
        self, target_name: str, actual: list[int],
        predicted: list[float]
    ) -> list[dict[str, Any]]:
        frame = pd.DataFrame({
            "actual": actual, "predicted": predicted
        })
        rows = []
        for low in np.arange(0.0, 1.0, 0.1):
            high = low + 0.1
            group = frame[
                (frame["predicted"] >= low)
                & (
                    (frame["predicted"] < high)
                    if high < 1.0
                    else (frame["predicted"] <= high)
                )
            ]
            if group.empty:
                continue
            average = float(group["predicted"].mean())
            observed = float(group["actual"].mean())
            rows.append({
                "run_id": self.run_id,
                "target_name": target_name,
                "probability_bin_low": float(low),
                "probability_bin_high": float(high),
                "sample_count": len(group),
                "average_predicted_probability": average,
                "observed_rate": observed,
                "calibration_error": abs(average - observed),
                "calculated_at_utc": utcnow(),
            })
        return rows

    def walk_forward(
        self, frame: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
        cfg = self.config["walk_forward"]
        training_days = int(cfg["training_days"])
        test_days = int(cfg["test_days"])
        step_days = int(cfg["step_days"])
        earliest = frame["observation_date"].min()
        latest = frame["observation_date"].max()
        test_start = earliest + pd.Timedelta(days=training_days)
        folds = []
        calibration = []
        all_out_actual, all_out_pred = [], []
        all_pos_actual, all_pos_pred = [], []
        fold_number = 0

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
                low, high = self.target_bounds(train)
                y_reg_raw = train["excess_vs_btc_pct"].astype(float).to_numpy()
                y_reg = np.clip(y_reg_raw, low, high)
                y_test_reg = test["excess_vs_btc_pct"].astype(float).to_numpy()
                y_out = train["outperform_target"].astype(int).to_numpy()
                y_pos = train["positive_target"].astype(int).to_numpy()
                y_test_out = test["outperform_target"].astype(int).to_numpy()
                y_test_pos = test["positive_target"].astype(int).to_numpy()

                reg = self.regressor().fit(x_train, y_reg)
                out = self.classifier().fit(x_train, y_out)
                pos = self.classifier().fit(x_train, y_pos)

                raw_prediction = reg.predict(x_test)
                calibrated_prediction = np.clip(raw_prediction, low, high)
                p_out = out.predict_proba(x_test)[:, 1]
                p_pos = pos.predict_proba(x_test)[:, 1]

                all_out_actual.extend(y_test_out.tolist())
                all_out_pred.extend(p_out.tolist())
                all_pos_actual.extend(y_test_pos.tolist())
                all_pos_pred.extend(p_pos.tolist())

                folds.append({
                    "run_id": self.run_id,
                    "fold_number": fold_number,
                    "train_start": train_start.date(),
                    "train_end": train_end.date(),
                    "test_start": test_start.date(),
                    "test_end": min(test_end, latest).date(),
                    "training_rows": len(train),
                    "test_rows": len(test),
                    "regression_mae": float(mean_absolute_error(
                        y_test_reg, calibrated_prediction
                    )),
                    "raw_regression_mae": float(mean_absolute_error(
                        y_test_reg, raw_prediction
                    )),
                    "outperform_auc": safe_auc(y_test_out, p_out),
                    "positive_return_auc": safe_auc(y_test_pos, p_pos),
                    "outperform_balanced_accuracy_pct": float(
                        balanced_accuracy_score(
                            y_test_out, p_out >= 0.5
                        ) * 100
                    ),
                    "positive_balanced_accuracy_pct": float(
                        balanced_accuracy_score(
                            y_test_pos, p_pos >= 0.5
                        ) * 100
                    ),
                    "high_low_outperform_spread_pct": self.probability_spread(
                        y_test_out, p_out
                    ),
                    "high_low_positive_spread_pct": self.probability_spread(
                        y_test_pos, p_pos
                    ),
                    "calculated_at_utc": utcnow(),
                })
            test_start += pd.Timedelta(days=step_days)

        fold_frame = pd.DataFrame(folds)
        self.upsert("calibrated_walk_forward_results", fold_frame)

        calibration.extend(self.calibration_rows(
            "OUTPERFORM_BTC", all_out_actual, all_out_pred
        ))
        calibration.extend(self.calibration_rows(
            "POSITIVE_RETURN", all_pos_actual, all_pos_pred
        ))
        calibration_frame = pd.DataFrame(calibration)
        self.upsert("probability_calibration_bins", calibration_frame)

        summary = {
            "folds": len(fold_frame),
            "out_auc": float(
                fold_frame["outperform_auc"].dropna().mean()
            ) if not fold_frame.empty else 0.0,
            "pos_auc": float(
                fold_frame["positive_return_auc"].dropna().mean()
            ) if not fold_frame.empty else 0.0,
            "out_bal": float(
                fold_frame[
                    "outperform_balanced_accuracy_pct"
                ].mean()
            ) if not fold_frame.empty else 0.0,
            "pos_bal": float(
                fold_frame[
                    "positive_balanced_accuracy_pct"
                ].mean()
            ) if not fold_frame.empty else 0.0,
            "spread": float(
                fold_frame[[
                    "high_low_outperform_spread_pct",
                    "high_low_positive_spread_pct",
                ]].mean(axis=1).mean()
            ) if not fold_frame.empty else 0.0,
        }
        return fold_frame, calibration_frame, summary

    def promotion(
        self, summary: dict[str, float]
    ) -> tuple[float, bool, str]:
        cfg = self.config["promotion"]
        minimum_folds = int(
            self.config["walk_forward"][
                "minimum_folds_for_promotion"
            ]
        )
        if summary["folds"] < minimum_folds:
            return 0.0, False, "Insufficient walk-forward folds."
        average_auc = (summary["out_auc"] + summary["pos_auc"]) / 2
        average_bal = (summary["out_bal"] + summary["pos_bal"]) / 2
        if average_auc < float(cfg["minimum_auc"]):
            return 0.0, False, "Classification AUC remained below threshold."
        if average_bal < float(
            cfg["minimum_balanced_accuracy_pct"]
        ):
            return 0.0, False, "Balanced accuracy remained below threshold."
        if summary["spread"] < float(
            cfg["minimum_probability_spread_pct"]
        ):
            return 0.0, False, "Probability ranking spread remained weak."
        evidence = np.mean([
            min(1.0, max(0.0, (average_auc - 0.50) / 0.20)),
            min(1.0, max(0.0, (average_bal - 50.0) / 20.0)),
            min(1.0, max(
                0.0,
                summary["spread"]
                / float(cfg["minimum_probability_spread_pct"])
            )),
        ])
        weight = min(
            float(cfg["maximum_predictive_weight"]),
            float(cfg["maximum_predictive_weight"]) * evidence,
        )
        return (
            float(weight),
            bool(weight >= 0.10),
            "Classification evidence cleared promotion thresholds.",
        )

    def regime_validation(self, frame: pd.DataFrame) -> pd.DataFrame:
        minimum = int(
            self.config["regimes"]["minimum_training_rows"]
        )
        rows = []
        for phase, group in frame.groupby("cycle_phase"):
            if len(group) < minimum:
                continue
            rows.append({
                "run_id": self.run_id,
                "cycle_phase": phase,
                "sample_count": len(group),
                "outperform_auc": None,
                "positive_return_auc": None,
                "average_excess_return_pct": float(
                    group["excess_vs_btc_pct"].mean()
                ),
                "positive_return_rate_pct": float(
                    group["positive_target"].mean() * 100
                ),
                "usable": True,
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("regime_model_validation", result)
        return result

    def current_predictions(
        self, frame: pd.DataFrame, weight: float, promoted: bool
    ) -> pd.DataFrame:
        current = self.conn.execute(
            "SELECT * FROM latest_model_snapshots ORDER BY asset_id"
        ).fetchdf()
        rules = self.conn.execute(
            """
            SELECT asset_id, overall_score, signal, confidence
            FROM latest_asset_signals
            """
        ).fetchdf()
        current = current.merge(rules, on="asset_id", how="left")
        medians = frame[FEATURES].astype(float).median()
        x_train = (
            frame[FEATURES].astype(float).fillna(medians).to_numpy()
        )
        x_current = (
            current[FEATURES].astype(float).fillna(medians).to_numpy()
        )
        low, high = self.target_bounds(frame)

        reg = self.regressor().fit(
            x_train,
            np.clip(
                frame["excess_vs_btc_pct"].astype(float).to_numpy(),
                low, high,
            ),
        )
        out_global = self.classifier().fit(
            x_train,
            frame["outperform_target"].astype(int).to_numpy(),
        )
        pos_global = self.classifier().fit(
            x_train,
            frame["positive_target"].astype(int).to_numpy(),
        )
        regression = np.clip(reg.predict(x_current), low, high)
        p_out_global = out_global.predict_proba(x_current)[:, 1]
        p_pos_global = pos_global.predict_proba(x_current)[:, 1]

        regime_weight = float(
            self.config["regimes"]["blend_weight"]
        )
        minimum = int(
            self.config["regimes"]["minimum_training_rows"]
        )
        rows = []
        for index, row in current.iterrows():
            phase_group = frame[frame["cycle_phase"] == row["cycle_phase"]]
            regime_out = None
            regime_pos = None
            if (
                len(phase_group) >= minimum
                and phase_group["outperform_target"].nunique() == 2
                and phase_group["positive_target"].nunique() == 2
            ):
                x_phase = (
                    phase_group[FEATURES]
                    .astype(float).fillna(medians).to_numpy()
                )
                x_one = x_current[index].reshape(1, -1)
                regime_out = float(
                    self.classifier()
                    .fit(
                        x_phase,
                        phase_group["outperform_target"]
                        .astype(int).to_numpy(),
                    )
                    .predict_proba(x_one)[0, 1]
                )
                regime_pos = float(
                    self.classifier()
                    .fit(
                        x_phase,
                        phase_group["positive_target"]
                        .astype(int).to_numpy(),
                    )
                    .predict_proba(x_one)[0, 1]
                )
            p_out = float(p_out_global[index])
            p_pos = float(p_pos_global[index])
            if regime_out is not None:
                p_out = (
                    p_out * (1 - regime_weight)
                    + regime_out * regime_weight
                )
            if regime_pos is not None:
                p_pos = (
                    p_pos * (1 - regime_weight)
                    + regime_pos * regime_weight
                )

            predictive_score = clamp(
                50
                + (p_out - 0.5) * 55
                + (p_pos - 0.5) * 35
                + float(regression[index]) * 0.08
            )
            rules_score = float(row["overall_score"])
            final_score = (
                rules_score * (1 - weight)
                + predictive_score * weight
            )
            probability_margin = (
                abs(p_out - 0.5) + abs(p_pos - 0.5)
            ) / 2
            predictive_conf = clamp(
                45 + probability_margin * 70
                + (10 if promoted else 0),
                float(self.config["confidence"]["minimum_confidence"]),
                float(self.config["confidence"]["maximum_confidence"]),
            )
            rules_conf = float(row["confidence"])
            final_conf = clamp(
                rules_conf * (1 - weight)
                + predictive_conf * weight,
                35, 95,
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": row["asset_id"],
                "observation_date": pd.to_datetime(
                    row["observation_date"]
                ).date(),
                "cycle_phase": row["cycle_phase"],
                "calibrated_excess_return_pct": float(regression[index]),
                "probability_outperform_btc": p_out,
                "probability_positive_return": p_pos,
                "global_probability_outperform": float(
                    p_out_global[index]
                ),
                "regime_probability_outperform": regime_out,
                "global_probability_positive": float(
                    p_pos_global[index]
                ),
                "regime_probability_positive": regime_pos,
                "predictive_score": predictive_score,
                "predictive_signal": score_signal(predictive_score),
                "predictive_confidence": predictive_conf,
                "rules_score": rules_score,
                "rules_signal": row["signal"],
                "final_ensemble_score": final_score,
                "final_ensemble_signal": score_signal(final_score),
                "final_ensemble_confidence": final_conf,
                "predictive_weight": weight,
                "promotion_status": (
                    "PROMOTED" if promoted else "RESEARCH_ONLY"
                ),
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("predictive_classification_current", result)
        return result

    def run(self) -> dict[str, Any]:
        frame = self.frame()
        minimum = int(
            self.config["calibrated_prediction"][
                "minimum_training_rows"
            ]
        )
        if len(frame) < minimum:
            raise RuntimeError(
                f"Module 9 requires {minimum} rows; found {len(frame)}."
            )
        horizon = int(
            self.config["calibrated_prediction"][
                "target_horizon_days"
            ]
        )
        self.conn.execute(
            """
            INSERT INTO module9_runs(
                run_id,started_at_utc,status,target_horizon_days,
                training_rows,validation_folds,promoted,
                predictive_weight,notes,platform_version
            ) VALUES (?,?,'RUNNING',?,0,0,FALSE,0,NULL,'4.0.0')
            """,
            [self.run_id, self.started, horizon],
        )

        folds, calibration, summary = self.walk_forward(frame)
        weight, promoted, reason = self.promotion(summary)
        regimes = self.regime_validation(frame)
        predictions = self.current_predictions(
            frame, weight, promoted
        )

        promotion = pd.DataFrame([{
            "run_id": self.run_id,
            "validation_folds": summary["folds"],
            "average_outperform_auc": summary["out_auc"],
            "average_positive_auc": summary["pos_auc"],
            "average_outperform_balanced_accuracy_pct": summary["out_bal"],
            "average_positive_balanced_accuracy_pct": summary["pos_bal"],
            "average_probability_spread_pct": summary["spread"],
            "recommended_predictive_weight": weight,
            "promoted": promoted,
            "promotion_reason": reason,
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("predictive_promotion_summary", promotion)

        notes = (
            f"rows={len(frame)}; folds={len(folds)}; "
            f"calibration_bins={len(calibration)}; regimes={len(regimes)}; "
            f"predictions={len(predictions)}; weight={weight:.3f}; "
            f"promoted={promoted}."
        )
        self.conn.execute(
            """
            UPDATE module9_runs
            SET completed_at_utc=?,status='SUCCESS',
                training_rows=?,validation_folds=?,promoted=?,
                predictive_weight=?,notes=?
            WHERE run_id=?
            """,
            [
                utcnow(), len(frame), len(folds), promoted,
                weight, notes, self.run_id,
            ],
        )
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "training_rows": len(frame),
            "validation_folds": len(folds),
            "predictive_weight": weight,
            "promoted": promoted,
            "prediction_count": len(predictions),
        }

def run_module9() -> dict[str, Any]:
    return Module9Runner().run()
