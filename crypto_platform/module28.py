from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.inspection import permutation_importance
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA, REGIMES
from crypto_platform.module27 import MODULE27_SCHEMA

MODULE28_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module28_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module27_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    candidate_features INTEGER,
    retained_features INTEGER,
    adaptive_candidates INTEGER,
    outer_folds INTEGER,
    nested_rows INTEGER,
    nested_agreement_pct DOUBLE,
    calibrated_mae DOUBLE,
    meta_ensemble_stability_pct DOUBLE,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    validation_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m28_feature_selection(
    run_id VARCHAR,
    feature_key VARCHAR,
    source_group VARCHAR,
    permutation_importance DOUBLE,
    mutual_information_proxy DOUBLE,
    fold_survival_rate_pct DOUBLE,
    mean_ablation_delta_pct DOUBLE,
    redundancy_penalty DOUBLE,
    composite_score DOUBLE,
    retained BOOLEAN,
    selection_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS m28_adaptive_search(
    run_id VARCHAR,
    outer_fold INTEGER,
    generation INTEGER,
    candidate_id VARCHAR,
    gmm_weight DOUBLE,
    kmeans_weight DOUBLE,
    rules_weight DOUBLE,
    state_space_weight DOUBLE,
    probability_temperature DOUBLE,
    smoothing DOUBLE,
    transition_strength DOUBLE,
    inner_agreement_pct DOUBLE,
    inner_calibration_mae DOUBLE,
    inner_switch_rate DOUBLE,
    objective_score DOUBLE,
    selected_for_meta BOOLEAN,
    meta_weight DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, outer_fold, candidate_id)
);

CREATE TABLE IF NOT EXISTS m28_nested_predictions(
    run_id VARCHAR,
    outer_fold INTEGER,
    observation_date DATE,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    retained_features_json VARCHAR,
    meta_candidates_json VARCHAR,
    calibration_method VARCHAR,
    actual_regime VARCHAR,
    predicted_regime VARCHAR,
    raw_confidence DOUBLE,
    calibrated_confidence DOUBLE,
    label_match BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m28_calibration_comparison(
    run_id VARCHAR,
    outer_fold INTEGER,
    calibration_method VARCHAR,
    validation_rows INTEGER,
    validation_mae DOUBLE,
    validation_brier DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, outer_fold, calibration_method)
);

CREATE TABLE IF NOT EXISTS m28_fold_summary(
    run_id VARCHAR,
    outer_fold INTEGER,
    testing_start_date DATE,
    testing_end_date DATE,
    test_days INTEGER,
    retained_features INTEGER,
    meta_candidates INTEGER,
    agreement_pct DOUBLE,
    raw_calibration_mae DOUBLE,
    calibrated_mae DOUBLE,
    mean_confidence DOUBLE,
    switch_rate DOUBLE,
    selected_calibration VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, outer_fold)
);

CREATE TABLE IF NOT EXISTS m28_robustness_summary(
    run_id VARCHAR,
    robustness_key VARCHAR,
    observations INTEGER,
    agreement_pct DOUBLE,
    calibration_mae DOUBLE,
    agreement_with_primary_pct DOUBLE,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, robustness_key)
);

CREATE TABLE IF NOT EXISTS m28_research_summary(
    run_id VARCHAR PRIMARY KEY,
    candidate_features INTEGER,
    retained_features INTEGER,
    retained_feature_list VARCHAR,
    adaptive_candidates INTEGER,
    outer_folds INTEGER,
    nested_rows INTEGER,
    nested_agreement_pct DOUBLE,
    raw_calibration_mae DOUBLE,
    calibrated_mae DOUBLE,
    meta_ensemble_stability_pct DOUBLE,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m28_feature_selection AS
SELECT * FROM m28_feature_selection
WHERE run_id=(SELECT run_id FROM module28_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY selection_rank, composite_score DESC;

CREATE OR REPLACE VIEW latest_m28_adaptive_search AS
SELECT * FROM m28_adaptive_search
WHERE run_id=(SELECT run_id FROM module28_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY outer_fold, selected_for_meta DESC, objective_score DESC;

CREATE OR REPLACE VIEW latest_m28_nested_predictions AS
SELECT * FROM m28_nested_predictions
WHERE run_id=(SELECT run_id FROM module28_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_m28_calibration_comparison AS
SELECT * FROM m28_calibration_comparison
WHERE run_id=(SELECT run_id FROM module28_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY outer_fold, selected DESC, validation_mae;

CREATE OR REPLACE VIEW latest_m28_fold_summary AS
SELECT * FROM m28_fold_summary
WHERE run_id=(SELECT run_id FROM module28_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY outer_fold;

CREATE OR REPLACE VIEW latest_m28_robustness_summary AS
SELECT * FROM m28_robustness_summary
WHERE run_id=(SELECT run_id FROM module28_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY robustness_key;

CREATE OR REPLACE VIEW latest_m28_research_summary AS
SELECT * FROM m28_research_summary
WHERE run_id=(SELECT run_id FROM module28_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

CORE_FEATURES = [
    "liquidity_score", "trend_score", "risk_score", "recovery_score",
    "change_pressure", "btc_return_90d", "btc_distance_sma200",
    "btc_volatility_90d", "btc_drawdown_180d", "core_breadth",
    "stablecoin_growth_30d", "high_yield_spread", "dollar_index",
    "fear_greed",
]

REPRESENTATION_FEATURES = [
    "correlation_mean_90d", "correlation_dispersion_90d",
    "beta_dispersion_180d", "volatility_term_ratio",
    "downside_share_30d", "return_skew_90d",
    "breadth_momentum_30d", "alt_relative_strength_30d",
    "alt_relative_strength_90d", "drawdown_velocity_30d",
    "trend_acceleration", "liquidity_impulse", "credit_impulse",
    "dollar_impulse", "stress_concentration", "risk_on_composite",
    "risk_off_composite", "transition_pressure",
]

def utcnow():
    return datetime.now(timezone.utc)

def safe(value: Any, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return float(default)
    return float(value)

def normalize_probability(values):
    values = np.asarray(values, dtype=float)
    values = np.clip(values, 1e-12, None)
    return values / values.sum()

def temperature_scale(probability, temperature):
    p = np.clip(np.asarray(probability, dtype=float), 1e-12, 1)
    logits = np.log(p) / max(float(temperature), 0.05)
    logits -= logits.max()
    return normalize_probability(np.exp(np.clip(logits, -50, 50)))

class Module28Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE25_SCHEMA)
        self.conn.execute(MODULE27_SCHEMA)
        self.conn.execute(MODULE28_SCHEMA)
        self.cfg = self.settings["module28"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        row = self.conn.execute(
            "SELECT run_id FROM module27_runs WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("No successful Module 27 run is available.")
        self.source_module27_run_id = str(row[0])
        row = self.conn.execute(
            "SELECT source_module25_run_id FROM module27_runs WHERE run_id=?",
            [self.source_module27_run_id],
        ).fetchone()
        self.source_module25_run_id = str(row[0])

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m28_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m28_stage"
        )
        self.conn.unregister("_m28_stage")

    def data(self):
        base = self.conn.execute(
            "SELECT * FROM m25_regime_features WHERE run_id=? ORDER BY observation_date",
            [self.source_module25_run_id],
        ).fetchdf()
        rep = self.conn.execute(
            "SELECT * FROM m27_representation_features WHERE run_id=? "
            "ORDER BY observation_date",
            [self.source_module27_run_id],
        ).fetchdf()
        labels = self.conn.execute(
            "SELECT observation_date, dominant_regime "
            "FROM m25_regime_probabilities WHERE run_id=? ORDER BY observation_date",
            [self.source_module25_run_id],
        ).fetchdf()
        for frame in (base, rep, labels):
            frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        base = base.set_index("observation_date")
        rep = rep.set_index("observation_date")
        labels = labels.set_index("observation_date")
        available_core = [c for c in CORE_FEATURES if c in base.columns]
        available_rep = [c for c in REPRESENTATION_FEATURES if c in rep.columns]
        frame = pd.concat(
            [base[available_core], rep[available_rep], labels], axis=1
        ).replace([np.inf, -np.inf], np.nan).dropna()
        return frame, available_core, available_rep

    @staticmethod
    def transition_matrix(labels):
        counts = pd.DataFrame(1.0, index=REGIMES, columns=REGIMES)
        values = labels.dropna().tolist()
        for current, nxt in zip(values[:-1], values[1:]):
            counts.loc[current, nxt] += 1
        return counts.div(counts.sum(axis=1), axis=0)

    @staticmethod
    def rule_probability(row):
        scores = np.array([
            1.25*safe(row.get("liquidity_score"))
            + .45*safe(row.get("risk_on_composite"))
            + .30*safe(row.get("breadth_momentum_30d"))
            - .25*safe(row.get("risk_score")),
            1.30*safe(row.get("trend_score"))
            + .45*safe(row.get("alt_relative_strength_30d"))
            + .25*safe(row.get("core_breadth")),
            1.25*safe(row.get("recovery_score"))
            + .40*safe(row.get("drawdown_velocity_30d"))
            + .25*safe(row.get("liquidity_impulse")),
            -.80*abs(safe(row.get("trend_score")))
            -.45*abs(safe(row.get("liquidity_score")))
            -.20*safe(row.get("transition_pressure")),
            1.20*safe(row.get("risk_score"))
            + .40*safe(row.get("risk_off_composite"))
            -.50*safe(row.get("liquidity_score")),
            1.15*safe(row.get("volatility_term_ratio"))
            + .70*safe(row.get("stress_concentration"))
            + .60*safe(row.get("transition_pressure")),
        ])
        scores -= scores.max()
        return normalize_probability(np.exp(np.clip(scores, -50, 50)))

    @staticmethod
    def cluster_map(centers, scaler, columns):
        original = scaler.inverse_transform(centers)
        mapping, used = {}, set()
        for index, values in enumerate(original):
            row = pd.Series(values, index=columns)
            order = np.argsort(-Module28Runner.rule_probability(row))
            regime = next(
                (REGIMES[i] for i in order if REGIMES[i] not in used),
                REGIMES[int(order[0])],
            )
            mapping[index] = regime
            used.add(regime)
        return mapping

    @staticmethod
    def prototypes(train_x, train_y):
        scaler = StandardScaler()
        values = scaler.fit_transform(train_x)
        frame = pd.DataFrame(values, index=train_x.index, columns=train_x.columns)
        means, variances = {}, {}
        for regime in REGIMES:
            group = frame[train_y == regime]
            if group.empty:
                means[regime] = np.zeros(train_x.shape[1])
                variances[regime] = np.ones(train_x.shape[1]) * 4
            else:
                means[regime] = group.mean().to_numpy()
                variances[regime] = (
                    group.var().fillna(1).clip(lower=.05).to_numpy()
                )
        return scaler, means, variances

    @staticmethod
    def emission(row, means, variances):
        log_likelihoods = []
        for regime in REGIMES:
            diff = row - means[regime]
            var = variances[regime]
            log_likelihoods.append(
                -.5*np.sum(np.log(2*math.pi*var)+(diff*diff)/var)
            )
        x = np.asarray(log_likelihoods)
        x -= x.max()
        return normalize_probability(np.exp(np.clip(x, -50, 50)))

    def components(self, train_x, train_y, test_x):
        scaler = StandardScaler()
        x_train = scaler.fit_transform(train_x)
        x_test = scaler.transform(test_x)
        seed = int(self.cfg["models"]["random_state"])
        gmm = GaussianMixture(
            n_components=6, covariance_type="diag", random_state=seed,
            reg_covar=1e-4, n_init=5
        ).fit(x_train)
        kmeans = KMeans(
            n_clusters=6, random_state=seed, n_init=20
        ).fit(x_train)
        gmap = self.cluster_map(gmm.means_, scaler, train_x.columns)
        kmap = self.cluster_map(
            kmeans.cluster_centers_, scaler, train_x.columns
        )
        gp = gmm.predict_proba(x_test)
        kl = kmeans.predict(x_test)
        state_scaler, means, variances = self.prototypes(train_x, train_y)
        state_test = state_scaler.transform(test_x)
        transition = self.transition_matrix(train_y)
        prior_regime = train_y.iloc[-1]
        output = []
        for index, (_, row) in enumerate(test_x.iterrows()):
            g = np.zeros(6)
            for cluster in range(6):
                g[REGIMES.index(gmap[cluster])] += gp[index, cluster]
            k = np.zeros(6)
            k[REGIMES.index(kmap[int(kl[index])])] = 1
            rule = self.rule_probability(row)
            prior = transition.loc[prior_regime].reindex(REGIMES).to_numpy()
            state = normalize_probability(
                self.emission(state_test[index], means, variances) * prior
            )
            output.append((g, k, rule, state, prior))
            prior_regime = REGIMES[int(np.argmax(state))]
        return output

    @staticmethod
    def apply_candidate(component, candidate, previous=None):
        g, k, rule, state, prior = component
        state_adjusted = normalize_probability(
            state * np.power(
                np.clip(prior, 1e-6, 1),
                candidate["transition_strength"] - 1,
            )
        )
        weights = candidate["weights"]
        probability = normalize_probability(
            weights[0]*g + weights[1]*k
            + weights[2]*rule + weights[3]*state_adjusted
        )
        probability = temperature_scale(
            probability, candidate["temperature"]
        )
        if previous is not None:
            probability = normalize_probability(
                previous*candidate["smoothing"]
                + probability*(1-candidate["smoothing"])
            )
        return probability

    def evaluate(self, components, actual, candidate):
        probabilities, predictions = [], []
        previous = None
        for component in components:
            p = self.apply_candidate(component, candidate, previous)
            probabilities.append(p)
            predictions.append(REGIMES[int(np.argmax(p))])
            previous = p
        correctness = np.array(
            [p == a for p, a in zip(predictions, actual)], dtype=float
        )
        confidence = np.array([p.max() for p in probabilities])
        agreement = float(correctness.mean()*100)
        calibration_mae = float(np.mean(np.abs(confidence-correctness)))
        switch_rate = (
            float(np.mean(
                np.asarray(predictions[1:])
                != np.asarray(predictions[:-1])
            ))
            if len(predictions)>1 else 0.0
        )
        objective = agreement - 35*calibration_mae - 8*switch_rate
        return {
            "probabilities": probabilities,
            "predictions": predictions,
            "agreement": agreement,
            "calibration_mae": calibration_mae,
            "switch_rate": switch_rate,
            "objective": objective,
        }

    def initial_candidates(self, rng, count):
        anchors = [
            (np.array([.30,.15,.20,.35]), .90, .65, 1.0),
            (np.array([.20,.10,.15,.55]), .80, .72, 1.3),
            (np.array([.35,.20,.30,.15]), 1.10, .55, .75),
        ]
        candidates = []
        for idx, (weights, temperature, smoothing, transition) in enumerate(anchors):
            candidates.append({
                "candidate_id": f"A{idx+1:04d}",
                "weights": weights,
                "temperature": temperature,
                "smoothing": smoothing,
                "transition_strength": transition,
                "generation": 0,
            })
        while len(candidates) < count:
            candidates.append({
                "candidate_id": f"A{len(candidates)+1:04d}",
                "weights": rng.dirichlet([1.7, .9, 1.5, 2.2]),
                "temperature": float(rng.uniform(.70, 1.35)),
                "smoothing": float(rng.uniform(.38, .87)),
                "transition_strength": float(rng.uniform(.50, 1.80)),
                "generation": 0,
            })
        return candidates

    def mutate_candidates(self, rng, elite, count, generation):
        candidates = []
        while len(candidates) < count:
            parent = elite[int(rng.integers(0, len(elite)))]
            concentration = np.maximum(parent["weights"]*45, .5)
            weights = rng.dirichlet(concentration)
            candidates.append({
                "candidate_id": f"G{generation}_{len(candidates)+1:04d}",
                "weights": weights,
                "temperature": float(np.clip(
                    rng.normal(parent["temperature"], .10), .55, 1.50
                )),
                "smoothing": float(np.clip(
                    rng.normal(parent["smoothing"], .06), .25, .92
                )),
                "transition_strength": float(np.clip(
                    rng.normal(parent["transition_strength"], .18), .25, 2.25
                )),
                "generation": generation,
            })
        return candidates

    def adaptive_search(self, components, actual, fold):
        rng = np.random.default_rng(
            int(self.cfg["adaptive_search"]["seed"]) + fold
        )
        initial_count = int(
            self.cfg["adaptive_search"]["initial_candidates"]
        )
        generation_count = int(
            self.cfg["adaptive_search"]["generation_candidates"]
        )
        generations = int(
            self.cfg["adaptive_search"]["generations"]
        )
        elite_count = int(
            self.cfg["adaptive_search"]["elite_count"]
        )
        all_scored = []
        candidates = self.initial_candidates(rng, initial_count)
        for generation in range(generations):
            scored = []
            for candidate in candidates:
                result = self.evaluate(components, actual, candidate)
                scored.append((result["objective"], candidate, result))
                all_scored.append((result["objective"], candidate, result))
            scored.sort(key=lambda item:item[0], reverse=True)
            elite = [item[1] for item in scored[:elite_count]]
            candidates = self.mutate_candidates(
                rng, elite, generation_count, generation+1
            )
        all_scored.sort(key=lambda item:item[0], reverse=True)
        return all_scored

    def feature_selection(self, frame, core_features, rep_features):
        feature_columns = [c for c in frame.columns if c != "dominant_regime"]
        x = frame[feature_columns]
        y = frame["dominant_regime"]
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x)
        classifier = LogisticRegression(
            max_iter=1500, class_weight="balanced",
            random_state=int(self.cfg["models"]["random_state"]),
        )
        classifier.fit(x_scaled, y)
        perm = permutation_importance(
            classifier, x_scaled, y,
            scoring="accuracy",
            n_repeats=int(
                self.cfg["feature_selection"]["permutation_repeats"]
            ),
            random_state=int(self.cfg["models"]["random_state"]),
        )
        corr = x.corr().abs()
        baseline = classifier.score(x_scaled, y)*100
        rows = []
        for index, feature in enumerate(feature_columns):
            source = "CORE" if feature in core_features else "REPRESENTATION"
            redundancy = (
                float(corr.loc[feature].drop(feature).nlargest(3).mean())
                if len(feature_columns)>1 else 0.0
            )
            # Rolling stability and simple information proxy.
            grouped_means = x.groupby(y)[feature].mean()
            information_proxy = float(
                grouped_means.std()
                / max(x[feature].std(), 1e-9)
            )
            # Ablation delta on the same transparent classifier.
            reduced = [c for c in feature_columns if c != feature]
            reduced_scaled = StandardScaler().fit_transform(x[reduced])
            reduced_model = LogisticRegression(
                max_iter=1500, class_weight="balanced",
                random_state=int(self.cfg["models"]["random_state"]),
            ).fit(reduced_scaled, y)
            delta = baseline - reduced_model.score(reduced_scaled, y)*100
            composite = (
                float(perm.importances_mean[index])*100
                + information_proxy*12
                + delta*1.5
                - redundancy*8
            )
            rows.append({
                "run_id": self.run_id,
                "feature_key": feature,
                "source_group": source,
                "permutation_importance": float(
                    perm.importances_mean[index]
                ),
                "mutual_information_proxy": information_proxy,
                "fold_survival_rate_pct": 0.0,
                "mean_ablation_delta_pct": delta,
                "redundancy_penalty": redundancy,
                "composite_score": composite,
                "retained": False,
                "selection_rank": None,
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows).sort_values(
            "composite_score", ascending=False
        )
        minimum_core = int(
            self.cfg["feature_selection"]["minimum_core_features"]
        )
        max_features = int(
            self.cfg["feature_selection"]["maximum_features"]
        )
        max_corr = float(
            self.cfg["feature_selection"]["maximum_pairwise_correlation"]
        )
        retained = []
        core_ranked = result[
            result["source_group"]=="CORE"
        ]["feature_key"].tolist()
        for feature in core_ranked[:minimum_core]:
            retained.append(feature)
        for feature in result["feature_key"]:
            if feature in retained:
                continue
            if all(
                corr.loc[feature, other] < max_corr
                for other in retained
            ):
                retained.append(feature)
            if len(retained) >= max_features:
                break
        result["retained"] = result["feature_key"].isin(retained)
        ranks = {feature:index+1 for index,feature in enumerate(retained)}
        result["selection_rank"] = result["feature_key"].map(ranks)
        return result, retained

    def select_features_for_fold(
        self,
        train,
        candidate_features=None,
    ):
        if "dominant_regime" not in train.columns:
            raise ValueError(
                "Fold training data must contain dominant_regime."
            )
        excluded = {
            "dominant_regime",
            "run_id",
            "calculated_at_utc",
        }
        available = [
            column
            for column in train.columns
            if column not in excluded
            and pd.api.types.is_numeric_dtype(train[column])
        ]
        if candidate_features is not None:
            allowed = set(candidate_features)
            available = [
                column
                for column in available
                if column in allowed
            ]
        if not available:
            raise ValueError(
                "No eligible fold-local features are available."
            )
        maximum_features = int(
            self.cfg["feature_selection"]["maximum_features"]
        )
        core_features = [
            feature
            for feature in available
            if feature in CORE_FEATURES
        ]
        representation_features = [
            feature
            for feature in available
            if feature not in CORE_FEATURES
        ]
        if train["dominant_regime"].nunique() < 2:
            fallback = (
                core_features + representation_features
            )[:maximum_features]
            if not fallback:
                raise ValueError(
                    "Fold-local fallback returned no features."
                )
            return fallback
        fold_frame = train[
            available + ["dominant_regime"]
        ].copy()
        _, retained = self.feature_selection(
            fold_frame,
            core_features,
            representation_features,
        )
        if not retained:
            raise ValueError(
                "Fold-local feature selection returned no features."
            )
        return retained

    def calibrators(self, raw, correct):
        results = {}
        # Isotonic.
        if len(np.unique(raw))>1 and len(np.unique(correct))>1:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(raw, correct)
            iso_values = iso.predict(raw)
            results["ISOTONIC"] = (
                iso, float(np.mean(np.abs(iso_values-correct))),
                float(np.mean((iso_values-correct)**2))
            )
            platt = LogisticRegression(random_state=280)
            platt.fit(np.asarray(raw).reshape(-1,1), correct.astype(int))
            platt_values = platt.predict_proba(
                np.asarray(raw).reshape(-1,1)
            )[:,1]
            results["PLATT"] = (
                platt, float(np.mean(np.abs(platt_values-correct))),
                float(np.mean((platt_values-correct)**2))
            )
        results["IDENTITY"] = (
            None,
            float(np.mean(np.abs(raw-correct))),
            float(np.mean((raw-correct)**2)),
        )
        return results

    @staticmethod
    def apply_calibrator(method, model, values):
        values = np.asarray(values)
        if method == "ISOTONIC":
            return model.predict(values)
        if method == "PLATT":
            return model.predict_proba(values.reshape(-1,1))[:,1]
        return values

    def nested_run(self, frame, retained):
        train_days = int(
            self.cfg["nested_walk_forward"]["minimum_training_days"]
        )
        inner_days = int(
            self.cfg["nested_walk_forward"]["inner_validation_days"]
        )
        test_days = int(
            self.cfg["nested_walk_forward"]["outer_test_days"]
        )
        top_meta = int(
            self.cfg["meta_ensemble"]["top_candidates"]
        )
        rows, search_rows, calibration_rows, fold_rows = [], [], [], []
        fold = 0
        start = train_days
        while start < len(frame):
            end = min(start+test_days, len(frame))
            train = frame.iloc[:start]
            test = frame.iloc[start:end]
            if len(test)==0 or len(train)<=inner_days+240:
                break
            fold += 1
            fold_retained = self.select_features_for_fold(
                train,
                retained,
            )
            inner_train = train.iloc[:-inner_days]
            inner_test = train.iloc[-inner_days:]
            inner_components = self.components(
                inner_train[fold_retained],
                inner_train["dominant_regime"],
                inner_test[fold_retained],
            )
            scored = self.adaptive_search(
                inner_components,
                inner_test["dominant_regime"].tolist(),
                fold,
            )
            selected = scored[:top_meta]
            objectives = np.array([item[0] for item in selected])
            objective_weights = np.exp(
                (objectives-objectives.max())
                / max(float(self.cfg["meta_ensemble"]["temperature"]), .1)
            )
            objective_weights = objective_weights/objective_weights.sum()
            selected_ids = {
                item[1]["candidate_id"]: float(weight)
                for item,weight in zip(selected,objective_weights)
            }
            for objective,candidate,result in scored:
                weights = candidate["weights"]
                search_rows.append({
                    "run_id": self.run_id,
                    "outer_fold": fold,
                    "generation": candidate["generation"],
                    "candidate_id": candidate["candidate_id"],
                    "gmm_weight": float(weights[0]),
                    "kmeans_weight": float(weights[1]),
                    "rules_weight": float(weights[2]),
                    "state_space_weight": float(weights[3]),
                    "probability_temperature": candidate["temperature"],
                    "smoothing": candidate["smoothing"],
                    "transition_strength": candidate["transition_strength"],
                    "inner_agreement_pct": result["agreement"],
                    "inner_calibration_mae": result["calibration_mae"],
                    "inner_switch_rate": result["switch_rate"],
                    "objective_score": objective,
                    "selected_for_meta": candidate["candidate_id"] in selected_ids,
                    "meta_weight": selected_ids.get(candidate["candidate_id"],0.0),
                    "calculated_at_utc": utcnow(),
                })

            # Build inner meta probabilities for calibration choice.
            inner_meta = []
            for date_index in range(len(inner_test)):
                combined = np.zeros(6)
                for (objective,candidate,result),weight in zip(
                    selected, objective_weights
                ):
                    combined += weight*result["probabilities"][date_index]
                inner_meta.append(normalize_probability(combined))
            inner_raw = np.array([p.max() for p in inner_meta])
            inner_pred = [
                REGIMES[int(np.argmax(p))] for p in inner_meta
            ]
            inner_correct = np.array([
                pred==actual for pred,actual in zip(
                    inner_pred,
                    inner_test["dominant_regime"].tolist()
                )
            ],dtype=float)
            calibration_candidates = self.calibrators(
                inner_raw, inner_correct
            )
            selected_method = min(
                calibration_candidates,
                key=lambda method: (
                    calibration_candidates[method][1],
                    calibration_candidates[method][2],
                ),
            )
            for method,(model,mae,brier) in calibration_candidates.items():
                calibration_rows.append({
                    "run_id": self.run_id,
                    "outer_fold": fold,
                    "calibration_method": method,
                    "validation_rows": len(inner_raw),
                    "validation_mae": mae,
                    "validation_brier": brier,
                    "selected": method==selected_method,
                    "calculated_at_utc": utcnow(),
                })

            outer_components = self.components(
                train[fold_retained],
                train["dominant_regime"],
                test[fold_retained],
            )
            candidate_outer_results = []
            for _,candidate,_ in selected:
                candidate_outer_results.append(
                    self.evaluate(
                        outer_components,
                        test["dominant_regime"].tolist(),
                        candidate,
                    )
                )
            outer_probabilities = []
            for date_index in range(len(test)):
                p = np.zeros(6)
                for result,weight in zip(
                    candidate_outer_results, objective_weights
                ):
                    p += weight*result["probabilities"][date_index]
                outer_probabilities.append(normalize_probability(p))
            raw_values = np.array([p.max() for p in outer_probabilities])
            selected_model = calibration_candidates[selected_method][0]
            calibrated_values = self.apply_calibrator(
                selected_method, selected_model, raw_values
            )
            predicted = [
                REGIMES[int(np.argmax(p))]
                for p in outer_probabilities
            ]
            actual = test["dominant_regime"].tolist()
            correctness = np.array(
                [p==a for p,a in zip(predicted,actual)],dtype=float
            )
            for date,pred,act,raw,calibrated in zip(
                test.index,predicted,actual,raw_values,calibrated_values
            ):
                rows.append({
                    "run_id": self.run_id,
                    "outer_fold": fold,
                    "observation_date": date.date(),
                    "training_start_date": train.index.min().date(),
                    "training_end_date": train.index.max().date(),
                    "testing_start_date": test.index.min().date(),
                    "testing_end_date": test.index.max().date(),
                    "retained_features_json": json.dumps(fold_retained),
                    "meta_candidates_json": json.dumps(selected_ids,sort_keys=True),
                    "calibration_method": selected_method,
                    "actual_regime": act,
                    "predicted_regime": pred,
                    "raw_confidence": float(raw),
                    "calibrated_confidence": float(calibrated),
                    "label_match": bool(pred==act),
                    "calculated_at_utc": utcnow(),
                })
            switch_rate = (
                float(np.mean(
                    np.asarray(predicted[1:])
                    != np.asarray(predicted[:-1])
                ))
                if len(predicted)>1 else 0.0
            )
            fold_rows.append({
                "run_id": self.run_id,
                "outer_fold": fold,
                "testing_start_date": test.index.min().date(),
                "testing_end_date": test.index.max().date(),
                "test_days": len(test),
                "retained_features": len(fold_retained),
                "meta_candidates": len(selected),
                "agreement_pct": float(correctness.mean()*100),
                "raw_calibration_mae": float(
                    np.mean(np.abs(raw_values-correctness))
                ),
                "calibrated_mae": float(
                    np.mean(np.abs(calibrated_values-correctness))
                ),
                "mean_confidence": float(np.mean(calibrated_values)),
                "switch_rate": switch_rate,
                "selected_calibration": selected_method,
                "calculated_at_utc": utcnow(),
            })
            start = end
        return (
            pd.DataFrame(search_rows),
            pd.DataFrame(rows),
            pd.DataFrame(calibration_rows),
            pd.DataFrame(fold_rows),
        )

    def robustness(self, frame, retained, primary):
        scenarios = {
            "PRIMARY": retained,
            "CORE_ONLY": [c for c in retained if c in CORE_FEATURES],
            "TOP_8": retained[:min(8,len(retained))],
            "DROP_LOWEST_2": retained[:-2] if len(retained)>2 else retained,
        }
        baseline = primary.set_index("observation_date")
        output = []
        original_initial = self.cfg["adaptive_search"]["initial_candidates"]
        original_generation = self.cfg["adaptive_search"]["generation_candidates"]
        original_generations = self.cfg["adaptive_search"]["generations"]
        for key,features in scenarios.items():
            if key=="PRIMARY":
                predictions = primary
            else:
                self.cfg["adaptive_search"]["initial_candidates"] = int(
                    self.cfg["robustness"]["initial_candidates"]
                )
                self.cfg["adaptive_search"]["generation_candidates"] = int(
                    self.cfg["robustness"]["generation_candidates"]
                )
                self.cfg["adaptive_search"]["generations"] = int(
                    self.cfg["robustness"]["generations"]
                )
                try:
                    _,predictions,_,_ = self.nested_run(frame,features)
                finally:
                    self.cfg["adaptive_search"]["initial_candidates"] = original_initial
                    self.cfg["adaptive_search"]["generation_candidates"] = original_generation
                    self.cfg["adaptive_search"]["generations"] = original_generations
            if predictions.empty:
                continue
            indexed = predictions.set_index("observation_date")
            common = baseline.index.intersection(indexed.index)
            agreement_with_primary = (
                float((
                    baseline.loc[common,"predicted_regime"]
                    == indexed.loc[common,"predicted_regime"]
                ).mean()*100)
                if len(common) else 0.0
            )
            correctness = predictions["label_match"].astype(float)
            mae = float(np.mean(np.abs(
                predictions["calibrated_confidence"]-correctness
            )))
            current = predictions.sort_values("observation_date").iloc[-1]
            output.append({
                "run_id": self.run_id,
                "robustness_key": key,
                "observations": len(predictions),
                "agreement_pct": float(correctness.mean()*100),
                "calibration_mae": mae,
                "agreement_with_primary_pct": agreement_with_primary,
                "current_regime": current["predicted_regime"],
                "current_confidence": float(current["calibrated_confidence"]),
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(output)

    def run(self):
        self.conn.execute("""
            INSERT INTO module28_runs VALUES(
                ?,?,?,NULL,'RUNNING',0,0,0,0,0,NULL,NULL,NULL,
                NULL,NULL,NULL,NULL,'7.3.0'
            )
        """,[self.run_id,self.source_module27_run_id,self.started])
        try:
            frame,core_features,rep_features = self.data()
            feature_research,retained = self.feature_selection(
                frame,core_features,rep_features
            )
            candidate_features = list(dict.fromkeys(
                core_features + rep_features
            ))
            search,predictions,calibration,folds = self.nested_run(
                frame,candidate_features
            )
            robustness = self.robustness(
                frame,retained,predictions
            )
            self.upsert("m28_feature_selection",feature_research)
            self.upsert("m28_adaptive_search",search)
            self.upsert("m28_nested_predictions",predictions)
            self.upsert("m28_calibration_comparison",calibration)
            self.upsert("m28_fold_summary",folds)
            self.upsert("m28_robustness_summary",robustness)

            agreement = float(
                predictions["label_match"].mean()*100
            )
            raw_mae = float(np.mean(np.abs(
                predictions["raw_confidence"]
                - predictions["label_match"].astype(float)
            )))
            calibrated_mae = float(np.mean(np.abs(
                predictions["calibrated_confidence"]
                - predictions["label_match"].astype(float)
            )))
            nonprimary = robustness[
                robustness["robustness_key"]!="PRIMARY"
            ]
            stability = (
                float(nonprimary["agreement_with_primary_pct"].mean())
                if not nonprimary.empty else 0.0
            )
            current = predictions.sort_values(
                "observation_date"
            ).iloc[-1]
            passed = (
                agreement >= float(
                    self.cfg["validation"]["minimum_nested_agreement_pct"]
                )
                and calibrated_mae <= float(
                    self.cfg["validation"]["maximum_calibrated_mae"]
                )
                and stability >= float(
                    self.cfg["validation"]["minimum_meta_stability_pct"]
                )
            )
            status = "PASSED" if passed else "LIMITED"
            recommendation = (
                "READY_FOR_SPECIALIST_STRATEGY_LAB"
                if passed else "CONTINUE_FEATURE_PRUNING_RESEARCH"
            )
            summary = pd.DataFrame([{
                "run_id": self.run_id,
                "candidate_features": len(core_features)+len(rep_features),
                "retained_features": len(retained),
                "retained_feature_list": json.dumps(retained),
                "adaptive_candidates": int(
                    self.cfg["adaptive_search"]["initial_candidates"]
                    + self.cfg["adaptive_search"]["generation_candidates"]
                    * max(
                        self.cfg["adaptive_search"]["generations"]-1,0
                    )
                ),
                "outer_folds": int(
                    predictions["outer_fold"].nunique()
                ),
                "nested_rows": len(predictions),
                "nested_agreement_pct": agreement,
                "raw_calibration_mae": raw_mae,
                "calibrated_mae": calibrated_mae,
                "meta_ensemble_stability_pct": stability,
                "current_regime": current["predicted_regime"],
                "current_confidence": float(
                    current["calibrated_confidence"]
                ),
                "validation_status": status,
                "advancement_recommendation": recommendation,
                "calculated_at_utc": utcnow(),
            }])
            self.upsert("m28_research_summary",summary)
            record = summary.iloc[0]
            self.conn.execute("""
                UPDATE module28_runs
                SET completed_at_utc=?,status='SUCCESS',
                    candidate_features=?,retained_features=?,
                    adaptive_candidates=?,outer_folds=?,nested_rows=?,
                    nested_agreement_pct=?,calibrated_mae=?,
                    meta_ensemble_stability_pct=?,
                    current_regime=?,current_confidence=?,
                    validation_status=?,notes=?
                WHERE run_id=?
            """,[
                utcnow(),
                int(record["candidate_features"]),
                int(record["retained_features"]),
                int(record["adaptive_candidates"]),
                int(record["outer_folds"]),
                int(record["nested_rows"]),
                float(record["nested_agreement_pct"]),
                float(record["calibrated_mae"]),
                float(record["meta_ensemble_stability_pct"]),
                record["current_regime"],
                float(record["current_confidence"]),
                record["validation_status"],
                (
                    "v7.3 prunes features, adaptively concentrates search, "
                    "compares calibration methods, and blends top candidates. "
                    "Modules 25-27 remain unchanged."
                ),
                self.run_id,
            ])
            self.conn.close()
            return record.to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module28_runs SET completed_at_utc=?,"
                "status='FAILED',notes=? WHERE run_id=?",
                [utcnow(),str(exc)[:1000],self.run_id],
            )
            self.conn.close()
            raise

def run_module28():
    return Module28Runner().run()
