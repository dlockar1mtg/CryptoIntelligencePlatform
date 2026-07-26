from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module38 import MODULE38_SCHEMA
from crypto_platform.module39 import MODULE39_SCHEMA

MODULE40_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module40_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module38_run_id VARCHAR,
    source_module39_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    forecasts_ingested INTEGER,
    model_snapshots_ingested INTEGER,
    attribution_snapshots_ingested INTEGER,
    outcomes_matured INTEGER,
    learning_summary_rows INTEGER,
    calibration_curve_rows INTEGER,
    models_evaluated INTEGER,
    earliest_forecast_date DATE,
    latest_forecast_date DATE,
    realized_horizons INTEGER,
    memory_status VARCHAR,
    continuous_learning_status VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m40_forecast_memory(
    forecast_memory_id VARCHAR PRIMARY KEY,
    source_module38_run_id VARCHAR,
    source_module39_run_id VARCHAR,
    forecast_date DATE,
    outcome_due_date DATE,
    asset_id VARCHAR,
    horizon_days INTEGER,
    current_price DOUBLE,
    predicted_return_pct DOUBLE,
    predicted_price DOUBLE,
    raw_probability_positive DOUBLE,
    calibrated_probability_positive DOUBLE,
    raw_lower_return_pct DOUBLE,
    raw_upper_return_pct DOUBLE,
    calibrated_lower_return_pct DOUBLE,
    calibrated_upper_return_pct DOUBLE,
    forecast_confidence DOUBLE,
    model_agreement DOUBLE,
    predictive_regime VARCHAR,
    predictive_regime_confidence DOUBLE,
    forecast_status VARCHAR,
    model_version VARCHAR,
    outcome_status VARCHAR,
    realized_date DATE,
    realized_price DOUBLE,
    realized_return_pct DOUBLE,
    forecast_error_pct DOUBLE,
    absolute_error_pct DOUBLE,
    direction_correct BOOLEAN,
    interval_covered BOOLEAN,
    probability_outcome INTEGER,
    matured_at_utc TIMESTAMPTZ,
    created_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS m40_model_memory(
    forecast_memory_id VARCHAR,
    model_key VARCHAR,
    validation_rows INTEGER,
    validation_mae_pct DOUBLE,
    validation_rmse_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    ensemble_weight DOUBLE,
    selected BOOLEAN,
    created_at_utc TIMESTAMPTZ,
    PRIMARY KEY(forecast_memory_id, model_key)
);

CREATE TABLE IF NOT EXISTS m40_attribution_memory(
    forecast_memory_id VARCHAR,
    driver_key VARCHAR,
    driver_category VARCHAR,
    contribution_pct DOUBLE,
    contribution_direction VARCHAR,
    importance_rank INTEGER,
    created_at_utc TIMESTAMPTZ,
    PRIMARY KEY(forecast_memory_id, driver_key)
);

CREATE TABLE IF NOT EXISTS m40_learning_summary(
    run_id VARCHAR,
    grouping_type VARCHAR,
    grouping_key VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    forecasts_total INTEGER,
    outcomes_matured INTEGER,
    maturity_rate_pct DOUBLE,
    mean_absolute_error_pct DOUBLE,
    root_mean_squared_error_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    brier_score DOUBLE,
    interval_coverage_pct DOUBLE,
    mean_confidence DOUBLE,
    realized_sharpe DOUBLE,
    calibration_gap DOUBLE,
    learning_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id, grouping_type, grouping_key,
        asset_id, horizon_days
    )
);

CREATE TABLE IF NOT EXISTS m40_calibration_curve(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    probability_bin_lower DOUBLE,
    probability_bin_upper DOUBLE,
    forecasts INTEGER,
    mean_predicted_probability DOUBLE,
    observed_positive_rate DOUBLE,
    calibration_gap DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id, asset_id, horizon_days,
        probability_bin_lower
    )
);

CREATE TABLE IF NOT EXISTS m40_model_leaderboard(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    model_key VARCHAR,
    forecasts_evaluated INTEGER,
    mean_validation_mae_pct DOUBLE,
    mean_validation_rmse_pct DOUBLE,
    mean_directional_accuracy_pct DOUBLE,
    mean_ensemble_weight DOUBLE,
    realized_forecast_mae_pct DOUBLE,
    model_score DOUBLE,
    model_rank INTEGER,
    model_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(
        run_id, asset_id, horizon_days, model_key
    )
);

CREATE TABLE IF NOT EXISTS m40_retraining_recommendations(
    run_id VARCHAR,
    asset_id VARCHAR,
    horizon_days INTEGER,
    matured_forecasts INTEGER,
    recent_mae_pct DOUBLE,
    prior_mae_pct DOUBLE,
    recent_directional_accuracy_pct DOUBLE,
    prior_directional_accuracy_pct DOUBLE,
    calibration_gap DOUBLE,
    drift_detected BOOLEAN,
    retraining_priority VARCHAR,
    recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id, horizon_days)
);

CREATE TABLE IF NOT EXISTS m40_memory_summary(
    run_id VARCHAR PRIMARY KEY,
    forecasts_stored INTEGER,
    pending_forecasts INTEGER,
    matured_forecasts INTEGER,
    assets_tracked INTEGER,
    horizons_tracked INTEGER,
    mean_absolute_error_pct DOUBLE,
    directional_accuracy_pct DOUBLE,
    mean_brier_score DOUBLE,
    interval_coverage_pct DOUBLE,
    calibration_gap DOUBLE,
    high_priority_retraining_rows INTEGER,
    memory_status VARCHAR,
    continuous_learning_status VARCHAR,
    advancement_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m40_forecast_memory AS
SELECT *
FROM m40_forecast_memory
ORDER BY forecast_date DESC, asset_id, horizon_days;

CREATE OR REPLACE VIEW latest_m40_matured_forecasts AS
SELECT *
FROM m40_forecast_memory
WHERE outcome_status='MATURED'
ORDER BY realized_date DESC, asset_id, horizon_days;

CREATE OR REPLACE VIEW latest_m40_pending_forecasts AS
SELECT *
FROM m40_forecast_memory
WHERE outcome_status='PENDING'
ORDER BY outcome_due_date, asset_id, horizon_days;

CREATE OR REPLACE VIEW latest_m40_learning_summary AS
SELECT * FROM m40_learning_summary
WHERE run_id=(
    SELECT run_id FROM module40_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY grouping_type, grouping_key, asset_id, horizon_days;

CREATE OR REPLACE VIEW latest_m40_calibration_curve AS
SELECT * FROM m40_calibration_curve
WHERE run_id=(
    SELECT run_id FROM module40_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY asset_id, horizon_days, probability_bin_lower;

CREATE OR REPLACE VIEW latest_m40_model_leaderboard AS
SELECT * FROM m40_model_leaderboard
WHERE run_id=(
    SELECT run_id FROM module40_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY asset_id, horizon_days, model_rank;

CREATE OR REPLACE VIEW latest_m40_retraining_recommendations AS
SELECT * FROM m40_retraining_recommendations
WHERE run_id=(
    SELECT run_id FROM module40_runs
    ORDER BY started_at_utc DESC LIMIT 1
)
ORDER BY
    CASE retraining_priority
        WHEN 'HIGH' THEN 1
        WHEN 'MEDIUM' THEN 2
        ELSE 3
    END,
    asset_id,
    horizon_days;

CREATE OR REPLACE VIEW latest_m40_memory_summary AS
SELECT * FROM m40_memory_summary
WHERE run_id=(
    SELECT run_id FROM module40_runs
    ORDER BY started_at_utc DESC LIMIT 1
);
"""


def utcnow():
    return datetime.now(timezone.utc)


def memory_id(source_run, asset_id, horizon_days, forecast_date):
    """Canonical prediction-event identity.

    One forecast event exists for each forecast date, asset, and horizon.
    Model version and source run remain lineage metadata, but they do not
    create a second forecast event.
    """
    namespace = uuid.UUID("4ac9db72-12a2-4e6e-8c15-1fa242c7cb83")
    key = (
        f"{forecast_date}|{asset_id}|"
        f"{int(horizon_days)}"
    )
    return str(uuid.uuid5(namespace, key))


def safe_float(value, default=np.nan):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


class Module40Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE38_SCHEMA)
        self.conn.execute(MODULE39_SCHEMA)
        self.conn.execute(MODULE40_SCHEMA)
        self.ensure_canonical_memory_schema()
        self.cfg = self.settings["module40"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

        source38 = self.conn.execute(
            """
            SELECT run_id
            FROM module38_runs
            WHERE status='SUCCESS'
            ORDER BY started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        source39 = self.conn.execute(
            """
            SELECT run_id
            FROM module39_runs
            WHERE status='SUCCESS'
            ORDER BY started_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        if source38 is None or source39 is None:
            raise RuntimeError(
                "Successful Modules 38 and 39 are required."
            )
        self.source38 = str(source38[0])
        self.source39 = str(source39[0])

    def ensure_canonical_memory_schema(self):
        """Upgrade restored databases to the canonical memory identity.

        Older hosted database snapshots may contain Module 40 tables but
        lack the unique index required by the forecast-memory ON CONFLICT
        clause. This migration consolidates duplicate forecast events,
        rewires child records to the surviving forecast ID, and creates
        the required canonical unique index.
        """
        self.conn.execute("BEGIN TRANSACTION")
        try:
            self.conn.execute(
                """
                CREATE OR REPLACE TEMP TABLE
                    m40_identity_rank AS
                SELECT
                    forecast_memory_id,
                    first_value(forecast_memory_id) OVER(
                        PARTITION BY
                            forecast_date,
                            asset_id,
                            horizon_days
                        ORDER BY
                            CASE
                                WHEN outcome_status='MATURED'
                                THEN 0
                                ELSE 1
                            END,
                            created_at_utc DESC,
                            forecast_memory_id DESC
                    ) AS survivor_id,
                    row_number() OVER(
                        PARTITION BY
                            forecast_date,
                            asset_id,
                            horizon_days
                        ORDER BY
                            CASE
                                WHEN outcome_status='MATURED'
                                THEN 0
                                ELSE 1
                            END,
                            created_at_utc DESC,
                            forecast_memory_id DESC
                    ) AS identity_rank
                FROM m40_forecast_memory
                """
            )

            self.conn.execute(
                """
                CREATE OR REPLACE TEMP TABLE
                    m40_models_consolidated AS
                SELECT
                    ranked.survivor_id
                        AS forecast_memory_id,
                    child.model_key,
                    arg_max(
                        child.validation_rows,
                        child.created_at_utc
                    ) AS validation_rows,
                    arg_max(
                        child.validation_mae_pct,
                        child.created_at_utc
                    ) AS validation_mae_pct,
                    arg_max(
                        child.validation_rmse_pct,
                        child.created_at_utc
                    ) AS validation_rmse_pct,
                    arg_max(
                        child.directional_accuracy_pct,
                        child.created_at_utc
                    ) AS directional_accuracy_pct,
                    arg_max(
                        child.ensemble_weight,
                        child.created_at_utc
                    ) AS ensemble_weight,
                    bool_or(child.selected) AS selected,
                    max(child.created_at_utc)
                        AS created_at_utc
                FROM m40_model_memory AS child
                JOIN m40_identity_rank AS ranked
                  ON ranked.forecast_memory_id =
                     child.forecast_memory_id
                GROUP BY
                    ranked.survivor_id,
                    child.model_key
                """
            )

            self.conn.execute(
                """
                CREATE OR REPLACE TEMP TABLE
                    m40_attributions_consolidated AS
                SELECT
                    ranked.survivor_id
                        AS forecast_memory_id,
                    child.driver_key,
                    arg_max(
                        child.driver_category,
                        child.created_at_utc
                    ) AS driver_category,
                    arg_max(
                        child.contribution_pct,
                        child.created_at_utc
                    ) AS contribution_pct,
                    arg_max(
                        child.contribution_direction,
                        child.created_at_utc
                    ) AS contribution_direction,
                    arg_max(
                        child.importance_rank,
                        child.created_at_utc
                    ) AS importance_rank,
                    max(child.created_at_utc)
                        AS created_at_utc
                FROM m40_attribution_memory AS child
                JOIN m40_identity_rank AS ranked
                  ON ranked.forecast_memory_id =
                     child.forecast_memory_id
                GROUP BY
                    ranked.survivor_id,
                    child.driver_key
                """
            )

            self.conn.execute(
                "DELETE FROM m40_model_memory"
            )
            self.conn.execute(
                "DELETE FROM m40_attribution_memory"
            )
            self.conn.execute(
                """
                DELETE FROM m40_forecast_memory
                WHERE forecast_memory_id IN(
                    SELECT forecast_memory_id
                    FROM m40_identity_rank
                    WHERE identity_rank > 1
                )
                """
            )

            self.conn.execute(
                """
                INSERT INTO m40_model_memory
                SELECT *
                FROM m40_models_consolidated
                """
            )
            self.conn.execute(
                """
                INSERT INTO m40_attribution_memory
                SELECT *
                FROM m40_attributions_consolidated
                """
            )

            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    ux_m40_canonical_forecast
                ON m40_forecast_memory(
                    forecast_date,
                    asset_id,
                    horizon_days
                )
                """
            )

            duplicate_count = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        forecast_date,
                        asset_id,
                        horizon_days,
                        COUNT(*) AS row_count
                    FROM m40_forecast_memory
                    GROUP BY
                        forecast_date,
                        asset_id,
                        horizon_days
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]

            orphan_models = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM m40_model_memory AS child
                LEFT JOIN m40_forecast_memory AS parent
                  ON parent.forecast_memory_id =
                     child.forecast_memory_id
                WHERE parent.forecast_memory_id IS NULL
                """
            ).fetchone()[0]

            orphan_attributions = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM m40_attribution_memory AS child
                LEFT JOIN m40_forecast_memory AS parent
                  ON parent.forecast_memory_id =
                     child.forecast_memory_id
                WHERE parent.forecast_memory_id IS NULL
                """
            ).fetchone()[0]

            if duplicate_count:
                raise RuntimeError(
                    "Module 40 canonical migration left "
                    f"{duplicate_count} duplicate forecast events."
                )

            if orphan_models or orphan_attributions:
                raise RuntimeError(
                    "Module 40 canonical migration created "
                    "orphaned child records: "
                    f"models={orphan_models}, "
                    f"attributions={orphan_attributions}."
                )

            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def upsert(self, table, frame):
        """Persist a frame using explicit conflict targets.

        DuckDB cannot infer a conflict target when a table has both a
        primary key and an additional unique index. Module 40 therefore
        uses table-specific persistence semantics rather than
        INSERT OR REPLACE.
        """
        if frame.empty:
            return

        self.conn.register("_m40_stage", frame)
        try:
            columns = list(frame.columns)
            column_sql = ",".join(columns)

            if table == "m40_forecast_memory":
                # Canonical identity:
                # forecast_date + asset_id + horizon_days + model_version.
                # Existing matured outcomes must never be overwritten by a
                # later rerun of the same forecast.
                update_columns = [
                    column
                    for column in columns
                    if column not in {
                        "forecast_memory_id",
                        "forecast_date",
                        "asset_id",
                        "horizon_days",
                        "outcome_status",
                        "realized_date",
                        "realized_price",
                        "realized_return_pct",
                        "forecast_error_pct",
                        "absolute_error_pct",
                        "direction_correct",
                        "interval_covered",
                        "probability_outcome",
                        "matured_at_utc",
                        "created_at_utc",
                    }
                ]
                assignments = ",".join(
                    f"{column}=excluded.{column}"
                    for column in update_columns
                )
                self.conn.execute(
                    f"""
                    INSERT INTO {table}({column_sql})
                    SELECT {column_sql}
                    FROM _m40_stage
                    ON CONFLICT(
                        forecast_date,
                        asset_id,
                        horizon_days
                    )
                    DO UPDATE SET {assignments}
                    """
                )

            elif table == "m40_model_memory":
                update_columns = [
                    column
                    for column in columns
                    if column not in {
                        "forecast_memory_id",
                        "model_key",
                        "created_at_utc",
                    }
                ]
                assignments = ",".join(
                    f"{column}=excluded.{column}"
                    for column in update_columns
                )
                self.conn.execute(
                    f"""
                    INSERT INTO {table}({column_sql})
                    SELECT {column_sql}
                    FROM _m40_stage
                    ON CONFLICT(
                        forecast_memory_id,
                        model_key
                    )
                    DO UPDATE SET {assignments}
                    """
                )

            elif table == "m40_attribution_memory":
                update_columns = [
                    column
                    for column in columns
                    if column not in {
                        "forecast_memory_id",
                        "driver_key",
                        "created_at_utc",
                    }
                ]
                assignments = ",".join(
                    f"{column}=excluded.{column}"
                    for column in update_columns
                )
                self.conn.execute(
                    f"""
                    INSERT INTO {table}({column_sql})
                    SELECT {column_sql}
                    FROM _m40_stage
                    ON CONFLICT(
                        forecast_memory_id,
                        driver_key
                    )
                    DO UPDATE SET {assignments}
                    """
                )

            else:
                # Run-scoped analytics tables have only one primary key.
                self.conn.execute(
                    f"""
                    INSERT OR REPLACE INTO {table}({column_sql})
                    SELECT {column_sql}
                    FROM _m40_stage
                    """
                )
        finally:
            self.conn.unregister("_m40_stage")

    def validate_memory_consistency(self):
        """Validate canonical uniqueness and child-table integrity."""
        duplicate_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT forecast_date,
                       asset_id,
                       horizon_days,
                       model_version,
                       COUNT(*) AS row_count
                FROM m40_forecast_memory
                GROUP BY
                    forecast_date,
                    asset_id,
                    horizon_days,
                    model_version
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        orphan_models = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM m40_model_memory child
            LEFT JOIN m40_forecast_memory parent
              ON parent.forecast_memory_id=
                 child.forecast_memory_id
            WHERE parent.forecast_memory_id IS NULL
            """
        ).fetchone()[0]

        orphan_attributions = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM m40_attribution_memory child
            LEFT JOIN m40_forecast_memory parent
              ON parent.forecast_memory_id=
                 child.forecast_memory_id
            WHERE parent.forecast_memory_id IS NULL
            """
        ).fetchone()[0]

        invalid_matured = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM m40_forecast_memory
            WHERE outcome_status='MATURED'
              AND (
                    realized_date IS NULL
                 OR realized_price IS NULL
                 OR realized_return_pct IS NULL
                 OR absolute_error_pct IS NULL
                 OR direction_correct IS NULL
                 OR interval_covered IS NULL
                 OR probability_outcome IS NULL
              )
            """
        ).fetchone()[0]

        if duplicate_count:
            raise RuntimeError(
                f"Memory validation failed: "
                f"{duplicate_count} canonical duplicates."
            )
        if orphan_models:
            raise RuntimeError(
                f"Memory validation failed: "
                f"{orphan_models} orphan model rows."
            )
        if orphan_attributions:
            raise RuntimeError(
                f"Memory validation failed: "
                f"{orphan_attributions} orphan attribution rows."
            )
        if invalid_matured:
            raise RuntimeError(
                f"Memory validation failed: "
                f"{invalid_matured} incomplete matured forecasts."
            )

        return {
            "canonical_duplicates": int(duplicate_count),
            "orphan_model_rows": int(orphan_models),
            "orphan_attribution_rows": int(
                orphan_attributions
            ),
            "invalid_matured_rows": int(invalid_matured),
        }

    def recover_interrupted_runs(self):
        """Close stale RUNNING rows before beginning a new transaction."""
        self.conn.execute(
            """
            UPDATE module40_runs
            SET status='FAILED',
                completed_at_utc=COALESCE(
                    completed_at_utc,
                    CURRENT_TIMESTAMP
                ),
                notes=COALESCE(notes,'')
                    || '; Automatically closed by v11.0.1 recovery.'
            WHERE status='RUNNING'
              AND run_id<>?
            """,
            [self.run_id],
        )

    def ingest_forecasts(self):
        forecasts = self.conn.execute(
            """
            SELECT f.*,
                   c.calibrated_probability_positive,
                   c.conformal_lower_return_pct,
                   c.conformal_upper_return_pct,
                   p.dominant_predictive_regime,
                   p.predictive_regime_confidence
            FROM m38_asset_forecasts f
            LEFT JOIN m39_calibrated_forecasts c
              ON c.run_id=?
             AND c.asset_id=f.asset_id
             AND c.horizon_days=f.horizon_days
             AND c.forecast_date=f.forecast_date
            LEFT JOIN m38_portfolio_forecast p
              ON p.run_id=f.run_id
            WHERE f.run_id=?
            ORDER BY f.asset_id, f.horizon_days
            """,
            [self.source39, self.source38],
        ).fetchdf()

        rows = []
        for _, row in forecasts.iterrows():
            forecast_date = pd.Timestamp(
                row["forecast_date"]
            ).date()
            horizon = int(row["horizon_days"])
            rows.append({
                "forecast_memory_id": memory_id(
                    self.source38,
                    row["asset_id"],
                    horizon,
                    forecast_date,
                ),
                "source_module38_run_id": self.source38,
                "source_module39_run_id": self.source39,
                "forecast_date": forecast_date,
                "outcome_due_date": (
                    pd.Timestamp(forecast_date)
                    + pd.Timedelta(days=horizon)
                ).date(),
                "asset_id": row["asset_id"],
                "horizon_days": horizon,
                "current_price": safe_float(
                    row["current_price"]
                ),
                "predicted_return_pct": safe_float(
                    row["predicted_return_pct"]
                ),
                "predicted_price": safe_float(
                    row["predicted_price"]
                ),
                "raw_probability_positive": safe_float(
                    row["probability_positive"]
                ),
                "calibrated_probability_positive": safe_float(
                    row[
                        "calibrated_probability_positive"
                    ],
                    safe_float(
                        row["probability_positive"],
                        0.5,
                    ),
                ),
                "raw_lower_return_pct": safe_float(
                    row["lower_return_pct"]
                ),
                "raw_upper_return_pct": safe_float(
                    row["upper_return_pct"]
                ),
                "calibrated_lower_return_pct": safe_float(
                    row["conformal_lower_return_pct"],
                    safe_float(row["lower_return_pct"]),
                ),
                "calibrated_upper_return_pct": safe_float(
                    row["conformal_upper_return_pct"],
                    safe_float(row["upper_return_pct"]),
                ),
                "forecast_confidence": safe_float(
                    row["forecast_confidence"]
                ),
                "model_agreement": safe_float(
                    row["model_agreement"]
                ),
                "predictive_regime": row[
                    "dominant_predictive_regime"
                ],
                "predictive_regime_confidence": safe_float(
                    row[
                        "predictive_regime_confidence"
                    ]
                ),
                "forecast_status": row["forecast_status"],
                "model_version": "11.0.3",
                "outcome_status": "PENDING",
                "realized_date": pd.NaT,
                "realized_price": np.nan,
                "realized_return_pct": np.nan,
                "forecast_error_pct": np.nan,
                "absolute_error_pct": np.nan,
                "direction_correct": pd.NA,
                "interval_covered": pd.NA,
                "probability_outcome": pd.NA,
                "matured_at_utc": pd.NaT,
                "created_at_utc": utcnow(),
            })

        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame

        # Preserve matured fields if this forecast already exists.
        existing = self.conn.execute(
            """
            SELECT forecast_memory_id,
                   outcome_status, realized_date,
                   realized_price, realized_return_pct,
                   forecast_error_pct, absolute_error_pct,
                   direction_correct, interval_covered,
                   probability_outcome, matured_at_utc,
                   created_at_utc
            FROM m40_forecast_memory
            """
        ).fetchdf()
        if not existing.empty:
            frame = frame.merge(
                existing,
                on="forecast_memory_id",
                how="left",
                suffixes=("", "_existing"),
            )
            preserve = [
                "outcome_status",
                "realized_date",
                "realized_price",
                "realized_return_pct",
                "forecast_error_pct",
                "absolute_error_pct",
                "direction_correct",
                "interval_covered",
                "probability_outcome",
                "matured_at_utc",
                "created_at_utc",
            ]
            for column in preserve:
                existing_column = f"{column}_existing"
                frame[column] = frame[
                    existing_column
                ].combine_first(frame[column])
                frame.drop(
                    columns=[existing_column],
                    inplace=True,
                )
        self.upsert("m40_forecast_memory", frame)
        return frame

    def ingest_models(self):
        models = self.conn.execute(
            """
            SELECT *
            FROM m38_model_validation
            WHERE run_id=?
            """,
            [self.source38],
        ).fetchdf()
        rows = []
        for _, row in models.iterrows():
            forecast_row = self.conn.execute(
                """
                SELECT forecast_memory_id
                FROM m40_forecast_memory
                WHERE source_module38_run_id=?
                  AND asset_id=?
                  AND horizon_days=?
                LIMIT 1
                """,
                [
                    self.source38,
                    row["asset_id"],
                    int(row["horizon_days"]),
                ],
            ).fetchone()
            if forecast_row is None:
                continue
            rows.append({
                "forecast_memory_id": forecast_row[0],
                "model_key": row["model_key"],
                "validation_rows": int(
                    row["validation_rows"]
                ),
                "validation_mae_pct": safe_float(
                    row["validation_mae_pct"]
                ),
                "validation_rmse_pct": safe_float(
                    row["validation_rmse_pct"]
                ),
                "directional_accuracy_pct": safe_float(
                    row["directional_accuracy_pct"]
                ),
                "ensemble_weight": safe_float(
                    row["ensemble_weight"]
                ),
                "selected": bool(row["selected"]),
                "created_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert("m40_model_memory", frame)
        return frame

    def ingest_attributions(self):
        data = self.conn.execute(
            """
            SELECT *
            FROM m38_forecast_attribution
            WHERE run_id=?
            """,
            [self.source38],
        ).fetchdf()
        rows = []
        for _, row in data.iterrows():
            forecast_row = self.conn.execute(
                """
                SELECT forecast_memory_id
                FROM m40_forecast_memory
                WHERE source_module38_run_id=?
                  AND asset_id=?
                  AND horizon_days=?
                LIMIT 1
                """,
                [
                    self.source38,
                    row["asset_id"],
                    int(row["horizon_days"]),
                ],
            ).fetchone()
            if forecast_row is None:
                continue
            rows.append({
                "forecast_memory_id": forecast_row[0],
                "driver_key": row["driver_key"],
                "driver_category": row[
                    "driver_category"
                ],
                "contribution_pct": safe_float(
                    row["contribution_pct"]
                ),
                "contribution_direction": row[
                    "contribution_direction"
                ],
                "importance_rank": int(
                    row["importance_rank"]
                ),
                "created_at_utc": utcnow(),
            })
        frame = pd.DataFrame(rows)
        self.upsert(
            "m40_attribution_memory",
            frame,
        )
        return frame

    def mature_outcomes(self):
        pending = self.conn.execute(
            """
            SELECT *
            FROM m40_forecast_memory
            WHERE outcome_status='PENDING'
              AND outcome_due_date<=CURRENT_DATE
            ORDER BY outcome_due_date
            """
        ).fetchdf()
        matured = 0

        for _, row in pending.iterrows():
            realized = self.conn.execute(
                """
                SELECT observation_date, price_usd
                FROM canonical_market_daily
                WHERE asset_id=?
                  AND observation_date>=?
                  AND price_usd IS NOT NULL
                ORDER BY observation_date
                LIMIT 1
                """,
                [
                    row["asset_id"],
                    row["outcome_due_date"],
                ],
            ).fetchone()
            if realized is None:
                continue

            realized_date = pd.Timestamp(
                realized[0]
            ).date()
            realized_price = float(realized[1])
            realized_return = (
                realized_price
                / float(row["current_price"])
                - 1
            ) * 100
            error = (
                realized_return
                - float(row["predicted_return_pct"])
            )
            direction_correct = bool(
                np.sign(realized_return)
                == np.sign(
                    float(row["predicted_return_pct"])
                )
            )
            interval_covered = bool(
                realized_return
                >= float(
                    row[
                        "calibrated_lower_return_pct"
                    ]
                )
                and realized_return
                <= float(
                    row[
                        "calibrated_upper_return_pct"
                    ]
                )
            )
            probability_outcome = int(
                realized_return > 0
            )

            self.conn.execute(
                """
                UPDATE m40_forecast_memory
                SET outcome_status='MATURED',
                    realized_date=?,
                    realized_price=?,
                    realized_return_pct=?,
                    forecast_error_pct=?,
                    absolute_error_pct=?,
                    direction_correct=?,
                    interval_covered=?,
                    probability_outcome=?,
                    matured_at_utc=?
                WHERE forecast_memory_id=?
                """,
                [
                    realized_date,
                    realized_price,
                    realized_return,
                    error,
                    abs(error),
                    direction_correct,
                    interval_covered,
                    probability_outcome,
                    utcnow(),
                    row["forecast_memory_id"],
                ],
            )
            matured += 1
        return matured

    def learning_summaries(self):
        memory = self.conn.execute(
            """
            SELECT *
            FROM m40_forecast_memory
            """
        ).fetchdf()
        matured = memory[
            memory["outcome_status"] == "MATURED"
        ].copy()
        rows = []

        group_specs = [
            (
                "ASSET_HORIZON",
                ["asset_id", "horizon_days"],
            ),
            (
                "REGIME",
                [
                    "predictive_regime",
                    "asset_id",
                    "horizon_days",
                ],
            ),
            (
                "CONFIDENCE_BAND",
                [
                    "confidence_band",
                    "asset_id",
                    "horizon_days",
                ],
            ),
        ]

        if not matured.empty:
            matured["confidence_band"] = pd.cut(
                matured["forecast_confidence"],
                bins=[-np.inf, 0.4, 0.6, 0.8, np.inf],
                labels=[
                    "LOW",
                    "MODERATE",
                    "HIGH",
                    "VERY_HIGH",
                ],
            ).astype(str)

        for grouping_type, columns in group_specs:
            if matured.empty:
                continue
            for keys, group in matured.groupby(
                columns,
                dropna=False,
            ):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                key_map = dict(zip(columns, keys))
                total_filter = memory[
                    (memory["asset_id"]
                     == key_map["asset_id"])
                    & (
                        memory["horizon_days"]
                        == key_map["horizon_days"]
                    )
                ]
                if "predictive_regime" in key_map:
                    total_filter = total_filter[
                        total_filter["predictive_regime"]
                        == key_map[
                            "predictive_regime"
                        ]
                    ]
                probability = group[
                    "calibrated_probability_positive"
                ].astype(float)
                outcome = group[
                    "probability_outcome"
                ].astype(float)
                brier = float(
                    np.mean(
                        (probability - outcome) ** 2
                    )
                )
                calibration_gap = float(
                    probability.mean()
                    - outcome.mean()
                )
                strategy_return = (
                    np.sign(
                        group[
                            "predicted_return_pct"
                        ].astype(float)
                    )
                    * group[
                        "realized_return_pct"
                    ].astype(float)
                    / 100
                )
                realized_sharpe = (
                    float(
                        strategy_return.mean()
                        / strategy_return.std(ddof=0)
                        * math.sqrt(
                            365
                            / max(
                                int(
                                    key_map[
                                        "horizon_days"
                                    ]
                                ),
                                1,
                            )
                        )
                    )
                    if strategy_return.std(ddof=0)
                    > 0
                    else 0.0
                )
                minimum = int(
                    self.cfg[
                        "minimum_matured_forecasts"
                    ]
                )
                status = (
                    "RELIABLE"
                    if len(group) >= minimum
                    and group[
                        "direction_correct"
                    ].mean()
                    >= 0.55
                    and brier <= 0.25
                    else "LEARNING"
                )
                if grouping_type == "REGIME":
                    grouping_key = str(
                        key_map["predictive_regime"]
                    )
                elif grouping_type == "CONFIDENCE_BAND":
                    grouping_key = str(
                        key_map["confidence_band"]
                    )
                else:
                    grouping_key = (
                        f"{key_map['asset_id']}_"
                        f"{key_map['horizon_days']}D"
                    )
                rows.append({
                    "run_id": self.run_id,
                    "grouping_type": grouping_type,
                    "grouping_key": grouping_key,
                    "asset_id": key_map[
                        "asset_id"
                    ],
                    "horizon_days": int(
                        key_map["horizon_days"]
                    ),
                    "forecasts_total": len(
                        total_filter
                    ),
                    "outcomes_matured": len(group),
                    "maturity_rate_pct": (
                        len(group)
                        / max(
                            len(total_filter),
                            1,
                        )
                        * 100
                    ),
                    "mean_absolute_error_pct": float(
                        group[
                            "absolute_error_pct"
                        ].mean()
                    ),
                    "root_mean_squared_error_pct": float(
                        np.sqrt(
                            np.mean(
                                group[
                                    "forecast_error_pct"
                                ].astype(float)
                                ** 2
                            )
                        )
                    ),
                    "directional_accuracy_pct": float(
                        group[
                            "direction_correct"
                        ].mean()
                        * 100
                    ),
                    "brier_score": brier,
                    "interval_coverage_pct": float(
                        group[
                            "interval_covered"
                        ].mean()
                        * 100
                    ),
                    "mean_confidence": float(
                        group[
                            "forecast_confidence"
                        ].mean()
                    ),
                    "realized_sharpe": (
                        realized_sharpe
                    ),
                    "calibration_gap": (
                        calibration_gap
                    ),
                    "learning_status": status,
                    "calculated_at_utc": utcnow(),
                })

        frame = pd.DataFrame(rows)
        self.upsert("m40_learning_summary", frame)
        return frame

    def calibration_curves(self):
        matured = self.conn.execute(
            """
            SELECT *
            FROM m40_forecast_memory
            WHERE outcome_status='MATURED'
            """
        ).fetchdf()
        rows = []
        bins = np.linspace(0, 1, 11)

        if not matured.empty:
            for (asset, horizon), group in matured.groupby(
                ["asset_id", "horizon_days"]
            ):
                for lower, upper in zip(
                    bins[:-1],
                    bins[1:],
                ):
                    include_upper = upper == 1.0
                    subset = group[
                        (
                            group[
                                "calibrated_probability_positive"
                            ]
                            >= lower
                        )
                        & (
                            group[
                                "calibrated_probability_positive"
                            ]
                            <= upper
                            if include_upper
                            else group[
                                "calibrated_probability_positive"
                            ]
                            < upper
                        )
                    ]
                    if subset.empty:
                        continue
                    predicted = float(
                        subset[
                            "calibrated_probability_positive"
                        ].mean()
                    )
                    observed = float(
                        subset[
                            "probability_outcome"
                        ].mean()
                    )
                    rows.append({
                        "run_id": self.run_id,
                        "asset_id": asset,
                        "horizon_days": int(
                            horizon
                        ),
                        "probability_bin_lower": (
                            float(lower)
                        ),
                        "probability_bin_upper": (
                            float(upper)
                        ),
                        "forecasts": len(subset),
                        "mean_predicted_probability": (
                            predicted
                        ),
                        "observed_positive_rate": (
                            observed
                        ),
                        "calibration_gap": (
                            predicted - observed
                        ),
                        "calculated_at_utc": utcnow(),
                    })
        frame = pd.DataFrame(rows)
        self.upsert("m40_calibration_curve", frame)
        return frame

    def model_leaderboard(self):
        models = self.conn.execute(
            """
            SELECT fm.asset_id,
                   fm.horizon_days,
                   mm.model_key,
                   mm.validation_mae_pct,
                   mm.validation_rmse_pct,
                   mm.directional_accuracy_pct,
                   mm.ensemble_weight,
                   fm.absolute_error_pct,
                   fm.outcome_status
            FROM m40_model_memory mm
            JOIN m40_forecast_memory fm
              ON fm.forecast_memory_id=
                 mm.forecast_memory_id
            """
        ).fetchdf()
        rows = []

        for (
            asset,
            horizon,
            model_key,
        ), group in models.groupby(
            ["asset_id", "horizon_days", "model_key"]
        ):
            matured = group[
                group["outcome_status"] == "MATURED"
            ]
            realized_mae = (
                float(
                    matured[
                        "absolute_error_pct"
                    ].mean()
                )
                if not matured.empty
                else np.nan
            )
            validation_mae = float(
                group[
                    "validation_mae_pct"
                ].mean()
            )
            direction = float(
                group[
                    "directional_accuracy_pct"
                ].mean()
            )
            score = (
                0.45
                * max(100 - validation_mae, 0)
                + 0.35 * direction
                + 0.20
                * (
                    max(100 - realized_mae, 0)
                    if np.isfinite(realized_mae)
                    else 50
                )
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": asset,
                "horizon_days": int(horizon),
                "model_key": model_key,
                "forecasts_evaluated": len(
                    matured
                ),
                "mean_validation_mae_pct": (
                    validation_mae
                ),
                "mean_validation_rmse_pct": float(
                    group[
                        "validation_rmse_pct"
                    ].mean()
                ),
                "mean_directional_accuracy_pct": (
                    direction
                ),
                "mean_ensemble_weight": float(
                    group[
                        "ensemble_weight"
                    ].mean()
                ),
                "realized_forecast_mae_pct": (
                    realized_mae
                ),
                "model_score": score,
                "model_rank": 0,
                "model_status": (
                    "PROVEN"
                    if len(matured)
                    >= int(
                        self.cfg[
                            "minimum_matured_forecasts"
                        ]
                    )
                    else "OBSERVATION"
                ),
                "calculated_at_utc": utcnow(),
            })

        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame["model_rank"] = (
                frame.groupby(
                    ["asset_id", "horizon_days"]
                )["model_score"]
                .rank(
                    ascending=False,
                    method="dense",
                )
                .astype(int)
            )
        self.upsert("m40_model_leaderboard", frame)
        return frame

    def retraining_recommendations(self):
        matured = self.conn.execute(
            """
            SELECT *
            FROM m40_forecast_memory
            WHERE outcome_status='MATURED'
            ORDER BY realized_date
            """
        ).fetchdf()
        rows = []

        if not matured.empty:
            for (asset, horizon), group in matured.groupby(
                ["asset_id", "horizon_days"]
            ):
                group = group.sort_values(
                    "realized_date"
                )
                split = max(len(group) // 2, 1)
                prior = group.iloc[:split]
                recent = group.iloc[split:]
                if recent.empty:
                    recent = prior
                recent_mae = float(
                    recent[
                        "absolute_error_pct"
                    ].mean()
                )
                prior_mae = float(
                    prior[
                        "absolute_error_pct"
                    ].mean()
                )
                recent_direction = float(
                    recent[
                        "direction_correct"
                    ].mean()
                    * 100
                )
                prior_direction = float(
                    prior[
                        "direction_correct"
                    ].mean()
                    * 100
                )
                calibration_gap = float(
                    recent[
                        "calibrated_probability_positive"
                    ].mean()
                    - recent[
                        "probability_outcome"
                    ].mean()
                )
                drift = bool(
                    recent_mae
                    > prior_mae
                    * float(
                        self.cfg[
                            "retraining_mae_multiplier"
                        ]
                    )
                    or recent_direction
                    < prior_direction - 15
                    or abs(calibration_gap) > 0.20
                )
                enough = len(group) >= int(
                    self.cfg[
                        "minimum_matured_forecasts"
                    ]
                )
                priority = (
                    "HIGH"
                    if drift and enough
                    else "MEDIUM"
                    if drift
                    else "LOW"
                )
                recommendation = (
                    "RETRAIN_NOW"
                    if priority == "HIGH"
                    else "CONTINUE_MONITORING"
                    if priority == "LOW"
                    else "ACCUMULATE_MORE_EVIDENCE"
                )
                rows.append({
                    "run_id": self.run_id,
                    "asset_id": asset,
                    "horizon_days": int(
                        horizon
                    ),
                    "matured_forecasts": len(group),
                    "recent_mae_pct": recent_mae,
                    "prior_mae_pct": prior_mae,
                    "recent_directional_accuracy_pct": (
                        recent_direction
                    ),
                    "prior_directional_accuracy_pct": (
                        prior_direction
                    ),
                    "calibration_gap": (
                        calibration_gap
                    ),
                    "drift_detected": drift,
                    "retraining_priority": (
                        priority
                    ),
                    "recommendation": recommendation,
                    "calculated_at_utc": utcnow(),
                })
        frame = pd.DataFrame(rows)
        self.upsert(
            "m40_retraining_recommendations",
            frame,
        )
        return frame

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module40_runs(
                run_id,
                source_module38_run_id,
                source_module39_run_id,
                started_at_utc,
                completed_at_utc,
                status,
                forecasts_ingested,
                model_snapshots_ingested,
                attribution_snapshots_ingested,
                outcomes_matured,
                learning_summary_rows,
                calibration_curve_rows,
                models_evaluated,
                earliest_forecast_date,
                latest_forecast_date,
                realized_horizons,
                memory_status,
                continuous_learning_status,
                recommendation,
                notes,
                platform_version
            )
            VALUES(
                ?, ?, ?, ?, NULL, 'RUNNING',
                0, 0, 0, 0, 0, 0, 0,
                NULL, NULL, 0,
                NULL, NULL, NULL, NULL, '11.0.3'
            )
            """,
            [
                self.run_id,
                self.source38,
                self.source39,
                self.started,
            ],
        )

        try:
            self.recover_interrupted_runs()
            self.conn.execute("BEGIN TRANSACTION")

            forecasts = self.ingest_forecasts()
            models = self.ingest_models()
            attributions = self.ingest_attributions()
            matured_now = self.mature_outcomes()
            learning = self.learning_summaries()
            curves = self.calibration_curves()
            leaderboard = self.model_leaderboard()
            retraining = (
                self.retraining_recommendations()
            )

            memory = self.conn.execute(
                """
                SELECT *
                FROM m40_forecast_memory
                """
            ).fetchdf()
            matured = memory[
                memory["outcome_status"] == "MATURED"
            ]
            pending = memory[
                memory["outcome_status"] == "PENDING"
            ]

            if matured.empty:
                mae = direction = brier = coverage = gap = np.nan
            else:
                mae = float(
                    matured[
                        "absolute_error_pct"
                    ].mean()
                )
                direction = float(
                    matured[
                        "direction_correct"
                    ].mean()
                    * 100
                )
                probability = matured[
                    "calibrated_probability_positive"
                ].astype(float)
                outcome = matured[
                    "probability_outcome"
                ].astype(float)
                brier = float(
                    np.mean(
                        (probability - outcome) ** 2
                    )
                )
                coverage = float(
                    matured[
                        "interval_covered"
                    ].mean()
                    * 100
                )
                gap = float(
                    probability.mean()
                    - outcome.mean()
                )

            high_priority = (
                int(
                    (
                        retraining[
                            "retraining_priority"
                        ]
                        == "HIGH"
                    ).sum()
                )
                if not retraining.empty
                else 0
            )
            minimum = int(
                self.cfg[
                    "minimum_matured_forecasts"
                ]
            )
            memory_status = (
                "ESTABLISHED"
                if len(matured) >= minimum
                else "ACCUMULATING"
            )
            continuous_status = (
                "ACTIVE"
                if len(matured) >= minimum
                else "BASELINE_CREATED"
            )
            recommendation = (
                "CONTINUOUS_LEARNING_OPERATIONAL"
                if continuous_status == "ACTIVE"
                and high_priority == 0
                else "RETRAIN_PRIORITY_MODELS"
                if high_priority > 0
                else "CONTINUE_FORECAST_COLLECTION"
            )

            summary = pd.DataFrame([{
                "run_id": self.run_id,
                "forecasts_stored": len(memory),
                "pending_forecasts": len(pending),
                "matured_forecasts": len(matured),
                "assets_tracked": (
                    memory["asset_id"].nunique()
                ),
                "horizons_tracked": (
                    memory["horizon_days"].nunique()
                ),
                "mean_absolute_error_pct": mae,
                "directional_accuracy_pct": (
                    direction
                ),
                "mean_brier_score": brier,
                "interval_coverage_pct": coverage,
                "calibration_gap": gap,
                "high_priority_retraining_rows": (
                    high_priority
                ),
                "memory_status": memory_status,
                "continuous_learning_status": (
                    continuous_status
                ),
                "advancement_recommendation": (
                    recommendation
                ),
                "calculated_at_utc": utcnow(),
            }])
            self.upsert(
                "m40_memory_summary",
                summary,
            )

            earliest = (
                memory["forecast_date"].min()
                if not memory.empty
                else pd.NaT
            )
            latest = (
                memory["forecast_date"].max()
                if not memory.empty
                else pd.NaT
            )
            realized_horizons = (
                matured["horizon_days"].nunique()
                if not matured.empty
                else 0
            )
            notes = (
                "Forecast, model, and attribution snapshots stored; "
                "due outcomes matured; learning summaries, calibration "
                "curves, model leaderboard, and retraining recommendations "
                "updated."
            )
            persistence_validation = (
                self.validate_memory_consistency()
            )
            notes = (
                notes
                + " Persistence validation="
                + json.dumps(
                    persistence_validation,
                    separators=(",", ":"),
                )
            )
            self.conn.execute(
                """
                UPDATE module40_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    forecasts_ingested=?,
                    model_snapshots_ingested=?,
                    attribution_snapshots_ingested=?,
                    outcomes_matured=?,
                    learning_summary_rows=?,
                    calibration_curve_rows=?,
                    models_evaluated=?,
                    earliest_forecast_date=?,
                    latest_forecast_date=?,
                    realized_horizons=?,
                    memory_status=?,
                    continuous_learning_status=?,
                    recommendation=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(forecasts),
                    len(models),
                    len(attributions),
                    matured_now,
                    len(learning),
                    len(curves),
                    len(leaderboard),
                    earliest,
                    latest,
                    realized_horizons,
                    memory_status,
                    continuous_status,
                    recommendation,
                    notes,
                    self.run_id,
                ],
            )
            self.conn.execute("COMMIT")
            self.conn.close()
            return summary.iloc[0].to_dict()

        except Exception as exc:
            try:
                self.conn.execute("ROLLBACK")
            except Exception:
                pass

            # Record the failure outside the rolled-back transaction.
            self.conn.execute(
                """
                UPDATE module40_runs
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


def run_module40():
    return Module40Runner().run()
