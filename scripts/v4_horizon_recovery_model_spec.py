from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import BayesianRidge, LogisticRegression

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"
RECOVERY_HORIZONS = (7, 30, 365)
TRANSACTION_COST_BPS = 15.0

NATIVE_LAG_DAYS = {
    "btc_return_30d_pct": 1,
    "core_breadth_above_sma50_pct": 1,
    "core_median_return_30d_pct": 1,
    "fear_greed_index": 1,
    "stablecoin_supply_usd": 1,
    "stablecoin_growth_30d_pct": 1,
    "dollar_index": 2,
    "vix": 2,
    "macro_liquidity_score": 2,
    "risk_appetite_score": 2,
}

CANDIDATE_CONTRACTS = {
    7: {
        "assets_required_nonnegative": 4,
        "families": {
            "V4_7D_SHORT_TREND_REVERSAL_LOGIT": {
                "kind": "classifier",
                "features": [
                    "return_1d", "return_3d", "return_7d", "return_14d", "return_30d",
                    "volatility_7d", "volatility_14d", "volatility_30d",
                    "distance_sma20", "distance_sma50",
                ],
            },
            "V4_7D_RELATIVE_STRENGTH_GB": {
                "kind": "classifier",
                "features": [
                    "return_1d", "return_3d", "return_7d", "return_14d", "return_30d",
                    "volatility_14d", "volatility_30d", "distance_sma20", "distance_sma50",
                    "asset_minus_btc_return_7d", "asset_minus_btc_return_14d", "asset_minus_btc_return_30d",
                    "asset_minus_core_median_return_7d", "asset_minus_core_median_return_14d", "asset_minus_core_median_return_30d",
                    "core_breadth_positive_7d_pct", "core_breadth_positive_14d_pct", "core_breadth_positive_30d_pct",
                    "core_return_dispersion_7d", "core_return_dispersion_14d", "core_return_dispersion_30d",
                ],
            },
            "V4_7D_VOLATILITY_STATE_EXTRA_TREES": {
                "kind": "classifier",
                "features": [
                    "return_1d", "return_3d", "return_7d", "return_14d", "return_30d",
                    "volatility_7d", "volatility_14d", "volatility_30d", "volatility_ratio_7d_30d",
                    "distance_sma20", "distance_sma50",
                    "asset_minus_btc_return_7d", "asset_minus_core_median_return_7d",
                    "core_breadth_positive_7d_pct", "core_return_dispersion_7d",
                ],
            },
        },
    },
    30: {
        "assets_required_nonnegative": 4,
        "families": {
            "V4_30D_TREND_REVERSAL_LOGIT": {
                "kind": "classifier",
                "features": [
                    "return_7d", "return_14d", "return_30d", "return_60d", "return_90d",
                    "volatility_30d", "volatility_60d", "volatility_90d",
                    "distance_sma20", "distance_sma50", "distance_sma200",
                ],
            },
            "V4_30D_RELATIVE_CONTEXT_GB": {
                "kind": "classifier",
                "features": [
                    "return_7d", "return_14d", "return_30d", "return_60d", "return_90d",
                    "volatility_30d", "volatility_60d", "volatility_90d",
                    "distance_sma50", "distance_sma200",
                    "asset_minus_btc_return_30d", "asset_minus_btc_return_60d", "asset_minus_btc_return_90d",
                    "asset_minus_core_median_return_30d", "asset_minus_core_median_return_60d", "asset_minus_core_median_return_90d",
                    "core_breadth_positive_30d_pct", "core_breadth_positive_60d_pct", "core_breadth_positive_90d_pct",
                    "core_return_dispersion_30d", "core_return_dispersion_60d", "core_return_dispersion_90d",
                    "core_breadth_above_sma50_pct", "core_median_return_30d_pct", "fear_greed_index",
                ],
            },
            "V4_30D_VOLATILITY_STATE_EXTRA_TREES": {
                "kind": "classifier",
                "features": [
                    "return_7d", "return_30d", "return_60d", "return_90d",
                    "volatility_30d", "volatility_60d", "volatility_90d", "volatility_ratio_30d_90d",
                    "distance_sma20", "distance_sma50", "distance_sma200",
                    "asset_minus_btc_return_30d", "asset_minus_core_median_return_30d",
                    "core_breadth_positive_30d_pct", "core_return_dispersion_30d",
                ],
            },
        },
    },
    365: {
        "assets_required_nonnegative": 3,
        "families": {
            "V4_365D_LONG_TREND_LOGIT": {
                "kind": "classifier",
                "features": [
                    "return_90d", "return_180d", "return_365d",
                    "volatility_90d", "volatility_180d",
                    "distance_sma200", "trailing_drawdown_365d",
                ],
            },
            "V4_365D_LONG_REGIME_GB": {
                "kind": "classifier",
                "features": [
                    "return_90d", "return_180d", "return_365d",
                    "volatility_90d", "volatility_180d",
                    "distance_sma200", "trailing_drawdown_365d",
                    "asset_minus_btc_return_90d", "asset_minus_btc_return_180d",
                    "asset_minus_core_median_return_90d", "asset_minus_core_median_return_180d",
                    "core_breadth_positive_90d_pct", "core_breadth_positive_180d_pct",
                    "core_return_dispersion_90d", "core_return_dispersion_180d",
                    "btc_return_30d_pct", "core_breadth_above_sma50_pct", "core_median_return_30d_pct",
                    "fear_greed_index", "stablecoin_supply_usd", "stablecoin_growth_30d_pct",
                    "dollar_index", "vix", "macro_liquidity_score", "risk_appetite_score",
                ],
            },
            "V4_365D_RETURN_MAGNITUDE_ENSEMBLE": {
                "kind": "regressor_ensemble",
                "features": [
                    "return_90d", "return_180d", "return_365d",
                    "volatility_90d", "volatility_180d",
                    "distance_sma200", "trailing_drawdown_365d",
                    "asset_minus_btc_return_90d", "asset_minus_btc_return_180d",
                    "asset_minus_core_median_return_90d", "asset_minus_core_median_return_180d",
                    "core_breadth_positive_90d_pct", "core_breadth_positive_180d_pct",
                    "core_return_dispersion_90d", "core_return_dispersion_180d",
                    "btc_return_30d_pct", "core_breadth_above_sma50_pct", "core_median_return_30d_pct",
                    "fear_greed_index", "stablecoin_supply_usd", "stablecoin_growth_30d_pct",
                    "dollar_index", "vix", "macro_liquidity_score", "risk_appetite_score",
                ],
            },
        },
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_price_features(asset_frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    frame = asset_frame.sort_values("observation_date").copy().reset_index(drop=True)
    price = frame["price_usd"].astype(float)
    one_day = price.pct_change(fill_method=None)
    out = pd.DataFrame({"observation_date": pd.to_datetime(frame["observation_date"])})
    for window in (1, 3, 7, 14, 30, 60, 90, 180, 365):
        out[f"return_{window}d"] = price.pct_change(window, fill_method=None)
    for window in (7, 14, 30, 60, 90, 180):
        out[f"volatility_{window}d"] = one_day.rolling(window).std() * math.sqrt(365)
    for window in (20, 50, 200):
        out[f"distance_sma{window}"] = price / price.rolling(window).mean() - 1.0
    out["volatility_ratio_7d_30d"] = out["volatility_7d"] / out["volatility_30d"]
    out["volatility_ratio_30d_90d"] = out["volatility_30d"] / out["volatility_90d"]
    rolling_peak = price.rolling(365, min_periods=365).max()
    out["trailing_drawdown_365d"] = price / rolling_peak - 1.0
    out["target_return"] = price.shift(-int(horizon)) / price - 1.0
    out["target_positive"] = (out["target_return"] > 0).astype(float)
    out.loc[out["target_return"].isna(), "target_positive"] = np.nan
    out["target_exceeds_15pct"] = (out["target_return"] > 0.15).astype(float)
    out.loc[out["target_return"].isna(), "target_exceeds_15pct"] = np.nan
    return out.replace([np.inf, -np.inf], np.nan)


def build_relative_market(prices: pd.DataFrame) -> pd.DataFrame:
    pivot = prices.pivot(index="observation_date", columns="asset_id", values="price_usd").sort_index()
    rows = []
    windows = (7, 14, 30, 60, 90, 180)
    returns = {window: pivot.pct_change(window, fill_method=None) for window in windows}
    medians = {window: returns[window].median(axis=1) for window in windows}
    for asset in [column for column in pivot.columns if column != ""]:
        block = pd.DataFrame(index=pivot.index)
        block["asset_id"] = asset
        for window in windows:
            r = returns[window]
            block[f"asset_minus_btc_return_{window}d"] = r[asset] - r["bitcoin"]
            block[f"asset_minus_core_median_return_{window}d"] = r[asset] - medians[window]
            block[f"core_breadth_positive_{window}d_pct"] = (r > 0).mean(axis=1) * 100.0
            block[f"core_return_dispersion_{window}d"] = r.std(axis=1)
        rows.append(block.reset_index())
    return pd.concat(rows, ignore_index=True).replace([np.inf, -np.inf], np.nan)


def attach_relative(frame: pd.DataFrame, relative: pd.DataFrame, asset: str, features: Iterable[str]) -> pd.DataFrame:
    wanted = [column for column in features if column.startswith("asset_minus_") or column.startswith("core_breadth_positive_") or column.startswith("core_return_dispersion_")]
    if not wanted:
        return frame.copy()
    available = relative[relative["asset_id"] == asset][["observation_date"] + wanted].copy()
    available["observation_date"] = pd.to_datetime(available["observation_date"]).astype("datetime64[ns]")
    out = frame.copy()
    out["observation_date"] = pd.to_datetime(out["observation_date"]).astype("datetime64[ns]")
    return out.merge(available, on="observation_date", how="left", validate="one_to_one")


def attach_lagged_native(frame: pd.DataFrame, context: pd.DataFrame, features: Iterable[str]) -> pd.DataFrame:
    wanted = [feature for feature in features if feature in NATIVE_LAG_DAYS]
    out = frame.copy().sort_values("observation_date")
    if not wanted:
        return out
    base_dates = pd.to_datetime(out["observation_date"]).astype("datetime64[ns]")
    for feature in wanted:
        lag = int(NATIVE_LAG_DAYS[feature])
        source = context[["observation_date", feature]].dropna().copy()
        source["observation_date"] = pd.to_datetime(source["observation_date"]).astype("datetime64[ns]")
        source = source.sort_values("observation_date").rename(columns={"observation_date": "source_date"})
        lookup = pd.DataFrame({"_row": out.index, "eligible_date": base_dates - pd.to_timedelta(lag, unit="D")}).sort_values("eligible_date")
        merged = pd.merge_asof(
            lookup,
            source,
            left_on="eligible_date",
            right_on="source_date",
            direction="backward",
            allow_exact_matches=True,
        ).set_index("_row")
        out[feature] = merged.reindex(out.index)[feature]
        source_dates = pd.to_datetime(merged.reindex(out.index)["source_date"])
        eligible = base_dates - pd.to_timedelta(lag, unit="D")
        require(bool((source_dates.dropna() <= eligible[source_dates.notna()]).all()), f"Lag violation for {feature}")
    return out


def candidate_features(horizon: int, family: str) -> list[str]:
    return list(CANDIDATE_CONTRACTS[int(horizon)]["families"][family]["features"])


def candidate_kind(horizon: int, family: str) -> str:
    return str(CANDIDATE_CONTRACTS[int(horizon)]["families"][family]["kind"])


def model_list(horizon: int, family: str, random_state: int):
    seed = int(random_state) + int(horizon)
    if family in {"V4_7D_SHORT_TREND_REVERSAL_LOGIT", "V4_30D_TREND_REVERSAL_LOGIT", "V4_365D_LONG_TREND_LOGIT"}:
        return [LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed)]
    if family in {"V4_7D_RELATIVE_STRENGTH_GB", "V4_30D_RELATIVE_CONTEXT_GB", "V4_365D_LONG_REGIME_GB"}:
        return [GradientBoostingClassifier(n_estimators=180, learning_rate=0.04, max_depth=2, min_samples_leaf=15, random_state=seed)]
    if family in {"V4_7D_VOLATILITY_STATE_EXTRA_TREES", "V4_30D_VOLATILITY_STATE_EXTRA_TREES"}:
        return [ExtraTreesClassifier(n_estimators=300, max_depth=8, min_samples_leaf=8, max_features=0.8, class_weight="balanced", random_state=seed, n_jobs=-1)]
    if family == "V4_365D_RETURN_MAGNITUDE_ENSEMBLE":
        return [
            GradientBoostingRegressor(n_estimators=180, learning_rate=0.04, max_depth=2, min_samples_leaf=15, loss="huber", random_state=seed),
            RandomForestRegressor(n_estimators=220, max_depth=6, min_samples_leaf=10, max_features=0.8, random_state=seed, n_jobs=-1),
            BayesianRidge(),
        ]
    raise RuntimeError(f"Unknown V4 family: {family}")


def all_candidate_families() -> list[str]:
    return [family for horizon in RECOVERY_HORIZONS for family in CANDIDATE_CONTRACTS[horizon]["families"]]
