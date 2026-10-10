from __future__ import annotations

import hashlib
import inspect
import json
import math
import platform as _platform
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler

from crypto_platform.module38 import ASSETS, Module38Runner

TEST_ORIGINS_PER_FOLD = 10


def clip_probability(values):
    return np.clip(np.asarray(values, dtype=float), 1e-4, 1 - 1e-4)


def split_capacity(
    usable_rows: int,
    horizon: int,
    minimum_training_rows: int,
    minimum_validation_rows: int,
    configured_validation: int,
    maximum_validation_share: float,
) -> tuple[int, int]:
    adaptive_validation = min(
        configured_validation,
        max(minimum_validation_rows, int(usable_rows * maximum_validation_share)),
    )
    adaptive_validation = min(
        adaptive_validation,
        usable_rows - minimum_training_rows,
    )
    if adaptive_validation < minimum_validation_rows:
        return adaptive_validation, -1
    validation_start = usable_rows - adaptive_validation
    train_end = validation_start - int(horizon)
    return adaptive_validation, train_end


def exact_candidates(
    features: pd.DataFrame,
    horizon: int,
    minimum_training_rows: int,
    minimum_validation_rows: int,
    configured_validation: int,
    maximum_validation_share: float,
) -> list[int]:
    dates = pd.to_datetime(features["observation_date"])
    candidates: list[int] = []
    for idx in range(len(features)):
        origin = dates.iloc[idx]
        due_mask = (
            dates + pd.to_timedelta(horizon, unit="D") <= origin
        ) & (dates < origin)
        usable_rows = int(due_mask.sum())
        adaptive_validation, train_end = split_capacity(
            usable_rows=usable_rows,
            horizon=horizon,
            minimum_training_rows=minimum_training_rows,
            minimum_validation_rows=minimum_validation_rows,
            configured_validation=configured_validation,
            maximum_validation_share=maximum_validation_share,
        )
        if (
            adaptive_validation >= minimum_validation_rows
            and train_end >= minimum_training_rows
        ):
            candidates.append(idx)
    return candidates


def select_groups(candidates: list[int], folds: int) -> list[list[int]]:
    required = folds * TEST_ORIGINS_PER_FOLD
    if len(candidates) < required:
        raise RuntimeError("Candidate selection called without sufficient evidence")
    positions = np.linspace(0, len(candidates) - 1, required, dtype=int)
    chosen = [candidates[int(pos)] for pos in positions]
    return [
        chosen[i * TEST_ORIGINS_PER_FOLD:(i + 1) * TEST_ORIGINS_PER_FOLD]
        for i in range(folds)
    ]


def point_in_time_prediction(
    runner: Module38Runner,
    features: pd.DataFrame,
    origin_idx: int,
    horizon: int,
    conformal_alpha: float,
) -> dict:
    origin_date = pd.Timestamp(features.iloc[origin_idx]["observation_date"])
    dates = pd.to_datetime(features["observation_date"])
    due_mask = (
        dates + pd.to_timedelta(horizon, unit="D") <= origin_date
    ) & (dates < origin_date)
    available = features.loc[due_mask].copy()

    cfg = runner.cfg
    minimum_training_rows = int(cfg.get("absolute_minimum_training_rows", 90))
    minimum_validation_rows = int(cfg.get("minimum_validation_rows", 30))
    configured_validation = int(cfg["validation_rows"])
    maximum_validation_share = float(cfg.get("maximum_validation_share", 0.25))

    usable_rows = len(available)
    adaptive_validation, train_end = split_capacity(
        usable_rows=usable_rows,
        horizon=horizon,
        minimum_training_rows=minimum_training_rows,
        minimum_validation_rows=minimum_validation_rows,
        configured_validation=configured_validation,
        maximum_validation_share=maximum_validation_share,
    )
    if adaptive_validation < minimum_validation_rows:
        raise RuntimeError(f"Insufficient internal validation at {origin_date.date()}")
    if train_end < minimum_training_rows:
        raise RuntimeError(f"Insufficient purged train at {origin_date.date()}")

    validation_start = usable_rows - adaptive_validation
    train = available.iloc[:train_end].copy()
    validation = available.iloc[validation_start:].copy()
    current = features.iloc[[origin_idx]].copy()

    columns = [
        c for c in train.columns
        if c not in {"observation_date", "target_return"}
    ]
    train_x = train[columns].astype(float).copy()
    val_x = validation[columns].astype(float).copy()
    current_x = current[columns].astype(float).copy()
    training_min = train_x.min(axis=0)
    training_max = train_x.max(axis=0)
    val_x = val_x.clip(lower=training_min, upper=training_max, axis=1)
    current_x = current_x.clip(lower=training_min, upper=training_max, axis=1)

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_x)
    x_val = scaler.transform(val_x)
    x_current = scaler.transform(current_x)
    y_train = train["target_return"].to_numpy(dtype=float)
    y_val = validation["target_return"].to_numpy(dtype=float)

    predictions = []
    residuals = []
    raw_weights = []
    for model in runner.model_suite(int(cfg["random_state"]) + horizon).values():
        model.fit(x_train, y_train)
        val_pred = model.predict(x_val)
        current_pred = float(model.predict(x_current)[0])
        mae = float(np.mean(np.abs(y_val - val_pred)))
        raw_weights.append(1 / max(mae, 1e-6))
        predictions.append(current_pred)
        residuals.extend((y_val - val_pred).tolist())

    weights = np.asarray(raw_weights, dtype=float)
    weights /= weights.sum()
    ensemble = float(np.dot(weights, np.asarray(predictions, dtype=float)))
    residual_array = np.asarray(residuals, dtype=float)
    probability_positive = float(np.mean(ensemble + residual_array > 0))
    half_width = float(
        np.quantile(np.abs(residual_array), max(0.0, min(1.0, 1 - conformal_alpha)))
    ) if len(residual_array) else 0.0

    actual = float(features.iloc[origin_idx]["target_return"])
    lower = ensemble - half_width
    upper = ensemble + half_width
    return {
        "forecast_date": pd.Timestamp(origin_date).date(),
        "training_end_date": pd.Timestamp(train["observation_date"].iloc[-1]).date(),
        "predicted_return_pct": ensemble * 100,
        "actual_return_pct": actual * 100,
        "raw_probability_positive": probability_positive,
        "observed_positive": int(actual > 0),
        "training_rows": int(len(train)),
        "internal_validation_rows": int(len(validation)),
        "lower_return_pct": lower * 100,
        "upper_return_pct": upper * 100,
        "interval_covered": bool(lower <= actual <= upper),
    }


# ---------------------------------------------------------------------------
# Replay origin cache
#
# Each replay origin is an independent fit that depends only on: the feature rows that
# were due (matured) before the origin, the origin row itself, the horizon, the Module 38
# configuration, conformal_alpha, and the code and library versions that do the fit.
# About half of the ~900 daily origins are the same as the day before, so their results
# are stored and reused when every one of those inputs is unchanged. A changed input row,
# setting, code line or library version gives a different key, and the origin is
# recomputed. A cache hit returns the stored values exactly (DuckDB DOUBLE, DATE,
# INTEGER and BOOLEAN round-trip Python values without loss).
# ---------------------------------------------------------------------------

REPLAY_CACHE_VERSION = "m39-replay-origin-cache-v1"
REPLAY_CACHE_TABLE = "m39_replay_origin_cache"
# Entries not used for this many days are deleted.
REPLAY_CACHE_RETENTION_DAYS = 45

# Field order of point_in_time_prediction's result; replay frames keep this column order.
REPLAY_RESULT_FIELDS = (
    "forecast_date",
    "training_end_date",
    "predicted_return_pct",
    "actual_return_pct",
    "raw_probability_positive",
    "observed_positive",
    "training_rows",
    "internal_validation_rows",
    "lower_return_pct",
    "upper_return_pct",
    "interval_covered",
)

REPLAY_CACHE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {REPLAY_CACHE_TABLE}(
    asset_id VARCHAR,
    horizon_days INTEGER,
    origin_date DATE,
    input_hash VARCHAR,
    config_hash VARCHAR,
    forecast_date DATE,
    training_end_date DATE,
    predicted_return_pct DOUBLE,
    actual_return_pct DOUBLE,
    raw_probability_positive DOUBLE,
    observed_positive INTEGER,
    training_rows INTEGER,
    internal_validation_rows INTEGER,
    lower_return_pct DOUBLE,
    upper_return_pct DOUBLE,
    interval_covered BOOLEAN,
    created_at_utc TIMESTAMPTZ,
    last_used_at_utc TIMESTAMPTZ,
    PRIMARY KEY(asset_id, horizon_days, origin_date, input_hash, config_hash)
);
"""


def _hash_frame(digest, frame: pd.DataFrame) -> None:
    digest.update(json.dumps([str(c) for c in frame.columns]).encode())
    digest.update(str(len(frame)).encode())
    for column in frame.columns:
        values = frame[column].to_numpy()
        digest.update(str(values.dtype).encode())
        if values.dtype.kind in "biufcmM":
            digest.update(np.ascontiguousarray(values).tobytes())
        else:
            digest.update(repr(values.tolist()).encode())


def replay_input_hash(features: pd.DataFrame, origin_idx: int, horizon: int) -> str:
    """Hash of exactly the rows point_in_time_prediction reads for this origin."""
    origin_date = pd.Timestamp(features.iloc[origin_idx]["observation_date"])
    dates = pd.to_datetime(features["observation_date"])
    due_mask = (
        dates + pd.to_timedelta(horizon, unit="D") <= origin_date
    ) & (dates < origin_date)
    digest = hashlib.sha256()
    digest.update(f"horizon={int(horizon)};origin={origin_date.isoformat()}".encode())
    _hash_frame(digest, features.loc[due_mask])
    digest.update(b"|origin-row|")
    _hash_frame(digest, features.iloc[[origin_idx]])
    return digest.hexdigest()


def replay_config_hash(m38_cfg: dict, conformal_alpha: float) -> str:
    """Hash of the settings, code and library versions that determine a replay fit."""
    code = [
        inspect.getsource(function)
        for function in (
            point_in_time_prediction,
            split_capacity,
            clip_probability,
            Module38Runner.model_suite,
        )
    ]
    payload = {
        "cache_version": REPLAY_CACHE_VERSION,
        "module38_config": m38_cfg,
        "conformal_alpha": float(conformal_alpha),
        "code": code,
        "versions": {
            "python": _platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "scipy": scipy.__version__,
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def _utc_timestamp(value) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


class ReplayOriginCache:
    """Stores replay origin results in DuckDB. Any cache error falls back to computing."""

    def __init__(self, conn, config_hash: str):
        self.conn = conn
        self.config_hash = config_hash
        self.enabled = True
        self.hits = 0
        self.misses = 0
        self._entries: dict[tuple, dict] = {}
        self._created: dict[tuple, object] = {}
        self._used: dict[tuple, dict] = {}
        try:
            conn.execute(REPLAY_CACHE_SCHEMA)
            rows = conn.execute(
                f"""
                SELECT asset_id, horizon_days, origin_date, input_hash, created_at_utc,
                       {", ".join(REPLAY_RESULT_FIELDS)}
                FROM {REPLAY_CACHE_TABLE}
                WHERE config_hash = ?
                """,
                [config_hash],
            ).fetchall()
        except Exception as exc:
            print(f"Module 39 replay cache unavailable ({exc}); computing every origin.")
            self.enabled = False
            return
        for row in rows:
            key = (str(row[0]), int(row[1]), row[2], str(row[3]))
            self._created[key] = row[4]
            self._entries[key] = dict(zip(REPLAY_RESULT_FIELDS, row[5:]))

    @staticmethod
    def key(asset_id, horizon, features, origin_idx) -> tuple:
        origin_date = pd.Timestamp(features.iloc[origin_idx]["observation_date"]).date()
        return (
            str(asset_id),
            int(horizon),
            origin_date,
            replay_input_hash(features, origin_idx, horizon),
        )

    def get(self, key: tuple) -> dict | None:
        if not self.enabled:
            return None
        entry = self._entries.get(key)
        if entry is None:
            return None
        self.hits += 1
        self._used[key] = entry
        return dict(entry)

    def put(self, key: tuple, result: dict) -> None:
        self.misses += 1
        if not self.enabled:
            return
        entry = {field: result[field] for field in REPLAY_RESULT_FIELDS}
        self._entries[key] = entry
        self._used[key] = entry

    def flush(self) -> None:
        if not self.enabled or not self._used:
            return
        now = datetime.now(timezone.utc)
        records = []
        for key, entry in self._used.items():
            record = {
                "asset_id": key[0],
                "horizon_days": key[1],
                "origin_date": pd.Timestamp(key[2]),
                "input_hash": key[3],
                "config_hash": self.config_hash,
            }
            for field in REPLAY_RESULT_FIELDS:
                value = entry[field]
                if field in {"forecast_date", "training_end_date"}:
                    value = pd.Timestamp(value)
                record[field] = value
            created = self._created.get(key)
            record["created_at_utc"] = _utc_timestamp(created if created is not None else now)
            record["last_used_at_utc"] = _utc_timestamp(now)
            records.append(record)
        frame = pd.DataFrame.from_records(records)
        for field in ("predicted_return_pct", "actual_return_pct", "raw_probability_positive",
                      "lower_return_pct", "upper_return_pct"):
            frame[field] = frame[field].astype("float64")
        frame["interval_covered"] = frame["interval_covered"].astype(bool)
        try:
            self.conn.register("_m39_replay_cache_stage", frame)
            self.conn.execute(
                f"""
                INSERT OR REPLACE INTO {REPLAY_CACHE_TABLE}
                SELECT asset_id, CAST(horizon_days AS INTEGER), CAST(origin_date AS DATE),
                       input_hash, config_hash,
                       CAST(forecast_date AS DATE), CAST(training_end_date AS DATE),
                       predicted_return_pct, actual_return_pct, raw_probability_positive,
                       CAST(observed_positive AS INTEGER), CAST(training_rows AS INTEGER),
                       CAST(internal_validation_rows AS INTEGER),
                       lower_return_pct, upper_return_pct, interval_covered,
                       CAST(created_at_utc AS TIMESTAMPTZ), CAST(last_used_at_utc AS TIMESTAMPTZ)
                FROM _m39_replay_cache_stage
                """
            )
            self.conn.unregister("_m39_replay_cache_stage")
            cutoff = now - timedelta(days=REPLAY_CACHE_RETENTION_DAYS)
            self.conn.execute(
                f"DELETE FROM {REPLAY_CACHE_TABLE} WHERE config_hash <> ? OR last_used_at_utc < ?",
                [self.config_hash, cutoff],
            )
        except Exception as exc:
            print(f"Module 39 replay cache could not be saved ({exc}); results are unaffected.")


def cached_point_in_time_prediction(
    cache: ReplayOriginCache | None,
    asset_id: str,
    runner: Module38Runner,
    features: pd.DataFrame,
    origin_idx: int,
    horizon: int,
    conformal_alpha: float,
) -> dict:
    if cache is None:
        return point_in_time_prediction(runner, features, origin_idx, horizon, conformal_alpha)
    key = cache.key(asset_id, horizon, features, origin_idx)
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = point_in_time_prediction(runner, features, origin_idx, horizon, conformal_alpha)
    cache.put(key, result)
    return result


def _replay_cache(conn, m38_cfg: dict, m39_cfg: dict, conformal_alpha: float):
    if not bool(m39_cfg.get("replay_cache_enabled", True)):
        return None
    try:
        config_hash = replay_config_hash(m38_cfg, conformal_alpha)
    except Exception as exc:  # e.g. source code not available to hash
        print(f"Module 39 replay cache disabled ({exc}).")
        return None
    return ReplayOriginCache(conn, config_hash)


@dataclass
class CalibrationSpec:
    method: str
    logistic_coef: float | None = None
    logistic_intercept: float | None = None
    isotonic_x: np.ndarray | None = None
    isotonic_y: np.ndarray | None = None
    empirical_rate: float | None = None


def _fit_method(method: str, frame: pd.DataFrame) -> CalibrationSpec:
    x = frame[["raw_probability_positive"]].to_numpy(dtype=float)
    y = frame["observed_positive"].astype(int).to_numpy()
    if method == "PLATT":
        model = LogisticRegression().fit(x, y)
        return CalibrationSpec(
            method="PLATT",
            logistic_coef=float(model.coef_[0][0]),
            logistic_intercept=float(model.intercept_[0]),
        )
    if method == "ISOTONIC":
        model = IsotonicRegression(out_of_bounds="clip").fit(x[:, 0], y)
        return CalibrationSpec(
            method="ISOTONIC",
            isotonic_x=np.asarray(model.X_thresholds_, dtype=float),
            isotonic_y=np.asarray(model.y_thresholds_, dtype=float),
        )
    return CalibrationSpec(
        method="EVIDENCE_SHRINKAGE",
        empirical_rate=float(frame["observed_positive"].mean()) if len(frame) else 0.5,
    )


def apply_calibration(spec: CalibrationSpec, probability: float) -> float:
    p = float(clip_probability([probability])[0])
    if spec.method == "PLATT":
        z = float(spec.logistic_intercept) + float(spec.logistic_coef) * p
        return float(1 / (1 + math.exp(-z)))
    if spec.method == "ISOTONIC":
        return float(np.interp(p, spec.isotonic_x, spec.isotonic_y))
    return float(spec.empirical_rate if spec.empirical_rate is not None else 0.5)


def calibration_evidence(rows: pd.DataFrame) -> tuple[dict, CalibrationSpec]:
    rows = rows.sort_values("forecast_date").reset_index(drop=True)
    if len(rows) < 30:
        raise RuntimeError("Calibration replay requires 30 chronological observations")
    train = rows.iloc[:15].copy()
    selection = rows.iloc[15:20].copy()
    test = rows.iloc[20:30].copy()

    raw_test = clip_probability(test["raw_probability_positive"].to_numpy())
    observed_test = test["observed_positive"].astype(int).to_numpy()
    raw_brier = float(brier_score_loss(observed_test, raw_test))
    raw_ll = float(log_loss(observed_test, raw_test, labels=[0, 1]))

    eligible = (
        train["observed_positive"].nunique() >= 2
        and train["raw_probability_positive"].nunique() >= 2
    )
    selected_method = "EVIDENCE_SHRINKAGE"
    if eligible:
        scored = []
        observed_selection = selection["observed_positive"].astype(int).to_numpy()
        for method in ("PLATT", "ISOTONIC"):
            spec = _fit_method(method, train)
            probs = np.asarray([
                apply_calibration(spec, p)
                for p in selection["raw_probability_positive"].to_numpy(dtype=float)
            ])
            score = float(brier_score_loss(observed_selection, clip_probability(probs)))
            scored.append((method, score))
        selected_method = min(scored, key=lambda item: item[1])[0]

    development = rows.iloc[:20].copy()
    if (
        selected_method != "EVIDENCE_SHRINKAGE"
        and (
            development["observed_positive"].nunique() < 2
            or development["raw_probability_positive"].nunique() < 2
        )
    ):
        selected_method = "EVIDENCE_SHRINKAGE"
    spec = _fit_method(selected_method, development)
    calibrated_test = np.asarray([
        apply_calibration(spec, p)
        for p in test["raw_probability_positive"].to_numpy(dtype=float)
    ])
    calibrated_test = clip_probability(calibrated_test)
    calibrated_brier = float(brier_score_loss(observed_test, calibrated_test))
    calibrated_ll = float(log_loss(observed_test, calibrated_test, labels=[0, 1]))
    return {
        "calibration_method": selected_method,
        "validation_rows": int(len(test)),
        "raw_brier_score": raw_brier,
        "calibrated_brier_score": calibrated_brier,
        "raw_log_loss": raw_ll,
        "calibrated_log_loss": calibrated_ll,
        "raw_mean_probability": float(raw_test.mean()),
        "calibrated_mean_probability": float(calibrated_test.mean()),
        "observed_positive_rate": float(observed_test.mean()),
        "calibration_improvement_pct": float(
            (raw_brier - calibrated_brier) / max(raw_brier, 1e-9) * 100
        ),
    }, spec


def build_true_replay_evidence(conn, settings) -> dict:
    m38_cfg = settings["module38"]
    m39_cfg = settings["module39"]
    runner = object.__new__(Module38Runner)
    runner.cfg = m38_cfg

    folds = int(m39_cfg["rolling_folds"])
    minimum_training_rows = int(m38_cfg.get("absolute_minimum_training_rows", 90))
    minimum_validation_rows = int(m38_cfg.get("minimum_validation_rows", 30))
    configured_validation = int(m38_cfg["validation_rows"])
    maximum_validation_share = float(m38_cfg.get("maximum_validation_share", 0.25))
    conformal_alpha = float(m39_cfg["conformal_alpha"])
    horizons = [int(v) for v in m38_cfg["horizons_days"]]
    required_candidates = folds * TEST_ORIGINS_PER_FOLD
    cache = _replay_cache(conn, m38_cfg, m39_cfg, conformal_alpha)

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

    replay_rows = []
    fold_rows = []
    calibration_rows = []
    calibration_specs = {}
    evidence_gaps = []

    for asset in ASSETS:
        asset_frame = prices[prices.asset_id == asset].copy()
        for horizon in horizons:
            features = runner.build_features(asset_frame, horizon).reset_index(drop=True)
            candidates = exact_candidates(
                features=features,
                horizon=horizon,
                minimum_training_rows=minimum_training_rows,
                minimum_validation_rows=minimum_validation_rows,
                configured_validation=configured_validation,
                maximum_validation_share=maximum_validation_share,
            )
            if len(candidates) < required_candidates:
                evidence_gaps.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "evidence_gap": "INSUFFICIENT_POINT_IN_TIME_REPLAY_HISTORY",
                    "available_candidates": int(len(candidates)),
                    "required_candidates": int(required_candidates),
                    "predictive_skill_certified": False,
                })
                continue

            groups = select_groups(candidates, folds)
            group_predictions = []
            for fold_number, indices in enumerate(groups, start=1):
                fold_predictions = [
                    cached_point_in_time_prediction(
                        cache,
                        asset,
                        runner,
                        features,
                        idx,
                        horizon,
                        conformal_alpha,
                    )
                    for idx in indices
                ]
                frame = pd.DataFrame(fold_predictions)
                frame["asset_id"] = asset
                frame["horizon_days"] = horizon
                frame["fold_number"] = fold_number
                replay_rows.extend(frame.to_dict("records"))
                group_predictions.extend(fold_predictions)

                error = frame["actual_return_pct"] - frame["predicted_return_pct"]
                fold_rows.append({
                    "asset_id": asset,
                    "horizon_days": horizon,
                    "fold_number": fold_number,
                    "training_rows": int(frame["training_rows"].min()),
                    "testing_rows": int(len(frame)),
                    # A fold contains expanding rolling origins, so no single
                    # training-end date truthfully describes the whole fold.
                    # Per-origin chronology is retained in replay evidence.
                    "training_end_date": None,
                    "testing_start_date": min(frame["forecast_date"]),
                    "testing_end_date": max(frame["forecast_date"]),
                    "mae_pct": float(error.abs().mean()),
                    "rmse_pct": float(np.sqrt(np.mean(error ** 2))),
                    "directional_accuracy_pct": float(
                        (np.sign(frame["actual_return_pct"]) == np.sign(frame["predicted_return_pct"])).mean() * 100
                    ),
                    "brier_score": float(
                        brier_score_loss(
                            frame["observed_positive"],
                            clip_probability(frame["raw_probability_positive"]),
                        )
                    ),
                    "interval_coverage_pct": float(frame["interval_covered"].mean() * 100),
                })

            group_frame = pd.DataFrame(group_predictions)
            calibration, spec = calibration_evidence(group_frame)
            calibration.update({"asset_id": asset, "horizon_days": horizon})
            calibration_rows.append(calibration)
            calibration_specs[(asset, horizon)] = spec

    replay_cache_stats = {"enabled": False, "reused": 0, "computed": 0}
    if cache is not None:
        cache.flush()
        replay_cache_stats = {
            "enabled": cache.enabled,
            "reused": cache.hits,
            "computed": cache.misses,
        }
        print(
            f"Module 39 replay cache: {cache.hits} origins reused, "
            f"{cache.misses} computed."
        )

    replay = pd.DataFrame(replay_rows)
    folds_frame = pd.DataFrame(fold_rows)
    calibration_frame = pd.DataFrame(calibration_rows)
    gaps_frame = pd.DataFrame(evidence_gaps)

    if replay.empty:
        raise RuntimeError("No supported Module 39 replay groups were produced")

    model_accuracy = float(
        (np.sign(replay["actual_return_pct"]) == np.sign(replay["predicted_return_pct"])).mean() * 100
    )
    positive_rate = float((replay["actual_return_pct"] > 0).mean() * 100)
    majority_accuracy = max(positive_rate, 100 - positive_rate)

    return {
        "replay": replay,
        "rolling": folds_frame,
        "calibration": calibration_frame,
        "calibration_specs": calibration_specs,
        "evidence_gaps": gaps_frame,
        "model_directional_accuracy_pct": model_accuracy,
        "majority_directional_accuracy_pct": majority_accuracy,
        "model_minus_majority_accuracy_pct_points": model_accuracy - majority_accuracy,
        "replay_cache": replay_cache_stats,
    }
