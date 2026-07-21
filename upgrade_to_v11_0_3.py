import shutil
import uuid

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module40 import MODULE40_SCHEMA


NAMESPACE = uuid.UUID(
    "4ac9db72-12a2-4e6e-8c15-1fa242c7cb83"
)


def canonical_id(
    forecast_date,
    asset_id,
    horizon_days,
):
    key = (
        f"{forecast_date}|{asset_id}|"
        f"{int(horizon_days)}"
    )
    return str(uuid.uuid5(NAMESPACE, key))


def main():
    settings, _ = load_all()
    database = path_for(
        settings,
        "database_path",
    )
    backup = database.with_name(
        database.stem
        + "_before_v11_0_3"
        + database.suffix
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
        """
        SELECT COUNT(*)
        FROM m40_forecast_memory
        WHERE outcome_status='MATURED'
        """
    ).fetchone()[0]

    source_rows = conn.execute(
        """
        SELECT *
        FROM m40_forecast_memory
        ORDER BY
            forecast_date,
            asset_id,
            horizon_days,
            CASE
                WHEN outcome_status='MATURED'
                THEN 0 ELSE 1
            END,
            created_at_utc DESC,
            forecast_memory_id DESC
        """
    ).fetchdf()

    if source_rows.empty:
        print(
            "No existing forecast memory rows were found. "
            "Creating the canonical index only."
        )

    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            """
            UPDATE module40_runs
            SET status='FAILED',
                completed_at_utc=COALESCE(
                    completed_at_utc,
                    CURRENT_TIMESTAMP
                ),
                notes=COALESCE(notes,'')
                    || '; Closed during v11.0.3 canonical rebuild.'
            WHERE status='RUNNING'
            """
        )

        conn.execute(
            """
            DROP INDEX IF EXISTS
            ux_m40_canonical_forecast
            """
        )

        # Build new canonical tables with the same schema.
        conn.execute(
            """
            DROP TABLE IF EXISTS
            m40_forecast_memory_rebuild
            """
        )
        conn.execute(
            """
            CREATE TABLE
            m40_forecast_memory_rebuild
            AS SELECT *
            FROM m40_forecast_memory
            WHERE 1=0
            """
        )

        conn.execute(
            """
            DROP TABLE IF EXISTS
            m40_model_memory_rebuild
            """
        )
        conn.execute(
            """
            CREATE TABLE
            m40_model_memory_rebuild
            AS SELECT *
            FROM m40_model_memory
            WHERE 1=0
            """
        )

        conn.execute(
            """
            DROP TABLE IF EXISTS
            m40_attribution_memory_rebuild
            """
        )
        conn.execute(
            """
            CREATE TABLE
            m40_attribution_memory_rebuild
            AS SELECT *
            FROM m40_attribution_memory
            WHERE 1=0
            """
        )

        # Build canonical parent rows in Python so identity is explicit.
        canonical_rows = []
        mapping_rows = []
        grouped = source_rows.groupby(
            [
                "forecast_date",
                "asset_id",
                "horizon_days",
            ],
            sort=False,
            dropna=False,
        )

        for (
            forecast_date,
            asset_id,
            horizon_days,
        ), group in grouped:
            group = group.copy()
            matured = group[
                group["outcome_status"] == "MATURED"
            ]
            survivor = (
                matured.iloc[0]
                if not matured.empty
                else group.iloc[0]
            ).copy()

            new_id = canonical_id(
                forecast_date,
                asset_id,
                horizon_days,
            )
            old_ids = group[
                "forecast_memory_id"
            ].tolist()

            survivor["forecast_memory_id"] = (
                new_id
            )
            survivor["model_version"] = (
                "11.0.3"
            )

            canonical_rows.append(
                survivor.to_dict()
            )
            for old_id in old_ids:
                mapping_rows.append({
                    "old_id": old_id,
                    "new_id": new_id,
                })

        if canonical_rows:
            import pandas as pd

            canonical_frame = pd.DataFrame(
                canonical_rows
            )
            mapping_frame = pd.DataFrame(
                mapping_rows
            )

            conn.register(
                "_m40_parent_stage",
                canonical_frame,
            )
            conn.execute(
                """
                INSERT INTO
                m40_forecast_memory_rebuild
                SELECT *
                FROM _m40_parent_stage
                """
            )
            conn.unregister(
                "_m40_parent_stage"
            )

            conn.register(
                "_m40_id_map",
                mapping_frame,
            )

            # Consolidate model lineage deterministically.
            conn.execute(
                """
                INSERT INTO
                m40_model_memory_rebuild
                SELECT
                    map.new_id
                        AS forecast_memory_id,
                    model_key,
                    arg_max(
                        validation_rows,
                        created_at_utc
                    ) AS validation_rows,
                    arg_max(
                        validation_mae_pct,
                        created_at_utc
                    ) AS validation_mae_pct,
                    arg_max(
                        validation_rmse_pct,
                        created_at_utc
                    ) AS validation_rmse_pct,
                    arg_max(
                        directional_accuracy_pct,
                        created_at_utc
                    )
                        AS directional_accuracy_pct,
                    arg_max(
                        ensemble_weight,
                        created_at_utc
                    ) AS ensemble_weight,
                    bool_or(selected)
                        AS selected,
                    max(created_at_utc)
                        AS created_at_utc
                FROM m40_model_memory child
                JOIN _m40_id_map map
                  ON map.old_id=
                     child.forecast_memory_id
                GROUP BY
                    map.new_id,
                    model_key
                """
            )

            # Consolidate attribution lineage deterministically.
            conn.execute(
                """
                INSERT INTO
                m40_attribution_memory_rebuild
                SELECT
                    map.new_id
                        AS forecast_memory_id,
                    driver_key,
                    arg_max(
                        driver_category,
                        created_at_utc
                    ) AS driver_category,
                    arg_max(
                        contribution_pct,
                        created_at_utc
                    ) AS contribution_pct,
                    arg_max(
                        contribution_direction,
                        created_at_utc
                    )
                        AS contribution_direction,
                    arg_max(
                        importance_rank,
                        created_at_utc
                    ) AS importance_rank,
                    max(created_at_utc)
                        AS created_at_utc
                FROM m40_attribution_memory child
                JOIN _m40_id_map map
                  ON map.old_id=
                     child.forecast_memory_id
                GROUP BY
                    map.new_id,
                    driver_key
                """
            )
            conn.unregister("_m40_id_map")

        # Validate rebuilt tables before swap.
        rebuilt_duplicates = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    forecast_date,
                    asset_id,
                    horizon_days,
                    COUNT(*) AS row_count
                FROM
                    m40_forecast_memory_rebuild
                GROUP BY
                    forecast_date,
                    asset_id,
                    horizon_days
                HAVING COUNT(*)>1
            )
            """
        ).fetchone()[0]

        rebuilt_orphan_models = conn.execute(
            """
            SELECT COUNT(*)
            FROM m40_model_memory_rebuild child
            LEFT JOIN
                m40_forecast_memory_rebuild parent
              ON parent.forecast_memory_id=
                 child.forecast_memory_id
            WHERE parent.forecast_memory_id
                  IS NULL
            """
        ).fetchone()[0]

        rebuilt_orphan_attributions = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM
                    m40_attribution_memory_rebuild
                    child
                LEFT JOIN
                    m40_forecast_memory_rebuild
                    parent
                  ON parent.forecast_memory_id=
                     child.forecast_memory_id
                WHERE parent.forecast_memory_id
                      IS NULL
                """
            ).fetchone()[0]
        )

        rebuilt_matured = conn.execute(
            """
            SELECT COUNT(*)
            FROM m40_forecast_memory_rebuild
            WHERE outcome_status='MATURED'
            """
        ).fetchone()[0]

        invalid_matured = conn.execute(
            """
            SELECT COUNT(*)
            FROM m40_forecast_memory_rebuild
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

        if rebuilt_duplicates:
            raise RuntimeError(
                "Rebuild validation failed: "
                f"{rebuilt_duplicates} duplicate "
                "prediction events."
            )
        if rebuilt_orphan_models:
            raise RuntimeError(
                "Rebuild validation failed: "
                f"{rebuilt_orphan_models} orphan "
                "model rows."
            )
        if rebuilt_orphan_attributions:
            raise RuntimeError(
                "Rebuild validation failed: "
                f"{rebuilt_orphan_attributions} "
                "orphan attribution rows."
            )
        if invalid_matured:
            raise RuntimeError(
                "Rebuild validation failed: "
                f"{invalid_matured} incomplete "
                "matured forecasts."
            )

        # Duplicated matured copies collapse to one event.
        expected_matured = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT
                    forecast_date,
                    asset_id,
                    horizon_days
                FROM m40_forecast_memory
                WHERE outcome_status='MATURED'
            )
            """
        ).fetchone()[0]

        if rebuilt_matured != expected_matured:
            raise RuntimeError(
                "Matured outcome preservation failed. "
                f"expected={expected_matured}, "
                f"rebuilt={rebuilt_matured}"
            )

        # Atomic rebuild-and-swap.
        conn.execute(
            """
            ALTER TABLE m40_forecast_memory
            RENAME TO m40_forecast_memory_legacy
            """
        )
        conn.execute(
            """
            ALTER TABLE m40_model_memory
            RENAME TO m40_model_memory_legacy
            """
        )
        conn.execute(
            """
            ALTER TABLE m40_attribution_memory
            RENAME TO m40_attribution_memory_legacy
            """
        )

        conn.execute(
            """
            ALTER TABLE
            m40_forecast_memory_rebuild
            RENAME TO m40_forecast_memory
            """
        )
        conn.execute(
            """
            ALTER TABLE
            m40_model_memory_rebuild
            RENAME TO m40_model_memory
            """
        )
        conn.execute(
            """
            ALTER TABLE
            m40_attribution_memory_rebuild
            RENAME TO m40_attribution_memory
            """
        )

        conn.execute(
            """
            CREATE UNIQUE INDEX
            ux_m40_canonical_forecast
            ON m40_forecast_memory(
                forecast_date,
                asset_id,
                horizon_days
            )
            """
        )

        # Recreate child primary-key indexes after CTAS rebuild.
        conn.execute(
            """
            CREATE UNIQUE INDEX
            ux_m40_model_memory_key
            ON m40_model_memory(
                forecast_memory_id,
                model_key
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX
            ux_m40_attribution_memory_key
            ON m40_attribution_memory(
                forecast_memory_id,
                driver_key
            )
            """
        )

        # Final validation after swap.
        final_forecasts = conn.execute(
            """
            SELECT COUNT(*)
            FROM m40_forecast_memory
            """
        ).fetchone()[0]

        final_distinct = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT
                    forecast_date,
                    asset_id,
                    horizon_days
                FROM m40_forecast_memory
            )
            """
        ).fetchone()[0]

        if final_forecasts != final_distinct:
            raise RuntimeError(
                "Final table is not canonical. "
                f"rows={final_forecasts}, "
                f"events={final_distinct}"
            )

        # Legacy tables are retained inside the transaction until all
        # validation succeeds, then removed before commit.
        conn.execute(
            """
            DROP TABLE
            m40_forecast_memory_legacy
            """
        )
        conn.execute(
            """
            DROP TABLE
            m40_model_memory_legacy
            """
        )
        conn.execute(
            """
            DROP TABLE
            m40_attribution_memory_legacy
            """
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
    after_matured = conn.execute(
        """
        SELECT COUNT(*)
        FROM m40_forecast_memory
        WHERE outcome_status='MATURED'
        """
    ).fetchone()[0]

    conn.close()

    print(
        "Crypto Intelligence Platform "
        "v11.0.3 installed."
    )
    print(
        f"Forecast rows rebuilt: "
        f"{before_forecasts} -> "
        f"{after_forecasts}"
    )
    print(
        f"Duplicate prediction rows removed: "
        f"{before_forecasts-after_forecasts}"
    )
    print(
        f"Model rows consolidated: "
        f"{before_models} -> "
        f"{after_models}"
    )
    print(
        f"Attribution rows consolidated: "
        f"{before_attributions} -> "
        f"{after_attributions}"
    )
    print(
        f"Matured prediction events preserved: "
        f"{before_matured} raw rows -> "
        f"{after_matured} canonical events"
    )
    print(
        "Canonical forecast, model, and "
        "attribution indexes created."
    )


if __name__ == "__main__":
    main()
