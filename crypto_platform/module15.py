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
from crypto_platform.module14 import MODULE14_SCHEMA

CORE_IDS = [
    "bitcoin", "ethereum", "solana",
    "chainlink", "xrp", "avalanche",
]

MODULE15_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module15_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    variants_tested INTEGER,
    walk_forward_folds INTEGER,
    selected_variant VARCHAR,
    selected_oos_return_pct DOUBLE,
    selected_btc_excess_pct DOUBLE,
    selected_information_ratio DOUBLE,
    selected_maximum_drawdown_pct DOUBLE,
    promoted BOOLEAN,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS strategy_variant_results(
    run_id VARCHAR,
    variant_name VARCHAR,
    evaluation_scope VARCHAR,
    fold_number INTEGER,
    start_date DATE,
    end_date DATE,
    periods INTEGER,
    total_return_pct DOUBLE,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    btc_return_pct DOUBLE,
    equal_weight_return_pct DOUBLE,
    btc_eth_return_pct DOUBLE,
    btc_excess_pct DOUBLE,
    equal_weight_excess_pct DOUBLE,
    btc_eth_excess_pct DOUBLE,
    tracking_error_pct DOUBLE,
    information_ratio DOUBLE,
    benchmark_win_rate_pct DOUBLE,
    average_turnover_pct DOUBLE,
    transaction_cost_drag_pct DOUBLE,
    objective_score DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, variant_name, evaluation_scope, fold_number)
);

CREATE TABLE IF NOT EXISTS walk_forward_selection(
    run_id VARCHAR,
    fold_number INTEGER,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    selected_variant VARCHAR,
    training_objective_score DOUBLE,
    test_total_return_pct DOUBLE,
    test_btc_return_pct DOUBLE,
    test_btc_excess_pct DOUBLE,
    test_information_ratio DOUBLE,
    test_maximum_drawdown_pct DOUBLE,
    test_benchmark_win_rate_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, fold_number)
);

CREATE TABLE IF NOT EXISTS benchmark_comparison(
    run_id VARCHAR,
    benchmark_name VARCHAR,
    start_date DATE,
    end_date DATE,
    total_return_pct DOUBLE,
    annualized_return_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, benchmark_name)
);

CREATE TABLE IF NOT EXISTS calibrated_strategy_recommendation(
    run_id VARCHAR PRIMARY KEY,
    selected_variant VARCHAR,
    evidence_status VARCHAR,
    out_of_sample_folds INTEGER,
    out_of_sample_total_return_pct DOUBLE,
    out_of_sample_btc_return_pct DOUBLE,
    out_of_sample_btc_excess_pct DOUBLE,
    out_of_sample_information_ratio DOUBLE,
    out_of_sample_maximum_drawdown_pct DOUBLE,
    out_of_sample_benchmark_win_rate_pct DOUBLE,
    baseline_total_return_pct DOUBLE,
    baseline_btc_excess_pct DOUBLE,
    recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_strategy_variant_results AS
SELECT x.* FROM strategy_variant_results x
JOIN (
    SELECT run_id FROM module15_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_walk_forward_selection AS
SELECT x.* FROM walk_forward_selection x
JOIN (
    SELECT run_id FROM module15_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY fold_number;

CREATE OR REPLACE VIEW latest_benchmark_comparison AS
SELECT x.* FROM benchmark_comparison x
JOIN (
    SELECT run_id FROM module15_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);

CREATE OR REPLACE VIEW latest_calibrated_strategy_recommendation AS
SELECT x.* FROM calibrated_strategy_recommendation x
JOIN (
    SELECT run_id FROM module15_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def score_linear(value: float | None, bad: float, good: float) -> float:
    if value is None or pd.isna(value):
        return 50.0
    return float(clamp((float(value) - bad) / (good - bad) * 100))

def score_inverse(value: float | None, good: float, bad: float) -> float:
    return score_linear(value, bad, good)

def annual_metrics(returns: pd.Series, periods_per_year: float) -> dict[str, float | None]:
    if returns.empty:
        return {
            "total_return": 0.0, "annualized_return": 0.0,
            "annualized_volatility": 0.0, "sharpe": None,
            "maximum_drawdown": 0.0,
        }
    curve = (1 + returns).cumprod()
    total_return = float(curve.iloc[-1] - 1)
    years = max(len(returns) / periods_per_year, 1 / periods_per_year)
    annualized_return = (1 + total_return) ** (1 / years) - 1
    annualized_volatility = float(returns.std(ddof=1) * math.sqrt(periods_per_year))
    sharpe = (
        annualized_return / annualized_volatility
        if annualized_volatility > 0 else None
    )
    drawdown = curve / curve.cummax() - 1
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "maximum_drawdown": float(drawdown.min()),
    }

class Module15Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
            MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
            MODULE9_SCHEMA, MODULE10_SCHEMA, MODULE11_SCHEMA,
            MODULE12_SCHEMA, MODULE13_SCHEMA, MODULE14_SCHEMA,
            MODULE15_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module15"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m15_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m15_stage"
        )
        self.conn.unregister("_m15_stage")

    def histories(self) -> dict[str, pd.Series]:
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
                "canonical_market_daily has no core history. "
                "Run Module 1 and Module 6 sync."
            )
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        histories = {
            asset_id: (
                group.sort_values("observation_date")
                .drop_duplicates("observation_date", keep="last")
                .set_index("observation_date")["price_usd"]
                .astype(float)
            )
            for asset_id, group in frame.groupby("asset_id")
        }
        missing = [asset for asset in CORE_IDS if asset not in histories]
        if missing:
            raise RuntimeError(f"Missing core histories: {missing}")
        return histories

    def rebalance_dates(
        self, histories: dict[str, pd.Series]
    ) -> list[pd.Timestamp]:
        start = pd.Timestamp(self.config["research"]["start_date"])
        end = min(series.index.max() for series in histories.values())
        frequency = int(
            self.config["research"]["rebalance_frequency_days"]
        )
        btc_dates = histories["bitcoin"].index
        dates = []
        current = start
        while current <= end:
            eligible = btc_dates[btc_dates >= current]
            if len(eligible) == 0:
                break
            actual = eligible[0]
            if not dates or actual > dates[-1]:
                dates.append(actual)
            current = actual + pd.Timedelta(days=frequency)
        return dates

    def features_at(
        self, series: pd.Series, btc: pd.Series, date: pd.Timestamp
    ) -> dict[str, float | str] | None:
        minimum = int(self.config["research"]["minimum_history_days"])
        s = series[series.index <= date].tail(365)
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
                (current / sma200 - 1) * 100 if sma200 else None,
                -35, 35,
            ) * 0.6
        )
        momentum = (
            score_linear(period_return(30), -30, 40) * 0.35
            + score_linear(period_return(90), -45, 80) * 0.40
            + score_linear(period_return(180), -60, 150) * 0.25
        )
        volatility = float(
            returns.tail(90).std(ddof=1) * math.sqrt(365) * 100
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
        drawdown = s / s.cummax() - 1
        max_drawdown = float(drawdown.tail(365).min())
        calmar = (
            annual_return / abs(max_drawdown)
            if max_drawdown < 0 else None
        )
        risk_adjusted_components = [
            score_linear(sharpe, -1, 2),
            score_linear(sortino, -1, 3),
            score_linear(calmar, -0.5, 3),
        ]
        risk_adjusted_base = float(np.mean(risk_adjusted_components))

        btc_window = btc[btc.index <= date].tail(181)
        aligned = pd.concat(
            [s.pct_change(), btc_window.pct_change()],
            axis=1, join="inner",
        ).dropna().tail(180)
        beta = 1.0
        if len(aligned) >= 60:
            variance = float(aligned.iloc[:, 1].var())
            if variance > 0:
                beta = float(aligned.cov().iloc[0, 1] / variance)
        relative_strength = float(np.mean([
            score_inverse(abs(beta - 1), 0, 2),
            score_linear(period_return(90), -50, 100),
            score_linear(period_return(180), -75, 180),
        ]))
        value = score_inverse(abs(max_drawdown * 100), 15, 85)
        return {
            "trend": trend,
            "momentum": momentum,
            "value": value,
            "risk_adjusted_base": risk_adjusted_base,
            "relative_strength": relative_strength,
            "liquidity": 75.0,
            "derivatives": 50.0,
            "volatility": volatility,
            "risk_level": (
                "LOW" if volatility < 55
                else "MEDIUM" if volatility < 100
                else "HIGH"
            ),
        }

    def variant_scores(
        self, histories: dict[str, pd.Series],
        date: pd.Timestamp, variant: dict[str, Any]
    ) -> pd.DataFrame:
        btc = histories["bitcoin"]
        rows = []
        for asset_id in CORE_IDS:
            features = self.features_at(
                histories[asset_id], btc, date
            )
            if features is None:
                continue
            volatility_score = score_inverse(
                features["volatility"], 35, 180
            )
            risk_adjusted = (
                features["risk_adjusted_base"] * 0.75
                + volatility_score
                * 0.25
                * float(variant["volatility_penalty_strength"])
                + 50
                * 0.25
                * (1 - float(variant["volatility_penalty_strength"]))
            )
            overall = (
                features["trend"] * float(variant["trend_weight"])
                + features["momentum"] * float(variant["momentum_weight"])
                + features["value"] * float(variant["value_weight"])
                + risk_adjusted
                * float(variant["risk_adjusted_weight"])
                + features["relative_strength"]
                * float(variant["relative_strength_weight"])
                + features["liquidity"]
                * float(variant["liquidity_weight"])
                + features["derivatives"]
                * float(variant["derivatives_weight"])
            )
            rows.append({
                "asset_id": asset_id,
                "score": float(overall),
                "risk_level": features["risk_level"],
                "volatility": features["volatility"],
            })
        return pd.DataFrame(rows)

    def allocate(
        self, scores: pd.DataFrame, variant: dict[str, Any]
    ) -> dict[str, float]:
        average_score = float(scores["score"].mean())
        sensitivity = float(variant["cash_sensitivity"])
        max_cash = float(variant["maximum_cash_weight"])
        cash = clamp(
            ((60 - average_score) / 60 * sensitivity) * 100,
            5,
            max_cash * 100,
        ) / 100
        investable = 1 - cash

        raw = np.maximum(scores["score"].to_numpy() - 25, 1)
        base_penalties = scores["risk_level"].map({
            "LOW": 1.0,
            "MEDIUM": 0.82,
            "HIGH": 0.60,
        }).astype(float).to_numpy()
        strength = float(variant["volatility_penalty_strength"])
        penalties = 1 - (1 - base_penalties) * strength
        raw = raw * penalties
        weights = raw / raw.sum() * investable

        maximum = 0.45
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
        result = dict(zip(scores["asset_id"], weights))
        result["CASH"] = cash
        return result

    def period_asset_return(
        self, series: pd.Series,
        start: pd.Timestamp, end: pd.Timestamp
    ) -> float:
        start_rows = series[series.index >= start]
        end_rows = series[series.index >= end]
        if start_rows.empty or end_rows.empty:
            return 0.0
        return float(end_rows.iloc[0] / start_rows.iloc[0] - 1)

    def simulate(
        self, histories: dict[str, pd.Series],
        dates: list[pd.Timestamp],
        variant: dict[str, Any],
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        cost_rate = float(
            self.config["research"]["transaction_cost_bps"]
        ) / 10000
        prior = {asset: 0.0 for asset in CORE_IDS}
        prior["CASH"] = 1.0
        rows = []

        for index in range(len(dates) - 1):
            date = dates[index]
            next_date = dates[index + 1]
            if start_date is not None and date < start_date:
                continue
            if end_date is not None and next_date > end_date:
                continue
            scores = self.variant_scores(histories, date, variant)
            if len(scores) < 4:
                continue
            weights = self.allocate(scores, variant)
            turnover = 0.5 * sum(
                abs(weights.get(asset, 0) - prior.get(asset, 0))
                for asset in set(weights) | set(prior)
            )
            transaction_cost = turnover * cost_rate
            portfolio_return = -transaction_cost
            asset_returns = {}
            for asset, weight in weights.items():
                realized = (
                    0.0 if asset == "CASH"
                    else self.period_asset_return(
                        histories[asset], date, next_date
                    )
                )
                asset_returns[asset] = realized
                portfolio_return += weight * realized

            btc_return = self.period_asset_return(
                histories["bitcoin"], date, next_date
            )
            equal_weight_return = float(np.mean([
                self.period_asset_return(
                    histories[asset], date, next_date
                )
                for asset in CORE_IDS
            ]))
            btc_eth_weight = float(
                self.config["benchmarks"]["btc_eth_btc_weight"]
            )
            btc_eth_return = (
                btc_eth_weight * btc_return
                + (1 - btc_eth_weight)
                * self.period_asset_return(
                    histories["ethereum"], date, next_date
                )
            )
            rows.append({
                "date": date,
                "next_date": next_date,
                "portfolio_return": portfolio_return,
                "btc_return": btc_return,
                "equal_weight_return": equal_weight_return,
                "btc_eth_return": btc_eth_return,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
            })
            prior = weights
        return pd.DataFrame(rows)

    def objective_score(self, metrics: dict[str, float | None]) -> float:
        weights = self.config["selection"]["objective_weights"]
        information_ratio = metrics["information_ratio"]
        normalized_ir = clamp(
            ((information_ratio if information_ratio is not None else -1) + 1)
            / 3 * 100
        )
        normalized_return = clamp(
            (metrics["annualized_return"] + 0.25) / 1.0 * 100
        )
        normalized_drawdown = clamp(
            (metrics["maximum_drawdown"] + 0.80) / 0.80 * 100
        )
        normalized_win = clamp(metrics["benchmark_win_rate"])
        normalized_turnover = clamp(
            (0.50 - metrics["average_turnover"]) / 0.50 * 100
        )
        return float(
            normalized_return * float(weights["annualized_return"])
            + normalized_ir * float(weights["information_ratio"])
            + normalized_drawdown * float(weights["drawdown"])
            + normalized_win * float(weights["benchmark_win_rate"])
            + normalized_turnover * float(weights["turnover"])
        )

    def evaluate(
        self, frame: pd.DataFrame
    ) -> dict[str, float | None]:
        periods_per_year = 365 / float(
            self.config["research"]["rebalance_frequency_days"]
        )
        portfolio = annual_metrics(
            frame["portfolio_return"], periods_per_year
        )
        btc = annual_metrics(frame["btc_return"], periods_per_year)
        equal = annual_metrics(
            frame["equal_weight_return"], periods_per_year
        )
        btc_eth = annual_metrics(
            frame["btc_eth_return"], periods_per_year
        )
        active = frame["portfolio_return"] - frame["btc_return"]
        tracking_error = float(
            active.std(ddof=1) * math.sqrt(periods_per_year)
        )
        information_ratio = (
            (portfolio["annualized_return"] - btc["annualized_return"])
            / tracking_error
            if tracking_error > 0 else None
        )
        metrics = {
            "periods": len(frame),
            "total_return": portfolio["total_return"],
            "annualized_return": portfolio["annualized_return"],
            "annualized_volatility": portfolio["annualized_volatility"],
            "sharpe": portfolio["sharpe"],
            "maximum_drawdown": portfolio["maximum_drawdown"],
            "btc_return": btc["total_return"],
            "equal_weight_return": equal["total_return"],
            "btc_eth_return": btc_eth["total_return"],
            "btc_excess": portfolio["total_return"] - btc["total_return"],
            "equal_weight_excess": (
                portfolio["total_return"] - equal["total_return"]
            ),
            "btc_eth_excess": (
                portfolio["total_return"] - btc_eth["total_return"]
            ),
            "tracking_error": tracking_error,
            "information_ratio": information_ratio,
            "benchmark_win_rate": float(
                (frame["portfolio_return"] > frame["btc_return"]).mean()
                * 100
            ),
            "average_turnover": float(frame["turnover"].mean()),
            "transaction_cost_drag": float(
                frame["transaction_cost"].sum()
            ),
        }
        metrics["objective_score"] = self.objective_score(metrics)
        return metrics

    def result_row(
        self, variant_name: str, scope: str, fold: int,
        frame: pd.DataFrame, metrics: dict[str, float | None],
    ) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "variant_name": variant_name,
            "evaluation_scope": scope,
            "fold_number": fold,
            "start_date": frame["date"].min().date(),
            "end_date": frame["next_date"].max().date(),
            "periods": metrics["periods"],
            "total_return_pct": metrics["total_return"] * 100,
            "annualized_return_pct": metrics["annualized_return"] * 100,
            "annualized_volatility_pct": metrics["annualized_volatility"] * 100,
            "sharpe_ratio": metrics["sharpe"],
            "maximum_drawdown_pct": metrics["maximum_drawdown"] * 100,
            "btc_return_pct": metrics["btc_return"] * 100,
            "equal_weight_return_pct": metrics["equal_weight_return"] * 100,
            "btc_eth_return_pct": metrics["btc_eth_return"] * 100,
            "btc_excess_pct": metrics["btc_excess"] * 100,
            "equal_weight_excess_pct": metrics["equal_weight_excess"] * 100,
            "btc_eth_excess_pct": metrics["btc_eth_excess"] * 100,
            "tracking_error_pct": metrics["tracking_error"] * 100,
            "information_ratio": metrics["information_ratio"],
            "benchmark_win_rate_pct": metrics["benchmark_win_rate"],
            "average_turnover_pct": metrics["average_turnover"] * 100,
            "transaction_cost_drag_pct": (
                metrics["transaction_cost_drag"] * 100
            ),
            "objective_score": metrics["objective_score"],
            "calculated_at_utc": utcnow(),
        }

    def benchmarks(
        self, histories: dict[str, pd.Series],
        dates: list[pd.Timestamp],
    ) -> pd.DataFrame:
        neutral = {
            key: 0 for key in [
                "trend_weight", "momentum_weight", "value_weight",
                "risk_adjusted_weight", "relative_strength_weight",
                "liquidity_weight", "derivatives_weight",
            ]
        }
        neutral.update({
            "volatility_penalty_strength": 0,
            "cash_sensitivity": 0,
            "maximum_cash_weight": 0,
        })
        # Use simulation dates only to align benchmark periods.
        frame = self.simulate(
            histories, dates,
            self.config["strategy_variants"]["baseline"],
        )
        periods_per_year = 365 / float(
            self.config["research"]["rebalance_frequency_days"]
        )
        rows = []
        for name, column in [
            ("BITCOIN", "btc_return"),
            ("EQUAL_WEIGHT_CORE", "equal_weight_return"),
            ("BTC_ETH_70_30", "btc_eth_return"),
        ]:
            metrics = annual_metrics(frame[column], periods_per_year)
            rows.append({
                "run_id": self.run_id,
                "benchmark_name": name,
                "start_date": frame["date"].min().date(),
                "end_date": frame["next_date"].max().date(),
                "total_return_pct": metrics["total_return"] * 100,
                "annualized_return_pct": metrics["annualized_return"] * 100,
                "annualized_volatility_pct": (
                    metrics["annualized_volatility"] * 100
                ),
                "sharpe_ratio": metrics["sharpe"],
                "maximum_drawdown_pct": (
                    metrics["maximum_drawdown"] * 100
                ),
                "calculated_at_utc": utcnow(),
            })
        result = pd.DataFrame(rows)
        self.upsert("benchmark_comparison", result)
        return result

    def walk_forward_windows(
        self, dates: list[pd.Timestamp]
    ) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
        training_months = int(
            self.config["walk_forward"]["training_months"]
        )
        testing_months = int(
            self.config["walk_forward"]["testing_months"]
        )
        step_months = int(
            self.config["walk_forward"]["step_months"]
        )
        first = dates[0]
        last = dates[-1]
        windows = []
        test_start = first + pd.DateOffset(months=training_months)
        while True:
            train_start = test_start - pd.DateOffset(months=training_months)
            train_end = test_start
            test_end = test_start + pd.DateOffset(months=testing_months)
            if test_end > last:
                break
            windows.append(
                (pd.Timestamp(train_start), pd.Timestamp(train_end),
                 pd.Timestamp(test_start), pd.Timestamp(test_end))
            )
            test_start = test_start + pd.DateOffset(months=step_months)
        return windows

    def aggregate_oos(
        self, selections: pd.DataFrame
    ) -> dict[str, float | None]:
        if selections.empty:
            return {}
        # Chain fold returns; folds are non-overlapping under default setup.
        total_return = float(
            np.prod(1 + selections["test_total_return_pct"] / 100) - 1
        )
        btc_return = float(
            np.prod(1 + selections["test_btc_return_pct"] / 100) - 1
        )
        return {
            "folds": len(selections),
            "total_return": total_return,
            "btc_return": btc_return,
            "btc_excess": total_return - btc_return,
            "information_ratio": float(
                selections["test_information_ratio"].dropna().mean()
            ) if selections["test_information_ratio"].notna().any()
            else None,
            "maximum_drawdown": float(
                selections["test_maximum_drawdown_pct"].min() / 100
            ),
            "benchmark_win_rate": float(
                selections["test_benchmark_win_rate_pct"].mean()
            ),
        }

    def run(self) -> dict[str, Any]:
        self.conn.execute("""
            UPDATE module15_runs
            SET status='FAILED',completed_at_utc=?,
                notes=COALESCE(notes,'') ||
                    CASE WHEN COALESCE(notes,'')='' THEN '' ELSE '; ' END ||
                    'Marked failed before new v4.0 research run.'
            WHERE status='RUNNING'
        """, [utcnow()])
        self.conn.execute("""
            INSERT INTO module15_runs(
                run_id,started_at_utc,status,variants_tested,
                walk_forward_folds,selected_variant,
                selected_oos_return_pct,selected_btc_excess_pct,
                selected_information_ratio,
                selected_maximum_drawdown_pct,promoted,
                notes,platform_version
            ) VALUES (?,?,'RUNNING',0,0,NULL,NULL,NULL,NULL,NULL,
                      FALSE,NULL,'4.0.0')
        """, [self.run_id, self.started])

        try:
            histories = self.histories()
            dates = self.rebalance_dates(histories)
            variants = self.config["strategy_variants"]
            all_rows = []

            # Full-sample descriptive comparison only.
            full_metrics = {}
            for variant_name, variant in variants.items():
                frame = self.simulate(histories, dates, variant)
                metrics = self.evaluate(frame)
                full_metrics[variant_name] = metrics
                all_rows.append(
                    self.result_row(
                        variant_name, "FULL_SAMPLE", 0,
                        frame, metrics,
                    )
                )

            windows = self.walk_forward_windows(dates)
            minimum_folds = int(
                self.config["walk_forward"]["minimum_folds"]
            )
            if len(windows) < minimum_folds:
                raise RuntimeError(
                    f"Only {len(windows)} walk-forward folds were available; "
                    f"{minimum_folds} required."
                )

            selection_rows = []
            for fold_number, (
                train_start, train_end, test_start, test_end
            ) in enumerate(windows, start=1):
                training_results = []
                test_frames = {}
                for variant_name, variant in variants.items():
                    train_frame = self.simulate(
                        histories, dates, variant,
                        start_date=train_start,
                        end_date=train_end,
                    )
                    test_frame = self.simulate(
                        histories, dates, variant,
                        start_date=test_start,
                        end_date=test_end,
                    )
                    if train_frame.empty or test_frame.empty:
                        continue
                    train_metrics = self.evaluate(train_frame)
                    test_metrics = self.evaluate(test_frame)
                    training_results.append({
                        "variant_name": variant_name,
                        "objective_score": train_metrics["objective_score"],
                    })
                    test_frames[variant_name] = (
                        test_frame, test_metrics
                    )
                    all_rows.append(self.result_row(
                        variant_name, "TRAIN", fold_number,
                        train_frame, train_metrics,
                    ))
                    all_rows.append(self.result_row(
                        variant_name, "TEST", fold_number,
                        test_frame, test_metrics,
                    ))

                if not training_results:
                    continue
                selected = max(
                    training_results,
                    key=lambda item: item["objective_score"]
                )
                selected_name = selected["variant_name"]
                test_frame, test_metrics = test_frames[selected_name]
                selection_rows.append({
                    "run_id": self.run_id,
                    "fold_number": fold_number,
                    "training_start_date": train_start.date(),
                    "training_end_date": train_end.date(),
                    "testing_start_date": test_start.date(),
                    "testing_end_date": test_end.date(),
                    "selected_variant": selected_name,
                    "training_objective_score": (
                        selected["objective_score"]
                    ),
                    "test_total_return_pct": (
                        test_metrics["total_return"] * 100
                    ),
                    "test_btc_return_pct": (
                        test_metrics["btc_return"] * 100
                    ),
                    "test_btc_excess_pct": (
                        test_metrics["btc_excess"] * 100
                    ),
                    "test_information_ratio": (
                        test_metrics["information_ratio"]
                    ),
                    "test_maximum_drawdown_pct": (
                        test_metrics["maximum_drawdown"] * 100
                    ),
                    "test_benchmark_win_rate_pct": (
                        test_metrics["benchmark_win_rate"]
                    ),
                    "calculated_at_utc": utcnow(),
                })

            variant_results = pd.DataFrame(all_rows)
            selections = pd.DataFrame(selection_rows)
            self.upsert("strategy_variant_results", variant_results)
            self.upsert("walk_forward_selection", selections)
            benchmarks = self.benchmarks(histories, dates)

            oos = self.aggregate_oos(selections)
            if not oos:
                raise RuntimeError(
                    "Walk-forward selection produced no out-of-sample results."
                )

            selected_counts = (
                selections["selected_variant"].value_counts()
            )
            selected_variant = selected_counts.index[0]
            baseline = full_metrics["baseline"]

            thresholds = self.config["selection"]
            promoted = (
                len(selections) >= int(
                    thresholds["minimum_test_folds"]
                )
                and oos["information_ratio"] is not None
                and oos["information_ratio"] >= float(
                    thresholds["minimum_information_ratio"]
                )
                and oos["benchmark_win_rate"] >= float(
                    thresholds["minimum_benchmark_win_rate_pct"]
                )
                and oos["maximum_drawdown"] * 100 >= float(
                    thresholds["maximum_drawdown_pct"]
                )
            )
            evidence_status = (
                "PROMOTION_CANDIDATE"
                if promoted else "RESEARCH_ONLY"
            )
            recommendation = (
                f"Promote {selected_variant} to shadow-live testing; "
                "do not replace the live methodology automatically."
                if promoted
                else "Retain the current live methodology while recalibrating; "
                "no variant cleared all out-of-sample thresholds."
            )

            recommendation_frame = pd.DataFrame([{
                "run_id": self.run_id,
                "selected_variant": selected_variant,
                "evidence_status": evidence_status,
                "out_of_sample_folds": int(oos["folds"]),
                "out_of_sample_total_return_pct": (
                    oos["total_return"] * 100
                ),
                "out_of_sample_btc_return_pct": (
                    oos["btc_return"] * 100
                ),
                "out_of_sample_btc_excess_pct": (
                    oos["btc_excess"] * 100
                ),
                "out_of_sample_information_ratio": (
                    oos["information_ratio"]
                ),
                "out_of_sample_maximum_drawdown_pct": (
                    oos["maximum_drawdown"] * 100
                ),
                "out_of_sample_benchmark_win_rate_pct": (
                    oos["benchmark_win_rate"]
                ),
                "baseline_total_return_pct": (
                    baseline["total_return"] * 100
                ),
                "baseline_btc_excess_pct": (
                    baseline["btc_excess"] * 100
                ),
                "recommendation": recommendation,
                "calculated_at_utc": utcnow(),
            }])
            self.upsert(
                "calibrated_strategy_recommendation",
                recommendation_frame,
            )

            notes = (
                f"variants={len(variants)}; folds={len(selections)}; "
                f"variant_rows={len(variant_results)}; "
                f"benchmarks={len(benchmarks)}."
            )
            self.conn.execute("""
                UPDATE module15_runs
                SET completed_at_utc=?,status='SUCCESS',
                    variants_tested=?,walk_forward_folds=?,
                    selected_variant=?,selected_oos_return_pct=?,
                    selected_btc_excess_pct=?,
                    selected_information_ratio=?,
                    selected_maximum_drawdown_pct=?,
                    promoted=?,notes=?
                WHERE run_id=?
            """, [
                utcnow(), len(variants), len(selections),
                selected_variant,
                oos["total_return"] * 100,
                oos["btc_excess"] * 100,
                oos["information_ratio"],
                oos["maximum_drawdown"] * 100,
                promoted, notes, self.run_id,
            ])
            self.conn.close()
            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "variants_tested": len(variants),
                "walk_forward_folds": len(selections),
                "selected_variant": selected_variant,
                "oos_return_pct": oos["total_return"] * 100,
                "oos_btc_return_pct": oos["btc_return"] * 100,
                "oos_excess_pct": oos["btc_excess"] * 100,
                "information_ratio": oos["information_ratio"],
                "maximum_drawdown_pct": (
                    oos["maximum_drawdown"] * 100
                ),
                "promoted": promoted,
            }
        except Exception as exc:
            try:
                self.conn.execute("""
                    UPDATE module15_runs
                    SET completed_at_utc=?,status='FAILED',notes=?
                    WHERE run_id=?
                """, [utcnow(), str(exc)[:1000], self.run_id])
                self.conn.close()
            finally:
                pass
            raise

def run_module15() -> dict[str, Any]:
    return Module15Runner().run()
