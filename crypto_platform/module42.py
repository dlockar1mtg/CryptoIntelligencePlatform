from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.module37 import MODULE37_SCHEMA
from crypto_platform.module38 import MODULE38_SCHEMA
from crypto_platform.module39 import MODULE39_SCHEMA
from crypto_platform.module40 import MODULE40_SCHEMA
from crypto_platform.module41 import MODULE41_SCHEMA


MODULE42_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module42_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module30_run_id VARCHAR,
    source_module37_run_id VARCHAR,
    source_module38_run_id VARCHAR,
    source_module39_run_id VARCHAR,
    source_module40_run_id VARCHAR,
    source_module41_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    recommendation_rows INTEGER,
    projection_rows INTEGER,
    assets_covered INTEGER,
    horizons_covered INTEGER,
    total_target_risk_weight DOUBLE,
    target_cash_weight DOUBLE,
    overall_action VARCHAR,
    overall_timeline VARCHAR,
    evidence_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m42_asset_recommendations(
    run_id VARCHAR,
    recommendation_date DATE,
    asset_id VARCHAR,
    current_price DOUBLE,
    investment_score DOUBLE,
    best_action VARCHAR,
    current_portfolio_weight DOUBLE,
    best_current_portfolio_pct DOUBLE,
    weight_change_pct DOUBLE,
    suggested_timeline VARCHAR,
    entry_strategy VARCHAR,
    conviction VARCHAR,
    forecast_confidence DOUBLE,
    reliability_score DOUBLE,
    regime_alignment_score DOUBLE,
    risk_score DOUBLE,
    short_term_signal DOUBLE,
    medium_term_signal DOUBLE,
    long_term_signal DOUBLE,
    primary_reason VARCHAR,
    risk_warning VARCHAR,
    evidence_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, recommendation_date, asset_id)
);

CREATE TABLE IF NOT EXISTS m42_price_projections(
    run_id VARCHAR,
    recommendation_date DATE,
    asset_id VARCHAR,
    horizon_label VARCHAR,
    horizon_days INTEGER,
    horizon_months DOUBLE,
    projection_date DATE,
    current_price DOUBLE,
    bear_price DOUBLE,
    median_price DOUBLE,
    bull_price DOUBLE,
    bear_return_pct DOUBLE,
    median_return_pct DOUBLE,
    bull_return_pct DOUBLE,
    annualized_median_return_pct DOUBLE,
    scenario_width_pct DOUBLE,
    projection_confidence DOUBLE,
    projection_method VARCHAR,
    evidence_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id,
        recommendation_date,
        asset_id,
        horizon_label
    )
);

CREATE TABLE IF NOT EXISTS m42_portfolio_plan(
    run_id VARCHAR,
    recommendation_date DATE,
    asset_id VARCHAR,
    target_weight DOUBLE,
    current_weight DOUBLE,
    trade_weight DOUBLE,
    trade_action VARCHAR,
    execution_stage INTEGER,
    execution_window VARCHAR,
    tranche_pct DOUBLE,
    trigger_description VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id,
        recommendation_date,
        asset_id,
        execution_stage
    )
);

CREATE TABLE IF NOT EXISTS m42_decision_summary(
    run_id VARCHAR PRIMARY KEY,
    recommendation_date DATE,
    overall_action VARCHAR,
    overall_timeline VARCHAR,
    target_cash_weight DOUBLE,
    target_risk_weight DOUBLE,
    highest_conviction_asset VARCHAR,
    highest_conviction_score DOUBLE,
    positive_assets INTEGER,
    wait_assets INTEGER,
    reduce_assets INTEGER,
    evidence_status VARCHAR,
    decision_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m42_asset_recommendations AS
SELECT *
FROM m42_asset_recommendations
WHERE run_id=(
    SELECT run_id
    FROM module42_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY investment_score DESC;

CREATE OR REPLACE VIEW latest_m42_price_projections AS
SELECT *
FROM m42_price_projections
WHERE run_id=(
    SELECT run_id
    FROM module42_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY asset_id, horizon_days;

CREATE OR REPLACE VIEW latest_m42_portfolio_plan AS
SELECT *
FROM m42_portfolio_plan
WHERE run_id=(
    SELECT run_id
    FROM module42_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY execution_stage, target_weight DESC;

CREATE OR REPLACE VIEW latest_m42_decision_summary AS
SELECT *
FROM m42_decision_summary
WHERE run_id=(
    SELECT run_id
    FROM module42_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
);
"""


ASSETS = [
    "bitcoin",
    "ethereum",
    "solana",
    "chainlink",
    "xrp",
    "avalanche",
]

SHORT_HORIZONS = [
    ("7D", 7, 7 / 30.4375),
    ("30D", 30, 30 / 30.4375),
]

QUARTERLY_HORIZONS = [
    (f"M{month:02d}", int(round(month * 30.4375)), float(month))
    for month in range(3, 49, 3)
]

ALL_HORIZONS = SHORT_HORIZONS + QUARTERLY_HORIZONS


def utcnow():
    return datetime.now(timezone.utc)


def safe_float(value, default=0.0):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def clip(value, lower, upper):
    return float(np.clip(value, lower, upper))


def annualize_return(total_return, days):
    if days <= 0:
        return 0.0
    base = max(1 + total_return, 0.01)
    return base ** (365 / days) - 1


class Module42Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE30_SCHEMA)
        self.conn.execute(MODULE37_SCHEMA)
        self.conn.execute(MODULE38_SCHEMA)
        self.conn.execute(MODULE39_SCHEMA)
        self.conn.execute(MODULE40_SCHEMA)
        self.conn.execute(MODULE41_SCHEMA)
        self.conn.execute(MODULE42_SCHEMA)

        self.cfg = self.settings["module42"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

        self.source30 = self.latest_success(
            "module30_runs"
        )
        self.source37 = self.latest_success(
            "module37_runs"
        )
        self.source38 = self.latest_success(
            "module38_runs"
        )
        self.source39 = self.latest_success(
            "module39_runs"
        )
        self.source40 = self.latest_success(
            "module40_runs"
        )
        self.source41 = self.latest_success(
            "module41_runs"
        )

    def latest_success(self, table):
        row = self.conn.execute(
            f"""
            SELECT run_id
            FROM {table}
            WHERE status='SUCCESS'
            ORDER BY started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError(
                f"A successful {table} run is required."
            )
        return str(row[0])

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m42_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"""
            INSERT OR REPLACE INTO {table}({columns})
            SELECT {columns}
            FROM _m42_stage
            """
        )
        self.conn.unregister("_m42_stage")

    def current_prices(self):
        frame = self.conn.execute(
            """
            SELECT asset_id,
                   arg_max(price_usd, observation_date)
                       AS current_price,
                   max(observation_date)
                       AS price_date
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana',
                'chainlink','xrp','avalanche'
            )
              AND price_usd IS NOT NULL
            GROUP BY asset_id
            """
        ).fetchdf()
        return frame.set_index("asset_id")

    def historical_statistics(self):
        frame = self.conn.execute(
            """
            SELECT asset_id,
                   observation_date,
                   price_usd
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana',
                'chainlink','xrp','avalanche'
            )
              AND price_usd IS NOT NULL
            ORDER BY asset_id, observation_date
            """
        ).fetchdf()
        rows = []
        lookback = int(
            self.cfg["historical_lookback_days"]
        )
        for asset, group in frame.groupby("asset_id"):
            group = group.tail(lookback)
            returns = (
                group["price_usd"]
                .astype(float)
                .pct_change(fill_method=None)
                .dropna()
            )
            annual_return = (
                float(returns.mean() * 365)
                if not returns.empty
                else 0.0
            )
            annual_volatility = (
                float(
                    returns.std(ddof=0)
                    * math.sqrt(365)
                )
                if not returns.empty
                else 0.0
            )
            drawdown = 0.0
            if not group.empty:
                price = group["price_usd"].astype(float)
                peak = price.cummax()
                drawdown = float(
                    (price / peak - 1).min()
                )
            rows.append({
                "asset_id": asset,
                "historical_annual_return": annual_return,
                "annual_volatility": annual_volatility,
                "maximum_drawdown": drawdown,
            })
        return pd.DataFrame(rows).set_index(
            "asset_id"
        )

    def source_signals(self):
        forecasts = self.conn.execute(
            """
            SELECT *
            FROM m39_calibrated_forecasts
            WHERE run_id=?
            """,
            [self.source39],
        ).fetchdf()

        allocations = self.conn.execute(
            """
            SELECT asset_id,
                   risk_adjusted_weight
            FROM m37_optimized_allocations
            WHERE run_id=?
            """,
            [self.source37],
        ).fetchdf()

        reliability = self.conn.execute(
            """
            SELECT asset_id,
                   horizon_days,
                   reliability_score,
                   reliability_grade,
                   matured_forecasts
            FROM m41_horizon_reliability
            WHERE run_id=?
            """,
            [self.source41],
        ).fetchdf()

        feedback = self.conn.execute(
            """
            SELECT asset_id,
                   horizon_days,
                   adaptive_expected_return_pct,
                   feedback_status,
                   confidence_multiplier
            FROM m41_optimizer_feedback
            WHERE run_id=?
            """,
            [self.source41],
        ).fetchdf()

        regime = self.conn.execute(
            """
            SELECT clean_regime,
                   clean_probability
            FROM clean_regime_current
            WHERE run_id=?
            LIMIT 1
            """,
            [self.source30],
        ).fetchone()

        return {
            "forecasts": forecasts,
            "allocations": dict(zip(
                allocations["asset_id"],
                allocations["risk_adjusted_weight"],
            )),
            "reliability": reliability,
            "feedback": feedback,
            "regime": (
                str(regime[0]),
                safe_float(regime[1], 0.5),
            ),
        }

    def regime_alignment(self, regime):
        positive = {
            "LIQUIDITY_EXPANSION": 85,
            "MOMENTUM_BULL": 90,
            "RECOVERY": 75,
            "RANGE_BOUND": 50,
            "MACRO_STRESS": 25,
            "VOLATILITY_SHOCK": 15,
        }
        return float(positive.get(regime, 50))

    def forecast_for(self, frame, asset, horizon):
        subset = frame[
            (frame["asset_id"] == asset)
            & (
                frame["horizon_days"]
                == horizon
            )
        ]
        if subset.empty:
            return None
        return subset.iloc[0]

    def adaptive_for(self, frame, asset, horizon):
        subset = frame[
            (frame["asset_id"] == asset)
            & (
                frame["horizon_days"]
                == horizon
            )
        ]
        if subset.empty:
            return None
        return subset.iloc[0]

    def reliability_for(
        self,
        frame,
        asset,
        horizon,
    ):
        subset = frame[
            (frame["asset_id"] == asset)
            & (
                frame["horizon_days"]
                == horizon
            )
        ]
        if subset.empty:
            return {
                "score": 0.0,
                "grade": "INSUFFICIENT_EVIDENCE",
                "matured": 0,
            }
        row = subset.iloc[0]
        return {
            "score": safe_float(
                row["reliability_score"]
            ),
            "grade": row[
                "reliability_grade"
            ],
            "matured": int(
                row["matured_forecasts"]
            ),
        }

    def estimate_long_run_annual_return(
        self,
        asset,
        forecast_frame,
        feedback_frame,
        historical,
        regime_score,
        reliability_score,
    ):
        short_inputs = []
        for horizon in [30, 90, 180]:
            adaptive = self.adaptive_for(
                feedback_frame,
                asset,
                horizon,
            )
            if adaptive is not None:
                total_return = safe_float(
                    adaptive[
                        "adaptive_expected_return_pct"
                    ]
                ) / 100
                annualized = annualize_return(
                    total_return,
                    horizon,
                )
                short_inputs.append(
                    clip(annualized, -0.80, 1.50)
                )
                continue

            forecast = self.forecast_for(
                forecast_frame,
                asset,
                horizon,
            )
            if forecast is not None:
                total_return = safe_float(
                    forecast[
                        "predicted_return_pct"
                    ]
                ) / 100
                annualized = annualize_return(
                    total_return,
                    horizon,
                )
                short_inputs.append(
                    clip(annualized, -0.80, 1.50)
                )

        forecast_anchor = (
            float(np.median(short_inputs))
            if short_inputs
            else 0.0
        )
        historical_anchor = clip(
            safe_float(
                historical.loc[
                    asset,
                    "historical_annual_return",
                ]
            ),
            -0.50,
            1.00,
        )
        neutral_prior = float(
            self.cfg[
                "long_range_neutral_annual_return"
            ]
        )

        evidence_ratio = clip(
            reliability_score / 100,
            0,
            1,
        )
        forecast_weight = (
            float(
                self.cfg[
                    "long_range_weights"
                ]["forecast"]
            )
            * (
                0.35
                + 0.65 * evidence_ratio
            )
        )
        historical_weight = float(
            self.cfg[
                "long_range_weights"
            ]["historical"]
        )
        prior_weight = float(
            self.cfg[
                "long_range_weights"
            ]["neutral_prior"]
        )

        regime_adjustment = (
            (regime_score - 50)
            / 50
            * float(
                self.cfg[
                    "maximum_regime_annual_adjustment"
                ]
            )
        )

        denominator = (
            forecast_weight
            + historical_weight
            + prior_weight
        )
        estimate = (
            forecast_weight * forecast_anchor
            + historical_weight
            * historical_anchor
            + prior_weight * neutral_prior
        ) / max(denominator, 1e-9)
        estimate += regime_adjustment

        return clip(
            estimate,
            float(
                self.cfg[
                    "minimum_long_range_annual_return"
                ]
            ),
            float(
                self.cfg[
                    "maximum_long_range_annual_return"
                ]
            ),
        )

    def projection_rows(
        self,
        asset,
        current_price,
        forecast_frame,
        feedback_frame,
        reliability_frame,
        historical,
        regime_score,
        recommendation_date,
    ):
        reliability_90 = self.reliability_for(
            reliability_frame,
            asset,
            90,
        )
        annual_return = (
            self.estimate_long_run_annual_return(
                asset,
                forecast_frame,
                feedback_frame,
                historical,
                regime_score,
                reliability_90["score"],
            )
        )
        annual_volatility = safe_float(
            historical.loc[
                asset,
                "annual_volatility",
            ],
            0.70,
        )
        annual_volatility = clip(
            annual_volatility,
            0.20,
            float(
                self.cfg[
                    "maximum_projection_volatility"
                ]
            ),
        )

        rows = []
        for label, days, months in ALL_HORIZONS:
            exact = self.forecast_for(
                forecast_frame,
                asset,
                days,
            )
            adaptive = self.adaptive_for(
                feedback_frame,
                asset,
                days,
            )
            reliability = self.reliability_for(
                reliability_frame,
                asset,
                days,
            )

            if exact is not None and days in {
                7,
                30,
                90,
                180,
            }:
                median_return = safe_float(
                    exact[
                        "predicted_return_pct"
                    ]
                ) / 100
                lower_return = safe_float(
                    exact[
                        "conformal_lower_return_pct"
                    ]
                ) / 100
                upper_return = safe_float(
                    exact[
                        "conformal_upper_return_pct"
                    ]
                ) / 100
                if adaptive is not None:
                    adaptive_return = safe_float(
                        adaptive[
                            "adaptive_expected_return_pct"
                        ]
                    ) / 100
                    median_return = (
                        0.70 * median_return
                        + 0.30 * adaptive_return
                    )
                method = (
                    "CALIBRATED_ENSEMBLE"
                )
                confidence = clip(
                    safe_float(
                        exact[
                            "forecast_confidence"
                        ]
                    )
                    * (
                        0.60
                        + 0.40
                        * clip(
                            reliability["score"]
                            / 100,
                            0,
                            1,
                        )
                    ),
                    0.05,
                    0.95,
                )
                evidence = (
                    "LIVE_VALIDATED"
                    if reliability["matured"]
                    >= int(
                        self.cfg[
                            "minimum_matured_for_live"
                        ]
                    )
                    else "MODEL_VALIDATED"
                )
            else:
                years = days / 365
                median_return = (
                    (1 + annual_return) ** years
                    - 1
                )
                z = float(
                    self.cfg[
                        "scenario_standard_deviations"
                    ]
                )
                uncertainty = (
                    z
                    * annual_volatility
                    * math.sqrt(years)
                )
                median_log = math.log(
                    max(
                        1 + median_return,
                        0.01,
                    )
                )
                lower_return = (
                    math.exp(
                        median_log - uncertainty
                    )
                    - 1
                )
                upper_return = (
                    math.exp(
                        median_log + uncertainty
                    )
                    - 1
                )
                method = (
                    "LONG_RANGE_SCENARIO_MODEL"
                )
                horizon_decay = math.exp(
                    -days
                    / float(
                        self.cfg[
                            "confidence_half_life_days"
                        ]
                    )
                )
                confidence = clip(
                    (
                        0.20
                        + 0.50
                        * clip(
                            reliability_90[
                                "score"
                            ]
                            / 100,
                            0,
                            1,
                        )
                    )
                    * horizon_decay,
                    0.03,
                    0.70,
                )
                evidence = (
                    "SCENARIO_ONLY"
                )

            lower_return = max(
                lower_return,
                -0.95,
            )
            median_return = max(
                median_return,
                -0.95,
            )
            upper_return = max(
                upper_return,
                median_return,
            )

            projection_date = (
                pd.Timestamp(
                    recommendation_date
                )
                + pd.Timedelta(days=days)
            ).date()
            bear_price = current_price * (
                1 + lower_return
            )
            median_price = current_price * (
                1 + median_return
            )
            bull_price = current_price * (
                1 + upper_return
            )

            rows.append({
                "run_id": self.run_id,
                "recommendation_date": (
                    recommendation_date
                ),
                "asset_id": asset,
                "horizon_label": label,
                "horizon_days": days,
                "horizon_months": months,
                "projection_date": (
                    projection_date
                ),
                "current_price": current_price,
                "bear_price": bear_price,
                "median_price": median_price,
                "bull_price": bull_price,
                "bear_return_pct": (
                    lower_return * 100
                ),
                "median_return_pct": (
                    median_return * 100
                ),
                "bull_return_pct": (
                    upper_return * 100
                ),
                "annualized_median_return_pct": (
                    annualize_return(
                        median_return,
                        days,
                    )
                    * 100
                ),
                "scenario_width_pct": (
                    (
                        upper_return
                        - lower_return
                    )
                    * 100
                ),
                "projection_confidence": (
                    confidence
                ),
                "projection_method": method,
                "evidence_status": evidence,
                "calculated_at_utc": utcnow(),
            })
        return rows

    def recommendation_for(
        self,
        asset,
        projections,
        current_weight,
        reliability,
        regime_score,
        annual_volatility,
    ):
        projection_map = {
            row["horizon_label"]: row
            for row in projections
        }
        return_7d = (
            projection_map["7D"][
                "median_return_pct"
            ]
        )
        return_30d = (
            projection_map["30D"][
                "median_return_pct"
            ]
        )
        return_90d = (
            projection_map["M03"][
                "median_return_pct"
            ]
        )
        return_12m = (
            projection_map["M12"][
                "median_return_pct"
            ]
        )
        return_48m = (
            projection_map["M48"][
                "median_return_pct"
            ]
        )

        short_signal = clip(
            50
            + 2.0 * return_7d
            + 1.0 * return_30d,
            0,
            100,
        )
        medium_signal = clip(
            50
            + 0.7 * return_90d
            + 0.25 * return_12m,
            0,
            100,
        )
        long_signal = clip(
            50
            + 0.10 * return_48m,
            0,
            100,
        )
        reliability_score = safe_float(
            reliability["score"]
        )
        risk_score = clip(
            100
            - annual_volatility * 65,
            0,
            100,
        )

        score = (
            0.20 * short_signal
            + 0.25 * medium_signal
            + 0.15 * long_signal
            + 0.15 * regime_score
            + 0.15 * reliability_score
            + 0.10 * risk_score
        )

        if (
            return_30d < -5
            and return_90d < 0
        ):
            action = "WAIT"
        elif score >= 78 and return_30d > 0:
            action = "STRONG_BUY"
        elif score >= 65 and return_90d > 0:
            action = "BUY"
        elif score >= 52 and return_12m > 0:
            action = "SCALE_IN"
        elif score >= 42:
            action = "HOLD"
        elif current_weight > 0.005:
            action = "REDUCE"
        else:
            action = "AVOID"

        conviction = (
            "HIGH"
            if score >= 75
            else "MODERATE"
            if score >= 55
            else "LOW"
        )

        if action == "STRONG_BUY":
            timeline = "BEGIN_WITHIN_1_TO_3_DAYS"
            entry = (
                "50% now, 25% after 7 days, "
                "25% on a 5-10% pullback"
            )
        elif action == "BUY":
            timeline = "BEGIN_WITHIN_1_WEEK"
            entry = (
                "40% now, 30% over 2 weeks, "
                "30% on weakness"
            )
        elif action == "SCALE_IN":
            timeline = "ACCUMULATE_OVER_2_TO_6_WEEKS"
            entry = (
                "Four equal weekly or biweekly tranches"
            )
        elif action == "HOLD":
            timeline = "REVIEW_IN_30_DAYS"
            entry = (
                "No immediate increase; rebalance only"
            )
        elif action == "WAIT":
            timeline = "WAIT_7_TO_30_DAYS"
            entry = (
                "Reassess after short-term signal improves"
            )
        elif action == "REDUCE":
            timeline = "REDUCE_WITHIN_1_TO_2_WEEKS"
            entry = (
                "Trim in two equal stages"
            )
        else:
            timeline = "NO_ENTRY_TIMELINE"
            entry = "Do not initiate a position"

        return {
            "score": score,
            "action": action,
            "conviction": conviction,
            "timeline": timeline,
            "entry_strategy": entry,
            "short_signal": short_signal,
            "medium_signal": medium_signal,
            "long_signal": long_signal,
            "risk_score": risk_score,
            "return_7d": return_7d,
            "return_30d": return_30d,
            "return_90d": return_90d,
            "return_12m": return_12m,
            "return_48m": return_48m,
        }


    def target_weights(
        self,
        recommendations,
        current_allocations,
    ):
        """Create action-consistent total-portfolio targets.

        The configured crypto percentage is a ceiling, not a deployment
        target. New capital is assigned only to STRONG_BUY, BUY, or
        SCALE_IN assets. HOLD preserves the current position, WAIT blocks
        new capital, REDUCE trims, and AVOID targets zero.
        """
        max_asset = float(
            self.cfg[
                "maximum_asset_portfolio_pct"
            ]
        ) / 100
        maximum_crypto = float(
            self.cfg[
                "maximum_crypto_portfolio_pct"
            ]
        ) / 100

        targets = {}
        deployable_scores = {}

        for asset in ASSETS:
            rec = recommendations[asset]
            current = max(
                safe_float(
                    current_allocations.get(
                        asset,
                        0.0,
                    )
                ),
                0.0,
            )
            action = rec["action"]

            if action == "HOLD":
                targets[asset] = min(
                    current,
                    max_asset,
                )
            elif action == "WAIT":
                targets[asset] = min(
                    current,
                    max_asset,
                )
            elif action == "REDUCE":
                targets[asset] = min(
                    current
                    * float(
                        self.cfg[
                            "reduce_target_fraction"
                        ]
                    ),
                    max_asset,
                )
            elif action == "AVOID":
                targets[asset] = 0.0
            else:
                targets[asset] = min(
                    current,
                    max_asset,
                )
                action_multiplier = {
                    "STRONG_BUY": 1.00,
                    "BUY": 0.75,
                    "SCALE_IN": 0.45,
                }[action]
                evidence_multiplier = (
                    1.00
                    if rec.get(
                        "evidence_status"
                    )
                    == "LIVE_VALIDATED"
                    else float(
                        self.cfg[
                            "accumulating_evidence_multiplier"
                        ]
                    )
                )
                confidence_multiplier = clip(
                    rec.get(
                        "forecast_confidence",
                        0.0,
                    ),
                    float(
                        self.cfg[
                            "minimum_confidence_multiplier"
                        ]
                    ),
                    1.0,
                )
                deployable_scores[asset] = (
                    max(
                        rec["score"]
                        - float(
                            self.cfg[
                                "minimum_buy_score"
                            ]
                        ),
                        0.0,
                    )
                    * action_multiplier
                    * evidence_multiplier
                    * confidence_multiplier
                )

        current_total = sum(targets.values())
        available_capacity = max(
            maximum_crypto - current_total,
            0.0,
        )

        if (
            available_capacity > 0
            and deployable_scores
        ):
            total_score = sum(
                deployable_scores.values()
            )
            if total_score > 0:
                for asset, score in (
                    deployable_scores.items()
                ):
                    headroom = max(
                        max_asset
                        - targets[asset],
                        0.0,
                    )
                    allocation = (
                        available_capacity
                        * score
                        / total_score
                    )
                    targets[asset] += min(
                        allocation,
                        headroom,
                    )

        # Never force risk exposure up to the configured maximum.
        total = sum(targets.values())
        if total > maximum_crypto:
            excess = total - maximum_crypto
            reducible = sorted(
                ASSETS,
                key=lambda asset: (
                    recommendations[asset][
                        "score"
                    ],
                    targets[asset],
                ),
            )
            for asset in reducible:
                if excess <= 1e-12:
                    break
                floor = 0.0
                if recommendations[asset][
                    "action"
                ] in {"HOLD", "WAIT"}:
                    floor = min(
                        safe_float(
                            current_allocations.get(
                                asset,
                                0.0,
                            )
                        ),
                        targets[asset],
                    )
                removable = max(
                    targets[asset] - floor,
                    0.0,
                )
                reduction = min(
                    removable,
                    excess,
                )
                targets[asset] -= reduction
                excess -= reduction

        return {
            asset: clip(
                targets.get(asset, 0.0),
                0.0,
                max_asset,
            )
            for asset in ASSETS
        }


    def plan_rows(
        self,
        recommendation_date,
        recommendations,
        target,
        current,
    ):
        rows = []

        for asset in ASSETS:
            rec = recommendations[asset]
            current_weight = safe_float(
                current.get(asset, 0.0)
            )
            target_weight = safe_float(
                target.get(asset, 0.0)
            )
            action = rec["action"]
            trade_weight = (
                target_weight
                - current_weight
            )

            # Guardrail: HOLD and WAIT cannot create new-buy instructions.
            if action in {"HOLD", "WAIT"}:
                trade_weight = min(
                    trade_weight,
                    0.0,
                )
                target_weight = min(
                    target_weight,
                    current_weight,
                )

            if action == "AVOID":
                target_weight = 0.0
                trade_weight = -current_weight

            if action == "REDUCE":
                trade_weight = min(
                    trade_weight,
                    0.0,
                )

            trade_action = (
                "BUY"
                if trade_weight > 0.0025
                else "SELL"
                if trade_weight < -0.0025
                else "HOLD"
            )

            if trade_action == "BUY":
                if action not in {
                    "STRONG_BUY",
                    "BUY",
                    "SCALE_IN",
                }:
                    raise RuntimeError(
                        f"Decision consistency violation: "
                        f"{asset} action={action} "
                        "cannot generate a BUY plan."
                    )

                tranches = (
                    [0.50, 0.25, 0.25]
                    if action in {
                        "STRONG_BUY",
                        "BUY",
                    }
                    else [
                        0.25,
                        0.25,
                        0.25,
                        0.25,
                    ]
                )
                windows = (
                    [
                        "NOW_TO_3_DAYS",
                        "DAY_7_TO_14",
                        "ON_5_TO_10_PCT_PULLBACK",
                    ]
                    if len(tranches) == 3
                    else [
                        "WEEK_1",
                        "WEEK_2",
                        "WEEK_4",
                        "WEEK_6",
                    ]
                )

                for stage, (
                    fraction,
                    window,
                ) in enumerate(
                    zip(tranches, windows),
                    start=1,
                ):
                    rows.append({
                        "run_id": self.run_id,
                        "recommendation_date": (
                            recommendation_date
                        ),
                        "asset_id": asset,
                        "target_weight": (
                            target_weight
                        ),
                        "current_weight": (
                            current_weight
                        ),
                        "trade_weight": (
                            trade_weight
                            * fraction
                        ),
                        "trade_action": "BUY",
                        "execution_stage": stage,
                        "execution_window": window,
                        "tranche_pct": (
                            fraction * 100
                        ),
                        "trigger_description": (
                            rec[
                                "entry_strategy"
                            ]
                        ),
                        "calculated_at_utc": (
                            utcnow()
                        ),
                    })
            else:
                rows.append({
                    "run_id": self.run_id,
                    "recommendation_date": (
                        recommendation_date
                    ),
                    "asset_id": asset,
                    "target_weight": target_weight,
                    "current_weight": current_weight,
                    "trade_weight": trade_weight,
                    "trade_action": trade_action,
                    "execution_stage": 1,
                    "execution_window": (
                        rec["timeline"]
                    ),
                    "tranche_pct": 100.0,
                    "trigger_description": (
                        rec["entry_strategy"]
                    ),
                    "calculated_at_utc": (
                        utcnow()
                    ),
                })

        return rows

    def validate_decision_consistency(
        self,
        summary,
        recommendations,
        plan,
    ):
        """Block contradictory defensive or action-inconsistent output."""
        errors = []

        positive_actions = {
            "STRONG_BUY",
            "BUY",
            "SCALE_IN",
        }

        merged = plan.merge(
            recommendations[
                [
                    "asset_id",
                    "best_action",
                ]
            ],
            on="asset_id",
            how="left",
        )

        invalid_buys = merged[
            (merged["trade_action"] == "BUY")
            & (
                ~merged["best_action"].isin(
                    positive_actions
                )
            )
        ]
        if not invalid_buys.empty:
            errors.append(
                "BUY instructions exist for "
                "non-buy recommendations: "
                + ",".join(
                    sorted(
                        invalid_buys[
                            "asset_id"
                        ].unique()
                    )
                )
            )

        defensive = (
            summary.iloc[0]["overall_action"]
            == "REMAIN_DEFENSIVE"
        )
        material_buys = plan[
            (plan["trade_action"] == "BUY")
            & (
                plan["trade_weight"]
                > float(
                    self.cfg[
                        "material_trade_weight_pct"
                    ]
                )
                / 100
            )
        ]
        if defensive and not material_buys.empty:
            errors.append(
                "Defensive summary contains "
                "material purchase instructions."
            )

        hold_wait_increases = recommendations[
            recommendations[
                "best_action"
            ].isin({"HOLD", "WAIT"})
            & (
                recommendations[
                    "weight_change_pct"
                ]
                > float(
                    self.cfg[
                        "weight_change_tolerance_pct"
                    ]
                )
            )
        ]
        if not hold_wait_increases.empty:
            errors.append(
                "HOLD/WAIT targets increase exposure: "
                + ",".join(
                    sorted(
                        hold_wait_increases[
                            "asset_id"
                        ].tolist()
                    )
                )
            )

        target_risk = float(
            recommendations[
                "best_current_portfolio_pct"
            ].sum()
            / 100
        )
        maximum_crypto = float(
            self.cfg[
                "maximum_crypto_portfolio_pct"
            ]
        ) / 100
        if target_risk > maximum_crypto + 1e-9:
            errors.append(
                f"Target crypto weight "
                f"{target_risk:.4f} exceeds "
                f"ceiling {maximum_crypto:.4f}."
            )

        if errors:
            raise RuntimeError(
                "Decision consistency validation failed: "
                + " | ".join(errors)
            )

        return {
            "invalid_buy_rows": 0,
            "defensive_material_buys": 0,
            "hold_wait_increases": 0,
            "target_risk_weight": target_risk,
            "maximum_crypto_weight": maximum_crypto,
        }

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module42_runs(
                run_id,
                source_module30_run_id,
                source_module37_run_id,
                source_module38_run_id,
                source_module39_run_id,
                source_module40_run_id,
                source_module41_run_id,
                started_at_utc,
                completed_at_utc,
                status,
                recommendation_rows,
                projection_rows,
                assets_covered,
                horizons_covered,
                total_target_risk_weight,
                target_cash_weight,
                overall_action,
                overall_timeline,
                evidence_status,
                recommendation,
                notes,
                platform_version
            )
            VALUES(
                ?,?,?,?,?,?,?,?,
                NULL,'RUNNING',
                0,0,0,0,
                NULL,NULL,NULL,NULL,NULL,NULL,NULL,
                '12.0.1'
            )
            """,
            [
                self.run_id,
                self.source30,
                self.source37,
                self.source38,
                self.source39,
                self.source40,
                self.source41,
                self.started,
            ],
        )

        try:
            prices = self.current_prices()
            historical = (
                self.historical_statistics()
            )
            signals = self.source_signals()
            regime, regime_probability = (
                signals["regime"]
            )
            regime_score = (
                self.regime_alignment(regime)
                * (
                    0.60
                    + 0.40
                    * regime_probability
                )
            )

            recommendation_date = pd.Timestamp(
                prices["price_date"].max()
            ).date()

            projection_rows = []
            recommendation_inputs = {}
            recommendation_rows = []

            for asset in ASSETS:
                current_price = safe_float(
                    prices.loc[
                        asset,
                        "current_price",
                    ]
                )
                asset_projections = (
                    self.projection_rows(
                        asset,
                        current_price,
                        signals["forecasts"],
                        signals["feedback"],
                        signals["reliability"],
                        historical,
                        regime_score,
                        recommendation_date,
                    )
                )
                projection_rows.extend(
                    asset_projections
                )
                reliability = (
                    self.reliability_for(
                        signals["reliability"],
                        asset,
                        90,
                    )
                )
                current_weight = safe_float(
                    signals["allocations"].get(
                        asset,
                        0.0,
                    )
                )
                rec = self.recommendation_for(
                    asset,
                    asset_projections,
                    current_weight,
                    reliability,
                    regime_score,
                    safe_float(
                        historical.loc[
                            asset,
                            "annual_volatility",
                        ],
                        0.75,
                    ),
                )
                rec["forecast_confidence"] = float(
                    np.mean([
                        row[
                            "projection_confidence"
                        ]
                        for row in asset_projections
                        if row[
                            "horizon_label"
                        ] in {
                            "7D",
                            "30D",
                            "M03",
                        }
                    ])
                )
                rec["evidence_status"] = (
                    "LIVE_VALIDATED"
                    if reliability["matured"]
                    >= int(
                        self.cfg[
                            "minimum_matured_for_live"
                        ]
                    )
                    else "ACCUMULATING_EVIDENCE"
                )
                recommendation_inputs[
                    asset
                ] = rec

            targets = self.target_weights(
                recommendation_inputs,
                signals["allocations"],
            )

            for asset in ASSETS:
                rec = recommendation_inputs[
                    asset
                ]
                reliability = (
                    self.reliability_for(
                        signals["reliability"],
                        asset,
                        90,
                    )
                )
                current_weight = safe_float(
                    signals["allocations"].get(
                        asset,
                        0.0,
                    )
                )
                target_weight = safe_float(
                    targets.get(asset, 0.0)
                )
                evidence_status = rec[
                    "evidence_status"
                ]
                primary_reason = (
                    f"7D {rec['return_7d']:.1f}%, "
                    f"30D {rec['return_30d']:.1f}%, "
                    f"3M {rec['return_90d']:.1f}%, "
                    f"12M {rec['return_12m']:.1f}%; "
                    f"regime={regime}."
                )
                risk_warning = (
                    "Long-range prices are scenario estimates "
                    "with declining confidence."
                )
                recommendation_rows.append({
                    "run_id": self.run_id,
                    "recommendation_date": (
                        recommendation_date
                    ),
                    "asset_id": asset,
                    "current_price": safe_float(
                        prices.loc[
                            asset,
                            "current_price",
                        ]
                    ),
                    "investment_score": (
                        rec["score"]
                    ),
                    "best_action": (
                        rec["action"]
                    ),
                    "current_portfolio_weight": (
                        current_weight
                    ),
                    "best_current_portfolio_pct": (
                        target_weight * 100
                    ),
                    "weight_change_pct": (
                        (
                            target_weight
                            - current_weight
                        )
                        * 100
                    ),
                    "suggested_timeline": (
                        rec["timeline"]
                    ),
                    "entry_strategy": (
                        rec["entry_strategy"]
                    ),
                    "conviction": (
                        rec["conviction"]
                    ),
                    "forecast_confidence": (
                        rec[
                            "forecast_confidence"
                        ]
                    ),
                    "reliability_score": (
                        reliability["score"]
                    ),
                    "regime_alignment_score": (
                        regime_score
                    ),
                    "risk_score": (
                        rec["risk_score"]
                    ),
                    "short_term_signal": (
                        rec["short_signal"]
                    ),
                    "medium_term_signal": (
                        rec["medium_signal"]
                    ),
                    "long_term_signal": (
                        rec["long_signal"]
                    ),
                    "primary_reason": (
                        primary_reason
                    ),
                    "risk_warning": risk_warning,
                    "evidence_status": (
                        evidence_status
                    ),
                    "calculated_at_utc": (
                        utcnow()
                    ),
                })

            plan_rows = self.plan_rows(
                recommendation_date,
                recommendation_inputs,
                targets,
                signals["allocations"],
            )

            recommendation_frame = pd.DataFrame(
                recommendation_rows
            )
            projection_frame = pd.DataFrame(
                projection_rows
            )
            plan_frame = pd.DataFrame(
                plan_rows
            )

            target_risk = float(
                recommendation_frame[
                    "best_current_portfolio_pct"
                ].sum()
                / 100
            )
            target_cash = max(
                1 - target_risk,
                0,
            )
            highest = recommendation_frame.sort_values(
                "investment_score",
                ascending=False,
            ).iloc[0]

            positive_actions = {
                "STRONG_BUY",
                "BUY",
                "SCALE_IN",
            }
            positive_assets = int(
                recommendation_frame[
                    "best_action"
                ].isin(
                    positive_actions
                ).sum()
            )
            wait_assets = int(
                recommendation_frame[
                    "best_action"
                ].isin(
                    {"WAIT", "HOLD"}
                ).sum()
            )
            reduce_assets = int(
                recommendation_frame[
                    "best_action"
                ].isin(
                    {"REDUCE", "AVOID"}
                ).sum()
            )

            total_current_risk = float(
                sum(
                    safe_float(
                        signals[
                            "allocations"
                        ].get(
                            asset,
                            0.0,
                        )
                    )
                    for asset in ASSETS
                )
            )
            net_risk_change = (
                target_risk
                - total_current_risk
            )

            overall_action = (
                "DEPLOY_CAPITAL_GRADUALLY"
                if positive_assets >= 3
                and net_risk_change
                > float(
                    self.cfg[
                        "material_trade_weight_pct"
                    ]
                )
                / 100
                else "SELECTIVE_ACCUMULATION"
                if positive_assets > 0
                and net_risk_change > 0
                else "REMAIN_DEFENSIVE"
            )
            overall_timeline = (
                "NEXT_2_TO_6_WEEKS"
                if overall_action
                != "REMAIN_DEFENSIVE"
                else "REASSESS_IN_30_DAYS"
            )
            evidence_status = (
                "LIVE_VALIDATED"
                if (
                    recommendation_frame[
                        "evidence_status"
                    ]
                    == "LIVE_VALIDATED"
                ).all()
                else "ACCUMULATING_EVIDENCE"
            )

            summary = pd.DataFrame([{
                "run_id": self.run_id,
                "recommendation_date": (
                    recommendation_date
                ),
                "overall_action": overall_action,
                "overall_timeline": (
                    overall_timeline
                ),
                "target_cash_weight": (
                    target_cash
                ),
                "target_risk_weight": (
                    target_risk
                ),
                "highest_conviction_asset": (
                    highest["asset_id"]
                ),
                "highest_conviction_score": (
                    highest[
                        "investment_score"
                    ]
                ),
                "positive_assets": (
                    positive_assets
                ),
                "wait_assets": wait_assets,
                "reduce_assets": reduce_assets,
                "evidence_status": (
                    evidence_status
                ),
                "decision_status": (
                    "ACTIONABLE_WITH_CAUTION"
                    if positive_assets > 0
                    else "DEFENSIVE"
                ),
                "calculated_at_utc": utcnow(),
            }])

            consistency = (
                self.validate_decision_consistency(
                    summary,
                    recommendation_frame,
                    plan_frame,
                )
            )

            self.upsert(
                "m42_asset_recommendations",
                recommendation_frame,
            )
            self.upsert(
                "m42_price_projections",
                projection_frame,
            )
            self.upsert(
                "m42_portfolio_plan",
                plan_frame,
            )
            self.upsert(
                "m42_decision_summary",
                summary,
            )

            notes = (
                "Generated action-consistent asset recommendations, "
                "non-forced target weights, staged execution timelines, "
                "and bear/median/bull projections through month 48. "
                "Long-range scenario influence is confidence-discounted. "
                "Consistency validation="
                + json.dumps(
                    consistency,
                    separators=(",", ":"),
                )
            )
            self.conn.execute(
                """
                UPDATE module42_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    recommendation_rows=?,
                    projection_rows=?,
                    assets_covered=?,
                    horizons_covered=?,
                    total_target_risk_weight=?,
                    target_cash_weight=?,
                    overall_action=?,
                    overall_timeline=?,
                    evidence_status=?,
                    recommendation=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(recommendation_frame),
                    len(projection_frame),
                    recommendation_frame[
                        "asset_id"
                    ].nunique(),
                    projection_frame[
                        "horizon_label"
                    ].nunique(),
                    target_risk,
                    target_cash,
                    overall_action,
                    overall_timeline,
                    evidence_status,
                    summary.iloc[0][
                        "decision_status"
                    ],
                    notes,
                    self.run_id,
                ],
            )
            self.conn.close()
            return summary.iloc[0].to_dict()

        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module42_runs
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


def run_module42():
    return Module42Runner().run()
