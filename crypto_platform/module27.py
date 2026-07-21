from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.isotonic import IsotonicRegression
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA, REGIMES
from crypto_platform.module26 import MODULE26_SCHEMA

MODULE27_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module27_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module25_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    representation_features INTEGER,
    random_candidates INTEGER,
    outer_folds INTEGER,
    nested_rows INTEGER,
    nested_agreement_pct DOUBLE,
    calibrated_mae DOUBLE,
    empirical_stability_pct DOUBLE,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    validation_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m27_representation_features(
    run_id VARCHAR,
    observation_date DATE,
    correlation_mean_90d DOUBLE,
    correlation_dispersion_90d DOUBLE,
    beta_dispersion_180d DOUBLE,
    volatility_term_ratio DOUBLE,
    downside_share_30d DOUBLE,
    return_skew_90d DOUBLE,
    breadth_momentum_30d DOUBLE,
    alt_relative_strength_30d DOUBLE,
    alt_relative_strength_90d DOUBLE,
    drawdown_velocity_30d DOUBLE,
    trend_acceleration DOUBLE,
    liquidity_impulse DOUBLE,
    credit_impulse DOUBLE,
    dollar_impulse DOUBLE,
    stress_concentration DOUBLE,
    risk_on_composite DOUBLE,
    risk_off_composite DOUBLE,
    transition_pressure DOUBLE,
    feature_completeness_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m27_random_search(
    run_id VARCHAR,
    outer_fold INTEGER,
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
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, outer_fold, candidate_id)
);

CREATE TABLE IF NOT EXISTS m27_nested_predictions(
    run_id VARCHAR,
    outer_fold INTEGER,
    observation_date DATE,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    selected_candidate_id VARCHAR,
    selected_parameters_json VARCHAR,
    actual_regime VARCHAR,
    predicted_regime VARCHAR,
    raw_confidence DOUBLE,
    calibrated_confidence DOUBLE,
    label_match BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m27_empirical_sensitivity(
    run_id VARCHAR,
    scenario_key VARCHAR,
    scenario_description VARCHAR,
    nested_rows INTEGER,
    agreement_pct DOUBLE,
    agreement_with_baseline_pct DOUBLE,
    calibration_mae DOUBLE,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, scenario_key)
);

CREATE TABLE IF NOT EXISTS m27_calibration_summary(
    run_id VARCHAR,
    confidence_bin VARCHAR,
    observations INTEGER,
    mean_raw_confidence DOUBLE,
    mean_calibrated_confidence DOUBLE,
    observed_accuracy DOUBLE,
    raw_error DOUBLE,
    calibrated_error DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, confidence_bin)
);

CREATE TABLE IF NOT EXISTS m27_fold_summary(
    run_id VARCHAR,
    outer_fold INTEGER,
    testing_start_date DATE,
    testing_end_date DATE,
    test_days INTEGER,
    agreement_pct DOUBLE,
    mean_raw_confidence DOUBLE,
    mean_calibrated_confidence DOUBLE,
    switch_rate DOUBLE,
    selected_candidate_id VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, outer_fold)
);

CREATE TABLE IF NOT EXISTS m27_research_summary(
    run_id VARCHAR PRIMARY KEY,
    representation_features INTEGER,
    random_candidates INTEGER,
    outer_folds INTEGER,
    nested_rows INTEGER,
    nested_agreement_pct DOUBLE,
    raw_calibration_mae DOUBLE,
    calibrated_mae DOUBLE,
    empirical_stability_pct DOUBLE,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m27_representation_features AS
SELECT * FROM m27_representation_features
WHERE run_id=(SELECT run_id FROM module27_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_m27_random_search AS
SELECT * FROM m27_random_search
WHERE run_id=(SELECT run_id FROM module27_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY outer_fold, selected DESC, objective_score DESC;

CREATE OR REPLACE VIEW latest_m27_nested_predictions AS
SELECT * FROM m27_nested_predictions
WHERE run_id=(SELECT run_id FROM module27_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_m27_empirical_sensitivity AS
SELECT * FROM m27_empirical_sensitivity
WHERE run_id=(SELECT run_id FROM module27_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY scenario_key;

CREATE OR REPLACE VIEW latest_m27_calibration_summary AS
SELECT * FROM m27_calibration_summary
WHERE run_id=(SELECT run_id FROM module27_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY confidence_bin;

CREATE OR REPLACE VIEW latest_m27_fold_summary AS
SELECT * FROM m27_fold_summary
WHERE run_id=(SELECT run_id FROM module27_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY outer_fold;

CREATE OR REPLACE VIEW latest_m27_research_summary AS
SELECT * FROM m27_research_summary
WHERE run_id=(SELECT run_id FROM module27_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

CORE_IDS = ["bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"]

def utcnow():
    return datetime.now(timezone.utc)

def safe(value: Any, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return float(default)
    return float(value)

def normalize_probability(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    values = np.clip(values, 1e-12, None)
    return values / values.sum()

def temperature_scale(probability: np.ndarray, temperature: float) -> np.ndarray:
    p = np.clip(probability, 1e-12, 1.0)
    logits = np.log(p) / max(temperature, 0.05)
    logits -= logits.max()
    scaled = np.exp(logits)
    return scaled / scaled.sum()

class Module27Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE25_SCHEMA)
        self.conn.execute(MODULE26_SCHEMA)
        self.conn.execute(MODULE27_SCHEMA)
        self.cfg = self.settings["module27"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        row = self.conn.execute(
            "SELECT run_id FROM module25_runs WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("No successful Module 25 run is available.")
        self.source_run_id = str(row[0])

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m27_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m27_stage"
        )
        self.conn.unregister("_m27_stage")

    def prices(self) -> pd.DataFrame:
        frame = self.conn.execute("""
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana',
                'chainlink','xrp','avalanche'
            ) AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
        """).fetchdf()
        if frame.empty:
            raise RuntimeError("Canonical market history is empty.")
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.pivot(
            index="observation_date", columns="asset_id", values="price_usd"
        ).sort_index()

    def base_features(self) -> pd.DataFrame:
        frame = self.conn.execute(
            "SELECT * FROM m25_regime_features WHERE run_id=? ORDER BY observation_date",
            [self.source_run_id],
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date").sort_index()

    def labels(self) -> pd.DataFrame:
        frame = self.conn.execute(
            "SELECT observation_date, dominant_regime "
            "FROM m25_regime_probabilities WHERE run_id=? ORDER BY observation_date",
            [self.source_run_id],
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date").sort_index()

    @staticmethod
    def rolling_beta(asset: pd.Series, benchmark: pd.Series, window: int) -> pd.Series:
        covariance = asset.rolling(window).cov(benchmark)
        variance = benchmark.rolling(window).var().replace(0, np.nan)
        return covariance / variance

    def build_representation(
        self, price: pd.DataFrame, base: pd.DataFrame
    ) -> pd.DataFrame:
        returns = price.pct_change(fill_method=None)
        btc = returns["bitcoin"]
        alt_cols = [asset for asset in CORE_IDS if asset != "bitcoin"]

        correlations = []
        betas = []
        for asset in alt_cols:
            correlations.append(returns[asset].rolling(90).corr(btc).rename(asset))
            betas.append(self.rolling_beta(returns[asset], btc, 180).rename(asset))
        corr_frame = pd.concat(correlations, axis=1)
        beta_frame = pd.concat(betas, axis=1)

        short_vol = btc.rolling(30).std() * math.sqrt(365)
        long_vol = btc.rolling(90).std() * math.sqrt(365)
        negative_share = (returns["bitcoin"] < 0).rolling(30).mean()
        skew = returns["bitcoin"].rolling(90).skew()
        alt_30 = price[alt_cols].pct_change(30, fill_method=None).mean(axis=1)
        alt_90 = price[alt_cols].pct_change(90, fill_method=None).mean(axis=1)
        btc_30 = price["bitcoin"].pct_change(30, fill_method=None)
        btc_90 = price["bitcoin"].pct_change(90, fill_method=None)

        frame = pd.DataFrame(index=price.index)
        frame["correlation_mean_90d"] = corr_frame.mean(axis=1)
        frame["correlation_dispersion_90d"] = corr_frame.std(axis=1)
        frame["beta_dispersion_180d"] = beta_frame.std(axis=1)
        frame["volatility_term_ratio"] = short_vol / long_vol.replace(0, np.nan)
        frame["downside_share_30d"] = negative_share
        frame["return_skew_90d"] = skew
        frame["breadth_momentum_30d"] = base["core_breadth"].diff(30)
        frame["alt_relative_strength_30d"] = alt_30 - btc_30
        frame["alt_relative_strength_90d"] = alt_90 - btc_90
        frame["drawdown_velocity_30d"] = base["btc_drawdown_180d"].diff(30)
        frame["trend_acceleration"] = base["trend_score"].diff(30)
        frame["liquidity_impulse"] = base["liquidity_score"].diff(30)
        frame["credit_impulse"] = -base["high_yield_spread"].diff(30)
        frame["dollar_impulse"] = -base["dollar_index"].pct_change(
            30, fill_method=None
        )
        frame["stress_concentration"] = (
            base["risk_score"]
            * frame["correlation_mean_90d"]
            * frame["volatility_term_ratio"]
        )
        frame["risk_on_composite"] = pd.concat([
            frame["alt_relative_strength_30d"],
            frame["breadth_momentum_30d"],
            frame["liquidity_impulse"],
            frame["trend_acceleration"],
        ], axis=1).rank(pct=True).mean(axis=1)
        frame["risk_off_composite"] = pd.concat([
            frame["volatility_term_ratio"],
            frame["downside_share_30d"],
            frame["stress_concentration"],
            -frame["credit_impulse"],
        ], axis=1).rank(pct=True).mean(axis=1)
        frame["transition_pressure"] = pd.concat([
            frame["trend_acceleration"].abs(),
            frame["liquidity_impulse"].abs(),
            frame["drawdown_velocity_30d"].abs(),
            frame["volatility_term_ratio"].diff(7).abs(),
        ], axis=1).rank(pct=True).mean(axis=1)
        frame["feature_completeness_pct"] = frame.notna().mean(axis=1) * 100

        output = frame.reset_index().rename(columns={"index": "observation_date"})
        output.insert(0, "run_id", self.run_id)
        output["observation_date"] = pd.to_datetime(
            output["observation_date"]
        ).dt.date
        output["calculated_at_utc"] = utcnow()
        self.upsert("m27_representation_features", output)
        return frame

    def model_frame(
        self, base: pd.DataFrame, representation: pd.DataFrame, labels: pd.DataFrame
    ) -> pd.DataFrame:
        base_cols = [
            "liquidity_score", "trend_score", "risk_score", "recovery_score",
            "change_pressure", "btc_return_90d", "btc_distance_sma200",
            "btc_volatility_90d", "btc_drawdown_180d", "core_breadth",
            "stablecoin_growth_30d", "high_yield_spread", "dollar_index",
            "fear_greed",
        ]
        rep_cols = [
            c for c in representation.columns
            if c != "feature_completeness_pct"
        ]
        frame = pd.concat(
            [base[base_cols], representation[rep_cols], labels], axis=1
        ).replace([np.inf, -np.inf], np.nan).dropna()
        return frame

    @staticmethod
    def transition_matrix(labels: pd.Series) -> pd.DataFrame:
        counts = pd.DataFrame(1.0, index=REGIMES, columns=REGIMES)
        values = labels.dropna().tolist()
        for a, b in zip(values[:-1], values[1:]):
            counts.loc[a, b] += 1
        return counts.div(counts.sum(axis=1), axis=0)

    @staticmethod
    def regime_prototypes(train_x: pd.DataFrame, train_y: pd.Series):
        scaler = StandardScaler()
        scaled = scaler.fit_transform(train_x)
        scaled_frame = pd.DataFrame(scaled, index=train_x.index, columns=train_x.columns)
        means, variances = {}, {}
        for regime in REGIMES:
            group = scaled_frame[train_y == regime]
            if group.empty:
                means[regime] = np.zeros(train_x.shape[1])
                variances[regime] = np.ones(train_x.shape[1]) * 4
            else:
                means[regime] = group.mean(axis=0).to_numpy()
                variances[regime] = (
                    group.var(axis=0).fillna(1.0).clip(lower=0.05).to_numpy()
                )
        return scaler, means, variances

    @staticmethod
    def emission_probability(
        scaled_row: np.ndarray, means: dict, variances: dict
    ) -> np.ndarray:
        scores = []
        for regime in REGIMES:
            diff = scaled_row - means[regime]
            var = variances[regime]
            log_likelihood = -0.5 * np.sum(
                np.log(2 * math.pi * var) + (diff * diff) / var
            )
            scores.append(log_likelihood)
        scores = np.asarray(scores)
        scores -= scores.max()
        p = np.exp(np.clip(scores, -50, 50))
        return normalize_probability(p)

    @staticmethod
    def rule_probability(row: pd.Series) -> np.ndarray:
        scores = np.array([
            1.2*safe(row.get("liquidity_score"))
            + .5*safe(row.get("risk_on_composite"))
            + .3*safe(row.get("breadth_momentum_30d"))
            - .3*safe(row.get("risk_off_composite")),
            1.2*safe(row.get("trend_score"))
            + .6*safe(row.get("alt_relative_strength_30d"))
            + .4*safe(row.get("risk_on_composite")),
            1.2*safe(row.get("recovery_score"))
            + .5*safe(row.get("drawdown_velocity_30d"))
            + .3*safe(row.get("liquidity_impulse")),
            -.8*abs(safe(row.get("trend_score")))
            -.5*abs(safe(row.get("liquidity_impulse")))
            -.3*safe(row.get("transition_pressure")),
            1.1*safe(row.get("risk_score"))
            + .5*safe(row.get("risk_off_composite"))
            -.5*safe(row.get("liquidity_score")),
            1.2*safe(row.get("transition_pressure"))
            + .8*safe(row.get("volatility_term_ratio"))
            + .5*safe(row.get("stress_concentration")),
        ])
        scores -= scores.max()
        p = np.exp(np.clip(scores, -50, 50))
        return normalize_probability(p)

    @staticmethod
    def cluster_mapping(centers, scaler, columns):
        original = scaler.inverse_transform(centers)
        mapping, used = {}, set()
        for index, values in enumerate(original):
            row = pd.Series(values, index=columns)
            scores = Module27Runner.rule_probability(row)
            order = np.argsort(-scores)
            selected = next(
                (REGIMES[i] for i in order if REGIMES[i] not in used),
                REGIMES[int(order[0])],
            )
            mapping[index] = selected
            used.add(selected)
        return mapping

    def components(
        self, train_x: pd.DataFrame, train_y: pd.Series, test_x: pd.DataFrame
    ):
        scaler = StandardScaler()
        train_scaled = scaler.fit_transform(train_x)
        test_scaled = scaler.transform(test_x)
        seed = int(self.cfg["models"]["random_state"])

        gmm = GaussianMixture(
            n_components=6, covariance_type="diag", random_state=seed,
            reg_covar=1e-4, n_init=5
        ).fit(train_scaled)
        km = KMeans(n_clusters=6, random_state=seed, n_init=20).fit(train_scaled)
        gmap = self.cluster_mapping(gmm.means_, scaler, train_x.columns)
        kmap = self.cluster_mapping(km.cluster_centers_, scaler, train_x.columns)

        gmm_probs = gmm.predict_proba(test_scaled)
        km_labels = km.predict(test_scaled)

        state_scaler, means, variances = self.regime_prototypes(train_x, train_y)
        state_scaled = state_scaler.transform(test_x)
        transition = self.transition_matrix(train_y)

        rows = []
        previous = train_y.iloc[-1]
        for i, (_, feature_row) in enumerate(test_x.iterrows()):
            gp = np.zeros(6)
            for cluster in range(6):
                gp[REGIMES.index(gmap[cluster])] += gmm_probs[i, cluster]
            kp = np.zeros(6)
            kp[REGIMES.index(kmap[int(km_labels[i])])] = 1.0
            rp = self.rule_probability(feature_row)
            emission = self.emission_probability(
                state_scaled[i], means, variances
            )
            prior = transition.loc[previous].reindex(REGIMES).to_numpy()
            sp = normalize_probability(emission * np.power(prior, 1.0))
            rows.append((gp, kp, rp, sp, prior))
            previous = REGIMES[int(np.argmax(sp))]
        return rows

    def candidate_set(self, fold: int):
        rng = np.random.default_rng(
            int(self.cfg["random_search"]["seed"]) + fold
        )
        count = int(self.cfg["random_search"]["candidates_per_fold"])
        candidates = []
        anchors = [
            (np.array([.30,.15,.25,.30]), 1.0, .65, 1.0),
            (np.array([.20,.10,.20,.50]), .85, .75, 1.4),
            (np.array([.35,.20,.30,.15]), 1.15, .55, .7),
        ]
        for idx, (weights, temperature, smoothing, transition_strength) in enumerate(anchors):
            candidates.append({
                "candidate_id": f"R{idx+1:04d}",
                "weights": weights,
                "temperature": temperature,
                "smoothing": smoothing,
                "transition_strength": transition_strength,
            })
        while len(candidates) < count:
            weights = rng.dirichlet(np.array([1.8,1.0,1.8,2.2]))
            candidates.append({
                "candidate_id": f"R{len(candidates)+1:04d}",
                "weights": weights,
                "temperature": float(rng.uniform(.70, 1.35)),
                "smoothing": float(rng.uniform(.40, .86)),
                "transition_strength": float(rng.uniform(.50, 1.75)),
            })
        return candidates

    @staticmethod
    def apply_candidate(component, candidate, previous_probability=None):
        gp, kp, rp, sp, prior = component
        state_adjusted = normalize_probability(
            sp * np.power(np.clip(prior, 1e-6, 1), candidate["transition_strength"]-1)
        )
        w = candidate["weights"]
        probability = (
            w[0]*gp + w[1]*kp + w[2]*rp + w[3]*state_adjusted
        )
        probability = temperature_scale(
            normalize_probability(probability), candidate["temperature"]
        )
        if previous_probability is not None:
            probability = (
                previous_probability*candidate["smoothing"]
                + probability*(1-candidate["smoothing"])
            )
        return normalize_probability(probability)

    def evaluate_candidate(self, components, actual, candidate):
        probabilities, predicted = [], []
        previous = None
        for component in components:
            p = self.apply_candidate(component, candidate, previous)
            probabilities.append(p)
            predicted.append(REGIMES[int(np.argmax(p))])
            previous = p
        confidence = np.array([p.max() for p in probabilities])
        correct = np.array(
            [p == a for p, a in zip(predicted, actual)], dtype=float
        )
        agreement = float(correct.mean()*100)
        calibration_mae = float(np.mean(np.abs(confidence-correct)))
        switch_rate = float(
            np.mean(np.array(predicted[1:]) != np.array(predicted[:-1]))
        ) if len(predicted)>1 else 0.0
        objective = agreement - calibration_mae*35 - switch_rate*10
        return {
            "agreement": agreement,
            "calibration_mae": calibration_mae,
            "switch_rate": switch_rate,
            "objective": objective,
            "probabilities": probabilities,
            "predicted": predicted,
        }

    def nested_run(self, frame: pd.DataFrame):
        train_days = int(self.cfg["nested_walk_forward"]["minimum_training_days"])
        inner_days = int(self.cfg["nested_walk_forward"]["inner_validation_days"])
        test_days = int(self.cfg["nested_walk_forward"]["outer_test_days"])
        feature_cols = [c for c in frame.columns if c != "dominant_regime"]

        search_rows, prediction_rows, fold_rows = [], [], []
        fold = 0
        start = train_days
        while start < len(frame):
            end = min(start+test_days, len(frame))
            train = frame.iloc[:start]
            test = frame.iloc[start:end]
            if len(test)==0 or len(train) <= inner_days+240:
                break
            fold += 1
            inner_train = train.iloc[:-inner_days]
            inner_test = train.iloc[-inner_days:]

            inner_components = self.components(
                inner_train[feature_cols],
                inner_train["dominant_regime"],
                inner_test[feature_cols],
            )
            candidates = self.candidate_set(fold)
            scored = []
            for candidate in candidates:
                result = self.evaluate_candidate(
                    inner_components,
                    inner_test["dominant_regime"].tolist(),
                    candidate,
                )
                scored.append((result["objective"], candidate, result))
                weights = candidate["weights"]
                search_rows.append({
                    "run_id": self.run_id,
                    "outer_fold": fold,
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
                    "objective_score": result["objective"],
                    "selected": False,
                    "calculated_at_utc": utcnow(),
                })
            scored.sort(key=lambda x:x[0], reverse=True)
            best_candidate = scored[0][1]
            for row in search_rows:
                if (
                    row["outer_fold"] == fold
                    and row["candidate_id"] == best_candidate["candidate_id"]
                ):
                    row["selected"] = True

            # Inner-fold isotonic calibration.
            best_inner = scored[0][2]
            raw_inner = np.array([p.max() for p in best_inner["probabilities"]])
            correct_inner = np.array([
                pred == actual for pred, actual in zip(
                    best_inner["predicted"],
                    inner_test["dominant_regime"].tolist()
                )
            ], dtype=float)
            calibrator = None
            if len(np.unique(raw_inner)) > 1 and len(np.unique(correct_inner)) > 1:
                calibrator = IsotonicRegression(out_of_bounds="clip")
                calibrator.fit(raw_inner, correct_inner)

            outer_components = self.components(
                train[feature_cols],
                train["dominant_regime"],
                test[feature_cols],
            )
            outer_result = self.evaluate_candidate(
                outer_components,
                test["dominant_regime"].tolist(),
                best_candidate,
            )
            calibrated_values = []
            for date, p, predicted, actual in zip(
                test.index,
                outer_result["probabilities"],
                outer_result["predicted"],
                test["dominant_regime"],
            ):
                raw = float(p.max())
                calibrated = (
                    float(calibrator.predict([raw])[0])
                    if calibrator is not None else raw
                )
                calibrated_values.append(calibrated)
                params = {
                    "weights": best_candidate["weights"].tolist(),
                    "temperature": best_candidate["temperature"],
                    "smoothing": best_candidate["smoothing"],
                    "transition_strength": best_candidate["transition_strength"],
                }
                prediction_rows.append({
                    "run_id": self.run_id,
                    "outer_fold": fold,
                    "observation_date": date.date(),
                    "training_start_date": train.index.min().date(),
                    "training_end_date": train.index.max().date(),
                    "testing_start_date": test.index.min().date(),
                    "testing_end_date": test.index.max().date(),
                    "selected_candidate_id": best_candidate["candidate_id"],
                    "selected_parameters_json": json.dumps(params, sort_keys=True),
                    "actual_regime": actual,
                    "predicted_regime": predicted,
                    "raw_confidence": raw,
                    "calibrated_confidence": calibrated,
                    "label_match": bool(predicted == actual),
                    "calculated_at_utc": utcnow(),
                })
            fold_rows.append({
                "run_id": self.run_id,
                "outer_fold": fold,
                "testing_start_date": test.index.min().date(),
                "testing_end_date": test.index.max().date(),
                "test_days": len(test),
                "agreement_pct": outer_result["agreement"],
                "mean_raw_confidence": float(
                    np.mean([p.max() for p in outer_result["probabilities"]])
                ),
                "mean_calibrated_confidence": float(np.mean(calibrated_values)),
                "switch_rate": outer_result["switch_rate"],
                "selected_candidate_id": best_candidate["candidate_id"],
                "calculated_at_utc": utcnow(),
            })
            start = end
        return (
            pd.DataFrame(search_rows),
            pd.DataFrame(prediction_rows),
            pd.DataFrame(fold_rows),
        )

    def calibration_summary(self, predictions):
        if predictions.empty:
            return pd.DataFrame()
        frame = predictions.copy()
        frame["correct"] = frame["label_match"].astype(float)
        bins = [0,.2,.4,.5,.6,.7,.8,1.0001]
        labels = ["0-20%","20-40%","40-50%","50-60%","60-70%","70-80%","80-100%"]
        frame["bin"] = pd.cut(
            frame["raw_confidence"], bins=bins, labels=labels, right=False
        )
        rows = []
        for label, group in frame.groupby("bin", observed=True):
            if group.empty:
                continue
            raw = float(group["raw_confidence"].mean())
            cal = float(group["calibrated_confidence"].mean())
            observed = float(group["correct"].mean())
            rows.append({
                "run_id": self.run_id,
                "confidence_bin": str(label),
                "observations": len(group),
                "mean_raw_confidence": raw,
                "mean_calibrated_confidence": cal,
                "observed_accuracy": observed,
                "raw_error": abs(raw-observed),
                "calibrated_error": abs(cal-observed),
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def empirical_sensitivity(self, frame, baseline_predictions):
        scenarios = [
            ("BASELINE", "Original representation and random search", []),
            ("DROP_CORRELATION", "Remove correlation features", [
                "correlation_mean_90d", "correlation_dispersion_90d"
            ]),
            ("DROP_IMPULSES", "Remove liquidity, credit, and dollar impulses", [
                "liquidity_impulse", "credit_impulse", "dollar_impulse"
            ]),
            ("DROP_STATE_PRESSURE", "Remove stress and transition features", [
                "stress_concentration", "transition_pressure"
            ]),
            ("CORE_ONLY", "Use original Module 25-style features only", [
                c for c in frame.columns
                if c not in {
                    "dominant_regime","liquidity_score","trend_score","risk_score",
                    "recovery_score","change_pressure","btc_return_90d",
                    "btc_distance_sma200","btc_volatility_90d",
                    "btc_drawdown_180d","core_breadth","stablecoin_growth_30d",
                    "high_yield_spread","dollar_index","fear_greed"
                }
            ]),
        ]
        baseline = baseline_predictions.set_index("observation_date")
        rows = []
        for index, (key, description, drops) in enumerate(scenarios):
            scenario_frame = frame.drop(
                columns=[c for c in drops if c in frame.columns]
            )
            if key == "BASELINE":
                predictions = baseline_predictions.copy()
            else:
                # Reduced empirical rerun: use same nested structure with a
                # smaller random search to keep validation practical.
                original_count = self.cfg["random_search"]["candidates_per_fold"]
                self.cfg["random_search"]["candidates_per_fold"] = int(
                    self.cfg["sensitivity"]["candidates_per_scenario"]
                )
                try:
                    _, predictions, _ = self.nested_run(scenario_frame)
                finally:
                    self.cfg["random_search"]["candidates_per_fold"] = original_count
            if predictions.empty:
                continue
            agreement = float(predictions["label_match"].mean()*100)
            indexed = predictions.set_index("observation_date")
            common = baseline.index.intersection(indexed.index)
            baseline_match = float(
                (baseline.loc[common,"predicted_regime"]
                 == indexed.loc[common,"predicted_regime"]).mean()*100
            ) if len(common) else 0.0
            calibration_mae = float(
                np.mean(np.abs(
                    predictions["calibrated_confidence"]
                    - predictions["label_match"].astype(float)
                ))
            )
            current = predictions.sort_values("observation_date").iloc[-1]
            rows.append({
                "run_id": self.run_id,
                "scenario_key": key,
                "scenario_description": description,
                "nested_rows": len(predictions),
                "agreement_pct": agreement,
                "agreement_with_baseline_pct": baseline_match,
                "calibration_mae": calibration_mae,
                "current_regime": current["predicted_regime"],
                "current_confidence": float(current["calibrated_confidence"]),
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute("""
            INSERT INTO module27_runs VALUES(
                ?,?,?,NULL,'RUNNING',0,0,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'7.2.0'
            )
        """, [self.run_id, self.source_run_id, self.started])
        try:
            prices = self.prices()
            base = self.base_features()
            labels = self.labels()
            representation = self.build_representation(prices, base)
            frame = self.model_frame(base, representation, labels)

            search, predictions, folds = self.nested_run(frame)
            calibration = self.calibration_summary(predictions)
            sensitivity = self.empirical_sensitivity(frame, predictions)

            for table, data in [
                ("m27_random_search", search),
                ("m27_nested_predictions", predictions),
                ("m27_fold_summary", folds),
                ("m27_calibration_summary", calibration),
                ("m27_empirical_sensitivity", sensitivity),
            ]:
                self.upsert(table, data)

            agreement = float(predictions["label_match"].mean()*100)
            raw_mae = float(calibration["raw_error"].mean()) if not calibration.empty else 1.0
            calibrated_mae = (
                float(calibration["calibrated_error"].mean())
                if not calibration.empty else 1.0
            )
            nonbaseline = sensitivity[
                sensitivity["scenario_key"] != "BASELINE"
            ]
            stability = (
                float(nonbaseline["agreement_with_baseline_pct"].mean())
                if not nonbaseline.empty else 0.0
            )
            current = predictions.sort_values("observation_date").iloc[-1]
            passed = (
                agreement >= float(
                    self.cfg["validation"]["minimum_nested_agreement_pct"]
                )
                and calibrated_mae <= float(
                    self.cfg["validation"]["maximum_calibrated_mae"]
                )
                and stability >= float(
                    self.cfg["validation"]["minimum_empirical_stability_pct"]
                )
            )
            status = "PASSED" if passed else "LIMITED"
            recommendation = (
                "READY_FOR_SPECIALIST_STRATEGY_LAB"
                if passed else "CONTINUE_REPRESENTATION_RESEARCH"
            )
            summary = pd.DataFrame([{
                "run_id": self.run_id,
                "representation_features": len([
                    c for c in representation.columns
                    if c != "feature_completeness_pct"
                ]),
                "random_candidates": int(
                    self.cfg["random_search"]["candidates_per_fold"]
                ),
                "outer_folds": int(predictions["outer_fold"].nunique()),
                "nested_rows": len(predictions),
                "nested_agreement_pct": agreement,
                "raw_calibration_mae": raw_mae,
                "calibrated_mae": calibrated_mae,
                "empirical_stability_pct": stability,
                "current_regime": current["predicted_regime"],
                "current_confidence": float(current["calibrated_confidence"]),
                "validation_status": status,
                "advancement_recommendation": recommendation,
                "calculated_at_utc": utcnow(),
            }])
            self.upsert("m27_research_summary", summary)

            self.conn.execute("""
                UPDATE module27_runs
                SET completed_at_utc=?,status='SUCCESS',
                    representation_features=?,random_candidates=?,
                    outer_folds=?,nested_rows=?,
                    nested_agreement_pct=?,calibrated_mae=?,
                    empirical_stability_pct=?,current_regime=?,
                    current_confidence=?,validation_status=?,notes=?
                WHERE run_id=?
            """, [
                utcnow(),
                int(summary.iloc[0]["representation_features"]),
                int(summary.iloc[0]["random_candidates"]),
                int(summary.iloc[0]["outer_folds"]),
                len(predictions),
                agreement,
                calibrated_mae,
                stability,
                current["predicted_regime"],
                float(current["calibrated_confidence"]),
                status,
                (
                    "v7.2 uses richer cross-asset representation, randomized "
                    "ensemble search, Gaussian state-space emissions, and "
                    "empirical sensitivity reruns. Module 25 remains unchanged."
                ),
                self.run_id,
            ])
            self.conn.close()
            return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module27_runs SET completed_at_utc=?,status='FAILED',notes=? "
                "WHERE run_id=?",
                [utcnow(), str(exc)[:1000], self.run_id],
            )
            self.conn.close()
            raise

def run_module27():
    return Module27Runner().run()
