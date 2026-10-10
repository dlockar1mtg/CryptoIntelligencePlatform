"""Module 39 replay origin cache: cached results are exactly the uncached results."""

from __future__ import annotations

import copy
from dataclasses import fields
from datetime import timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest
import yaml
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import BayesianRidge

from crypto_platform import module39_validation as validation
from crypto_platform.module38 import Module38Runner


ROOT = Path(__file__).resolve().parents[2]


def light_model_suite(self, random_state):
    # Same model types as production, smaller so the test is quick. Single-threaded so the
    # uncached baseline is itself reproducible bit for bit (see test docstrings).
    return {
        "GRADIENT_BOOSTING": GradientBoostingRegressor(
            n_estimators=12, learning_rate=0.1, max_depth=2, random_state=random_state, loss="huber"
        ),
        "RANDOM_FOREST": RandomForestRegressor(
            n_estimators=6, max_depth=4, min_samples_leaf=5, random_state=random_state, n_jobs=1
        ),
        "BAYESIAN_RIDGE": BayesianRidge(),
    }


def _prices(days: int = 420, seed: int = 7) -> list[tuple]:
    rng = np.random.default_rng(seed)
    price = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.03, days)))
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    return [
        ("bitcoin", d.date(), float(p), float(p) * 2e7, 1e9 * (1.5 + np.sin(i / 9)))
        for i, (d, p) in enumerate(zip(dates, price))
    ]


@pytest.fixture()
def replay_env(monkeypatch):
    monkeypatch.setattr(Module38Runner, "model_suite", light_model_suite)
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    settings["module38"]["horizons_days"] = [7]
    connection = duckdb.connect()
    connection.execute(
        "CREATE TABLE canonical_market_daily(asset_id VARCHAR, observation_date DATE, "
        "price_usd DOUBLE, market_cap_usd DOUBLE, volume_24h_usd DOUBLE)"
    )
    connection.executemany("INSERT INTO canonical_market_daily VALUES (?,?,?,?,?)", _prices())
    calls = {"count": 0}
    original = validation.point_in_time_prediction

    def counting(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(validation, "point_in_time_prediction", counting)
    yield {"conn": connection, "settings": settings, "calls": calls}
    connection.close()


def _replay(env, *, cache: bool, settings: dict | None = None) -> dict:
    run_settings = copy.deepcopy(settings or env["settings"])
    run_settings["module39"]["replay_cache_enabled"] = cache
    env["calls"]["count"] = 0
    bundle = validation.build_true_replay_evidence(env["conn"], run_settings)
    bundle["fits"] = env["calls"]["count"]
    return bundle


def _assert_identical(left: dict, right: dict) -> None:
    for key in ("replay", "rolling", "calibration", "evidence_gaps"):
        assert left[key].equals(right[key]), key
        pdt.assert_frame_equal(left[key], right[key], check_exact=True)
        assert list(left[key].dtypes) == list(right[key].dtypes)
    for key in (
        "model_directional_accuracy_pct",
        "majority_directional_accuracy_pct",
        "model_minus_majority_accuracy_pct_points",
    ):
        assert left[key] == right[key]
    assert left["calibration_specs"].keys() == right["calibration_specs"].keys()
    for spec_key, spec in left["calibration_specs"].items():
        other = right["calibration_specs"][spec_key]
        for field in fields(spec):
            a, b = getattr(spec, field.name), getattr(other, field.name)
            if isinstance(a, np.ndarray):
                assert np.array_equal(a, b) and a.tobytes() == b.tobytes()
            else:
                assert a == b


def test_cold_and_warm_cache_match_the_uncached_replay_exactly(replay_env) -> None:
    uncached = _replay(replay_env, cache=False)
    cold = _replay(replay_env, cache=True)
    warm = _replay(replay_env, cache=True)

    assert len(uncached["replay"]) == 30
    assert uncached["fits"] == 30 and uncached["replay_cache"]["enabled"] is False
    assert cold["fits"] == 30 and cold["replay_cache"] == {"enabled": True, "reused": 0, "computed": 30}
    assert warm["fits"] == 0 and warm["replay_cache"] == {"enabled": True, "reused": 30, "computed": 0}

    _assert_identical(uncached, cold)
    _assert_identical(cold, warm)
    # Bit-for-bit: the float columns have the same bytes.
    for column in ("predicted_return_pct", "raw_probability_positive", "lower_return_pct"):
        assert (
            cold["replay"][column].to_numpy().tobytes()
            == warm["replay"][column].to_numpy().tobytes()
        )
    stored = replay_env["conn"].execute(
        f"SELECT COUNT(*) FROM {validation.REPLAY_CACHE_TABLE}"
    ).fetchone()[0]
    assert stored == 30


def test_a_changed_input_row_invalidates_only_the_origins_that_read_it(replay_env) -> None:
    _replay(replay_env, cache=True)
    origins = sorted(_replay(replay_env, cache=False)["replay"]["forecast_date"])
    # Change one price that only the later origins can see (as matured history).
    changed_day = origins[20] - timedelta(days=10)
    replay_env["conn"].execute(
        "UPDATE canonical_market_daily SET price_usd = price_usd * 1.0001 "
        "WHERE asset_id = 'bitcoin' AND observation_date = ?",
        [changed_day],
    )

    warm = _replay(replay_env, cache=True)
    fresh = _replay(replay_env, cache=False)

    assert warm["replay_cache"]["computed"] > 0
    assert warm["replay_cache"]["reused"] > 0
    assert warm["fits"] == warm["replay_cache"]["computed"]
    _assert_identical(warm, fresh)


def test_input_hash_changes_with_one_value_and_ignores_rows_after_the_origin() -> None:
    features = pd.DataFrame({
        "observation_date": pd.date_range("2024-01-01", periods=60, freq="D"),
        "return_1d": np.linspace(-0.01, 0.01, 60),
        "target_return": np.linspace(0.02, -0.02, 60),
    })
    base = validation.replay_input_hash(features, 40, 7)
    assert base == validation.replay_input_hash(features.copy(), 40, 7)

    earlier = features.copy()
    earlier.loc[10, "return_1d"] += 1e-12
    assert validation.replay_input_hash(earlier, 40, 7) != base

    origin_row = features.copy()
    origin_row.loc[40, "target_return"] += 1e-12  # the realized outcome is part of the result
    assert validation.replay_input_hash(origin_row, 40, 7) != base

    not_yet_matured = features.copy()
    not_yet_matured.loc[37, "return_1d"] += 1.0  # within the purge gap: not read
    not_yet_matured.loc[50, "return_1d"] += 1.0  # after the origin: not read
    assert validation.replay_input_hash(not_yet_matured, 40, 7) == base


def test_a_changed_setting_invalidates_every_origin(replay_env) -> None:
    _replay(replay_env, cache=True)
    changed = copy.deepcopy(replay_env["settings"])
    changed["module38"]["random_state"] = 1001
    warm = _replay(replay_env, cache=True, settings=changed)
    fresh = _replay(replay_env, cache=False, settings=changed)
    assert warm["replay_cache"] == {"enabled": True, "reused": 0, "computed": 30}
    _assert_identical(warm, fresh)
    # Entries made under the old settings are removed.
    hashes = replay_env["conn"].execute(
        f"SELECT COUNT(DISTINCT config_hash) FROM {validation.REPLAY_CACHE_TABLE}"
    ).fetchone()[0]
    assert hashes == 1


def test_config_hash_covers_code_and_settings() -> None:
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    base = validation.replay_config_hash(settings["module38"], 0.1)
    assert base == validation.replay_config_hash(copy.deepcopy(settings["module38"]), 0.1)
    assert base != validation.replay_config_hash(settings["module38"], 0.2)
    changed = copy.deepcopy(settings["module38"])
    changed["validation_rows"] = 121
    assert base != validation.replay_config_hash(changed, 0.1)
