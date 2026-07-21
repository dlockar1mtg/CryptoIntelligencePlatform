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
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import MODULE12_SCHEMA
from crypto_platform.module13 import MODULE13_SCHEMA

MODULE14_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module14_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    rebalance_periods INTEGER,
    validation_rows INTEGER,
    portfolio_return_pct DOUBLE,
    benchmark_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    maximum_drawdown_pct DOUBLE,
    information_ratio DOUBLE,
    promoted BOOLEAN,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS historical_score_validation(
    run_id VARCHAR,
    signal_date DATE,
    asset_id VARCHAR,
    score DOUBLE,
    rating VARCHAR,
    forward_horizon_days INTEGER,
    forward_return_pct DOUBLE,
    benchmark_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    score_rank INTEGER,
    return_rank INTEGER,
    top_half BOOLEAN,
    outperformed_benchmark BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, signal_date, asset_id, forward_horizon_days)
);

CREATE TABLE IF NOT EXISTS score_validation_summary(
    run_id VARCHAR,
    forward_horizon_days INTEGER,
    sample_count INTEGER,
    signal_dates INTEGER,
    spearman_rank_correlation DOUBLE,
    top_half_hit_rate_pct DOUBLE,
    benchmark_outperformance_rate_pct DOUBLE,
    top_score_minus_bottom_score_pct DOUBLE,
    average_forward_return_pct DOUBLE,
    average_excess_return_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, forward_horizon_days)
);

CREATE TABLE IF NOT EXISTS portfolio_backtest_periods(
    run_id VARCHAR,
    rebalance_date DATE,
    next_rebalance_date DATE,
    asset_id VARCHAR,
    target_weight DOUBLE,
    realized_return_pct DOUBLE,
    contribution_pct DOUBLE,
    turnover DOUBLE,
    transaction_cost_pct DOUBLE,
    portfolio_period_return_pct DOUBLE,
    benchmark_period_return_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, rebalance_date, asset_id)
);

CREATE TABLE IF NOT EXISTS portfolio_backtest_summary(
    run_id VARCHAR PRIMARY KEY,
    start_date DATE,
    end_date DATE,
    rebalance_periods INTEGER,
    total_return_pct DOUBLE,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    benchmark_total_return_pct DOUBLE,
    benchmark_annualized_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    tracking_error_pct DOUBLE,
    information_ratio DOUBLE,
    average_turnover_pct DOUBLE,
    transaction_cost_drag_pct DOUBLE,
    positive_period_rate_pct DOUBLE,
    benchmark_win_rate_pct DOUBLE,
    promoted BOOLEAN,
    promotion_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS portfolio_regime_validation(
    run_id VARCHAR,
    regime VARCHAR,
    periods INTEGER,
    portfolio_return_pct DOUBLE,
    benchmark_return_pct DOUBLE,
    excess_return_pct DOUBLE,
    win_rate_pct DOUBLE,
    maximum_drawdown_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, regime)
);

CREATE OR REPLACE VIEW latest_score_validation AS
SELECT x.*
FROM historical_score_validation x
JOIN (
    SELECT run_id FROM module14_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_score_validation_summary AS
SELECT x.*
FROM score_validation_summary x
JOIN (
    SELECT run_id FROM module14_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_portfolio_backtest_periods AS
SELECT x.*
FROM portfolio_backtest_periods x
JOIN (
    SELECT run_id FROM module14_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_portfolio_backtest_summary AS
SELECT x.*
FROM portfolio_backtest_summary x
JOIN (
    SELECT run_id FROM module14_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_portfolio_regime_validation AS
SELECT x.*
FROM portfolio_regime_validation x
JOIN (
    SELECT run_id FROM module14_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

CORE_IDS = [
    "bitcoin",
    "ethereum",
    "solana",
    "chainlink",
    "xrp",
    "avalanche",
]

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def score_linear(value: float | None, bad: float, good: float) -> float:
    if value is None or pd.isna(value):
        return 50.0
    return float(clamp((float(value) - bad) / (good - bad) * 100))

def score_inverse(value: float | None, good: float, bad: float) -> float:
    return score_linear(value, bad, good)

def rating(score: float) -> str:
    if score >= 82:
        return "STRONG_BUY"
    if score >= 68:
        return "BUY"
    if score >= 48:
        return "HOLD"
    if score >= 35:
        return "REDUCE"
    return "AVOID"

def safe_spearman(x: pd.Series, y: pd.Series) -> float | None:
    if len(x) < 3 or x.nunique() < 2 or y.nunique() < 2:
        return None
    return float(x.rank().corr(y.rank()))

class Module14Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA, MODULE10_SCHEMA, MODULE11_SCHEMA,
            MODULE12_SCHEMA, MODULE13_SCHEMA, MODULE14_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module14"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m14_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m14_stage"
        )
        self.conn.unregister("_m14_stage")

    def histories(self) -> dict[str, pd.Series]:
        columns = {
            row[1]
            for row in self.conn.execute(
                "PRAGMA table_info('canonical_market_daily')"
            ).fetchall()
        }
        if not columns:
            raise RuntimeError(
                "canonical_market_daily is missing. Run Module 6 sync."
            )
        frame = self.conn.execute("""
            SELECT asset_id,observation_date,price_usd
            FROM canonical_market_daily
            WHERE asset_id IN (
                'bitcoin','ethereum','solana',
                'chainlink','xrp','avalanche'
            )
              AND price_usd IS NOT NULL
            ORDER BY asset_id,observation_date
        """).fetchdf()
        if frame.empty:
            raise RuntimeError(
                "canonical_market_daily has no core-asset rows."
            )
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        return {
            asset_id: (
                group.sort_values("observation_date")
                .drop_duplicates("observation_date", keep="last")
                .set_index("observation_date")["price_usd"]
                .astype(float)
            )
            for asset_id, group in frame.groupby("asset_id")
        }

    def score_at(
        self, series: pd.Series, btc: pd.Series, date: pd.Timestamp
    ) -> dict[str, float] | None:
        lookback = int(self.config["backtest"]["lookback_days"])
        minimum = int(self.config["backtest"]["minimum_history_days"])
        s = series[series.index <= date].tail(lookback)
        if len(s) < minimum:
            return None
        returns = s.pct_change().dropna()
        current = float(s.iloc[-1])
        sma50 = float(s.tail(50).mean())
        sma200 = float(s.tail(200).mean()) if len(s) >= 200 else None

        def period_return(days: int) -> float | None:
            if len(s) <= days:
                return None
            prior = float(s.iloc[-days - 1])
            return (current / prior - 1) * 100 if prior > 0 else None

        trend = (
            score_linear((current / sma50 - 1) * 100, -20, 20) * 0.4
            + score_linear(
                (current / sma200 - 1) * 100
                if sma200 else None,
                -35,
                35,
            ) * 0.6
        )
        momentum = (
            score_linear(period_return(30), -30, 40) * 0.35
            + score_linear(period_return(90), -45, 80) * 0.40
            + score_linear(period_return(180), -60, 150) * 0.25
        )
        volatility = (
            float(returns.tail(90).std(ddof=1) * math.sqrt(365) * 100)
            if len(returns) >= 90 else None
        )
        annual_return = float(returns.tail(180).mean() * 365)
        annual_vol = float(
            returns.tail(180).std(ddof=1) * math.sqrt(365)
        )
        sharpe = (
            (annual_return - 0.04) / annual_vol
            if annual_vol > 0 else None
        )
        downside = float(
            returns.tail(180)[returns.tail(180) < 0]
            .std(ddof=1) * math.sqrt(365)
        )
        sortino = (
            (annual_return - 0.04) / downside
            if downside > 0 else None
        )
        drawdowns = s / s.cummax() - 1
        max_drawdown = float(drawdowns.tail(365).min())
        calmar = (
            annual_return / abs(max_drawdown)
            if max_drawdown < 0 else None
        )
        risk_adjusted = float(np.mean([
            score_linear(sharpe, -1, 2),
            score_linear(sortino, -1, 3),
            score_linear(calmar, -0.5, 3),
            score_inverse(volatility, 35, 180),
        ]))

        btc_window = btc[btc.index <= date].tail(181)
        aligned = pd.concat(
            [s.pct_change(), btc_window.pct_change()],
            axis=1,
            join="inner",
        ).dropna().tail(180)
        beta = 1.0
        if len(aligned) >= 60:
            variance = float(aligned.iloc[:, 1].var())
            if variance > 0:
                beta = float(
                    aligned.cov().iloc[0, 1] / variance
                )
        relative_strength = float(np.mean([
            score_inverse(abs(beta - 1), 0, 2),
            score_linear(period_return(90), -50, 100),
        ]))
        value = score_inverse(abs(max_drawdown * 100), 15, 85)
        liquidity = 75.0
        derivatives = 50.0

        weights = self.settings["module13"][
            "recommendations"
        ]["score_weights"]
        overall = (
            trend * float(weights["trend"])
            + momentum * float(weights["momentum"])
            + value * float(weights["value"])
            + risk_adjusted * float(weights["risk_adjusted"])
            + relative_strength
            * float(weights["relative_strength"])
            + liquidity * float(weights["liquidity"])
            + derivatives * float(weights["derivatives"])
        )
        risk_level = (
            "LOW" if (volatility or 999) < 55
            else "MEDIUM" if (volatility or 999) < 100
            else "HIGH"
        )
        return {
            "score": overall,
            "rating": rating(overall),
            "risk_level": risk_level,
            "volatility": volatility or 0.0,
        }

    def rebalance_dates(
        self, histories: dict[str, pd.Series]
    ) -> list[pd.Timestamp]:
        start = pd.Timestamp(
            self.config["backtest"]["start_date"]
        )
        end = min(series.index.max() for series in histories.values())
        frequency = int(
            self.config["backtest"]["rebalance_frequency_days"]
        )
        dates = []
        current = start
        btc_dates = histories["bitcoin"].index
        while current < end:
            eligible = btc_dates[btc_dates >= current]
            if len(eligible) == 0:
                break
            actual = eligible[0]
            if not dates or actual > dates[-1]:
                dates.append(actual)
            current = actual + pd.Timedelta(days=frequency)
        return dates

    def forward_return(
        self, series: pd.Series, date: pd.Timestamp, days: int
    ) -> float | None:
        start_rows = series[series.index >= date]
        if start_rows.empty:
            return None
        start_date = start_rows.index[0]
        target = start_date + pd.Timedelta(days=days)
        end_rows = series[series.index >= target]
        if end_rows.empty:
            return None
        start_price = float(series.loc[start_date])
        end_price = float(series.loc[end_rows.index[0]])
        if start_price <= 0:
            return None
        return (end_price / start_price - 1) * 100

    def validate_scores(
        self, histories: dict[str, pd.Series],
        dates: list[pd.Timestamp],
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        rows = []
        horizons = self.config["validation"][
            "forward_horizons_days"
        ]
        btc = histories["bitcoin"]

        for date in dates:
            scored = []
            for asset_id, series in histories.items():
                result = self.score_at(series, btc, date)
                if result is not None:
                    scored.append((asset_id, result))
            if len(scored) < int(
                self.config["validation"][
                    "minimum_cross_section_assets"
                ]
            ):
                continue

            for horizon in horizons:
                cross = []
                benchmark_return = self.forward_return(
                    btc, date, int(horizon)
                )
                if benchmark_return is None:
                    continue
                for asset_id, result in scored:
                    forward = self.forward_return(
                        histories[asset_id],
                        date,
                        int(horizon),
                    )
                    if forward is None:
                        continue
                    cross.append({
                        "asset_id": asset_id,
                        "score": result["score"],
                        "rating": result["rating"],
                        "forward_return": forward,
                        "benchmark_return": benchmark_return,
                    })
                if len(cross) < 4:
                    continue
                frame = pd.DataFrame(cross)
                frame["score_rank"] = (
                    frame["score"]
                    .rank(ascending=False, method="min")
                    .astype(int)
                )
                frame["return_rank"] = (
                    frame["forward_return"]
                    .rank(ascending=False, method="min")
                    .astype(int)
                )
                median_score = float(frame["score"].median())
                for _, row in frame.iterrows():
                    rows.append({
                        "run_id": self.run_id,
                        "signal_date": date.date(),
                        "asset_id": row["asset_id"],
                        "score": float(row["score"]),
                        "rating": row["rating"],
                        "forward_horizon_days": int(horizon),
                        "forward_return_pct": float(
                            row["forward_return"]
                        ),
                        "benchmark_return_pct": float(
                            row["benchmark_return"]
                        ),
                        "excess_return_pct": float(
                            row["forward_return"]
                            - row["benchmark_return"]
                        ),
                        "score_rank": int(row["score_rank"]),
                        "return_rank": int(row["return_rank"]),
                        "top_half": bool(
                            row["score"] >= median_score
                        ),
                        "outperformed_benchmark": bool(
                            row["forward_return"]
                            > row["benchmark_return"]
                        ),
                        "calculated_at_utc": utcnow(),
                    })

        validation = pd.DataFrame(rows)
        self.upsert("historical_score_validation", validation)

        summaries = []
        if not validation.empty:
            for horizon, group in validation.groupby(
                "forward_horizon_days"
            ):
                correlations = []
                top_spreads = []
                for _, date_group in group.groupby("signal_date"):
                    corr = safe_spearman(
                        date_group["score"],
                        date_group["forward_return_pct"],
                    )
                    if corr is not None:
                        correlations.append(corr)
                    ordered = date_group.sort_values("score")
                    bucket = max(1, len(ordered) // 3)
                    top_spreads.append(
                        float(
                            ordered.tail(bucket)[
                                "forward_return_pct"
                            ].mean()
                            - ordered.head(bucket)[
                                "forward_return_pct"
                            ].mean()
                        )
                    )
                summaries.append({
                    "run_id": self.run_id,
                    "forward_horizon_days": int(horizon),
                    "sample_count": len(group),
                    "signal_dates": group["signal_date"].nunique(),
                    "spearman_rank_correlation": (
                        float(np.mean(correlations))
                        if correlations else None
                    ),
                    "top_half_hit_rate_pct": float(
                        group[group["top_half"]][
                            "outperformed_benchmark"
                        ].mean() * 100
                    ),
                    "benchmark_outperformance_rate_pct": float(
                        group["outperformed_benchmark"].mean()
                        * 100
                    ),
                    "top_score_minus_bottom_score_pct": float(
                        np.mean(top_spreads)
                    ) if top_spreads else None,
                    "average_forward_return_pct": float(
                        group["forward_return_pct"].mean()
                    ),
                    "average_excess_return_pct": float(
                        group["excess_return_pct"].mean()
                    ),
                    "calculated_at_utc": utcnow(),
                })
        summary = pd.DataFrame(summaries)
        self.upsert("score_validation_summary", summary)
        return validation, summary

    def allocate(
        self, scores: pd.DataFrame
    ) -> tuple[dict[str, float], float]:
        average_score = float(scores["score"].mean())
        floor = float(
            self.config["portfolio"]["minimum_cash_weight"]
        )
        ceiling = float(
            self.config["portfolio"]["maximum_cash_weight"]
        )
        cash = clamp(
            (60 - average_score) / 60 * 100,
            floor * 100,
            ceiling * 100,
        ) / 100
        investable = 1 - cash
        penalties = self.config["portfolio"]["risk_penalties"]
        raw = np.maximum(scores["score"].to_numpy() - 30, 1)
        risk_penalty = scores["risk_level"].map(
            penalties
        ).astype(float).to_numpy()
        raw = raw * risk_penalty
        weights = raw / raw.sum() * investable
        maximum = float(
            self.config["portfolio"][
                "maximum_single_asset_weight"
            ]
        )
        for _ in range(10):
            excess = np.maximum(weights - maximum, 0).sum()
            weights = np.minimum(weights, maximum)
            uncapped = weights < maximum - 1e-9
            if excess <= 1e-9 or not uncapped.any():
                break
            weights[uncapped] += (
                excess
                * weights[uncapped]
                / weights[uncapped].sum()
            )
        return dict(zip(scores["asset_id"], weights)), cash

    def backtest_portfolio(
        self, histories: dict[str, pd.Series],
        dates: list[pd.Timestamp],
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        btc = histories["bitcoin"]
        period_rows = []
        period_summary = []
        prior_weights = {asset: 0.0 for asset in CORE_IDS}
        prior_weights["CASH"] = 1.0
        cost_rate = float(
            self.config["backtest"]["transaction_cost_bps"]
        ) / 10000

        usable_dates = dates[:-1]
        for index, date in enumerate(usable_dates):
            next_date = dates[index + 1]
            scored = []
            for asset_id in CORE_IDS:
                result = self.score_at(
                    histories[asset_id], btc, date
                )
                if result is not None:
                    scored.append({
                        "asset_id": asset_id,
                        **result,
                    })
            if len(scored) < 4:
                continue
            scores = pd.DataFrame(scored)
            weights, cash = self.allocate(scores)
            weights["CASH"] = cash
            turnover = 0.5 * sum(
                abs(
                    weights.get(asset, 0)
                    - prior_weights.get(asset, 0)
                )
                for asset in set(weights) | set(prior_weights)
            )
            transaction_cost = turnover * cost_rate

            contributions = {}
            period_returns = {}
            for asset, weight in weights.items():
                if asset == "CASH":
                    realized = 0.0
                else:
                    start_rows = histories[asset][
                        histories[asset].index >= date
                    ]
                    end_rows = histories[asset][
                        histories[asset].index >= next_date
                    ]
                    if start_rows.empty or end_rows.empty:
                        realized = 0.0
                    else:
                        realized = (
                            float(end_rows.iloc[0])
                            / float(start_rows.iloc[0])
                            - 1
                        )
                period_returns[asset] = realized
                contributions[asset] = weight * realized

            gross = sum(contributions.values())
            net = gross - transaction_cost
            benchmark_start = btc[btc.index >= date]
            benchmark_end = btc[btc.index >= next_date]
            benchmark = (
                float(benchmark_end.iloc[0])
                / float(benchmark_start.iloc[0])
                - 1
                if not benchmark_start.empty
                and not benchmark_end.empty
                else 0.0
            )
            for asset, weight in weights.items():
                period_rows.append({
                    "run_id": self.run_id,
                    "rebalance_date": date.date(),
                    "next_rebalance_date": next_date.date(),
                    "asset_id": asset,
                    "target_weight": weight,
                    "realized_return_pct": (
                        period_returns[asset] * 100
                    ),
                    "contribution_pct": (
                        contributions[asset] * 100
                    ),
                    "turnover": turnover,
                    "transaction_cost_pct": (
                        transaction_cost * 100
                    ),
                    "portfolio_period_return_pct": net * 100,
                    "benchmark_period_return_pct": benchmark * 100,
                    "calculated_at_utc": utcnow(),
                })
            period_summary.append({
                "date": date,
                "next_date": next_date,
                "portfolio_return": net,
                "benchmark_return": benchmark,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
            })
            prior_weights = weights

        periods = pd.DataFrame(period_rows)
        self.upsert("portfolio_backtest_periods", periods)
        summary_frame = pd.DataFrame(period_summary)
        if summary_frame.empty:
            return periods, pd.DataFrame(), pd.DataFrame()

        portfolio_curve = (
            1 + summary_frame["portfolio_return"]
        ).cumprod()
        benchmark_curve = (
            1 + summary_frame["benchmark_return"]
        ).cumprod()
        total_return = float(portfolio_curve.iloc[-1] - 1)
        benchmark_total = float(benchmark_curve.iloc[-1] - 1)
        years = max(
            1 / 365,
            (
                summary_frame["next_date"].max()
                - summary_frame["date"].min()
            ).days / 365.25,
        )
        annualized = (1 + total_return) ** (1 / years) - 1
        benchmark_annualized = (
            (1 + benchmark_total) ** (1 / years) - 1
        )
        frequency = 365 / float(
            self.config["backtest"][
                "rebalance_frequency_days"
            ]
        )
        annual_vol = float(
            summary_frame["portfolio_return"].std(ddof=1)
            * math.sqrt(frequency)
        )
        sharpe = annualized / annual_vol if annual_vol > 0 else None
        drawdown = portfolio_curve / portfolio_curve.cummax() - 1
        maximum_drawdown = float(drawdown.min())
        active = (
            summary_frame["portfolio_return"]
            - summary_frame["benchmark_return"]
        )
        tracking_error = float(
            active.std(ddof=1) * math.sqrt(frequency)
        )
        information_ratio = (
            (annualized - benchmark_annualized)
            / tracking_error
            if tracking_error > 0 else None
        )

        promoted = (
            information_ratio is not None
            and information_ratio
            >= float(
                self.config["promotion"][
                    "minimum_information_ratio"
                ]
            )
            and float(
                (
                    summary_frame["portfolio_return"]
                    > summary_frame["benchmark_return"]
                ).mean() * 100
            )
            >= float(
                self.config["promotion"][
                    "minimum_hit_rate_pct"
                ]
            )
        )
        reason = (
            "Portfolio methodology cleared configured validation thresholds."
            if promoted
            else "Portfolio methodology remains research-only pending stronger historical evidence."
        )
        summary = pd.DataFrame([{
            "run_id": self.run_id,
            "start_date": summary_frame["date"].min().date(),
            "end_date": summary_frame["next_date"].max().date(),
            "rebalance_periods": len(summary_frame),
            "total_return_pct": total_return * 100,
            "annualized_return_pct": annualized * 100,
            "annualized_volatility_pct": annual_vol * 100,
            "sharpe_ratio": sharpe,
            "maximum_drawdown_pct": maximum_drawdown * 100,
            "benchmark_total_return_pct": benchmark_total * 100,
            "benchmark_annualized_return_pct": (
                benchmark_annualized * 100
            ),
            "excess_return_pct": (
                total_return - benchmark_total
            ) * 100,
            "tracking_error_pct": tracking_error * 100,
            "information_ratio": information_ratio,
            "average_turnover_pct": float(
                summary_frame["turnover"].mean() * 100
            ),
            "transaction_cost_drag_pct": float(
                summary_frame["transaction_cost"].sum() * 100
            ),
            "positive_period_rate_pct": float(
                (summary_frame["portfolio_return"] > 0).mean()
                * 100
            ),
            "benchmark_win_rate_pct": float(
                (
                    summary_frame["portfolio_return"]
                    > summary_frame["benchmark_return"]
                ).mean() * 100
            ),
            "promoted": promoted,
            "promotion_reason": reason,
            "calculated_at_utc": utcnow(),
        }])
        self.upsert("portfolio_backtest_summary", summary)

        regime_rows = []
        summary_frame["regime"] = pd.cut(
            summary_frame["benchmark_return"],
            bins=[-np.inf, -0.10, -0.02, 0.02, 0.10, np.inf],
            labels=[
                "SHARP_CONTRACTION",
                "CONTRACTION",
                "SIDEWAYS",
                "EXPANSION",
                "SHARP_EXPANSION",
            ],
        ).astype(str)
        for regime, group in summary_frame.groupby("regime"):
            curve = (1 + group["portfolio_return"]).cumprod()
            dd = curve / curve.cummax() - 1
            regime_rows.append({
                "run_id": self.run_id,
                "regime": regime,
                "periods": len(group),
                "portfolio_return_pct": float(
                    ((1 + group["portfolio_return"]).prod() - 1)
                    * 100
                ),
                "benchmark_return_pct": float(
                    ((1 + group["benchmark_return"]).prod() - 1)
                    * 100
                ),
                "excess_return_pct": float(
                    (
                        (1 + group["portfolio_return"]).prod()
                        - (1 + group["benchmark_return"]).prod()
                    ) * 100
                ),
                "win_rate_pct": float(
                    (
                        group["portfolio_return"]
                        > group["benchmark_return"]
                    ).mean() * 100
                ),
                "maximum_drawdown_pct": float(dd.min() * 100),
                "calculated_at_utc": utcnow(),
            })
        regimes = pd.DataFrame(regime_rows)
        self.upsert("portfolio_regime_validation", regimes)
        return periods, summary, regimes

    def run(self) -> dict[str, Any]:
        self.conn.execute("""
            UPDATE module14_runs
            SET status='FAILED',completed_at_utc=?,
                notes=COALESCE(notes,'') ||
                      CASE WHEN COALESCE(notes,'')='' THEN '' ELSE '; ' END ||
                      'Marked failed before new validation run.'
            WHERE status='RUNNING'
        """, [utcnow()])
        self.conn.execute("""
            INSERT INTO module14_runs(
                run_id,started_at_utc,status,rebalance_periods,
                validation_rows,portfolio_return_pct,
                benchmark_return_pct,excess_return_pct,
                maximum_drawdown_pct,information_ratio,
                promoted,notes,platform_version
            ) VALUES (?,?,'RUNNING',0,0,NULL,NULL,NULL,NULL,NULL,
                      FALSE,NULL,'4.0.0')
        """, [self.run_id, self.started])

        histories = self.histories()
        missing = [
            asset for asset in CORE_IDS
            if asset not in histories
        ]
        if missing:
            self.conn.execute("""
                UPDATE module14_runs
                SET status='FAILED',completed_at_utc=?,notes=?
                WHERE run_id=?
            """, [
                utcnow(),
                f"Missing core history: {missing}",
                self.run_id,
            ])
            self.conn.close()
            raise RuntimeError(
                f"Module 14 is missing core history for: {missing}"
            )

        dates = self.rebalance_dates(histories)
        if len(dates) < int(
            self.config["validation"][
                "minimum_rebalance_periods"
            ]
        ):
            raise RuntimeError(
                f"Only {len(dates)} rebalance dates were available."
            )

        validation, score_summary = self.validate_scores(
            histories, dates
        )
        periods, portfolio_summary, regimes = (
            self.backtest_portfolio(histories, dates)
        )
        if portfolio_summary.empty:
            raise RuntimeError(
                "Portfolio backtest produced no summary."
            )
        result = portfolio_summary.iloc[0]
        notes = (
            f"score_rows={len(validation)}; "
            f"score_summaries={len(score_summary)}; "
            f"portfolio_rows={len(periods)}; "
            f"regimes={len(regimes)}."
        )
        self.conn.execute("""
            UPDATE module14_runs
            SET completed_at_utc=?,status='SUCCESS',
                rebalance_periods=?,validation_rows=?,
                portfolio_return_pct=?,benchmark_return_pct=?,
                excess_return_pct=?,maximum_drawdown_pct=?,
                information_ratio=?,promoted=?,notes=?
            WHERE run_id=?
        """, [
            utcnow(),
            int(result["rebalance_periods"]),
            len(validation),
            float(result["total_return_pct"]),
            float(result["benchmark_total_return_pct"]),
            float(result["excess_return_pct"]),
            float(result["maximum_drawdown_pct"]),
            (
                float(result["information_ratio"])
                if pd.notna(result["information_ratio"])
                else None
            ),
            bool(result["promoted"]),
            notes,
            self.run_id,
        ])
        self.conn.close()
        return {
            "run_id": self.run_id,
            "status": "SUCCESS",
            "rebalance_periods": int(
                result["rebalance_periods"]
            ),
            "validation_rows": len(validation),
            "portfolio_return_pct": float(
                result["total_return_pct"]
            ),
            "benchmark_return_pct": float(
                result["benchmark_total_return_pct"]
            ),
            "excess_return_pct": float(
                result["excess_return_pct"]
            ),
            "maximum_drawdown_pct": float(
                result["maximum_drawdown_pct"]
            ),
            "information_ratio": (
                float(result["information_ratio"])
                if pd.notna(result["information_ratio"])
                else None
            ),
            "promoted": bool(result["promoted"]),
        }

def run_module14() -> dict[str, Any]:
    return Module14Runner().run()
