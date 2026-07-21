from __future__ import annotations

import itertools
import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.module32 import MODULE32_SCHEMA
from crypto_platform.ml.classes import canonical_classes
from crypto_platform.ml.validation import validate_probability_matrix

MODULE33_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module33_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module32_run_id VARCHAR,
    source_module30_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    candidate_rows INTEGER,
    daily_rows INTEGER,
    cost_sensitivity_rows INTEGER,
    drift_rows INTEGER,
    selected_candidate_id VARCHAR,
    selected_strategy VARCHAR,
    annualized_turnover_pct DOUBLE,
    selected_sharpe DOUBLE,
    selected_max_drawdown_pct DOUBLE,
    btc_sharpe DOUBLE,
    btc_max_drawdown_pct DOUBLE,
    adjusted_drift_status VARCHAR,
    validation_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m33_probability_regularization(
    run_id VARCHAR,
    observation_date DATE,
    raw_top_probability DOUBLE,
    regularized_top_probability DOUBLE,
    raw_entropy DOUBLE,
    regularized_entropy DOUBLE,
    temperature DOUBLE,
    probability_floor DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m33_adjusted_probability_drift(
    run_id VARCHAR,
    window_end_date DATE,
    window_days INTEGER,
    observations INTEGER,
    rolling_reference_days INTEGER,
    mean_top_probability DOUBLE,
    mean_entropy DOUBLE,
    probability_psi DOUBLE,
    entropy_psi DOUBLE,
    confidence_shift_pct DOUBLE,
    disagreement_rate_pct DOUBLE,
    drift_score DOUBLE,
    drift_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, window_end_date, window_days)
);

CREATE TABLE IF NOT EXISTS m33_decision_candidates(
    run_id VARCHAR,
    candidate_id VARCHAR,
    temperature DOUBLE,
    probability_floor DOUBLE,
    switch_margin DOUBLE,
    minimum_hold_days INTEGER,
    confidence_floor DOUBLE,
    maximum_risk_exposure DOUBLE,
    observations INTEGER,
    cumulative_return_pct DOUBLE,
    cagr_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    calmar_ratio DOUBLE,
    annualized_turnover_pct DOUBLE,
    total_transaction_cost_pct DOUBLE,
    switch_count INTEGER,
    objective_score DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS m33_optimized_daily(
    run_id VARCHAR,
    observation_date DATE,
    candidate_id VARCHAR,
    raw_regime VARCHAR,
    held_regime VARCHAR,
    raw_probability DOUBLE,
    regularized_probability DOUBLE,
    confidence_multiplier DOUBLE,
    target_risk_exposure DOUBLE,
    daily_return DOUBLE,
    cumulative_return DOUBLE,
    turnover DOUBLE,
    transaction_cost DOUBLE,
    switched BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m33_cost_sensitivity(
    run_id VARCHAR,
    transaction_cost_bps DOUBLE,
    observations INTEGER,
    cumulative_return_pct DOUBLE,
    cagr_pct DOUBLE,
    sharpe_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    annualized_turnover_pct DOUBLE,
    total_transaction_cost_pct DOUBLE,
    passed BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, transaction_cost_bps)
);

CREATE TABLE IF NOT EXISTS m33_benchmark_comparison(
    run_id VARCHAR,
    strategy_key VARCHAR,
    observations INTEGER,
    cumulative_return_pct DOUBLE,
    cagr_pct DOUBLE,
    annualized_volatility_pct DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    maximum_drawdown_pct DOUBLE,
    calmar_ratio DOUBLE,
    annualized_turnover_pct DOUBLE,
    total_transaction_cost_pct DOUBLE,
    selected BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, strategy_key)
);

CREATE TABLE IF NOT EXISTS m33_validation_summary(
    run_id VARCHAR PRIMARY KEY,
    selected_candidate_id VARCHAR,
    temperature DOUBLE,
    switch_margin DOUBLE,
    minimum_hold_days INTEGER,
    confidence_floor DOUBLE,
    maximum_risk_exposure DOUBLE,
    adjusted_drift_status VARCHAR,
    optimized_sharpe DOUBLE,
    btc_sharpe DOUBLE,
    optimized_max_drawdown_pct DOUBLE,
    btc_max_drawdown_pct DOUBLE,
    optimized_turnover_pct DOUBLE,
    cost_sensitivity_pass_rate_pct DOUBLE,
    validation_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m33_probability_regularization AS
SELECT * FROM m33_probability_regularization
WHERE run_id=(
    SELECT run_id FROM module33_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_m33_adjusted_probability_drift AS
SELECT * FROM m33_adjusted_probability_drift
WHERE run_id=(
    SELECT run_id FROM module33_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY window_end_date DESC, window_days;

CREATE OR REPLACE VIEW latest_m33_decision_candidates AS
SELECT * FROM m33_decision_candidates
WHERE run_id=(
    SELECT run_id FROM module33_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY selected DESC, objective_score DESC;

CREATE OR REPLACE VIEW latest_m33_optimized_daily AS
SELECT * FROM m33_optimized_daily
WHERE run_id=(
    SELECT run_id FROM module33_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_m33_cost_sensitivity AS
SELECT * FROM m33_cost_sensitivity
WHERE run_id=(
    SELECT run_id FROM module33_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY transaction_cost_bps;

CREATE OR REPLACE VIEW latest_m33_benchmark_comparison AS
SELECT * FROM m33_benchmark_comparison
WHERE run_id=(
    SELECT run_id FROM module33_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY selected DESC, sharpe_ratio DESC;

CREATE OR REPLACE VIEW latest_m33_validation_summary AS
SELECT * FROM m33_validation_summary
WHERE run_id=(
    SELECT run_id FROM module33_runs
    ORDER BY started_at_utc DESC LIMIT 1
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

REGIME_WEIGHTS = {
    "LIQUIDITY_EXPANSION": np.array([.30, .24, .16, .10, .10, .10]),
    "MOMENTUM_BULL": np.array([.30, .25, .18, .10, .09, .08]),
    "RECOVERY": np.array([.28, .24, .17, .11, .10, .10]),
    "RANGE_BOUND": np.array([.42, .28, .08, .08, .08, .06]),
    "MACRO_STRESS": np.array([.60, .24, .04, .04, .04, .04]),
    "VOLATILITY_SHOCK": np.array([.70, .20, .025, .025, .025, .025]),
}

REGIME_RISK = {
    "LIQUIDITY_EXPANSION": 1.00,
    "MOMENTUM_BULL": 1.00,
    "RECOVERY": .80,
    "RANGE_BOUND": .45,
    "MACRO_STRESS": .18,
    "VOLATILITY_SHOCK": .08,
}


def utcnow():
    return datetime.now(timezone.utc)


def entropy(matrix):
    matrix = np.clip(np.asarray(matrix, dtype=float), 1e-12, 1.0)
    return -np.sum(matrix * np.log(matrix), axis=1)


def regularize_probabilities(matrix, temperature, probability_floor):
    matrix = np.clip(np.asarray(matrix, dtype=float), 1e-12, 1.0)
    logits = np.log(matrix) / max(float(temperature), .05)
    logits -= logits.max(axis=1, keepdims=True)
    scaled = np.exp(np.clip(logits, -50, 50))
    scaled /= scaled.sum(axis=1, keepdims=True)
    scaled = np.maximum(scaled, float(probability_floor))
    scaled /= scaled.sum(axis=1, keepdims=True)
    return scaled


def population_stability_index(expected, actual, bins=8):
    expected = pd.Series(expected).dropna().astype(float)
    actual = pd.Series(actual).dropna().astype(float)
    if len(expected) < 30 or len(actual) < 15:
        return 0.0

    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(expected, quantiles))
    if len(edges) < 3:
        return 0.0

    edges[0] = -np.inf
    edges[-1] = np.inf
    expected_count, _ = np.histogram(expected, bins=edges)
    actual_count, _ = np.histogram(actual, bins=edges)
    expected_pct = np.clip(
        expected_count / max(expected_count.sum(), 1),
        1e-5,
        None,
    )
    actual_pct = np.clip(
        actual_count / max(actual_count.sum(), 1),
        1e-5,
        None,
    )
    return float(np.sum(
        (actual_pct - expected_pct)
        * np.log(actual_pct / expected_pct)
    ))


def performance_metrics(strategy_return, turnover, transaction_cost):
    strategy_return = pd.Series(strategy_return).dropna()
    turnover = pd.Series(turnover).reindex(strategy_return.index).fillna(0)
    transaction_cost = (
        pd.Series(transaction_cost)
        .reindex(strategy_return.index)
        .fillna(0)
    )
    cumulative = (1 + strategy_return).cumprod()
    years = max(len(strategy_return) / 365, 1 / 365)
    cagr = float(cumulative.iloc[-1] ** (1 / years) - 1)
    volatility = float(strategy_return.std() * math.sqrt(365))
    sharpe = (
        float(
            strategy_return.mean()
            / strategy_return.std()
            * math.sqrt(365)
        )
        if strategy_return.std() > 0
        else 0.0
    )
    downside = strategy_return[strategy_return < 0].std()
    sortino = (
        float(
            strategy_return.mean()
            / downside
            * math.sqrt(365)
        )
        if downside is not None
        and not pd.isna(downside)
        and downside > 0
        else 0.0
    )
    drawdown = cumulative / cumulative.cummax() - 1
    maximum_drawdown = float(drawdown.min())
    calmar = (
        float(cagr / abs(maximum_drawdown))
        if maximum_drawdown < 0
        else 0.0
    )
    return {
        "cumulative": cumulative,
        "cumulative_return_pct": float(
            (cumulative.iloc[-1] - 1) * 100
        ),
        "cagr_pct": cagr * 100,
        "annualized_volatility_pct": volatility * 100,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "maximum_drawdown_pct": maximum_drawdown * 100,
        "calmar_ratio": calmar,
        "annualized_turnover_pct": float(
            turnover.mean() * 365 * 100
        ),
        "total_transaction_cost_pct": float(
            transaction_cost.sum() * 100
        ),
    }


class Module33Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE30_SCHEMA)
        self.conn.execute(MODULE32_SCHEMA)
        self.conn.execute(MODULE33_SCHEMA)
        self.cfg = self.settings["module33"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        self.classes = canonical_classes()

        row = self.conn.execute(
            """
            SELECT run_id, source_module30_run_id
            FROM module32_runs
            WHERE status='SUCCESS'
            ORDER BY started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError(
                "No successful Module 32 run is available."
            )
        self.source_m32 = str(row[0])
        self.source_m30 = str(row[1])

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m33_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m33_stage"
        )
        self.conn.unregister("_m33_stage")

    def probabilities(self):
        frame = self.conn.execute(
            """
            SELECT observation_date, regime, probability
            FROM clean_probability_history
            WHERE run_id=?
            ORDER BY observation_date, regime
            """,
            [self.source_m30],
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        matrix = frame.pivot(
            index="observation_date",
            columns="regime",
            values="probability",
        ).reindex(columns=self.classes)
        validate_probability_matrix(
            matrix.to_numpy(),
            self.classes,
        )
        return matrix.sort_index()

    def disagreement(self):
        history = self.conn.execute(
            """
            SELECT observation_date, model_agreement
            FROM clean_regime_history
            WHERE run_id=?
            ORDER BY observation_date
            """,
            [self.source_m30],
        ).fetchdf()
        history["observation_date"] = pd.to_datetime(
            history["observation_date"]
        )
        return history.set_index("observation_date")[
            "model_agreement"
        ]

    def prices(self):
        frame = self.conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
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
        return frame.pivot(
            index="observation_date",
            columns="asset_id",
            values="price_usd",
        ).reindex(columns=ASSETS).sort_index()

    def adjusted_drift(
        self,
        regularized,
        disagreement,
    ):
        reference_days = int(
            self.cfg["drift"]["rolling_reference_days"]
        )
        windows = [
            int(value)
            for value in self.cfg["drift"]["window_days"]
        ]
        top = regularized.max(axis=1)
        ent = pd.Series(
            entropy(regularized.to_numpy()),
            index=regularized.index,
        )
        rows = []

        for window in windows:
            for end in range(
                reference_days + window,
                len(regularized) + 1,
                window,
            ):
                actual = regularized.iloc[
                    end - window:end
                ]
                reference = regularized.iloc[
                    end - window - reference_days:
                    end - window
                ]
                actual_top = actual.max(axis=1)
                reference_top = reference.max(axis=1)
                actual_entropy = ent.reindex(actual.index)
                reference_entropy = ent.reindex(reference.index)
                probability_psi = population_stability_index(
                    reference_top,
                    actual_top,
                )
                entropy_psi = population_stability_index(
                    reference_entropy,
                    actual_entropy,
                )
                confidence_shift = float(
                    (
                        actual_top.mean()
                        / max(reference_top.mean(), 1e-9)
                        - 1
                    )
                    * 100
                )
                block_agreement = disagreement.reindex(
                    actual.index
                )
                disagreement_rate = float(
                    (block_agreement < .55).mean() * 100
                )
                drift_score = float(
                    .35 * min(probability_psi / .25, 1)
                    + .25 * min(entropy_psi / .25, 1)
                    + .20 * min(abs(confidence_shift) / 30, 1)
                    + .20 * min(disagreement_rate / 50, 1)
                )
                if drift_score >= .75:
                    status = "CRITICAL"
                elif drift_score >= .45:
                    status = "WARNING"
                else:
                    status = "STABLE"

                rows.append({
                    "run_id": self.run_id,
                    "window_end_date": actual.index.max().date(),
                    "window_days": window,
                    "observations": len(actual),
                    "rolling_reference_days": reference_days,
                    "mean_top_probability": float(
                        actual_top.mean()
                    ),
                    "mean_entropy": float(
                        actual_entropy.mean()
                    ),
                    "probability_psi": probability_psi,
                    "entropy_psi": entropy_psi,
                    "confidence_shift_pct": confidence_shift,
                    "disagreement_rate_pct": disagreement_rate,
                    "drift_score": drift_score,
                    "drift_status": status,
                    "calculated_at_utc": utcnow(),
                })

        return pd.DataFrame(rows)

    def decision_path(
        self,
        probabilities,
        returns,
        parameters,
        transaction_cost_bps,
    ):
        temperature = parameters["temperature"]
        floor = parameters["probability_floor"]
        margin = parameters["switch_margin"]
        minimum_hold = parameters["minimum_hold_days"]
        confidence_floor = parameters["confidence_floor"]
        max_risk = parameters["maximum_risk_exposure"]

        regularized = regularize_probabilities(
            probabilities.to_numpy(),
            temperature,
            floor,
        )
        regularized = pd.DataFrame(
            regularized,
            index=probabilities.index,
            columns=self.classes,
        )

        current_regime = None
        hold_days = 0
        weights = []
        rows = []

        for date, probability_row in regularized.iterrows():
            order = np.argsort(-probability_row.to_numpy())
            raw_regime = self.classes[order[0]]
            raw_probability = float(
                probability_row.iloc[order[0]]
            )

            switched = False
            if current_regime is None:
                current_regime = raw_regime
                switched = True
                hold_days = 0
            else:
                current_probability = float(
                    probability_row[current_regime]
                )
                improvement = (
                    raw_probability - current_probability
                )
                if (
                    raw_regime != current_regime
                    and hold_days >= minimum_hold
                    and improvement >= margin
                ):
                    current_regime = raw_regime
                    switched = True
                    hold_days = 0
                else:
                    hold_days += 1

            held_probability = float(
                probability_row[current_regime]
            )
            confidence_multiplier = np.clip(
                (
                    held_probability - confidence_floor
                )
                / max(1 - confidence_floor, 1e-9),
                0,
                1,
            )
            risk_exposure = float(
                max_risk
                * REGIME_RISK[current_regime]
                * confidence_multiplier
            )
            target = (
                REGIME_WEIGHTS[current_regime]
                * risk_exposure
            )
            weights.append(target)
            rows.append({
                "observation_date": date,
                "raw_regime": raw_regime,
                "held_regime": current_regime,
                "raw_probability": float(
                    probabilities.loc[date].max()
                ),
                "regularized_probability": held_probability,
                "confidence_multiplier": float(
                    confidence_multiplier
                ),
                "target_risk_exposure": risk_exposure,
                "switched": switched,
            })

        weights = pd.DataFrame(
            weights,
            index=regularized.index,
            columns=ASSETS,
        )
        held = weights.shift(1).fillna(weights.iloc[0])
        turnover = (
            weights.diff().abs().sum(axis=1)
            .fillna(weights.iloc[0].abs().sum())
        )
        transaction_cost = turnover * (
            float(transaction_cost_bps) / 10000
        )
        strategy_return = (
            held * returns.reindex(weights.index)
        ).sum(axis=1) - transaction_cost
        metrics = performance_metrics(
            strategy_return,
            turnover,
            transaction_cost,
        )
        path = pd.DataFrame(rows).set_index(
            "observation_date"
        )
        path["daily_return"] = strategy_return
        path["cumulative_return"] = metrics[
            "cumulative"
        ]
        path["turnover"] = turnover
        path["transaction_cost"] = transaction_cost
        return regularized, path, metrics

    def candidate_search(self, probabilities, returns):
        cfg = self.cfg["optimization"]
        parameter_grid = itertools.product(
            cfg["temperatures"],
            cfg["probability_floors"],
            cfg["switch_margins"],
            cfg["minimum_hold_days"],
            cfg["confidence_floors"],
            cfg["maximum_risk_exposures"],
        )
        rows = []
        paths = {}
        regularized_cache = {}
        cost_bps = float(
            self.cfg["transaction_cost_bps"]
        )

        for index, values in enumerate(
            parameter_grid,
            start=1,
        ):
            parameters = {
                "temperature": float(values[0]),
                "probability_floor": float(values[1]),
                "switch_margin": float(values[2]),
                "minimum_hold_days": int(values[3]),
                "confidence_floor": float(values[4]),
                "maximum_risk_exposure": float(values[5]),
            }
            candidate_id = f"C{index:04d}"
            regularized, path, metrics = self.decision_path(
                probabilities,
                returns,
                parameters,
                cost_bps,
            )
            switch_count = int(path["switched"].sum())
            turnover_penalty = max(
                metrics["annualized_turnover_pct"]
                - float(
                    self.cfg["validation"][
                        "maximum_turnover_pct"
                    ]
                ),
                0,
            )
            objective = float(
                55 * metrics["sharpe_ratio"]
                + 20 * metrics["calmar_ratio"]
                + .22 * metrics["cagr_pct"]
                - .10 * abs(
                    metrics["maximum_drawdown_pct"]
                )
                - .03 * turnover_penalty
                - .40 * metrics[
                    "total_transaction_cost_pct"
                ]
            )
            rows.append({
                "run_id": self.run_id,
                "candidate_id": candidate_id,
                **parameters,
                "observations": len(path),
                "cumulative_return_pct": metrics[
                    "cumulative_return_pct"
                ],
                "cagr_pct": metrics["cagr_pct"],
                "annualized_volatility_pct": metrics[
                    "annualized_volatility_pct"
                ],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "sortino_ratio": metrics["sortino_ratio"],
                "maximum_drawdown_pct": metrics[
                    "maximum_drawdown_pct"
                ],
                "calmar_ratio": metrics["calmar_ratio"],
                "annualized_turnover_pct": metrics[
                    "annualized_turnover_pct"
                ],
                "total_transaction_cost_pct": metrics[
                    "total_transaction_cost_pct"
                ],
                "switch_count": switch_count,
                "objective_score": objective,
                "selected": False,
                "calculated_at_utc": utcnow(),
            })
            paths[candidate_id] = path
            regularized_cache[candidate_id] = regularized

        candidates = pd.DataFrame(rows)
        selected_index = candidates[
            "objective_score"
        ].idxmax()
        candidates.loc[selected_index, "selected"] = True
        selected_id = str(
            candidates.loc[selected_index, "candidate_id"]
        )
        return (
            candidates,
            selected_id,
            paths[selected_id],
            regularized_cache[selected_id],
        )

    def benchmark_rows(
        self,
        returns,
        selected_path,
        selected_candidate_id,
    ):
        common = selected_path.index
        cost_bps = float(
            self.cfg["transaction_cost_bps"]
        )

        selected_metrics = performance_metrics(
            selected_path["daily_return"],
            selected_path["turnover"],
            selected_path["transaction_cost"],
        )

        btc_return = returns.reindex(common)[
            "bitcoin"
        ].fillna(0)
        zero = pd.Series(0.0, index=common)
        btc_metrics = performance_metrics(
            btc_return,
            zero,
            zero,
        )

        equal_return = returns.reindex(
            common
        ).fillna(0).mean(axis=1)
        equal_metrics = performance_metrics(
            equal_return,
            zero,
            zero,
        )

        rows = []
        for key, metrics, selected in [
            (
                "OPTIMIZED_DECISION",
                selected_metrics,
                True,
            ),
            ("BTC_BUY_HOLD", btc_metrics, False),
            ("EQUAL_WEIGHT_6", equal_metrics, False),
        ]:
            rows.append({
                "run_id": self.run_id,
                "strategy_key": key,
                "observations": len(common),
                "cumulative_return_pct": metrics[
                    "cumulative_return_pct"
                ],
                "cagr_pct": metrics["cagr_pct"],
                "annualized_volatility_pct": metrics[
                    "annualized_volatility_pct"
                ],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "sortino_ratio": metrics["sortino_ratio"],
                "maximum_drawdown_pct": metrics[
                    "maximum_drawdown_pct"
                ],
                "calmar_ratio": metrics["calmar_ratio"],
                "annualized_turnover_pct": metrics[
                    "annualized_turnover_pct"
                ],
                "total_transaction_cost_pct": metrics[
                    "total_transaction_cost_pct"
                ],
                "selected": selected,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def cost_sensitivity(
        self,
        probabilities,
        returns,
        selected_parameters,
        btc_metrics,
    ):
        rows = []
        maximum_turnover = float(
            self.cfg["validation"][
                "maximum_turnover_pct"
            ]
        )
        for cost in self.cfg["cost_sensitivity_bps"]:
            _, path, metrics = self.decision_path(
                probabilities,
                returns,
                selected_parameters,
                float(cost),
            )
            passed = bool(
                metrics["sharpe_ratio"]
                >= btc_metrics["sharpe_ratio"]
                and metrics["maximum_drawdown_pct"]
                > btc_metrics["maximum_drawdown_pct"]
                and metrics["annualized_turnover_pct"]
                <= maximum_turnover
            )
            rows.append({
                "run_id": self.run_id,
                "transaction_cost_bps": float(cost),
                "observations": len(path),
                "cumulative_return_pct": metrics[
                    "cumulative_return_pct"
                ],
                "cagr_pct": metrics["cagr_pct"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "maximum_drawdown_pct": metrics[
                    "maximum_drawdown_pct"
                ],
                "annualized_turnover_pct": metrics[
                    "annualized_turnover_pct"
                ],
                "total_transaction_cost_pct": metrics[
                    "total_transaction_cost_pct"
                ],
                "passed": passed,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module33_runs(
                run_id,
                source_module32_run_id,
                source_module30_run_id,
                started_at_utc,
                completed_at_utc,
                status,
                candidate_rows,
                daily_rows,
                cost_sensitivity_rows,
                drift_rows,
                selected_candidate_id,
                selected_strategy,
                annualized_turnover_pct,
                selected_sharpe,
                selected_max_drawdown_pct,
                btc_sharpe,
                btc_max_drawdown_pct,
                adjusted_drift_status,
                validation_status,
                recommendation,
                notes,
                platform_version
            )
            VALUES(
                ?, ?, ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0,
                NULL, NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL, NULL,
                NULL, '8.3.1'
            )
            """,
            [
                self.run_id,
                self.source_m32,
                self.source_m30,
                self.started,
            ],
        )

        try:
            probabilities = self.probabilities()
            prices = self.prices()
            returns = prices.pct_change(
                fill_method=None
            ).fillna(0)
            common = probabilities.index.intersection(
                returns.index
            )
            probabilities = probabilities.reindex(common)
            returns = returns.reindex(common)
            disagreement = self.disagreement().reindex(
                common
            )

            (
                candidates,
                selected_id,
                selected_path,
                regularized,
            ) = self.candidate_search(
                probabilities,
                returns,
            )
            selected = candidates[
                candidates["candidate_id"] == selected_id
            ].iloc[0]

            regularization = pd.DataFrame({
                "run_id": self.run_id,
                "observation_date": common.date,
                "raw_top_probability": (
                    probabilities.max(axis=1).to_numpy()
                ),
                "regularized_top_probability": (
                    regularized.max(axis=1).to_numpy()
                ),
                "raw_entropy": entropy(
                    probabilities.to_numpy()
                ),
                "regularized_entropy": entropy(
                    regularized.to_numpy()
                ),
                "temperature": float(
                    selected["temperature"]
                ),
                "probability_floor": float(
                    selected["probability_floor"]
                ),
                "calculated_at_utc": utcnow(),
            })
            drift = self.adjusted_drift(
                regularized,
                disagreement,
            )
            benchmark = self.benchmark_rows(
                returns,
                selected_path,
                selected_id,
            )
            btc_row = benchmark[
                benchmark["strategy_key"]
                == "BTC_BUY_HOLD"
            ].iloc[0]
            btc_metrics = {
                "sharpe_ratio": float(
                    btc_row["sharpe_ratio"]
                ),
                "maximum_drawdown_pct": float(
                    btc_row["maximum_drawdown_pct"]
                ),
            }

            selected_parameters = {
                "temperature": float(
                    selected["temperature"]
                ),
                "probability_floor": float(
                    selected["probability_floor"]
                ),
                "switch_margin": float(
                    selected["switch_margin"]
                ),
                "minimum_hold_days": int(
                    selected["minimum_hold_days"]
                ),
                "confidence_floor": float(
                    selected["confidence_floor"]
                ),
                "maximum_risk_exposure": float(
                    selected["maximum_risk_exposure"]
                ),
            }
            cost_sensitivity = self.cost_sensitivity(
                probabilities,
                returns,
                selected_parameters,
                btc_metrics,
            )

            optimized = selected_path.reset_index()
            optimized.insert(0, "run_id", self.run_id)
            optimized.insert(
                2,
                "candidate_id",
                selected_id,
            )
            optimized["observation_date"] = pd.to_datetime(
                optimized["observation_date"]
            ).dt.date
            optimized["calculated_at_utc"] = utcnow()

            current_drift = (
                str(
                    drift.sort_values(
                        "window_end_date"
                    ).iloc[-1]["drift_status"]
                )
                if not drift.empty
                else "UNKNOWN"
            )
            pass_rate = float(
                cost_sensitivity["passed"].mean() * 100
            )
            maximum_turnover = float(
                self.cfg["validation"][
                    "maximum_turnover_pct"
                ]
            )
            minimum_cost_pass_rate = float(
                self.cfg["validation"][
                    "minimum_cost_pass_rate_pct"
                ]
            )

            passed = bool(
                float(selected["sharpe_ratio"])
                >= float(btc_row["sharpe_ratio"])
                and float(
                    selected["maximum_drawdown_pct"]
                )
                > float(
                    btc_row["maximum_drawdown_pct"]
                )
                and float(
                    selected["annualized_turnover_pct"]
                )
                <= maximum_turnover
                and pass_rate >= minimum_cost_pass_rate
                and current_drift != "CRITICAL"
            )
            validation_status = (
                "PASSED" if passed else "LIMITED"
            )
            recommendation = (
                "READY_FOR_PORTFOLIO_INTELLIGENCE"
                if passed
                else "DECISION_ENGINE_REQUIRES_REFINEMENT"
            )

            summary = pd.DataFrame([{
                "run_id": self.run_id,
                "selected_candidate_id": selected_id,
                "temperature": float(
                    selected["temperature"]
                ),
                "switch_margin": float(
                    selected["switch_margin"]
                ),
                "minimum_hold_days": int(
                    selected["minimum_hold_days"]
                ),
                "confidence_floor": float(
                    selected["confidence_floor"]
                ),
                "maximum_risk_exposure": float(
                    selected["maximum_risk_exposure"]
                ),
                "adjusted_drift_status": current_drift,
                "optimized_sharpe": float(
                    selected["sharpe_ratio"]
                ),
                "btc_sharpe": float(
                    btc_row["sharpe_ratio"]
                ),
                "optimized_max_drawdown_pct": float(
                    selected["maximum_drawdown_pct"]
                ),
                "btc_max_drawdown_pct": float(
                    btc_row["maximum_drawdown_pct"]
                ),
                "optimized_turnover_pct": float(
                    selected["annualized_turnover_pct"]
                ),
                "cost_sensitivity_pass_rate_pct": (
                    pass_rate
                ),
                "validation_status": validation_status,
                "advancement_recommendation": (
                    recommendation
                ),
                "calculated_at_utc": utcnow(),
            }])

            for table, frame in [
                (
                    "m33_probability_regularization",
                    regularization,
                ),
                (
                    "m33_adjusted_probability_drift",
                    drift,
                ),
                (
                    "m33_decision_candidates",
                    candidates,
                ),
                ("m33_optimized_daily", optimized),
                (
                    "m33_cost_sensitivity",
                    cost_sensitivity,
                ),
                (
                    "m33_benchmark_comparison",
                    benchmark,
                ),
                (
                    "m33_validation_summary",
                    summary,
                ),
            ]:
                self.upsert(table, frame)

            notes = (
                "Probability regularization, hysteresis, minimum holding "
                "periods, confidence-scaled exposure, turnover-aware "
                "optimization, rolling-reference drift, and transaction-cost "
                "sensitivity completed. Modules 30-32 remain unchanged."
            )
            self.conn.execute(
                """
                UPDATE module33_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    candidate_rows=?,
                    daily_rows=?,
                    cost_sensitivity_rows=?,
                    drift_rows=?,
                    selected_candidate_id=?,
                    selected_strategy='OPTIMIZED_DECISION',
                    annualized_turnover_pct=?,
                    selected_sharpe=?,
                    selected_max_drawdown_pct=?,
                    btc_sharpe=?,
                    btc_max_drawdown_pct=?,
                    adjusted_drift_status=?,
                    validation_status=?,
                    recommendation=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(candidates),
                    len(optimized),
                    len(cost_sensitivity),
                    len(drift),
                    selected_id,
                    float(
                        selected[
                            "annualized_turnover_pct"
                        ]
                    ),
                    float(selected["sharpe_ratio"]),
                    float(
                        selected["maximum_drawdown_pct"]
                    ),
                    float(btc_row["sharpe_ratio"]),
                    float(
                        btc_row["maximum_drawdown_pct"]
                    ),
                    current_drift,
                    validation_status,
                    recommendation,
                    notes,
                    self.run_id,
                ],
            )
            self.conn.close()
            return summary.iloc[0].to_dict()

        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module33_runs
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


def run_module33():
    return Module33Runner().run()
