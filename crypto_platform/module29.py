from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA, REGIMES
from crypto_platform.module27 import MODULE27_SCHEMA
from crypto_platform.module28 import MODULE28_SCHEMA

MODULE29_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module29_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module25_run_id VARCHAR,
    source_module27_run_id VARCHAR,
    source_module28_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    candidate_features INTEGER,
    stable_features INTEGER,
    walk_forward_folds INTEGER,
    bootstrap_iterations INTEGER,
    rolling_windows INTEGER,
    stable_feature_list VARCHAR,
    stable_core_features INTEGER,
    stable_representation_features INTEGER,
    validation_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m29_feature_registry(
    run_id VARCHAR,
    feature_key VARCHAR,
    source_group VARCHAR,
    coverage_pct DOUBLE,
    permutation_importance_mean DOUBLE,
    permutation_importance_std DOUBLE,
    positive_importance_fold_rate_pct DOUBLE,
    bootstrap_selection_rate_pct DOUBLE,
    rolling_positive_rate_pct DOUBLE,
    regime_separation_score DOUBLE,
    redundancy_penalty DOUBLE,
    ablation_delta_pct DOUBLE,
    stability_score DOUBLE,
    composite_evidence_score DOUBLE,
    evidence_grade VARCHAR,
    stable_feature BOOLEAN,
    selection_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS m29_walk_forward_importance(
    run_id VARCHAR,
    fold_number INTEGER,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    feature_key VARCHAR,
    permutation_importance DOUBLE,
    ablation_delta_pct DOUBLE,
    fold_accuracy_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number, feature_key)
);

CREATE TABLE IF NOT EXISTS m29_bootstrap_stability(
    run_id VARCHAR,
    feature_key VARCHAR,
    bootstrap_iterations INTEGER,
    selected_iterations INTEGER,
    selection_rate_pct DOUBLE,
    importance_mean DOUBLE,
    importance_std DOUBLE,
    positive_importance_rate_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS m29_rolling_importance(
    run_id VARCHAR,
    window_number INTEGER,
    window_start_date DATE,
    window_end_date DATE,
    observations INTEGER,
    feature_key VARCHAR,
    permutation_importance DOUBLE,
    positive_importance BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, window_number, feature_key)
);

CREATE TABLE IF NOT EXISTS m29_regime_feature_importance(
    run_id VARCHAR,
    regime VARCHAR,
    feature_key VARCHAR,
    observations INTEGER,
    standardized_mean_difference DOUBLE,
    within_regime_variability DOUBLE,
    regime_separation_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, regime, feature_key)
);

CREATE TABLE IF NOT EXISTS m29_feature_ablation(
    run_id VARCHAR,
    feature_key VARCHAR,
    full_model_accuracy_pct DOUBLE,
    reduced_model_accuracy_pct DOUBLE,
    ablation_delta_pct DOUBLE,
    helpful BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS m29_minimal_model_validation(
    run_id VARCHAR,
    model_key VARCHAR,
    feature_count INTEGER,
    feature_list VARCHAR,
    test_rows INTEGER,
    walk_forward_accuracy_pct DOUBLE,
    mean_fold_accuracy_pct DOUBLE,
    worst_fold_accuracy_pct DOUBLE,
    best_fold_accuracy_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, model_key)
);

CREATE TABLE IF NOT EXISTS m29_research_summary(
    run_id VARCHAR PRIMARY KEY,
    candidate_features INTEGER,
    stable_features INTEGER,
    stable_feature_list VARCHAR,
    stable_core_features INTEGER,
    stable_representation_features INTEGER,
    full_feature_accuracy_pct DOUBLE,
    core_only_accuracy_pct DOUBLE,
    stable_feature_accuracy_pct DOUBLE,
    stable_feature_worst_fold_pct DOUBLE,
    bootstrap_iterations INTEGER,
    rolling_windows INTEGER,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m29_feature_registry AS
SELECT * FROM m29_feature_registry
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY selection_rank, composite_evidence_score DESC;

CREATE OR REPLACE VIEW latest_m29_walk_forward_importance AS
SELECT * FROM m29_walk_forward_importance
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY fold_number, permutation_importance DESC;

CREATE OR REPLACE VIEW latest_m29_bootstrap_stability AS
SELECT * FROM m29_bootstrap_stability
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY selection_rate_pct DESC;

CREATE OR REPLACE VIEW latest_m29_rolling_importance AS
SELECT * FROM m29_rolling_importance
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY window_number, permutation_importance DESC;

CREATE OR REPLACE VIEW latest_m29_regime_feature_importance AS
SELECT * FROM m29_regime_feature_importance
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY regime, regime_separation_score DESC;

CREATE OR REPLACE VIEW latest_m29_feature_ablation AS
SELECT * FROM m29_feature_ablation
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY ablation_delta_pct DESC;

CREATE OR REPLACE VIEW latest_m29_minimal_model_validation AS
SELECT * FROM m29_minimal_model_validation
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY walk_forward_accuracy_pct DESC;

CREATE OR REPLACE VIEW latest_m29_research_summary AS
SELECT * FROM m29_research_summary
WHERE run_id=(
    SELECT run_id FROM module29_runs
    ORDER BY started_at_utc DESC LIMIT 1
);
"""

CORE_FEATURES = [
    "liquidity_score",
    "trend_score",
    "risk_score",
    "recovery_score",
    "change_pressure",
    "btc_return_90d",
    "btc_distance_sma200",
    "btc_volatility_90d",
    "btc_drawdown_180d",
    "core_breadth",
    "stablecoin_growth_30d",
    "high_yield_spread",
    "dollar_index",
    "fear_greed",
]

REPRESENTATION_FEATURES = [
    "correlation_mean_90d",
    "correlation_dispersion_90d",
    "beta_dispersion_180d",
    "volatility_term_ratio",
    "downside_share_30d",
    "return_skew_90d",
    "breadth_momentum_30d",
    "alt_relative_strength_30d",
    "alt_relative_strength_90d",
    "drawdown_velocity_30d",
    "trend_acceleration",
    "liquidity_impulse",
    "credit_impulse",
    "dollar_impulse",
    "stress_concentration",
    "risk_on_composite",
    "risk_off_composite",
    "transition_pressure",
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def safe(value: Any, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return float(default)
    return float(value)


class Module29Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE25_SCHEMA)
        self.conn.execute(MODULE27_SCHEMA)
        self.conn.execute(MODULE28_SCHEMA)
        self.conn.execute(MODULE29_SCHEMA)
        self.cfg = self.settings["module29"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

        m25 = self.conn.execute(
            "SELECT run_id FROM module25_runs "
            "WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        m27 = self.conn.execute(
            "SELECT run_id FROM module27_runs "
            "WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        m28 = self.conn.execute(
            "SELECT run_id FROM module28_runs "
            "WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()

        if m25 is None or m27 is None or m28 is None:
            raise RuntimeError(
                "Successful Modules 25, 27, and 28 are required."
            )
        self.source_m25 = str(m25[0])
        self.source_m27 = str(m27[0])
        self.source_m28 = str(m28[0])

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m29_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m29_stage"
        )
        self.conn.unregister("_m29_stage")

    def data(self):
        base = self.conn.execute(
            "SELECT * FROM m25_regime_features "
            "WHERE run_id=? ORDER BY observation_date",
            [self.source_m25],
        ).fetchdf()
        rep = self.conn.execute(
            "SELECT * FROM m27_representation_features "
            "WHERE run_id=? ORDER BY observation_date",
            [self.source_m27],
        ).fetchdf()
        labels = self.conn.execute(
            "SELECT observation_date, dominant_regime "
            "FROM m25_regime_probabilities "
            "WHERE run_id=? ORDER BY observation_date",
            [self.source_m25],
        ).fetchdf()

        for frame in (base, rep, labels):
            frame["observation_date"] = pd.to_datetime(
                frame["observation_date"]
            )

        base = base.set_index("observation_date")
        rep = rep.set_index("observation_date")
        labels = labels.set_index("observation_date")

        core = [c for c in CORE_FEATURES if c in base.columns]
        representation = [
            c for c in REPRESENTATION_FEATURES if c in rep.columns
        ]
        frame = pd.concat(
            [base[core], rep[representation], labels],
            axis=1,
        ).replace([np.inf, -np.inf], np.nan)

        minimum_coverage = float(
            self.cfg["feature_evidence"]["minimum_coverage"]
        )
        usable = [
            c for c in core + representation
            if frame[c].notna().mean() >= minimum_coverage
        ]
        frame = frame[usable + ["dominant_regime"]].dropna()
        return frame, [c for c in core if c in usable], [
            c for c in representation if c in usable
        ]

    def classifier(self):
        return LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=int(self.cfg["models"]["random_state"]),
        )

    def walk_forward_importance(
        self,
        frame: pd.DataFrame,
        features: list[str],
    ):
        train_days = int(
            self.cfg["walk_forward"]["minimum_training_days"]
        )
        test_days = int(
            self.cfg["walk_forward"]["test_days"]
        )
        repeats = int(
            self.cfg["feature_evidence"]["permutation_repeats"]
        )

        records = []
        fold_metrics = []
        fold = 0
        start = train_days

        while start < len(frame):
            end = min(start + test_days, len(frame))
            train = frame.iloc[:start]
            test = frame.iloc[start:end]
            if test.empty:
                break

            fold += 1
            scaler = StandardScaler()
            x_train = scaler.fit_transform(train[features])
            x_test = scaler.transform(test[features])
            model = self.classifier()
            model.fit(x_train, train["dominant_regime"])
            full_accuracy = (
                accuracy_score(
                    test["dominant_regime"],
                    model.predict(x_test),
                )
                * 100
            )

            importance = permutation_importance(
                model,
                x_test,
                test["dominant_regime"],
                n_repeats=repeats,
                random_state=(
                    int(self.cfg["models"]["random_state"])
                    + fold
                ),
                scoring="accuracy",
            )

            for index, feature in enumerate(features):
                reduced = [f for f in features if f != feature]
                reduced_scaler = StandardScaler()
                reduced_train = reduced_scaler.fit_transform(
                    train[reduced]
                )
                reduced_test = reduced_scaler.transform(test[reduced])
                reduced_model = self.classifier()
                reduced_model.fit(
                    reduced_train,
                    train["dominant_regime"],
                )
                reduced_accuracy = (
                    accuracy_score(
                        test["dominant_regime"],
                        reduced_model.predict(reduced_test),
                    )
                    * 100
                )
                records.append({
                    "run_id": self.run_id,
                    "fold_number": fold,
                    "training_start_date": train.index.min().date(),
                    "training_end_date": train.index.max().date(),
                    "testing_start_date": test.index.min().date(),
                    "testing_end_date": test.index.max().date(),
                    "feature_key": feature,
                    "permutation_importance": float(
                        importance.importances_mean[index]
                    ),
                    "ablation_delta_pct": float(
                        full_accuracy - reduced_accuracy
                    ),
                    "fold_accuracy_pct": float(full_accuracy),
                    "calculated_at_utc": utcnow(),
                })

            fold_metrics.append({
                "fold": fold,
                "accuracy": full_accuracy,
                "rows": len(test),
            })
            start = end

        return pd.DataFrame(records), pd.DataFrame(fold_metrics)

    def bootstrap_stability(
        self,
        frame: pd.DataFrame,
        features: list[str],
    ):
        iterations = int(
            self.cfg["bootstrap"]["iterations"]
        )
        top_count = int(
            self.cfg["bootstrap"]["top_features_per_iteration"]
        )
        rng = np.random.default_rng(
            int(self.cfg["bootstrap"]["seed"])
        )

        importance_values = {
            feature: [] for feature in features
        }
        selection_counts = {
            feature: 0 for feature in features
        }

        x = frame[features]
        y = frame["dominant_regime"]

        for iteration in range(iterations):
            indices = rng.integers(0, len(frame), len(frame))
            sample_x = x.iloc[indices]
            sample_y = y.iloc[indices]

            if sample_y.nunique() < 2:
                continue

            scaler = StandardScaler()
            scaled = scaler.fit_transform(sample_x)
            model = self.classifier()
            model.fit(scaled, sample_y)

            # Coefficient magnitude is used inside each bootstrap sample.
            coefficients = np.mean(
                np.abs(model.coef_),
                axis=0,
            )
            order = np.argsort(-coefficients)
            selected = {
                features[index]
                for index in order[:top_count]
            }

            for index, feature in enumerate(features):
                value = float(coefficients[index])
                importance_values[feature].append(value)
                if feature in selected:
                    selection_counts[feature] += 1

        rows = []
        completed = max(
            len(next(iter(importance_values.values()))),
            1,
        )
        for feature in features:
            values = np.asarray(
                importance_values[feature],
                dtype=float,
            )
            rows.append({
                "run_id": self.run_id,
                "feature_key": feature,
                "bootstrap_iterations": completed,
                "selected_iterations": int(
                    selection_counts[feature]
                ),
                "selection_rate_pct": float(
                    selection_counts[feature]
                    / completed
                    * 100
                ),
                "importance_mean": float(
                    np.mean(values)
                ) if len(values) else 0.0,
                "importance_std": float(
                    np.std(values)
                ) if len(values) else 0.0,
                "positive_importance_rate_pct": float(
                    np.mean(values > 0) * 100
                ) if len(values) else 0.0,
                "calculated_at_utc": utcnow(),
            })

        return pd.DataFrame(rows)

    def rolling_importance(
        self,
        frame: pd.DataFrame,
        features: list[str],
    ):
        window_days = int(
            self.cfg["rolling"]["window_days"]
        )
        step_days = int(
            self.cfg["rolling"]["step_days"]
        )
        repeats = int(
            self.cfg["rolling"]["permutation_repeats"]
        )

        rows = []
        window_number = 0

        for start in range(
            0,
            max(len(frame) - window_days + 1, 0),
            step_days,
        ):
            window = frame.iloc[start:start + window_days]
            if (
                len(window) < window_days
                or window["dominant_regime"].nunique() < 2
            ):
                continue

            split = int(len(window) * 0.75)
            train = window.iloc[:split]
            test = window.iloc[split:]
            if test["dominant_regime"].nunique() < 2:
                continue

            window_number += 1
            scaler = StandardScaler()
            x_train = scaler.fit_transform(train[features])
            x_test = scaler.transform(test[features])
            model = self.classifier()
            model.fit(x_train, train["dominant_regime"])
            importance = permutation_importance(
                model,
                x_test,
                test["dominant_regime"],
                n_repeats=repeats,
                random_state=(
                    int(self.cfg["models"]["random_state"])
                    + window_number
                ),
                scoring="accuracy",
            )

            for index, feature in enumerate(features):
                value = float(
                    importance.importances_mean[index]
                )
                rows.append({
                    "run_id": self.run_id,
                    "window_number": window_number,
                    "window_start_date": window.index.min().date(),
                    "window_end_date": window.index.max().date(),
                    "observations": len(window),
                    "feature_key": feature,
                    "permutation_importance": value,
                    "positive_importance": bool(value > 0),
                    "calculated_at_utc": utcnow(),
                })

        return pd.DataFrame(rows)

    def regime_importance(
        self,
        frame: pd.DataFrame,
        features: list[str],
    ):
        rows = []

        for regime in REGIMES:
            in_regime = frame[
                frame["dominant_regime"] == regime
            ]
            out_regime = frame[
                frame["dominant_regime"] != regime
            ]

            if len(in_regime) < 10 or len(out_regime) < 10:
                continue

            for feature in features:
                pooled_std = max(
                    float(frame[feature].std()),
                    1e-9,
                )
                standardized_difference = (
                    float(in_regime[feature].mean())
                    - float(out_regime[feature].mean())
                ) / pooled_std
                within_variability = float(
                    in_regime[feature].std()
                    / pooled_std
                )
                separation = (
                    abs(standardized_difference)
                    / max(within_variability, 0.25)
                )

                rows.append({
                    "run_id": self.run_id,
                    "regime": regime,
                    "feature_key": feature,
                    "observations": len(in_regime),
                    "standardized_mean_difference": (
                        standardized_difference
                    ),
                    "within_regime_variability": (
                        within_variability
                    ),
                    "regime_separation_score": separation,
                    "calculated_at_utc": utcnow(),
                })

        return pd.DataFrame(rows)

    def aggregate_registry(
        self,
        frame: pd.DataFrame,
        core: list[str],
        representation: list[str],
        walk_forward: pd.DataFrame,
        bootstrap: pd.DataFrame,
        rolling: pd.DataFrame,
        regime: pd.DataFrame,
    ):
        features = core + representation
        correlation = frame[features].corr().abs()

        wf_group = walk_forward.groupby("feature_key").agg(
            permutation_importance_mean=(
                "permutation_importance",
                "mean",
            ),
            permutation_importance_std=(
                "permutation_importance",
                "std",
            ),
            positive_importance_fold_rate_pct=(
                "permutation_importance",
                lambda values: float(
                    np.mean(np.asarray(values) > 0) * 100
                ),
            ),
            ablation_delta_pct=(
                "ablation_delta_pct",
                "mean",
            ),
        )

        rolling_group = (
            rolling.groupby("feature_key").agg(
                rolling_positive_rate_pct=(
                    "positive_importance",
                    "mean",
                ),
            )
            if not rolling.empty
            else pd.DataFrame()
        )
        if not rolling_group.empty:
            rolling_group[
                "rolling_positive_rate_pct"
            ] *= 100

        regime_group = regime.groupby(
            "feature_key"
        )["regime_separation_score"].mean()

        bootstrap_indexed = bootstrap.set_index(
            "feature_key"
        )

        rows = []
        for feature in features:
            redundancy = (
                float(
                    correlation.loc[feature]
                    .drop(feature)
                    .nlargest(3)
                    .mean()
                )
                if len(features) > 1
                else 0.0
            )
            wf_importance = safe(
                wf_group.loc[
                    feature,
                    "permutation_importance_mean",
                ]
                if feature in wf_group.index
                else 0.0
            )
            wf_std = safe(
                wf_group.loc[
                    feature,
                    "permutation_importance_std",
                ]
                if feature in wf_group.index
                else 0.0
            )
            fold_positive = safe(
                wf_group.loc[
                    feature,
                    "positive_importance_fold_rate_pct",
                ]
                if feature in wf_group.index
                else 0.0
            )
            ablation = safe(
                wf_group.loc[
                    feature,
                    "ablation_delta_pct",
                ]
                if feature in wf_group.index
                else 0.0
            )
            bootstrap_rate = safe(
                bootstrap_indexed.loc[
                    feature,
                    "selection_rate_pct",
                ]
                if feature in bootstrap_indexed.index
                else 0.0
            )
            rolling_rate = safe(
                rolling_group.loc[
                    feature,
                    "rolling_positive_rate_pct",
                ]
                if (
                    not rolling_group.empty
                    and feature in rolling_group.index
                )
                else 0.0
            )
            separation = safe(
                regime_group.loc[feature]
                if feature in regime_group.index
                else 0.0
            )

            stability = (
                0.35 * fold_positive
                + 0.35 * bootstrap_rate
                + 0.30 * rolling_rate
            )
            evidence = (
                wf_importance * 120
                + max(ablation, 0) * 0.8
                + stability * 0.30
                + separation * 8
                - redundancy * 12
                - wf_std * 40
            )

            rows.append({
                "run_id": self.run_id,
                "feature_key": feature,
                "source_group": (
                    "CORE"
                    if feature in core
                    else "REPRESENTATION"
                ),
                "coverage_pct": float(
                    frame[feature].notna().mean() * 100
                ),
                "permutation_importance_mean": wf_importance,
                "permutation_importance_std": wf_std,
                "positive_importance_fold_rate_pct": (
                    fold_positive
                ),
                "bootstrap_selection_rate_pct": (
                    bootstrap_rate
                ),
                "rolling_positive_rate_pct": rolling_rate,
                "regime_separation_score": separation,
                "redundancy_penalty": redundancy,
                "ablation_delta_pct": ablation,
                "stability_score": stability,
                "composite_evidence_score": evidence,
                "evidence_grade": None,
                "stable_feature": False,
                "selection_rank": None,
                "calculated_at_utc": utcnow(),
            })

        result = pd.DataFrame(rows).sort_values(
            "composite_evidence_score",
            ascending=False,
        )

        minimum_stability = float(
            self.cfg["selection"]["minimum_stability_score"]
        )
        minimum_fold_positive = float(
            self.cfg["selection"][
                "minimum_positive_fold_rate_pct"
            ]
        )
        minimum_bootstrap = float(
            self.cfg["selection"][
                "minimum_bootstrap_selection_rate_pct"
            ]
        )
        maximum_features = int(
            self.cfg["selection"]["maximum_stable_features"]
        )
        minimum_core = int(
            self.cfg["selection"]["minimum_core_features"]
        )
        maximum_correlation = float(
            self.cfg["selection"][
                "maximum_pairwise_correlation"
            ]
        )

        eligible = result[
            (
                result["stability_score"]
                >= minimum_stability
            )
            & (
                result[
                    "positive_importance_fold_rate_pct"
                ]
                >= minimum_fold_positive
            )
            & (
                result["bootstrap_selection_rate_pct"]
                >= minimum_bootstrap
            )
        ]

        stable = []
        core_eligible = eligible[
            eligible["source_group"] == "CORE"
        ]["feature_key"].tolist()

        for feature in core_eligible[:minimum_core]:
            stable.append(feature)

        for feature in eligible["feature_key"]:
            if feature in stable:
                continue
            if all(
                correlation.loc[feature, selected]
                < maximum_correlation
                for selected in stable
            ):
                stable.append(feature)
            if len(stable) >= maximum_features:
                break

        # Guarantee a usable minimal research set even when strict evidence
        # thresholds leave too few features.
        if len(stable) < minimum_core:
            for feature in result[
                result["source_group"] == "CORE"
            ]["feature_key"]:
                if feature not in stable:
                    stable.append(feature)
                if len(stable) >= minimum_core:
                    break

        result["stable_feature"] = result[
            "feature_key"
        ].isin(stable)
        ranks = {
            feature: index + 1
            for index, feature in enumerate(stable)
        }
        result["selection_rank"] = result[
            "feature_key"
        ].map(ranks)

        def grade(row):
            if (
                row["stable_feature"]
                and row["stability_score"] >= 75
            ):
                return "A"
            if row["stable_feature"]:
                return "B"
            if row["stability_score"] >= 50:
                return "C"
            return "D"

        result["evidence_grade"] = result.apply(
            grade,
            axis=1,
        )
        return result, stable

    def model_validation(
        self,
        frame: pd.DataFrame,
        feature_sets: dict[str, list[str]],
    ):
        train_days = int(
            self.cfg["walk_forward"]["minimum_training_days"]
        )
        test_days = int(
            self.cfg["walk_forward"]["test_days"]
        )
        rows = []

        for model_key, features in feature_sets.items():
            accuracies = []
            rows_tested = 0
            start = train_days

            while start < len(frame):
                end = min(start + test_days, len(frame))
                train = frame.iloc[:start]
                test = frame.iloc[start:end]
                if test.empty:
                    break

                scaler = StandardScaler()
                x_train = scaler.fit_transform(
                    train[features]
                )
                x_test = scaler.transform(test[features])
                model = self.classifier()
                model.fit(
                    x_train,
                    train["dominant_regime"],
                )
                accuracy = (
                    accuracy_score(
                        test["dominant_regime"],
                        model.predict(x_test),
                    )
                    * 100
                )
                accuracies.append(accuracy)
                rows_tested += len(test)
                start = end

            rows.append({
                "run_id": self.run_id,
                "model_key": model_key,
                "feature_count": len(features),
                "feature_list": json.dumps(features),
                "test_rows": rows_tested,
                "walk_forward_accuracy_pct": float(
                    np.average(
                        accuracies,
                        weights=None,
                    )
                ) if accuracies else 0.0,
                "mean_fold_accuracy_pct": float(
                    np.mean(accuracies)
                ) if accuracies else 0.0,
                "worst_fold_accuracy_pct": float(
                    np.min(accuracies)
                ) if accuracies else 0.0,
                "best_fold_accuracy_pct": float(
                    np.max(accuracies)
                ) if accuracies else 0.0,
                "calculated_at_utc": utcnow(),
            })

        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute("""
            INSERT INTO module29_runs VALUES(
                ?,?,?,?,?,NULL,'RUNNING',
                0,0,0,0,0,NULL,0,0,NULL,NULL,'8.0.0'
            )
        """, [
            self.run_id,
            self.source_m25,
            self.source_m27,
            self.source_m28,
            self.started,
        ])

        try:
            frame, core, representation = self.data()
            features = core + representation

            walk_forward, fold_metrics = (
                self.walk_forward_importance(
                    frame,
                    features,
                )
            )
            bootstrap = self.bootstrap_stability(
                frame,
                features,
            )
            rolling = self.rolling_importance(
                frame,
                features,
            )
            regime = self.regime_importance(
                frame,
                features,
            )
            registry, stable = self.aggregate_registry(
                frame,
                core,
                representation,
                walk_forward,
                bootstrap,
                rolling,
                regime,
            )

            ablation = (
                walk_forward.groupby("feature_key").agg(
                    full_model_accuracy_pct=(
                        "fold_accuracy_pct",
                        "mean",
                    ),
                    ablation_delta_pct=(
                        "ablation_delta_pct",
                        "mean",
                    ),
                ).reset_index()
            )
            ablation[
                "reduced_model_accuracy_pct"
            ] = (
                ablation["full_model_accuracy_pct"]
                - ablation["ablation_delta_pct"]
            )
            ablation["helpful"] = (
                ablation["ablation_delta_pct"] > 0
            )
            ablation.insert(0, "run_id", self.run_id)
            ablation["calculated_at_utc"] = utcnow()
            ablation = ablation[[
                "run_id",
                "feature_key",
                "full_model_accuracy_pct",
                "reduced_model_accuracy_pct",
                "ablation_delta_pct",
                "helpful",
                "calculated_at_utc",
            ]]

            validation = self.model_validation(
                frame,
                {
                    "FULL_FEATURE_SET": features,
                    "CORE_ONLY": core,
                    "STABLE_FEATURE_SET": stable,
                    "TOP_5_STABLE": stable[:min(5, len(stable))],
                },
            )

            self.upsert(
                "m29_walk_forward_importance",
                walk_forward,
            )
            self.upsert(
                "m29_bootstrap_stability",
                bootstrap,
            )
            self.upsert(
                "m29_rolling_importance",
                rolling,
            )
            self.upsert(
                "m29_regime_feature_importance",
                regime,
            )
            self.upsert(
                "m29_feature_registry",
                registry,
            )
            self.upsert(
                "m29_feature_ablation",
                ablation,
            )
            self.upsert(
                "m29_minimal_model_validation",
                validation,
            )

            indexed = validation.set_index("model_key")
            full_accuracy = safe(
                indexed.loc[
                    "FULL_FEATURE_SET",
                    "walk_forward_accuracy_pct",
                ]
            )
            core_accuracy = safe(
                indexed.loc[
                    "CORE_ONLY",
                    "walk_forward_accuracy_pct",
                ]
            )
            stable_accuracy = safe(
                indexed.loc[
                    "STABLE_FEATURE_SET",
                    "walk_forward_accuracy_pct",
                ]
            )
            stable_worst = safe(
                indexed.loc[
                    "STABLE_FEATURE_SET",
                    "worst_fold_accuracy_pct",
                ]
            )

            minimum_accuracy = float(
                self.cfg["validation"][
                    "minimum_stable_model_accuracy_pct"
                ]
            )
            minimum_worst = float(
                self.cfg["validation"][
                    "minimum_worst_fold_accuracy_pct"
                ]
            )
            maximum_representation = int(
                self.cfg["validation"][
                    "maximum_representation_features"
                ]
            )

            stable_representation = len([
                feature for feature in stable
                if feature in representation
            ])
            passed = (
                stable_accuracy >= minimum_accuracy
                and stable_worst >= minimum_worst
                and stable_representation
                <= maximum_representation
            )
            status = "PASSED" if passed else "LIMITED"
            recommendation = (
                "READY_FOR_CLEAN_REGIME_RETRAINING"
                if passed
                else "CONTINUE_EXPLAINABILITY_RESEARCH"
            )

            summary = pd.DataFrame([{
                "run_id": self.run_id,
                "candidate_features": len(features),
                "stable_features": len(stable),
                "stable_feature_list": json.dumps(stable),
                "stable_core_features": len([
                    feature for feature in stable
                    if feature in core
                ]),
                "stable_representation_features": (
                    stable_representation
                ),
                "full_feature_accuracy_pct": full_accuracy,
                "core_only_accuracy_pct": core_accuracy,
                "stable_feature_accuracy_pct": (
                    stable_accuracy
                ),
                "stable_feature_worst_fold_pct": (
                    stable_worst
                ),
                "bootstrap_iterations": int(
                    bootstrap[
                        "bootstrap_iterations"
                    ].max()
                ) if not bootstrap.empty else 0,
                "rolling_windows": int(
                    rolling["window_number"].nunique()
                ) if not rolling.empty else 0,
                "validation_status": status,
                "advancement_recommendation": (
                    recommendation
                ),
                "calculated_at_utc": utcnow(),
            }])
            self.upsert(
                "m29_research_summary",
                summary,
            )

            record = summary.iloc[0]
            self.conn.execute("""
                UPDATE module29_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    candidate_features=?,
                    stable_features=?,
                    walk_forward_folds=?,
                    bootstrap_iterations=?,
                    rolling_windows=?,
                    stable_feature_list=?,
                    stable_core_features=?,
                    stable_representation_features=?,
                    validation_status=?,
                    notes=?
                WHERE run_id=?
            """, [
                utcnow(),
                len(features),
                len(stable),
                int(
                    walk_forward[
                        "fold_number"
                    ].nunique()
                ),
                int(record["bootstrap_iterations"]),
                int(record["rolling_windows"]),
                record["stable_feature_list"],
                int(record["stable_core_features"]),
                int(
                    record[
                        "stable_representation_features"
                    ]
                ),
                status,
                (
                    "v8.0 measures feature evidence across "
                    "walk-forward folds, bootstrap samples, "
                    "rolling windows, regimes, and ablations. "
                    "Modules 25-28 remain unchanged."
                ),
                self.run_id,
            ])
            self.conn.close()
            return record.to_dict()

        except Exception as exc:
            self.conn.execute("""
                UPDATE module29_runs
                SET completed_at_utc=?,
                    status='FAILED',
                    notes=?
                WHERE run_id=?
            """, [
                utcnow(),
                str(exc)[:1000],
                self.run_id,
            ])
            self.conn.close()
            raise


def run_module29():
    return Module29Runner().run()
