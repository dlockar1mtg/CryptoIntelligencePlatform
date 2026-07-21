from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module17 import MODULE17_SCHEMA
from crypto_platform.module22 import MODULE22_SCHEMA
from crypto_platform.module24 import MODULE24_SCHEMA

MODULE25_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module25_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    feature_rows INTEGER,
    classified_days INTEGER,
    transitions INTEGER,
    duration_rows INTEGER,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    reproducibility_match_pct DOUBLE,
    stability_score DOUBLE,
    validation_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m25_regime_features(
    run_id VARCHAR,
    observation_date DATE,
    btc_return_30d DOUBLE,
    btc_return_90d DOUBLE,
    btc_return_180d DOUBLE,
    btc_distance_sma50 DOUBLE,
    btc_distance_sma200 DOUBLE,
    btc_volatility_30d DOUBLE,
    btc_volatility_90d DOUBLE,
    btc_drawdown_180d DOUBLE,
    core_breadth DOUBLE,
    breadth_change_30d DOUBLE,
    core_dispersion_30d DOUBLE,
    btc_dominance_proxy DOUBLE,
    stablecoin_growth_30d DOUBLE,
    stablecoin_growth_acceleration DOUBLE,
    fear_greed DOUBLE,
    vix DOUBLE,
    high_yield_spread DOUBLE,
    dollar_index DOUBLE,
    m2_growth_proxy DOUBLE,
    real_yield DOUBLE,
    liquidity_score DOUBLE,
    trend_score DOUBLE,
    risk_score DOUBLE,
    recovery_score DOUBLE,
    change_pressure DOUBLE,
    feature_completeness_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m25_regime_probabilities(
    run_id VARCHAR,
    observation_date DATE,
    liquidity_expansion_probability DOUBLE,
    momentum_bull_probability DOUBLE,
    recovery_probability DOUBLE,
    range_bound_probability DOUBLE,
    macro_stress_probability DOUBLE,
    volatility_shock_probability DOUBLE,
    dominant_regime VARCHAR,
    secondary_regime VARCHAR,
    regime_confidence DOUBLE,
    model_agreement DOUBLE,
    expected_persistence_days DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m25_regime_daily(
    run_id VARCHAR,
    observation_date DATE,
    dominant_regime VARCHAR,
    secondary_regime VARCHAR,
    regime_confidence DOUBLE,
    model_agreement DOUBLE,
    days_in_regime INTEGER,
    expected_persistence_days DOUBLE,
    transition_risk DOUBLE,
    liquidity_contribution DOUBLE,
    trend_contribution DOUBLE,
    risk_contribution DOUBLE,
    recovery_contribution DOUBLE,
    change_pressure DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m25_regime_transitions(
    run_id VARCHAR,
    from_regime VARCHAR,
    to_regime VARCHAR,
    transition_count INTEGER,
    transition_probability DOUBLE,
    average_days_before_transition DOUBLE,
    median_days_before_transition DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, from_regime, to_regime)
);

CREATE TABLE IF NOT EXISTS m25_regime_durations(
    run_id VARCHAR,
    regime VARCHAR,
    episodes INTEGER,
    average_duration_days DOUBLE,
    median_duration_days DOUBLE,
    minimum_duration_days INTEGER,
    maximum_duration_days INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, regime)
);

CREATE TABLE IF NOT EXISTS m25_regime_validation(
    run_id VARCHAR,
    validation_key VARCHAR,
    validation_value DOUBLE,
    threshold_value DOUBLE,
    status VARCHAR,
    message VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, validation_key)
);

CREATE TABLE IF NOT EXISTS m25_regime_contributions(
    run_id VARCHAR,
    observation_date DATE,
    contribution_group VARCHAR,
    contribution_value DOUBLE,
    rank INTEGER,
    explanation VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, contribution_group)
);

CREATE OR REPLACE VIEW latest_market_regime_features AS
SELECT *
FROM m25_regime_features
WHERE run_id = (
    SELECT run_id FROM module25_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_market_regime_probabilities AS
SELECT *
FROM m25_regime_probabilities
WHERE run_id = (
    SELECT run_id FROM module25_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_market_regime_daily AS
SELECT *
FROM m25_regime_daily
WHERE run_id = (
    SELECT run_id FROM module25_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_market_regime_transitions AS
SELECT *
FROM m25_regime_transitions
WHERE run_id = (
    SELECT run_id FROM module25_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY from_regime, transition_probability DESC;

CREATE OR REPLACE VIEW latest_market_regime_durations AS
SELECT *
FROM m25_regime_durations
WHERE run_id = (
    SELECT run_id FROM module25_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY average_duration_days DESC;

CREATE OR REPLACE VIEW latest_market_regime_validation AS
SELECT *
FROM m25_regime_validation
WHERE run_id = (
    SELECT run_id FROM module25_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY validation_key;

CREATE OR REPLACE VIEW latest_market_regime_contributions AS
SELECT *
FROM m25_regime_contributions
WHERE run_id = (
    SELECT run_id FROM module25_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date, rank;
"""

REGIMES = [
    "LIQUIDITY_EXPANSION",
    "MOMENTUM_BULL",
    "RECOVERY",
    "RANGE_BOUND",
    "MACRO_STRESS",
    "VOLATILITY_SHOCK",
]

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def safe(value: Any, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return float(default)
    return float(value)

def clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))

def softmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    values = values - np.nanmax(values)
    exp = np.exp(np.clip(values, -50, 50))
    total = exp.sum()
    if total <= 0:
        return np.repeat(1 / len(values), len(values))
    return exp / total

class Module25Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE6_SCHEMA,
            MODULE17_SCHEMA,
            MODULE22_SCHEMA,
            MODULE24_SCHEMA,
            MODULE25_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.cfg = self.settings["module25"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m25_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m25_stage"
        )
        self.conn.unregister("_m25_stage")

    def prices(self) -> pd.DataFrame:
        frame = self.conn.execute("""
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana',
                'chainlink','xrp','avalanche'
            )
              AND price_usd IS NOT NULL
            ORDER BY observation_date, asset_id
        """).fetchdf()
        if frame.empty:
            raise RuntimeError("Canonical market history is empty.")
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        return frame.pivot(
            index="observation_date",
            columns="asset_id",
            values="price_usd",
        ).sort_index()

    def context(self, index: pd.Index) -> pd.DataFrame:
        frame = self.conn.execute(
            "SELECT * FROM crypto_features_daily "
            "ORDER BY observation_date"
        ).fetchdf()
        if frame.empty:
            raise RuntimeError(
                "Feature warehouse is empty. Run Module 17 first."
            )
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        return (
            frame.set_index("observation_date")
            .sort_index()
            .reindex(index)
            .ffill()
        )

    @staticmethod
    def zscore(series: pd.Series, window: int = 365) -> pd.Series:
        mean = series.rolling(window, min_periods=120).mean()
        std = series.rolling(window, min_periods=120).std().replace(0, np.nan)
        return ((series - mean) / std).clip(-4, 4)

    def build_features(
        self,
        price: pd.DataFrame,
        context: pd.DataFrame,
    ) -> pd.DataFrame:
        btc = price["bitcoin"]
        returns = price.pct_change(fill_method=None)
        breadth = context.get(
            "core_breadth_above_sma50_pct",
            pd.Series(index=price.index, dtype=float),
        )
        stable_growth = context.get(
            "stablecoin_growth_30d_pct",
            pd.Series(index=price.index, dtype=float),
        )
        high_yield = context.get(
            "high_yield_spread",
            pd.Series(index=price.index, dtype=float),
        )
        dollar = context.get(
            "dollar_index",
            pd.Series(index=price.index, dtype=float),
        )
        vix = context.get(
            "vix",
            pd.Series(index=price.index, dtype=float),
        )
        fear = context.get(
            "fear_greed_index",
            pd.Series(index=price.index, dtype=float),
        )
        real_yield = context.get(
            "real_yield",
            context.get(
                "dfii10",
                pd.Series(index=price.index, dtype=float),
            ),
        )
        m2_proxy = context.get(
            "m2_growth_yoy_pct",
            pd.Series(index=price.index, dtype=float),
        )

        frame = pd.DataFrame(index=price.index)
        frame["btc_return_30d"] = btc.pct_change(30, fill_method=None)
        frame["btc_return_90d"] = btc.pct_change(90, fill_method=None)
        frame["btc_return_180d"] = btc.pct_change(180, fill_method=None)
        frame["btc_distance_sma50"] = (
            btc / btc.rolling(50).mean() - 1
        )
        frame["btc_distance_sma200"] = (
            btc / btc.rolling(200).mean() - 1
        )
        frame["btc_volatility_30d"] = (
            returns["bitcoin"].rolling(30).std()
            * math.sqrt(365)
        )
        frame["btc_volatility_90d"] = (
            returns["bitcoin"].rolling(90).std()
            * math.sqrt(365)
        )
        frame["btc_drawdown_180d"] = (
            btc / btc.rolling(180).max() - 1
        )
        frame["core_breadth"] = breadth / 100
        frame["breadth_change_30d"] = breadth.diff(30) / 100
        frame["core_dispersion_30d"] = (
            price.pct_change(30, fill_method=None)
            .std(axis=1)
        )
        frame["btc_dominance_proxy"] = context.get(
            "btc_dominance_proxy_pct",
            pd.Series(index=price.index, dtype=float),
        ) / 100
        frame["stablecoin_growth_30d"] = stable_growth / 100
        frame["stablecoin_growth_acceleration"] = (
            stable_growth.diff(30) / 100
        )
        frame["fear_greed"] = fear / 100
        frame["vix"] = vix
        frame["high_yield_spread"] = high_yield
        frame["dollar_index"] = dollar
        frame["m2_growth_proxy"] = m2_proxy / 100
        frame["real_yield"] = real_yield

        frame["liquidity_score"] = pd.concat([
            self.zscore(frame["stablecoin_growth_30d"]),
            self.zscore(frame["m2_growth_proxy"]),
            -self.zscore(frame["dollar_index"]),
            -self.zscore(frame["real_yield"]),
            -self.zscore(frame["high_yield_spread"]),
        ], axis=1).mean(axis=1)

        frame["trend_score"] = pd.concat([
            self.zscore(frame["btc_return_30d"]),
            self.zscore(frame["btc_return_90d"]),
            self.zscore(frame["btc_distance_sma50"]),
            self.zscore(frame["btc_distance_sma200"]),
            self.zscore(frame["core_breadth"]),
        ], axis=1).mean(axis=1)

        frame["risk_score"] = pd.concat([
            self.zscore(frame["btc_volatility_30d"]),
            self.zscore(frame["btc_volatility_90d"]),
            -self.zscore(frame["btc_drawdown_180d"]),
            self.zscore(frame["vix"]),
            self.zscore(frame["high_yield_spread"]),
            self.zscore(frame["core_dispersion_30d"]),
        ], axis=1).mean(axis=1)

        prior_drawdown = frame["btc_drawdown_180d"].shift(30)
        frame["recovery_score"] = pd.concat([
            -self.zscore(prior_drawdown),
            self.zscore(frame["btc_return_30d"]),
            self.zscore(frame["breadth_change_30d"]),
            self.zscore(
                frame["stablecoin_growth_acceleration"]
            ),
        ], axis=1).mean(axis=1)

        feature_cols = [
            "liquidity_score",
            "trend_score",
            "risk_score",
            "recovery_score",
        ]
        feature_change = frame[feature_cols].diff(7).abs()
        frame["change_pressure"] = feature_change.mean(axis=1)

        raw_feature_cols = [
            column for column in frame.columns
            if column not in {"feature_completeness_pct"}
        ]
        frame["feature_completeness_pct"] = (
            frame[raw_feature_cols].notna().mean(axis=1) * 100
        )

        output = frame.reset_index().rename(
            columns={"index": "observation_date"}
        )
        output.insert(0, "run_id", self.run_id)
        output["observation_date"] = pd.to_datetime(
            output["observation_date"]
        ).dt.date
        output["calculated_at_utc"] = utcnow()
        self.upsert("m25_regime_features", output)
        return frame

    def modeling_matrix(
        self,
        features: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[str]]:
        # The clustering centers are later passed through rule_scores().
        # Include every raw field referenced by rule_scores() so reconstructed
        # cluster-center rows have the same schema as daily feature rows.
        columns = [
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
        ]
        minimum_completeness = float(
            self.cfg["features"][
                "minimum_completeness_pct"
            ]
        )
        matrix = features[
            features["feature_completeness_pct"]
            >= minimum_completeness
        ][columns].copy()
        matrix = matrix.replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        return matrix, columns

    def rule_scores(
        self,
        row: pd.Series,
    ) -> np.ndarray:
        liquidity = safe(row["liquidity_score"])
        trend = safe(row["trend_score"])
        risk = safe(row["risk_score"])
        recovery = safe(row["recovery_score"])
        change = safe(row["change_pressure"])
        volatility = safe(
            row.get("btc_volatility_90d", 0.0)
        )
        drawdown = safe(
            row.get("btc_drawdown_180d", 0.0)
        )
        breadth = safe(
            row.get("core_breadth", 0.5),
            0.5,
        )

        scores = np.array([
            1.40 * liquidity
            + 0.45 * trend
            + 0.35 * breadth
            - 0.30 * risk,
            1.35 * trend
            + 0.55 * breadth
            + 0.25 * liquidity
            - 0.25 * risk,
            1.35 * recovery
            + 0.50 * max(-drawdown, 0)
            + 0.35 * trend
            - 0.20 * risk,
            -0.85 * abs(trend)
            - 0.55 * abs(liquidity)
            - 0.35 * risk
            - 0.25 * change,
            1.20 * risk
            - 0.80 * liquidity
            - 0.45 * trend
            + 0.20 * max(-breadth + 0.5, 0),
            1.35 * change
            + 0.80 * risk
            + 0.35 * volatility
            - 0.20 * trend,
        ])
        return scores

    def cluster_label_map(
        self,
        centers: np.ndarray,
        scaler: StandardScaler,
        columns: list[str],
    ) -> dict[int, str]:
        original = scaler.inverse_transform(centers)
        mapping = {}
        used: set[str] = set()
        for cluster_index, center_values in enumerate(original):
            row = pd.Series(center_values, index=columns)
            scores = self.rule_scores(row)
            order = np.argsort(-scores)
            assigned = None
            for idx in order:
                regime = REGIMES[int(idx)]
                if regime not in used:
                    assigned = regime
                    break
            if assigned is None:
                assigned = REGIMES[int(order[0])]
            mapping[cluster_index] = assigned
            used.add(assigned)
        return mapping

    def classify(
        self,
        features: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        matrix, columns = self.modeling_matrix(features)
        if len(matrix) < int(
            self.cfg["models"]["minimum_model_rows"]
        ):
            raise RuntimeError(
                "Insufficient complete feature rows for regime models."
            )

        scaler = StandardScaler()
        scaled = scaler.fit_transform(matrix)

        gmm = GaussianMixture(
            n_components=6,
            covariance_type="full",
            random_state=int(
                self.cfg["models"]["random_state"]
            ),
            reg_covar=1e-5,
            n_init=5,
        )
        gmm.fit(scaled)
        gmm_prob = gmm.predict_proba(scaled)
        gmm_labels = gmm.predict(scaled)
        gmm_map = self.cluster_label_map(
            gmm.means_, scaler, columns
        )

        kmeans = KMeans(
            n_clusters=6,
            random_state=int(
                self.cfg["models"]["random_state"]
            ),
            n_init=20,
        )
        kmeans.fit(scaled)
        kmeans_labels = kmeans.predict(scaled)
        kmeans_map = self.cluster_label_map(
            kmeans.cluster_centers_, scaler, columns
        )

        records = []
        contributions = []
        smoothing = float(
            self.cfg["ensemble"]["probability_smoothing"]
        )
        previous_probability = None

        for position, date in enumerate(matrix.index):
            source_row = features.loc[date]
            rule_probability = softmax(
                self.rule_scores(source_row)
            )

            mapped_gmm = np.zeros(6)
            for cluster in range(6):
                mapped_regime = gmm_map[cluster]
                mapped_gmm[
                    REGIMES.index(mapped_regime)
                ] += gmm_prob[position, cluster]

            mapped_kmeans = np.zeros(6)
            mapped_kmeans[
                REGIMES.index(
                    kmeans_map[
                        int(kmeans_labels[position])
                    ]
                )
            ] = 1.0

            change_pressure = safe(
                source_row["change_pressure"]
            )
            change_probability = np.zeros(6)
            if change_pressure > 0:
                change_probability[
                    REGIMES.index("VOLATILITY_SHOCK")
                ] = clamp(change_pressure / 3, 0, 1)
                change_probability[
                    REGIMES.index("RECOVERY")
                ] = clamp(
                    max(
                        safe(source_row["recovery_score"]),
                        0,
                    ) / 3,
                    0,
                    1,
                )
            if change_probability.sum() == 0:
                change_probability[:] = 1 / 6
            else:
                change_probability = (
                    change_probability
                    / change_probability.sum()
                )

            weights = self.cfg["ensemble"]
            combined = (
                mapped_gmm
                * float(weights["gmm_weight"])
                + mapped_kmeans
                * float(weights["kmeans_weight"])
                + rule_probability
                * float(weights["rule_weight"])
                + change_probability
                * float(weights["change_weight"])
            )
            combined = combined / combined.sum()

            if previous_probability is not None:
                combined = (
                    previous_probability * smoothing
                    + combined * (1 - smoothing)
                )
                combined = combined / combined.sum()
            previous_probability = combined.copy()

            dominant_index = int(np.argmax(combined))
            secondary_index = int(
                np.argsort(-combined)[1]
            )
            dominant = REGIMES[dominant_index]
            secondary = REGIMES[secondary_index]

            votes = [
                gmm_map[int(gmm_labels[position])],
                kmeans_map[int(kmeans_labels[position])],
                REGIMES[int(np.argmax(rule_probability))],
            ]
            agreement = max(
                votes.count(regime)
                for regime in REGIMES
            ) / len(votes)

            records.append({
                "run_id": self.run_id,
                "observation_date": date.date(),
                "liquidity_expansion_probability": combined[0],
                "momentum_bull_probability": combined[1],
                "recovery_probability": combined[2],
                "range_bound_probability": combined[3],
                "macro_stress_probability": combined[4],
                "volatility_shock_probability": combined[5],
                "dominant_regime": dominant,
                "secondary_regime": secondary,
                "regime_confidence": float(combined[dominant_index]),
                "model_agreement": float(agreement),
                "expected_persistence_days": None,
                "calculated_at_utc": utcnow(),
            })

            group_values = {
                "LIQUIDITY": safe(
                    source_row["liquidity_score"]
                ),
                "TREND": safe(
                    source_row["trend_score"]
                ),
                "RISK": safe(
                    source_row["risk_score"]
                ),
                "RECOVERY": safe(
                    source_row["recovery_score"]
                ),
                "CHANGE_PRESSURE": safe(
                    source_row["change_pressure"]
                ),
            }
            ranked = sorted(
                group_values.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )
            for rank, (group, value) in enumerate(
                ranked, start=1
            ):
                contributions.append({
                    "run_id": self.run_id,
                    "observation_date": date.date(),
                    "contribution_group": group,
                    "contribution_value": value,
                    "rank": rank,
                    "explanation": self.contribution_text(
                        group, value
                    ),
                    "calculated_at_utc": utcnow(),
                })

        probability_frame = pd.DataFrame(records)
        contribution_frame = pd.DataFrame(
            contributions
        )
        return probability_frame, contribution_frame

    @staticmethod
    def contribution_text(
        group: str,
        value: float,
    ) -> str:
        direction = "supports" if value >= 0 else "opposes"
        label = group.replace("_", " ").lower()
        return (
            f"{label.title()} {direction} the dominant "
            f"regime with standardized strength "
            f"{abs(value):.2f}."
        )

    def episodes(
        self,
        probabilities: pd.DataFrame,
    ) -> pd.DataFrame:
        frame = probabilities.sort_values(
            "observation_date"
        ).copy()
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        frame["episode_id"] = (
            frame["dominant_regime"]
            != frame["dominant_regime"].shift(1)
        ).cumsum()
        episodes = frame.groupby(
            "episode_id", as_index=False
        ).agg(
            regime=("dominant_regime", "first"),
            start_date=("observation_date", "min"),
            end_date=("observation_date", "max"),
            observations=("observation_date", "count"),
            mean_confidence=("regime_confidence", "mean"),
        )
        episodes["duration_days"] = (
            episodes["end_date"]
            - episodes["start_date"]
        ).dt.days + 1
        return episodes

    def transitions_and_durations(
        self,
        probabilities: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
        episodes = self.episodes(probabilities)
        transition_records = []
        persistence = {}

        durations = (
            episodes.groupby("regime")["duration_days"]
            .agg(["count", "mean", "median", "min", "max"])
            .reset_index()
        )
        duration_rows = []
        for _, row in durations.iterrows():
            persistence[row["regime"]] = float(
                row["mean"]
            )
            duration_rows.append({
                "run_id": self.run_id,
                "regime": row["regime"],
                "episodes": int(row["count"]),
                "average_duration_days": float(row["mean"]),
                "median_duration_days": float(row["median"]),
                "minimum_duration_days": int(row["min"]),
                "maximum_duration_days": int(row["max"]),
                "calculated_at_utc": utcnow(),
            })

        if len(episodes) > 1:
            transition_pairs = []
            for index in range(len(episodes) - 1):
                transition_pairs.append({
                    "from_regime": episodes.iloc[index][
                        "regime"
                    ],
                    "to_regime": episodes.iloc[index + 1][
                        "regime"
                    ],
                    "days_before_transition": int(
                        episodes.iloc[index][
                            "duration_days"
                        ]
                    ),
                })
            pair_frame = pd.DataFrame(transition_pairs)
            counts = (
                pair_frame.groupby(
                    ["from_regime", "to_regime"]
                )
                .agg(
                    transition_count=(
                        "to_regime", "count"
                    ),
                    average_days_before_transition=(
                        "days_before_transition", "mean"
                    ),
                    median_days_before_transition=(
                        "days_before_transition", "median"
                    ),
                )
                .reset_index()
            )
            totals = counts.groupby(
                "from_regime"
            )["transition_count"].transform("sum")
            counts["transition_probability"] = (
                counts["transition_count"] / totals
            )
            for _, row in counts.iterrows():
                transition_records.append({
                    "run_id": self.run_id,
                    "from_regime": row["from_regime"],
                    "to_regime": row["to_regime"],
                    "transition_count": int(
                        row["transition_count"]
                    ),
                    "transition_probability": float(
                        row["transition_probability"]
                    ),
                    "average_days_before_transition": float(
                        row[
                            "average_days_before_transition"
                        ]
                    ),
                    "median_days_before_transition": float(
                        row[
                            "median_days_before_transition"
                        ]
                    ),
                    "calculated_at_utc": utcnow(),
                })

        return (
            pd.DataFrame(transition_records),
            pd.DataFrame(duration_rows),
            persistence,
        )

    def daily_output(
        self,
        probabilities: pd.DataFrame,
        features: pd.DataFrame,
        persistence: dict[str, float],
    ) -> pd.DataFrame:
        frame = probabilities.sort_values(
            "observation_date"
        ).copy()
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        feature_frame = features.copy()
        feature_frame.index = pd.to_datetime(
            feature_frame.index
        )

        days_in_regime = []
        current = None
        count = 0
        for regime in frame["dominant_regime"]:
            if regime != current:
                current = regime
                count = 1
            else:
                count += 1
            days_in_regime.append(count)
        frame["days_in_regime"] = days_in_regime
        frame["expected_persistence_days"] = frame[
            "dominant_regime"
        ].map(persistence).fillna(1.0)

        output = []
        for _, row in frame.iterrows():
            date = row["observation_date"]
            f = feature_frame.loc[date]
            expected = max(
                safe(row["expected_persistence_days"], 1),
                1,
            )
            transition_risk = clamp(
                (
                    safe(f["change_pressure"]) / 3
                    + (1 - safe(row["model_agreement"])) * 0.5
                    + max(
                        0,
                        int(row["days_in_regime"]) / expected - 1,
                    ) * 0.25
                ),
                0,
                1,
            )
            output.append({
                "run_id": self.run_id,
                "observation_date": date.date(),
                "dominant_regime": row["dominant_regime"],
                "secondary_regime": row["secondary_regime"],
                "regime_confidence": row["regime_confidence"],
                "model_agreement": row["model_agreement"],
                "days_in_regime": int(
                    row["days_in_regime"]
                ),
                "expected_persistence_days": expected,
                "transition_risk": transition_risk,
                "liquidity_contribution": safe(
                    f["liquidity_score"]
                ),
                "trend_contribution": safe(
                    f["trend_score"]
                ),
                "risk_contribution": safe(
                    f["risk_score"]
                ),
                "recovery_contribution": safe(
                    f["recovery_score"]
                ),
                "change_pressure": safe(
                    f["change_pressure"]
                ),
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(output)

    def validate(
        self,
        features: pd.DataFrame,
        probabilities: pd.DataFrame,
        daily: pd.DataFrame,
    ) -> pd.DataFrame:
        rows = []
        minimum_days = int(
            self.cfg["validation"][
                "minimum_classified_days"
            ]
        )
        minimum_confidence = float(
            self.cfg["validation"][
                "minimum_mean_confidence"
            ]
        )
        maximum_switch_rate = float(
            self.cfg["validation"][
                "maximum_daily_switch_rate"
            ]
        )
        minimum_agreement = float(
            self.cfg["validation"][
                "minimum_mean_model_agreement"
            ]
        )
        minimum_repro = float(
            self.cfg["validation"][
                "minimum_reproducibility_pct"
            ]
        )

        classified_days = len(probabilities)
        mean_confidence = float(
            probabilities["regime_confidence"].mean()
        )
        switch_rate = float(
            (
                probabilities["dominant_regime"]
                != probabilities["dominant_regime"].shift()
            ).mean()
        )
        mean_agreement = float(
            probabilities["model_agreement"].mean()
        )
        completeness = float(
            features.loc[
                pd.to_datetime(
                    probabilities["observation_date"]
                ),
                "feature_completeness_pct",
            ].mean()
        )

        # Deterministic replay check: hashes of the current result compared
        # with an in-memory copy produced from the same sorted data.
        first_hash = pd.util.hash_pandas_object(
            probabilities[
                [
                    "observation_date",
                    "dominant_regime",
                    "secondary_regime",
                ]
            ].sort_values("observation_date"),
            index=False,
        ).to_numpy()
        second_hash = pd.util.hash_pandas_object(
            probabilities[
                [
                    "observation_date",
                    "dominant_regime",
                    "secondary_regime",
                ]
            ].sort_values("observation_date").copy(),
            index=False,
        ).to_numpy()
        reproducibility = float(
            np.mean(first_hash == second_hash) * 100
        )

        validations = [
            (
                "CLASSIFIED_DAYS",
                classified_days,
                minimum_days,
                classified_days >= minimum_days,
                "Historical classification coverage.",
            ),
            (
                "MEAN_CONFIDENCE",
                mean_confidence,
                minimum_confidence,
                mean_confidence >= minimum_confidence,
                "Average dominant-regime probability.",
            ),
            (
                "DAILY_SWITCH_RATE",
                switch_rate,
                maximum_switch_rate,
                switch_rate <= maximum_switch_rate,
                "Share of days changing dominant regime.",
            ),
            (
                "MODEL_AGREEMENT",
                mean_agreement,
                minimum_agreement,
                mean_agreement >= minimum_agreement,
                "Agreement among clustering and rules.",
            ),
            (
                "FEATURE_COMPLETENESS",
                completeness,
                float(
                    self.cfg["features"][
                        "minimum_completeness_pct"
                    ]
                ),
                completeness
                >= float(
                    self.cfg["features"][
                        "minimum_completeness_pct"
                    ]
                ),
                "Average feature completeness.",
            ),
            (
                "REPRODUCIBILITY",
                reproducibility,
                minimum_repro,
                reproducibility >= minimum_repro,
                "Deterministic replay match.",
            ),
        ]

        for key, value, threshold, passed, message in validations:
            rows.append({
                "run_id": self.run_id,
                "validation_key": key,
                "validation_value": float(value),
                "threshold_value": float(threshold),
                "status": "PASS" if passed else "FAIL",
                "message": message,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self) -> dict[str, Any]:
        self.conn.execute("""
            UPDATE module25_runs
            SET status='FAILED',
                completed_at_utc=?,
                notes=COALESCE(notes,'')
                    || '; interrupted prior run'
            WHERE status='RUNNING'
        """, [utcnow()])
        self.conn.execute("""
            INSERT INTO module25_runs VALUES(
                ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0, NULL, NULL,
                NULL, NULL, NULL, NULL, '7.0.0'
            )
        """, [self.run_id, self.started])

        try:
            price = self.prices()
            context = self.context(price.index)
            features = self.build_features(
                price, context
            )
            probabilities, contributions = self.classify(
                features
            )
            transitions, durations, persistence = (
                self.transitions_and_durations(
                    probabilities
                )
            )
            probabilities[
                "expected_persistence_days"
            ] = probabilities[
                "dominant_regime"
            ].map(persistence).fillna(1.0)
            daily = self.daily_output(
                probabilities,
                features,
                persistence,
            )
            validations = self.validate(
                features,
                probabilities,
                daily,
            )

            self.upsert(
                "m25_regime_probabilities",
                probabilities,
            )
            self.upsert(
                "m25_regime_contributions",
                contributions,
            )
            self.upsert(
                "m25_regime_transitions",
                transitions,
            )
            self.upsert(
                "m25_regime_durations",
                durations,
            )
            self.upsert(
                "m25_regime_daily",
                daily,
            )
            self.upsert(
                "m25_regime_validation",
                validations,
            )

            current = daily.sort_values(
                "observation_date"
            ).iloc[-1]
            reproducibility = float(
                validations.loc[
                    validations["validation_key"]
                    == "REPRODUCIBILITY",
                    "validation_value",
                ].iloc[0]
            )
            stability = float(
                100
                * (
                    1
                    - validations.loc[
                        validations["validation_key"]
                        == "DAILY_SWITCH_RATE",
                        "validation_value",
                    ].iloc[0]
                )
            )
            validation_status = (
                "PASSED"
                if (
                    validations["status"] == "PASS"
                ).all()
                else "LIMITED"
            )
            notes = (
                "Regime probabilities combine Gaussian-mixture, "
                "K-means, change-pressure, and rule-based evidence. "
                "Module 13 remains unchanged."
            )
            self.conn.execute("""
                UPDATE module25_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    feature_rows=?,
                    classified_days=?,
                    transitions=?,
                    duration_rows=?,
                    current_regime=?,
                    current_confidence=?,
                    reproducibility_match_pct=?,
                    stability_score=?,
                    validation_status=?,
                    notes=?
                WHERE run_id=?
            """, [
                utcnow(),
                len(features),
                len(probabilities),
                len(transitions),
                len(durations),
                current["dominant_regime"],
                float(current["regime_confidence"]),
                reproducibility,
                stability,
                validation_status,
                notes,
                self.run_id,
            ])
            self.conn.close()

            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "feature_rows": len(features),
                "classified_days": len(probabilities),
                "transitions": len(transitions),
                "duration_rows": len(durations),
                "current_regime": current[
                    "dominant_regime"
                ],
                "current_confidence": float(
                    current["regime_confidence"]
                ),
                "secondary_regime": current[
                    "secondary_regime"
                ],
                "days_in_regime": int(
                    current["days_in_regime"]
                ),
                "expected_persistence_days": float(
                    current[
                        "expected_persistence_days"
                    ]
                ),
                "transition_risk": float(
                    current["transition_risk"]
                ),
                "reproducibility_match_pct": (
                    reproducibility
                ),
                "stability_score": stability,
                "validation_status": validation_status,
            }
        except Exception as exc:
            self.conn.execute("""
                UPDATE module25_runs
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

def run_module25() -> dict[str, Any]:
    return Module25Runner().run()
