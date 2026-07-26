from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from crypto_platform.platform import load_all, connect
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.module31 import MODULE31_SCHEMA
from crypto_platform.module35 import MODULE35_SCHEMA
from crypto_platform.module36 import MODULE36_SCHEMA

MODULE37_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module37_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module35_run_id VARCHAR,
    source_module36_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    candidate_rows INTEGER,
    allocation_rows INTEGER,
    frontier_rows INTEGER,
    risk_contribution_rows INTEGER,
    selected_candidate_id VARCHAR,
    selected_method VARCHAR,
    expected_return_pct DOUBLE,
    expected_volatility_pct DOUBLE,
    expected_sharpe DOUBLE,
    diversification_ratio DOUBLE,
    effective_assets DOUBLE,
    concentration_score DOUBLE,
    cash_weight DOUBLE,
    turnover_pct DOUBLE,
    validation_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m37_expected_returns(
    run_id VARCHAR,
    observation_date DATE,
    asset_id VARCHAR,
    historical_return_pct DOUBLE,
    regime_return_pct DOUBLE,
    shrinkage_prior_pct DOUBLE,
    blended_expected_return_pct DOUBLE,
    current_regime_probability DOUBLE,
    confidence_weight DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, asset_id)
);

CREATE TABLE IF NOT EXISTS m37_optimizer_candidates(
    run_id VARCHAR,
    candidate_id VARCHAR,
    method VARCHAR,
    expected_return_pct DOUBLE,
    expected_volatility_pct DOUBLE,
    expected_sharpe DOUBLE,
    diversification_ratio DOUBLE,
    risky_sleeve_effective_assets DOUBLE,
    risky_sleeve_concentration_pct DOUBLE,
    cash_weight DOUBLE,
    turnover_pct DOUBLE,
    maximum_asset_weight DOUBLE,
    minimum_asset_weight DOUBLE,
    objective_score DOUBLE,
    optimization_success BOOLEAN,
    selected BOOLEAN,
    weights_json VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS m37_optimized_allocations(
    run_id VARCHAR,
    observation_date DATE,
    asset_id VARCHAR,
    prior_weight DOUBLE,
    unconstrained_weight DOUBLE,
    optimized_weight DOUBLE,
    risk_adjusted_weight DOUBLE,
    trade_weight DOUBLE,
    marginal_risk_contribution_pct DOUBLE,
    allocation_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, asset_id)
);

CREATE TABLE IF NOT EXISTS m37_risk_decomposition(
    run_id VARCHAR,
    observation_date DATE,
    asset_id VARCHAR,
    weight DOUBLE,
    standalone_volatility_pct DOUBLE,
    marginal_contribution DOUBLE,
    component_risk_contribution_pct DOUBLE,
    diversification_benefit_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date, asset_id)
);

CREATE TABLE IF NOT EXISTS m37_efficient_frontier(
    run_id VARCHAR,
    frontier_id INTEGER,
    target_return_pct DOUBLE,
    expected_return_pct DOUBLE,
    expected_volatility_pct DOUBLE,
    expected_sharpe DOUBLE,
    diversification_ratio DOUBLE,
    concentration_pct DOUBLE,
    weights_json VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, frontier_id)
);

CREATE TABLE IF NOT EXISTS m37_portfolio_statistics(
    run_id VARCHAR PRIMARY KEY,
    observation_date DATE,
    selected_method VARCHAR,
    expected_return_pct DOUBLE,
    expected_volatility_pct DOUBLE,
    expected_sharpe DOUBLE,
    diversification_ratio DOUBLE,
    risky_sleeve_effective_assets DOUBLE,
    risky_sleeve_concentration_pct DOUBLE,
    cash_weight DOUBLE,
    turnover_pct DOUBLE,
    active_share_pct DOUBLE,
    information_ratio DOUBLE,
    portfolio_entropy DOUBLE,
    recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m37_expected_returns AS
SELECT * FROM m37_expected_returns
WHERE run_id=(
    SELECT run_id FROM module37_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY blended_expected_return_pct DESC;

CREATE OR REPLACE VIEW latest_m37_optimizer_candidates AS
SELECT * FROM m37_optimizer_candidates
WHERE run_id=(
    SELECT run_id FROM module37_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY selected DESC, objective_score DESC;

CREATE OR REPLACE VIEW latest_m37_optimized_allocations AS
SELECT * FROM m37_optimized_allocations
WHERE run_id=(
    SELECT run_id FROM module37_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY risk_adjusted_weight DESC;

CREATE OR REPLACE VIEW latest_m37_risk_decomposition AS
SELECT * FROM m37_risk_decomposition
WHERE run_id=(
    SELECT run_id FROM module37_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY component_risk_contribution_pct DESC;

CREATE OR REPLACE VIEW latest_m37_efficient_frontier AS
SELECT * FROM m37_efficient_frontier
WHERE run_id=(
    SELECT run_id FROM module37_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY expected_volatility_pct;

CREATE OR REPLACE VIEW latest_m37_portfolio_statistics AS
SELECT * FROM m37_portfolio_statistics
WHERE run_id=(
    SELECT run_id FROM module37_runs
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


def utcnow():
    return datetime.now(timezone.utc)


def normalize(weights, total=1.0):
    weights = np.clip(np.asarray(weights, dtype=float), 0, None)
    denominator = weights.sum()
    if denominator <= 0:
        return np.repeat(total / len(weights), len(weights))
    return weights / denominator * total


def portfolio_metrics(weights, expected_returns, covariance):
    expected_return = float(weights @ expected_returns)
    variance = float(weights @ covariance @ weights)
    volatility = math.sqrt(max(variance, 0))
    sharpe = expected_return / volatility if volatility > 0 else 0.0
    asset_volatility = np.sqrt(np.clip(np.diag(covariance), 1e-12, None))
    weighted_standalone = float(weights @ asset_volatility)
    diversification_ratio = (
        weighted_standalone / volatility
        if volatility > 0
        else 0.0
    )
    risky_total = max(weights.sum(), 1e-12)
    risky_normalized = weights / risky_total
    concentration = float(np.sum(risky_normalized ** 2))
    effective_assets = 1 / concentration if concentration > 0 else 0.0
    positive_weights = risky_normalized[
        risky_normalized > 0
    ]
    entropy = float(
        -np.sum(
            positive_weights
            * np.log(positive_weights)
        )
    )
    return {
        "expected_return": expected_return,
        "volatility": volatility,
        "sharpe": sharpe,
        "diversification_ratio": diversification_ratio,
        "concentration": concentration,
        "effective_assets": effective_assets,
        "entropy": entropy,
    }


class Module37Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE30_SCHEMA)
        self.conn.execute(MODULE31_SCHEMA)
        self.conn.execute(MODULE35_SCHEMA)
        self.conn.execute(MODULE36_SCHEMA)
        self.conn.execute(MODULE37_SCHEMA)
        self.cfg = self.settings["module37"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

        source_row = self.conn.execute(
            """
            SELECT
                portfolio.run_id,
                risk.run_id,
                execution.source_module30_run_id,
                validation.source_module31_run_id
            FROM module36_runs AS risk
            JOIN module35_runs AS portfolio
              ON portfolio.run_id = risk.source_module35_run_id
            JOIN module34_runs AS execution
              ON execution.run_id =
                 portfolio.source_module34_run_id
            JOIN module33_runs AS regularization
              ON regularization.run_id =
                 execution.source_module33_run_id
            JOIN module32_runs AS validation
              ON validation.run_id =
                 regularization.source_module32_run_id
            WHERE risk.status='SUCCESS'
              AND portfolio.status='SUCCESS'
            ORDER BY risk.started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        if source_row is None:
            raise RuntimeError(
                "A complete Module 35 through Module 36 lineage "
                "is required."
            )
        self.source_m35 = str(source_row[0])
        self.source_m36 = str(source_row[1])
        self.source_m30 = str(source_row[2])
        self.source_m31 = str(source_row[3])

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m37_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m37_stage"
        )
        self.conn.unregister("_m37_stage")

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

    def prior_allocations(self):
        frame = self.conn.execute(
            """
            SELECT observation_date, asset_id, final_target_weight
            FROM m35_portfolio_allocations
            WHERE run_id=?
            ORDER BY asset_id
            """,
            [self.source_m35],
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        risky = np.asarray([
            float(
                frame.loc[
                    frame["asset_id"] == asset,
                    "final_target_weight",
                ].iloc[0]
            )
            if not frame.loc[
                frame["asset_id"] == asset
            ].empty
            else 0.0
            for asset in ASSETS
        ])
        cash_rows = frame.loc[frame["asset_id"] == "CASH"]
        cash = (
            float(cash_rows["final_target_weight"].iloc[0])
            if not cash_rows.empty
            else max(1 - risky.sum(), 0)
        )
        observation_date = frame["observation_date"].max()
        return risky, cash, observation_date

    def current_regime_probabilities(self):
        frame = self.conn.execute(
            """
            SELECT regime, probability
            FROM clean_probability_current
            WHERE run_id=?
            ORDER BY probability_rank
            """,
            [self.source_m30],
        ).fetchdf()
        return dict(zip(frame["regime"], frame["probability"]))

    def regime_forward_returns(self):
        frame = self.conn.execute(
            """
            SELECT regime, asset_id, horizon_days,
                   mean_forward_return_pct
            FROM m31_forward_return_validation
            WHERE run_id=?
              AND signal_source='CLEAN'
              AND horizon_days IN (30, 60, 90)
            """,
            [self.source_m31],
        ).fetchdf()
        return frame

    def expected_returns(
        self,
        returns,
        observation_date,
    ):
        lookback = int(self.cfg["lookback_days"])
        sample = returns.tail(lookback)
        historical = sample.mean() * 365
        prior = historical.median()
        regime_probabilities = (
            self.current_regime_probabilities()
        )
        regime_frame = self.regime_forward_returns()

        rows = []
        blended = []
        historical_weight = float(
            self.cfg["expected_returns"][
                "historical_weight"
            ]
        )
        regime_weight = float(
            self.cfg["expected_returns"]["regime_weight"]
        )
        prior_weight = float(
            self.cfg["expected_returns"]["prior_weight"]
        )

        confidence_row = self.conn.execute(
            """
            SELECT portfolio_confidence
            FROM m35_portfolio_statistics
            WHERE run_id=?
            """,
            [self.source_m35],
        ).fetchone()
        confidence = (
            float(confidence_row[0]) / 100
            if confidence_row
            else 0.5
        )
        effective_regime_weight = regime_weight * confidence
        adjusted_historical_weight = (
            historical_weight
            + regime_weight
            - effective_regime_weight
        )

        for asset in ASSETS:
            regime_return = 0.0
            probability_mass = 0.0
            asset_views = regime_frame[
                regime_frame["asset_id"] == asset
            ]
            for _, row in asset_views.iterrows():
                probability = float(
                    regime_probabilities.get(
                        row["regime"],
                        0.0,
                    )
                )
                annualized = (
                    float(row["mean_forward_return_pct"])
                    / 100
                    * 365
                    / max(int(row["horizon_days"]), 1)
                )
                regime_return += probability * annualized
                probability_mass += probability
            if probability_mass > 0:
                regime_return /= probability_mass
            else:
                regime_return = float(historical[asset])

            blended_return = (
                adjusted_historical_weight
                * float(historical[asset])
                + effective_regime_weight
                * regime_return
                + prior_weight
                * float(prior)
            )
            total_weight = (
                adjusted_historical_weight
                + effective_regime_weight
                + prior_weight
            )
            blended_return /= max(total_weight, 1e-9)
            blended.append(blended_return)
            rows.append({
                "run_id": self.run_id,
                "observation_date": observation_date.date(),
                "asset_id": asset,
                "historical_return_pct": (
                    float(historical[asset]) * 100
                ),
                "regime_return_pct": (
                    regime_return * 100
                ),
                "shrinkage_prior_pct": (
                    float(prior) * 100
                ),
                "blended_expected_return_pct": (
                    blended_return * 100
                ),
                "current_regime_probability": (
                    max(regime_probabilities.values())
                    if regime_probabilities
                    else 0.0
                ),
                "confidence_weight": confidence,
                "calculated_at_utc": utcnow(),
            })
        return np.asarray(blended), pd.DataFrame(rows)

    def constraints(self, risky_total):
        minimum = float(
            self.cfg["constraints"][
                "minimum_asset_weight"
            ]
        )
        maximum = float(
            self.cfg["constraints"][
                "maximum_asset_weight"
            ]
        )
        bounds = [
            (
                0.0 if minimum <= 0 else min(minimum, risky_total),
                min(maximum, risky_total),
            )
            for _ in ASSETS
        ]
        equality = {
            "type": "eq",
            "fun": lambda weights: (
                np.sum(weights) - risky_total
            ),
        }
        return bounds, [equality]

    def solve(
        self,
        method,
        expected_returns,
        covariance,
        risky_total,
        prior_weights,
    ):
        bounds, constraints = self.constraints(risky_total)
        x0 = normalize(
            np.maximum(prior_weights, 1e-6),
            risky_total,
        )
        turnover_penalty = float(
            self.cfg["optimization"][
                "turnover_penalty"
            ]
        )
        concentration_penalty = float(
            self.cfg["optimization"][
                "concentration_penalty"
            ]
        )

        if method == "MINIMUM_VARIANCE":
            objective = lambda w: (
                float(w @ covariance @ w)
                + turnover_penalty
                * float(np.sum((w - prior_weights) ** 2))
            )
        elif method == "MAXIMUM_SHARPE":
            def objective(w):
                metrics = portfolio_metrics(
                    w,
                    expected_returns,
                    covariance,
                )
                return (
                    -metrics["sharpe"]
                    + concentration_penalty
                    * metrics["concentration"]
                    + turnover_penalty
                    * float(
                        np.sum((w - prior_weights) ** 2)
                    )
                )
        elif method == "RISK_PARITY":
            def objective(w):
                variance = float(w @ covariance @ w)
                marginal = covariance @ w
                contribution = (
                    w * marginal
                    / max(variance, 1e-12)
                )
                target = np.repeat(1 / len(w), len(w))
                return float(
                    np.sum((contribution - target) ** 2)
                    + turnover_penalty
                    * np.sum((w - prior_weights) ** 2)
                )
        elif method == "BLACK_LITTERMAN":
            equilibrium = normalize(
                1 / np.sqrt(
                    np.clip(
                        np.diag(covariance),
                        1e-12,
                        None,
                    )
                ),
                risky_total,
            )
            blended_view = (
                0.55 * expected_returns
                + 0.45
                * (
                    covariance
                    @ equilibrium
                    * float(
                        self.cfg["optimization"][
                            "risk_aversion"
                        ]
                    )
                )
            )

            def objective(w):
                metrics = portfolio_metrics(
                    w,
                    blended_view,
                    covariance,
                )
                return (
                    -metrics["sharpe"]
                    + concentration_penalty
                    * metrics["concentration"]
                    + turnover_penalty
                    * float(
                        np.sum((w - prior_weights) ** 2)
                    )
                )
        else:  # REGIME_AWARE
            def objective(w):
                metrics = portfolio_metrics(
                    w,
                    expected_returns,
                    covariance,
                )
                diversification_reward = (
                    metrics["diversification_ratio"]
                )
                return (
                    -metrics["sharpe"]
                    - 0.08 * diversification_reward
                    + concentration_penalty
                    * metrics["concentration"]
                    + turnover_penalty
                    * float(
                        np.sum((w - prior_weights) ** 2)
                    )
                )

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={
                "maxiter": 2500,
                "ftol": 1e-10,
            },
        )
        weights = (
            result.x
            if result.success
            else x0
        )
        weights = normalize(weights, risky_total)
        return weights, bool(result.success)

    def frontier(
        self,
        expected_returns,
        covariance,
        risky_total,
        prior_weights,
    ):
        minimum_return = float(
            np.min(expected_returns)
            * risky_total
        )
        maximum_return = float(
            np.max(expected_returns)
            * risky_total
        )
        targets = np.linspace(
            minimum_return,
            maximum_return,
            int(self.cfg["frontier_points"]),
        )
        bounds, base_constraints = self.constraints(
            risky_total
        )
        rows = []

        for index, target in enumerate(targets, 1):
            constraints = base_constraints + [{
                "type": "eq",
                "fun": (
                    lambda weights, target=target:
                    float(weights @ expected_returns)
                    - target
                ),
            }]
            result = minimize(
                lambda weights: float(
                    weights @ covariance @ weights
                ),
                normalize(prior_weights, risky_total),
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={
                    "maxiter": 1500,
                    "ftol": 1e-10,
                },
            )
            if not result.success:
                continue
            weights = normalize(result.x, risky_total)
            metrics = portfolio_metrics(
                weights,
                expected_returns,
                covariance,
            )
            rows.append({
                "run_id": self.run_id,
                "frontier_id": index,
                "target_return_pct": target * 100,
                "expected_return_pct": (
                    metrics["expected_return"] * 100
                ),
                "expected_volatility_pct": (
                    metrics["volatility"] * 100
                ),
                "expected_sharpe": metrics["sharpe"],
                "diversification_ratio": (
                    metrics["diversification_ratio"]
                ),
                "concentration_pct": (
                    metrics["concentration"] * 100
                ),
                "weights_json": json.dumps({
                    asset: float(weight)
                    for asset, weight in zip(
                        ASSETS,
                        weights,
                    )
                }),
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module37_runs(
                run_id,
                source_module35_run_id,
                source_module36_run_id,
                started_at_utc,
                completed_at_utc,
                status,
                candidate_rows,
                allocation_rows,
                frontier_rows,
                risk_contribution_rows,
                selected_candidate_id,
                selected_method,
                expected_return_pct,
                expected_volatility_pct,
                expected_sharpe,
                diversification_ratio,
                effective_assets,
                concentration_score,
                cash_weight,
                turnover_pct,
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
                NULL, NULL, NULL, '9.2.1'
            )
            """,
            [
                self.run_id,
                self.source_m35,
                self.source_m36,
                self.started,
            ],
        )

        try:
            prices = self.prices()
            returns = prices.pct_change(
                fill_method=None
            ).dropna(how="all").fillna(0)
            lookback = int(self.cfg["lookback_days"])
            sample = returns.tail(lookback)
            covariance = (
                sample.cov().to_numpy() * 365
            )
            covariance += (
                np.eye(len(ASSETS))
                * float(
                    self.cfg["covariance_ridge"]
                )
            )

            (
                prior_weights,
                prior_cash,
                observation_date,
            ) = self.prior_allocations()
            risk_row = self.conn.execute(
                """
                SELECT volatility_scaler
                FROM m36_portfolio_risk
                WHERE run_id=?
                """,
                [self.source_m36],
            ).fetchone()
            volatility_scaler = (
                float(risk_row[0])
                if risk_row
                else 1.0
            )
            original_risky_total = float(
                prior_weights.sum()
            )
            risky_total = min(
                original_risky_total
                * volatility_scaler,
                float(
                    self.cfg["constraints"][
                        "maximum_risky_exposure"
                    ]
                ),
            )
            minimum_cash = float(
                self.cfg["constraints"][
                    "minimum_cash_weight"
                ]
            )
            risky_total = min(
                risky_total,
                1 - minimum_cash,
            )
            expected_returns, expected_frame = (
                self.expected_returns(
                    returns,
                    observation_date,
                )
            )

            methods = [
                "MINIMUM_VARIANCE",
                "MAXIMUM_SHARPE",
                "RISK_PARITY",
                "BLACK_LITTERMAN",
                "REGIME_AWARE",
            ]
            candidates = []
            weights_map = {}

            for index, method in enumerate(methods, 1):
                weights, success = self.solve(
                    method,
                    expected_returns,
                    covariance,
                    risky_total,
                    prior_weights,
                )
                metrics = portfolio_metrics(
                    weights,
                    expected_returns,
                    covariance,
                )
                cash = float(max(1 - weights.sum(), 0))
                turnover = float(
                    np.abs(
                        np.append(weights, cash)
                        - np.append(
                            prior_weights,
                            prior_cash,
                        )
                    ).sum()
                    * 100
                )
                objective = float(
                    55 * metrics["sharpe"]
                    + 8
                    * metrics[
                        "diversification_ratio"
                    ]
                    + 0.18
                    * metrics["expected_return"]
                    * 100
                    - 0.12
                    * metrics["volatility"]
                    * 100
                    - 0.08 * turnover
                    - 12
                    * metrics["concentration"]
                )
                candidate_id = f"I{index:03d}"
                candidates.append({
                    "run_id": self.run_id,
                    "candidate_id": candidate_id,
                    "method": method,
                    "expected_return_pct": (
                        metrics["expected_return"] * 100
                    ),
                    "expected_volatility_pct": (
                        metrics["volatility"] * 100
                    ),
                    "expected_sharpe": metrics["sharpe"],
                    "diversification_ratio": (
                        metrics["diversification_ratio"]
                    ),
                    "risky_sleeve_effective_assets": (
                        metrics["effective_assets"]
                    ),
                    "risky_sleeve_concentration_pct": (
                        metrics["concentration"] * 100
                    ),
                    "cash_weight": cash,
                    "turnover_pct": turnover,
                    "maximum_asset_weight": float(
                        weights.max()
                    ),
                    "minimum_asset_weight": float(
                        weights.min()
                    ),
                    "objective_score": objective,
                    "optimization_success": success,
                    "selected": False,
                    "weights_json": json.dumps({
                        asset: float(weight)
                        for asset, weight in zip(
                            ASSETS,
                            weights,
                        )
                    }),
                    "calculated_at_utc": utcnow(),
                })
                weights_map[candidate_id] = weights

            candidate_frame = pd.DataFrame(candidates)
            successful = candidate_frame[
                candidate_frame["optimization_success"]
            ]
            selection_pool = (
                successful
                if not successful.empty
                else candidate_frame
            )
            selected_index = selection_pool[
                "objective_score"
            ].idxmax()
            candidate_frame.loc[
                selected_index,
                "selected",
            ] = True
            selected = candidate_frame.loc[
                selected_index
            ]
            selected_id = str(
                selected["candidate_id"]
            )
            selected_weights = weights_map[
                selected_id
            ]
            selected_cash = float(
                selected["cash_weight"]
            )

            selected_metrics = portfolio_metrics(
                selected_weights,
                expected_returns,
                covariance,
            )
            variance = float(
                selected_weights
                @ covariance
                @ selected_weights
            )
            marginal = covariance @ selected_weights
            component = (
                selected_weights
                * marginal
                / max(variance, 1e-12)
            )
            asset_volatility = np.sqrt(
                np.clip(
                    np.diag(covariance),
                    1e-12,
                    None,
                )
            )

            risk_rows = []
            allocation_rows = []
            for index, asset in enumerate(ASSETS):
                standalone = float(
                    asset_volatility[index]
                )
                contribution = float(component[index])
                diversification_benefit = float(
                    max(
                        standalone
                        * selected_weights[index]
                        - contribution
                        * selected_metrics[
                            "volatility"
                        ],
                        0,
                    )
                    * 100
                )
                risk_rows.append({
                    "run_id": self.run_id,
                    "observation_date": (
                        observation_date.date()
                    ),
                    "asset_id": asset,
                    "weight": float(
                        selected_weights[index]
                    ),
                    "standalone_volatility_pct": (
                        standalone * 100
                    ),
                    "marginal_contribution": float(
                        marginal[index]
                    ),
                    "component_risk_contribution_pct": (
                        contribution * 100
                    ),
                    "diversification_benefit_pct": (
                        diversification_benefit
                    ),
                    "calculated_at_utc": utcnow(),
                })
                trade = float(
                    selected_weights[index]
                    - prior_weights[index]
                )
                allocation_rows.append({
                    "run_id": self.run_id,
                    "observation_date": (
                        observation_date.date()
                    ),
                    "asset_id": asset,
                    "prior_weight": float(
                        prior_weights[index]
                    ),
                    "unconstrained_weight": float(
                        selected_weights[index]
                    ),
                    "optimized_weight": float(
                        selected_weights[index]
                    ),
                    "risk_adjusted_weight": float(
                        selected_weights[index]
                    ),
                    "trade_weight": trade,
                    "marginal_risk_contribution_pct": (
                        contribution * 100
                    ),
                    "allocation_status": (
                        "INCREASE"
                        if trade > 0.01
                        else "REDUCE"
                        if trade < -0.01
                        else "HOLD"
                    ),
                    "calculated_at_utc": utcnow(),
                })

            allocation_rows.append({
                "run_id": self.run_id,
                "observation_date": (
                    observation_date.date()
                ),
                "asset_id": "CASH",
                "prior_weight": prior_cash,
                "unconstrained_weight": selected_cash,
                "optimized_weight": selected_cash,
                "risk_adjusted_weight": selected_cash,
                "trade_weight": (
                    selected_cash - prior_cash
                ),
                "marginal_risk_contribution_pct": 0.0,
                "allocation_status": (
                    "INCREASE"
                    if selected_cash > prior_cash + 0.01
                    else "REDUCE"
                    if selected_cash < prior_cash - 0.01
                    else "HOLD"
                ),
                "calculated_at_utc": utcnow(),
            })

            frontier = self.frontier(
                expected_returns,
                covariance,
                risky_total,
                prior_weights,
            )
            benchmark_weights = normalize(
                np.repeat(1.0, len(ASSETS)),
                risky_total,
            )
            benchmark_returns = (
                sample @ benchmark_weights
            )
            selected_returns = (
                sample @ selected_weights
            )
            active_return = (
                selected_returns
                - benchmark_returns
            )
            active_share = float(
                0.5
                * np.abs(
                    selected_weights
                    - benchmark_weights
                ).sum()
                * 100
            )
            tracking_error = float(
                active_return.std()
                * math.sqrt(365)
            )
            minimum_active_share = float(
                self.cfg["validation"].get(
                    "minimum_active_share_for_ir_pct",
                    5.0,
                )
            )
            information_ratio = (
                float(
                    active_return.mean()
                    * 365
                    / tracking_error
                )
                if tracking_error > 1e-9
                and active_share
                >= minimum_active_share
                else 0.0
            )

            recommendation = (
                "DEFENSIVE_OPTIMIZED"
                if selected_cash >= 0.75
                else "BALANCED_OPTIMIZED"
                if selected_cash >= 0.35
                else "RISK_ON_OPTIMIZED"
            )
            stats = pd.DataFrame([{
                "run_id": self.run_id,
                "observation_date": (
                    observation_date.date()
                ),
                "selected_method": str(
                    selected["method"]
                ),
                "expected_return_pct": float(
                    selected["expected_return_pct"]
                ),
                "expected_volatility_pct": float(
                    selected[
                        "expected_volatility_pct"
                    ]
                ),
                "expected_sharpe": float(
                    selected["expected_sharpe"]
                ),
                "diversification_ratio": float(
                    selected[
                        "diversification_ratio"
                    ]
                ),
                "risky_sleeve_effective_assets": float(
                    selected[
                        "risky_sleeve_effective_assets"
                    ]
                ),
                "risky_sleeve_concentration_pct": float(
                    selected[
                        "risky_sleeve_concentration_pct"
                    ]
                ),
                "cash_weight": selected_cash,
                "turnover_pct": float(
                    selected["turnover_pct"]
                ),
                "active_share_pct": active_share,
                "information_ratio": (
                    information_ratio
                ),
                "portfolio_entropy": float(
                    selected_metrics["entropy"]
                ),
                "recommendation": recommendation,
                "calculated_at_utc": utcnow(),
            }])

            self.upsert(
                "m37_expected_returns",
                expected_frame,
            )
            self.upsert(
                "m37_optimizer_candidates",
                candidate_frame,
            )
            self.upsert(
                "m37_optimized_allocations",
                pd.DataFrame(allocation_rows),
            )
            self.upsert(
                "m37_risk_decomposition",
                pd.DataFrame(risk_rows),
            )
            self.upsert(
                "m37_efficient_frontier",
                frontier,
            )
            self.upsert(
                "m37_portfolio_statistics",
                stats,
            )

            validation_status = (
                "PASSED"
                if bool(
                    selected[
                        "optimization_success"
                    ]
                )
                and float(
                    selected[
                        "risky_sleeve_concentration_pct"
                    ]
                )
                <= float(
                    self.cfg["validation"][
                        "maximum_concentration_pct"
                    ]
                )
                and float(
                    selected["turnover_pct"]
                )
                <= float(
                    self.cfg["validation"][
                        "maximum_turnover_pct"
                    ]
                )
                else "LIMITED"
            )
            notes = (
                "Institutional optimizer blended historical and "
                "regime-conditioned expected returns, applied covariance "
                "ridge stabilization, constrained risky-sleeve weights, "
                "and generated efficient-frontier and risk-decomposition outputs."
            )
            self.conn.execute(
                """
                UPDATE module37_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    candidate_rows=?,
                    allocation_rows=?,
                    frontier_rows=?,
                    risk_contribution_rows=?,
                    selected_candidate_id=?,
                    selected_method=?,
                    expected_return_pct=?,
                    expected_volatility_pct=?,
                    expected_sharpe=?,
                    diversification_ratio=?,
                    effective_assets=?,
                    concentration_score=?,
                    cash_weight=?,
                    turnover_pct=?,
                    validation_status=?,
                    recommendation=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(candidate_frame),
                    len(allocation_rows),
                    len(frontier),
                    len(risk_rows),
                    selected_id,
                    str(selected["method"]),
                    float(
                        selected[
                            "expected_return_pct"
                        ]
                    ),
                    float(
                        selected[
                            "expected_volatility_pct"
                        ]
                    ),
                    float(
                        selected["expected_sharpe"]
                    ),
                    float(
                        selected[
                            "diversification_ratio"
                        ]
                    ),
                    float(
                        selected[
                            "risky_sleeve_effective_assets"
                        ]
                    ),
                    float(
                        selected[
                            "risky_sleeve_concentration_pct"
                        ]
                    ),
                    selected_cash,
                    float(
                        selected["turnover_pct"]
                    ),
                    validation_status,
                    recommendation,
                    notes,
                    self.run_id,
                ],
            )
            self.conn.close()
            return stats.iloc[0].to_dict() | {
                "validation_status": validation_status
            }

        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module37_runs
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


def run_module37():
    return Module37Runner().run()
