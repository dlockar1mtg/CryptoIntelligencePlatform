import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module40 import MODULE40_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem + "_before_v11_0_2" + database.suffix
    )
    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)

    before_forecasts = conn.execute(
        "SELECT COUNT(*) FROM m40_forecast_memory"
    ).fetchone()[0]
    before_models = conn.execute(
        "SELECT COUNT(*) FROM m40_model_memory"
    ).fetchone()[0]
    before_attributions = conn.execute(
        "SELECT COUNT(*) FROM m40_attribution_memory"
    ).fetchone()[0]
    before_matured = conn.execute(
        "SELECT COUNT(*) FROM m40_forecast_memory "
        "WHERE outcome_status='MATURED'"
    ).fetchone()[0]

    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute("""
            UPDATE module40_runs
            SET status='FAILED',
                completed_at_utc=COALESCE(completed_at_utc,CURRENT_TIMESTAMP),
                notes=COALESCE(notes,'')
                    || '; Closed during v11.0.2 identity migration.'
            WHERE status='RUNNING'
        """)

        conn.execute("""
            CREATE OR REPLACE TEMP TABLE m40_identity_rank AS
            SELECT
                forecast_memory_id,
                first_value(forecast_memory_id) OVER(
                    PARTITION BY forecast_date,asset_id,horizon_days
                    ORDER BY
                        CASE WHEN outcome_status='MATURED' THEN 0 ELSE 1 END,
                        created_at_utc DESC,
                        forecast_memory_id DESC
                ) AS survivor_id,
                row_number() OVER(
                    PARTITION BY forecast_date,asset_id,horizon_days
                    ORDER BY
                        CASE WHEN outcome_status='MATURED' THEN 0 ELSE 1 END,
                        created_at_utc DESC,
                        forecast_memory_id DESC
                ) AS identity_rank
            FROM m40_forecast_memory
        """)

        duplicate_count = conn.execute(
            "SELECT COUNT(*) FROM m40_identity_rank WHERE identity_rank>1"
        ).fetchone()[0]

        conn.execute("""
            CREATE OR REPLACE TEMP TABLE m40_models_consolidated AS
            SELECT
                r.survivor_id AS forecast_memory_id,
                m.model_key,
                arg_max(m.validation_rows,m.created_at_utc) AS validation_rows,
                arg_max(m.validation_mae_pct,m.created_at_utc) AS validation_mae_pct,
                arg_max(m.validation_rmse_pct,m.created_at_utc) AS validation_rmse_pct,
                arg_max(m.directional_accuracy_pct,m.created_at_utc)
                    AS directional_accuracy_pct,
                arg_max(m.ensemble_weight,m.created_at_utc) AS ensemble_weight,
                bool_or(m.selected) AS selected,
                max(m.created_at_utc) AS created_at_utc
            FROM m40_model_memory m
            JOIN m40_identity_rank r
              ON r.forecast_memory_id=m.forecast_memory_id
            GROUP BY r.survivor_id,m.model_key
        """)

        conn.execute("""
            CREATE OR REPLACE TEMP TABLE m40_attributions_consolidated AS
            SELECT
                r.survivor_id AS forecast_memory_id,
                a.driver_key,
                arg_max(a.driver_category,a.created_at_utc) AS driver_category,
                arg_max(a.contribution_pct,a.created_at_utc) AS contribution_pct,
                arg_max(a.contribution_direction,a.created_at_utc)
                    AS contribution_direction,
                arg_max(a.importance_rank,a.created_at_utc) AS importance_rank,
                max(a.created_at_utc) AS created_at_utc
            FROM m40_attribution_memory a
            JOIN m40_identity_rank r
              ON r.forecast_memory_id=a.forecast_memory_id
            GROUP BY r.survivor_id,a.driver_key
        """)

        conn.execute("DELETE FROM m40_model_memory")
        conn.execute("DELETE FROM m40_attribution_memory")
        conn.execute("""
            DELETE FROM m40_forecast_memory
            WHERE forecast_memory_id IN(
                SELECT forecast_memory_id
                FROM m40_identity_rank
                WHERE identity_rank>1
            )
        """)
        conn.execute("INSERT INTO m40_model_memory SELECT * FROM m40_models_consolidated")
        conn.execute(
            "INSERT INTO m40_attribution_memory "
            "SELECT * FROM m40_attributions_consolidated"
        )

        conn.execute("DROP INDEX IF EXISTS ux_m40_canonical_forecast")
        conn.execute("""
            CREATE UNIQUE INDEX ux_m40_canonical_forecast
            ON m40_forecast_memory(forecast_date,asset_id,horizon_days)
        """)

        duplicates_after = conn.execute("""
            SELECT COUNT(*) FROM(
                SELECT forecast_date,asset_id,horizon_days,COUNT(*) n
                FROM m40_forecast_memory
                GROUP BY forecast_date,asset_id,horizon_days
                HAVING COUNT(*)>1
            )
        """).fetchone()[0]
        orphan_models = conn.execute("""
            SELECT COUNT(*)
            FROM m40_model_memory c
            LEFT JOIN m40_forecast_memory p USING(forecast_memory_id)
            WHERE p.forecast_memory_id IS NULL
        """).fetchone()[0]
        orphan_attributions = conn.execute("""
            SELECT COUNT(*)
            FROM m40_attribution_memory c
            LEFT JOIN m40_forecast_memory p USING(forecast_memory_id)
            WHERE p.forecast_memory_id IS NULL
        """).fetchone()[0]
        matured_after = conn.execute(
            "SELECT COUNT(*) FROM m40_forecast_memory "
            "WHERE outcome_status='MATURED'"
        ).fetchone()[0]

        if duplicates_after:
            raise RuntimeError(f"Canonical duplicates remain: {duplicates_after}")
        if orphan_models or orphan_attributions:
            raise RuntimeError(
                "Child lineage migration failed. "
                f"models={orphan_models}, attributions={orphan_attributions}"
            )
        if matured_after != before_matured:
            raise RuntimeError(
                "Matured forecast preservation failed. "
                f"before={before_matured}, after={matured_after}"
            )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        conn.close()
        raise

    after_forecasts = conn.execute(
        "SELECT COUNT(*) FROM m40_forecast_memory"
    ).fetchone()[0]
    after_models = conn.execute(
        "SELECT COUNT(*) FROM m40_model_memory"
    ).fetchone()[0]
    after_attributions = conn.execute(
        "SELECT COUNT(*) FROM m40_attribution_memory"
    ).fetchone()[0]
    conn.close()

    print("Crypto Intelligence Platform v11.0.2 installed.")
    print(f"Forecast rows before migration: {before_forecasts}")
    print(f"Duplicate forecast rows removed: {duplicate_count}")
    print(f"Forecast rows after migration: {after_forecasts}")
    print(f"Model rows consolidated: {before_models} -> {after_models}")
    print(
        f"Attribution rows consolidated: "
        f"{before_attributions} -> {after_attributions}"
    )
    print(f"Matured forecasts preserved: {before_matured}")
    print(
        "Database uniqueness now uses "
        "forecast_date + asset_id + horizon_days."
    )

if __name__ == "__main__":
    main()
