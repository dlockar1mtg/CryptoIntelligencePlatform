from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import BayesianRidge
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.module37 import MODULE37_SCHEMA

MODULE38_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module38_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module37_run_id VARCHAR,
    source_module30_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    forecast_rows INTEGER,
    model_rows INTEGER,
    transition_rows INTEGER,
    attribution_rows INTEGER,
    portfolio_rows INTEGER,
    horizons_completed INTEGER,
    assets_completed INTEGER,
    mean_validation_mae_pct DOUBLE,
    mean_forecast_confidence DOUBLE,
    predictive_regime VARCHAR,
    predictive_regime_confidence DOUBLE,
    portfolio_expected_return_pct DOUBLE,
    forecast_risk_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m38_asset_forecasts(
    run_id VARCHAR,
    forecast_date DATE,
    asset_id VARCHAR,
    horizon_days INTEGER,
    current_price DOUBLE,
    predicted_return_pct DOUBLE,
    predicted_price DOUBLE,
    lower_return_pct DOUBLE,
    upper_return_pct DOUBLE,
    lower_price DOUBLE,
    upper_price DOUBLE,
    probability_positive DOUBLE,
    forecast_confidence DOUBLE,
    model_agreement DOUBLE,
    regime_adjustment_pct DOUBLE,
    macro_adjustment_pct DOUBLE,
    forecast_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, forecast_date, asset_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m38_model_validation(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    model_key VARCHAR,
    validation_rows INTEGER,
    validation_mae_pct DOUBLE,
    validation_rmse_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    ensemble_weight DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_days, model_key)
);

CREATE TABLE IF NOT EXISTS m38_regime_transitions(
    run_id VARCHAR,
    forecast_date DATE,
    current_regime VARCHAR,
    next_regime VARCHAR,
    transition_probability DOUBLE,
    expected_duration_days DOUBLE,
    transition_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, forecast_date, current_regime, next_regime)
);

CREATE TABLE IF NOT EXISTS m38_forecast_attribution(
    run_id VARCHAR,
    forecast_date DATE,
    asset_id VARCHAR,
    horizon_days INTEGER,
    driver_key VARCHAR,
    driver_category VARCHAR,
    contribution_pct DOUBLE,
    contribution_direction VARCHAR,
    importance_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id,
        forecast_date,
        asset_id,
        horizon_days,
        driver_key
    )
);

CREATE TABLE IF NOT EXISTS m38_portfolio_forecast(
    run_id VARCHAR PRIMARY KEY,
    forecast_date DATE,
    horizon_days INTEGER,
    expected_portfolio_return_pct DOUBLE,
    lower_portfolio_return_pct DOUBLE,
    upper_portfolio_return_pct DOUBLE,
    probability_positive DOUBLE,
    expected_portfolio_volatility_pct DOUBLE,
    forecast_confidence DOUBLE,
    dominant_predictive_regime VARCHAR,
    predictive_regime_confidence DOUBLE,
    cash_weight DOUBLE,
    risk_asset_weight DOUBLE,
    forecast_risk_status VARCHAR,
    recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS m38_predictive_expected_returns(
    run_id VARCHAR,
    forecast_date DATE,
    asset_id VARCHAR,
    horizon_days INTEGER,
    module37_expected_return_pct DOUBLE,
    predictive_return_pct DOUBLE,
    blended_optimizer_return_pct DOUBLE,
    predictive_weight DOUBLE,
    optimizer_weight DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, forecast_date, asset_id, horizon_days)
);

CREATE OR REPLACE VIEW latest_m38_asset_forecasts AS
SELECT * FROM m38_asset_forecasts
WHERE run_id=(
    SELECT run_id FROM module38_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY horizon_days, predicted_return_pct DESC;

CREATE OR REPLACE VIEW latest_m38_model_validation AS
SELECT * FROM m38_model_validation
WHERE run_id=(
    SELECT run_id FROM module38_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY asset_id, horizon_days, ensemble_weight DESC;

CREATE OR REPLACE VIEW latest_m38_regime_transitions AS
SELECT * FROM m38_regime_transitions
WHERE run_id=(
    SELECT run_id FROM module38_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY transition_rank;

CREATE OR REPLACE VIEW latest_m38_forecast_attribution AS
SELECT * FROM m38_forecast_attribution
WHERE run_id=(
    SELECT run_id FROM module38_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY asset_id, horizon_days, importance_rank;

CREATE OR REPLACE VIEW latest_m38_portfolio_forecast AS
SELECT * FROM m38_portfolio_forecast
WHERE run_id=(
    SELECT run_id FROM module38_runs
    ORDER BY started_at_utc DESC LIMIT 1
);

CREATE OR REPLACE VIEW latest_m38_predictive_expected_returns AS
SELECT * FROM m38_predictive_expected_returns
WHERE run_id=(
    SELECT run_id FROM module38_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY horizon_days, blended_optimizer_return_pct DESC;
"""

ASSETS = [
    "bitcoin",
    "ethereum",
    "solana",
    "chainlink",
    "xrp",
    "avalanche",
]

REGIMES = [
    "LIQUIDITY_EXPANSION",
    "MACRO_STRESS",
    "MOMENTUM_BULL",
    "RANGE_BOUND",
    "RECOVERY",
    "VOLATILITY_SHOCK",
]


def utcnow():
    return datetime.now(timezone.utc)


def safe_float(value, default=0.0):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


class InsufficientForecastHistory(RuntimeError):
    """Raised when one asset/horizon cannot support a safe forecast."""

    def __init__(
        self,
        asset_id,
        horizon_days,
        usable_rows,
        required_rows,
    ):
        self.asset_id = asset_id
        self.horizon_days = int(horizon_days)
        self.usable_rows = int(usable_rows)
        self.required_rows = int(required_rows)
        super().__init__(
            f"{asset_id} horizon {horizon_days} has "
            f"{usable_rows} usable rows; requires at least "
            f"{required_rows}."
        )


class Module38Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE25_SCHEMA)
        self.conn.execute(MODULE30_SCHEMA)
        self.conn.execute(MODULE37_SCHEMA)
        self.conn.execute(MODULE38_SCHEMA)
        self.cfg = self.settings["module38"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

        row37 = self.conn.execute(
            """
            SELECT run_id
            FROM module37_runs
            WHERE status='SUCCESS'
              AND validation_status='PASSED'
            ORDER BY started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        row30 = self.conn.execute(
            """
            SELECT run_id
            FROM module30_runs
            WHERE status='SUCCESS'
            ORDER BY started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        if row37 is None or row30 is None:
            raise RuntimeError(
                "Successful Modules 30 and 37 are required."
            )
        self.source_m37 = str(row37[0])
        self.source_m30 = str(row30[0])

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m38_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m38_stage"
        )
        self.conn.unregister("_m38_stage")

    def prices(self):
        frame = self.conn.execute(
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
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        return frame

    def macro(self):
        tables = self.conn.execute(
            """
            SELECT lower(table_name)
            FROM information_schema.tables
            """
        ).fetchall()
        names = {row[0] for row in tables}
        candidates = [
            "macro_daily",
            "macro_observations",
            "macro_data",
        ]
        table = next(
            (name for name in candidates if name in names),
            None,
        )
        if table is None:
            return pd.DataFrame()
        try:
            frame = self.conn.execute(
                f"SELECT * FROM {table}"
            ).fetchdf()
            return frame
        except Exception:
            return pd.DataFrame()

    def regime_history(self):
        frame = self.conn.execute(
            """
            SELECT observation_date, clean_regime
            FROM clean_regime_history
            WHERE run_id=?
            ORDER BY observation_date
            """,
            [self.source_m30],
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        return frame

    def current_regime(self):
        row = self.conn.execute(
            """
            SELECT clean_regime, clean_probability
            FROM clean_regime_current
            WHERE run_id=?
            LIMIT 1
            """,
            [self.source_m30],
        ).fetchone()
        if row is None:
            return "RANGE_BOUND", 0.5
        return str(row[0]), safe_float(row[1], 0.5)

    def optimizer_expected_returns(self):
        frame = self.conn.execute(
            """
            SELECT asset_id, blended_expected_return_pct
            FROM m37_expected_returns
            WHERE run_id=?
            """,
            [self.source_m37],
        ).fetchdf()
        return dict(zip(
            frame["asset_id"],
            frame["blended_expected_return_pct"],
        ))

    def optimizer_allocations(self):
        frame = self.conn.execute(
            """
            SELECT asset_id, risk_adjusted_weight
            FROM m37_optimized_allocations
            WHERE run_id=?
            """,
            [self.source_m37],
        ).fetchdf()
        return dict(zip(
            frame["asset_id"],
            frame["risk_adjusted_weight"],
        ))

    def build_features(self, asset_frame, horizon):
        asset_frame = asset_frame.sort_values(
            "observation_date"
        ).copy()
        price = asset_frame["price_usd"].astype(float)
        returns = price.pct_change(fill_method=None)

        features = pd.DataFrame({
            "observation_date": asset_frame[
                "observation_date"
            ],
            "return_1d": returns,
            "return_7d": price.pct_change(
                7,
                fill_method=None,
            ),
            "return_30d": price.pct_change(
                30,
                fill_method=None,
            ),
            "return_90d": price.pct_change(
                90,
                fill_method=None,
            ),
            "volatility_30d": (
                returns.rolling(30).std()
                * math.sqrt(365)
            ),
            "volatility_90d": (
                returns.rolling(90).std()
                * math.sqrt(365)
            ),
            "distance_sma50": (
                price / price.rolling(50).mean() - 1
            ),
            "distance_sma200": (
                price / price.rolling(200).mean() - 1
            ),
            "volume_change_30d": (
                asset_frame["volume_24h_usd"]
                .astype(float)
                .pct_change(30, fill_method=None)
                if "volume_24h_usd" in asset_frame
                else 0.0
            ),
            "market_cap_change_30d": (
                asset_frame["market_cap_usd"]
                .astype(float)
                .pct_change(30, fill_method=None)
                if "market_cap_usd" in asset_frame
                else 0.0
            ),
        })
        features["target_return"] = (
            price.shift(-horizon) / price - 1
        )
        return features.replace(
            [np.inf, -np.inf],
            np.nan,
        ).dropna()

    def model_suite(self, random_state):
        return {
            "GRADIENT_BOOSTING": (
                GradientBoostingRegressor(
                    n_estimators=180,
                    learning_rate=0.04,
                    max_depth=2,
                    min_samples_leaf=15,
                    random_state=random_state,
                    loss="huber",
                )
            ),
            "RANDOM_FOREST": (
                RandomForestRegressor(
                    n_estimators=220,
                    max_depth=6,
                    min_samples_leaf=10,
                    max_features=0.8,
                    random_state=random_state,
                    n_jobs=-1,
                )
            ),
            "BAYESIAN_RIDGE": BayesianRidge(),
        }

    def train_forecast(
        self,
        asset_id,
        horizon,
        features,
        current_features,
        current_price,
    ):
        columns = [
            column
            for column in features.columns
            if column not in {
                "observation_date",
                "target_return",
            }
        ]
        configured_minimum = int(
            self.cfg["minimum_training_rows"]
        )
        configured_validation = int(
            self.cfg["validation_rows"]
        )
        absolute_minimum = int(
            self.cfg.get(
                "absolute_minimum_training_rows",
                90,
            )
        )
        minimum_validation = int(
            self.cfg.get(
                "minimum_validation_rows",
                30,
            )
        )
        maximum_validation_share = float(
            self.cfg.get(
                "maximum_validation_share",
                0.25,
            )
        )

        usable_rows = len(features)
        adaptive_validation = min(
            configured_validation,
            max(
                minimum_validation,
                int(
                    usable_rows
                    * maximum_validation_share
                ),
            ),
        )
        adaptive_validation = min(
            adaptive_validation,
            usable_rows - absolute_minimum,
        )
        adaptive_training = (
            usable_rows - adaptive_validation
        )

        if (
            adaptive_training < absolute_minimum
            or adaptive_validation < minimum_validation
        ):
            raise InsufficientForecastHistory(
                asset_id=asset_id,
                horizon_days=horizon,
                usable_rows=usable_rows,
                required_rows=(
                    absolute_minimum
                    + minimum_validation
                ),
            )

        # The configured minimum is a preferred target rather than a
        # hard failure threshold. Shorter histories use the largest
        # leakage-safe training window available.
        minimum_train = min(
            configured_minimum,
            adaptive_training,
        )
        validation_rows = adaptive_validation

        train = features.iloc[
            :usable_rows - validation_rows
        ]
        validation = features.iloc[
            usable_rows - validation_rows:
        ]
        scaler = StandardScaler()
        x_train = scaler.fit_transform(
            train[columns]
        )
        x_validation = scaler.transform(
            validation[columns]
        )
        x_current = scaler.transform(
            current_features[columns]
        )
        y_train = train["target_return"].to_numpy()
        y_validation = validation[
            "target_return"
        ].to_numpy()

        model_rows = []
        predictions = []
        residual_samples = []
        raw_weights = []

        for index, (
            model_key,
            model,
        ) in enumerate(
            self.model_suite(
                int(self.cfg["random_state"])
                + horizon
            ).items(),
            start=1,
        ):
            model.fit(x_train, y_train)
            validation_prediction = model.predict(
                x_validation
            )
            current_prediction = float(
                model.predict(x_current)[0]
            )
            mae = float(
                mean_absolute_error(
                    y_validation,
                    validation_prediction,
                )
            )
            rmse = float(
                np.sqrt(
                    np.mean(
                        (
                            y_validation
                            - validation_prediction
                        ) ** 2
                    )
                )
            )
            directional = float(
                np.mean(
                    np.sign(y_validation)
                    == np.sign(
                        validation_prediction
                    )
                )
                * 100
            )
            weight = 1 / max(mae, 1e-6)
            raw_weights.append(weight)
            predictions.append(current_prediction)
            residual_samples.extend(
                (
                    y_validation
                    - validation_prediction
                ).tolist()
            )
            model_rows.append({
                "run_id": self.run_id,
                "asset_id": asset_id,
                "horizon_days": horizon,
                "model_key": model_key,
                "validation_rows": len(validation),
                "validation_mae_pct": mae * 100,
                "validation_rmse_pct": rmse * 100,
                "directional_accuracy_pct": directional,
                "ensemble_weight": 0.0,
                "selected": False,
                "calculated_at_utc": utcnow(),
            })

        weights = np.asarray(raw_weights)
        weights /= weights.sum()
        ensemble_prediction = float(
            np.dot(
                weights,
                np.asarray(predictions),
            )
        )
        for row, weight in zip(model_rows, weights):
            row["ensemble_weight"] = float(weight)
            row["selected"] = bool(
                weight == weights.max()
            )

        residual_array = np.asarray(
            residual_samples,
            dtype=float,
        )
        lower = float(
            ensemble_prediction
            + np.quantile(
                residual_array,
                0.10,
            )
        )
        upper = float(
            ensemble_prediction
            + np.quantile(
                residual_array,
                0.90,
            )
        )
        probability_positive = float(
            np.mean(
                ensemble_prediction
                + residual_array
                > 0
            )
        )
        agreement = float(
            1
            - np.std(predictions)
            / max(
                np.mean(
                    np.abs(predictions)
                ),
                1e-6,
            )
        )
        agreement = float(
            np.clip(agreement, 0, 1)
        )
        mean_mae = float(
            np.mean([
                row["validation_mae_pct"]
                for row in model_rows
            ])
            / 100
        )
        confidence = float(
            np.clip(
                0.45 * agreement
                + 0.30
                * (1 - min(mean_mae / 0.25, 1))
                + 0.25
                * abs(
                    probability_positive - 0.5
                )
                * 2,
                0,
                1,
            )
        )

        return {
            "prediction": ensemble_prediction,
            "lower": min(lower, upper),
            "upper": max(lower, upper),
            "probability_positive": probability_positive,
            "agreement": agreement,
            "confidence": confidence,
            "model_rows": model_rows,
            "columns": columns,
            "weights": weights,
            "current_price": current_price,
        }

    def transition_matrix(self, regime_history):
        counts = pd.DataFrame(
            0.0,
            index=REGIMES,
            columns=REGIMES,
        )
        values = regime_history[
            "clean_regime"
        ].tolist()
        for current, following in zip(
            values[:-1],
            values[1:],
        ):
            if (
                current in counts.index
                and following in counts.columns
            ):
                counts.loc[
                    current,
                    following,
                ] += 1
        counts += float(
            self.cfg["transition_smoothing"]
        )
        return counts.div(
            counts.sum(axis=1),
            axis=0,
        )

    def attribution_rows(
        self,
        asset_id,
        horizon,
        current_features,
        forecast,
        forecast_date,
    ):
        candidate_drivers = {
            "return_30d": "MOMENTUM",
            "return_90d": "MOMENTUM",
            "volatility_30d": "RISK",
            "volatility_90d": "RISK",
            "distance_sma50": "TREND",
            "distance_sma200": "TREND",
            "volume_change_30d": "LIQUIDITY",
            "market_cap_change_30d": "MARKET_STRUCTURE",
        }
        values = {}
        row = current_features.iloc[0]
        for driver in forecast["columns"]:
            value = safe_float(row[driver])
            values[driver] = value

        scale = sum(
            abs(value)
            for value in values.values()
        )
        scale = max(scale, 1e-9)
        ranked = sorted(
            values.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
        rows = []
        for rank, (driver, value) in enumerate(
            ranked,
            start=1,
        ):
            contribution = (
                value / scale
                * forecast["prediction"]
                * 100
            )
            rows.append({
                "run_id": self.run_id,
                "forecast_date": forecast_date,
                "asset_id": asset_id,
                "horizon_days": horizon,
                "driver_key": driver,
                "driver_category": (
                    candidate_drivers.get(
                        driver,
                        "OTHER",
                    )
                ),
                "contribution_pct": contribution,
                "contribution_direction": (
                    "POSITIVE"
                    if contribution > 0
                    else "NEGATIVE"
                    if contribution < 0
                    else "NEUTRAL"
                ),
                "importance_rank": rank,
                "calculated_at_utc": utcnow(),
            })
        return rows

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module38_runs(
                run_id,
                source_module37_run_id,
                source_module30_run_id,
                started_at_utc,
                completed_at_utc,
                status,
                forecast_rows,
                model_rows,
                transition_rows,
                attribution_rows,
                portfolio_rows,
                horizons_completed,
                assets_completed,
                mean_validation_mae_pct,
                mean_forecast_confidence,
                predictive_regime,
                predictive_regime_confidence,
                portfolio_expected_return_pct,
                forecast_risk_status,
                recommendation,
                notes,
                platform_version
            )
            VALUES(
                ?, ?, ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0, 0,
                0, 0, NULL, NULL,
                NULL, NULL, NULL, NULL,
                NULL, NULL, '10.0.2'
            )
            """,
            [
                self.run_id,
                self.source_m37,
                self.source_m30,
                self.started,
            ],
        )

        try:
            price_frame = self.prices()
            regime_history = self.regime_history()
            current_regime, current_regime_confidence = (
                self.current_regime()
            )
            optimizer_returns = (
                self.optimizer_expected_returns()
            )
            allocations = self.optimizer_allocations()
            horizons = [
                int(value)
                for value in self.cfg["horizons_days"]
            ]
            forecast_date = pd.to_datetime(
                price_frame[
                    "observation_date"
                ].max()
            ).date()

            transition = self.transition_matrix(
                regime_history
            )
            transition_probability = (
                transition.loc[current_regime]
                if current_regime
                in transition.index
                else pd.Series(
                    np.repeat(
                        1 / len(REGIMES),
                        len(REGIMES),
                    ),
                    index=REGIMES,
                )
            )
            transition_rows = []
            for rank, (
                next_regime,
                probability,
            ) in enumerate(
                transition_probability
                .sort_values(
                    ascending=False
                )
                .items(),
                start=1,
            ):
                stay_probability = safe_float(
                    transition.loc[
                        next_regime,
                        next_regime,
                    ],
                    0.5,
                )
                duration = 1 / max(
                    1 - stay_probability,
                    1e-6,
                )
                transition_rows.append({
                    "run_id": self.run_id,
                    "forecast_date": forecast_date,
                    "current_regime": (
                        current_regime
                    ),
                    "next_regime": next_regime,
                    "transition_probability": (
                        float(probability)
                    ),
                    "expected_duration_days": (
                        min(duration, 365)
                    ),
                    "transition_rank": rank,
                    "calculated_at_utc": utcnow(),
                })

            forecasts = []
            validations = []
            attributions = []
            predictive_returns = []
            skipped_forecasts = []
            all_confidence = []
            all_mae = []

            for asset in ASSETS:
                asset_frame = price_frame[
                    price_frame["asset_id"]
                    == asset
                ].copy()
                current_price = float(
                    asset_frame.sort_values(
                        "observation_date"
                    )["price_usd"].iloc[-1]
                )
                for horizon in horizons:
                    features = self.build_features(
                        asset_frame,
                        horizon,
                    )
                    # Build the latest feature row separately. The
                    # historical training frame drops rows without a future
                    # target, but the live forecast must use the most recent
                    # available market observation.
                    live_frame = asset_frame.sort_values(
                        "observation_date"
                    ).copy()
                    live_price = live_frame[
                        "price_usd"
                    ].astype(float)
                    live_returns = live_price.pct_change(
                        fill_method=None
                    )
                    current_features = pd.DataFrame({
                        "observation_date": [
                            live_frame[
                                "observation_date"
                            ].iloc[-1]
                        ],
                        "return_1d": [
                            live_returns.iloc[-1]
                        ],
                        "return_7d": [
                            live_price.pct_change(
                                7,
                                fill_method=None,
                            ).iloc[-1]
                        ],
                        "return_30d": [
                            live_price.pct_change(
                                30,
                                fill_method=None,
                            ).iloc[-1]
                        ],
                        "return_90d": [
                            live_price.pct_change(
                                90,
                                fill_method=None,
                            ).iloc[-1]
                        ],
                        "volatility_30d": [
                            live_returns.rolling(
                                30
                            ).std().iloc[-1]
                            * math.sqrt(365)
                        ],
                        "volatility_90d": [
                            live_returns.rolling(
                                90
                            ).std().iloc[-1]
                            * math.sqrt(365)
                        ],
                        "distance_sma50": [
                            live_price.iloc[-1]
                            / live_price.rolling(
                                50
                            ).mean().iloc[-1]
                            - 1
                        ],
                        "distance_sma200": [
                            live_price.iloc[-1]
                            / live_price.rolling(
                                200
                            ).mean().iloc[-1]
                            - 1
                        ],
                        "volume_change_30d": [
                            live_frame[
                                "volume_24h_usd"
                            ].astype(float).pct_change(
                                30,
                                fill_method=None,
                            ).iloc[-1]
                            if "volume_24h_usd"
                            in live_frame
                            else 0.0
                        ],
                        "market_cap_change_30d": [
                            live_frame[
                                "market_cap_usd"
                            ].astype(float).pct_change(
                                30,
                                fill_method=None,
                            ).iloc[-1]
                            if "market_cap_usd"
                            in live_frame
                            else 0.0
                        ],
                    }).replace(
                        [np.inf, -np.inf],
                        np.nan,
                    )
                    current_features = (
                        current_features
                        .ffill(axis=0)
                        .fillna(0.0)
                    )
                    try:
                        forecast = self.train_forecast(
                            asset,
                            horizon,
                            features,
                            current_features,
                            current_price,
                        )
                    except InsufficientForecastHistory as exc:
                        skipped_forecasts.append({
                            "asset_id": exc.asset_id,
                            "horizon_days": exc.horizon_days,
                            "usable_rows": exc.usable_rows,
                            "required_rows": exc.required_rows,
                        })
                        continue

                    regime_adjustment = float(
                        (
                            transition_probability.get(
                                "LIQUIDITY_EXPANSION",
                                0,
                            )
                            + transition_probability.get(
                                "MOMENTUM_BULL",
                                0,
                            )
                            - transition_probability.get(
                                "MACRO_STRESS",
                                0,
                            )
                            - transition_probability.get(
                                "VOLATILITY_SHOCK",
                                0,
                            )
                        )
                        * float(
                            self.cfg[
                                "regime_adjustment_strength"
                            ]
                        )
                    )
                    macro_adjustment = 0.0
                    prediction = (
                        forecast["prediction"]
                        + regime_adjustment
                        + macro_adjustment
                    )
                    lower = (
                        forecast["lower"]
                        + regime_adjustment
                        + macro_adjustment
                    )
                    upper = (
                        forecast["upper"]
                        + regime_adjustment
                        + macro_adjustment
                    )
                    predicted_price = (
                        current_price
                        * (1 + prediction)
                    )
                    lower_price = current_price * (
                        1 + lower
                    )
                    upper_price = current_price * (
                        1 + upper
                    )
                    status = (
                        "POSITIVE"
                        if prediction > 0.03
                        else "NEGATIVE"
                        if prediction < -0.03
                        else "NEUTRAL"
                    )
                    forecasts.append({
                        "run_id": self.run_id,
                        "forecast_date": forecast_date,
                        "asset_id": asset,
                        "horizon_days": horizon,
                        "current_price": current_price,
                        "predicted_return_pct": (
                            prediction * 100
                        ),
                        "predicted_price": predicted_price,
                        "lower_return_pct": lower * 100,
                        "upper_return_pct": upper * 100,
                        "lower_price": lower_price,
                        "upper_price": upper_price,
                        "probability_positive": (
                            forecast[
                                "probability_positive"
                            ]
                        ),
                        "forecast_confidence": (
                            forecast["confidence"]
                        ),
                        "model_agreement": (
                            forecast["agreement"]
                        ),
                        "regime_adjustment_pct": (
                            regime_adjustment * 100
                        ),
                        "macro_adjustment_pct": (
                            macro_adjustment * 100
                        ),
                        "forecast_status": status,
                        "calculated_at_utc": utcnow(),
                    })
                    validations.extend(
                        forecast["model_rows"]
                    )
                    attributions.extend(
                        self.attribution_rows(
                            asset,
                            horizon,
                            current_features,
                            forecast,
                            forecast_date,
                        )
                    )
                    all_confidence.append(
                        forecast["confidence"]
                    )
                    all_mae.extend([
                        row[
                            "validation_mae_pct"
                        ]
                        for row in forecast[
                            "model_rows"
                        ]
                    ])

                    module37_return = safe_float(
                        optimizer_returns.get(
                            asset,
                            0.0,
                        )
                    )
                    predictive_weight = float(
                        self.cfg[
                            "optimizer_feedback"
                        ][
                            "predictive_weight"
                        ]
                    )
                    optimizer_weight = (
                        1 - predictive_weight
                    )
                    annualized_prediction = (
                        prediction
                        * 365
                        / max(horizon, 1)
                        * 100
                    )
                    blended = (
                        predictive_weight
                        * annualized_prediction
                        + optimizer_weight
                        * module37_return
                    )
                    predictive_returns.append({
                        "run_id": self.run_id,
                        "forecast_date": forecast_date,
                        "asset_id": asset,
                        "horizon_days": horizon,
                        "module37_expected_return_pct": (
                            module37_return
                        ),
                        "predictive_return_pct": (
                            annualized_prediction
                        ),
                        "blended_optimizer_return_pct": (
                            blended
                        ),
                        "predictive_weight": (
                            predictive_weight
                        ),
                        "optimizer_weight": (
                            optimizer_weight
                        ),
                        "calculated_at_utc": utcnow(),
                    })

            forecast_frame = pd.DataFrame(
                forecasts
            )
            if forecast_frame.empty:
                raise RuntimeError(
                    "Module 38 found no asset/horizon combinations "
                    "with sufficient forecast history."
                )

            portfolio_horizon = int(
                self.cfg[
                    "portfolio_summary_horizon_days"
                ]
            )
            available_portfolio_rows = forecast_frame[
                forecast_frame["horizon_days"]
                == portfolio_horizon
            ]
            if available_portfolio_rows.empty:
                available_horizons = sorted(
                    forecast_frame[
                        "horizon_days"
                    ].unique().tolist()
                )
                raise RuntimeError(
                    f"Configured portfolio horizon "
                    f"{portfolio_horizon} is unavailable. "
                    f"Available horizons: {available_horizons}"
                )

            validation_frame = pd.DataFrame(
                validations
            )
            attribution_frame = pd.DataFrame(
                attributions
            )
            predictive_frame = pd.DataFrame(
                predictive_returns
            )
            transition_frame = pd.DataFrame(
                transition_rows
            )

            portfolio_assets = forecast_frame[
                forecast_frame["horizon_days"]
                == portfolio_horizon
            ]
            expected_return = 0.0
            lower_return = 0.0
            upper_return = 0.0
            positive_probability = 0.0
            risk_weight = 0.0
            for _, row in portfolio_assets.iterrows():
                weight = safe_float(
                    allocations.get(
                        row["asset_id"],
                        0.0,
                    )
                )
                risk_weight += weight
                expected_return += (
                    weight
                    * row[
                        "predicted_return_pct"
                    ]
                )
                lower_return += (
                    weight
                    * row["lower_return_pct"]
                )
                upper_return += (
                    weight
                    * row["upper_return_pct"]
                )
                positive_probability += (
                    weight
                    * row[
                        "probability_positive"
                    ]
                )
            cash_weight = safe_float(
                allocations.get("CASH", 0.0)
            )
            if risk_weight > 0:
                positive_probability /= risk_weight
            volatility_row = self.conn.execute(
                """
                SELECT expected_volatility_pct
                FROM m37_portfolio_statistics
                WHERE run_id=?
                """,
                [self.source_m37],
            ).fetchone()
            expected_volatility = (
                safe_float(
                    volatility_row[0],
                    0.0,
                )
                if volatility_row
                else 0.0
            )
            mean_confidence = float(
                np.mean(all_confidence)
                if all_confidence
                else 0.0
            )
            risk_status = (
                "HIGH"
                if lower_return < -10
                or mean_confidence < 0.35
                else "MODERATE"
                if lower_return < -5
                or mean_confidence < 0.55
                else "CONTROLLED"
            )
            recommendation = (
                "DEFENSIVE_FORECAST"
                if expected_return < 0
                or risk_status == "HIGH"
                else "SELECTIVE_ACCUMULATION"
                if expected_return < 5
                or risk_status == "MODERATE"
                else "PREDICTIVE_RISK_ON"
            )
            portfolio_frame = pd.DataFrame([{
                "run_id": self.run_id,
                "forecast_date": forecast_date,
                "horizon_days": portfolio_horizon,
                "expected_portfolio_return_pct": (
                    expected_return
                ),
                "lower_portfolio_return_pct": (
                    lower_return
                ),
                "upper_portfolio_return_pct": (
                    upper_return
                ),
                "probability_positive": (
                    positive_probability
                ),
                "expected_portfolio_volatility_pct": (
                    expected_volatility
                ),
                "forecast_confidence": (
                    mean_confidence
                ),
                "dominant_predictive_regime": (
                    transition_probability
                    .idxmax()
                ),
                "predictive_regime_confidence": (
                    float(
                        transition_probability.max()
                    )
                ),
                "cash_weight": cash_weight,
                "risk_asset_weight": risk_weight,
                "forecast_risk_status": (
                    risk_status
                ),
                "recommendation": recommendation,
                "calculated_at_utc": utcnow(),
            }])

            self.upsert(
                "m38_asset_forecasts",
                forecast_frame,
            )
            self.upsert(
                "m38_model_validation",
                validation_frame,
            )
            self.upsert(
                "m38_regime_transitions",
                transition_frame,
            )
            self.upsert(
                "m38_forecast_attribution",
                attribution_frame,
            )
            self.upsert(
                "m38_portfolio_forecast",
                portfolio_frame,
            )
            self.upsert(
                "m38_predictive_expected_returns",
                predictive_frame,
            )

            mean_mae = float(
                np.mean(all_mae)
                if all_mae
                else 0.0
            )
            skipped_note = (
                json.dumps(
                    skipped_forecasts,
                    separators=(",", ":"),
                )
                if skipped_forecasts
                else "[]"
            )
            notes = (
                "Multi-horizon ensemble forecasts, empirical uncertainty "
                "intervals, regime transitions, driver attribution, and "
                "predictive optimizer expected-return feedback completed. "
                f"Skipped unsupported forecasts={skipped_note}"
            )
            self.conn.execute(
                """
                UPDATE module38_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    forecast_rows=?,
                    model_rows=?,
                    transition_rows=?,
                    attribution_rows=?,
                    portfolio_rows=?,
                    horizons_completed=?,
                    assets_completed=?,
                    mean_validation_mae_pct=?,
                    mean_forecast_confidence=?,
                    predictive_regime=?,
                    predictive_regime_confidence=?,
                    portfolio_expected_return_pct=?,
                    forecast_risk_status=?,
                    recommendation=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(forecast_frame),
                    len(validation_frame),
                    len(transition_frame),
                    len(attribution_frame),
                    len(portfolio_frame),
                    forecast_frame[
                        "horizon_days"
                    ].nunique(),
                    forecast_frame[
                        "asset_id"
                    ].nunique(),
                    mean_mae,
                    mean_confidence,
                    transition_probability.idxmax(),
                    float(
                        transition_probability.max()
                    ),
                    expected_return,
                    risk_status,
                    recommendation,
                    notes,
                    self.run_id,
                ],
            )
            self.conn.close()
            return portfolio_frame.iloc[0].to_dict() | {
                "forecast_rows": len(
                    forecast_frame
                ),
                "mean_validation_mae_pct": (
                    mean_mae
                ),
            }

        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module38_runs
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
            self.conn.close()
            raise


def run_module38():
    return Module38Runner().run()
