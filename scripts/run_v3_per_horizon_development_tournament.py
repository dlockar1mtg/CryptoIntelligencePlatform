from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.module38 import ASSETS, Module38Runner
from crypto_platform.module39_validation import exact_candidates, split_capacity

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_TOURNAMENT_V3"
EVIDENCE_CLASS = "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME"
EXPECTED_V3_MANIFEST_CONTENT_SHA256 = "69a848d935509ac692d6af50f6e95d72fb3c0a22925a39d2434e678e1e5c628d"
DEVELOPMENT_FOLDS = 5
ORIGINS_PER_FOLD = 10
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

HORIZON_CONTRACTS = {
    7: {
        "base": ["return_1d", "return_7d", "return_30d", "volatility_30d", "distance_sma50"],
        "native": [],
        "relative": [
            "asset_minus_btc_return_7d",
            "asset_minus_core_median_return_7d",
            "core_return_dispersion_7d",
            "core_breadth_positive_7d_pct",
        ],
        "families": [
            "PRICE_ONLY_DIRECTION_FIRST",
            "GRADIENT_BOOSTED_DIRECTION",
            "HIST_GRADIENT_BOOSTED_DIRECTION",
            "EXTRA_TREES_DIRECTION",
            "RELATIVE_MARKET_DIRECTION",
        ],
    },
    30: {
        "base": [
            "return_7d", "return_30d", "return_90d", "volatility_30d",
            "volatility_90d", "distance_sma50", "distance_sma200",
        ],
        "native": [
            "core_breadth_above_sma50_pct",
            "core_median_return_30d_pct",
            "fear_greed_index",
        ],
        "relative": [
            "asset_minus_btc_return_7d", "asset_minus_btc_return_30d",
            "asset_minus_core_median_return_30d", "core_return_dispersion_30d",
            "core_breadth_positive_30d_pct",
        ],
        "families": [
            "PRICE_ONLY_DIRECTION_FIRST", "NATIVE_CONTEXT_DIRECTION_FIRST",
            "GRADIENT_BOOSTED_DIRECTION", "HIST_GRADIENT_BOOSTED_DIRECTION",
            "EXTRA_TREES_DIRECTION", "RELATIVE_MARKET_DIRECTION",
        ],
    },
    90: {
        "base": [
            "return_30d", "return_90d", "volatility_30d", "volatility_90d",
            "distance_sma50", "distance_sma200",
        ],
        "native": list(NATIVE_LAG_DAYS),
        "relative": [
            "asset_minus_btc_return_7d", "asset_minus_btc_return_30d",
            "asset_minus_core_median_return_7d", "asset_minus_core_median_return_30d",
            "core_return_dispersion_7d", "core_return_dispersion_30d",
            "core_breadth_positive_7d_pct", "core_breadth_positive_30d_pct",
        ],
        "families": [
            "PRICE_ONLY_DIRECTION_FIRST", "NATIVE_CONTEXT_DIRECTION_FIRST",
            "GRADIENT_BOOSTED_DIRECTION", "HIST_GRADIENT_BOOSTED_DIRECTION",
            "EXTRA_TREES_DIRECTION", "RELATIVE_MARKET_DIRECTION",
        ],
    },
    180: {
        "base": ["return_30d", "return_90d", "volatility_90d", "distance_sma50", "distance_sma200"],
        "native": list(NATIVE_LAG_DAYS),
        "relative": [
            "asset_minus_btc_return_7d", "asset_minus_btc_return_30d",
            "asset_minus_core_median_return_7d", "asset_minus_core_median_return_30d",
            "core_return_dispersion_7d", "core_return_dispersion_30d",
            "core_breadth_positive_7d_pct", "core_breadth_positive_30d_pct",
        ],
        "families": [
            "PRICE_ONLY_DIRECTION_FIRST", "NATIVE_CONTEXT_DIRECTION_FIRST",
            "GRADIENT_BOOSTED_DIRECTION", "HIST_GRADIENT_BOOSTED_DIRECTION",
            "EXTRA_TREES_DIRECTION", "RELATIVE_MARKET_DIRECTION",
        ],
    },
    365: {
        "base": ["return_90d", "volatility_90d", "distance_sma200"],
        "native": list(NATIVE_LAG_DAYS),
        "relative": [
            "asset_minus_btc_return_7d", "asset_minus_btc_return_30d",
            "asset_minus_core_median_return_7d", "asset_minus_core_median_return_30d",
            "core_return_dispersion_7d", "core_return_dispersion_30d",
            "core_breadth_positive_7d_pct", "core_breadth_positive_30d_pct",
        ],
        "families": [
            "PRICE_ONLY_DIRECTION_FIRST", "NATIVE_CONTEXT_DIRECTION_FIRST",
            "GRADIENT_BOOSTED_DIRECTION", "HIST_GRADIENT_BOOSTED_DIRECTION",
            "EXTRA_TREES_DIRECTION", "RELATIVE_MARKET_DIRECTION",
        ],
    },
}

FAMILY_SIMPLICITY_ORDER = {
    "PRICE_ONLY_DIRECTION_FIRST": 0,
    "NATIVE_CONTEXT_DIRECTION_FIRST": 1,
    "GRADIENT_BOOSTED_DIRECTION": 2,
    "HIST_GRADIENT_BOOSTED_DIRECTION": 3,
    "EXTRA_TREES_DIRECTION": 4,
    "RELATIVE_MARKET_DIRECTION": 5,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_content_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_relative_market(prices: pd.DataFrame) -> pd.DataFrame:
    pivot = prices.pivot(index="observation_date", columns="asset_id", values="price_usd").sort_index()
    ret7 = pivot.pct_change(7, fill_method=None)
    ret30 = pivot.pct_change(30, fill_method=None)
    core_median7 = ret7.median(axis=1)
    core_median30 = ret30.median(axis=1)
    rows = []
    for asset in [a for a in ASSETS if a in pivot.columns]:
        frame = pd.DataFrame(index=pivot.index)
        frame["asset_id"] = asset
        frame["asset_minus_btc_return_7d"] = ret7[asset] - ret7["bitcoin"]
        frame["asset_minus_btc_return_30d"] = ret30[asset] - ret30["bitcoin"]
        frame["asset_minus_core_median_return_7d"] = ret7[asset] - core_median7
        frame["asset_minus_core_median_return_30d"] = ret30[asset] - core_median30
        frame["core_return_dispersion_7d"] = ret7.std(axis=1)
        frame["core_return_dispersion_30d"] = ret30.std(axis=1)
        frame["core_breadth_positive_7d_pct"] = (ret7 > 0).mean(axis=1) * 100
        frame["core_breadth_positive_30d_pct"] = (ret30 > 0).mean(axis=1) * 100
        rows.append(frame.reset_index())
    return pd.concat(rows, ignore_index=True)


def attach_lagged_native(frame: pd.DataFrame, context: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    out = frame.copy().sort_values("observation_date")
    if not features:
        return out
    base_dates = pd.to_datetime(out["observation_date"])
    for feature in features:
        lag = int(NATIVE_LAG_DAYS[feature])
        source = context[["observation_date", feature]].dropna().copy()
        source["observation_date"] = pd.to_datetime(source["observation_date"])
        source = source.sort_values("observation_date").rename(columns={"observation_date": "source_date"})
        lookup = pd.DataFrame({
            "_row": out.index,
            "eligible_date": base_dates - pd.to_timedelta(lag, unit="D"),
        }).sort_values("eligible_date")
        merged = pd.merge_asof(
            lookup,
            source.sort_values("source_date"),
            left_on="eligible_date",
            right_on="source_date",
            direction="backward",
            allow_exact_matches=True,
        ).set_index("_row")
        out[feature] = merged.reindex(out.index)[feature]
        out[f"__source_date__{feature}"] = merged.reindex(out.index)["source_date"]
        eligible = base_dates - pd.to_timedelta(lag, unit="D")
        source_dates = pd.to_datetime(out[f"__source_date__{feature}"])
        require(bool((source_dates.dropna() <= eligible[source_dates.notna()]).all()), f"Lag violation for {feature}")
    return out


def attach_relative(frame: pd.DataFrame, relative: pd.DataFrame, asset: str, features: list[str]) -> pd.DataFrame:
    if not features:
        return frame.copy()
    rel = relative[relative["asset_id"] == asset][["observation_date"] + features].copy()
    rel["observation_date"] = pd.to_datetime(rel["observation_date"])
    return frame.merge(rel, on="observation_date", how="left")


def split_origin(
    features: pd.DataFrame,
    origin_idx: int,
    horizon: int,
    runner: Module38Runner,
    excluded_dates: set[str],
) -> tuple[pd.Timestamp, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    origin_date = pd.Timestamp(features.iloc[origin_idx]["observation_date"])
    dates = pd.to_datetime(features["observation_date"])
    due_mask = (dates + pd.to_timedelta(horizon, unit="D") <= origin_date) & (dates < origin_date)
    available = features.loc[due_mask].copy()
    available = available[
        ~pd.to_datetime(available["observation_date"]).dt.date.astype(str).isin(excluded_dates)
    ].copy()
    cfg = runner.cfg
    validation_rows, train_end = split_capacity(
        usable_rows=len(available),
        horizon=horizon,
        minimum_training_rows=int(cfg.get("absolute_minimum_training_rows", 90)),
        minimum_validation_rows=int(cfg.get("minimum_validation_rows", 30)),
        configured_validation=int(cfg["validation_rows"]),
        maximum_validation_share=float(cfg.get("maximum_validation_share", 0.25)),
    )
    require(validation_rows >= int(cfg.get("minimum_validation_rows", 30)), "Unsafe internal validation split")
    require(train_end >= int(cfg.get("absolute_minimum_training_rows", 90)), "Unsafe purged training split")
    validation_start = len(available) - validation_rows
    train = available.iloc[:train_end].copy()
    validation = available.iloc[validation_start:].copy()
    current = features.iloc[[origin_idx]].copy()
    require(pd.Timestamp(train["observation_date"].iloc[-1]) < origin_date, "Development chronology violation")
    return origin_date, train, validation, current


def model_list(family: str, random_state: int, horizon: int):
    seed = int(random_state) + int(horizon)
    if family in {"PRICE_ONLY_DIRECTION_FIRST", "NATIVE_CONTEXT_DIRECTION_FIRST"}:
        return [
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed),
            RandomForestClassifier(
                n_estimators=220, max_depth=6, min_samples_leaf=10, max_features=0.8,
                class_weight="balanced_subsample", random_state=seed, n_jobs=-1,
            ),
        ]
    if family == "GRADIENT_BOOSTED_DIRECTION":
        return [GradientBoostingClassifier(
            n_estimators=180, learning_rate=0.04, max_depth=2,
            min_samples_leaf=15, random_state=seed,
        )]
    if family == "HIST_GRADIENT_BOOSTED_DIRECTION":
        return [HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=180, max_leaf_nodes=15,
            min_samples_leaf=15, l2_regularization=0.1, random_state=seed,
        )]
    if family == "EXTRA_TREES_DIRECTION":
        return [ExtraTreesClassifier(
            n_estimators=300, max_depth=8, min_samples_leaf=8, max_features=0.8,
            class_weight="balanced", random_state=seed, n_jobs=-1,
        )]
    if family == "RELATIVE_MARKET_DIRECTION":
        return [
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed),
            RandomForestClassifier(
                n_estimators=220, max_depth=6, min_samples_leaf=10, max_features=0.8,
                class_weight="balanced_subsample", random_state=seed, n_jobs=-1,
            ),
            GradientBoostingClassifier(
                n_estimators=180, learning_rate=0.04, max_depth=2,
                min_samples_leaf=15, random_state=seed,
            ),
        ]
    raise RuntimeError(f"Unknown candidate family: {family}")


def family_columns(family: str, contract: dict) -> list[str]:
    base = list(contract["base"])
    native = list(contract["native"])
    relative = list(contract["relative"])
    if family == "PRICE_ONLY_DIRECTION_FIRST":
        return base
    if family == "NATIVE_CONTEXT_DIRECTION_FIRST":
        return base + native
    if family in {"GRADIENT_BOOSTED_DIRECTION", "HIST_GRADIENT_BOOSTED_DIRECTION", "EXTRA_TREES_DIRECTION"}:
        return base + native
    if family == "RELATIVE_MARKET_DIRECTION":
        return base + native + relative
    raise RuntimeError(f"Unknown family: {family}")


def fit_probability(train: pd.DataFrame, validation: pd.DataFrame, current: pd.DataFrame, columns: list[str], family: str, random_state: int, horizon: int) -> float:
    train = train.dropna(subset=columns + ["target_return"]).copy()
    validation = validation.dropna(subset=columns + ["target_return"]).copy()
    current = current.dropna(subset=columns).copy()
    require(len(train) >= 90, f"Insufficient complete training rows for {family}")
    require(len(validation) >= 30, f"Insufficient complete validation rows for {family}")
    require(len(current) == 1, f"Missing required current features for {family}")

    x_train = train[columns].astype(float).copy()
    x_val = validation[columns].astype(float).copy()
    x_current = current[columns].astype(float).copy()
    lo = x_train.min(axis=0)
    hi = x_train.max(axis=0)
    x_val = x_val.clip(lower=lo, upper=hi, axis=1)
    x_current = x_current.clip(lower=lo, upper=hi, axis=1)

    scaler = StandardScaler()
    tx = scaler.fit_transform(x_train)
    vx = scaler.transform(x_val)
    cx = scaler.transform(x_current)
    y_train = (train["target_return"].to_numpy(dtype=float) > 0).astype(int)
    y_val = (validation["target_return"].to_numpy(dtype=float) > 0).astype(int)
    if len(np.unique(y_train)) < 2:
        return float(y_train.mean())

    probs = []
    weights = []
    for model in model_list(family, random_state, horizon):
        model.fit(tx, y_train)
        val_prob = np.clip(model.predict_proba(vx)[:, 1], 1e-4, 1 - 1e-4)
        current_prob = float(model.predict_proba(cx)[0, 1])
        score = float(brier_score_loss(y_val, val_prob))
        probs.append(current_prob)
        weights.append(1.0 / max(score, 1e-6))
    w = np.asarray(weights, dtype=float)
    w /= w.sum()
    return float(np.dot(w, np.asarray(probs, dtype=float)))


def chronological_calibrated_brier(frame: pd.DataFrame) -> float:
    ordered = frame.sort_values(["forecast_date", "asset_id"]).reset_index(drop=True)
    split = max(30, int(len(ordered) * 0.60))
    require(split < len(ordered), "Insufficient development rows for calibration assessment")
    development = ordered.iloc[:split].copy()
    test = ordered.iloc[split:].copy()
    x = development[["raw_probability_positive"]].to_numpy(dtype=float)
    y = development["observed_positive"].astype(int).to_numpy()
    if len(np.unique(y)) < 2 or development["raw_probability_positive"].nunique() < 2:
        calibrated = np.repeat(float(y.mean()) if len(y) else 0.5, len(test))
    else:
        calibrator = LogisticRegression(max_iter=1000).fit(x, y)
        calibrated = calibrator.predict_proba(test[["raw_probability_positive"]].to_numpy(dtype=float))[:, 1]
    return float(brier_score_loss(test["observed_positive"].astype(int), np.clip(calibrated, 1e-4, 1 - 1e-4)))


def summarize_family(frame: pd.DataFrame) -> dict:
    model_correct = (frame["predicted_positive"].astype(int) == frame["observed_positive"].astype(int)).astype(int)
    baseline_correct = (frame["baseline_positive"].astype(int) == frame["observed_positive"].astype(int)).astype(int)
    direction = float(model_correct.mean() * 100)
    baseline = float(baseline_correct.mean() * 100)
    raw_brier = float(brier_score_loss(frame["observed_positive"].astype(int), np.clip(frame["raw_probability_positive"].astype(float), 1e-4, 1 - 1e-4)))
    calibrated_brier = chronological_calibrated_brier(frame)
    by_asset = {}
    positive_contributions = []
    for asset, group in frame.groupby("asset_id"):
        mc = (group["predicted_positive"].astype(int) == group["observed_positive"].astype(int)).astype(int)
        bc = (group["baseline_positive"].astype(int) == group["observed_positive"].astype(int)).astype(int)
        delta = float((mc.mean() - bc.mean()) * 100)
        contribution = int(mc.sum() - bc.sum())
        by_asset[str(asset)] = {
            "rows": int(len(group)),
            "directional_accuracy_pct": float(mc.mean() * 100),
            "baseline_accuracy_pct": float(bc.mean() * 100),
            "baseline_adjusted_skill_pp": delta,
            "net_correct_gain_vs_baseline": contribution,
        }
        positive_contributions.append(max(0, contribution))
    nonnegative_assets = sum(1 for row in by_asset.values() if float(row["baseline_adjusted_skill_pp"]) >= 0)
    total_positive = int(sum(positive_contributions))
    max_positive = int(max(positive_contributions)) if positive_contributions else 0
    single_asset_majority = bool(total_positive > 0 and max_positive > total_positive / 2)

    ordered = frame.sort_values(["asset_id", "forecast_date"]).copy()
    ordered["position"] = np.where(ordered["predicted_positive"].astype(int) == 1, 1.0, -1.0)
    ordered["previous_position"] = ordered.groupby("asset_id")["position"].shift(1).fillna(0.0)
    ordered["turnover"] = (ordered["position"] - ordered["previous_position"]).abs()
    ordered["strategy_return_pct_after_cost"] = (
        ordered["position"] * ordered["actual_return_pct"]
        - ordered["turnover"] * (TRANSACTION_COST_BPS / 100.0)
    )

    delta = direction - baseline
    qualifies = bool(delta > 0 and nonnegative_assets >= 3 and not single_asset_majority)
    return {
        "development_rows": int(len(frame)),
        "directional_accuracy_pct": direction,
        "development_majority_baseline_accuracy_pct": baseline,
        "model_minus_development_majority_accuracy_pct_points": delta,
        "raw_brier_score": raw_brier,
        "leakage_safe_calibrated_brier_score": calibrated_brier,
        "assets_nonnegative_baseline_adjusted_skill": int(nonnegative_assets),
        "single_asset_explains_majority_of_positive_gain": single_asset_majority,
        "mean_sign_strategy_return_pct_after_15bps_cost": float(ordered["strategy_return_pct_after_cost"].mean()),
        "turnover_units": float(ordered["turnover"].sum()),
        "by_asset": by_asset,
        "development_selection_gate_pass": qualifies,
    }


def choose_winner(results: dict) -> str | None:
    eligible = [(family, metrics) for family, metrics in results.items() if metrics["development_selection_gate_pass"]]
    if not eligible:
        return None
    eligible.sort(key=lambda item: (
        -float(item[1]["model_minus_development_majority_accuracy_pct_points"]),
        -float(item[1]["directional_accuracy_pct"]),
        float(item[1]["leakage_safe_calibrated_brier_score"]),
        float(item[1]["raw_brier_score"]),
        int(FAMILY_SIMPLICITY_ORDER[item[0]]),
    ))
    return eligible[0][0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v2-manifest", required=True)
    parser.add_argument("--v3-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    v2_path = Path(args.v2_manifest).resolve()
    v3_path = Path(args.v3_manifest).resolve()
    output = Path(args.output).resolve()
    require(source.is_file(), f"Database missing: {source}")
    require(v2_path.is_file(), f"V2 manifest missing: {v2_path}")
    require(v3_path.is_file(), f"V3 manifest missing: {v3_path}")
    require(not output.exists(), f"Development tournament output already exists: {output}")

    before_db = sha256(source)
    before_v2 = sha256(v2_path)
    before_v3 = sha256(v3_path)
    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v3 = json.loads(v3_path.read_text(encoding="utf-8"))
    require(v3["experiment_id"] == EXPERIMENT_ID, "Unexpected V3 manifest experiment id")
    require(v3["holdout_outcomes_viewed_before_freeze"] is False, "V3 holdout was not pre-outcome frozen")
    require(v3["manifest_content_sha256"] == EXPECTED_V3_MANIFEST_CONTENT_SHA256, "Unexpected V3 manifest content hash")
    require(manifest_content_hash(v3) == EXPECTED_V3_MANIFEST_CONTENT_SHA256, "V3 manifest canonical hash mismatch")
    require(int(v3["supported_groups"]) == 29, "Expected 29 V3 supported groups")
    require(int(v3["rows_per_supported_group"]) == 10, "Expected 10 V3 holdout rows per group")

    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in v2["groups"]}
    v3_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_holdout_origin_dates"]) for g in v3["groups"]}
    require(set(v2_dates) == set(v3_dates), "V2/V3 supported group mismatch")
    require(all(v2_dates[k].isdisjoint(v3_dates[k]) for k in v2_dates), "V2/V3 holdout overlap detected")

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v3_tournament_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import load_all, connect
            settings, _ = load_all()
            conn = connect(settings)
            runner = object.__new__(Module38Runner)
            runner.cfg = settings["module38"]
            prices = conn.execute(
                """
                SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd
                FROM canonical_market_daily
                WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
                  AND price_usd IS NOT NULL
                ORDER BY observation_date, asset_id
                """
            ).fetchdf()
            prices["observation_date"] = pd.to_datetime(prices["observation_date"])
            context = conn.execute(
                "SELECT observation_date," + ",".join(NATIVE_LAG_DAYS) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
            context["observation_date"] = pd.to_datetime(context["observation_date"])
            relative = build_relative_market(prices)
            relative["observation_date"] = pd.to_datetime(relative["observation_date"])

            rows_by_horizon_family: dict[int, dict[str, list[dict]]] = {
                h: {family: [] for family in HORIZON_CONTRACTS[h]["families"]}
                for h in HORIZON_CONTRACTS
            }
            random_state = int(runner.cfg["random_state"])

            for asset in ASSETS:
                asset_frame = prices[prices["asset_id"] == asset].copy()
                for horizon, contract in HORIZON_CONTRACTS.items():
                    key = (asset, horizon)
                    if key not in v3_dates:
                        continue
                    features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
                    # Final-holdout labels are mechanically masked before any development selection or split.
                    v3_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(v3_dates[key])
                    features.loc[v3_mask, "target_return"] = np.nan
                    candidates = exact_candidates(
                        features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"}),
                        horizon,
                        int(runner.cfg.get("absolute_minimum_training_rows", 90)),
                        int(runner.cfg.get("minimum_validation_rows", 30)),
                        int(runner.cfg["validation_rows"]),
                        float(runner.cfg.get("maximum_validation_share", 0.25)),
                    )
                    candidate_frame = features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"})
                    safe_indices = []
                    for candidate_pos in candidates:
                        original_idx = int(candidate_frame.iloc[candidate_pos]["_original_index"])
                        date_key = pd.Timestamp(features.iloc[original_idx]["observation_date"]).date().isoformat()
                        if date_key in v2_dates[key] or date_key in v3_dates[key]:
                            continue
                        safe_indices.append(original_idx)
                    required = DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD
                    require(len(safe_indices) >= required, f"Insufficient development origins for {asset} {horizon}d")
                    positions = np.linspace(0, len(safe_indices) - 1, required, dtype=int)
                    selected = [safe_indices[int(pos)] for pos in positions]
                    excluded = set(v2_dates[key]) | set(v3_dates[key])

                    for fold_id in range(DEVELOPMENT_FOLDS):
                        fold_indices = selected[fold_id * ORIGINS_PER_FOLD:(fold_id + 1) * ORIGINS_PER_FOLD]
                        for origin_idx in fold_indices:
                            origin_date, train, validation, current = split_origin(
                                features, origin_idx, horizon, runner, excluded
                            )
                            actual = float(features.iloc[origin_idx]["target_return"])
                            baseline_positive = int((train["target_return"].astype(float) > 0).mean() >= 0.5)

                            train = attach_lagged_native(train, context, contract["native"])
                            validation = attach_lagged_native(validation, context, contract["native"])
                            current = attach_lagged_native(current, context, contract["native"])
                            train = attach_relative(train, relative, asset, contract["relative"])
                            validation = attach_relative(validation, relative, asset, contract["relative"])
                            current = attach_relative(current, relative, asset, contract["relative"])

                            for family in contract["families"]:
                                columns = family_columns(family, contract)
                                probability = fit_probability(
                                    train, validation, current, columns, family, random_state, horizon
                                )
                                rows_by_horizon_family[horizon][family].append({
                                    "asset_id": asset,
                                    "horizon_days": horizon,
                                    "fold_id": fold_id + 1,
                                    "forecast_date": origin_date.date().isoformat(),
                                    "observed_positive": int(actual > 0),
                                    "actual_return_pct": actual * 100,
                                    "baseline_positive": baseline_positive,
                                    "raw_probability_positive": probability,
                                    "predicted_positive": int(probability >= 0.5),
                                })
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    require(sha256(source) == before_db, "Source database changed during V3 development tournament")
    require(sha256(v2_path) == before_v2, "V2 manifest changed during V3 development tournament")
    require(sha256(v3_path) == before_v3, "V3 manifest changed during development tournament")

    horizon_results = {}
    winners = {}
    for horizon, family_rows in rows_by_horizon_family.items():
        family_results = {}
        for family, rows in family_rows.items():
            frame = pd.DataFrame(rows)
            expected_assets = 5 if horizon == 365 else 6
            expected_rows = expected_assets * DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD
            require(len(frame) == expected_rows, f"Unexpected development row count for {horizon}d {family}")
            family_results[family] = summarize_family(frame)
        winner = choose_winner(family_results)
        horizon_results[str(horizon)] = {
            "candidate_results": family_results,
            "selected_development_winner": winner,
            "qualified_winner_exists": winner is not None,
        }
        winners[str(horizon)] = winner

    all_winners_frozen = all(winner is not None for winner in winners.values())
    report = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": EVIDENCE_CLASS,
        "strict_point_in_time_claim_allowed": False,
        "development_folds": DEVELOPMENT_FOLDS,
        "origins_per_fold_per_supported_asset": ORIGINS_PER_FOLD,
        "v2_consumed_origins_excluded_from_selection_training_and_validation": True,
        "v3_final_holdout_origins_excluded_from_selection_training_and_validation": True,
        "v3_final_holdout_outcomes_viewed": False,
        "governed_native_context_lags_enforced": True,
        "recommendation_policy_changed": False,
        "production_promotion_allowed": False,
        "horizon_results": horizon_results,
        "selected_winners": winners,
        "all_five_horizons_have_qualified_winners": all_winners_frozen,
        "next_gate": "FREEZE_V3_HORIZON_WINNERS_BEFORE_FINAL_HOLDOUT" if all_winners_frozen else "REVIEW_HORIZONS_WITH_NO_QUALIFIED_DEVELOPMENT_WINNER_WITHOUT_VIEWING_V3_HOLDOUT",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("CRYPTO_V3_PER_HORIZON_DEVELOPMENT_TOURNAMENT=COMPLETE")
    print(f"EVIDENCE_CLASS={EVIDENCE_CLASS}")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("GOVERNED_NATIVE_CONTEXT_LAGS_ENFORCED=TRUE")
    print(f"ALL_FIVE_HORIZONS_HAVE_QUALIFIED_WINNERS={str(all_winners_frozen).upper()}")
    for horizon in [7, 30, 90, 180, 365]:
        print(f"WINNER_{horizon}D={winners[str(horizon)] or 'NO_QUALIFIED_WINNER'}")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
