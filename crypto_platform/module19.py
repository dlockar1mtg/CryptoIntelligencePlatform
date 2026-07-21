from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

from crypto_platform.platform import load_all, connect
from crypto_platform.module17 import MODULE17_SCHEMA
from crypto_platform.module18 import MODULE18_SCHEMA

MODULE19_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module19_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    refreshed_validation_rows INTEGER,
    rolling_validation_rows INTEGER,
    grouped_permutation_rows INTEGER,
    registry_rows INTEGER,
    promoted_features INTEGER,
    demoted_features INTEGER,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS feature_validation_refreshed(
    run_id VARCHAR,
    feature_key VARCHAR,
    forward_horizon_days INTEGER,
    sample_count INTEGER,
    pearson_correlation DOUBLE,
    spearman_correlation DOUBLE,
    top_quartile_forward_return_pct DOUBLE,
    bottom_quartile_forward_return_pct DOUBLE,
    top_minus_bottom_pct DOUBLE,
    directional_hit_rate_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key, forward_horizon_days)
);

CREATE TABLE IF NOT EXISTS feature_rolling_validation(
    run_id VARCHAR,
    feature_key VARCHAR,
    forward_horizon_days INTEGER,
    window_number INTEGER,
    training_start_date DATE,
    training_end_date DATE,
    testing_start_date DATE,
    testing_end_date DATE,
    training_spearman DOUBLE,
    testing_spearman DOUBLE,
    testing_directional_hit_rate_pct DOUBLE,
    testing_top_minus_bottom_pct DOUBLE,
    testing_sample_count INTEGER,
    sign_consistent BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id, feature_key, forward_horizon_days, window_number
    )
);

CREATE TABLE IF NOT EXISTS grouped_feature_permutation_importance(
    run_id VARCHAR,
    feature_group VARCHAR,
    forward_horizon_days INTEGER,
    feature_key VARCHAR,
    training_rows INTEGER,
    testing_rows INTEGER,
    base_r2 DOUBLE,
    importance_mean DOUBLE,
    importance_std DOUBLE,
    importance_rank INTEGER,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id, feature_group, forward_horizon_days, feature_key
    )
);

CREATE TABLE IF NOT EXISTS feature_registry(
    run_id VARCHAR,
    feature_key VARCHAR,
    feature_class VARCHAR,
    source_type VARCHAR,
    production_eligible BOOLEAN,
    registry_status VARCHAR,
    first_date DATE,
    latest_date DATE,
    active_window_days INTEGER,
    active_window_coverage_pct DOUBLE,
    best_absolute_spearman DOUBLE,
    rolling_windows INTEGER,
    rolling_positive_windows INTEGER,
    rolling_sign_consistency_pct DOUBLE,
    mean_testing_spearman DOUBLE,
    regime_count INTEGER,
    stable_regime_count INTEGER,
    permutation_groups INTEGER,
    best_permutation_importance DOUBLE,
    promotion_score DOUBLE,
    promotion_reason VARCHAR,
    effective_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, feature_key)
);

CREATE TABLE IF NOT EXISTS feature_registry_history(
    registry_event_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    feature_key VARCHAR,
    previous_status VARCHAR,
    new_status VARCHAR,
    promotion_score DOUBLE,
    event_reason VARCHAR,
    event_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_feature_validation_refreshed AS
SELECT x.*
FROM feature_validation_refreshed x
JOIN (
    SELECT run_id FROM module19_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY ABS(spearman_correlation) DESC NULLS LAST;

CREATE OR REPLACE VIEW latest_feature_rolling_validation AS
SELECT x.*
FROM feature_rolling_validation x
JOIN (
    SELECT run_id FROM module19_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY feature_key, forward_horizon_days, window_number;

CREATE OR REPLACE VIEW latest_grouped_permutation_importance AS
SELECT x.*
FROM grouped_feature_permutation_importance x
JOIN (
    SELECT run_id FROM module19_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY feature_group, forward_horizon_days, importance_rank;

CREATE OR REPLACE VIEW latest_feature_registry AS
SELECT x.*
FROM feature_registry x
JOIN (
    SELECT run_id FROM module19_runs
    ORDER BY started_at_utc DESC LIMIT 1
) r USING(run_id)
ORDER BY promotion_score DESC, feature_key;

CREATE OR REPLACE VIEW production_feature_candidates AS
SELECT *
FROM latest_feature_registry
WHERE registry_status IN ('PROMOTED_SHADOW', 'WATCHLIST')
  AND production_eligible=TRUE
ORDER BY promotion_score DESC;
"""

FEATURE_GROUPS = {
    "MACRO": [
        "dollar_index",
        "high_yield_spread",
        "vix",
        "macro_liquidity_score",
    ],
    "SENTIMENT": [
        "fear_greed_index",
        "risk_appetite_score",
    ],
    "MARKET_STRUCTURE": [
        "btc_dominance_proxy_pct",
        "total2_market_cap_proxy_usd",
        "total3_market_cap_proxy_usd",
        "core_breadth_above_sma50_pct",
        "core_median_return_30d_pct",
        "btc_return_30d_pct",
    ],
    "LIQUIDITY_FLOWS": [
        "stablecoin_supply_usd",
        "stablecoin_growth_30d_pct",
        "etf_net_flow_usd",
    ],
}

SNAPSHOT_FEATURES = {
    "btc_dominance_pct",
    "total_market_cap_usd",
}

PROXY_FEATURES = {
    "btc_dominance_proxy_pct",
    "total2_market_cap_proxy_usd",
    "total3_market_cap_proxy_usd",
}

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)

class Module19Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE17_SCHEMA)
        self.conn.execute(MODULE18_SCHEMA)
        self.conn.execute(MODULE19_SCHEMA)
        self.cfg = self.settings["module19"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        self.conn.register("_m19_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m19_stage"
        )
        self.conn.unregister("_m19_stage")

    def feature_frame(self) -> pd.DataFrame:
        frame = self.conn.execute(
            "SELECT * FROM crypto_features_daily "
            "ORDER BY observation_date"
        ).fetchdf()
        if frame.empty:
            raise RuntimeError(
                "Module 17 feature warehouse is empty. "
                "Run Module 17 and Module 18 first."
            )
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"]
        )
        return frame

    @staticmethod
    def add_forward(
        frame: pd.DataFrame, horizon: int
    ) -> pd.DataFrame:
        result = frame.copy()
        result[f"forward_{horizon}"] = (
            result["btc_price_usd"].shift(-horizon)
            / result["btc_price_usd"]
            - 1
        ) * 100
        return result

    def eligible_features(
        self, frame: pd.DataFrame
    ) -> list[str]:
        configured = []
        for values in FEATURE_GROUPS.values():
            configured.extend(values)
        return [
            key for key in dict.fromkeys(configured)
            if key in frame.columns
        ]

    def refresh_validation(
        self, frame: pd.DataFrame
    ) -> pd.DataFrame:
        rows = []
        minimum = int(
            self.cfg["validation"]["minimum_observations"]
        )
        features = self.eligible_features(frame)

        for horizon in self.cfg["horizons_days"]:
            target = f"forward_{horizon}"
            evaluated = self.add_forward(
                frame, int(horizon)
            )

            for feature_key in features:
                sample = evaluated[
                    [feature_key, target]
                ].dropna()
                if len(sample) < minimum:
                    continue

                pearson = sample[feature_key].corr(
                    sample[target]
                )
                spearman = sample[feature_key].rank().corr(
                    sample[target].rank()
                )
                lower = sample[feature_key].quantile(0.25)
                upper = sample[feature_key].quantile(0.75)
                top = sample.loc[
                    sample[feature_key] >= upper, target
                ].mean()
                bottom = sample.loc[
                    sample[feature_key] <= lower, target
                ].mean()

                centered = (
                    sample[feature_key]
                    - sample[feature_key].median()
                )
                hit = (
                    np.sign(centered)
                    == np.sign(sample[target])
                ).mean() * 100

                rows.append({
                    "run_id": self.run_id,
                    "feature_key": feature_key,
                    "forward_horizon_days": int(horizon),
                    "sample_count": len(sample),
                    "pearson_correlation": safe_float(pearson),
                    "spearman_correlation": safe_float(spearman),
                    "top_quartile_forward_return_pct": safe_float(top),
                    "bottom_quartile_forward_return_pct": safe_float(bottom),
                    "top_minus_bottom_pct": safe_float(top - bottom),
                    "directional_hit_rate_pct": safe_float(hit),
                    "calculated_at_utc": utcnow(),
                })

        result = pd.DataFrame(rows)
        self.upsert(
            "feature_validation_refreshed", result
        )
        return result

    def rolling_windows(
        self, frame: pd.DataFrame
    ) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
        train_months = int(
            self.cfg["rolling"]["training_months"]
        )
        test_months = int(
            self.cfg["rolling"]["testing_months"]
        )
        step_months = int(
            self.cfg["rolling"]["step_months"]
        )

        first = frame["observation_date"].min()
        last = frame["observation_date"].max()
        test_start = first + pd.DateOffset(
            months=train_months
        )
        windows = []

        while True:
            train_start = test_start - pd.DateOffset(
                months=train_months
            )
            train_end = test_start
            test_end = test_start + pd.DateOffset(
                months=test_months
            )
            if test_end > last:
                break
            windows.append(
                (
                    pd.Timestamp(train_start),
                    pd.Timestamp(train_end),
                    pd.Timestamp(test_start),
                    pd.Timestamp(test_end),
                )
            )
            test_start = test_start + pd.DateOffset(
                months=step_months
            )

        return windows

    def rolling_validation(
        self, frame: pd.DataFrame
    ) -> pd.DataFrame:
        rows = []
        features = self.eligible_features(frame)
        windows = self.rolling_windows(frame)
        minimum_train = int(
            self.cfg["rolling"][
                "minimum_training_observations"
            ]
        )
        minimum_test = int(
            self.cfg["rolling"][
                "minimum_testing_observations"
            ]
        )

        for horizon in self.cfg["horizons_days"]:
            target = f"forward_{horizon}"
            evaluated = self.add_forward(
                frame, int(horizon)
            )

            for feature_key in features:
                for number, (
                    train_start, train_end,
                    test_start, test_end,
                ) in enumerate(windows, start=1):
                    train = evaluated[
                        (evaluated["observation_date"] >= train_start)
                        & (evaluated["observation_date"] < train_end)
                    ][[feature_key, target]].dropna()
                    test = evaluated[
                        (evaluated["observation_date"] >= test_start)
                        & (evaluated["observation_date"] < test_end)
                    ][[feature_key, target]].dropna()

                    if (
                        len(train) < minimum_train
                        or len(test) < minimum_test
                    ):
                        continue

                    train_spearman = (
                        train[feature_key].rank().corr(
                            train[target].rank()
                        )
                    )
                    test_spearman = (
                        test[feature_key].rank().corr(
                            test[target].rank()
                        )
                    )

                    lower = test[feature_key].quantile(0.25)
                    upper = test[feature_key].quantile(0.75)
                    top = test.loc[
                        test[feature_key] >= upper, target
                    ].mean()
                    bottom = test.loc[
                        test[feature_key] <= lower, target
                    ].mean()
                    centered = (
                        test[feature_key]
                        - train[feature_key].median()
                    )
                    hit = (
                        np.sign(centered)
                        == np.sign(test[target])
                    ).mean() * 100

                    rows.append({
                        "run_id": self.run_id,
                        "feature_key": feature_key,
                        "forward_horizon_days": int(horizon),
                        "window_number": number,
                        "training_start_date": train_start.date(),
                        "training_end_date": train_end.date(),
                        "testing_start_date": test_start.date(),
                        "testing_end_date": test_end.date(),
                        "training_spearman": safe_float(
                            train_spearman
                        ),
                        "testing_spearman": safe_float(
                            test_spearman
                        ),
                        "testing_directional_hit_rate_pct": safe_float(hit),
                        "testing_top_minus_bottom_pct": safe_float(
                            top - bottom
                        ),
                        "testing_sample_count": len(test),
                        "sign_consistent": bool(
                            pd.notna(train_spearman)
                            and pd.notna(test_spearman)
                            and np.sign(train_spearman)
                            == np.sign(test_spearman)
                        ),
                        "calculated_at_utc": utcnow(),
                    })

        result = pd.DataFrame(rows)
        self.upsert(
            "feature_rolling_validation", result
        )
        return result

    def grouped_permutation(
        self, frame: pd.DataFrame
    ) -> pd.DataFrame:
        rows = []
        minimum_train = int(
            self.cfg["permutation"][
                "minimum_training_rows"
            ]
        )
        minimum_test = int(
            self.cfg["permutation"][
                "minimum_testing_rows"
            ]
        )

        for group_name, configured in FEATURE_GROUPS.items():
            features = [
                key for key in configured
                if key in frame.columns
            ]
            if len(features) < 2:
                continue

            for horizon in self.cfg["horizons_days"]:
                target = f"forward_{horizon}"
                sample = self.add_forward(
                    frame, int(horizon)
                )[features + [target]].dropna()

                if len(sample) < (
                    minimum_train + minimum_test
                ):
                    continue

                split = int(len(sample) * float(
                    self.cfg["permutation"][
                        "training_fraction"
                    ]
                ))
                train = sample.iloc[:split]
                test = sample.iloc[split:]

                if (
                    len(train) < minimum_train
                    or len(test) < minimum_test
                ):
                    continue

                model = RandomForestRegressor(
                    n_estimators=int(
                        self.cfg["permutation"][
                            "n_estimators"
                        ]
                    ),
                    min_samples_leaf=int(
                        self.cfg["permutation"][
                            "min_samples_leaf"
                        ]
                    ),
                    random_state=int(
                        self.cfg["permutation"][
                            "random_state"
                        ]
                    ),
                    n_jobs=-1,
                )
                model.fit(
                    train[features], train[target]
                )
                base_r2 = model.score(
                    test[features], test[target]
                )
                importance = permutation_importance(
                    model,
                    test[features],
                    test[target],
                    n_repeats=int(
                        self.cfg["permutation"][
                            "n_repeats"
                        ]
                    ),
                    random_state=int(
                        self.cfg["permutation"][
                            "random_state"
                        ]
                    ),
                    n_jobs=-1,
                )

                order = np.argsort(
                    -importance.importances_mean
                )
                for rank, index in enumerate(
                    order, start=1
                ):
                    rows.append({
                        "run_id": self.run_id,
                        "feature_group": group_name,
                        "forward_horizon_days": int(horizon),
                        "feature_key": features[index],
                        "training_rows": len(train),
                        "testing_rows": len(test),
                        "base_r2": safe_float(base_r2),
                        "importance_mean": safe_float(
                            importance.importances_mean[index]
                        ),
                        "importance_std": safe_float(
                            importance.importances_std[index]
                        ),
                        "importance_rank": rank,
                        "calculated_at_utc": utcnow(),
                    })

        result = pd.DataFrame(rows)
        self.upsert(
            "grouped_feature_permutation_importance",
            result,
        )
        return result

    def source_metadata(
        self, feature_key: str
    ) -> tuple[str, str, bool]:
        if feature_key in SNAPSHOT_FEATURES:
            return (
                "SNAPSHOT",
                "LATEST_SNAPSHOT",
                False,
            )
        if feature_key in PROXY_FEATURES:
            return (
                "DERIVED_PROXY",
                "CANONICAL_MARKET_WAREHOUSE",
                True,
            )
        if feature_key == "etf_net_flow_usd":
            return (
                "MANUAL_VALIDATED",
                "MANUAL_OR_LICENSED",
                True,
            )
        if feature_key in {
            "fear_greed_index",
            "stablecoin_supply_usd",
            "stablecoin_growth_30d_pct",
        }:
            return (
                "EXTERNAL_HISTORY",
                "PUBLIC_API",
                True,
            )
        return (
            "DERIVED_OR_MACRO",
            "PLATFORM_WAREHOUSE",
            True,
        )

    def prior_registry(self) -> dict[str, str]:
        try:
            frame = self.conn.execute(
                """
                SELECT feature_key, registry_status
                FROM feature_registry
                QUALIFY ROW_NUMBER() OVER(
                    PARTITION BY feature_key
                    ORDER BY effective_at_utc DESC
                )=1
                """
            ).fetchdf()
        except Exception:
            return {}
        return dict(
            zip(
                frame["feature_key"],
                frame["registry_status"],
            )
        )

    def build_registry(
        self,
        frame: pd.DataFrame,
        refreshed: pd.DataFrame,
        rolling: pd.DataFrame,
        grouped: pd.DataFrame,
    ) -> pd.DataFrame:
        readiness = self.conn.execute(
            "SELECT * FROM latest_feature_readiness_v2"
        ).fetchdf()
        regimes = self.conn.execute(
            "SELECT * FROM latest_feature_regime_stability"
        ).fetchdf()
        prior = self.prior_registry()
        rows = []
        history_events = []

        all_features = sorted(
            set(self.eligible_features(frame))
            | SNAPSHOT_FEATURES
        )

        promotion = self.cfg["promotion"]

        for feature_key in all_features:
            source_type, source_label, eligible = (
                self.source_metadata(feature_key)
            )

            ready = readiness[
                readiness["feature_key"] == feature_key
            ]
            if ready.empty:
                first = latest = None
                active_days = 0
                coverage = 0.0
            else:
                record = ready.iloc[0]
                first = record["first_date"]
                latest = record["latest_date"]
                active_days = int(
                    record["active_window_days"]
                )
                coverage = float(
                    record[
                        "active_window_coverage_pct"
                    ]
                )

            validation = refreshed[
                refreshed["feature_key"] == feature_key
            ]
            best_spearman = (
                float(
                    validation[
                        "spearman_correlation"
                    ].abs().max()
                )
                if not validation.empty
                else 0.0
            )

            roll = rolling[
                rolling["feature_key"] == feature_key
            ]
            rolling_windows = len(roll)
            rolling_positive = int(
                (
                    roll["testing_spearman"]
                    .fillna(0)
                    .abs()
                    >= float(
                        promotion[
                            "minimum_window_absolute_spearman"
                        ]
                    )
                ).sum()
            ) if not roll.empty else 0
            sign_consistency = (
                float(
                    roll["sign_consistent"].mean()
                    * 100
                )
                if not roll.empty
                else 0.0
            )
            mean_testing_spearman = (
                float(
                    roll["testing_spearman"].mean()
                )
                if not roll.empty
                else 0.0
            )

            regime = regimes[
                regimes["feature_key"] == feature_key
            ]
            regime_count = int(
                regime["regime"].nunique()
            ) if not regime.empty else 0
            stable_regime_count = int(
                (
                    regime["spearman_correlation"]
                    .fillna(0)
                    .abs()
                    >= float(
                        promotion[
                            "minimum_regime_absolute_spearman"
                        ]
                    )
                ).groupby(regime["regime"]).any().sum()
            ) if not regime.empty else 0

            perm = grouped[
                grouped["feature_key"] == feature_key
            ]
            permutation_groups = int(
                perm["feature_group"].nunique()
            ) if not perm.empty else 0
            best_importance = (
                float(perm["importance_mean"].max())
                if not perm.empty
                else 0.0
            )

            history_score = min(
                100.0,
                active_days
                / float(
                    promotion[
                        "target_history_days"
                    ]
                )
                * 100,
            )
            coverage_score = min(100.0, coverage)
            predictive_score = min(
                100.0,
                best_spearman
                / float(
                    promotion[
                        "target_absolute_spearman"
                    ]
                )
                * 100,
            )
            rolling_score = min(
                100.0,
                sign_consistency
                * 0.6
                + (
                    rolling_positive
                    / max(
                        1,
                        int(
                            promotion[
                                "target_positive_windows"
                            ]
                        ),
                    )
                    * 100
                )
                * 0.4,
            )
            regime_score = min(
                100.0,
                stable_regime_count
                / max(
                    1,
                    int(
                        promotion[
                            "target_stable_regimes"
                        ]
                    ),
                )
                * 100,
            )
            permutation_score = max(
                0.0,
                min(
                    100.0,
                    best_importance
                    / float(
                        promotion[
                            "target_permutation_importance"
                        ]
                    )
                    * 100,
                ),
            )

            score = (
                history_score * 0.15
                + coverage_score * 0.10
                + predictive_score * 0.25
                + rolling_score * 0.25
                + regime_score * 0.15
                + permutation_score * 0.10
            )

            if not eligible:
                status = "SNAPSHOT_REFERENCE"
                reason = (
                    "Snapshot-only feature; historical "
                    "proxy is required for research."
                )
            elif (
                active_days
                < int(
                    promotion[
                        "minimum_history_days"
                    ]
                )
                or coverage
                < float(
                    promotion[
                        "minimum_active_window_coverage_pct"
                    ]
                )
            ):
                status = "INSUFFICIENT_HISTORY"
                reason = (
                    "Insufficient history or active-window "
                    "coverage."
                )
            elif (
                rolling_windows
                < int(
                    promotion[
                        "minimum_rolling_windows"
                    ]
                )
            ):
                status = "WATCHLIST"
                reason = (
                    "Research evidence exists, but there "
                    "are too few rolling test windows."
                )
            elif (
                score
                >= float(
                    promotion[
                        "promoted_shadow_score"
                    ]
                )
                and sign_consistency
                >= float(
                    promotion[
                        "minimum_sign_consistency_pct"
                    ]
                )
                and stable_regime_count
                >= int(
                    promotion[
                        "minimum_stable_regimes"
                    ]
                )
            ):
                status = "PROMOTED_SHADOW"
                reason = (
                    "Cleared history, rolling, regime, "
                    "and composite promotion thresholds."
                )
            elif score >= float(
                promotion["watchlist_score"]
            ):
                status = "WATCHLIST"
                reason = (
                    "Promising evidence, but not enough "
                    "for shadow promotion."
                )
            else:
                status = "RESEARCH_ONLY"
                reason = (
                    "Did not clear the configured "
                    "promotion thresholds."
                )

            rows.append({
                "run_id": self.run_id,
                "feature_key": feature_key,
                "feature_class": next(
                    (
                        group
                        for group, members
                        in FEATURE_GROUPS.items()
                        if feature_key in members
                    ),
                    "REFERENCE",
                ),
                "source_type": (
                    f"{source_type}:{source_label}"
                ),
                "production_eligible": eligible,
                "registry_status": status,
                "first_date": first,
                "latest_date": latest,
                "active_window_days": active_days,
                "active_window_coverage_pct": coverage,
                "best_absolute_spearman": best_spearman,
                "rolling_windows": rolling_windows,
                "rolling_positive_windows": rolling_positive,
                "rolling_sign_consistency_pct": sign_consistency,
                "mean_testing_spearman": mean_testing_spearman,
                "regime_count": regime_count,
                "stable_regime_count": stable_regime_count,
                "permutation_groups": permutation_groups,
                "best_permutation_importance": best_importance,
                "promotion_score": score,
                "promotion_reason": reason,
                "effective_at_utc": utcnow(),
            })

            previous = prior.get(feature_key)
            if previous != status:
                history_events.append({
                    "registry_event_id": str(
                        uuid.uuid4()
                    ),
                    "run_id": self.run_id,
                    "feature_key": feature_key,
                    "previous_status": previous,
                    "new_status": status,
                    "promotion_score": score,
                    "event_reason": reason,
                    "event_at_utc": utcnow(),
                })

        registry = pd.DataFrame(rows)
        events = pd.DataFrame(history_events)
        self.upsert("feature_registry", registry)
        self.upsert(
            "feature_registry_history", events
        )
        return registry

    def run(self) -> dict[str, Any]:
        self.conn.execute(
            """
            UPDATE module19_runs
            SET status='FAILED',
                completed_at_utc=?,
                notes=COALESCE(notes,'') ||
                      '; interrupted prior run'
            WHERE status='RUNNING'
            """,
            [utcnow()],
        )
        self.conn.execute(
            """
            INSERT INTO module19_runs VALUES(
                ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0, 0, 0,
                NULL, '4.2.2'
            )
            """,
            [self.run_id, self.started],
        )

        try:
            frame = self.feature_frame()
            refreshed = self.refresh_validation(
                frame
            )
            rolling = self.rolling_validation(frame)
            grouped = self.grouped_permutation(frame)
            registry = self.build_registry(
                frame,
                refreshed,
                rolling,
                grouped,
            )

            promoted = int(
                (
                    registry["registry_status"]
                    == "PROMOTED_SHADOW"
                ).sum()
            )

            prior_promoted = self.conn.execute(
                """
                SELECT COUNT(DISTINCT feature_key)
                FROM feature_registry_history
                WHERE previous_status='PROMOTED_SHADOW'
                  AND new_status<>'PROMOTED_SHADOW'
                  AND run_id=?
                """,
                [self.run_id],
            ).fetchone()[0]

            notes = (
                "Feature registry is research governance "
                "only. Module 13 remains unchanged."
            )
            self.conn.execute(
                """
                UPDATE module19_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    refreshed_validation_rows=?,
                    rolling_validation_rows=?,
                    grouped_permutation_rows=?,
                    registry_rows=?,
                    promoted_features=?,
                    demoted_features=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(refreshed),
                    len(rolling),
                    len(grouped),
                    len(registry),
                    promoted,
                    int(prior_promoted),
                    notes,
                    self.run_id,
                ],
            )
            self.conn.close()
            return {
                "run_id": self.run_id,
                "status": "SUCCESS",
                "refreshed_validation_rows": len(
                    refreshed
                ),
                "rolling_validation_rows": len(
                    rolling
                ),
                "grouped_permutation_rows": len(
                    grouped
                ),
                "registry_rows": len(registry),
                "promoted_features": promoted,
                "demoted_features": int(
                    prior_promoted
                ),
            }
        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module19_runs
                SET completed_at_utc=?,
                    status='FAILED',
                    notes=?
                WHERE run_id=?
                """,
                [utcnow(), str(exc)[:1000], self.run_id],
            )
            self.conn.close()
            raise

def run_module19() -> dict[str, Any]:
    return Module19Runner().run()
