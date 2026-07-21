from crypto_platform.platform import load_all, connect
from crypto_platform.module40 import MODULE40_SCHEMA


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)

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

    indexes = conn.execute(
        """
        SELECT COUNT(*)
        FROM duckdb_indexes()
        WHERE index_name='ux_m40_canonical_forecast'
        """
    ).fetchone()[0]

    conn.close()

    assert duplicates == 0, duplicates
    assert orphan_models == 0, orphan_models
    assert orphan_attributions == 0, orphan_attributions
    assert indexes == 1, indexes

    print("v11.0.1 memory persistence preflight passed.")
    print(f"Canonical duplicates: {duplicates}")
    print(f"Orphan model rows: {orphan_models}")
    print(
        f"Orphan attribution rows: "
        f"{orphan_attributions}"
    )
    print(f"Canonical unique indexes: {indexes}")


if __name__ == "__main__":
    main()
