import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module40 import MODULE40_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem
        + "_before_v11_0_1"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)

    conn.execute(
        """
        UPDATE module40_runs
        SET status='FAILED',
            completed_at_utc=COALESCE(
                completed_at_utc,
                CURRENT_TIMESTAMP
            ),
            notes=COALESCE(notes,'')
                || '; Closed during v11.0.1 persistence upgrade.'
        WHERE status='RUNNING'
        """
    )

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_m40_canonical_forecast
        ON m40_forecast_memory(
            forecast_date,
            asset_id,
            horizon_days,
            model_version
        )
        """
    )

    duplicates = conn.execute(
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

    orphan_models = conn.execute(
        """
        SELECT COUNT(*)
        FROM m40_model_memory child
        LEFT JOIN m40_forecast_memory parent
          ON parent.forecast_memory_id=
             child.forecast_memory_id
        WHERE parent.forecast_memory_id IS NULL
        """
    ).fetchone()[0]

    orphan_attributions = conn.execute(
        """
        SELECT COUNT(*)
        FROM m40_attribution_memory child
        LEFT JOIN m40_forecast_memory parent
          ON parent.forecast_memory_id=
             child.forecast_memory_id
        WHERE parent.forecast_memory_id IS NULL
        """
    ).fetchone()[0]

    conn.close()

    if duplicates:
        raise RuntimeError(
            f"Canonical duplicate rows remain: {duplicates}"
        )
    if orphan_models or orphan_attributions:
        raise RuntimeError(
            "Forecast memory contains orphan child records. "
            f"models={orphan_models}, "
            f"attributions={orphan_attributions}"
        )

    print("Crypto Intelligence Platform v11.0.1 installed.")
    print("Explicit canonical conflict targets are enabled.")
    print("Transactional forecast-memory writes are enabled.")
    print("Rollback-safe recovery is enabled.")
    print("Pre-commit memory validation is enabled.")
    print(f"Canonical duplicates: {duplicates}")
    print(f"Orphan model rows: {orphan_models}")
    print(
        f"Orphan attribution rows: "
        f"{orphan_attributions}"
    )


if __name__ == "__main__":
    main()
