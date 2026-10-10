"""Module 16's evaluation cache is keyed by parameters AND the data the evaluation read."""

from __future__ import annotations

import duckdb
import pandas as pd

from crypto_platform import module16
from crypto_platform.module16 import (
    MODULE16_CACHE_MIGRATION,
    MODULE16_SCHEMA,
    Module16Runner,
    data_fingerprint,
)


CONFIG = {"research": {"start_date": "2020-01-01", "rebalance_frequency_days": 7}}


def _histories(bump: float = 0.0) -> dict[str, pd.Series]:
    index = pd.date_range("2024-01-01", periods=30, freq="D")
    btc = pd.Series([100.0 + i for i in range(30)], index=index)
    btc.iloc[-1] += bump
    return {"bitcoin": btc, "ethereum": pd.Series([10.0 + i for i in range(30)], index=index)}


def _dates(histories):
    return list(histories["bitcoin"].index[::7])


def test_fingerprint_changes_with_new_prices_dates_or_settings() -> None:
    histories = _histories()
    base = data_fingerprint(histories, _dates(histories), CONFIG)
    assert base == data_fingerprint(_histories(), _dates(histories), CONFIG)
    assert base != data_fingerprint(_histories(bump=0.01), _dates(histories), CONFIG)

    longer_index = pd.date_range("2024-01-01", periods=31, freq="D")
    longer = {
        asset: pd.Series([*series.tolist(), series.iloc[-1]], index=longer_index)
        for asset, series in histories.items()
    }
    assert base != data_fingerprint(longer, _dates(longer), CONFIG)
    assert base != data_fingerprint(histories, _dates(histories)[:-1], CONFIG)
    assert base != data_fingerprint(
        histories, _dates(histories), {"research": {**CONFIG["research"], "rebalance_frequency_days": 14}}
    )


def _runner(connection, fingerprint: str) -> Module16Runner:
    runner = object.__new__(Module16Runner)
    runner.conn = connection
    runner.data_fingerprint = fingerprint
    return runner


METRICS = {
    "total_return": 0.5, "annualized_return": 0.2, "annualized_volatility": 0.6, "sharpe": 0.4,
    "maximum_drawdown": -0.3, "btc_return": 0.4, "btc_excess": 0.1, "information_ratio": 0.2,
    "benchmark_win_rate": 55.0, "average_turnover": 0.1, "transaction_cost_drag": 0.01,
    "periods": 12, "equal_weight_return": 0.0, "btc_eth_return": 0.0, "equal_weight_excess": 0.0,
    "btc_eth_excess": 0.0, "tracking_error": 0.0,
}


def test_cache_only_hits_for_the_same_data(monkeypatch) -> None:
    monkeypatch.setattr(module16, "composite_objective", lambda metrics: 1.0)
    connection = duckdb.connect()
    connection.execute(MODULE16_SCHEMA)
    connection.execute(MODULE16_CACHE_MIGRATION)
    connection.execute(MODULE16_CACHE_MIGRATION)  # idempotent
    # A row written before this change has no fingerprint and must not be reused.
    connection.execute(
        "INSERT INTO candidate_evaluation_cache(parameter_hash, parameters_json, objective_score) "
        "VALUES ('legacy', '{}', 9.0)"
    )
    candidate = {"parameter_hash": "abc", "parameters": {"trend_weight": 0.2}}

    old_data = _runner(connection, "fingerprint-1")
    assert old_data.cache_lookup("legacy") is None
    old_data.cache_store(candidate, METRICS)
    assert old_data.cache_lookup("abc") is not None

    new_data = _runner(connection, "fingerprint-2")
    assert new_data.cache_lookup("abc") is None
    new_data.cache_store(candidate, METRICS)
    assert new_data.cache_lookup("abc") is not None
    rows = connection.execute(
        "SELECT data_fingerprint FROM candidate_evaluation_cache WHERE parameter_hash = 'abc'"
    ).fetchall()
    assert rows == [("fingerprint-2",)]


def test_run_sets_the_fingerprint_before_evaluating_candidates() -> None:
    source = module16.Module16Runner.run.__code__.co_names
    assert "data_fingerprint" in source
    text = open(module16.__file__, encoding="utf-8").read()
    assert text.index("self.data_fingerprint=data_fingerprint(") < text.index("cache=self.cache_lookup(")
