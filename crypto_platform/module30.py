from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss

from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA
from crypto_platform.module27 import MODULE27_SCHEMA
from crypto_platform.ml.classes import canonical_classes
from crypto_platform.module29 import MODULE29_SCHEMA
from crypto_platform.ml.datasets import aligned_feature_label_frame
from crypto_platform.ml.models import (
    fit_clean_models,
    predict_component_probabilities,
    blend_probabilities,
    probability_agreement,
)
from crypto_platform.ml.calibration import fit_multiclass_calibrator
from crypto_platform.ml.validation import (
    choose_blend_weight,
    multiclass_brier_score,
    validate_probability_matrix,
)
from crypto_platform.ml.drift import (
    feature_drift_table,
    drift_status,
)
from crypto_platform.ml.explainability import (
    counterfactual_feature_contributions,
)
from crypto_platform.ml.registry import (
    EXPERIMENT_REGISTRY_SCHEMA,
    start_experiment,
    complete_experiment,
)

MODULE30_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module30_runs(
    run_id VARCHAR PRIMARY KEY,
    experiment_id VARCHAR,
    source_module29_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    stable_features INTEGER,
    outer_folds INTEGER,
    historical_rows INTEGER,
    clean_accuracy_pct DOUBLE,
    legacy_accuracy_pct DOUBLE,
    calibrated_log_loss DOUBLE,
    calibrated_brier_score DOUBLE,
    current_regime VARCHAR,
    current_probability DOUBLE,
    confidence_level VARCHAR,
    model_agreement DOUBLE,
    drift_status VARCHAR,
    promotion_status VARCHAR,
    validation_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS clean_regime_history(
    run_id VARCHAR,
    observation_date DATE,
    outer_fold INTEGER,
    actual_legacy_regime VARCHAR,
    clean_regime VARCHAR,
    secondary_regime VARCHAR,
    clean_probability DOUBLE,
    secondary_probability DOUBLE,
    confidence_level VARCHAR,
    model_agreement DOUBLE,
    gradient_weight DOUBLE,
    calibration_applied BOOLEAN,
    label_match BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS clean_probability_history(
    run_id VARCHAR,
    observation_date DATE,
    regime VARCHAR,
    probability DOUBLE,
    probability_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, regime)
);

CREATE TABLE IF NOT EXISTS clean_regime_current(
    run_id VARCHAR PRIMARY KEY,
    observation_date DATE,
    clean_regime VARCHAR,
    secondary_regime VARCHAR,
    clean_probability DOUBLE,
    secondary_probability DOUBLE,
    confidence_level VARCHAR,
    model_agreement DOUBLE,
    historical_reliability DOUBLE,
    feature_drift_score DOUBLE,
    drift_status VARCHAR,
    legacy_regime VARCHAR,
    agrees_with_legacy BOOLEAN,
    promotion_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS clean_probability_current(
    run_id VARCHAR,
    regime VARCHAR,
    probability DOUBLE,
    probability_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, regime)
);

CREATE TABLE IF NOT EXISTS clean_feature_contributions(
    run_id VARCHAR,
    observation_date DATE,
    feature_key VARCHAR,
    feature_value DOUBLE,
    reference_value DOUBLE,
    probability_contribution DOUBLE,
    direction VARCHAR,
    absolute_contribution DOUBLE,
    rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, feature_key)
);

CREATE TABLE IF NOT EXISTS clean_feature_drift(
    run_id VARCHAR,
    observation_date DATE,
    feature_key VARCHAR,
    training_mean DOUBLE,
    training_std DOUBLE,
    current_value DOUBLE,
    current_z_score DOUBLE,
    psi DOUBLE,
    feature_drift_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, feature_key)
);

CREATE TABLE IF NOT EXISTS clean_legacy_benchmark(
    run_id VARCHAR PRIMARY KEY,
    test_rows INTEGER,
    clean_accuracy_pct DOUBLE,
    legacy_self_accuracy_pct DOUBLE,
    clean_log_loss DOUBLE,
    clean_brier_score DOUBLE,
    current_clean_regime VARCHAR,
    current_legacy_regime VARCHAR,
    current_agreement BOOLEAN,
    relative_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS clean_model_disagreement(
    run_id VARCHAR,
    observation_date DATE,
    gradient_regime VARCHAR,
    elastic_regime VARCHAR,
    gradient_probability DOUBLE,
    elastic_probability DOUBLE,
    probability_agreement DOUBLE,
    total_variation_distance DOUBLE,
    blended_regime VARCHAR,
    blended_probability DOUBLE,
    disagreement_flag BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS clean_validation_folds(
    run_id VARCHAR,
    outer_fold INTEGER,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    test_rows INTEGER,
    selected_gradient_weight DOUBLE,
    validation_accuracy_pct DOUBLE,
    test_accuracy_pct DOUBLE,
    test_log_loss DOUBLE,
    test_brier_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, outer_fold)
);

CREATE OR REPLACE VIEW latest_clean_regime_history AS
SELECT * FROM clean_regime_history
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_clean_probability_history AS
SELECT * FROM clean_probability_history
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date, probability_rank;

CREATE OR REPLACE VIEW latest_clean_regime_current AS
SELECT * FROM clean_regime_current
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
);

CREATE OR REPLACE VIEW latest_clean_probability_current AS
SELECT * FROM clean_probability_current
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY probability_rank;

CREATE OR REPLACE VIEW latest_clean_feature_contributions AS
SELECT * FROM clean_feature_contributions
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY rank;

CREATE OR REPLACE VIEW latest_clean_feature_drift AS
SELECT * FROM clean_feature_drift
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY feature_drift_score DESC;

CREATE OR REPLACE VIEW latest_clean_legacy_benchmark AS
SELECT * FROM clean_legacy_benchmark
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
);

CREATE OR REPLACE VIEW latest_clean_model_disagreement AS
SELECT * FROM clean_model_disagreement
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_clean_validation_folds AS
SELECT * FROM clean_validation_folds
WHERE run_id=(
    SELECT run_id FROM module30_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY outer_fold;
"""


def utcnow():
    return datetime.now(timezone.utc)


def confidence_level(
    probability: float,
    agreement: float,
    drift: str,
) -> str:
    if drift == "HIGH":
        return "LOW"
    if probability >= 0.70 and agreement >= 0.80 and drift == "LOW":
        return "HIGH"
    if probability >= 0.50 and agreement >= 0.55:
        return "MODERATE"
    return "LOW"


class Module30Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE25_SCHEMA)
        self.conn.execute(MODULE27_SCHEMA)
        self.conn.execute(MODULE29_SCHEMA)
        self.conn.execute(EXPERIMENT_REGISTRY_SCHEMA)
        self.conn.execute(MODULE30_SCHEMA)
        self.cfg = self.settings["module30"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

        row = self.conn.execute(
            """
            SELECT
                summary.run_id,
                summary.stable_feature_list,
                runs.source_module27_run_id
            FROM m29_research_summary AS summary
            JOIN module29_runs AS runs
              ON runs.run_id = summary.run_id
            WHERE summary.validation_status='PASSED'
              AND runs.status='SUCCESS'
            ORDER BY summary.calculated_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError(
                "No passed Module 29 feature registry is available."
            )
        self.source_m29 = str(row[0])
        self.features = list(json.loads(row[1]))
        self.source_m27 = str(row[2])
        minimum = int(self.cfg["features"]["minimum_stable_features"])
        if len(self.features) < minimum:
            raise RuntimeError(
                f"Module 29 retained only {len(self.features)} features; "
                f"at least {minimum} are required."
            )

        self.experiment_id = start_experiment(
            self.conn,
            module_name="Module 30 Clean Regime Engine",
            release_version="8.1.1",
            feature_set=self.features,
            hyperparameters=self.cfg,
        )

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m30_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m30_stage"
        )
        self.conn.unregister("_m30_stage")

    def data(self):
        core_features = self.conn.execute(
            """
            SELECT *
            FROM m25_regime_features
            WHERE run_id=(
                SELECT source_module25_run_id
                FROM module29_runs
                WHERE run_id=?
            )
            ORDER BY observation_date
            """,
            [self.source_m29],
        ).fetchdf()

        representation_features = self.conn.execute(
            """
            SELECT *
            FROM m27_representation_features
            WHERE run_id=?
            ORDER BY observation_date
            """,
            [self.source_m27],
        ).fetchdf()

        labels = self.conn.execute(
            """
            SELECT observation_date,
                   dominant_regime
            FROM m25_regime_probabilities
            WHERE run_id=(
                SELECT source_module25_run_id
                FROM module29_runs
                WHERE run_id=?
            )
            ORDER BY observation_date
            """,
            [self.source_m29],
        ).fetchdf()

        for frame in (
            core_features,
            representation_features,
            labels,
        ):
            frame["observation_date"] = pd.to_datetime(
                frame["observation_date"]
            )

        core_features = core_features.set_index(
            "observation_date"
        )
        representation_features = representation_features.set_index(
            "observation_date"
        )
        labels = labels.set_index("observation_date")

        duplicate_columns = [
            column
            for column in representation_features.columns
            if column in core_features.columns
        ]
        representation_features = representation_features.drop(
            columns=duplicate_columns
        )

        features = core_features.join(
            representation_features,
            how="outer",
        )

        return aligned_feature_label_frame(
            features,
            labels,
            self.features,
            "dominant_regime",
        )

    def walk_forward(self, frame):
        minimum_training = int(
            self.cfg["validation"]["minimum_training_days"]
        )
        internal_validation = int(
            self.cfg["validation"]["internal_validation_days"]
        )
        test_days = int(
            self.cfg["validation"]["outer_test_days"]
        )
        candidates = [
            float(value)
            for value in self.cfg["models"]["gradient_weight_candidates"]
        ]
        random_state = int(self.cfg["models"]["random_state"])
        classes = canonical_classes()

        history_rows = []
        probability_rows = []
        fold_rows = []
        fold = 0
        start = minimum_training

        while start < len(frame):
            end = min(start + test_days, len(frame))
            training = frame.iloc[:start]
            testing = frame.iloc[start:end]
            if (
                testing.empty
                or len(training) <= internal_validation + 240
            ):
                break

            fold += 1
            model_training = training.iloc[:-internal_validation]
            model_validation = training.iloc[-internal_validation:]

            bundle = fit_clean_models(
                model_training[self.features],
                model_training["dominant_regime"],
                random_state + fold,
            )
            gradient, elastic = predict_component_probabilities(
                bundle,
                model_validation[self.features],
                classes,
            )
            weight, weight_results = choose_blend_weight(
                gradient,
                elastic,
                model_validation["dominant_regime"],
                classes,
                candidates,
            )
            validation_probabilities = blend_probabilities(
                gradient,
                elastic,
                weight,
            )
            calibrator = fit_multiclass_calibrator(
                validation_probabilities,
                model_validation["dominant_regime"],
                classes,
                random_state + fold,
            )

            # Refit the two base models on all data available before the test.
            final_bundle = fit_clean_models(
                training[self.features],
                training["dominant_regime"],
                random_state + fold,
            )
            gradient_test, elastic_test = (
                predict_component_probabilities(
                    final_bundle,
                    testing[self.features],
                    classes,
                )
            )
            blended_test = blend_probabilities(
                gradient_test,
                elastic_test,
                weight,
            )
            calibrated = calibrator.predict(blended_test)
            predictions = classes[np.argmax(calibrated, axis=1)]

            validation_best = max(
                result["validation_accuracy"]
                for result in weight_results
            )
            test_accuracy = accuracy_score(
                testing["dominant_regime"],
                predictions,
            )
            test_loss = log_loss(
                testing["dominant_regime"],
                calibrated,
                labels=classes,
            )
            test_brier = multiclass_brier_score(
                calibrated,
                testing["dominant_regime"],
                classes,
            )

            fold_rows.append({
                "run_id": self.run_id,
                "outer_fold": fold,
                "training_start_date": training.index.min().date(),
                "training_end_date": training.index.max().date(),
                "testing_start_date": testing.index.min().date(),
                "testing_end_date": testing.index.max().date(),
                "test_rows": len(testing),
                "selected_gradient_weight": weight,
                "validation_accuracy_pct": validation_best * 100,
                "test_accuracy_pct": test_accuracy * 100,
                "test_log_loss": test_loss,
                "test_brier_score": test_brier,
                "calculated_at_utc": utcnow(),
            })

            for row_index, (date, actual) in enumerate(
                testing["dominant_regime"].items()
            ):
                probability = calibrated[row_index]
                gradient_probability = gradient_test[row_index]
                elastic_probability = elastic_test[row_index]
                order = np.argsort(-probability)
                clean = classes[order[0]]
                secondary = classes[order[1]]
                agreement = float(
                    probability_agreement(
                        gradient_probability.reshape(1, -1),
                        elastic_probability.reshape(1, -1),
                    )[0]
                )
                level = confidence_level(
                    float(probability[order[0]]),
                    agreement,
                    "LOW",
                )
                history_rows.append({
                    "run_id": self.run_id,
                    "observation_date": date.date(),
                    "outer_fold": fold,
                    "actual_legacy_regime": actual,
                    "clean_regime": clean,
                    "secondary_regime": secondary,
                    "clean_probability": float(
                        probability[order[0]]
                    ),
                    "secondary_probability": float(
                        probability[order[1]]
                    ),
                    "confidence_level": level,
                    "model_agreement": agreement,
                    "gradient_weight": weight,
                    "calibration_applied": (
                        calibrator.model is not None
                    ),
                    "label_match": bool(clean == actual),
                    "calculated_at_utc": utcnow(),
                })
                for rank, class_index in enumerate(
                    order,
                    start=1,
                ):
                    probability_rows.append({
                        "run_id": self.run_id,
                        "observation_date": date.date(),
                        "regime": classes[class_index],
                        "probability": float(
                            probability[class_index]
                        ),
                        "probability_rank": rank,
                        "calculated_at_utc": utcnow(),
                    })

            start = end

        return (
            pd.DataFrame(history_rows),
            pd.DataFrame(probability_rows),
            pd.DataFrame(fold_rows),
        )

    def current_model(self, frame):
        validation_days = int(
            self.cfg["validation"]["internal_validation_days"]
        )
        random_state = int(self.cfg["models"]["random_state"])
        classes = canonical_classes()
        candidates = [
            float(value)
            for value in self.cfg["models"]["gradient_weight_candidates"]
        ]

        training = frame.iloc[:-1]
        current = frame.iloc[[-1]]
        model_training = training.iloc[:-validation_days]
        model_validation = training.iloc[-validation_days:]

        tuning_bundle = fit_clean_models(
            model_training[self.features],
            model_training["dominant_regime"],
            random_state + 999,
        )
        gradient_validation, elastic_validation = (
            predict_component_probabilities(
                tuning_bundle,
                model_validation[self.features],
                classes,
            )
        )
        weight, _ = choose_blend_weight(
            gradient_validation,
            elastic_validation,
            model_validation["dominant_regime"],
            classes,
            candidates,
        )
        validation_blend = blend_probabilities(
            gradient_validation,
            elastic_validation,
            weight,
        )
        calibrator = fit_multiclass_calibrator(
            validation_blend,
            model_validation["dominant_regime"],
            classes,
            random_state + 999,
        )

        bundle = fit_clean_models(
            training[self.features],
            training["dominant_regime"],
            random_state + 999,
        )
        gradient, elastic = predict_component_probabilities(
            bundle,
            current[self.features],
            classes,
        )
        raw = blend_probabilities(
            gradient,
            elastic,
            weight,
        )
        probability = calibrator.predict(raw)[0]
        order = np.argsort(-probability)
        clean = classes[order[0]]
        secondary = classes[order[1]]
        agreement = float(
            probability_agreement(
                gradient,
                elastic,
            )[0]
        )

        recent_days = int(self.cfg["drift"]["recent_window_days"])
        drift_table = feature_drift_table(
            training[self.features],
            training[self.features].tail(recent_days),
            current[self.features].iloc[0],
        )
        drift_score, current_drift_status = drift_status(
            drift_table
        )
        level = confidence_level(
            float(probability[order[0]]),
            agreement,
            current_drift_status,
        )

        contributions = counterfactual_feature_contributions(
            bundle=bundle,
            calibrator=calibrator,
            current=current,
            training_medians=training[self.features].median(),
            features=self.features,
            classes=classes,
            gradient_weight=weight,
            predicted_regime=clean,
        )

        return {
            "bundle": bundle,
            "calibrator": calibrator,
            "weight": weight,
            "date": current.index[0],
            "clean": clean,
            "secondary": secondary,
            "probability": probability,
            "order": order,
            "agreement": agreement,
            "gradient_probability": gradient[0],
            "elastic_probability": elastic[0],
            "confidence": level,
            "drift_table": drift_table,
            "drift_score": drift_score,
            "drift_status": current_drift_status,
            "contributions": contributions,
        }

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module30_runs VALUES(
                ?,?,?,?,NULL,'RUNNING',0,0,0,
                NULL,NULL,NULL,NULL,NULL,NULL,NULL,
                NULL,NULL,'OBSERVATION',NULL,NULL,'8.1.1'
            )
            """,
            [
                self.run_id,
                self.experiment_id,
                self.source_m29,
                self.started,
            ],
        )

        try:
            frame = self.data()
            history, probabilities, folds = self.walk_forward(
                frame
            )
            if history.empty:
                raise RuntimeError(
                    "Clean-regime walk-forward produced no test rows."
                )

            current = self.current_model(frame)
            self.upsert("clean_regime_history", history)
            self.upsert(
                "clean_probability_history",
                probabilities,
            )
            self.upsert("clean_validation_folds", folds)

            clean_accuracy = float(
                history["label_match"].mean() * 100
            )
            classes = canonical_classes()
            historical_matrix = probabilities.pivot(
                index="observation_date",
                columns="regime",
                values="probability",
            ).reindex(columns=classes)
            actual = history.set_index(
                "observation_date"
            )["actual_legacy_regime"].reindex(
                historical_matrix.index
            )
            historical_probabilities = historical_matrix.to_numpy()
            validate_probability_matrix(
                historical_probabilities,
                classes,
            )
            clean_loss = log_loss(
                actual,
                historical_probabilities,
                labels=classes.tolist(),
            )
            clean_brier = multiclass_brier_score(
                historical_probabilities,
                actual,
                classes,
            )

            legacy_current_row = self.conn.execute(
                """
                SELECT dominant_regime
                FROM latest_market_regime_daily
                ORDER BY observation_date DESC
                LIMIT 1
                """
            ).fetchone()
            legacy_current = (
                str(legacy_current_row[0])
                if legacy_current_row is not None
                else None
            )

            minimum_accuracy = float(
                self.cfg["promotion"]["minimum_accuracy_pct"]
            )
            maximum_log_loss = float(
                self.cfg["promotion"]["maximum_log_loss"]
            )
            minimum_folds = int(
                self.cfg["promotion"]["minimum_outer_folds"]
            )
            validation_passed = (
                clean_accuracy >= minimum_accuracy
                and clean_loss <= maximum_log_loss
                and len(folds) >= minimum_folds
            )
            validation_status = (
                "PASSED"
                if validation_passed
                else "LIMITED"
            )
            promotion_status = "OBSERVATION"

            disagreement_rows = []
            gradient_current = current["gradient_probability"]
            elastic_current = current["elastic_probability"]
            gradient_index = int(np.argmax(gradient_current))
            elastic_index = int(np.argmax(elastic_current))
            blended_index = int(current["order"][0])
            total_variation = float(
                1.0 - current["agreement"]
            )
            disagreement_rows.append({
                "run_id": self.run_id,
                "observation_date": current["date"].date(),
                "gradient_regime": classes[gradient_index],
                "elastic_regime": classes[elastic_index],
                "gradient_probability": float(
                    gradient_current[gradient_index]
                ),
                "elastic_probability": float(
                    elastic_current[elastic_index]
                ),
                "probability_agreement": current["agreement"],
                "total_variation_distance": total_variation,
                "blended_regime": current["clean"],
                "blended_probability": float(
                    current["probability"][blended_index]
                ),
                "disagreement_flag": bool(
                    classes[gradient_index]
                    != classes[elastic_index]
                    or current["agreement"] < 0.65
                ),
                "calculated_at_utc": utcnow(),
            })
            self.upsert(
                "clean_model_disagreement",
                pd.DataFrame(disagreement_rows),
            )

            current_probability_rows = []
            for rank, class_index in enumerate(
                current["order"],
                start=1,
            ):
                current_probability_rows.append({
                    "run_id": self.run_id,
                    "regime": classes[class_index],
                    "probability": float(
                        current["probability"][class_index]
                    ),
                    "probability_rank": rank,
                    "calculated_at_utc": utcnow(),
                })
            self.upsert(
                "clean_probability_current",
                pd.DataFrame(current_probability_rows),
            )

            drift = current["drift_table"].copy()
            drift.insert(0, "run_id", self.run_id)
            drift.insert(
                1,
                "observation_date",
                current["date"].date(),
            )
            drift["calculated_at_utc"] = utcnow()
            self.upsert("clean_feature_drift", drift)

            contributions = current[
                "contributions"
            ].copy()
            contributions.insert(0, "run_id", self.run_id)
            contributions.insert(
                1,
                "observation_date",
                current["date"].date(),
            )
            contributions["calculated_at_utc"] = utcnow()
            self.upsert(
                "clean_feature_contributions",
                contributions,
            )

            historical_reliability = clean_accuracy / 100
            current_row = pd.DataFrame([{
                "run_id": self.run_id,
                "observation_date": current["date"].date(),
                "clean_regime": current["clean"],
                "secondary_regime": current["secondary"],
                "clean_probability": float(
                    current["probability"][
                        current["order"][0]
                    ]
                ),
                "secondary_probability": float(
                    current["probability"][
                        current["order"][1]
                    ]
                ),
                "confidence_level": current["confidence"],
                "model_agreement": current["agreement"],
                "historical_reliability": (
                    historical_reliability
                ),
                "feature_drift_score": current["drift_score"],
                "drift_status": current["drift_status"],
                "legacy_regime": legacy_current,
                "agrees_with_legacy": bool(
                    current["clean"] == legacy_current
                ),
                "promotion_status": promotion_status,
                "calculated_at_utc": utcnow(),
            }])
            self.upsert(
                "clean_regime_current",
                current_row,
            )

            benchmark = pd.DataFrame([{
                "run_id": self.run_id,
                "test_rows": len(history),
                "clean_accuracy_pct": clean_accuracy,
                "legacy_self_accuracy_pct": 100.0,
                "clean_log_loss": clean_loss,
                "clean_brier_score": clean_brier,
                "current_clean_regime": current["clean"],
                "current_legacy_regime": legacy_current,
                "current_agreement": bool(
                    current["clean"] == legacy_current
                ),
                "relative_status": (
                    "CLEAN_MODEL_VALIDATED"
                    if validation_passed
                    else "CLEAN_MODEL_RESEARCH_ONLY"
                ),
                "calculated_at_utc": utcnow(),
            }])
            self.upsert(
                "clean_legacy_benchmark",
                benchmark,
            )

            notes = (
                "Clean model uses only Module 29 stable features. "
                "Legacy Module 25 remains the production benchmark. "
                "Promotion is deliberately held at OBSERVATION."
            )
            self.conn.execute(
                """
                UPDATE module30_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    stable_features=?,
                    outer_folds=?,
                    historical_rows=?,
                    clean_accuracy_pct=?,
                    legacy_accuracy_pct=100.0,
                    calibrated_log_loss=?,
                    calibrated_brier_score=?,
                    current_regime=?,
                    current_probability=?,
                    confidence_level=?,
                    model_agreement=?,
                    drift_status=?,
                    promotion_status=?,
                    validation_status=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(self.features),
                    len(folds),
                    len(history),
                    clean_accuracy,
                    clean_loss,
                    clean_brier,
                    current["clean"],
                    float(
                        current["probability"][
                            current["order"][0]
                        ]
                    ),
                    current["confidence"],
                    current["agreement"],
                    current["drift_status"],
                    promotion_status,
                    validation_status,
                    notes,
                    self.run_id,
                ],
            )

            complete_experiment(
                self.conn,
                self.experiment_id,
                status="SUCCESS",
                validation_metrics={
                    "outer_folds": len(folds),
                    "historical_rows": len(history),
                    "accuracy_pct": clean_accuracy,
                    "log_loss": clean_loss,
                    "brier_score": clean_brier,
                },
                calibration_metrics={
                    "current_probability": float(
                        current["probability"][
                            current["order"][0]
                        ]
                    ),
                    "current_confidence": current["confidence"],
                    "model_agreement": current["agreement"],
                    "drift_status": current["drift_status"],
                },
                promotion_status=promotion_status,
                notes=notes,
            )
            self.conn.close()

            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "stable_features": len(self.features),
                "outer_folds": len(folds),
                "historical_rows": len(history),
                "clean_accuracy_pct": clean_accuracy,
                "clean_log_loss": clean_loss,
                "clean_brier_score": clean_brier,
                "current_regime": current["clean"],
                "secondary_regime": current["secondary"],
                "current_probability": float(
                    current["probability"][
                        current["order"][0]
                    ]
                ),
                "confidence_level": current["confidence"],
                "model_agreement": current["agreement"],
                "drift_status": current["drift_status"],
                "legacy_regime": legacy_current,
                "validation_status": validation_status,
                "promotion_status": promotion_status,
                "experiment_id": self.experiment_id,
            }

        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module30_runs
                SET completed_at_utc=?,
                    status='FAILED',
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    str(exc)[:1000],
                    self.run_id,
                ],
            )
            complete_experiment(
                self.conn,
                self.experiment_id,
                status="FAILED",
                validation_metrics={},
                calibration_metrics={},
                promotion_status="REJECTED",
                notes=str(exc)[:1000],
            )
            self.conn.close()
            raise


def run_module30():
    return Module30Runner().run()
